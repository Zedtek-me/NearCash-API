from typing import Optional, Union, Type

from apps.wallet.models import FinancialAsset, Transaction

from utils.helpers.exception import CustomException

from apps.wallet.constants import EXCHANGE_RATE_SERVICES

class WalletService:

    @classmethod
    def get_financial_asset(
        cls, raise_exc: Optional[bool] = False, **kwargs
    ) -> Optional[FinancialAsset]:
        """returns a financial asset object"""
        fin_asset = FinancialAsset.objects.filter(**kwargs).first()
        if not fin_asset and raise_exc:
            raise CustomException("Financial asset not found.")
        return fin_asset


    @classmethod
    def get_exchange_rate_service(
        cls, provider: str = "twelvedata"
    ) -> dict:
        """
        returns the credentials for an exchange rate provider
        """
        return EXCHANGE_RATE_SERVICES.get(provider.upper(), {})
