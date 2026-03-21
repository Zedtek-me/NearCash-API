from requests import Response

from rest_framework.response import Response as RestResponse

from utils.helpers.logs import logger
from utils.helpers.exception import CustomException

class HttpPerser:

    @classmethod
    def parse_response(
        cls, response: Response, raise_exception: bool = False
    ) -> dict:
        """
        returns a dict after reading the http response body
        """
        try:
            parsed_response = response.json()
        except Exception as e:
            logger.exception(e)
            if not raise_exception:
                parsed_response = {}
            else:
                raise CustomException(e)
        return parsed_response


    @classmethod
    def success(
        cls, data: dict | None = None, status: int = 200
    ) -> RestResponse:
        return RestResponse(
            data=data,
            status=200
        )

    @classmethod
    def error(
        cls, message: str | dict | None = None, status=400
    ) -> RestResponse:
        return RestResponse(
            data=message,
            status=status
        )
