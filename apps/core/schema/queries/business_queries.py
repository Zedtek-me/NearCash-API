import graphene
from graphql_jwt.decorators import login_required

from django.db.models import Q, F

from apps.core.models import Business
from apps.core.schema.types.business_types import (
    BusinessType, RouteInputType, BusinessTransactionPolicyType,
    CashCollectionModes, BusinessClientType, AnalyticsType
)
from apps.core.constants import LOCATION_SERVICES

from apps.auths.schema.types.auth_types import UserType

from utils.core_utils.business_utils import BusinessUtil, GeolocationUtils
from utils.core_utils.core_utils import CoreUtil
from utils.helpers.kwargs import KwargUtil
from utils.helpers.pagination import PaginationUtil
from utils.helpers.logs import logger
from utils.helpers.exception import CustomException


class Query(graphene.ObjectType):
    pagination = None

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
    business_transaction_policy_for_user = graphene.Field(
        BusinessTransactionPolicyType,
        business_id=graphene.String(required=True),
        description="Returns a transaction policy that should be applied to the current client"
    )
    business_transaction_policies = graphene.List(
        BusinessTransactionPolicyType, name=graphene.String(),
        id=graphene.String(), meet_up_charge=graphene.Float(),
        business_id=graphene.String(required=True),
        cash_collection_mode=CashCollectionModes(), page_number=graphene.Int(),
        page_count=graphene.Int()
    )
    business_transaction_policy = graphene.Field(
        BusinessTransactionPolicyType, id=graphene.String(required=True),
        business_id=graphene.String(required=True)
    )
    business_clients = graphene.List(
        BusinessClientType,
        category_id=graphene.String(),
        business_id=graphene.String(),
        page_count=graphene.Int(default_value=10),
        page_number=graphene.Int(default_value=1)
    )

    analytics = graphene.Field(
        AnalyticsType, business_id=graphene.String(),
        user_type=graphene.String(required=True)
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
        businesses = paginated.pop("items")
        return businesses


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
        return routes

    @login_required
    def resolve_business_transaction_policy_for_user(self, info, **kwargs):
        """gets the policy registered for the current user"""
        user = info.context.user
        policy = BusinessUtil.fetch_business_txn_policy_for_current_client(
            user, kwargs.get("business_id")
        )
        return policy

    @login_required
    def resolve_business_transaction_policies(
        self, info, **kwargs
    ):
        user = info.context.user
        business_id = kwargs.pop("business_id", None)
        page_no = kwargs.get("page_number", 1)
        page_count = kwargs.get("page_count", 10)

        business = BusinessUtil.get_business({"id": business_id, "owner": user})
        if not business:
            raise CustomException(
                message=f"invalid business id provided for owner: {user.email}!"
            )
        policies = CoreUtil.fetch_business_txn_policy(business_id, kwargs, only_one=False)
        paginated = PaginationUtil.paginate(
            policies, page_no, page_count
        )
        Query.pagination = paginated
        policies = paginated.pop("items")
        return policies

    @login_required
    def resolve_business_transaction_policy(
        self, info, **kwargs
    ):
        _id = kwargs.get("id")
        business_id = kwargs.get("business_id")
        return CoreUtil.fetch_business_txn_policy(business_id, {"id": _id})

    @login_required
    def resolve_business_clients(self, info, **kwargs):
        """
        returns clients that have patronized a business.
        """
        user = info.context.user
        page_count = kwargs.pop("page_count", 10)
        page_number = kwargs.pop("page_number", 1)
        clients = CoreUtil.get_business_clients(user, kwargs)

        paginated = PaginationUtil.paginate(
            clients, page_number=page_number, page_size=page_count
        )
        Query.pagination = paginated
        return paginated.pop("items")

    @login_required
    def resolve_analytics(self, info, **kwargs):
        """
        resolves the analytics for a business and its transactions
        """
        user = info.context.user
        buz_id = kwargs.get("business_id")
        user_type = kwargs.get("user_type")
        return BusinessUtil.get_txn_analytics(user, user_type, buz_id)

    @login_required
    def resolve_pagination(
        self, info
    ) -> dict:
        return Query.pagination
