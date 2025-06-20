import graphene
from graphene import ObjectType
from graphene_django import DjangoObjectType

from apps.auths.models import User


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = "__all__"
    user_type = graphene.String()

    def resolve_user_type(self, info):
        return self.meta.get("user_type", "CLIENT")



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

class UpdateUserInputType(graphene.InputObjectType):
    user_type = graphene.String(required=False)
    first_name = graphene.String(required=False)
    last_name = graphene.String(required=False)
    username = graphene.String(required=False)
    picture = graphene.String(required=False)
