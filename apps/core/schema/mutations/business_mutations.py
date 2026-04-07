import graphene
import logging
from graphql_jwt.decorators import login_required
from django.db import transaction

from apps.core.schema.types.business_types import (
    BusinessType, CreateBusinessInputType, UpdateBusinessInputType,
    BusinessClientCategoryType, CreateClientCategoryInputType,
    AddClientsToCategoryInputType, BusinessClientType, BusinessTransactionPolicyType,
    CreateTransactionPolicyInputType
)
from apps.wallet.schema.types.wallet import (
    AssetInputType,
    InitiateVendorToVendorTransactionInputType,
    TransactionType
)

from utils.core_utils.business_utils import BusinessUtil
from utils.core_utils.core_utils import CoreUtil
from utils.wallet_utils.wallet import WalletUtil
from utils.helpers.exception import CustomException

logger = logging.getLogger("nearcash")

class CreateBusiness(graphene.Mutation):
    """Creates a new business for the user."""

    message = graphene.String()
    business = graphene.Field(BusinessType)

    class Arguments:
        data = CreateBusinessInputType(required=True)
        financial_assets = graphene.List(
            AssetInputType, required=False
        )

    @login_required
    @transaction.atomic
    def mutate(self, info, **kwargs):
        from utils.user_utils.users import UserUtil

        user = info.context.user
        data = kwargs.get("data", {})
        financial_assets = kwargs.get("financial_assets", [])
        business_data = UserUtil.prepare_business_data(data)
        business = BusinessUtil.create_business(user, business_data)
        if financial_assets:
            WalletUtil.create_or_update_financial_assets(
                business, financial_assets
            )
        return CreateBusiness(
            message="Business created successfully.",
            business=business
        )

class UpdateBusiness(graphene.Mutation):
    message = graphene.String()
    business = graphene.Field(BusinessType)

    class Arguments:
        business_id = graphene.String(required=True)
        update_data = UpdateBusinessInputType(required=False)
        financial_assets = graphene.List(
            AssetInputType, required=False
        )

    @login_required
    @transaction.atomic
    def mutate(self, info, **kwargs):
        """updates a business"""
        user = info.context.user

        business_id = kwargs.get("business_id")
        business = BusinessUtil.get_business({"id": business_id, "owner": user})
        if not business:
            raise CustomException(
                message=f"invalid business id: {business_id}"
            )
        business = BusinessUtil.update_business(
            business, kwargs.get("update_data"),
            financial_assets=kwargs.get("financial_assets", [])
        )
        return UpdateBusiness(
            message="Business successfully updated",
            business=business
        )

class CreateClientCategory(graphene.Mutation):
    message = graphene.String()
    category = graphene.Field(BusinessClientCategoryType)

    class Arguments:
        business_id = graphene.String(required=True)
        category_info = CreateClientCategoryInputType(required=True)

    @login_required
    @transaction.atomic
    def mutate(self, info, **kwargs):
        """creates a client category for the business"""
        user = info.context.user
        business_id = kwargs.get("business_id")
        category_info = kwargs.get("category_info")
        business = BusinessUtil.get_business({"id": business_id, "owner": user})
        if not business:
            raise CustomException(f"invalid business id provided for user: {user.email}")
        category = CoreUtil.create_business_client_category(
            business, category_info
        )
        return CreateClientCategory(
            message="Client category successfully created",
            category=category
        )

class AddClientsToCategory(graphene.Mutation):
    message = graphene.String()
    category_clients = graphene.List(BusinessClientType)

    class Arguments:
        data = AddClientsToCategoryInputType(required=True)

    @login_required
    @transaction.atomic
    def mutate(self, info, **kwargs):
        user = info.context.user
        data = kwargs.get("data")
        category_clients = CoreUtil.add_client_to_category(
            user, data
        )
        return AddClientsToCategory(
            message="client successfully added to category!",
            category_clients=category_clients
        )


class CreateTransactionPolicy(graphene.Mutation):

    message = graphene.String()
    policy = graphene.Field(BusinessTransactionPolicyType)

    class Arguments:
        business_id = graphene.String(required=True)
        data = CreateTransactionPolicyInputType(required=True)

    @login_required
    @transaction.atomic
    def mutate(self, info, **kwargs):
        user = info.context.user
        business_id = kwargs.get("business_id")
        data = kwargs.get("data")
        business = BusinessUtil.get_business({"id": business_id, "owner": user})
        if not business:
            raise CustomException("Invalid business ID given!")
        policy = CoreUtil.create_business_txn_policy(
            business, data
        )
        return CreateTransactionPolicy(
            message="Transaction policy successfully created!",
            policy=policy
        )


class UpdateTransactionPolicy(graphene.Mutation):

    message = graphene.String()
    policy = graphene.Field(BusinessTransactionPolicyType)

    class Arguments:
        policy_id = graphene.String(required=True)
        data = CreateTransactionPolicyInputType(required=True)

    @login_required
    @transaction.atomic
    def mutate(self, info, **kwargs):
        user = info.context.user
        policy_id: int | str = kwargs.get("policy_id") or ""
        data: dict = kwargs.get("data") or {}
        policy = CoreUtil.update_business_txn_policy(
            user, policy_id, data
        )
        return UpdateTransactionPolicy(
            message="Transaction policy successfully updated!",
            policy=policy
        )


class AcceptTransactionOpportunity(graphene.Mutation):
    message = graphene.String()

    class Arguments:
        txn_id = graphene.String()
        txn_ref = graphene.String()
        business_id = graphene.String()

    @login_required
    def mutate(self, info, **kwargs):
        handled = BusinessUtil.accept_transaction_opportunity(**kwargs)
        if handled and handled is True:
            return AcceptTransactionOpportunity(
                message="opportunity_ack"
            )
        return AcceptTransactionOpportunity(
            message="opportunity_lost"
        )


class InitiateVendorToVendorTransaction(graphene.Mutation):
    message = graphene.String()
    txn = graphene.Field(TransactionType)

    class Arguments:
        data = InitiateVendorToVendorTransactionInputType(required=True)

    @login_required
    @transaction.atomic
    def mutate(self, info, **kwargs):
        user = info.context.user
        data: InitiateVendorToVendorTransactionInputType = kwargs.get("data")
        txn = BusinessUtil.initiate_vendor_to_vendor_transaction(user, data)
        return InitiateVendorToVendorTransaction(
            message="Transaction initiated successfully.",
            txn=txn
        )

class Mutation(graphene.ObjectType):
    create_business = CreateBusiness.Field(description="Create a new business for the user.")
    update_business = UpdateBusiness.Field(description="Updates an existing business")
    create_client_category = CreateClientCategory.Field(description="Creates a client category")
    add_clients_to_a_category = AddClientsToCategory.Field(
        description="Adds multiple client to a business category"
    )
    create_transaction_policy = CreateTransactionPolicy.Field(
        description="Creates a transaction policy for the given business"
    )
    update_transaction_policy = UpdateTransactionPolicy.Field(
        description="Updates a transaction policy for the given business"
    )
    accept_transaction_opportunity = AcceptTransactionOpportunity.Field(
        description="Accepts a transaction opportunity broadcastd by the system"
    )
    initiate_vendor_to_vendor_transaction = InitiateVendorToVendorTransaction.Field(
        description="Initiates a vendor to vendor transaction"
    )
