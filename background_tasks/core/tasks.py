from celery import shared_task, Task

from typing import Type, Union, Optional, List, Dict, Any
from django.utils import timezone
from django.conf import settings
from django.db import transaction, connection

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from utils.helpers.logs import logger
from utils.helpers.exception import CustomException
from utils.auth_utils.auths import AuthUtils
from utils.notifications.notifications import NotificationUtil

from dtos.generics import EmailArgsDto

from apps.wallet.models import Transaction
from apps.core.models import Business
from apps.auths.models import User

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
        cls, client: User, txn: Transaction
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

        txn = TransactionUtil.get_transaction(id=txn_id)
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
                    "vendor_name": txn.business and txn.business.name or None,
                    "client_name": txn.client.full_name,
                    "client_phone_number": txn.client.phone_number,
                    "vendor_phone_number": vendor and vendor.phone_number or None
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

        trxn: Transaction = TransactionUtil.get_transaction(id=trxn_id)
        if not trxn:
            logger.error(f"no transaction with id {trxn_id}")
            return

        client: User = trxn.client
        trxn_meta: dict = trxn.meta or {}
        is_v2v = trxn_meta.get("is_v2v")
        vendors_have_proposed = bool(trxn_meta.get("proposed_amounts"))

        if is_v2v and vendors_have_proposed:
            return

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
        latitude: float = trxn_initiation_point.get("latitude") or 0.0
        longitude: float  = trxn_initiation_point.get("longitude") or 0.0
        client: User = trxn.client

        if not (latitude and longitude):
            cur_location = BusinessUtil.fetch_existing_user_location(
                client, location_type="Client"
            )
            latitude = cur_location and cur_location.location.y
            longitude = cur_location and cur_location.location.x

        custom_msg_type = "Transaction Opportunity!"
        custom_msg_body =  (
           "A Client who is less than {}{} away from you needs an amount of {}\n"
           "Would you be able to fulfil it?"
        )
        BusinessAsyncOperations._fetch_vendors_and_publish_trxn_op(
            user=client, trxn=trxn, latitude=latitude, longitude=longitude,
            exclude_business_id=trxn.business.id if trxn.business else None,
            custom_msg_type=custom_msg_type,
            custom_msg_body=custom_msg_body
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


    @shared_task(
        bind=True, name="post-opportunity-acceptance-task"
    )
    def run_post_opportunity_acceptance_task(
        self, trxn_id: str, is_v2v: bool = False
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
        custom_msg_type = None
        custom_title = None
        custom_body = None
        if is_v2v:
            trxn_meta = trxn.meta or {}
            vendors_who_proposed = trxn_meta.get("proposed_amounts", [])
            custom_msg_type = custom_title = "Proposed Amount"
            custom_body = (
                f"{'Some' if len(vendors_who_proposed) > 1 else 'A'} vendor{'s' if len(vendors_who_proposed) > 1 else ''} "
                f"proposed {'their' if len(vendors_who_proposed) > 1 else 'an'} amount for this request.\n"
            )
            # decide later whether to schedule a task to notify each proposing vendor 
            # about expiry if the initiating vendor does not accept their proposal within
            # within the expiry time earlier set when proposing.
        NotificationUtil.send_socket_notification(
                txn=trxn, for_vendor_notif=False,
                custom_msg_type=custom_msg_type,
                custom_title=custom_title,
                custom_body=custom_body,
                skip_record=is_v2v
        )
        if not is_v2v:
            all_opportunities = TransactionOpportunity.objects.filter(
                transaction=trxn
            )
            all_opportunities.update(is_active=False)


    @shared_task(
        bind=True, name="initiate-vendor-to-vendor-transaction"
    )
    def run_initiate_vendor_to_vendor_transaction_task(
        self, requesting_vendor_id: str | int, data: dict,
        trxn_id: str | int
    ):
        """
        initiates a vendor to vendor transaction asynchronously
        """
        from utils.core_utils.business_utils import BusinessUtil
        from utils.wallet_utils.transactions import TransactionUtil
        from apps.core.models import Business
        from apps.auths.models import User

        trxn = TransactionUtil.get_transaction(id=trxn_id)
        requesting_vendor: User | None = AuthUtils.fetch_user({"id": requesting_vendor_id, "meta__user_type": "VENDOR"}) or trxn.client
        if not requesting_vendor:
            logger.error(f"requesting vendor with id {requesting_vendor_id} not found!")
            return
        requesting_vendor_business: Business | None = BusinessUtil.get_business(
            {
                "owner_id": requesting_vendor_id,
                "id": data.get("business_id"),
                "business_type": data.get("txn_type")
            }
        )
        if not requesting_vendor_business:
            logger.error(f"business with id {data.get('business_id')} not found for vendor {requesting_vendor_id}!")
            return

        vendor_curr_location = {
            "longitude": requesting_vendor_business.geo_location.x,
            "latitude": requesting_vendor_business.geo_location.y
        }
        if (
          not vendor_curr_location or
          vendor_curr_location.get("longitude") is None or
          vendor_curr_location.get("latitude") is None
        ):
            db_loc = BusinessUtil.fetch_existing_user_location(
                requesting_vendor, location_type="Vendor"
            )
            vendor_curr_location = {
                "longitude": trxn.meta.get("client_current_location", {}).get("longitude"),
                "latitude": trxn.meta.get("client_current_location", {}).get("latitude")
            } or {
                "longitude": db_loc.location.x,
                "latitude": db_loc.location.y
            }
        BusinessAsyncOperations._fetch_vendors_and_publish_trxn_op(
            user=requesting_vendor, trxn=trxn,
            latitude=vendor_curr_location.get("latitude", 0.0),
            longitude=vendor_curr_location.get("longitude", 0.0),
            exclude_business_id=data.get("business_id"),
            custom_msg_type="Liquidity Request!",
            custom_msg_body=(
                "Another vendor who is less than {}{} away from you needs an amount of {}\n"
                "Would you be able to fulfil it?"
            )
        )
        # notifies the requesting vendor later if no other vendor takes action about the trxn in next 30 seconds
        BusinessAsyncOperations.check_vendor_transaction_responsiveness.apply_async(
            eta=(
                trxn.last_updated + timezone.timedelta(seconds=30)
            ),
            kwargs={"trxn_id": trxn_id, "custom_message_type": "No Available Vendors"}
        )
        return


    @classmethod
    def _fetch_vendors_and_publish_trxn_op(
        cls, user, trxn: Transaction,
        latitude: float, longitude: float,
        exclude_business_id: Optional[str] = None,
        custom_msg_type: str = "Transaction Opportunity!",
        custom_msg_body: Optional[str] = None
    ) -> bool:
        from utils.core_utils.business_utils import BusinessUtil
        from apps.auths.models import User

        nearby_vendors = list(BusinessUtil.get_nearby_businesses(
            user,
            current_lat=latitude,
            current_long=longitude,
            vendor_type=trxn.txn_type or "local"
        ).exclude(id=exclude_business_id).filter(
            available_liquidity__gte=trxn.amount
        ))
        trxn_info = BusinessAsyncOperations.get_txn_info_for_async_ops(trxn, skip_error=True)

        if "vendor_name" in trxn_info and "vendor_phone_number" in trxn_info:
            del trxn_info["vendor_name"]
            del trxn_info["vendor_phone_number"]


        trxn_opportunity_msg = {
            "message_type": custom_msg_type,
            "txn_info": trxn_info
        }
        title = custom_msg_type
        body = (
           "Another vendor who is less than {}{} away from you needs an amount of {}\n"
           "Would you be able to fulfil it?"
        )
        logger.debug(f"title for trxn opportunity in v2v: {title}\n body for trxn opportunity in v2v: {body}\n nearby vendors found: {nearby_vendors}")
        if custom_msg_body:
            body = custom_msg_body
        if nearby_vendors and len(nearby_vendors) > 0:
            owner_businesses = cls._get_owners_and_businesses(nearby_vendors)

            for owner, businesses in owner_businesses.items():
                trxn_opportunity_msg = cls._update_trxn_opportunity_msg(
                    owner, trxn_opportunity_msg, businesses
                )

                cls._register_opportunity_for_business(
                    trxn, businesses,
                    title=title,
                    body=body
                )

                cls._publish_trxn_opportunity_to_vendors(
                    owner, trxn_opportunity_msg
                )
            return True
        return False


    @classmethod
    def _get_owners_and_businesses(
        cls, businesses: List[Business]
    ) -> dict:
        owners_and_businesses = {}
        for business in businesses:
            owner = business.owner
            if owner not in owners_and_businesses:
                owners_and_businesses[owner] = []
            owners_and_businesses[owner].append(business)
        return owners_and_businesses


    @classmethod
    def _register_opportunity_for_business(
        cls, trxn: Transaction, businesses: List[Business],
        title: str = "Transaction Opportunity!",
        body: str = (
           "A Client who is less than {}{} away from you needs "
           "an amount of {}\n"
           "Would you be able to fulfil it?"
        )
    ):
        from utils.core_utils.business_utils import BusinessUtil

        for business in businesses:
            formatted_body = body.format(
            business.distance.km,
            "m" if business.distance.km < 1 else "km",
            trxn.amount
        )
            BusinessUtil.register_opportunity_for_business(
                trxn, business
            )
            NotificationUtil.record_notification(
                title=title,
                body=formatted_body,
                entity=business
            )


    @classmethod
    def _publish_trxn_opportunity_to_vendors(
        cls, owner: User,
        trxn_opportunity_msg: dict
    ) -> bool:
        channel_layer = get_channel_layer()
        logger.debug(f"Publishing transaction opportunity to vendors for owner: {owner.id}\n message: {trxn_opportunity_msg}")
        async_to_sync(
            channel_layer.group_send
        )(
            owner.user_queue,
            {
                "type": "send.notification",
                "message": trxn_opportunity_msg
            }
        )
        return True


    @classmethod
    def _update_trxn_opportunity_msg(
        cls, owner: User, trxn_opportunity_msg: dict,
        businesses: list[Business]
    ) -> dict:
        trxn_opportunity_msg["txn_info"].update({
            "vendor_name": owner.full_name,
            "businesses": [
                {"id": b.id, "name": b.name}
                for b in businesses
            ]
        })
        return trxn_opportunity_msg


    @shared_task(
        bind=True, name="notify-proposing-vendor-of-acceptance"
    )
    def notify_proposing_vendor_of_acceptance(
        self, trxn_id: IndentationError
    ) -> None:
        """
        informs the proposing vendor whose proposal was accepted by the initiating vendor
        about about the acceptance of their proposed amount
        """
        from utils.wallet_utils.transactions import TransactionUtil

        with transaction.atomic():
            trxn = TransactionUtil.get_transaction(id=trxn_id)
            trxn.refresh_from_db()
            if not trxn:
                logger.error(f"transaction with id {trxn_id} not found for notifying proposing vendor of acceptance!")
                return

            if not trxn.business or not trxn.vendor or trxn.vendor.id == trxn.client.id:
                logger.error(f"initiating vendor hasn't accepted any vendor proposal for trxn with id {trxn.id} yet!")
                return

            vendor_user = trxn.vendor
            channel_layer = get_channel_layer()
            user_queue = vendor_user.user_queue
            trxn_info = BusinessAsyncOperations.get_txn_info_for_async_ops(trxn, for_vendor=False)
            acceptance_message = {
                "type": "send.notification",
                "message": {
                    "message_type": "Proposed Amount Accepted!",
                    "txn_info": trxn_info
                }
            }
            async_to_sync(channel_layer.group_send)(
                user_queue, acceptance_message
            )
