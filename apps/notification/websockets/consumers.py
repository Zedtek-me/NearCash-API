from typing import Any, Dict, Union, Optional, Type

from asgiref.sync import sync_to_async, async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from utils.helpers.logs import logger
from utils.notifications.notifications import NotificationUtil
from utils.core_utils.business_utils import BusinessUtil
from utils.helpers.exception import CustomException

from apps.core.models import CurrentLocation

from django.conf import settings



class NotificationConsumer(JsonWebsocketConsumer):
    """WebSocket consumer for handling notifications."""

    general_notification_group_name = settings.GENERAL_NOTIFICATION_GROUP_NAME

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.auths.models import User as UserModel

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
        super().disconnect(close_code)

    def receive_json(self, text_data):
        """Handle incoming messages."""
        from utils.wallet_utils.transactions import TransactionUtil

        msg_type = text_data.get('message_type', "")
        if msg_type and msg_type.lower() == "vendor_location_update":
            vendor_id = text_data.get("vendor_id")
            business_id = text_data.get("business_id")
            location = text_data.get("location")

            # record the vendor's location
            try:
                self._record_vendor_location(
                    vendor_id=vendor_id,
                    business_id=business_id,
                    location=location
                )
            except Exception as e:
                logger.error(f"Error recording vendor location: {e}")
                self.send_json({
                    "message_type": "error",
                    "message": str(e)
                })
                return
            self.send_json({
                "message_type": "vendor_location_update_ack",
            })

        if msg_type == "retrieve_vendor_latest_location":
            vendor_id = text_data.get("vendor_id")
            txn_id = text_data.get("txn_id")
            client_coordinate = None
            txn = TransactionUtil.get_transaction(**{"id": txn_id})
            if txn:
                client_coordinate = {
                    "longitude": txn.meta.get("client_current_location", {}).get("longitude"),
                    "latitude": txn.meta.get("client_current_location", {}).get("latitude")
                }
            vendor_latest_location = BusinessUtil.get_vendor_latest_location(
                vendor_id, client_coordinate
            )
            self.send_json({
                "message_type": "vendor_latest_location",
                "vendor_id": vendor_id,
                "location": vendor_latest_location
            })
        return

    def send_notification(self, event):
        """Send a notification to the WebSocket."""
        self.send_json(content=event['message'])


    def _update_user_channel(self) -> None:
        """Update the user's status to online."""
        if self.user:
            self.user.user_queue = f"{self.user.id}_queue"

    def _record_vendor_location(self, **kwargs) -> CurrentLocation:
        from apps.auths.models import User as UserModel

        vendor_id = kwargs.get("vendor_id")
        business_id = kwargs.get("business_id")
        location = kwargs.get("location")

        if not location or not vendor_id:
            CustomException("Invalid data provided for recording location", status_code=400)
        vendor_user = UserModel.objects.filter(id=vendor_id, meta__user_type="VENDOR").first()
        location = BusinessUtil.record_current_location(
            vendor_user, location, location_type="Vendor",
            business_id=business_id
        )
        return location
