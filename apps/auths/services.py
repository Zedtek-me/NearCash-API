from typing import Optional, Dict, Any, List, Union
from django.conf import settings
from google_auth_oauthlib.flow import Flow

from interfaces.auths.interface import AuthInterface

class GoogleService(AuthInterface):

    flow = Flow.from_client_secrets_file(
        f"{settings.BASE_DIR}/oauth_client_ids.json",
        scopes=[
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile"
        ],
        redirect_uri=settings.GOOGLE_REDIRECT_URI
    )

    @classmethod
    def get_auth_url(cls) -> str:
        """
        Returns the Google OAuth2 authorization URL.
        """
        return cls.flow.authorization_url()
