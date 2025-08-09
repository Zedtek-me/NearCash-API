import jwt
from utils.helpers.logs import logger
from typing import Tuple
from graphql_jwt.utils import jwt_decode
from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync

from django.contrib.auth.models import AnonymousUser


class CustomSocketAuthMiddleware:

    def __init__(self, inner):
        self.app = inner
        self.scope = {}
        super().__init__()

    async def __call__(self, scope, receive, send):
        self.scope = scope
        headers = self.scope.get("headers", [])
        headers = self._parse_headers(headers)
        auth_token = headers.get("authorization")
        if not auth_token:
            self._set_anonymous_user()
        await self._populate_scope(self.scope, auth_token)
        return await self.app(scope, receive, send)


    def _parse_headers(
        self, headers: list
    ) -> dict:
        """
        formats header as dict
        """
        formatted_headers = {}
        def format_bytes(byte_data: Tuple[bytes])->dict:
            byte_key, byte_value = byte_data
            if not (byte_key and byte_data):
                return formatted_headers
            return {
                byte_key.decode(): byte_value.decode()
            }
        headers = list(map(format_bytes, headers))
        for header in headers:
            formatted_headers.update(header)
        return formatted_headers


    async def _populate_scope(self, scope, auth_token: str) -> None:
        from apps.auths.models import User

        _, token = auth_token.split(" ")
        decoded_payload = jwt_decode(token)
        email = decoded_payload.get("email")
        user = await database_sync_to_async(User.objects.filter(email__iexact=email).first)()
        if not user:
            self._set_anonymous_user()
        scope["user"] = user
        scope["auth_token"] = token

    def _set_anonymous_user(self):
        self.scope["user"] = AnonymousUser()
