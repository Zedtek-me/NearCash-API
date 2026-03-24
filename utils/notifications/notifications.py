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

from utils.helpers.logs import logger
from utils.helpers.exception import CustomException
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
        skip_record: bool = False
    ) -> bool:
        from background_tasks.core.business import BusinessAsyncOperations

        channel_layer = get_channel_layer()
        try:
            # capture notification in db
            if for_vendor_notif and txn.status not in [
                INITIATED, CANCELLED
            ]:
                return False

            txn_info = BusinessAsyncOperations.get_txn_info_for_async_ops(
                txn, for_vendor=for_vendor_notif
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
                txn, client, for_vendor_notif, business
            )
            if txn_status == "Approved" and mode_of_transfer == BANK_TRANSFER:
                #generate virtual account for the client to pay into
                txn_info = TransactionUtil.update_trxn_info_with_account_details(txn, txn_info, client)
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
                    "message_type": (
                        "New Transaction Interest" if txn_status == "Initiated" and for_vendor_notif
                        else f"Transaction {txn_status}!"
                    ),
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
        business: Business | None = None
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

        if for_vendor_notif:
            business_id = business.id
        else:
            user_id = client.id
            title = (
                f"Transaction { txn_status }!"
                if txn_status in [ "Approved", "Declined" ]
                else "Transaction Status Update"
            )
            body = (
                f"{business.name} has {txn_status} your transaction of amount "
                f"{txn.amount}{txn.currency}."
            )
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
