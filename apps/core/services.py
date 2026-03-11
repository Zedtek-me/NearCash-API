from typing import Optional, Union, Type
from requests import request, Request
from googlemaps import Client as GoogleMapClient


from django.conf import settings
from django.utils import timezone

from interfaces.general.location import LocationInterface
from utils.helpers.logs import logger
from utils.helpers.exception import CustomException

from apps.auths.models import User
from apps.wallet.models import (
    Transaction, FinancialAsset
)
from apps.wallet.services import WalletService





class GeoapifyService(LocationInterface):
    """all things related to geoapify platform"""
    BASE_URL = settings.GEOAPIFY_BASE_URL
    API_KEY = settings.GEOAPIFY_API_KEY

    @classmethod
    def _initiate_request(
        cls, endpoint: str, params: Optional[dict] = None,
        payload: Optional[dict] = None, method: Optional[str] = "GET",
        extra_headers = None
    ) -> Optional[dict]:
        """request initiator"""
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        if method == "GET":
            response = request(
                method=method,
                url=f"{cls.BASE_URL}{endpoint}",
                params=params,
                headers=headers,
                timeout=10
            )
        else:
            response = request(
                method=method,
                url=f"{cls.BASE_URL}{endpoint}",
                json=payload,
                headers=headers,
                timeout=10
            )
        response = cls._parse_response(response)
        return response

    @classmethod
    def _parse_response(
        cls, response: Request
    ) -> Optional[dict]:
        _response = {}
        try:
            _response = response.json()
        except Exception as e:
            logger.exception(f"Error parsing response: {e}")
        return _response

    @classmethod
    def get_coordinate(cls, address: str, country_code: Optional[str] = "ng") -> dict:
        """address to coordinates"""
        endpoint = "/geocode/search"
        params = {
            "format": "json",
            "text": address,
            "filter": country_code,
            "lan": "en",
            "type": "street",
            "limit": 1,
            "apiKey": cls.API_KEY
        }
        try:
            response = cls._initiate_request(endpoint, params=params)
        except Exception as e:
            logger.exception(f"Error fetching coordinates: {e}")
            return {}
        data = response.get("results", [])
        first_street = data[0] if data else {}
        logger.info(f"Geoapify response: {response}\n\nFirst street data: {first_street}")
        coordinates = {
            "latitude": first_street.get("lat", 0.0),
            "longitude": first_street.get("lon", 0.0)
        }
        return coordinates

    @classmethod
    def get_routes(
        cls, start_coord: dict, end_coord: Optional[dict] = None,
        business: Optional[Type["Business"]] = None, mode: Optional[str] = "walk"
    ) -> dict:
        """
        gets routes between two coordinates.
        ideally, this gets the routes between the current user location and a business location.
        """
        endpoint = "/routing"
        if not (end_coord.get("longitude") and end_coord.get("latitude")) and not business:
            raise CustomException(
                message="Either end coordinates or business must be provided.",
            )
        if not end_coord.get("longitude") or not end_coord.get("latitude"):
            end_coord = {
                "latitude": business.geo_location.y,
                "longitude": business.geo_location.x
            }
        params = {
            "apiKey": cls.API_KEY,
            "mode": mode,
            "waypoints": f"{start_coord['latitude']},{start_coord['longitude']}|{end_coord['latitude']},{end_coord['longitude']}",
        }
        try:
            response = cls._initiate_request(endpoint, params=params)
        except Exception as e:
            logger.exception(f"Error fetching routes: {e}")
            response = {}
        return response


class OpenCageService(LocationInterface):
    """all things related to opencage platform"""
    # BASE_URL = settings.OPENCAGE_BASE_URL
    # API_KEY = settings.OPENCAGE_API_KEY

    @classmethod
    def get_coordinate(cls, address: str, country_code: Optional[str] = "ng") -> dict:
        """address to coordinates"""
        # endpoint = "/geocode/v1/json"
        # params = {
        #     "q": address,
        #     "key": cls.API_KEY,
        #     "countrycode": country_code,
        #     "limit": 1
        # }
        # response = cls._initiate_request(endpoint, params=params)
        # logger.info(f"OpenCage response: {response}")
        # return response

class GoogleMapServices(LocationInterface):

    @classmethod
    def get_coordinate(cls, address: str, country_code: Optional[str] = "ng") -> dict:
        """gets the coordinate of an address"""
        client = GoogleMapClient(key=settings.GOOGLE_API_KEY)
        results = client.geocode(address, components={"country": country_code})
        geometry = results[0].get("geometry", {}) if results else {}
        location = geometry.get("location", {})
        return {
            "latitude": location.get("lat", 0.0),
            "longitude": location.get("lng", 0.0)
        }


    @classmethod
    def get_routes(cls, start_coord, end_coord = None, business = None, mode = "walk"):...



