from asgiref.sync import async_to_sync
from celery import shared_task

from channels.layers import get_channel_layer

from django.conf import settings
from django.db.models import Model

from typing import Union, Any, Optional

from apps.notification.models import Notification
from apps.auths.models import User
from apps.core.models import Business


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
        from django.contrib.contenttypes.models import ContentType

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
