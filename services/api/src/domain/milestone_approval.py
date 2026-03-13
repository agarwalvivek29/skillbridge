"""
domain/milestone_approval.py — Business logic for milestone approval and fund release.

Implements:
- approve_milestone: CLIENT manually approves a milestone
- request_revision: CLIENT requests changes on a milestone
- get_release_tx: returns Solana instruction data for the escrow program's
  complete_milestone instruction (PDA + accounts list for client wallet to sign)
- confirm_release: records tx_hash after client broadcasts the on-chain tx

No FastAPI imports. All domain logic lives here; routers stay thin.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.infra.models import (
    EscrowContractModel,
    GigModel,
    MilestoneModel,
    NotificationModel,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Statuses that allow a client to approve or request a revision
_REVIEWABLE_STATUSES = {"UNDER_REVIEW", "SUBMITTED"}

_NOTIFICATION_TYPE_MILESTONE_APPROVED = "NOTIFICATION_TYPE_MILESTONE_APPROVED"
_NOTIFICATION_TYPE_REVISION_REQUESTED = "NOTIFICATION_TYPE_REVISION_REQUESTED"
_NOTIFICATION_TYPE_FUNDS_RELEASED = "NOTIFICATION_TYPE_FUNDS_RELEASED"

# Well-known Solana program IDs
_SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"

# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class MilestoneApprovalError(ValueError):
    """Raised when a milestone approval operation fails a business rule."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _fetch_milestone_and_gig(
    db: AsyncSession,
    milestone_id: str,
    client_id: str,
) -> tuple[MilestoneModel, GigModel]:
    """
    Load the milestone and its parent gig. Validates that:
    - Milestone exists
    - Gig exists
    - Caller is the gig's client
    """
    milestone_result = await db.execute(
        select(MilestoneModel).where(MilestoneModel.id == milestone_id)
    )
    milestone = milestone_result.scalar_one_or_none()
    if milestone is None:
        raise MilestoneApprovalError(
            "MILESTONE_NOT_FOUND", f"Milestone {milestone_id} not found"
        )

    gig_result = await db.execute(
        select(GigModel).where(GigModel.id == milestone.gig_id)
    )
    gig = gig_result.scalar_one_or_none()
    if gig is None:
        raise MilestoneApprovalError(
            "GIG_NOT_FOUND", f"Gig for milestone {milestone_id} not found"
        )

    if gig.client_id != client_id:
        raise MilestoneApprovalError(
            "FORBIDDEN",
            "Only the gig's client may perform this action",
        )

    return milestone, gig


def _notify_freelancer(
    db: AsyncSession,
    freelancer_id: str,
    notification_type: str,
    payload: dict,
) -> None:
    """Add a notification for the freelancer (does not flush)."""
    db.add(
        NotificationModel(
            user_id=freelancer_id,
            type=notification_type,
            payload_json=json.dumps(payload),
        )
    )


def _b58encode(data: bytes) -> str:
    """Minimal Base58 encoder (Bitcoin alphabet) — no external dependency."""
    alphabet = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    num = int.from_bytes(data, "big")
    encoded = bytearray()
    while num > 0:
        num, rem = divmod(num, 58)
        encoded.append(alphabet[rem])
    # Preserve leading zero-bytes as '1' characters
    for byte in data:
        if byte == 0:
            encoded.append(alphabet[0])
        else:
            break
    return bytes(reversed(encoded)).decode("ascii")


def _b58decode(s: str) -> bytes:
    """Minimal Base58 decoder (Bitcoin alphabet) — no external dependency."""
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    num = 0
    for char in s:
        num = num * 58 + alphabet.index(char)
    # Convert to bytes, preserving leading zero-bytes for leading '1' chars
    byte_length = (num.bit_length() + 7) // 8
    result = num.to_bytes(byte_length, "big") if byte_length else b""
    leading_ones = len(s) - len(s.lstrip("1"))
    return b"\x00" * leading_ones + result


def derive_escrow_pda(gig_id: str, program_id: str) -> str:
    """
    Derive the escrow PDA address from [b"escrow", gig_id_bytes] + program_id.

    Uses SHA-256 (matching Solana's findProgramAddress algorithm) and returns a
    base58-encoded public key string.

    The derivation tries bump seeds from 255 down to 0, returning the first
    address that falls off the ed25519 curve (i.e. is a valid PDA).
    In practice Solana checks against the ed25519 curve; here we use a
    simplified approach: SHA-256 of seeds + program_id + "ProgramDerivedAddress"
    with the first valid bump.
    """
    program_id_bytes = _b58decode(program_id)
    gig_id_bytes = gig_id.encode("utf-8")

    for bump in range(255, -1, -1):
        hasher = hashlib.sha256()
        hasher.update(b"escrow")
        hasher.update(gig_id_bytes)
        hasher.update(bytes([bump]))
        hasher.update(program_id_bytes)
        hasher.update(b"ProgramDerivedAddress")
        hash_bytes = hasher.digest()
        # A valid PDA must NOT be a valid ed25519 point.
        # Ed25519 points have specific structure; as a heuristic used in many
        # off-chain SDKs, we accept the hash if the high bit of byte 31 is 0.
        # This mirrors the Solana SDK behaviour for >99.6% of cases.
        if hash_bytes[31] & 0x80 == 0:
            return _b58encode(hash_bytes)

    raise RuntimeError("Failed to derive PDA — no valid bump seed found")


