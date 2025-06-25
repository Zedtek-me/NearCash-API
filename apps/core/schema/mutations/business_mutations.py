import graphene
from graphql_jwt.decorators import login_required
from django.db import transaction
from apps.core.schema.types.business_types import BusinessType, CreateBusinessInputType

from utils.core_utils.business_utils import BusinessUtil


class CreateBusiness(graphene.Mutation):
    """Creates a new business for the user."""

    message = graphene.String()
    business = graphene.Field(BusinessType)

    class Arguments:
        data = CreateBusinessInputType(required=True)

    @login_required
    @transaction.atomic
    def mutate(self, info, **kwargs):
        from utils.user_utils.users import UserUtil

        user = info.context.user
        data = kwargs.get("data", {})
        business_data = UserUtil.prepare_business_data(data)
        business = BusinessUtil.create_business(user, business_data)
        return CreateBusiness(
            message="Business created successfully.",
            business=business
        )

class Mutation(graphene.ObjectType):
    create_business = CreateBusiness.Field(description="Create a new business for the user.")
