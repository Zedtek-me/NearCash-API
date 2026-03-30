from rest_framework.permissions import BasePermission

from django.conf import settings

import hmac
import json

from utils.helpers.logs import logger
from utils.helpers.exception import CustomException


class HookSignatureValid(BasePermission):
    def has_permission(self, request, view) -> bool:
        """
        checks whether the given signature
        is valid based on my secret hash key
        """
        flutterwave_signature = request.headers.get("flutterwave-signature")
        logger.debug(
            f"flutterwave signature from header here::::: {flutterwave_signature}\n"
        )
        try:
            logger.debug(f"request body with the body prop::: {request.body}")
        except Exception as e:
            logger.error(f"exception with req.body::: {e}")
        return self._verify_signature(
            flutterwave_signature, settings.HMAC_KEY,
            request.data
        )


    def _verify_signature(
        self, signature: str, hash_key: str,
        data: str | dict, digest: str = "SHA256"
    ) -> bool:
        refined_data = self._refine_raw_data(data)
        regenerated_hmac_hex = hmac.new(
            hash_key.encode(), refined_data, digestmod=digest
        ).hexdigest()
        logger.debug(f"regenerated hmac hex::::: {regenerated_hmac_hex}")
        return regenerated_hmac_hex == signature


    def _refine_raw_data(
        self, data: str | dict | bytes
    ) -> bytes:
        if not isinstance(data, (str, dict, bytes)):
            raise CustomException(
                message="data is not a valid python type!!"
            )
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return data.encode("utf-8")
        jsonified = json.dumps(data)
        return jsonified.encode("utf-8")
