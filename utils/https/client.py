from django.conf import settings
import requests
from interfaces.general.http import HttpInterface

from utils.helpers.logs import logger

from .parsers import HttpPerser

class Client(HttpInterface):

    def __init__(self, base_url: str | None = None, headers: dict | None = None):
        self.base_url = base_url
        self.headers = headers
        self.parser = HttpPerser

    def get(self, endpoint: str, headers: dict | None = None, params: dict | None = None) -> dict:
        if headers:
            self.headers = {
                **(self.headers or {}),
                **headers
            }
        endpoint = f"{self.base_url}{endpoint}"
        response = requests.request(
            "GET", url=endpoint, params=params,
            headers=self.headers, timeout=settings.DEFAULT_HTTP_TIMEOUT
        )
        return self.parser.parse_response(response)


    def post(self, endpoint: str, headers: dict | None = None, payload: dict | None = None) -> dict:
        if headers:
            self.headers = {
                **(self.headers or {}),
                **headers
            }
        endpoint = f"{self.base_url}{endpoint}"
        logger.debug(f"headers: {self.headers}\n payload: {payload}\n endpoint:: {endpoint}")
        response = requests.request(
            "POST", url=endpoint, headers=self.headers,
            json=payload, timeout=settings.DEFAULT_HTTP_TIMEOUT
        )
        return self.parser.parse_response(response)
