from typing import Optional, Union, Type

from apps.wallet.models import FinancialAsset

from utils.helpers.exception import CustomException
from utils.helpers.logs import logger
from utils.https.client import Client

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





class CurrencyService:
    """
    handles all things related to currencies
    including conversion and others.
    """

    @classmethod
    def convert_tendered_amount_to_dest_curr(
        cls, source_amount_tendered: float | int,
        source_curr: str | None = None,
        destination_curr: str | None = None
    ) -> int | float:
        """
        helps determine the equivalent destination amount
        from a tendered currency
        """
        if not (source_curr and destination_curr):
            raise CustomException(
                message="Source and destination currencies must be provided!"
            )
        exchange_rate = cls.get_exchange_rate(
            source_curr, destination_curr
        )
        if not exchange_rate or exchange_rate <= 0:
            exchange_rate = cls._retry_fetch_exchange_rate(
                source_curr, destination_curr
            )
        if not exchange_rate:
            raise CustomException(
                message="could not retrieve exchange rate at the moment!"
            )
        destination_equiv = float(source_amount_tendered // exchange_rate)
        return destination_equiv


    @classmethod
    def get_exchange_rate_service(
        cls, provider: str = "twelvedata"
    ) -> dict:
        """
        returns the credentials for an exchange rate provider
        """
        return EXCHANGE_RATE_SERVICES.get(provider.upper(), {})


    @classmethod
    def get_exchange_rate(
        cls, source_curr: str, destination_curr: str,
        provider: Optional[str] = None
    ) -> float:
        """
        returns the exchange rate for the given
        currency pairs
        """
        if not provider:
            # defaults to twelvedata exchange rate api
            provider = "twelvedata"
        credentials = cls.get_exchange_rate_service(provider)
        url = credentials.get("url")
        headers = credentials.get("default_headers", {})
        client = Client(url, headers=headers)
        response = client.get(
                    "/exchange_rate",
                    params={"symbol": f"{destination_curr}/{source_curr}"}
                )
        logger.debug(f"exchange rate response::: {response}")
        rate: float = response.get("rate", 0.0)
        if not rate:
            return 0.0
        return float(rate)


    @classmethod
    def _retry_fetch_exchange_rate(
        cls, source_curr: str, destination_curr: str,
        provider: str = "twelvedata", retry_count: int = 3,
    ) -> float:
        """
        performs a refetch of excchange rate data
        for a given {{ retry }} count
        """
        counter = 0
        exchange_rate = 0
        while (retry_count > counter):
            exchange_rate = cls.get_exchange_rate(
                source_curr,
                destination_curr,
                provider
            )
            if exchange_rate:
                return exchange_rate
            # else, switch provider here...
            provider = ""
            counter += 1
        return exchange_rate
