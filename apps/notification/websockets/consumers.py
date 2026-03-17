import time
from typing import Any, Dict, Union, Optional, Type

from asgiref.sync import sync_to_async, async_to_sync
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

from utils.helpers.logs import logger
from utils.helpers.exception import CustomException


from django.conf import settings



class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for handling notifications."""
    general_notification_group_name = settings.GENERAL_NOTIFICATION_GROUP_NAME

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.auths.models import User as UserModel
        from utils.core_utils.business_utils import BusinessUtil

        self.MESSAGE_TYPE_HANDLERS = {
            "vendor_location_update": {
                "handler": sync_to_async(BusinessUtil.record_vendor_location),
                "response": {}
            },
            "client_location_update": {
                "handler": sync_to_async(BusinessUtil.record_client_location),
                "response": {}
            },
            "retrieve_vendor_latest_location": {
                "handler": sync_to_async(BusinessUtil.get_vendor_latest_location),
                "response": {}
            },
            "retrieve_client_latest_location": {
                "handler": sync_to_async(BusinessUtil.get_client_latest_location),
                "response": {}
            },
            "opportunity_accepted": {
                "handler": sync_to_async(BusinessUtil.accept_transaction_opportunity),
                "response": {}
            }
        }


        self.user: Optional[UserModel] = None

    async def connect(self):
        """Handle new WebSocket connections."""
        from utils.core_utils.business_utils import BusinessUtil
        from utils.notifications.notifications import NotificationUtil

        self.user = self.scope.get('user')
        if not self.user or self.user.is_anonymous:
            await self.close(code=4000)
            return

        await self.accept()
        await database_sync_to_async(self._update_user_channel)()
        await sync_to_async(
                NotificationUtil.add_user_to_needed_groups
            )(self.user, self.channel_name)
        await database_sync_to_async(
            BusinessUtil.check_and_activate_vendor_businesses
        )(
            self.user, _all=True, skip_error=True
        )
        # await self.send_json(f"welcome {self.user.email}!")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnections."""
        from utils.core_utils.business_utils import BusinessUtil
        from utils.notifications.notifications import NotificationUtil

        if self.user and not self.user.is_anonymous:
            await sync_to_async(
                NotificationUtil.remove_users_from_needed_groups
            )(self.user, self.channel_name)
            await database_sync_to_async(
                BusinessUtil.deactivate_businesses_for_vendor
            )(
                self.user, _all=True, skip_error=True
            )
        await super().disconnect(close_code)

    async def receive_json(self, content: dict, *args, **kwargs):
        """Handle incoming messages."""
        from background_tasks.core.business import BusinessAsyncOperations

        logger.debug(f"content gotten on websocket msg receiver::::::::: {content}")
        msg_type = content.pop('message_type', "")

        # handle message type
        try:
            vendor_id = content.get("vendor_id")
            client_id = content.get("client_id")
            handler = self.MESSAGE_TYPE_HANDLERS.get(msg_type, {})\
                .get("handler")
            handled_response = None
            if handler:
                handled_response = await handler(**content)
            response: dict = self.MESSAGE_TYPE_HANDLERS.get(msg_type, {}).get("response", {})
        except Exception as e:
            # await sync_to_async(time.sleep)(5) #for debugging
            logger.exception(f"Error occured:::::: {e}")
            await self.send_json({
                "message_type": "error",
                "message": str(e)
            })
            return

        match msg_type:
            case "vendor_location_update":
                response["message_type"] = "vendor_location_update_ack"
                await self.send_json(response)
            case "client_location_update":
                response["message_type"] = "client_location_update_ack"
                await self.send_json(response)
            case "retrieve_vendor_latest_location":
                response.update({
                    "message_type": "vendor_latest_location",
                    "vendor_id": vendor_id,
                    "location": handled_response #will always be a dict for this msg type
                })
                await self.channel_layer.group_send(
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
                await self.channel_layer.group_send(
                    self.general_notification_group_name,
                    {
                        "type": "send.notification",
                        "message": response
                    }
                )
            case "opportunity_accepted":
                if handled_response and handled_response is True:
                    message_type = "acceptance_ack"
                    await sync_to_async(
                        BusinessAsyncOperations.run_post_opportunity_acceptance_task
                    )(trxn_id=content.get("txn_id"))
                else:
                    message_type = "opportunity_lost"
                response.update({
                    "message_type": message_type
                })
                await self.send_json(response)

            case _:
                await self.send_json({
                    "message_type": "error",
                    "message": "message unknown!"
                })
        return

    async def send_notification(self, event):
        """Send a notification to the WebSocket."""
        try:
            await self.send_json(content=event["message"])
            logger.debug(f"message from event: {event} was successfully handled by consumer!!!")
        except Exception as e:
            logger.exception(f"exception in 'send_notification' consumer handler::: {e} ")


    def _update_user_channel(self) -> None:
        """Update the user's status to online."""
        if self.user:
            self.user.user_queue = f"user_{self.user.id}_queue"
