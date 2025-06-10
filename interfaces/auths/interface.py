from abc import ABC, abstractmethod
from typing import Union, Optional

class AuthInterface(ABC):
    """to be implemented by all auth services"""
    NOT_IMPLEMENTED = "method not implemented!"
    @classmethod
    @abstractmethod
    def get_auth_url(cls) -> Optional[str]:
        """
        Returns the OAuth2 authorization URL.
        """
        raise NotImplementedError(cls.NOT_IMPLEMENTED)

    @classmethod
    @abstractmethod
    def get_auth_tokens(cls, auth_code) -> Union[dict, str, None]:
        """fetches auth tokens with auth code"""
        raise NotImplementedError(cls.NOT_IMPLEMENTED)

    @classmethod
    @abstractmethod
    def fetch_user_info(
        cls, credentials: dict
    ) -> Union[dict, str, list]:
        """fetches user information with $credentials"""
        raise NotImplementedError(cls.NOT_IMPLEMENTED)
