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

class UpdateBusinessInputType(CreateBusinessInputType):
    business_name = graphene.String(required=False)

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


class BusinessAnalyticsType(graphene.ObjectType):
    total_transactions = graphene.Float()
    current_month_transactions = graphene.Float()
