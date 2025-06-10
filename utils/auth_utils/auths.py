from typing import Optional, Dict, Any, List, Union
from graphql_jwt.utils import jwt_encode, jwt_payload

from apps.auths.constants import OAUTH_PLATFORMS, PasswordAuthTypeEnum
from apps.auths.models import User, SocialToken

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

    def get_auth_tokens(
        self, auth_code: str, source: Optional[str]="GOOGLE"
    )-> Union[dict, str, None]:
        """uses auth codes to fetch auth tokens"""
        user_creds = self.auth_service.get_auth_tokens(auth_code)
        cred_local_copy = SocialToken(
            source=source,
            access_token=user_creds.get("access_token"),
            refresh_token=user_creds.get("refresh_token", "")
        )
        cred_local_copy.save()
        user_creds["local_cred_id"] = cred_local_copy.id
        logger.debug(f"user credentials obtained::: {user_creds}")
        return user_creds

    @classmethod
    def authenticate_with_password(
        cls, email: str, password: str, **kwargs
    ) -> Union[User, dict, str, Exception, tuple, list]:
        """authenticates user with email and password"""
        auth_type: PasswordAuthTypeEnum = kwargs.get("auth_type")
        skip_pass_check = kwargs.get("skip_pass_check", False)
        if auth_type and auth_type == PasswordAuthTypeEnum.LOGIN.value:
            user = User.objects.filter(email__iexact=email).first()
            if not (user or password) and not skip_pass_check:
                raise Exception("Invalid authentication credentials!")
            if (user and password and not user.check_password(password) and not skip_pass_check):
                raise Exception("Invalid authentication credentials!")
            token = cls.generate_user_local_auth_tokens(user)
            return [user, token]
        # implement password signup
        first_name, last_name = (kwargs.get("first_name", ""), kwargs.get("last_name", ""))
        picture = kwargs.get("picture")
        user_data = {
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "username": f"{first_name} {last_name}"
        }
        user = User.objects.create_user(**user_data)
        user.meta["picture"] = picture
        user.save()
        token = cls.generate_user_local_auth_tokens(user)
        return [user, token]

    @classmethod
    def authorize_user_locally(
        cls, user_info: dict, auth_type="signup",
        source="GOOGLE"
    )-> Union[tuple, dict, str, list]:
        """
        uses the authorization tokens provided by the social auth to log user in locally
        """
        email = user_info.get("email", "")
        first_name = user_info.get("given_name", "")
        last_name = user_info.get("family_name")
        picture = user_info.get("picture")
        local_social_token_copy = SocialToken.fetch_instance(id=user_info.get("local_cred_id"))
        user, token = cls.authenticate_with_password(
            email, None, auth_type=auth_type, skip_pass_check=True,
            first_name=first_name, last_name=last_name, picture=picture
        )
        if user and local_social_token_copy:
            # update existing tokens for this user to inactive
            SocialToken.fetch_instance(return_all=True, user=user, source=source).update(is_active=False)
            local_social_token_copy.user = user
            local_social_token_copy.save()
        return [user, token]

    def fetch_user_info(
        self, credentials: Union[dict, str]
    ) -> Union[dict, list]:
        """fetches user info via the credential tokens provided"""
        local_cred_id = credentials.pop("local_cred_id", None)
        user_info = self.auth_service.fetch_user_info(credentials)
        if user_info:
            user_info["local_cred_id"] = local_cred_id
        return user_info

    @classmethod
    def generate_user_local_auth_tokens(
        cls, user: User, **kwargs
    ) -> dict:
        """creates a local copy of JWT tokens for user"""
        payload = jwt_payload(user)
        token = jwt_encode(payload)
        return token
