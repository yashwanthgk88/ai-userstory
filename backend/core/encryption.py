"""Simple Fernet encryption for storing integration tokens."""

from cryptography.fernet import Fernet
from config import settings


def _get_fernet() -> Fernet:
    return Fernet(settings.encryption_key.encode())


def encrypt_token(token: str) -> str:
    return _get_fernet().encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()
