import graphene
from django.contrib.gis.geos import Point

from graphene_django import DjangoObjectType
from apps.core.models import (
    Business, BusinessClientCategory, BusinessTransactionPolicy,
    BusinessClient
)
from apps.core.constants import (
    MEET_UP, STORE_WALK_IN, MEET_UP_AND_STORE_WALK_IN
)

from utils.helpers.logs import logger
from utils.helpers.types import PaginationType

class PointFieldType(graphene.types.Scalar):
    """Custom GraphQL Scalar for GeoDjango PointField"""

    @staticmethod
    def serialize(value: Point):
        return {
            "latitude": value.y,
            "longitude": value.x
        }

    @staticmethod
    def parse_literal(node):
        if isinstance(node, (graphene.InputObjectType, dict)):
            return Point(node["longitude"], node["latitude"])

    @staticmethod
    def parse_value(value):
        if isinstance(value, dict) and "latitude" in value and "longitude" in value:
            return Point(value["longitude"], value["latitude"])
        return None


class BusinessType(DjangoObjectType):
    location = PointFieldType()
    distance = graphene.Float()
    nearest = graphene.Boolean()
    business_policy_for_current_user = graphene.Field(lambda: BusinessTransactionPolicyType)

    class Meta:
        model = Business
        exclude = ["geo_location"]

    def resolve_location(self, info):
        return self.geo_location

    def resolve_distance(self, info):
        if hasattr(self, 'distance'):
            # resolve the distance in kilometers
            return float(round(self.distance.km, 2))
        return None

    def resolve_nearest(self, info):
        if hasattr(self, "nearest") and self.nearest is True:
            return self.nearest
        return False

    def resolve_business_policy_for_current_user(self, info):
        from utils.core_utils.business_utils import BusinessUtil

        user = info.context.user
        user_type: str = ((user.is_authenticated and user.meta.get("user_type")) or "").lower()
        if user.is_authenticated and user_type == "client":
            return BusinessUtil.fetch_business_txn_policy_for_current_client(user, self.id)
        return None


class BusinessListType(graphene.ObjectType):
    businesses = graphene.List(BusinessType)
    pagination = graphene.Field(PaginationType)

class BusinessClientCategoryType(DjangoObjectType):

    class Meta:
        model = BusinessClientCategory
        fields = "__all__"

class BusinessTransactionPolicyType(DjangoObjectType):
    class Meta:
        model = BusinessTransactionPolicy
        fields = "__all__"

class BusinessClientType(DjangoObjectType):
    class Meta:
        model = BusinessClient
        fields = "__all__"


class CreateBusinessInputType(graphene.InputObjectType):
    business_name = graphene.String(required=True)
    description = graphene.String(required=False)
    country = graphene.String(required=False)
    parent_business_id = graphene.String(required=False)
    address = graphene.String(required=False)
    business_type = graphene.String(required=True)

class UpdateBusinessInputType(CreateBusinessInputType):
    is_online = graphene.Boolean(required=False)
    business_name = graphene.String(required=False)
    address = graphene.String(required=False)

class RouteInputType(graphene.InputObjectType):
    start_long = graphene.Float(required=True)
    start_lat = graphene.Float(required=True)
    end_long = graphene.Float(required=False)
    end_lat = graphene.Float(required=False)

class CreateClientCategoryInputType(graphene.InputObjectType):
    name = graphene.String(required=True)
    description = graphene.String()
    transaction_policy_id = graphene.String()

class AddClientsToCategoryInputType(graphene.InputObjectType):
    client_ids = graphene.List(graphene.String, required=True)
    category_id = graphene.String(required=True)
    business_id = graphene.String(required=True)

class CashCollectionModes(graphene.Enum):
    MEET_UP = MEET_UP
    STORE_WALK_IN = STORE_WALK_IN
    MEET_UP_AND_STORE_WALK_IN = MEET_UP_AND_STORE_WALK_IN


class CreateTransactionPolicyInputType(graphene.InputObjectType):
    name = graphene.String()
    description = graphene.String()
    cash_collection_mode = CashCollectionModes()
    meet_up_charge = graphene.Float()


class AnalyticsType(graphene.ObjectType):
    total_transactions = graphene.Int()
    fulfilled_transactions = graphene.Int()
    current_month_transactions = graphene.Int()
    total_transaction_value = graphene.Float()
    current_month_transaction_value = graphene.Float()
    percentage_reduction_from_past_month = graphene.Float()
    total_charges_plus_extra = graphene.Float()
    extra_charges = graphene.Float()
