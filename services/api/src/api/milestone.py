"""
api/milestone.py — Milestone approval and fund release endpoints.

Endpoints:
  GET  /v1/milestones/{milestone_id}                  get single milestone with gig context (auth required)
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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.milestone_approval import (
    MilestoneApprovalError,
    approve_milestone,
    confirm_release,
    get_release_tx,
    request_revision,
)
from src.domain.enums import UserRole
from src.infra.database import get_db
from src.infra.models import (
    GigModel,
    MilestoneModel,
    ReviewReportModel,
    SubmissionModel,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/milestones", tags=["milestones"])

_CLIENT_ROLE = UserRole.CLIENT

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
    contract_index: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubmissionOut(BaseModel):
    id: str
    milestone_id: str
    freelancer_id: str
    repo_url: Optional[str] = None
    file_keys: list[str] = []
    notes: str = ""
    revision_number: int = 1
    status: str
    created_at: str


class ReviewReportOut(BaseModel):
    id: str
    submission_id: str
    verdict: str
    score: int
    body: str
    model_version: str
    created_at: str


class MilestoneDetailOut(BaseModel):
    id: str
    gig_id: str
    gig_title: str
    client_id: str
    freelancer_id: Optional[str] = None
    title: str
    description: str
    acceptance_criteria: str
    amount: str
    currency: str = "ETH"
    order: int
    due_date: Optional[datetime] = None
    status: str
    revision_count: int
    contract_index: int | None = None
    revision_feedback: Optional[str] = None
    submissions: list[SubmissionOut] = []
    latest_review: Optional[ReviewReportOut] = None
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


def _require_auth(request: Request) -> str:
    """FastAPI dependency: extracts user_id and enforces authentication."""
    user_id: str = getattr(request.state, "user_id", "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required"},
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


@router.get(
    "/{milestone_id}",
    response_model=MilestoneDetailOut,
    status_code=status.HTTP_200_OK,
)
async def get_milestone_endpoint(
    milestone_id: str,
    _user_id: str = Depends(_require_auth),
    db: AsyncSession = Depends(get_db),
) -> MilestoneDetailOut:
    """
    Return a single milestone with its parent gig context.
    Auth required (any role).
    """
    result = await db.execute(
        select(MilestoneModel).where(MilestoneModel.id == milestone_id)
    )
    milestone = result.scalar_one_or_none()
    if milestone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "MILESTONE_NOT_FOUND",
                "message": f"Milestone {milestone_id} not found",
            },
        )

    gig_result = await db.execute(
        select(GigModel).where(GigModel.id == milestone.gig_id)
    )
    gig = gig_result.scalar_one_or_none()
    if gig is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "GIG_NOT_FOUND",
                "message": f"Gig for milestone {milestone_id} not found",
            },
        )

    # Fetch submissions for this milestone
    sub_result = await db.execute(
        select(SubmissionModel)
        .where(SubmissionModel.milestone_id == milestone_id)
        .order_by(SubmissionModel.created_at.desc())
    )
    submissions = list(sub_result.scalars().all())
    submission_outs = [
        SubmissionOut(
            id=s.id,
            milestone_id=s.milestone_id,
            freelancer_id=s.freelancer_id,
            repo_url=s.repo_url,
            file_keys=s.file_keys or [],
            notes=s.notes or "",
            revision_number=s.revision_number,
            status=s.status,
            created_at=s.created_at.isoformat() if s.created_at else "",
        )
        for s in submissions
    ]

    # Fetch latest review report (from the most recent submission)
    latest_review = None
    if submissions:
        review_result = await db.execute(
            select(ReviewReportModel)
            .where(ReviewReportModel.submission_id.in_([s.id for s in submissions]))
            .order_by(ReviewReportModel.created_at.desc())
            .limit(1)
        )
        report = review_result.scalar_one_or_none()
        if report:
            latest_review = ReviewReportOut(
                id=report.id,
                submission_id=report.submission_id,
                verdict=report.verdict,
                score=report.score,
                body=report.body,
                model_version=report.model_version,
                created_at=report.created_at.isoformat() if report.created_at else "",
            )

    return MilestoneDetailOut(
        id=milestone.id,
        gig_id=gig.id,
        gig_title=gig.title,
        client_id=gig.client_id,
        freelancer_id=gig.freelancer_id,
        title=milestone.title,
        description=milestone.description,
        acceptance_criteria=milestone.acceptance_criteria,
        amount=milestone.amount,
        currency=gig.currency,
        order=milestone.order,
        due_date=milestone.due_date,
        status=milestone.status,
        revision_count=milestone.revision_count,
        contract_index=milestone.contract_index,
        submissions=submission_outs,
        latest_review=latest_review,
        created_at=milestone.created_at,
        updated_at=milestone.updated_at,
    )


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
