from abc import ABC, abstractmethod


class AuthInterface(ABC):
    """to be implemented by all auth services"""

    @classmethod
    @abstractmethod
    def get_auth_url(cls) -> str:
        """
        Returns the OAuth2 authorization URL.
        """
        pass
