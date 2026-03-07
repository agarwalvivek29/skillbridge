"""Unit tests for bcrypt password helpers."""

from src.domain.auth import hash_password, verify_password


class TestHashPassword:
    def test_returns_non_empty_string(self):
        h = hash_password("supersecret")
        assert isinstance(h, str)
        assert len(h) > 10

    def test_hashes_are_different_for_same_input(self):
        h1 = hash_password("supersecret")
        h2 = hash_password("supersecret")
        assert h1 != h2  # bcrypt uses random salt


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        h = hash_password("correct-password")
        assert verify_password("correct-password", h) is True

    def test_wrong_password_returns_false(self):
        h = hash_password("correct-password")
        assert verify_password("wrong-password", h) is False

    def test_empty_password_returns_false(self):
        h = hash_password("correct-password")
        assert verify_password("", h) is False
