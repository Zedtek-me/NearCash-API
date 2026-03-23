import os
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from utils.helpers.logs import logger
from utils.helpers.encryption import encrypt_data_with_fernet
from utils.https.client import Client

from apps.payment.models import PaymentPlatformToken

@shared_task(
    name="refresh-flutterwave-access-token", bind=True
)
def refresh_access_token(self):
    """
    checks to refresh access token
    from flutterwave
    """
    client_id = settings.FLUTTERWAVE_CLIENT_ID
    client_secret = settings.FLUTTERWAVE_CLIENT_SECRET
    grant_type = "client_credentials"
    token_key_name = "FLUTTERWAVE_ACCESS_TOKEN"

    current_token_info = PaymentPlatformToken.fetch_token_info("FLUTTERWAVE")
    existing_token = os.getenv(token_key_name)

    should_refresh = _should_refresh_token(existing_token, current_token_info)

    if should_refresh:
        client = Client(settings.FLUTTERWAVE_OAUTH_URL)
        response = client.post(
            "/token",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": grant_type
            }
        )
        logger.debug(f"response from access token generation on flutterwave::: {response}")
        if not response or response.get("status") == "failed":
            logger.error(f"unable to refresh flutterwave access token::: {response}")
            return
        token_expiry = response.get("expires_in", 600)
        access_token = response.get("access_token", "")
        encrypted_access_token = encrypt_data_with_fernet(access_token)
        if not current_token_info:
            current_token_info = PaymentPlatformToken()
        current_token_info.token = encrypted_access_token
        current_token_info.expires_in = timezone.timedelta(seconds=token_expiry)
        current_token_info.save()


def write_token_to_file(
    key: str, value: str
):
    new_lines = []
    key_exists = False
    with open(settings.DOTENV_FILENAME, "r") as file:
        all_items = file.readlines()

    for item in all_items:
        if item.startswith(f"{key}=") or item.startswith(f"{key} = "):
            new_lines.append(f"{key}={value}\n")
            key_exists = True
        else:
            new_lines.append(f"{item}")

    if not key_exists:
        new_lines.append(f"{key}={value}")

    if new_lines and not new_lines[-1].endswith("\n"):
        new_lines[-1] += "\n"

    with open(settings.DOTENV_FILENAME, "w") as file:
        file.writelines(new_lines)
    logger.debug("flutterwave key updated!!!")


def _should_refresh_token(
    existing_token: str | None = None,
    db_token_info: PaymentPlatformToken | None = None
) -> bool:

    if not existing_token:
        return True

    if not db_token_info:
        return True

    current_token_expiry = (
        db_token_info.expires_in
        or timezone.timedelta(minutes=10)
    )

    last_update_dt = db_token_info.last_updated
    time_left_to_refresh = last_update_dt - timezone.now()
    if time_left_to_refresh <= timezone.timedelta(seconds=1):
        return True
    return False
