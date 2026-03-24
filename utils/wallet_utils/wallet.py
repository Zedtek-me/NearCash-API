from django.db.models import Q, F
from typing import Optional, Union, List, Dict

from utils.helpers.logs import logger
from utils.helpers.exception import CustomException

from apps.core.models import Business
from apps.wallet.models import FinancialAsset, Wallet

class WalletUtil:
    """all utilities related to wallet operations"""

    @classmethod
    def create_or_update_financial_assets(
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
            if asset_data.get("id") is not None:
                if not (asset := FinancialAsset.objects.filter(
                    id=asset_data["id"],
                    business=business
                ).first()):
                    raise CustomException(
                        "Financial asset with the provided ID does not exist for this business."
                    )
                asset.range = asset_data["range"]
                asset.charge_rate = asset_data["charge_rate"]
            else:
                asset = FinancialAsset(
                    business=business,
                    **asset_data
                )
            assets.append(asset)
        assets = FinancialAsset.objects.bulk_create(
            assets, update_conflicts=True,
            update_fields=["charge_rate"],
            unique_fields=["range", "business"]
        )
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


    @classmethod
    def get_wallet(
        cls, filter_params: dict, raise_exception: bool = True
    ) -> Wallet:
        """
        fetches wallet matching the given params
        """
        wallet = Wallet.objects.filter(**filter_params).first()
        if not wallet and raise_exception:
            raise CustomException(
                message="No wallet found with the provided filter params!"
            )
        return wallet


    @classmethod
    def create_wallet(
        cls, params: dict
    ) -> Wallet:
        """creates a wallet"""
        currency = params.pop("currency", None)
        wallet = Wallet.objects.create(**params)
        if not currency:
            # default currency to NGN for now, pending future implementation of wallet type
            currency = "NGN"
        wallet.currency = currency
        wallet.save()
        return wallet

        
