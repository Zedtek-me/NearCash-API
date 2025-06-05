from typing import Optional, Dict, Any, List, Union

from apps.auths.constants import OAUTH_PLATFORMS
from apps.auths.models import User
from interfaces.auths.interface import AuthInterface

class AuthUtils:

    def __init__(self, auth_type) -> None:
        if auth_type not in OAUTH_PLATFORMS:
            raise ValueError("invalid auth type")
        self.auth_type = auth_type

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
