from typing import List, Dict, Union

from django.db.models import Q
import graphene
from graphql_jwt.decorators import login_required

from apps.wallet.schema.types.wallet import (
    FinancialAssetType, TransactionType, WalletType,
)

from utils.helpers.exception import CustomException
from utils.helpers.logs import logger
from utils.helpers.kwargs import KwargUtil
from utils.helpers.pagination import PaginationUtil
from utils.wallet_utils.wallet import WalletUtil
from utils.wallet_utils.transactions import TransactionUtil


class Query(graphene.ObjectType):

    business_assets = graphene.List(
        FinancialAssetType,
        location=graphene.String(),
        business_id=graphene.String(),
        range=graphene.String(required=False),
        charge_rate=graphene.Float(required=False),
        page_count=graphene.Int(),
        page_number=graphene.Int()
    )
    transactions = graphene.List(
        TransactionType,
        wallet_id=graphene.String(),
        business_id=graphene.String(),
        id=graphene.String(),
        status=graphene.String(),
        search=graphene.String(),
        page_count=graphene.Int(),
        page_number=graphene.Int()
    )
    transaction = graphene.Field(
        TransactionType,
        transaction_id=graphene.String(required=True)
    )

    @login_required
    def resolve_business_assets(
        self, info, **kwargs
    ) -> Union[List[FinancialAssetType], None]:
        [
            business_id,
            location, range_val, charge_rate
        ] = KwargUtil.cherry_pick_data(
            kwargs, ["business_id", "location", "range", "charge_rate"]
        )
        _filter = {}
        if business_id:
            _filter["business__id"] = business_id
        if location:
            _filter["business__address__icontains"] = location
        if range_val:
            _filter["range"] = range_val
        if charge_rate:
            _filter["charge_rate"] = charge_rate
        assets = WalletUtil.get_financial_assets(**_filter)
        pagination_data = PaginationUtil.paginate(
            assets, kwargs.get("page_number", 1), kwargs.get("page_count", 10)
        )
        info.context.pagination = pagination_data
        assets = pagination_data.pop("items")
        return assets


    @login_required
    def resolve_transactions(self, info, **kwargs):
        """
        returns txns based on provided filters.
        if business_id is provided, returns all txns related to that business;
        otherwise, assumes that the current user is a client, who wants visibility to his own txns
        """
        user = info.context.user
        page_count = kwargs.pop("page_count", 10)
        page_number = kwargs.pop("page_number", 1)
        search_filter, _filter = Query._prepare_txn_filter(user, kwargs) or (Q(), {})
        txns = TransactionUtil.get_transaction(False, search_filter=search_filter, **_filter)
        paginated_txns = PaginationUtil.paginate(txns, page_number, page_count)
        txns = paginated_txns.pop("items", [])
        info.context.pagination = paginated_txns
        return txns


    @staticmethod
    def _prepare_txn_filter(user: "User", initial_data: dict):

        search_filter = Q()
        [
            wallet_id, business_id, status, search, _id
        ] = KwargUtil.cherry_pick_data(
            initial_data, ["wallet_id", "business_id", "status", "search", "id"]
        )
        _filter = {}
        if wallet_id:
            _filter["wallet_id"] = wallet_id

        if not business_id:
            _filter["client"] = user
        else:
            _filter["business__id"] = business_id
            _filter["client__isnull"] = False
        
        if _id:
            _filter["id"] = _id

        if status:
            _filter["status__icontains"] = status
        if search:
            search_filter &= (
                Q(txn_ref__icontains=search) |
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search) |
                Q(client__email__icontains=search) |
                Q(vendor__first_name__icontains=search) |
                Q(vendor__last_name__icontains=search) |
                Q(vendor__email__icontains=search) |
                Q(asset__business__name__icontains=search) |
                Q(description__icontains=search)
            )
        return search_filter, _filter

    @login_required
    def resolve_transaction(self, info, **kwargs):
        txn_id = kwargs.get("transaction_id")
        txn = TransactionUtil.get_transaction(id=txn_id)
        return txn


