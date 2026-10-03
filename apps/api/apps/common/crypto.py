"""Symmetric encryption for secrets we must be able to read back (data-source
passwords). This is *reversible* encryption, not hashing — the AI service needs
the plaintext to open a customer connection.

Rules:
- The key comes from ``DATAFORGE_FERNET_KEY`` and never from source code.
- Ciphertext is stored in the database as bytes; plaintext is never logged,
  serialized to an API response, or written to disk.
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class CredentialCipherUnavailable(RuntimeError):
    """Raised when the encryption key is missing or malformed."""


def _cipher() -> Fernet:
    key = getattr(settings, "DATAFORGE_FERNET_KEY", "") or ""
    if not key:
        raise CredentialCipherUnavailable(
            "DATAFORGE_FERNET_KEY is not configured; refusing to handle credentials."
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:
        raise CredentialCipherUnavailable("DATAFORGE_FERNET_KEY is not a valid Fernet key.") from exc


def encrypt_secret(plaintext: str) -> bytes:
    """Encrypt a secret for storage."""
    if plaintext is None:
        raise ValueError("Refusing to encrypt a null secret.")
    return _cipher().encrypt(plaintext.encode("utf-8"))


def decrypt_secret(ciphertext: bytes | memoryview) -> str:
    """Decrypt a stored secret. Raises on tampering (Fernet is authenticated)."""
    if ciphertext is None:
        raise ValueError("No ciphertext supplied.")
    data = bytes(ciphertext)
    try:
        return _cipher().decrypt(data).decode("utf-8")
    except InvalidToken as exc:
        raise CredentialCipherUnavailable(
            "Stored credential could not be decrypted (key changed or data tampered)."
        ) from exc