class ClientService:

    @classmethod
    def initiate_transaction(
        cls, client: User, data: Union[dict, Type["InitiateTransactionInputType"]]
    ) -> Transaction:
        """initiates a transaction interest by a client to a vendor"""
        from utils.wallet_utils.transactions import TransactionUtil
        from utils.notifications.notifications import NotificationUtil
        from background_tasks.core.business import BusinessAsyncOperations


        [
            asset_id, vendor_id
        ] = data.get("asset_id"), data.get("vendor_id")
        fin_asset = WalletService.get_financial_asset(
            raise_exc=True, id=asset_id, business__id=vendor_id
        )
        txn_data: dict = cls._validate_txn_data(
            data, client, fin_asset
        )
        txn = TransactionUtil.create_transaction(**txn_data)
        # send websocket notification to vendor before other async operations
        NotificationUtil.send_socket_notification(txn)
        BusinessAsyncOperations.other_vendor_transaction_notif.delay(txn_id=txn.id)
        schedule_time = txn.date_created + timezone.timedelta(minutes=1)
        BusinessAsyncOperations.check_vendor_transaction_responsiveness.apply_async(
            eta=schedule_time,
            kwargs={"trxn_id": txn.id}
        )
        return txn

    @classmethod
    def _validate_withdrawal_amount(
        cls, asset, amount_to_withdraw: float
    ) -> bool:
        """
        validates that the amount to withdraw is
        within the range of the financial asset.
        """
        if "+" in asset.range:
            _range = asset.range
            amount = float(str(_range).replace("+", ""))
            if amount_to_withdraw < amount:
                return False
            return True
        min_amount, max_amount = asset.range.split("-")
        min_amount, max_amount = float(min_amount), float(max_amount)
        if not (min_amount <= amount_to_withdraw <= max_amount):
            return False
        return True

    @classmethod
    def prepare_client_txn_data(
        cls, client: User, data: Union[dict, Type["InitiateTransactionInputType"]],
        asset: FinancialAsset, **kwargs
    ) -> dict:
        """prepares a dict of data to create a transaction"""
        from utils.wallet_utils.transactions import TransactionUtil

        txn_ref = TransactionUtil.generate_txn_reference()
        txn_data = {
            "txn_ref": txn_ref,
            "client": client,
            "vendor": (asset.business and asset.business.owner) or None,
            "asset": asset,
            "amount": data.get("amount_to_withdraw"),
            "charge": asset.charge_rate,
            "currency": asset.currency_code,
            "business": asset.business,
            "collection_mode": data.get("collection_mode").value,
            "extra_charge": kwargs.get("extra_charge", {}),
            "txn_location": data.get("collection_location"),
            "description": f"Withdrawal transaction initiated by {client.email}.",
            "category": "client_cash_withdrawal",
            "meta": {
                "client_current_location": {
                    "longitude": data.get("client_current_coordinates").x,
                    "latitude": data.get("client_current_coordinates").y
                }
            }
        }
        return txn_data

    @classmethod
    def _validate_txn_data(
        cls, data: Union[dict, Union[dict, Type["InitiateTransactionInputType"]]],
        client: User, asset: FinancialAsset
    ) -> Optional[dict]:
        """validates all transaction data"""
        from utils.core_utils.business_utils import BusinessUtil
        from apps.core.constants import MEET_UP

        txn_policy = BusinessUtil.fetch_business_txn_policy_for_current_client(
            client, asset.business.id
        )
        amount_to_withdraw = data.get("amount_to_withdraw")
        cash_collection_mode = data.get("collection_mode").value
        extra_charge = 0.0
        if not cls._validate_withdrawal_amount(asset, amount_to_withdraw):
            raise CustomException(
                message=f"Amount to withdraw {amount_to_withdraw} is not within the range of the selected asset: {asset.range}."
            )
        if txn_policy and cash_collection_mode not in txn_policy.cash_collection_mode:
            raise CustomException(
                message=f"This vendor doesn't support the chosen collection mode {cash_collection_mode}."
            )
        if cash_collection_mode == MEET_UP:
            extra_charge = (txn_policy and txn_policy.meet_up_charge) or 0.0
        extra_charge_data = {
            "amount": extra_charge,
            "reason": "meet up charge"
        } if extra_charge > 0 else {}
        return cls.prepare_client_txn_data(
            client, data, asset, extra_charge=extra_charge_data
        )
