import graphene
from graphene import ObjectType
from graphene_django import DjangoObjectType

from apps.auths.models import User


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'is_active', 'is_staff')


class LoginInfoType(ObjectType):
    """
    Type for login information.
    """
    user = graphene.Field(UserType, required=False)
    token = graphene.String(required=False)
    redirect_url = graphene.String(required=False)

