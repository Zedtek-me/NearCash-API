from typing import Any, Dict, Union, Optional, Type

from asgiref.sync import sync_to_async, async_to_sync
from channels.db import database_sync_to_async
from channels.generic.websocket import JsonWebsocketConsumer

from utils.helpers.logs import logger



class NotificationConsumer(JsonWebsocketConsumer):
    """WebSocket consumer for handling notifications."""

    group_name = "nearcash_notifications"

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
        self.send_json(f"welcome {self.user.email}!")

    def disconnect(self, close_code):
        """Handle WebSocket disconnections."""
        super().disconnect(close_code)

    def receive_json(self, text_data):
        """Handle incoming messages."""
        pass

    def send_notification(self, event):
        """Send a notification to the WebSocket."""
        self.send_json(content=event['message'])


    def _update_user_channel(self) -> None:
        """Update the user's status to online."""
        if self.user:
            self.user.user_queue = self.channel_name
