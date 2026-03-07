"""Unit tests for domain/siwe.py — nonce generation and SIWE verification."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from api.domain.siwe import (
    InvalidMessageError,
    InvalidSignatureError,
    NonceExpiredError,
    generate_nonce,
    verify_siwe_message,
)


class TestGenerateNonce:
    def test_returns_tuple(self):
        result = generate_nonce()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_nonce_is_64_hex_chars(self):
        nonce, _ = generate_nonce()
        assert len(nonce) == 64
        assert all(c in "0123456789abcdef" for c in nonce)

    def test_expiry_is_utc_aware(self):
        _, expires_at = generate_nonce()
        assert expires_at.tzinfo is not None

    def test_expiry_respects_ttl(self):
        now = datetime.now(UTC)
        _, expires_at = generate_nonce(ttl_seconds=60)
        delta = (expires_at - now).total_seconds()
        assert 55 <= delta <= 65  # allow small timing tolerance

    def test_unique_nonces(self):
        n1, _ = generate_nonce()
        n2, _ = generate_nonce()
        assert n1 != n2


class TestVerifySiweMessage:
    DOMAIN = "example.com"
    CHAIN_ID = 84532
    ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    NONCE = "abc123nonce"

    def _make_mock_siwe_msg(self, domain=None, chain_id=None, nonce=None, address=None):
        msg = MagicMock()
        msg.domain = domain or self.DOMAIN
        msg.chain_id = chain_id or self.CHAIN_ID
        msg.nonce = nonce or self.NONCE
        msg.address = address or self.ADDRESS
        return msg

    @patch("api.domain.siwe.SiweMessage")
    def test_valid_message_returns_address(self, mock_siwe_cls):
        mock_msg = self._make_mock_siwe_msg()
        mock_msg.verify.return_value = None
        mock_siwe_cls.from_message.return_value = mock_msg

        result = verify_siwe_message(
            message="<siwe message>",
            signature="0xsig",
            expected_domain=self.DOMAIN,
            expected_chain_id=self.CHAIN_ID,
            nonce=self.NONCE,
        )
        assert result == self.ADDRESS

    @patch("api.domain.siwe.SiweMessage")
    def test_wrong_domain_raises_invalid_message(self, mock_siwe_cls):
        mock_msg = self._make_mock_siwe_msg(domain="evil.com")
        mock_siwe_cls.from_message.return_value = mock_msg

        with pytest.raises(InvalidMessageError, match="Domain mismatch"):
            verify_siwe_message(
                message="<siwe message>",
                signature="0xsig",
                expected_domain=self.DOMAIN,
                expected_chain_id=self.CHAIN_ID,
                nonce=self.NONCE,
            )

    @patch("api.domain.siwe.SiweMessage")
    def test_wrong_chain_raises_invalid_message(self, mock_siwe_cls):
        mock_msg = self._make_mock_siwe_msg(chain_id=1)
        mock_siwe_cls.from_message.return_value = mock_msg

        with pytest.raises(InvalidMessageError, match="Chain ID mismatch"):
            verify_siwe_message(
                message="<siwe message>",
                signature="0xsig",
                expected_domain=self.DOMAIN,
                expected_chain_id=self.CHAIN_ID,
                nonce=self.NONCE,
            )

    @patch("api.domain.siwe.SiweMessage")
    def test_wrong_nonce_raises_nonce_expired(self, mock_siwe_cls):
        mock_msg = self._make_mock_siwe_msg(nonce="differentnonce")
        mock_siwe_cls.from_message.return_value = mock_msg

        with pytest.raises(NonceExpiredError):
            verify_siwe_message(
                message="<siwe message>",
                signature="0xsig",
                expected_domain=self.DOMAIN,
                expected_chain_id=self.CHAIN_ID,
                nonce=self.NONCE,
            )

    @patch("api.domain.siwe.SiweMessage")
    def test_bad_signature_raises_invalid_signature(self, mock_siwe_cls):
        from siwe import InvalidSignature

        mock_msg = self._make_mock_siwe_msg()
        mock_msg.verify.side_effect = InvalidSignature
        mock_siwe_cls.from_message.return_value = mock_msg

        with pytest.raises(InvalidSignatureError):
            verify_siwe_message(
                message="<siwe message>",
                signature="0xbadsig",
                expected_domain=self.DOMAIN,
                expected_chain_id=self.CHAIN_ID,
                nonce=self.NONCE,
            )

    @patch("api.domain.siwe.SiweMessage")
    def test_malformed_message_raises_invalid_message(self, mock_siwe_cls):
        from siwe import MalformedSession

        mock_siwe_cls.from_message.side_effect = MalformedSession("bad")

        with pytest.raises(InvalidMessageError, match="Malformed"):
            verify_siwe_message(
                message="bad message",
                signature="0xsig",
                expected_domain=self.DOMAIN,
                expected_chain_id=self.CHAIN_ID,
                nonce=self.NONCE,
            )
