from typing import Optional, Dict, Any, List, Union
from django.conf import settings
from google_auth_oauthlib.flow import Flow

from interfaces.auths.interface import AuthInterface

from utils.helpers.logs import logger

class GoogleService(AuthInterface):

    flow = Flow.from_client_secrets_file(
        f"{settings.BASE_DIR}/oauth_client_ids.json",
        scopes=[
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
            "openid"
        ],
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )

    @classmethod
    def get_auth_url(cls) -> str:
        """
        Returns the Google OAuth2 authorization URL.
        """
        return cls.flow.authorization_url()[0]

    @classmethod
    def get_auth_tokens(
        cls, auth_code: str
    )-> Union[dict, str]:
        """
        fetches authorization tokens via the provided ${auth_code}
        """
        return cls.flow.fetch_token(code=auth_code)

    @classmethod
    def fetch_user_info(
        cls, credentials: Union[dict, str]
    )-> Union[dict, list, tuple]:
        """
        fetches user data using the credentials provided via the $get_auth_tokens method
        """
        flow_cred = cls.flow.credentials
        logger.debug(f"flow credentials object::::: {flow_cred}\n passed in user credentials: {credentials}")
