"""
domain/proposal.py — Business logic for gig proposals.
No FastAPI imports. All side-effect-free helpers + DB-taking functions.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.models import GigModel, NotificationModel, ProposalModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FREELANCER_ROLE = "USER_ROLE_FREELANCER"
_CLIENT_ROLE = "USER_ROLE_CLIENT"

_PROPOSAL_PENDING = "PENDING"
_PROPOSAL_ACCEPTED = "ACCEPTED"
_PROPOSAL_REJECTED = "REJECTED"
_PROPOSAL_WITHDRAWN = "WITHDRAWN"

_GIG_OPEN = "OPEN"
_GIG_IN_PROGRESS = "IN_PROGRESS"

_NOTIF_PROPOSAL_RECEIVED = "NOTIFICATION_TYPE_PROPOSAL_RECEIVED"
_NOTIF_PROPOSAL_ACCEPTED = "NOTIFICATION_TYPE_PROPOSAL_ACCEPTED"
_NOTIF_PROPOSAL_REJECTED = "NOTIFICATION_TYPE_PROPOSAL_REJECTED"


# ---------------------------------------------------------------------------
# Domain-level data classes (input DTOs only)
# ---------------------------------------------------------------------------


@dataclass
class CreateProposalInput:
    gig_id: str
    cover_letter: str
    estimated_days: int


# ---------------------------------------------------------------------------
# Validation error
# ---------------------------------------------------------------------------


class ProposalError(ValueError):
    """Raised when proposal data fails business-rule validation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _notification(user_id: str, notif_type: str, payload: dict) -> NotificationModel:
    return NotificationModel(
        user_id=user_id,
        type=notif_type,
        payload_json=json.dumps(payload),
    )


# ---------------------------------------------------------------------------
# Domain functions
# ---------------------------------------------------------------------------


