import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging

from django.conf import settings

from utils.helpers.logs import logger


class FirebaseService:
    """all things firebase"""
    def __init__(self):
        self.cred = credentials.Certificate(
            f"{settings.BASE_DIR}"
            "/nearcash-push-firebase-adminsdk-fbsvc-a8dd50a1bf.json"
        )
        self.app = firebase_admin.initialize_app(self.cred)


    def send_push_msg(
        self, *args, **kwargs
    ) -> bool:
        """
        sends push notification to the given recipients' platform
        """
        recipient_fids = kwargs.get("recipient_fids", [])
        message_data = kwargs.get("data", {})
        fcm_message = messaging.MulticastMessage(
            data=message_data,
            fids=recipient_fids
        )
        response = messaging.send_each_for_multicast(fcm_message)
        failed_responses = []
        if response.failure_count > 0:
            responses = response.responses
            for idx, resp in enumerate(responses):
                if not resp.success:
                    failed_responses.append(recipient_fids[idx])
            logger.debug(f"failed to send notification to the given fids:: {recipient_fids}")
            # TODO: log failed fids somewhere, alongside the message data they were meant to receive.
            # if the message isn't really a time-sensitive type, implement a background check for a retry or something related.
            return False
        logger.debug(
            f"response: {response}\n"
            f"responses:: {response.responses}"
        )
        return True
