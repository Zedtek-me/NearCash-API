from celery import shared_task

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from utils.helpers.logs import logger

from near_cash.celery import app

class BusinessAsyncOperations:

    @shared_task(bind=True, name="notify_vendor_about_transaction")
    def notify_vendor_about_transaction(
        self, txn_id: str | int, **kwargs
    ) -> bool:
        """
        Notifies the merchant of a client's txn interest.
        Notifies via email, sms and websocket
        """

        from apps.notification.email.app_emails import EmailService
        from utils.wallet_utils.transactions import TransactionUtil
        from apps.auths.models import User

        channel_layer = get_channel_layer()
        txn = TransactionUtil.get_transaction(**{"id": txn_id})
        logger.debug(f"Transaction to publish to vendor fetched: {txn}")
        if not txn:
            logger.error(f"Transaction with id {txn_id} not found.")
            return False
        vendor: User | None = txn.vendor
        if not vendor:
            return False

        txn_info = {
                    "txn_ref": txn.txn_ref,
                    "client_id": txn.client.id,
                    "amount": txn.amount,
                    "client_current_location": txn.meta.get("client_current_location", {}),
                    "mode": txn.collection_mode,
                }

        notification_data = {
            "type": "send.notification",
            "message": {
                "title": "New Transaction Interest",
                "txn_info": txn_info
            }
        }
        logger.debug(f"about to send websocket notification to vendor: {vendor.email} with data: {notification_data}")
        try:
            async_to_sync(
            channel_layer.send
            )(
                vendor.user_queue, notification_data
            )
        except Exception as e:
            logger.exception(f"exception while sending websocket notification: {e}")
            raise e
        # EmailService.send_email()
