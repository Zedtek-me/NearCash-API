import graphene
from graphql_jwt.decorators import login_required
from django.db import transaction
from apps.auths.schema.types.auth_types import UserType, UpdateUserInputType

from utils.user_utils.users import UserUtil


class UpdateUser(graphene.Mutation):
    """updates user profile information"""

    message = graphene.String()
    user = graphene.Field(UserType)

    class Arguments:
        data = UpdateUserInputType(required=True)

    @login_required
    @transaction.atomic
    def mutate(self, info, **kwargs):
        user = info.context.user
        data = kwargs.get("data", {})
        user = UserUtil.update_user(user, data)
        return UpdateUser(
            message="User updated successfully.",
            user=user
        )


class Mutation(graphene.ObjectType):
    update_user = UpdateUser.Field(description="Update user profile information.")
