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

class Mutation(ObjectType):
    login = LoginMutation.Field(description="Login mutation for user authentication.")
    logout = None
    signup = SignUpMutation.Field(description="Sign up mutation for user registration.")

