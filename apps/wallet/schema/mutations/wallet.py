import graphene
from graphql_jwt.decorators import login_required
from django.db import transaction

from apps.wallet.schema.types.wallet import (
    AssetInputType, FinancialAssetType,
    TransactionType, TxnStatusType
)

from utils.helpers.logs import logger
from utils.helpers.exception import CustomException
from utils.wallet_utils.wallet import WalletUtil
from utils.wallet_utils.transactions import TransactionUtil


class CreateFinancialAsset(graphene.Mutation):
    """Mutation to create a financial asset."""

    message = graphene.String()
    assets = graphene.List(FinancialAssetType)

    class Arguments:
        business_id = graphene.String(required=True)
        data = graphene.List(AssetInputType, required=True)

    @login_required
    @transaction.atomic
    def mutate(self, info, **kwargs):
        user = info.context.user
        data = kwargs.get("data")
        business = CreateFinancialAsset._validate_business_by_id(kwargs.get("business_id"))
        if user.id != business.owner.id:
            raise CustomException(
                "You do not have permission to create financial assets for this business."
            )
        assets = WalletUtil.create_financial_assets(
            business=business,
            data=data
        )
        return CreateFinancialAsset(
            message="Financial asset created successfully.",
            assets=assets
        )

    @classmethod
    def _validate_business_by_id(cls, business_id):
        from apps.core.models import Business

        business = Business.objects.filter(id=business_id).first()
        if not business:
            raise CustomException("Business not found.")
        return business


class UpdateFinancialAsset(graphene.Mutation):
    message = graphene.String()
    asset = graphene.Field(FinancialAssetType)

    class Arguments:
        asset_id = graphene.String(required=True)
        data = graphene.List(AssetInputType, required=True)

    @login_required
    @transaction.atomic
    def mutate(self, info, **kwargs):
        """updates existing asset with new values"""

class UpdateTxnStatus(graphene.Mutation):
    """
    allows both the client and the vendor update a txn status
    either accept, decline or reject.
    """

    message = graphene.String()
    transaction = graphene.Field(TransactionType)

    class Arguments:
        txn_id = graphene.String(required=True)
        status = TxnStatusType(required=True)

    @login_required
    def mutate(self, info, **kwargs):
        """update txn"""

        txn = TransactionUtil.update_txn_status(
            info.context.user, kwargs
        )
        return UpdateTxnStatus(
            message="Transaction successfully updated!",
            transaction=txn
        )

class Mutation(graphene.ObjectType):
    create_financial_asset = CreateFinancialAsset.Field(
        description="Create a financial asset for a business."
    )
    update_financial_asset = UpdateFinancialAsset.Field(
        description="Update an existing financial asset."
    )
    update_transaction_status = UpdateTxnStatus.Field(
        description="Updates a transaction status, and publish notification if needed"
    )
