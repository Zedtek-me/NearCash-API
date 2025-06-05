import graphene
from graphene import ObjectType
from apps.auths.schema.types.auth_types import UserType


class Query(ObjectType):
    user = graphene.Field(UserType)

    def resolve_user(self, info, **kwargs):
        return None
