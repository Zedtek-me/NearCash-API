import graphene
from graphene_django import DjangoObjectType

from apps.wallet.models import (
    Wallet, FinancialAsset, Transaction
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
