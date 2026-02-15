import logging

import jwt
from utils.helpers.logs import logger
from typing import Tuple
from graphql_jwt.utils import jwt_decode
from channels.db import database_sync_to_async
from asgiref.sync import async_to_sync

logger = logging.getLogger("nearcash")
logger.setLevel(logging.DEBUG)


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
        query_strings = self.scope.get("query_string", b"")
        parsed_query_strings = self._parse_query_strings(query_strings)
        token_in_query = parsed_query_strings.get("token")
        if not auth_token and not token_in_query:
            self._set_anonymous_user()
        if auth_token:
            await self._populate_scope(self.scope, auth_token)
        elif token_in_query:
            await self._populate_scope(self.scope, token_in_query, from_query=True)
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


    async def _populate_scope(self, scope, auth_token: str, **kwargs) -> None:
        from apps.auths.models import User

        if not kwargs.get("from_query", False):
            _, token = auth_token.split(" ")
        else:
            token = auth_token
        decoded_payload = jwt_decode(token)
        email = decoded_payload.get("email")
        user = await database_sync_to_async(User.objects.filter(email__iexact=email).first)()
        if not user:
            self._set_anonymous_user()
            return
        scope["user"] = user
        scope["auth_token"] = token

    def _set_anonymous_user(self):
        from django.contrib.auth.models import AnonymousUser

        self.scope["user"] = AnonymousUser()


    def _parse_query_strings(self, byte_query: bytes) -> dict:
        """formats query params as dict"""
        query_str = byte_query.decode("utf-8")
        queries = query_str.split("&")
        formatted = {}
        for query in queries:
            if "=" not in query:
                continue
            key, value = query.split("=", 1)
            if key and value:
                formatted[key] = value
        return formatted
