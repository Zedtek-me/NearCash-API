import graphene
from graphene import ObjectType

from apps.auths.services import GoogleService
from apps.auths.schema.types.enums import SignInWithEnum
from apps.auths.schema.types.auth_types import LoginInfoType

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
        if sign_in_with == SignInWithEnum.GOOGLE:
            auth_url = GoogleService.get_auth_url()
        return LoginMutation(
            message="Authentication mutation executed successfully."
        )

class Mutation(ObjectType):
    login = LoginMutation.Field(description="Login mutation for user authentication.")
    logout = None
