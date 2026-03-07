"""
SIWE (Sign-In with Ethereum) domain logic.

Handles nonce generation and EIP-4361 message verification.
Zero framework imports. All functions are pure and independently testable.
"""

import secrets
from datetime import UTC, datetime, timedelta

from siwe import ExpiredMessage, InvalidSignature, MalformedSession, SiweMessage


class SiweError(Exception):
    """Base exception for SIWE verification failures."""


class NonceExpiredError(SiweError):
    """Raised when the SIWE nonce has expired or already been used."""


class InvalidSignatureError(SiweError):
    """Raised when the SIWE signature cannot be verified."""


class InvalidMessageError(SiweError):
    """Raised when the SIWE message is malformed or has wrong domain/chain."""


def generate_nonce(ttl_seconds: int = 300) -> tuple[str, datetime]:
    """
    Generate a cryptographically random nonce and its expiry timestamp.

    Returns:
        (nonce, expires_at) — nonce is 64 hex chars; expires_at is UTC-aware.
    """
    nonce = secrets.token_hex(32)
    expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
    return nonce, expires_at


def verify_siwe_message(
    message: str,
    signature: str,
    expected_domain: str,
    expected_chain_id: int,
    nonce: str,
) -> str:
    """
    Verify a SIWE message and signature.

    Args:
        message:           Full EIP-4361 message string.
        signature:         0x-prefixed Ethereum signature hex.
        expected_domain:   Domain the message must claim (e.g. "skillbridge.xyz").
        expected_chain_id: EVM chain ID the message must claim.
        nonce:             Expected nonce from the server-side store.

    Returns:
        The checksummed Ethereum address extracted from the verified message.

    Raises:
        NonceExpiredError:    Nonce mismatch or expired.
        InvalidSignatureError: Signature does not match the address in the message.
        InvalidMessageError:  Malformed message, wrong domain, or wrong chain ID.
    """
    try:
        siwe_msg = SiweMessage.from_message(message=message)
    except (MalformedSession, ValueError) as exc:
        raise InvalidMessageError(f"Malformed SIWE message: {exc}") from exc

    if siwe_msg.domain != expected_domain:
        raise InvalidMessageError(
            f"Domain mismatch: expected '{expected_domain}', got '{siwe_msg.domain}'"
        )

    if siwe_msg.chain_id != expected_chain_id:
        raise InvalidMessageError(
            f"Chain ID mismatch: expected {expected_chain_id}, got {siwe_msg.chain_id}"
        )

    if siwe_msg.nonce != nonce:
        raise NonceExpiredError("Nonce mismatch — may have been used or expired")

    try:
        siwe_msg.verify(signature=signature)
    except ExpiredMessage as exc:
        raise NonceExpiredError("SIWE message has expired") from exc
    except InvalidSignature as exc:
        raise InvalidSignatureError("SIWE signature verification failed") from exc

    return siwe_msg.address


__all__ = [
    "generate_nonce",
    "verify_siwe_message",
    "SiweError",
    "NonceExpiredError",
    "InvalidSignatureError",
    "InvalidMessageError",
]
