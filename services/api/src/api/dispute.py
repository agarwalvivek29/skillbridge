"""
api/dispute.py — Dispute resolution endpoints.

Endpoints:
  POST /v1/milestones/{milestone_id}/dispute          raise dispute (CLIENT or FREELANCER)
  GET  /v1/milestones/{milestone_id}/dispute           get active dispute for milestone
  GET  /v1/disputes/{dispute_id}                       get dispute with messages
  POST /v1/disputes/{dispute_id}/messages              post discussion message
  POST /v1/disputes/{dispute_id}/resolve               resolve dispute (ADMIN only)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api._roles import ROLE_ADMIN
from src.domain.dispute import (
    DisputeError,
    generate_ai_evidence,
    get_dispute,
    get_dispute_by_milestone,
    post_dispute_message,
    raise_dispute,
    resolve_dispute,
)
from src.infra.database import get_db
from src.infra.models import GigModel, MilestoneModel
from src.infra.web3_client import OnChainError, call_resolve_dispute_on_chain

logger = logging.getLogger(__name__)

milestone_dispute_router = APIRouter(prefix="/v1/milestones", tags=["disputes"])
dispute_router = APIRouter(prefix="/v1/disputes", tags=["disputes"])

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class RaiseDisputeBody(BaseModel):
    reason: str


class PostMessageBody(BaseModel):
    content: str


class ResolveDisputeBody(BaseModel):
    resolution: str
    freelancer_split_amount: Optional[str] = None


class DisputeMessageOut(BaseModel):
    id: str
    dispute_id: str
    user_id: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DisputeOut(BaseModel):
    id: str
    milestone_id: str
    gig_id: str
    raised_by_user_id: str
    reason: str
    status: str
    ai_evidence_summary: Optional[str]
    resolution: Optional[str]
    freelancer_split_amount: Optional[str]
    resolution_tx_hash: Optional[str]
    discussion_deadline: datetime
    resolved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    messages: list[DisputeMessageOut] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATUS_CODE_MAP = {
    "MILESTONE_NOT_FOUND": 404,
    "GIG_NOT_FOUND": 404,
    "DISPUTE_NOT_FOUND": 404,
    "FORBIDDEN": 403,
    "MILESTONE_NOT_DISPUTABLE": 409,
    "DISPUTE_ALREADY_EXISTS": 409,
    "DISPUTE_NOT_OPEN": 409,
    "DISCUSSION_DEADLINE_PASSED": 409,
    "DISPUTE_NOT_RESOLVABLE": 409,
    "INVALID_RESOLUTION": 400,
    "SPLIT_AMOUNT_REQUIRED": 400,
    "ON_CHAIN_FAILED": 502,
}


def _handle_dispute_error(exc: DisputeError) -> HTTPException:
    http_status = _STATUS_CODE_MAP.get(exc.code, 400)
    return HTTPException(
        status_code=http_status,
        detail={"code": exc.code, "message": exc.message, "field_errors": []},
    )


def _require_auth(request: Request) -> tuple[str, str]:
    """Extract user_id and role from request state. Returns (user_id, role)."""
    user_id: str = getattr(request.state, "user_id", "")
    role: str = getattr(request.state, "role", "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required"},
        )
    return user_id, role


def _require_admin(request: Request) -> str:
    """Extract user_id and enforce ADMIN role. Returns user_id."""
    user_id, role = _require_auth(request)
    if role != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Only ADMIN-role users may resolve disputes",
            },
        )
    return user_id


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@milestone_dispute_router.post(
    "/{milestone_id}/dispute",
    response_model=DisputeOut,
    status_code=status.HTTP_201_CREATED,
)
async def raise_dispute_endpoint(
    milestone_id: str,
    body: RaiseDisputeBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> DisputeOut:
    """Raise a dispute on a milestone. CLIENT or FREELANCER role."""
    user_id, _role = _require_auth(request)

    try:
        dispute = await raise_dispute(db, user_id, milestone_id, body.reason)
    except DisputeError as exc:
        raise _handle_dispute_error(exc)

    # Trigger AI evidence generation in background (best-effort)
    try:
        await generate_ai_evidence(db, dispute.id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ai_evidence generation failed for dispute_id=%s: %s", dispute.id, exc
        )

    # Re-fetch with eager-loaded messages after AI evidence generation
    refreshed = await get_dispute(db, dispute.id)
    return DisputeOut.model_validate(refreshed)


@milestone_dispute_router.get(
    "/{milestone_id}/dispute",
    response_model=DisputeOut,
)
async def get_milestone_dispute_endpoint(
    milestone_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> DisputeOut:
    """Get the active dispute for a milestone."""
    _require_auth(request)

    dispute = await get_dispute_by_milestone(db, milestone_id)
    if dispute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "DISPUTE_NOT_FOUND",
                "message": f"No dispute found for milestone {milestone_id}",
            },
        )
    return DisputeOut.model_validate(dispute)


@dispute_router.get(
    "/{dispute_id}",
    response_model=DisputeOut,
)
async def get_dispute_endpoint(
    dispute_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> DisputeOut:
    """Get a dispute with messages."""
    _require_auth(request)

    dispute = await get_dispute(db, dispute_id)
    if dispute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "DISPUTE_NOT_FOUND",
                "message": f"Dispute {dispute_id} not found",
            },
        )
    return DisputeOut.model_validate(dispute)


@dispute_router.post(
    "/{dispute_id}/messages",
    response_model=DisputeMessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def post_message_endpoint(
    dispute_id: str,
    body: PostMessageBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> DisputeMessageOut:
    """Post a message in a dispute discussion. CLIENT or FREELANCER, while OPEN."""
    user_id, _role = _require_auth(request)

    try:
        message = await post_dispute_message(db, user_id, dispute_id, body.content)
    except DisputeError as exc:
        raise _handle_dispute_error(exc)

    return DisputeMessageOut.model_validate(message)


@dispute_router.post(
    "/{dispute_id}/resolve",
    response_model=DisputeOut,
    status_code=status.HTTP_200_OK,
)
async def resolve_dispute_endpoint(
    dispute_id: str,
    body: ResolveDisputeBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> DisputeOut:
    """Resolve a dispute. ADMIN role only. Calls GigEscrow.resolveDispute() on-chain."""
    _require_admin(request)

    # Load dispute to get gig_id and milestone_id
    dispute_row = await get_dispute(db, dispute_id)
    if dispute_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "DISPUTE_NOT_FOUND",
                "message": f"Dispute {dispute_id} not found",
            },
        )

    # Look up the gig's escrow contract address
    gig_result = await db.execute(
        select(GigModel).where(GigModel.id == dispute_row.gig_id)
    )
    gig = gig_result.scalar_one_or_none()
    contract_address = gig.contract_address if gig else None

    # Fail-fast: call on-chain BEFORE updating DB (skip if no contract deployed)
    tx_hash = ""
    if contract_address:
        # Determine milestone index (0-based position within the gig)
        milestone_index = 0
        ms_result = await db.execute(
            select(MilestoneModel)
            .where(MilestoneModel.gig_id == gig.id)
            .order_by(MilestoneModel.created_at)
        )
        milestones = list(ms_result.scalars().all())
        for i, m in enumerate(milestones):
            if m.id == dispute_row.milestone_id:
                milestone_index = i
                break

        try:
            tx_hash = await call_resolve_dispute_on_chain(
                contract_address=contract_address,
                milestone_index=milestone_index,
                resolution=body.resolution,
                freelancer_split_amount=body.freelancer_split_amount,
            )
        except OnChainError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "ON_CHAIN_FAILED",
                    "message": str(exc),
                    "field_errors": [],
                },
            )
    else:
        logger.warning(
            "dispute %s: gig has no contract_address, skipping on-chain call",
            dispute_id,
        )

    try:
        dispute = await resolve_dispute(
            db,
            dispute_id,
            body.resolution,
            body.freelancer_split_amount,
            tx_hash,
        )
    except DisputeError as exc:
        raise _handle_dispute_error(exc)

    return DisputeOut.model_validate(dispute)
