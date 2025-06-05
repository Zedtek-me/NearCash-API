from typing import Optional, Dict, Any, List, Union
from django.conf import settings
from google_auth_oauthlib.flow import Flow

class GoogleService:

    flow = Flow.from_client_secrets_file(
        "",
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