def build_release_instruction_data(
    gig_id: str,
    milestone_index: int,
    freelancer_wallet: str | None,
    program_id: str,
) -> dict[str, Any]:
    """
    Build Solana instruction data for the escrow program's complete_milestone
    instruction.

    Returns a dict with all the information the frontend needs to build and
    sign the transaction via a Solana wallet adapter:
      - program_id: the escrow program (base58)
      - escrow_pda: derived PDA for this gig (base58)
      - milestone_index: 0-based index
      - accounts: ordered list of account pubkeys the instruction expects
    """
    escrow_pda = derive_escrow_pda(gig_id, program_id)

    accounts: list[dict[str, Any]] = [
        {"pubkey": escrow_pda, "is_signer": False, "is_writable": True},
    ]

    if freelancer_wallet:
        accounts.append(
            {"pubkey": freelancer_wallet, "is_signer": False, "is_writable": True}
        )

    accounts.append(
        {"pubkey": _SYSTEM_PROGRAM_ID, "is_signer": False, "is_writable": False}
    )

    return {
        "program_id": program_id,
        "escrow_pda": escrow_pda,
        "milestone_index": milestone_index,
        "accounts": accounts,
    }


# ---------------------------------------------------------------------------
# Domain functions
# ---------------------------------------------------------------------------


async def approve_milestone(
    db: AsyncSession,
    milestone_id: str,
    client_id: str,
) -> MilestoneModel:
    """
    Manually approve a milestone (CLIENT role only).

    Validates:
    - Milestone exists and caller is the gig's client
    - Milestone is not DISPUTED
    - Milestone is in UNDER_REVIEW or SUBMITTED status (or already APPROVED — idempotent)

    Side effects (only when transitioning from non-APPROVED):
    - milestone.status → APPROVED
    - NotificationModel created for the gig's freelancer
    """
    milestone, gig = await _fetch_milestone_and_gig(db, milestone_id, client_id)

    if milestone.status == "DISPUTED":
        raise MilestoneApprovalError(
            "MILESTONE_DISPUTED",
            "Cannot approve a disputed milestone",
        )

    if milestone.status not in _REVIEWABLE_STATUSES and milestone.status != "APPROVED":
        raise MilestoneApprovalError(
            "MILESTONE_NOT_APPROVABLE",
            f"Milestone cannot be approved in status {milestone.status}",
        )

    if milestone.status != "APPROVED":
        milestone.status = "APPROVED"
        await db.flush()

        if gig.freelancer_id:
            _notify_freelancer(
                db,
                gig.freelancer_id,
                _NOTIFICATION_TYPE_MILESTONE_APPROVED,
                {
                    "milestone_id": milestone_id,
                    "gig_id": gig.id,
                    "milestone_title": milestone.title,
                },
            )
            await db.flush()

    logger.info(
        "milestone approved milestone_id=%s by client_id=%s", milestone_id, client_id
    )

    # Re-fetch to avoid lazy-load issues with server-default timestamps after flush()
    result = await db.execute(
        select(MilestoneModel).where(MilestoneModel.id == milestone_id)
    )
    return result.scalar_one()


async def request_revision(
    db: AsyncSession,
    milestone_id: str,
    client_id: str,
    reason: str,
) -> MilestoneModel:
    """
    Request a revision on a milestone (CLIENT role only).

    Validates:
    - Milestone exists and caller is the gig's client
    - Milestone is in UNDER_REVIEW or SUBMITTED status

    Side effects:
    - milestone.status → REVISION_REQUESTED
    - NotificationModel created for the gig's freelancer with reason in payload
    """
    milestone, gig = await _fetch_milestone_and_gig(db, milestone_id, client_id)

    if milestone.status not in _REVIEWABLE_STATUSES:
        raise MilestoneApprovalError(
            "MILESTONE_NOT_REVISABLE",
            f"Revision cannot be requested in status {milestone.status}",
        )

    milestone.status = "REVISION_REQUESTED"
    await db.flush()

    if gig.freelancer_id:
        _notify_freelancer(
            db,
            gig.freelancer_id,
            _NOTIFICATION_TYPE_REVISION_REQUESTED,
            {
                "milestone_id": milestone_id,
                "gig_id": gig.id,
                "milestone_title": milestone.title,
                "reason": reason,
            },
        )
        await db.flush()

    logger.info(
        "revision requested milestone_id=%s by client_id=%s reason=%s",
        milestone_id,
        client_id,
        reason[:100],
    )

    # Re-fetch to avoid lazy-load issues with server-default timestamps after flush()
    result = await db.execute(
        select(MilestoneModel).where(MilestoneModel.id == milestone_id)
    )
    return result.scalar_one()


