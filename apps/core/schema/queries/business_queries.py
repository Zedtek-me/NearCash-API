import graphene
from graphql_jwt.decorators import login_required

from django.db.models import Q, F

from apps.core.models import Business
from apps.core.schema.types.business_types import (
    BusinessType
)

from utils.core_utils.business_utils import BusinessUtil
from utils.helpers.pagination import PaginationUtil


class Query(graphene.ObjectType):
    pagination = graphene.Field(graphene.JSONString())
    business = graphene.Field(
        BusinessType,
        business_id=graphene.String(required=True)
    )
    businesses = graphene.List(
        BusinessType,
        location=graphene.String(),
        address=graphene.String(),
        id=graphene.String(),
        name=graphene.String(),
        owner_id=graphene.String(),
        page_count=graphene.Int(),
        page_number=graphene.Int()
    )
    businesses_around_me = graphene.List(
        BusinessType, current_lat=graphene.Float(required=True),
        current_long=graphene.Float(required=True),
    )

    @login_required
    def resolve_business(self, info, **kwargs) -> BusinessType:
        """"""

    @login_required
    def resolve_businesses(self, info, **kwargs) -> list:
        """"""

    @login_required
    def resolve_businesses_around_me(self, info, **kwargs) -> list:
        """
        Returns a list of businesses around the user's current location.
        """
        current_lat = kwargs.get("current_lat")
        current_long = kwargs.get("current_long")

        if not current_lat or not current_long:
            raise ValueError("Current latitude and longitude must be provided.")

        businesses = BusinessUtil.get_nearby_businesses(current_lat, current_long)
        paginated_businesses = PaginationUtil.paginate(
            businesses, kwargs.get("page_number", 1), kwargs.get("page_count", 10)
        )
        Query.pagination = paginated_businesses
        businesses = paginated_businesses.pop("items")
        return businesses

    @login_required
    def resolve_pagination(
        self, info
    ) -> dict:
        return Query.pagination
