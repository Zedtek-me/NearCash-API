import graphene

from graphene_django import DjangoObjectType
from apps.core.models import Business

class BusinessType(DjangoObjectType):
    class Meta:
        model = Business
        fields = "__all__"


class CreateBusinessInputType(graphene.InputObjectType):
    business_name = graphene.String(required=True)
    description = graphene.String(required=False)
    country = graphene.String(required=False)
    parent_business_id = graphene.String(required=False)
    address = graphene.String(required=False)
