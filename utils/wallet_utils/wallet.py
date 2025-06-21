from django.db.models import Q, F
from typing import Optional, Union, List, Dict

from utils.helpers.logs import logger
from utils.helpers.exception import CustomException

from apps.core.models import Business
from apps.wallet.models import FinancialAsset

class WalletUtil:
    """all utilities related to wallet operations"""

    @classmethod
    def create_financial_assets(
        cls, business: Business, data: List[Dict[str, Union[str, float]]]
    ) -> List[Dict[str, Union[str, float]]]:
        """
        Creates financial assets for a business.
        
        :param business_id: The ID of the business.
        :param data: A list of dictionaries containing asset data.
        :return: A list of created financial assets.
        """
        assets = []
        for asset_data in data:
            asset = FinancialAsset(
                business=business,
                **asset_data
            )
            assets.append(asset)
        assets = FinancialAsset.objects.bulk_create(assets)
        return assets

    @classmethod
    def get_financial_assets(
        cls, search_filter: Optional[Q]= Q(), **filters: Dict[str, Union[str, float]]
    ) -> Union[
        List[FinancialAsset], None
    ]:
        """lists financial assets based on provided filters"""
        return FinancialAsset.objects.filter(
            search_filter,
            **filters
        )
