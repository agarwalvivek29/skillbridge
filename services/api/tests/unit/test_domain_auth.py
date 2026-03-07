"""Unit tests for domain/auth.py — password hashing and JWT operations."""

import time

import pytest
from jose import JWTError

from api.domain.auth import hash_password, issue_jwt, verify_jwt, verify_password

SECRET = "a-test-secret-that-is-at-least-32-chars-long"


class TestHashPassword:
    def test_returns_non_empty_string(self):
        result = hash_password("mysecret")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_different_plaintext_different_hash(self):
        h1 = hash_password("password1")
        h2 = hash_password("password2")
        assert h1 != h2

    def test_same_plaintext_different_hash_each_call(self):
        # bcrypt uses a salt — same input should produce different hashes
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        assert h1 != h2

    def test_never_stores_plaintext(self):
        plain = "supersecret"
        h = hash_password(plain)
        assert plain not in h


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        plain = "correcthorse"
        h = hash_password(plain)
        assert verify_password(plain, h) is True

    def test_wrong_password_returns_false(self):
        h = hash_password("correct")
        assert verify_password("wrong", h) is False

    def test_empty_password_returns_false(self):
        h = hash_password("notempty")
        assert verify_password("", h) is False


class TestIssueJwt:
    def test_returns_string(self):
        token = issue_jwt("user-id-123", SECRET, expiry_seconds=3600)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_has_three_parts(self):
        token = issue_jwt("user-id-123", SECRET, expiry_seconds=3600)
        assert token.count(".") == 2

    def test_encodes_subject(self):
        token = issue_jwt("my-user-id", SECRET, expiry_seconds=3600)
        payload = verify_jwt(token, SECRET)
        assert payload["sub"] == "my-user-id"

    def test_encodes_role(self):
        token = issue_jwt("uid", SECRET, expiry_seconds=3600, role="USER_ROLE_ADMIN")
        payload = verify_jwt(token, SECRET)
        assert payload["role"] == "USER_ROLE_ADMIN"

    def test_default_role_is_member(self):
        token = issue_jwt("uid", SECRET, expiry_seconds=3600)
        payload = verify_jwt(token, SECRET)
        assert payload["role"] == "USER_ROLE_MEMBER"

    def test_expiry_is_set(self):
        before = int(time.time())
        token = issue_jwt("uid", SECRET, expiry_seconds=60)
        payload = verify_jwt(token, SECRET)
        assert payload["exp"] >= before + 60
        assert payload["exp"] <= before + 65  # small tolerance


class TestVerifyJwt:
    def test_valid_token_returns_payload(self):
        token = issue_jwt("uid", SECRET, expiry_seconds=3600)
        payload = verify_jwt(token, SECRET)
        assert payload["sub"] == "uid"

    def test_wrong_secret_raises(self):
        token = issue_jwt("uid", SECRET, expiry_seconds=3600)
        with pytest.raises(JWTError):
            verify_jwt(token, "wrong-secret-that-is-also-32-chars-long")

    def test_expired_token_raises(self):
        token = issue_jwt("uid", SECRET, expiry_seconds=-1)
        with pytest.raises(JWTError):
            verify_jwt(token, SECRET)

    def test_malformed_token_raises(self):
        with pytest.raises(JWTError):
            verify_jwt("not.a.valid.jwt", SECRET)
