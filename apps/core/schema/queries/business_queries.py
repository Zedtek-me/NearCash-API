import graphene
from graphql_jwt.decorators import login_required

from django.db.models import Q, F

from apps.core.models import Business
from apps.core.schema.types.business_types import (
    BusinessType, RouteInputType
)
from apps.core.constants import LOCATION_SERVICES

from utils.core_utils.business_utils import BusinessUtil, GeolocationUtils
from utils.helpers.kwargs import KwargUtil
from utils.helpers.pagination import PaginationUtil
from utils.helpers.logs import logger
from utils.helpers.exception import CustomException


class Query(graphene.ObjectType):
    pagination = graphene.Field(graphene.JSONString())
    business = graphene.Field(
        BusinessType,
        business_id=graphene.String(required=True)
    )
    businesses = graphene.List(
        BusinessType,
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

    routes = graphene.Field(
        graphene.JSONString,
        coordinates=RouteInputType(required=True),
        business_id=graphene.String(),
    )

    @login_required
    def resolve_business(self, info, **kwargs) -> BusinessType:
        """single business"""
        return BusinessUtil.get_business({"id": kwargs.get("business_id")})

    @login_required
    def resolve_businesses(self, info, **kwargs) -> list:
        """all businesses"""
        page_count = kwargs.pop("page_count", 10)
        page_no = kwargs.pop("page_number", 1)

        businesses = BusinessUtil.get_businesses(
            info.context.user, kwargs
        )
        paginated = PaginationUtil.paginate(
            businesses, page_no, page_count
        )
        Query.pagination = paginated
        return paginated.pop("items")


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
    def resolve_routes(
        self, info, **kwargs
    ):
        """
        Gets routes between two waypoints.
        If business_id is provided, it fetches the business location.
        """
        coordinates = kwargs.get("coordinates")
        start_coord = {
            "longitude": coordinates.get("start_long"),
            "latitude": coordinates.get("start_lat")
        }
        end_coord = {
            "longitude": coordinates.get("end_long"),
            "latitude": coordinates.get("end_lat")
        }
        business_id = kwargs.get("business_id")

        business = BusinessUtil.get_business({"id": business_id})
        geoapify = LOCATION_SERVICES.get("geoapify")
        routes = GeolocationUtils(geoapify).get_routes(
            start_coord=start_coord,
            end_coord= end_coord,
            business=business,
        )
        logger.info(f"Routes response: {routes}")
        return routes

    @login_required
    def resolve_pagination(
        self, info
    ) -> dict:
        return Query.pagination
