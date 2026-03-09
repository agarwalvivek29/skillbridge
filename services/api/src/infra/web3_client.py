"""
web3_client.py — On-chain transaction helpers.

Provides server-side transaction signing and broadcasting via the oracle wallet.
Used by dispute resolution to call GigEscrow.resolveDispute(index, resolution, splitAmount).
"""

from __future__ import annotations

import logging

from web3 import Web3
from web3.exceptions import Web3Exception

from src.config import settings

logger = logging.getLogger(__name__)

# keccak256("resolveDispute(uint256,uint8,uint256)")[:4]
_RESOLVE_DISPUTE_SELECTOR = bytes.fromhex("37c9ccb8")

# Resolution enum mapping (matches IGigEscrow.DisputeResolution)
_RESOLUTION_MAP = {
    "DISPUTE_RESOLUTION_PAY_FREELANCER": 1,
    "DISPUTE_RESOLUTION_REFUND_CLIENT": 2,
    "DISPUTE_RESOLUTION_SPLIT": 3,
}


class OnChainError(Exception):
    """Raised when an on-chain call fails."""


def _encode_resolve_dispute_calldata(
    milestone_index: int,
    resolution: str,
    freelancer_split_amount: str | None,
) -> bytes:
    """
    ABI-encode a call to resolveDispute(uint256 index, uint8 resolution, uint256 splitAmount).

    Encoding:
      - 4-byte selector
      - 32-byte uint256: milestone index
      - 32-byte uint8 (padded): resolution enum value (1, 2, or 3)
      - 32-byte uint256: freelancer split amount in wei (0 if not SPLIT)
    """
    resolution_value = _RESOLUTION_MAP.get(resolution)
    if resolution_value is None:
        raise OnChainError(f"Unknown resolution: {resolution}")

    split_amount = int(freelancer_split_amount) if freelancer_split_amount else 0

    encoded_index = milestone_index.to_bytes(32, "big")
    encoded_resolution = resolution_value.to_bytes(32, "big")
    encoded_amount = split_amount.to_bytes(32, "big")

    return (
        _RESOLVE_DISPUTE_SELECTOR + encoded_index + encoded_resolution + encoded_amount
    )


async def call_resolve_dispute_on_chain(
    contract_address: str,
    milestone_index: int,
    resolution: str,
    freelancer_split_amount: str | None,
) -> str:
    """
    Sign and broadcast resolveDispute() via the oracle hot wallet.

    Returns the transaction hash (0x-prefixed hex string).
    Raises OnChainError if the oracle key is not configured or the tx fails.
    """
    if not settings.oracle_private_key:
        raise OnChainError(
            "ORACLE_PRIVATE_KEY not configured; cannot sign on-chain transactions"
        )

    if not contract_address:
        raise OnChainError("No contract address provided for on-chain resolution")

    w3 = Web3(Web3.HTTPProvider(settings.base_rpc_url))
    if not w3.is_connected():
        raise OnChainError(f"Cannot connect to RPC at {settings.base_rpc_url}")

    account = w3.eth.account.from_key(settings.oracle_private_key)
    calldata = _encode_resolve_dispute_calldata(
        milestone_index, resolution, freelancer_split_amount
    )

    try:
        nonce = w3.eth.get_transaction_count(account.address)
        tx = {
            "to": Web3.to_checksum_address(contract_address),
            "data": calldata,
            "nonce": nonce,
            "chainId": settings.base_chain_id,
            "gas": 200_000,
            "maxFeePerGas": w3.eth.gas_price * 2,
            "maxPriorityFeePerGas": w3.eth.gas_price,
        }
        signed = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        hex_hash = tx_hash.hex()

        logger.info(
            "on-chain resolveDispute sent contract=%s tx_hash=0x%s",
            contract_address,
            hex_hash,
        )
        return f"0x{hex_hash}"

    except Web3Exception as exc:
        raise OnChainError(f"On-chain transaction failed: {exc}") from exc
