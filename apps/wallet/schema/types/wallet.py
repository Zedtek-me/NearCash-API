import graphene
from graphene_django import DjangoObjectType

from apps.wallet.models import (
    Wallet, FinancialAsset, Transaction
)

from apps.core.schema.types.business_types import (
    PointFieldType, CashCollectionModes
)


class FinancialAssetType(DjangoObjectType):
    class Meta:
        model = FinancialAsset
        fields = "__all__"

class WalletType(DjangoObjectType):
    class Meta:
        model = Wallet
        fields = "__all__"

class TransactionType(DjangoObjectType):
    class Meta:
        model = Transaction
        fields = "__all__"


class AssetInputType(graphene.InputObjectType):
    """
    Input type for creating or updating financial assets.
    """
    range = graphene.String(required=True)
    charge_rate = graphene.Float(required=True)


class InitiateTransactionInputType(graphene.InputObjectType):
    vendor_id = graphene.String(required=True)
    asset_id = graphene.String(required=True)
    amount_to_withdraw = graphene.Float(required=True)
    client_current_coordinates = PointFieldType(required=True)
    collection_mode = CashCollectionModes(required=True)
    collection_location = graphene.String(required=False)
