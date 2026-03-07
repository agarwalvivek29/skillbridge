"""Unit tests for SIWE signature verification."""

from eth_account import Account
from eth_account.messages import encode_defunct

from src.domain.auth import verify_siwe_signature


def _make_signature(private_key: str, message: str) -> str:
    msg = encode_defunct(text=message)
    signed = Account.sign_message(msg, private_key=private_key)
    return signed.signature.hex()


class TestVerifySiweSignature:
    # Deterministic test key (never used with real funds)
    _PRIVATE_KEY = "0x4c0883a69102937d6231471b5dbb6e538eba2ef5cf0e6e91a74b5e3e1e3a3c34"
    _WALLET = Account.from_key(_PRIVATE_KEY).address

    def test_valid_signature_returns_true(self):
        nonce = "testNonce123"
        message = f"Sign in to SkillBridge\nNonce: {nonce}"
        sig = _make_signature(self._PRIVATE_KEY, message)
        assert verify_siwe_signature(self._WALLET, message, sig, nonce) is True

    def test_wrong_address_returns_false(self):
        nonce = "testNonce123"
        message = f"Sign in to SkillBridge\nNonce: {nonce}"
        sig = _make_signature(self._PRIVATE_KEY, message)
        assert verify_siwe_signature("0xDeaD" + "0" * 36, message, sig, nonce) is False

    def test_wrong_nonce_in_message_returns_false(self):
        nonce = "testNonce123"
        message = "Sign in to SkillBridge\nNonce: differentNonce"
        sig = _make_signature(self._PRIVATE_KEY, message)
        assert verify_siwe_signature(self._WALLET, message, sig, nonce) is False

    def test_garbage_signature_returns_false(self):
        nonce = "testNonce123"
        message = f"Sign in to SkillBridge\nNonce: {nonce}"
        assert (
            verify_siwe_signature(self._WALLET, message, "0xdeadbeef", nonce) is False
        )
