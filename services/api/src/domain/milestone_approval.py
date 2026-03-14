"""
domain/milestone_approval.py — Business logic for milestone approval and fund release.

Implements:
- approve_milestone: CLIENT manually approves a milestone
- request_revision: CLIENT requests changes on a milestone
- get_release_tx: returns Solana escrow seeds, program_id, and accounts so the
  frontend can derive the PDA via PublicKey.findProgramAddress() and build the tx
- confirm_release: records tx_hash after client broadcasts the on-chain tx

No FastAPI imports. All domain logic lives here; routers stay thin.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.domain.enums import MilestoneStatus
from src.infra.models import (
    EscrowContractModel,
    GigModel,
    MilestoneModel,
    NotificationModel,
    UserModel,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Statuses that allow a client to approve or request a revision
_REVIEWABLE_STATUSES = {MilestoneStatus.UNDER_REVIEW, MilestoneStatus.SUBMITTED}

_NOTIFICATION_TYPE_MILESTONE_APPROVED = "NOTIFICATION_TYPE_MILESTONE_APPROVED"
_NOTIFICATION_TYPE_REVISION_REQUESTED = "NOTIFICATION_TYPE_REVISION_REQUESTED"
_NOTIFICATION_TYPE_FUNDS_RELEASED = "NOTIFICATION_TYPE_FUNDS_RELEASED"

# Well-known Solana program IDs
_SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"

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


def build_release_instruction_data(
    gig_id: str,
    milestone_index: int,
    freelancer_wallet: str | None,
    client_wallet: str | None,
    program_id: str,
) -> dict[str, Any]:
    """
    Build Solana instruction data for the escrow program's complete_milestone
    instruction.

    Instead of deriving the PDA on the backend (which cannot correctly replicate
    Solana's findProgramAddress), this returns the seeds and program_id so the
    frontend can call PublicKey.findProgramAddress() itself.

    Returns a dict with:
      - program_id: the escrow program (base58)
      - escrow_seeds: list of seed strings for PDA derivation (["escrow", gig_id])
      - milestone_index: 0-based index
      - accounts: ordered list of account metas the instruction expects
    """
    gig_id_bytes_hex = gig_id.encode("utf-8").hex()

    accounts: list[dict[str, Any]] = [
        # escrow PDA — derived by frontend from seeds + program_id
        {
            "pubkey": None,
            "is_signer": False,
            "is_writable": True,
            "is_escrow_pda": True,
        },
    ]

    if client_wallet:
        accounts.append(
            {"pubkey": client_wallet, "is_signer": True, "is_writable": True}
        )

    if freelancer_wallet:
        accounts.append(
            {"pubkey": freelancer_wallet, "is_signer": False, "is_writable": True}
        )

    accounts.append(
        {"pubkey": _SYSTEM_PROGRAM_ID, "is_signer": False, "is_writable": False}
    )

    return {
        "program_id": program_id,
        "escrow_seeds": ["escrow", gig_id_bytes_hex],
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

    if milestone.status == MilestoneStatus.DISPUTED:
        raise MilestoneApprovalError(
            "MILESTONE_DISPUTED",
            "Cannot approve a disputed milestone",
        )

    if (
        milestone.status not in _REVIEWABLE_STATUSES
        and milestone.status != MilestoneStatus.APPROVED
    ):
        raise MilestoneApprovalError(
            "MILESTONE_NOT_APPROVABLE",
            f"Milestone cannot be approved in status {milestone.status}",
        )

    if milestone.status != MilestoneStatus.APPROVED:
        milestone.status = MilestoneStatus.APPROVED
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

    milestone.status = MilestoneStatus.REVISION_REQUESTED
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

    Returns dict with: program_id, escrow_seeds, milestone_index, cluster, accounts.
    The frontend derives the PDA via PublicKey.findProgramAddress(escrow_seeds, program_id).
    """
    milestone, gig = await _fetch_milestone_and_gig(db, milestone_id, client_id)

    if milestone.status == MilestoneStatus.DISPUTED:
        raise MilestoneApprovalError(
            "MILESTONE_DISPUTED",
            "Cannot release funds for a disputed milestone",
        )

    if milestone.status != MilestoneStatus.APPROVED:
        raise MilestoneApprovalError(
            "MILESTONE_NOT_APPROVED",
            f"Milestone must be APPROVED before releasing funds; current status: {milestone.status}",
        )

    if not gig.escrow_pda:
        raise MilestoneApprovalError(
            "NO_CONTRACT_ADDRESS",
            "This gig does not have a deployed escrow contract address",
        )

    if not settings.escrow_program_id:
        raise MilestoneApprovalError(
            "NO_PROGRAM_ID",
            "Escrow program ID is not configured",
        )

    # Look up freelancer wallet from the user record
    freelancer_wallet: str | None = None
    if gig.freelancer_id:
        freelancer_result = await db.execute(
            select(UserModel).where(UserModel.id == gig.freelancer_id)
        )
        freelancer_user = freelancer_result.scalar_one_or_none()
        if freelancer_user:
            freelancer_wallet = freelancer_user.wallet_address

    # Look up client wallet from the user record
    client_wallet: str | None = None
    client_result = await db.execute(select(UserModel).where(UserModel.id == client_id))
    client_user = client_result.scalar_one_or_none()
    if client_user:
        client_wallet = client_user.wallet_address

    # Contract is 0-indexed; DB order is 1-indexed
    milestone_index = milestone.order - 1

    instruction_data = build_release_instruction_data(
        gig_id=gig.id,
        milestone_index=milestone_index,
        freelancer_wallet=freelancer_wallet,
        client_wallet=client_wallet,
        program_id=settings.escrow_program_id,
    )

    logger.info(
        "release-tx generated milestone_id=%s index=%d program=%s",
        milestone_id,
        milestone_index,
        settings.escrow_program_id,
    )

    return {
        "program_id": instruction_data["program_id"],
        "escrow_seeds": instruction_data["escrow_seeds"],
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

    if milestone.status != MilestoneStatus.APPROVED:
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

    milestone.status = MilestoneStatus.PAID
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
