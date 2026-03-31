from celery import shared_task, Task

from typing import Type, Union, Optional, List, Dict, Any
from django.utils import timezone
from django.conf import settings
from django.db import transaction, connection

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from utils.helpers.logs import logger
from utils.helpers.exception import CustomException

from dtos.generics import EmailArgsDto

class BusinessAsyncOperations:

    @shared_task(bind=True, name="notify-vendor-about-transaction")
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
        from apps.wallet.constants import (
            DECLINED, INITIATED, CANCELLED
        )

        txn = TransactionUtil.get_transaction(**{"id": txn_id})
        if not txn:
            logger.error(f"Transaction with id {txn_id} not found.")
            return False

        # send websocket notification to vendor before other async operations
        NotificationUtil.send_socket_notification(txn)
        txn_client: User | None = txn.client
        BusinessAsyncOperations.update_client_last_patronized(
            txn_client, txn
        )
        vendor: User | None = txn.vendor
        if not vendor:
            return False
        # lock the amount to withdraw away from the total available liquidity until
        BusinessAsyncOperations.lock_transaction_amount_from_vendor_liquidity(
            txn.business, txn
        )
        # txn_info = BusinessAsyncOperations.get_txn_info_for_async_ops(txn)
        # email_data: dict = {
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
        return True


    @classmethod
    def lock_transaction_amount_from_vendor_liquidity(
        cls, business, trxn
    ):
        """
        locks trxn amount away from total liquidity
        """
        business_current_total_liquidity = business.available_liquidity or 0.0
        if not business_current_total_liquidity or business_current_total_liquidity < 1:
            logger.warning(f"business is out of liquidity for the day!")
            return trxn
        business_current_total_liquidity -= float(trxn.amount)
        business.available_liquidity = business_current_total_liquidity
        business.save()
        return trxn

    @classmethod
    def return_transaction_amount_to_vendor_available_liquidity(
        cls, business, trxn
    ):
        """
        returns a transaction amount back to a vendor's available liquidity
        happens mostly whe a transaction is cancelled or rejected.
        """
        amount = trxn.amount or 0.0
        business.available_liquidity += amount
        business.save()
        trxn.meta["liquidity_returned"] = True
        trxn.save(update_fields=["meta"])
        return trxn

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


    @shared_task(bind=True, name="other-client-transaction-notif")
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
        if not txn:
            raise CustomException(
                "could not find a transaction with id: %s"%txn_id
            )
        # txn_info = BusinessAsyncOperations.get_txn_info_for_async_ops(
        #     txn, for_vendor=False
        # )

        NotificationUtil.send_socket_notification(txn, for_vendor_notif=False)
        # email_data: dict = {
        #     "subject": "Transaction is being processed!",
        #     "body": "txn_status_update.html",
        #     "recipients": [txn.client.email],
        #     "context": txn_info
        # }
        # EmailService().send_email(**email_data, raw=False)
        return True


    @classmethod
    def get_txn_info_for_async_ops(
        cls, txn, skip_error: bool = False, for_vendor: bool = True
    ) -> Dict[str, int | Any]:
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
                    "transfer_mode": txn.transfer_mode,
                    "vendor_name": txn.business.name,
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
                        "transfer_mode": txn.transfer_mode,
                        "vendor_name": (txn.business and txn.business.name) or "",
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
        self, trxn_id: str | int, custom_message_type: str = "Vendor Response Delayed"
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
        from apps.wallet.models import INITIATED, CANCELLED, Transaction
        from apps.auths.models import User
        # close connection to remove staleness
        connection.close()

        trxn = TransactionUtil.get_transaction(id=trxn_id)
        if not trxn:
            logger.error(f"no transaction with id {trxn_id}")
            return

        client: User = trxn.client
        channel_layer = get_channel_layer()
        trxn_info = BusinessAsyncOperations.get_txn_info_for_async_ops(trxn, for_vendor=False)
        client_message = {
            "type": "send.notification",
            "message": {
                "message_type": custom_message_type,
                "txn_info": trxn_info
            }
        }

        if custom_message_type == "No Available Vendors":
            with transaction.atomic():
                locked_trxn = Transaction.objects.select_for_update().filter(
                    id=trxn_id, status=INITIATED
                ).first()
                if not locked_trxn:
                    # Vendor already accepted — status is no longer INITIATED; send nothing
                    return
                locked_trxn.status = CANCELLED
                locked_trxn.save()
            async_to_sync(channel_layer.group_send)(client.user_queue, message=client_message)
            return

        if custom_message_type == "Vendor Response Delayed":
            trxn.refresh_from_db()
            if trxn.status == INITIATED:
                async_to_sync(channel_layer.group_send)(client.user_queue, message=client_message)


    @shared_task(
        bind=True, name="notify-other-vendors-of-transaction-op"
    )
    def notify_vendors_about_trxn_opportunity(
        self, trxn_id: str | int,
    ):
        from utils.wallet_utils.transactions import TransactionUtil
        from utils.core_utils.business_utils import BusinessUtil
        from utils.notifications.notifications import NotificationUtil
        from apps.auths.models import User

        trxn = TransactionUtil.get_transaction(id=trxn_id)
        if not trxn:
            logger.error(f"can't find trxn with id: {trxn_id} for opportunity broadcast!")
            return

        trxn_meta: dict = trxn.meta
        trxn_initiation_point = trxn_meta.get("client_current_location") or {}
        latitude: float | None = trxn_initiation_point.get("latitude")
        longitude: float | None = trxn_initiation_point.get("longitude")
        client: User = trxn.client
        trxn_amount = trxn.amount

        if not (latitude and longitude):
            cur_location = BusinessUtil.fetch_existing_user_location(
                client, location_type="Client"
            )
            latitude = cur_location and cur_location.location.y
            longitude = cur_location and cur_location.location.x

        nearby_vendors = BusinessUtil.get_nearby_businesses(
            current_lat=latitude, current_long=longitude
        ).exclude(id=trxn.business.id).filter(
            available_liquidity__gte=trxn_amount
        )
        trxn_info = BusinessAsyncOperations.get_txn_info_for_async_ops(trxn)

        if "vendor_name" in trxn_info and "vendor_phone_number" in trxn_info:
            del trxn_info["vendor_name"]
            del trxn_info["vendor_phone_number"]

        trxn_opportunity_msg = {
            "message_type": "Transaction Opportunity!",
            "txn_info": trxn_info
        }
        title = "Transaction Opportunity!"
        body = (
           "A client who is less than {} {} away from you needs an amount of {}\n"
           "Would you be able to fulfil it?"
        )
        if nearby_vendors and len(nearby_vendors) > 0:
            # Group businesses by owner
            owner_businesses: dict[User, list] = {}
            for business in nearby_vendors:
                owner: User = business.owner
                if owner not in owner_businesses:
                    owner_businesses[owner] = []
                owner_businesses[owner].append(business)

            for owner, businesses in owner_businesses.items():
                trxn_opportunity_msg["txn_info"].update({
                    "vendor_name": owner.full_name,
                    "businesses": [
                        {"id": b.id, "name": b.name}
                        for b in businesses
                    ]
                })

                for business in businesses:
                    formatted_body = body.format(
                    business.distance.km,
                    "m" if business.distance.km < 1 else "km",
                    trxn_amount
                )
                    BusinessUtil.register_opportunity_for_business(
                        trxn, business
                    )
                    NotificationUtil.record_notification(
                        title=title,
                        body=formatted_body,
                        entity=business
                    )
                channel_layer = get_channel_layer()
                async_to_sync(
                    channel_layer.group_send
                )(
                    owner.user_queue,
                    {
                        "type": "send.notification",
                        "message": trxn_opportunity_msg
                    }
                )
        trxn.meta["re_routed"] = True
        trxn.save()
        # notifies client later if no vendor takes action about the trxn in next 30 seconds
        BusinessAsyncOperations.check_vendor_transaction_responsiveness.apply_async(
            eta=(
                trxn.last_updated + timezone.timedelta(seconds=30)
            ),
            kwargs={"trxn_id": trxn_id, "custom_message_type": "No Available Vendors"}
        )


    @classmethod
    def _get_values_from_keys(
        cls, data: list[dict], key_to_check: str = "business_id"
    ) -> list:
        return [item.get(key_to_check) for item in data if key_to_check in item]


    @shared_task(
        bind=True, name="post-opportunity-acceptance-task"
    )
    def run_post_opportunity_acceptance_task(
        self, trxn_id: str
    ):
        """
        all things to be done after a vendor accepts a transaction opportunity
        """
        from utils.wallet_utils.transactions import TransactionUtil
        from utils.core_utils.business_utils import BusinessUtil
        from utils.notifications.notifications import NotificationUtil
        from apps.wallet.models import TransactionOpportunity

        trxn = TransactionUtil.get_transaction(id=trxn_id)

        # notify client of transaction acceptance
        NotificationUtil.send_socket_notification(
                txn=trxn, for_vendor_notif=False
        )
        all_opportunities = TransactionOpportunity.objects.filter(
            transaction=trxn
        )
        all_opportunities.update(is_active=False)
