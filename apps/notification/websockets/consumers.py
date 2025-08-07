from typing import Any, Dict, Union, Optional, Type

from asgiref.sync import sync_to_async, async_to_sync
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model



class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for handling notifications."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.auths.models import User as UserModel

        self.user: Optional[UserModel] = None
        self.group_name = None

    async def connect(self):
        """Handle new WebSocket connections."""
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        # Join the notification group for the user
        await self._update_user_channel()
        await self.accept()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnections."""
        await super().disconnect(close_code)

    async def receive(self, text_data):
        """Handle incoming messages."""
        pass

    async def send_notification(self, event):
        """Send a notification to the WebSocket."""
        await self.send(text_data=event['message'])

    async def _update_user_channel(self) -> None:
        """Update the user's status to online."""
        if self.user:
            self.user.meta["channel_name"] = self.channel_name
            await database_sync_to_async(self.user.save)()