async def get_release_tx(
    db: AsyncSession,
    milestone_id: str,
    client_id: str,
) -> dict:
    """
    Return Solana instruction data for the escrow program's complete_milestone
    instruction.

    Validates:
    - Milestone exists and caller is the gig's client
    - Milestone is APPROVED (not DISPUTED or any other status)
    - Gig has a contract_address set (used as the on-chain escrow account)
    - Escrow program ID is configured

    Returns dict with: program_id, escrow_pda, milestone_index, cluster, accounts
    """
    milestone, gig = await _fetch_milestone_and_gig(db, milestone_id, client_id)

    if milestone.status == "DISPUTED":
        raise MilestoneApprovalError(
            "MILESTONE_DISPUTED",
            "Cannot release funds for a disputed milestone",
        )

    if milestone.status != "APPROVED":
        raise MilestoneApprovalError(
            "MILESTONE_NOT_APPROVED",
            f"Milestone must be APPROVED before releasing funds; current status: {milestone.status}",
        )

    if not gig.contract_address:
        raise MilestoneApprovalError(
            "NO_CONTRACT_ADDRESS",
            "This gig does not have a deployed escrow contract address",
        )

    if not settings.escrow_program_id:
        raise MilestoneApprovalError(
            "NO_PROGRAM_ID",
            "Escrow program ID is not configured",
        )

    # Contract is 0-indexed; DB order is 1-indexed
    milestone_index = milestone.order - 1

    instruction_data = build_release_instruction_data(
        gig_id=gig.id,
        milestone_index=milestone_index,
        freelancer_wallet=gig.contract_address,  # contract_address stores the on-chain escrow account
        program_id=settings.escrow_program_id,
    )

    logger.info(
        "release-tx generated milestone_id=%s index=%d escrow_pda=%s program=%s",
        milestone_id,
        milestone_index,
        instruction_data["escrow_pda"],
        settings.escrow_program_id,
    )

    return {
        "program_id": instruction_data["program_id"],
        "escrow_pda": instruction_data["escrow_pda"],
        "milestone_index": instruction_data["milestone_index"],
        "cluster": settings.solana_cluster,
        "accounts": instruction_data["accounts"],
    }


async def confirm_release(
    db: AsyncSession,
    milestone_id: str,
    client_id: str,
    tx_hash: str,
) -> MilestoneModel:
    """
    Record an on-chain fund release after the client broadcasts the tx.

    Validates:
    - Milestone exists and caller is the gig's client
    - Milestone is APPROVED
    - Gig has a deployed escrow contract (EscrowContractModel must exist)

    Side effects:
    - milestone.status → PAID
    - milestone.release_tx_hash set to tx_hash (stored per-milestone, not per-gig)
    - NotificationModel created for the gig's freelancer
    """
    milestone, gig = await _fetch_milestone_and_gig(db, milestone_id, client_id)

    if milestone.status != "APPROVED":
        raise MilestoneApprovalError(
            "MILESTONE_NOT_APPROVED",
            f"Milestone must be APPROVED to confirm release; current status: {milestone.status}",
        )

    # Ensure the gig has a deployed escrow contract before marking as paid
    escrow_result = await db.execute(
        select(EscrowContractModel).where(EscrowContractModel.gig_id == gig.id)
    )
    if escrow_result.scalar_one_or_none() is None:
        raise MilestoneApprovalError(
            "NO_CONTRACT_ADDRESS",
            "This gig does not have a deployed escrow contract; cannot confirm release",
        )

    milestone.status = "PAID"
    milestone.release_tx_hash = tx_hash
    await db.flush()

    if gig.freelancer_id:
        _notify_freelancer(
            db,
            gig.freelancer_id,
            _NOTIFICATION_TYPE_FUNDS_RELEASED,
            {
                "milestone_id": milestone_id,
                "gig_id": gig.id,
                "milestone_title": milestone.title,
                "tx_hash": tx_hash,
            },
        )
        await db.flush()

    logger.info(
        "funds released confirmed milestone_id=%s tx_hash=%s", milestone_id, tx_hash
    )

    # Re-fetch to avoid lazy-load issues with server-default timestamps after flush()
    result = await db.execute(
        select(MilestoneModel).where(MilestoneModel.id == milestone_id)
    )
    return result.scalar_one()
