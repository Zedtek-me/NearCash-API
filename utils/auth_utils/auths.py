from typing import Optional, Dict, Any, List, Union

from apps.auths.constants import OAUTH_PLATFORMS, PasswordAuthTypeEnum
from apps.auths.models import User
from interfaces.auths.interface import AuthInterface
from utils.helpers.logs import logger

class AuthUtils:

    def __init__(self, auth_type) -> None:
        if auth_type.name not in OAUTH_PLATFORMS:
            raise ValueError("invalid auth type")
        self.auth_type = auth_type.name
        self.auth_service: AuthInterface = OAUTH_PLATFORMS[self.auth_type]

    def get_auth_url(self) -> str:
        """
        Gets the authentication URL for the specified OAuth platform.
        """
        return self.auth_service.get_auth_url()

    def get_auth_tokens(self, auth_code: str)-> Union[dict, str, None]:
        """uses auth codes to fetch auth tokens"""
        return self.auth_service.get_auth_tokens(auth_code)

    @classmethod
    def authenticate_with_password(
        cls, email: str, password: str, **kwargs
    ) -> Union[User, dict, str, Exception, tuple, list]:
        """authenticates user with email and password"""
        auth_type: PasswordAuthTypeEnum = kwargs.get("auth_type")
        if auth_type == auth_type.LOGIN:
            # implement login check
            return
        # implement password signup
        return []

    @classmethod
    def authorize_user_locally(
        cls, user_info: dict
    )-> Union[tuple, dict, str, list]:
        """
        uses the authorization tokens provided by the social auth to log user in locally
        """
        logger.debug(f"user info gotten::: {user_info}")
        return [None,None]

    def fetch_user_info(
        self, credentials: Union[dict, str]
    ) -> Union[dict, list]:
        """fetches user info via the credential tokens provided"""
        logger.debug(f"credentials provided:::: {credentials}")
        self.auth_service.fetch_user_info(credentials)
        return {}
