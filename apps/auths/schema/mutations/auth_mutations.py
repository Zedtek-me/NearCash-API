from typing import Optional
import graphene
from graphene import ObjectType
from django.db import transaction

from apps.auths.schema.types.enums import SignInWithEnum
from apps.auths.schema.types.auth_types import LoginInfoType, AuthInputType

from utils.helpers.logs import logger
from utils.auth_utils.auths import AuthUtils



class SignUpMutation(graphene.Mutation):
    message = graphene.String()
    data = graphene.Field(LoginInfoType)

    class Arguments:
        data = AuthInputType()
        sign_in_with = SignInWithEnum(required=False)

    @transaction.atomic
    def mutate(self, info, **kwargs):
        pass

class LoginMutation(graphene.Mutation):

    message = graphene.String()
    data = graphene.Field(LoginInfoType)

    class Arguments:
        email = graphene.String(required=False)
        password = graphene.String(required=False)
        sign_in_with = SignInWithEnum(required=False)

    def mutate(self, info, **kwargs):
        sign_in_with = kwargs.get('sign_in_with')
        email, password = kwargs.get('email'), kwargs.get('password')
        auth_url = user = token = None
        if sign_in_with:
            auth_url = AuthUtils(sign_in_with).get_auth_url()
            logger.debug(f"OAuth2 authorization URL: {auth_url}")
        else:
            user, token = AuthUtils.authenticate_with_password(email, password)
        data = {
            "user": user,
            "auth_url": auth_url,
            "token": token
        }
        return LoginMutation(
            message="success.",
            data=LoginInfoType(**data)
        )

class AuthorizeWithCode(LoginMutation):

    class Arguments:
        code = graphene.String(required=True)
        auth_type = SignInWithEnum(required=True)

    def mutate(self, info, **kwargs):
        code = kwargs.get("code")
        auth_type = kwargs.get("auth_type")
        user = token = None
        auth_obj = AuthUtils(auth_type)
        credential_tokens = auth_obj.get_auth_tokens(code)
        user_info: Optional[dict] = auth_obj.fetch_user_info(credential_tokens)
        user, token = auth_obj.authorize_user_locally(user_info)
        return AuthorizeWithCode(
            message="user successfully authorized",
            data=LoginInfoType(user=user, token=token)
        )


class Mutation(ObjectType):
    login = LoginMutation.Field(description="Login mutation for user authentication.")
    logout = None
    signup = SignUpMutation.Field(description="Sign up mutation for user registration.")
    authorize_with_code = AuthorizeWithCode.Field(description="Authorize with code")
