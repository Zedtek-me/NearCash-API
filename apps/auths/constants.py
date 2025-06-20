from enum import Enum
from typing import Optional, AnyStr
from apps.auths.services import GoogleService

OAUTH_PLATFORMS = {
    "GOOGLE": GoogleService,
    "FACEBOOK": None,  # Placeholder for Facebook service
    "GENERAL": None
}


class PasswordAuthTypeEnum(Enum):
    LOGIN = "login"
    SIGNUP = "signup"
