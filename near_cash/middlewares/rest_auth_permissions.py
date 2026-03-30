from rest_framework.permissions import BasePermission

from django.conf import settings

import hmac
import json
from base64 import b64encode

from utils.helpers.logs import logger
from utils.helpers.exception import CustomException


class HookSignatureValid(BasePermission):
    def has_permission(self, request, view) -> bool:
        """
        checks whether the given signature
        is valid based on my secret hash key
        """
        flutterwave_signature = request.headers.get("flutterwave-signature")
        return self._verify_signature(
            flutterwave_signature, settings.HMAC_KEY,
            request.body
        )


    def _verify_signature(
        self, signature: str, hash_key: str,
        byte_data: str | dict, digest: str = "SHA256"
    ) -> bool:
        refined_data = self._refine_raw_data(byte_data)
        regenerated_hmac_digest = hmac.new(
            hash_key.encode(), refined_data, digestmod=digest
        ).digest()
        encoded_digest = b64encode(regenerated_hmac_digest).decode()
        logger.debug(f"regenerated hmac_digest::::: {regenerated_hmac_digest}\n b64 encoded digest:: {encoded_digest}")
        return encoded_digest == signature


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
