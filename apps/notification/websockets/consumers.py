from typing import Any, Dict, Union, Optional, Type

from asgiref.sync import sync_to_async, async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from utils.helpers.logs import logger
from utils.notifications.notifications import NotificationUtil
from utils.helpers.exception import CustomException


from django.conf import settings



class NotificationConsumer(JsonWebsocketConsumer):
    """WebSocket consumer for handling notifications."""
    general_notification_group_name = settings.GENERAL_NOTIFICATION_GROUP_NAME

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.auths.models import User as UserModel
        from utils.core_utils.business_utils import BusinessUtil

        self.MESSAGE_TYPE_HANDLERS = {
            "vendor_location_update": {
                "handler": BusinessUtil.record_vendor_location,
                "response": {}
            },
            "client_location_update": {
                "handler": BusinessUtil.record_client_location,
                "response": {}
            },
            "retrieve_vendor_latest_location": {
                "handler": BusinessUtil.get_vendor_latest_location,
                "response": {}
            },
            "retrieve_client_latest_location": {
                "handler": BusinessUtil.get_client_latest_location,
                "response": {}
            }
        }


        self.user: Optional[UserModel] = None

    def connect(self):
        """Handle new WebSocket connections."""
        self.user = self.scope.get('user')
        if not self.user or self.user.is_anonymous:
            self.close(code=4000)
            return

        self.accept()
        self._update_user_channel()
        NotificationUtil.add_user_to_needed_groups(self.user, self.channel_name)
        self.send_json(f"welcome {self.user.email}!")

    def disconnect(self, close_code):
        """Handle WebSocket disconnections."""
        if self.user and not self.user.is_anonymous:
            NotificationUtil.remove_users_from_needed_groups(self.user, self.channel_name)
        super().disconnect(close_code)

    def receive_json(self, content: Union[dict, str], *args, **kwargs):
        """Handle incoming messages."""

        logger.debug(f"content gotten on websocket msg receiver::::::::: {content}")
        msg_type = content.pop('message_type', "")

        # handle message type
        try:
            vendor_id = content.get("vendor_id")
            client_id = content.get("client_id")
            handled_response = self.MESSAGE_TYPE_HANDLERS.get(msg_type, {})\
                .get("handler")(**content)
            response: dict = self.MESSAGE_TYPE_HANDLERS.get(msg_type, {}).get("response", {})
        except Exception as e:
            logger.error(f"Error recording vendor location: {e}")
            self.send_json({
                "message_type": "error",
                "message": str(e)
            })
            return

        match msg_type:
            case "vendor_location_update":
                response["message_type"] = "vendor_location_update_ack"
                self.send_json(response)
            case "client_location_update":
                response["message_type"] = "client_location_update_ack"
                self.send_json(response)
            case "retrieve_vendor_latest_location":
                response.update({
                    "message_type": "vendor_latest_location",
                    "vendor_id": vendor_id,
                    "location": handled_response #will always be a dict for this msg type
                })
                async_to_sync(self.channel_layer.group_send)(
                    self.general_notification_group_name,
                    {
                        "type": "send.notification",
                        "message": response
                    }
                )
            case "retrieve_client_latest_location":
                response.update({
                    "message_type": "client_latest_location",
                    "client_id": client_id,
                    "location": handled_response #will always be a dict for this msg type
                })
                async_to_sync(self.channel_layer.group_send)(
                    self.general_notification_group_name,
                    {
                        "type": "send.notification",
                        "message": response
                    }
                )
            case _:
                self.send_json({
                    "message_type": "error",
                    "message": "message unknown!"
                })
        return

    def send_notification(self, event):
        """Send a notification to the WebSocket."""
        self.send_json(content=event["message"])


    def _update_user_channel(self) -> None:
        """Update the user's status to online."""
        if self.user:
            self.user.user_queue = f"{self.user.id}_queue"
