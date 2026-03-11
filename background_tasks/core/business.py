from celery import shared_task, Task

from typing import Type, Union, Optional
from django.utils import timezone

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from utils.helpers.logs import logger
from utils.helpers.exception import CustomException

from dtos.generics import EmailArgsDto

class BusinessAsyncOperations:

    @shared_task(bind=True, name="notify_vendor_about_transaction")
    def other_vendor_transaction_notif(
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
        from apps.wallet.constants import (
            DECLINED, INITIATED, CANCELLED
        )

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


        # schedule a job that fires after 1 minute or so to check vendor's responsiveness
        # and notifies client if necessary
        # schedule_time = txn.date_created + timezone.timedelta(minutes=2)
        # BusinessAsyncOperations.check_vendor_transaction_responsiveness.apply_async(
        #     eta=schedule_time,
        #     kwargs={"trxn_id": txn.id}
        # )
        # txn_info = BusinessAsyncOperations.get_txn_info_for_async_ops(txn)
        # email_data: EmailArgsDto = {
        #     "subject": "New Transaction Interest",
        #     "body": "new_txn_interest.html",
        #     "recipients": [vendor.email],
        #     "context": txn_info
        # }

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

        txn = TransactionUtil.get_transaction(**{"id": txn_id})
        txn_info = BusinessAsyncOperations.get_txn_info_for_async_ops(
            txn, for_vendor=False
        )

        email_data: EmailArgsDto = {
            "subject": "Transaction is being processed!",
            "body": "txn_status_update.html",
            "recipients": [txn.client.email],
            "context": txn_info
        }
        # EmailService().send_email(**email_data, raw=False)
        return True


    @classmethod
    def get_txn_info_for_async_ops(
        cls, txn, skip_error: bool = False, for_vendor: bool = True
    ) -> Optional[dict]:
        from apps.auths.models import User

        vendor: User | None = txn.vendor
        if not vendor and not skip_error:
            raise CustomException(
                f"transaction with id: {txn.id} has no vendor attached!"
            )

        txn_info = {
                    "txn_id": txn.id,
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

        if not for_vendor:
            txn_info = {
                        "txn_id": txn.id,
                        "txn_ref": txn.txn_ref,
                        "status": txn.status,
                        "amount": txn.amount,
                        "vendor_name": (txn.vendor and txn.vendor.full_name) or "",
                        "client_name": txn.client.full_name,
                        "client_phone_number": txn.client.phone_number,
                        "vendor_phone_number": txn.vendor.phone_number if txn.vendor else "",
                        "client_current_location": txn.meta.get("client_current_location", {})
                    }
        return txn_info


    @shared_task(
        bind=True, name="expire-trxn-after-delay"
    )
    def check_vendor_transaction_responsiveness(
        self, trxn_id: str | int
    ):
        """
        notifies the client that the vendor is not available
        and whether to allow system look for another vendor
        to fulfill the transaction or not.
        This job mostly runs after it has been pre-schuled for about 1 minute
        from when a client user initiates a transaction.
        So it checks if the vendor has not taken any action on the trxn yet,
        in the space of that one minute.
        """
        from utils.wallet_utils.transactions import TransactionUtil
        from apps.wallet.models import INITIATED
        from apps.auths.models import User

        trxn = TransactionUtil.get_transaction(**{"id": trxn_id})
        if not trxn:
            logger.error(f"no transaction with id {trxn_id}")
            return
        status = trxn.status
        client: User = trxn.client
        channel_layer = get_channel_layer()
        trxn_info = BusinessAsyncOperations.get_txn_info_for_async_ops(trxn, for_vendor=False)
        client_message = {
            "type": "send.notification",
            "message": {
                "message_type": "Vendor Response Delayed",
                "txn_info": trxn_info
            }
        }

        if status == INITIATED:
            #prompt client to ether wait or let system recommend.
            user_channel = client.user_queue
            async_to_sync(channel_layer.group_send)(
                user_channel,
                message=client_message
            )


    @shared_task(
        bind=True, name="notify-other-vendors-of-transaction-op"
    )
    def notify_vendors_about_trxn_opportunity(
        self, trxn_id: str | int,
    ):
        from utils.wallet_utils.transactions import TransactionUtil
        from utils.core_utils.business_utils import BusinessUtil

        trxn = TransactionUtil.get_transaction(id=trxn_id)

        trxn_meta: dict = trxn.meta
        trxn_initiation_point = trxn_meta.get("client_current_location") or {}
        latitude: float | None = trxn_initiation_point.get("latitude")
        longitude: float | None = trxn_initiation_point.get("longitude")

        if not (latitude and longitude):
            # fetch client current location from the db
            pass

        nearby_vendors = BusinessUtil.get_nearby_businesses(
            current_lat=latitude, current_long=longitude
        ).exclude(id=trxn.business)
        # TODO: find a vendor with the transactiona amount and notify accordingly
        channel_layer = get_channel_layer()
