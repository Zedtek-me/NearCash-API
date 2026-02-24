from celery import shared_task, Task
from typing import Union

from typing import Type
from django.utils import timezone

from typing import Type
from django.utils import timezone

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from utils.helpers.logs import logger

from dtos.generics import EmailArgsDto

class BusinessAsyncOperations:

    @shared_task(bind=True, name="notify_vendor_about_transaction")
    def notify_vendor_about_transaction(
        self, txn_id: str | int, **kwargs
    ) -> bool:
        """
        Notifies the merchant of a client's txn interest.
        Notifies via email, sms and websocket
        """

        from apps.notification.email.app_emails import EmailService
        from apps.auths.models import User
        from utils.wallet_utils.transactions import TransactionUtil
        from utils.notifications.notifications import NotificationUtil


        channel_layer = get_channel_layer()
        txn = TransactionUtil.get_transaction(**{"id": txn_id})
        if not txn:
            logger.error(f"Transaction with id {txn_id} not found.")
            return False
        txn_client: User = txn.client
        BusinessAsyncOperations.update_client_last_patronized(
            txn_client, txn
        )
        vendor: User | None = txn.vendor
        if not vendor:
            return False

        txn_info = {
                    "txn_ref": txn.txn_ref,
                    "client_id": txn.client.id,
                    "amount": txn.amount,
                    "client_current_location": txn.meta.get("client_current_location", {}),
                    "mode": txn.collection_mode,
                    "vendor_name": vendor.full_name,
                    "client_name": txn.client.full_name,
                    "client_phone_number": txn.client.phone_number,
                    "vendor_phone_number": vendor.phone_number
                }

        # capture notification in db
        NotificationUtil.record_notification(
            title="New Transaction Interest",
            body=(
                f"{txn.client.full_name} is interested in a transaction of amount "
                f"{txn.amount} {txn.currency}."
            ),
            extra_data=txn_info,
            entity=txn.business #entity here is the vendor business
        )
        notification_data = {
            "type": "send.notification",
            "message": {
                "message_type": "New Transaction Interest",
                "txn_info": txn_info
            }
        }

        # publish push notification
        async_to_sync(
        channel_layer.group_send
        )(
            vendor.user_queue, notification_data
        )
        email_data: EmailArgsDto = {
            "subject": "New Transaction Interest",
            "body": "new_txn_interest.html",
            "recipients": [vendor.email],
            "context": txn_info
        }

        # send email notification
        # TODO: update the email data context with a reverse geocoded address for the client current location
        # EmailService().send_email(
        #     **email_data, raw=False
        # )

        # send sms notification
        return

    @classmethod
    def update_client_last_patronized(
        cls, client: Type["User"], txn: Type["Transaction"]
    ):
        """updates the last time a client patronized a business"""
        from apps.core.models import BusinessClient
        from utils.core_utils.core_utils import CoreUtil

        user_as_business_client: BusinessClient  = CoreUtil.get_or_create_user_as_business_client(
            client=client, business=txn.business
        )
        tz = timezone.get_current_timezone()
        user_as_business_client.last_patronized = timezone.now().replace(tzinfo=tz)
        user_as_business_client.save()
        return user_as_business_client


    @shared_task(bind=True, name="notify-client-of-txn-status")
    def notify_client_of_txn_status(
        self: Task, txn_id: Union[str, int]
    ) -> bool:
        """
        notifies the client of the transaction status update via email and websocket
        """
        from utils.wallet_utils.transactions import TransactionUtil
        from utils.notifications.notifications import NotificationUtil
        from apps.notification.email.app_emails import EmailService
        from apps.wallet.constants import (
            DECLINED, IN_PROGRESS
        )

        txn = TransactionUtil.get_transaction(**{"id": txn_id})
        channel_layer = get_channel_layer()
        txn_info = {
                        "txn_ref": txn.txn_ref,
                        "status": txn.status,
                        "amount": txn.amount,
                        "vendor_name": (txn.vendor and txn.vendor.full_name) or "",
                        "client_name": txn.client.full_name,
                        "client_phone_number": txn.client.phone_number,
                        "vendor_phone_number": txn.vendor.phone_number if txn.vendor else "",
                        "client_current_location": txn.meta.get("client_current_location", {})
                    }

        # capture notification in db
        txn_status = txn.status.title()
        business = txn.business
        title = (
            f"Transaction { 'Approved!' if txn_status == 'In_Progress' else txn_status }"
            if txn_status in [ "In_Progress", "Declined" ]
            else "Transaction Status Update"
        )
        NotificationUtil.record_notification(
            title=title,
            body=(
                f"{business.name} has approved your transaction of amount "
                f"{txn.amount}{txn.currency}."
            ),
            extra_data=txn_info,
            entity=txn.client #entity here is the client
        )

        async_to_sync(
            channel_layer.group_send
        )(
                txn.client.user_queue,
                {
                    "type": "send.notification",
                    "message": {
                        "message_type": "Vendor Accepted Transaction Request",
                        "txn_info": txn_info
                    }
                }
            )

        email_data: EmailArgsDto = {
            "subject": "Transaction is being processed!",
            "body": "txn_status_update.html",
            "recipients": [txn.client.email],
            "context": txn_info
        }
        # EmailService().send_email(**email_data, raw=False)
