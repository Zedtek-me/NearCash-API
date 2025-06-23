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


class Query(graphene.ObjectType):
    pagination = graphene.JSONString()

    business_assets = graphene.List(
        FinancialAssetType,
        location=graphene.String(),
        business_id=graphene.String(),
        range=graphene.String(required=False),
        charge_rate=graphene.Float(required=False),
        page_count=graphene.Int(),
        page_number=graphene.Int()
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
        Query.pagination = pagination_data
        assets = pagination_data.pop("items")
        return assets

    @login_required
    def resolve_pagination(
        self, info
    ) -> Union[dict, None]:
        return Query.pagination
