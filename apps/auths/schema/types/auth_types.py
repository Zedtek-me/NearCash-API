import graphene
from graphene import ObjectType
from graphene_django import DjangoObjectType

from apps.auths.models import User


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = "__all__"


class LoginInfoType(ObjectType):
    """
    Type for login information.
    """
    user = graphene.Field(UserType, required=False)
    token = graphene.String(required=False)
    auth_url = graphene.String(required=False)


class AuthInputType(graphene.InputObjectType):
    email = graphene.String()
    first_name = graphene.String(required=False)
    last_name = graphene.String(required=False)
    username = graphene.String(required=False)
    password = graphene.String()
