import graphene
from graphene_django import DjangoObjectType


class DelayedTransactionResponseEnum(graphene.Enum):
    WAIT = "wait_on_vendor"
    SYSTEM_SEARCH = "system_search"
    CANCEL = "cancel"


class DelayedTransactionResponseInputType(graphene.InputObjectType):
    txn_id = graphene.String(required=True)
    decision = DelayedTransactionResponseEnum()
