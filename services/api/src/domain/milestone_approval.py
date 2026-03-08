"""
domain/milestone_approval.py — Business logic for milestone approval and fund release.

Implements:
- approve_milestone: CLIENT manually approves a milestone
- request_revision: CLIENT requests changes on a milestone
- get_release_tx: returns ABI-encoded calldata for GigEscrow.completeMilestone(index)
- confirm_release: records tx_hash after client broadcasts the on-chain tx

No FastAPI imports. All domain logic lives here; routers stay thin.
"""

from __future__ import annotations

import json
import logging

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

_APPROVABLE_STATUSES = {"UNDER_REVIEW", "SUBMITTED"}
_REVISION_REQUESTABLE_STATUSES = {"UNDER_REVIEW", "SUBMITTED"}

_NOTIFICATION_TYPE_MILESTONE_APPROVED = "NOTIFICATION_TYPE_MILESTONE_APPROVED"
_NOTIFICATION_TYPE_REVISION_REQUESTED = "NOTIFICATION_TYPE_REVISION_REQUESTED"
_NOTIFICATION_TYPE_FUNDS_RELEASED = "NOTIFICATION_TYPE_FUNDS_RELEASED"

# keccak256("completeMilestone(uint256)")[:4] = 0x5a36fb08
_COMPLETE_MILESTONE_SELECTOR = bytes.fromhex("5a36fb08")

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


def _encode_complete_milestone_calldata(milestone_index: int) -> str:
    """
    ABI-encode a call to completeMilestone(uint256 index).

    Encoding:
      - 4-byte selector: 5a36fb08
      - 32-byte big-endian uint256: milestone_index
    Returns a 0x-prefixed hex string (36 bytes = 72 hex chars + 2 for '0x').
    """
    encoded_index = milestone_index.to_bytes(32, "big")
    return "0x" + (_COMPLETE_MILESTONE_SELECTOR + encoded_index).hex()


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

    Side effects:
    - milestone.status → APPROVED
    - NotificationModel created for the gig's freelancer
    """
    milestone, gig = await _fetch_milestone_and_gig(db, milestone_id, client_id)

    if milestone.status == "DISPUTED":
        raise MilestoneApprovalError(
            "MILESTONE_DISPUTED",
            "Cannot approve a disputed milestone",
        )

    if milestone.status not in _APPROVABLE_STATUSES and milestone.status != "APPROVED":
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

    if milestone.status not in _REVISION_REQUESTABLE_STATUSES:
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
    Return ABI-encoded calldata for GigEscrow.completeMilestone(index).

    Validates:
    - Milestone exists and caller is the gig's client
    - Milestone is APPROVED (not DISPUTED or any other status)
    - Gig has a contract_address set

    Returns dict with: contract_address, milestone_index, chain_id, calldata
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

    # Contract is 0-indexed; DB order is 1-indexed
    milestone_index = milestone.order - 1
    calldata = _encode_complete_milestone_calldata(milestone_index)

    logger.info(
        "release-tx generated milestone_id=%s index=%d contract=%s",
        milestone_id,
        milestone_index,
        gig.contract_address,
    )

    return {
        "contract_address": gig.contract_address,
        "milestone_index": milestone_index,
        "chain_id": settings.base_chain_id,
        "calldata": calldata,
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

    Side effects:
    - milestone.status → PAID
    - EscrowContractModel.release_tx_hash set if a record exists for this gig
    - NotificationModel created for the gig's freelancer
    """
    milestone, gig = await _fetch_milestone_and_gig(db, milestone_id, client_id)

    if milestone.status != "APPROVED":
        raise MilestoneApprovalError(
            "MILESTONE_NOT_APPROVED",
            f"Milestone must be APPROVED to confirm release; current status: {milestone.status}",
        )

    milestone.status = "PAID"
    await db.flush()

    # Store tx_hash on the EscrowContract record if one exists for this gig
    escrow_result = await db.execute(
        select(EscrowContractModel).where(EscrowContractModel.gig_id == gig.id)
    )
    escrow = escrow_result.scalar_one_or_none()
    if escrow is not None:
        escrow.release_tx_hash = tx_hash
        await db.flush()
    else:
        logger.warning(
            "confirm_release: no EscrowContractModel found for gig_id=%s; tx_hash=%s not stored",
            gig.id,
            tx_hash,
        )

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
