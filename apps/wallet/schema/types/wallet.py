import graphene
from graphene_django import DjangoObjectType

from apps.wallet.models import (
    Wallet, FinancialAsset, Transaction
)
from apps.wallet.constants import (
    IN_PROGRESS, INITIATED, DECLINED, CANCELLED,
    CARD, BANK_TRANSFER
)

from apps.core.schema.types.business_types import (
    PointFieldType, CashCollectionModes
)

from utils.helpers.types import PaginationType

class FinancialAssetType(DjangoObjectType):
    class Meta:
        model = FinancialAsset
        fields = "__all__"

class WalletType(DjangoObjectType):
    class Meta:
        model = Wallet
        fields = "__all__"

class TransactionType(DjangoObjectType):
    awaiting_transfer = graphene.Boolean()

    class Meta:
        model = Transaction
        fields = "__all__"

    def resolve_awaiting_transfer(self, info):
        virtual_account_info = self.meta.get("virtual_account", {})
        transfer_status = virtual_account_info.get("transfer_status", "")
        trxn_status = self.status
        return trxn_status == IN_PROGRESS and self.transfer_mode == BANK_TRANSFER and transfer_status != "success"


class TransactionListType(graphene.ObjectType):
    transactions = graphene.List(TransactionType)
    pagination = graphene.Field(PaginationType)


class AssetInputType(graphene.InputObjectType):
    """
    Input type for creating or updating financial assets.
    """
    id = graphene.String(required=False)
    range = graphene.String(required=True)
    charge_rate = graphene.Float(required=True)



class TransferModeEnum(graphene.Enum):
    CARD = CARD
    BANK_TRANSFER = BANK_TRANSFER

class InitiateTransactionInputType(graphene.InputObjectType):
    vendor_id = graphene.String(required=True)
    asset_id = graphene.String(required=True)
    amount_to_withdraw = graphene.Float(required=True)
    client_current_coordinates = PointFieldType(required=True)
    collection_mode = CashCollectionModes(required=True)
    transfer_mode = TransferModeEnum(required=True)
    collection_location = graphene.String(required=False)


class TxnStatusType(graphene.Enum):
    IN_PROGRESS = IN_PROGRESS
    CANCELLED = CANCELLED
    DECLINED = DECLINED
    INITIATED = INITIATED
