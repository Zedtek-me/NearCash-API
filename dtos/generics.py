from dataclasses import dataclass
from typing import Optional, List

from django.conf import settings

from utils.https.client import Client
from utils.helpers.exception import CustomException



SMS_PLATFORMS = {
    "termii": {
        "url": settings.TERMII_BASE_URL,
        "headers": {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"{settings.TERMII_API_KEY}"
        }
    }
}


from utils.helpers.logs import logger

@dataclass
class EmailArgsDto:
    subject: str
    body: str
    recipients: list
    context: Optional[dict]
    attchments: Optional[List[dict]]


@dataclass
class SMSPlatformDto:
    name: str
    base_url: str
    headers: dict

    def __post_init__(self):
        platform_cred = SMS_PLATFORMS.get(self.name, {})
        if not platform_cred:
            raise CustomException(
                message="platform name given is not amongst supported sms platforms!"
            )
        self.base_url = platform_cred.get("url") or ""
        self.headers = platform_cred.get("headers", {})


    def send_sms(
        self, content: dict | str | int | float,
        recipient_ids: list
    ) -> bool:
        client = Client(self.base_url, self.headers)
        payload = {
            "recipient": recipient_ids,
            "content": content
        }
        response = client.post("/sms", payload=payload)
        logger.debug(f"sms sending response::: {response}")
        return True
