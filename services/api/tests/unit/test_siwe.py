"""Unit tests for SIWE (EIP-4361) signature verification."""

from datetime import datetime, timezone

from eth_account import Account
from eth_account.messages import encode_defunct
from siwe import SiweMessage

from src.domain.auth import verify_siwe_signature

# Deterministic test key (never used with real funds)
_PRIVATE_KEY = "0x4c0883a69102937d6231471b5dbb6e538eba2ef5cf0e6e91a74b5e3e1e3a3c34"
_WALLET = Account.from_key(_PRIVATE_KEY).address
_DOMAIN = "skillbridge.xyz"


def _build_siwe_message(nonce: str, wallet: str = _WALLET) -> str:
    """Construct a fully-compliant EIP-4361 SIWE message string."""
    msg = SiweMessage(
        domain=_DOMAIN,
        address=wallet,
        statement="Sign in to SkillBridge",
        uri=f"https://{_DOMAIN}",
        version="1",
        chain_id=1,
        nonce=nonce,
        issued_at=datetime.now(timezone.utc).isoformat(),
    )
    return msg.prepare_message()


def _sign(private_key: str, message: str) -> str:
    """Sign a SIWE message with the given private key."""
    signable = encode_defunct(text=message)
    return Account.sign_message(signable, private_key=private_key).signature.hex()


class TestVerifySiweSignature:
    def test_valid_eip4361_message_returns_true(self):
        nonce = "testNonce1234"
        message = _build_siwe_message(nonce)
        sig = _sign(_PRIVATE_KEY, message)
        assert verify_siwe_signature(_WALLET, message, sig, nonce) is True

    def test_wrong_address_returns_false(self):
        nonce = "testNonce1234"
        message = _build_siwe_message(nonce)
        sig = _sign(_PRIVATE_KEY, message)
        # Claim a different wallet than what actually signed
        wrong_wallet = "0xDeaDDeaDDeaDDeaDDeaDDeaDDeaDDeaDDeaDDeaD"
        assert verify_siwe_signature(wrong_wallet, message, sig, nonce) is False

    def test_wrong_nonce_returns_false(self):
        nonce = "testNonce1234"
        message = _build_siwe_message(nonce)
        sig = _sign(_PRIVATE_KEY, message)
        # Verify with a different expected nonce than what is in the message
        assert verify_siwe_signature(_WALLET, message, sig, "differentNonce") is False

    def test_garbage_signature_returns_false(self):
        nonce = "testNonce1234"
        message = _build_siwe_message(nonce)
        assert verify_siwe_signature(_WALLET, message, "0xdeadbeef", nonce) is False

    def test_non_siwe_message_returns_false(self):
        """A plain EIP-191 message (not EIP-4361 format) must be rejected."""
        nonce = "testNonce1234"
        plain_message = f"Sign in to SkillBridge\nNonce: {nonce}"
        sig = _sign(_PRIVATE_KEY, plain_message)
        assert verify_siwe_signature(_WALLET, plain_message, sig, nonce) is False
