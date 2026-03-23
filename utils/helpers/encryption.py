from cryptography.fernet import Fernet
from django.conf import settings

from typing import Any


def encrypt_data_with_fernet(
    data: Any
) -> str | dict | None:
    fernet = Fernet(settings.FERNET_TOKEN_KEY.encode())
    encrypted_data = fernet.encrypt(data.encode()).decode()
    return encrypted_data


def decrypt_data_with_fernet(
    token: str
) -> str | dict | None:
    fernet = Fernet(settings.FERNET_TOKEN_KEY.encode())
    decrypted = fernet.decrypt(token.encode()).decode()
    return decrypted
