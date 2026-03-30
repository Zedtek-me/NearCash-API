import uuid
from django.utils import timezone

def generate_unique_id(count: int = 0):
    if count and count > 0:
        return uuid.uuid4().hex[:count]
    return uuid.uuid4().hex


def get_two_formatted_datetime(difference_in_sec: int = 8) -> tuple:
    """
    returns two stringified datetime objects formatted as start and end
    """
    now = timezone.now()
    expiry = now + timezone.timedelta(seconds=difference_in_sec)
    strigified_now = timezone.datetime.strftime(
        now, "%Y-%m-%dT%H:%M:%SZ"
    )
    stringified_expiry = timezone.datetime.strftime(
        expiry, "%Y-%m-%dT%H:%M:%SZ"
    )
    return (
            strigified_now, stringified_expiry
        )
