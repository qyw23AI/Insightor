"""Fernet encryption for sensitive config values (API keys, tokens)."""

from cryptography.fernet import Fernet
from pathlib import Path

_KEY_PATH = Path(__file__).resolve().parent.parent.parent / ".insightor" / ".fernet_key"


def _load_or_create_key() -> bytes:
    if _KEY_PATH.exists():
        return _KEY_PATH.read_bytes()
    key = Fernet.generate_key()
    _KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    _KEY_PATH.write_bytes(key)
    return key


_fernet = Fernet(_load_or_create_key())


def encrypt(value: str) -> str:
    if not value:
        return ""
    return _fernet.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    if not value:
        return ""
    return _fernet.decrypt(value.encode()).decode()
