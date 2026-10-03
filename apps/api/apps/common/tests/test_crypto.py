"""Tests for credential encryption at rest.

The cipher reads its key from settings on every call, so `override_settings` is
sufficient to exercise the failure modes without touching global state.
"""
from __future__ import annotations

import pytest
from django.test import override_settings

from apps.common.crypto import CredentialCipherUnavailable, decrypt_secret, encrypt_secret


def test_round_trip():
    ciphertext = encrypt_secret("sup3r-secret")
    assert isinstance(ciphertext, bytes)
    assert b"sup3r-secret" not in ciphertext
    assert decrypt_secret(ciphertext) == "sup3r-secret"


def test_ciphertext_is_non_deterministic():
    """Fernet includes a random IV, so identical inputs differ on the wire."""
    assert encrypt_secret("same") != encrypt_secret("same")


def test_tampered_ciphertext_is_rejected():
    ciphertext = bytearray(encrypt_secret("value"))
    ciphertext[-1] ^= 0xFF
    with pytest.raises(CredentialCipherUnavailable):
        decrypt_secret(bytes(ciphertext))


@override_settings(DATAFORGE_FERNET_KEY="")
def test_missing_key_refuses_to_operate():
    with pytest.raises(CredentialCipherUnavailable):
        encrypt_secret("value")


@override_settings(DATAFORGE_FERNET_KEY="not-a-valid-key")
def test_invalid_key_is_rejected():
    with pytest.raises(CredentialCipherUnavailable):
        encrypt_secret("value")


def test_encrypting_none_is_refused():
    with pytest.raises(ValueError):
        encrypt_secret(None)  # type: ignore[arg-type]


def test_decrypting_none_is_refused():
    with pytest.raises(ValueError):
        decrypt_secret(None)  # type: ignore[arg-type]
