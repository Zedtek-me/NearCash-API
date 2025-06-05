from typing import Optional, Dict, Any, List, Union

from apps.auths.constants import OAUTH_PLATFORMS
from apps.auths.models import User
from interfaces.auths.interface import AuthInterface
from utils.helpers.logs import logger

class AuthUtils:

    def __init__(self, auth_type) -> None:
        logger.debug(f"auth type from client: {auth_type.name}")
        if auth_type.name not in OAUTH_PLATFORMS:
            raise ValueError("invalid auth type")
        self.auth_type = auth_type.name

    def get_auth_url(self) -> str:
        """
        Gets the authentication URL for the specified OAuth platform.
        """
        auth_service: AuthInterface = OAUTH_PLATFORMS[self.auth_type]
        return auth_service.get_auth_url()

    @classmethod
    def authenticate_with_password(
        cls, email: str, password: str, **kwargs
    ) -> Union[User, dict, str, Exception, tuple]:
        """authenticates user with email and password"""
