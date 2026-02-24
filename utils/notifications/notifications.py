from asgiref.sync import async_to_sync

from channels.layers import get_channel_layer

from django.conf import settings

from typing import Union, Any, Optional


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
