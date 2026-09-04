from typing import Dict, Any, List

from asgiref.sync import async_to_sync
from celery import shared_task

from channels.layers import get_channel_layer

from django.conf import settings
from django.db.models import Model
from django.db.models import QuerySet, Q, Case, When, IntegerField, Value
from django.contrib.contenttypes.models import ContentType

from typing import Union, Any, Optional

from apps.notification.models import Notification
from apps.notification.schema.types.enums import NotificationEnum
from apps.auths.models import User
from apps.core.models import Business
from apps.wallet.models import Transaction
from apps.wallet.constants import (
    INITIATED, CANCELLED, BANK_TRANSFER
)
from apps.payment.services import PaymentService

from utils.helpers.logs import logger, log_message
from utils.helpers.exception import CustomException
from utils.helpers.general import get_two_formatted_datetime
from utils.wallet_utils.transactions import TransactionUtil


class NotificationUtil:

    @classmethod
    def add_user_to_needed_groups(
        cls, user, channel_name: str, *group_names
    ) -> Union[None, Any]:
        """Add the user to necessary groups."""
        channel_layer = get_channel_layer()

        # add user to the general notification group
        general_notification_group_name = settings.GENERAL_NOTIFICATION_GROUP_NAME
        async_to_sync(channel_layer.group_add)(
            general_notification_group_name,
            channel_name
        )
        # add user to its personal queue group
        async_to_sync(channel_layer.group_add)(
            user.user_queue,
            channel_name
        )
        # add user to other groups specified
        for group_name in group_names:
            async_to_sync(channel_layer.group_add)(
                group_name,
                channel_name
            )
        return user


    @classmethod
    def remove_users_from_needed_groups(
        cls, user, channel_name: str, *group_names
    ) -> Union[None, Any]:
        """
        cleanly removes users from the groups they were added to when they disconnect
        """
        channel_layer = get_channel_layer()

        general_notification_group = settings.GENERAL_NOTIFICATION_GROUP_NAME

        # general group
        async_to_sync(
            channel_layer.group_discard)(
            general_notification_group,
            channel_name
        )

        # personal group
        async_to_sync(
            channel_layer.group_discard)(
            user.user_queue,
            channel_name
        )

        # other groups specified
        for group in group_names:
            async_to_sync(
                channel_layer.group_discard)(
                group,
                channel_name
            )


    @classmethod
    def record_notification(
        cls, title: str, body: str, entity: Optional[Model] = None,
        extra_data: Optional[dict] = None
    ) -> Notification:
        """
        Persists notification data to the database.
        """
        notif = Notification(
            title=title,
            message=body,
            meta=extra_data or {}
        )
        if entity:
            entity_content_type = ContentType.objects.get_for_model(entity)
            notif.content_type = entity_content_type
            notif.object_id = entity.id
            notif.content_object = entity
        notif.save()


    @shared_task(bind=True, name="create_notification_task")
    def create_notification_async(
        self, **kwargs
    ) -> None:
        if not (
            "title" in kwargs and "body" in kwargs
        ):
            raise ValueError("Title and body are required to create a notification.")

        notif_data = {
            "title": kwargs.pop("title"),
            "body": kwargs.pop("body"),
            "extra_data": kwargs
        }
        if "user_id" in kwargs and kwargs.get("user_id") is not None:
            user = User.objects.filter(id=kwargs["user_id"]).first()
            if not user:
                raise ValueError(f"User with id {kwargs['user_id']} not found.")
            notif_data["entity"] = user
        if "business_id" in kwargs and kwargs.get("business_id") is not None:
            business = Business.objects.filter(id=kwargs["business_id"]).first()
            if not business:
                raise ValueError(f"Business with id {kwargs['business_id']} not found.")
            notif_data["entity"] = business
        NotificationUtil.record_notification(**notif_data)
        return


    @classmethod
    def fetch_notifications(
        cls, user_id: Union[str, int, None] = None,
        business_id: Union[str, int, None] = None,
        search: Optional[Union[str, Q]] = None,
        **kwargs
    ) -> QuerySet:
        """
        fetches notifications for a user or business
        """
        content_type = None
        user = None
        business = None
        search = search or Q()
        notifications = Notification.objects.filter(search).order_by("-date_created")
        notifications = notifications.annotate(
            is_read=Case(
                When(status=NotificationEnum.READ.value, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        ).order_by("is_read", "-date_created")

        if user_id:
            user = User.objects.filter(id=user_id).first()
            content_type = ContentType.objects.get_for_model(user)
        if business_id:
            business = Business.objects.filter(id=business_id).first()
            content_type = ContentType.objects.get_for_model(business)
        if user:
            notifications = notifications.filter(
                content_type=content_type,
                object_id=user.id
            )
        if business:
            notifications = notifications.filter(
                content_type=content_type,
                object_id=business.id
            )
        # all other filter params
        notifications = notifications.filter(**kwargs)
        return notifications


    @classmethod
    def send_socket_notification(
        cls, txn: Transaction, for_vendor_notif = True,
        skip_record: bool = False,
        custom_title: str | None = None, custom_body: str | None = None,
        custom_msg_type: str | None = None
    ) -> bool:
        from background_tasks.core.tasks import BusinessAsyncOperations

        channel_layer = get_channel_layer()
        try:
            # capture notification in db
            if for_vendor_notif and txn.status not in [
                INITIATED, CANCELLED
            ]:
                return False

            is_v2v = (txn.meta or {}).get("is_v2v", False)
            is_fx = txn.txn_type.upper() != "LOCAL"
            txn_info = BusinessAsyncOperations.get_txn_info_for_async_ops(
                txn, for_vendor=for_vendor_notif, skip_error=(is_fx or is_v2v)
            )
            txn_status = txn.status.title()
            txn_status = "Approved" if txn_status == "In_Progress" else txn_status
            vendor: User = txn.vendor
            client: User = txn.client
            mode_of_transfer = txn.transfer_mode or BANK_TRANSFER
            business: Business = txn.business
            [
                business_id, user_id, title, body
            ] = cls._get_notification_title_and_body(
                txn, client, for_vendor_notif, business,
                custom_title=custom_title, custom_body=custom_body
            )
            if (txn_status == "Approved" or is_v2v or is_fx) and mode_of_transfer == BANK_TRANSFER:
                #generate virtual account for the client to pay into
                try:
                    txn_info = TransactionUtil.update_trxn_info_with_account_details(txn, txn_info, client)
                except Exception as e:
                    logger.exception(f"exception occured when generating virtual account: {e}")
                    cls._populate_trxn_info_with_default_account_details(txn_info)

            msg_type = custom_msg_type or (
                        "New Transaction Interest" if txn_status == "Initiated"
                        and for_vendor_notif
                        else f"Transaction {txn_status}!"
                    )
            if is_v2v:
                txn_info.update({
                    "proposed_amounts": txn.meta.get("proposed_amounts", []),
                })
            if is_fx:
                txn_info.update({
                    "proposed_rates": txn.meta.get("proposed_rates", []),
                    "currency_market_rate": txn.meta.get("currency_market_rate") or 0.0
                })
            if not skip_record:
                cls.create_notification_async.delay(
                    title=title,
                    body=body,
                    user_id=user_id,
                    business_id=business_id,
                    txn_info=txn_info
                )
            socket_notification_data = {
                "type": "send.notification",
                "message": {
                    "message_type": msg_type,
                    "txn_info": txn_info
                }
            }
            # publish push notification
            channel = (
                vendor.user_queue if for_vendor_notif
                else client.user_queue
            ) or ""
            async_to_sync(
                channel_layer.group_send
            )(channel, socket_notification_data)
            cls._optionally_tell_vendor_to_wait_on_client(vendor, txn, txn_info)
        except Exception as e:
            logger.exception(f"exception when publishing socket notification>>>> {e}")
            return False
        return True


    @classmethod
    def update_notification(
        cls, user: User, data: dict
    ) -> Optional[Notification]:
        """updates notification status"""
        notification_id = data.get("notification_id")
        status: NotificationEnum = data.get("status")
        notif_to_update: Optional[Notification] = cls.fetch_notifications(
            search=Q(id=notification_id)
        ).first()
        if not notif_to_update:
            raise CustomException(
                f"invalid notification id provided: {notification_id}"
            )
        acceptable_statues = [
            NotificationEnum.READ.value,
            NotificationEnum.UNREAD.value
        ]
        if status.value not in acceptable_statues:
            raise CustomException(
                f"invalid status value provided: {status}"
            )
        notif_to_update.status = status.value
        notif_to_update.save()
        return notif_to_update


    @classmethod
    def _get_notification_title_and_body(
        cls, txn: Transaction, client: User, for_vendor_notif: bool = True,
        business: Business | None = None, custom_title: str | None = None,
        custom_body: str | None = None
    ) -> list[str | int | None]:
        """
        formarts notification information for db recording
        """
        txn_status = txn.status.title()
        txn_status = "Approved" if txn_status == "In_Progress" else txn_status
        business = business or txn.business
        title = (
                "New Transaction Interest" if txn_status == "Initiated"
                else f" Transaction {txn_status}"
            )
        body = (
                f"{client.full_name} has {txn_status} a transaction of amount "
                f"{txn.amount} {txn.currency}."
            )
        user_id = None
        business_id = None

        if for_vendor_notif and business:
            business_id = business.id
        else:
            user_id = client.id
            title = (
                f"Transaction { txn_status }!"
                if txn_status in [ "Approved", "Declined" ]
                else "Transaction Status Update"
            )
            body = (
                f"{business and business.name or 'A business'} has {txn_status} your transaction of amount "
                f"{txn.amount}{txn.currency}."
            )
        if custom_title:
            title = custom_title
        if custom_body:
            body = custom_body
        return [
            business_id, user_id, title, body
        ]


    @classmethod
    def _optionally_tell_vendor_to_wait_on_client(
        cls, vendor: User, trxn: Transaction, trxn_info: dict
    ):
        """
        optionally checks to see that the transction
        has been approved by the vendor.
        If approved, it notifies the vendor to wait
        while the client transfers the amount to the escrow
        account
        """
        trxn_status = trxn.status.title()
        trxn_status = "Approved" if trxn.status == "In_Progress" else trxn_status
        if trxn_status == "Approved" and trxn.transfer_mode == BANK_TRANSFER:
            channel_layer = get_channel_layer()
            group = vendor.user_queue or ""
            msg_format = {
                "message_type": "Pending Client Transfer",
                "txn_info": trxn_info
            }
            async_to_sync(
                channel_layer.group_send
            )(
                group,
                {
                    "type": "send.notification",
                    "message": msg_format
                }
            )


    @classmethod
    def _populate_trxn_info_with_default_account_details(
        cls, trxn_info: dict
    ) -> dict:
        trxn_info = TransactionUtil.populate_trxn_info_with_default_account_detail(trxn_info)
        return trxn_info


    @classmethod
    def broadcast_fx_trxn_request_notification(
        cls, trxn: Transaction
    ) -> bool:
        """
        broadcasts foreign transaction request to available and nearby FX vendors
        """
        from background_tasks.core.tasks import BusinessAsyncOperations
        from utils.core_utils.business_utils import BusinessUtil


        client: User = trxn.client
        client_db_loc = BusinessUtil.fetch_existing_user_location(client, location_type="Clietnt")
        client_current_coordinates = (
            trxn.meta.get("client_current_coordinates") or
            (client_db_loc and {
                "latitude": client_db_loc.location.y,
                "longitude": client_db_loc.location.x
            })
        )
        if not client_current_coordinates:
            logger.error(
                "client's current coordinates not found in transaction meta. "
                "Unable to broadcast FX transaction request."
            )
            # TODO: send an error socket message here too.
            return False

        trxn_info: Dict[str, Any] = BusinessAsyncOperations.get_txn_info_for_async_ops(
            trxn, skip_error=True
        )
        trxn_info["currency_market_rate"] = trxn.meta.get("currency_market_rate")
        fx_vendor_businesses = BusinessUtil.get_nearby_businesses(
            client,
            current_lat=client_current_coordinates.get("latitude"),
            current_long=client_current_coordinates.get("longitude"),
            vendor_type=trxn.txn_type.strip().upper(),
        )
        fx_vendor_businesses = list(BusinessUtil.get_vendors_specifically_for_given_fx_currency(
            fx_vendor_businesses, trxn
        ))
        logger.debug(f"nearby FX vendors found for the given currency: {fx_vendor_businesses}")
        if not fx_vendor_businesses:
            log_message(
                "No nearby FX vendors found for the given currency to broadcast transaction request.",
                level="warning",
                exc_info=True
            )
            user_queue = client.user_queue or ""
            trxn_info.update({
                "message": "No nearby FX vendors found to process your transaction request."
            })
            cls.send_msg(
                user_queue, {
                    "message_type": "No Nearby FX Vendors",
                    "txn_info": trxn_info
                }
            )
            return False
        fx_trxn_msg_fmt = {
            "message_type": "New FX Transaction Interest",
            "txn_info": trxn_info
        }
        currency_pair = trxn.meta.get("currency_pair", {})
        source_curr = currency_pair.get("source_currency_code")
        destination_curr = currency_pair.get("destination_currency_code")
        vendors_and_their_businesses: Dict[User, List[Business]] = BusinessAsyncOperations\
            .get_owners_and_businesses(fx_vendor_businesses)
        for vendor, businesses in vendors_and_their_businesses.items():
            fx_trxn_msg_fmt = BusinessAsyncOperations.update_trxn_opportunity_msg(
                vendor, fx_trxn_msg_fmt, businesses
            )
            user_queue = vendor.user_queue or ""
            socket_msg = fx_trxn_msg_fmt
            cls.send_msg(user_queue, socket_msg)
            # register FX notification for FX vendor
            # NOTE: This can be pushed to a separate worker for speed.
            for business in businesses:
                cls.record_notification(
                    title=fx_trxn_msg_fmt["message_type"],
                    body=(
                        f"{client.full_name} would like to exchange their "
                        f"{source_curr} for some "
                        f"{trxn.amount}{destination_curr} from you; "
                        "can you fulfil this request?"
                    ),
                    entity=business
                )
        return True


    @classmethod
    def send_msg(
        cls, queue_name: str, message: str | dict | Any,
        handler_type: str = "send.notification"
    ) -> bool:
        """
        custom util method to send message to a specific channel name or group.
        it saves from having to get the channel layer and call async_to_sync() every time
        """
        try:
            channel_layer = get_channel_layer()
            formatted_msg = {
                "type": handler_type,
                "message": message
            }
            async_to_sync(
                channel_layer.group_send
            )(
                queue_name,
                formatted_msg
            )
        except Exception as e:
            logger.exception(f"exception when sending message to {queue_name} >>>> {e}")
            return False
        return True