async def create_proposal(
    db: AsyncSession,
    freelancer_id: str,
    data: CreateProposalInput,
) -> ProposalModel:
    """
    Submit a proposal for an OPEN gig.

    Raises ProposalError if:
    - gig not found or not OPEN
    - freelancer already has a proposal for this gig
    - estimated_days < 1
    """
    if data.estimated_days < 1:
        raise ProposalError(
            "INVALID_ESTIMATED_DAYS",
            "estimated_days must be at least 1",
        )

    gig_result = await db.execute(select(GigModel).where(GigModel.id == data.gig_id))
    gig = gig_result.scalar_one_or_none()
    if gig is None:
        raise ProposalError("GIG_NOT_FOUND", f"Gig {data.gig_id} not found")
    if gig.status != _GIG_OPEN:
        raise ProposalError(
            "GIG_NOT_OPEN",
            f"Proposals can only be submitted for OPEN gigs (current status: {gig.status})",
        )

    existing = await db.execute(
        select(ProposalModel).where(
            ProposalModel.gig_id == data.gig_id,
            ProposalModel.freelancer_id == freelancer_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ProposalError(
            "DUPLICATE_PROPOSAL",
            "You have already submitted a proposal for this gig",
        )

    proposal = ProposalModel(
        gig_id=data.gig_id,
        freelancer_id=freelancer_id,
        cover_letter=data.cover_letter,
        estimated_days=data.estimated_days,
        status=_PROPOSAL_PENDING,
    )
    db.add(proposal)

    # proposal.id is Python-generated on instantiation — safe to use before flush
    db.add(
        _notification(
            gig.client_id,
            _NOTIF_PROPOSAL_RECEIVED,
            {
                "gig_id": gig.id,
                "proposal_id": proposal.id,
                "freelancer_id": freelancer_id,
            },
        )
    )
    await db.flush()
    await db.refresh(proposal)
    logger.info(
        "proposal created proposal_id=%s gig_id=%s freelancer_id=%s",
        proposal.id,
        data.gig_id,
        freelancer_id,
    )
    return proposal


async def list_proposals(
    db: AsyncSession,
    gig_id: str,
    client_id: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ProposalModel], int]:
    """
    Return paginated proposals for a gig.

    Raises ProposalError if gig not found or caller is not the gig client.
    """
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size

    gig_result = await db.execute(select(GigModel).where(GigModel.id == gig_id))
    gig = gig_result.scalar_one_or_none()
    if gig is None:
        raise ProposalError("GIG_NOT_FOUND", f"Gig {gig_id} not found")
    if gig.client_id != client_id:
        raise ProposalError("FORBIDDEN", "Only the gig owner may view proposals")

    count_result = await db.execute(
        select(func.count())
        .select_from(ProposalModel)
        .where(ProposalModel.gig_id == gig_id)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(ProposalModel)
        .where(ProposalModel.gig_id == gig_id)
        .order_by(ProposalModel.created_at.asc())
        .offset(offset)
        .limit(page_size)
    )
    proposals = list(result.scalars().all())
    return proposals, total


async def accept_proposal(
    db: AsyncSession,
    proposal_id: str,
    client_id: str,
) -> ProposalModel:
    """
    Accept a proposal.

    Side effects:
    - Accepted proposal → ACCEPTED
    - All other PENDING proposals for same gig → REJECTED
    - Gig → IN_PROGRESS, freelancer_id set
    - Notifications: ACCEPTED → freelancer, REJECTED → other freelancers

    Raises ProposalError if:
    - proposal not found
    - caller is not the gig client
    - gig is not OPEN
    - proposal is not PENDING
    """
    proposal_result = await db.execute(
        select(ProposalModel).where(ProposalModel.id == proposal_id)
    )
    proposal = proposal_result.scalar_one_or_none()
    if proposal is None:
        raise ProposalError("PROPOSAL_NOT_FOUND", f"Proposal {proposal_id} not found")

    gig_result = await db.execute(
        select(GigModel).where(GigModel.id == proposal.gig_id).with_for_update()
    )
    gig = gig_result.scalar_one_or_none()
    if gig is None:
        raise ProposalError("GIG_NOT_FOUND", f"Gig {proposal.gig_id} not found")
    if gig.client_id != client_id:
        raise ProposalError("FORBIDDEN", "Only the gig owner may accept proposals")
    if gig.status != _GIG_OPEN:
        raise ProposalError(
            "GIG_NOT_OPEN",
            f"Proposals can only be accepted for OPEN gigs (current status: {gig.status})",
        )
    if proposal.status != _PROPOSAL_PENDING:
        raise ProposalError(
            "PROPOSAL_NOT_PENDING",
            f"Only PENDING proposals can be accepted (current status: {proposal.status})",
        )

    # Accept this proposal
    proposal.status = _PROPOSAL_ACCEPTED

    # Reject all other PENDING proposals for this gig
    other_result = await db.execute(
        select(ProposalModel).where(
            ProposalModel.gig_id == proposal.gig_id,
            ProposalModel.id != proposal_id,
            ProposalModel.status == _PROPOSAL_PENDING,
        )
    )
    other_proposals = list(other_result.scalars().all())
    for other in other_proposals:
        other.status = _PROPOSAL_REJECTED
        db.add(
            _notification(
                other.freelancer_id,
                _NOTIF_PROPOSAL_REJECTED,
                {"gig_id": gig.id, "proposal_id": other.id},
            )
        )

    # Update gig status and assign freelancer
    gig.status = _GIG_IN_PROGRESS
    gig.freelancer_id = proposal.freelancer_id

    # Notify the accepted freelancer
    db.add(
        _notification(
            proposal.freelancer_id,
            _NOTIF_PROPOSAL_ACCEPTED,
            {"gig_id": gig.id, "proposal_id": proposal.id},
        )
    )

    await db.flush()
    await db.refresh(proposal)
    logger.info(
        "proposal accepted proposal_id=%s gig_id=%s freelancer_id=%s",
        proposal.id,
        gig.id,
        proposal.freelancer_id,
    )
    return proposal


async def withdraw_proposal(
    db: AsyncSession,
    proposal_id: str,
    freelancer_id: str,
) -> ProposalModel:
    """
    Withdraw a PENDING proposal.

    Raises ProposalError if:
    - proposal not found
    - caller is not the proposal owner
    - proposal is not PENDING
    """
    result = await db.execute(
        select(ProposalModel).where(ProposalModel.id == proposal_id)
    )
    proposal = result.scalar_one_or_none()
    if proposal is None:
        raise ProposalError("PROPOSAL_NOT_FOUND", f"Proposal {proposal_id} not found")
    if proposal.freelancer_id != freelancer_id:
        raise ProposalError("FORBIDDEN", "Only the proposal owner may withdraw it")
    if proposal.status != _PROPOSAL_PENDING:
        raise ProposalError(
            "PROPOSAL_NOT_PENDING",
            f"Only PENDING proposals can be withdrawn (current status: {proposal.status})",
        )

    proposal.status = _PROPOSAL_WITHDRAWN
    await db.flush()
    await db.refresh(proposal)
    logger.info(
        "proposal withdrawn proposal_id=%s freelancer_id=%s",
        proposal.id,
        freelancer_id,
    )
    return proposal
