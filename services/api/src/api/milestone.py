"""
api/milestone.py — Milestone approval and fund release endpoints.

Endpoints:
  POST /v1/milestones/{milestone_id}/approve          approve milestone (CLIENT role)
  POST /v1/milestones/{milestone_id}/request-revision request changes (CLIENT role)
  GET  /v1/milestones/{milestone_id}/release-tx       get Solana instruction data for on-chain release (CLIENT role)
  POST /v1/milestones/{milestone_id}/confirm-release  record tx_hash after broadcast (CLIENT role)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.milestone_approval import (
    MilestoneApprovalError,
    approve_milestone,
    confirm_release,
    get_release_tx,
    request_revision,
)
from src.infra.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/milestones", tags=["milestones"])

_CLIENT_ROLE = "USER_ROLE_CLIENT"

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class RequestRevisionBody(BaseModel):
    reason: str


class ConfirmReleaseBody(BaseModel):
    tx_hash: str


class MilestoneOut(BaseModel):
    id: str
    gig_id: str
    title: str
    description: str
    acceptance_criteria: str
    amount: str
    order: int
    due_date: Optional[datetime]
    status: str
    revision_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AccountMeta(BaseModel):
    pubkey: str | None
    is_signer: bool
    is_writable: bool
    is_escrow_pda: bool = False


class ReleaseTxOut(BaseModel):
    program_id: str
    escrow_seeds: list[str]
    milestone_index: int
    cluster: str
    accounts: list[AccountMeta]


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def require_client(request: Request) -> str:
    """FastAPI dependency: extracts user_id and enforces CLIENT role."""
    user_id: str = getattr(request.state, "user_id", "")
    role: str = getattr(request.state, "role", "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required"},
        )
    if role != _CLIENT_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Only CLIENT-role users may perform this action",
            },
        )
    return user_id


_STATUS_CODE_MAP = {
    "MILESTONE_NOT_FOUND": 404,
    "GIG_NOT_FOUND": 404,
    "FORBIDDEN": 403,
    "MILESTONE_DISPUTED": 409,
    "MILESTONE_NOT_APPROVABLE": 409,
    "MILESTONE_NOT_REVISABLE": 409,
    "MILESTONE_NOT_APPROVED": 409,
    "NO_CONTRACT_ADDRESS": 409,
}


def _handle_approval_error(exc: MilestoneApprovalError) -> HTTPException:
    http_status = _STATUS_CODE_MAP.get(exc.code, 400)
    return HTTPException(
        status_code=http_status,
        detail={"code": exc.code, "message": exc.message, "field_errors": []},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{milestone_id}/approve",
    response_model=MilestoneOut,
    status_code=status.HTTP_200_OK,
)
async def approve_milestone_endpoint(
    milestone_id: str,
    client_id: str = Depends(require_client),
    db: AsyncSession = Depends(get_db),
) -> MilestoneOut:
    """
    Approve a milestone. CLIENT role only.
    Milestone must be in UNDER_REVIEW or SUBMITTED status (APPROVED is idempotent).
    """
    try:
        milestone = await approve_milestone(db, milestone_id, client_id)
    except MilestoneApprovalError as exc:
        raise _handle_approval_error(exc)
    return MilestoneOut.model_validate(milestone)


@router.post(
    "/{milestone_id}/request-revision",
    response_model=MilestoneOut,
    status_code=status.HTTP_200_OK,
)
async def request_revision_endpoint(
    milestone_id: str,
    body: RequestRevisionBody,
    client_id: str = Depends(require_client),
    db: AsyncSession = Depends(get_db),
) -> MilestoneOut:
    """Request a revision on a milestone. CLIENT role only. Milestone must be UNDER_REVIEW or SUBMITTED."""
    try:
        milestone = await request_revision(db, milestone_id, client_id, body.reason)
    except MilestoneApprovalError as exc:
        raise _handle_approval_error(exc)
    return MilestoneOut.model_validate(milestone)


@router.get(
    "/{milestone_id}/release-tx",
    response_model=ReleaseTxOut,
    status_code=status.HTTP_200_OK,
)
async def get_release_tx_endpoint(
    milestone_id: str,
    client_id: str = Depends(require_client),
    db: AsyncSession = Depends(get_db),
) -> ReleaseTxOut:
    """
    Return Solana instruction data for the escrow program's complete_milestone instruction.
    CLIENT role only. Milestone must be APPROVED and gig must have a contract_address.
    """
    try:
        tx_data = await get_release_tx(db, milestone_id, client_id)
    except MilestoneApprovalError as exc:
        raise _handle_approval_error(exc)
    return ReleaseTxOut(**tx_data)


@router.post(
    "/{milestone_id}/confirm-release",
    response_model=MilestoneOut,
    status_code=status.HTTP_200_OK,
)
async def confirm_release_endpoint(
    milestone_id: str,
    body: ConfirmReleaseBody,
    client_id: str = Depends(require_client),
    db: AsyncSession = Depends(get_db),
) -> MilestoneOut:
    """
    Record an on-chain fund release after the client broadcasts the tx.
    Sets milestone → PAID and stores tx_hash on the milestone. CLIENT role only.
    """
    try:
        milestone = await confirm_release(db, milestone_id, client_id, body.tx_hash)
    except MilestoneApprovalError as exc:
        raise _handle_approval_error(exc)
    return MilestoneOut.model_validate(milestone)
