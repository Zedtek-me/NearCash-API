import graphene
from graphene import ObjectType
from graphql_jwt.decorators import login_required
from apps.auths.schema.types.auth_types import UserType


class Query(ObjectType):
    user = graphene.Field(UserType)

    @login_required
    def resolve_user(self, info, **kwargs):
        """returns the authenticated user"""
        return info.context.user
