from typing import Optional, Union
from requests import request, Request

from django.conf import settings

from interfaces.general.location import LocationInterface
from utils.helpers.logs import logger

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
        logger.info(f"Geoapify response: {response}")
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
