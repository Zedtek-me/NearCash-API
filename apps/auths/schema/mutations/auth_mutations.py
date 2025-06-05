import graphene
from graphene import ObjectType

from apps.auths.schema.types.enums import SignInWithEnum
from apps.auths.schema.types.auth_types import LoginInfoType

from utils.helpers.logs import logger
from utils.auth_utils.auths import AuthUtils

class LoginMutation(graphene.Mutation):

    message = graphene.String()
    data = LoginInfoType()

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
            message="Authentication mutation executed successfully.",
            data=LoginInfoType(**data)
        )

class Mutation(ObjectType):
    login = LoginMutation.Field(description="Login mutation for user authentication.")
    logout = None
    signup = None
