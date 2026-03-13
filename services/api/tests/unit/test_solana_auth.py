"""Unit tests for Solana Ed25519 signature verification."""

import base64
from datetime import datetime, timezone

import base58
import nacl.signing

from src.domain.auth import build_solana_sign_in_message, verify_solana_signature

# Deterministic test keypair (never used with real funds)
_SIGNING_KEY = nacl.signing.SigningKey.generate()
_VERIFY_KEY = _SIGNING_KEY.verify_key
_WALLET = base58.b58encode(_VERIFY_KEY.encode()).decode()


def _build_message(nonce: str, wallet: str = _WALLET) -> str:
    """Build the Solana sign-in message for testing."""
    issued_at = datetime.now(timezone.utc).isoformat()
    return (
        f"SkillBridge wants you to sign in with your Solana account:\n"
        f"{wallet}\n"
        f"\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued_at}"
    )


def _sign(message: str) -> str:
    """Sign a message with the test Ed25519 key and return base64 signature."""
    signed = _SIGNING_KEY.sign(message.encode("utf-8"))
    # signed.signature is just the 64-byte signature
    return base64.b64encode(signed.signature).decode()


class TestVerifySolanaSignature:
    def test_valid_signature_returns_true(self):
        nonce = "testNonce1234"
        message = _build_message(nonce)
        sig = _sign(message)
        assert verify_solana_signature(_WALLET, message, sig, nonce) is True

    def test_wrong_address_returns_false(self):
        nonce = "testNonce1234"
        message = _build_message(nonce)
        sig = _sign(message)
        # Use a different keypair's public key as the claimed wallet
        other_key = nacl.signing.SigningKey.generate()
        wrong_wallet = base58.b58encode(other_key.verify_key.encode()).decode()
        assert verify_solana_signature(wrong_wallet, message, sig, nonce) is False

    def test_wrong_nonce_returns_false(self):
        nonce = "testNonce1234"
        message = _build_message(nonce)
        sig = _sign(message)
        # Verify with a different expected nonce than what is in the message
        assert verify_solana_signature(_WALLET, message, sig, "differentNonce") is False

    def test_garbage_signature_returns_false(self):
        nonce = "testNonce1234"
        message = _build_message(nonce)
        garbage_sig = base64.b64encode(b"deadbeef" * 8).decode()
        assert verify_solana_signature(_WALLET, message, garbage_sig, nonce) is False

    def test_plain_message_without_nonce_field_returns_false(self):
        """A message without the Nonce: field must be rejected."""
        nonce = "testNonce1234"
        plain_message = f"Sign in to SkillBridge\n{nonce}"
        sig = _sign(plain_message)
        assert verify_solana_signature(_WALLET, plain_message, sig, nonce) is False

    def test_invalid_base58_address_returns_false(self):
        nonce = "testNonce1234"
        message = _build_message(nonce)
        sig = _sign(message)
        assert (
            verify_solana_signature("not-a-valid-address!!!", message, sig, nonce)
            is False
        )


class TestBuildSolanaSignInMessage:
    def test_contains_wallet_address(self):
        msg = build_solana_sign_in_message(_WALLET, "testNonce")
        assert _WALLET in msg

    def test_contains_nonce(self):
        msg = build_solana_sign_in_message(_WALLET, "myNonce123")
        assert "Nonce: myNonce123" in msg

    def test_contains_solana_account_header(self):
        msg = build_solana_sign_in_message(_WALLET, "n")
        assert "SkillBridge wants you to sign in with your Solana account:" in msg

    def test_contains_issued_at(self):
        msg = build_solana_sign_in_message(_WALLET, "n")
        assert "Issued At:" in msg
