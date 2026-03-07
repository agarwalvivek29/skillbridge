"""Unit tests for JWT encode/decode helpers."""

import time

import pytest
from jose import JWTError

from src.domain.auth import create_access_token, decode_access_token


class TestCreateAccessToken:
    def test_returns_token_and_positive_expiry(self):
        token, expires_in = create_access_token("user-123", "USER_ROLE_FREELANCER")
        assert isinstance(token, str)
        assert len(token) > 20
        assert expires_in > 0

    def test_token_contains_correct_claims(self):
        token, _ = create_access_token("user-456", "USER_ROLE_CLIENT")
        claims = decode_access_token(token)
        assert claims["sub"] == "user-456"
        assert claims["role"] == "USER_ROLE_CLIENT"

    def test_expiry_is_in_future(self):
        token, expires_in = create_access_token("user-789", "USER_ROLE_FREELANCER")
        claims = decode_access_token(token)
        assert claims["exp"] > time.time()


class TestDecodeAccessToken:
    def test_rejects_garbage_token(self):
        with pytest.raises(JWTError):
            decode_access_token("not.a.valid.token")

    def test_rejects_tampered_token(self):
        token, _ = create_access_token("user-001", "USER_ROLE_FREELANCER")
        # Tamper with payload
        parts = token.split(".")
        parts[1] = parts[1] + "garbage"
        with pytest.raises(JWTError):
            decode_access_token(".".join(parts))
