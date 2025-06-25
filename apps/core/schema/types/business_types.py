import graphene
from django.contrib.gis.geos import Point

from graphene_django import DjangoObjectType
from apps.core.models import Business

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

    class Meta:
        model = Business
        exclude = ["_location"]

    def resolve_location(self, info):
        return self._location

class CreateBusinessInputType(graphene.InputObjectType):
    business_name = graphene.String(required=True)
    description = graphene.String(required=False)
    country = graphene.String(required=False)
    parent_business_id = graphene.String(required=False)
    address = graphene.String(required=False)
