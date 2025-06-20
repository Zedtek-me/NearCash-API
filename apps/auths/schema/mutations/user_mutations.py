import graphene
from graphql_jwt.decorators import login_required

from apps.auths.schema.types.auth_types import UserType, UpdateUserInputType

from utils.user_utils.users import UserUtil


class UpdateUser(graphene.Mutation):
    """updates user profile information"""

    message = graphene.String()
    user = graphene.Field(UserType)

    class Arguments:
        user_id = graphene.String(required=True)
        data = UpdateUserInputType(required=True)

    @login_required
    def mutate(self, info, **kwargs):
        user = info.context.user
        user_id = kwargs.get("user_id")
        data = kwargs.get("data", {})
        if user.id != user_id:
            raise Exception("You can only update your own profile.")
        user = UserUtil.update_user(user, data)
        return UpdateUser(
            message="User updated successfully.",
            user=user
        )


class Mutation(graphene.ObjectType):
    update_user = UpdateUser.Field(description="Update user profile information.")
