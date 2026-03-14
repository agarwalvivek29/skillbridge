"""
api/workspace.py — Workspace aggregate endpoint.

Endpoints:
  GET /v1/gigs/{gig_id}/workspace  aggregate view for gig workspace (auth required)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infra.database import get_db
from src.infra.models import (
    GigModel,
    ReviewReportModel,
    SubmissionModel,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/gigs", tags=["workspace"])

# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class WorkspaceMilestoneOut(BaseModel):
    id: str
    title: str
    description: str
    acceptance_criteria: str
    amount: str
    order: int
    due_date: Optional[datetime]
    status: str
    revision_count: int

    model_config = {"from_attributes": True}


class WorkspaceGigOut(BaseModel):
    id: str
    title: str
    description: str
    status: str
    client_id: str
    freelancer_id: Optional[str]
    currency: str
    total_amount: str
    milestones: list[WorkspaceMilestoneOut]

    model_config = {"from_attributes": True}


class WorkspaceSubmissionOut(BaseModel):
    id: str
    milestone_id: str
    repo_url: Optional[str]
    file_keys: list[str]
    notes: Optional[str]
    review_verdict: Optional[str]
    review_score: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkspaceOut(BaseModel):
    gig: WorkspaceGigOut
    submissions: list[WorkspaceSubmissionOut]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_auth(request: Request) -> str:
    """Extract user_id from request state. Returns user_id."""
    user_id: str = getattr(request.state, "user_id", "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required"},
        )
    return user_id


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get("/{gig_id}/workspace", response_model=WorkspaceOut)
async def get_workspace(
    gig_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> WorkspaceOut:
    """
    Aggregate endpoint returning everything needed for the gig workspace view.
    Auth required. Only the gig's client or assigned freelancer can access.
    """
    user_id = _require_auth(request)

    # Fetch gig with milestones
    result = await db.execute(
        select(GigModel)
        .where(GigModel.id == gig_id)
        .options(selectinload(GigModel.milestones))
    )
    gig = result.scalar_one_or_none()
    if gig is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "GIG_NOT_FOUND", "message": f"Gig {gig_id} not found"},
        )

    # Authorization: must be client or assigned freelancer
    if gig.client_id != user_id and gig.freelancer_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Only the gig client or assigned freelancer can access this workspace",
            },
        )

    # Build milestones list (without submissions — submissions are returned flat)
    milestones_out = [
        WorkspaceMilestoneOut(
            id=m.id,
            title=m.title,
            description=m.description,
            acceptance_criteria=m.acceptance_criteria,
            amount=m.amount,
            order=m.order,
            due_date=m.due_date,
            status=m.status,
            revision_count=m.revision_count,
        )
        for m in sorted(gig.milestones, key=lambda x: x.order)
    ]

    # Batch-load all submissions for this gig's milestones in one query
    milestone_ids = [m.id for m in gig.milestones]
    submissions_out: list[WorkspaceSubmissionOut] = []
    if milestone_ids:
        sub_result = await db.execute(
            select(SubmissionModel)
            .where(SubmissionModel.milestone_id.in_(milestone_ids))
            .order_by(SubmissionModel.created_at.desc())
        )
        submissions = list(sub_result.scalars().all())

        # Batch-load review reports for all fetched submissions
        submission_ids = [s.id for s in submissions]
        report_by_sub: dict[str, ReviewReportModel] = {}
        if submission_ids:
            report_result = await db.execute(
                select(ReviewReportModel).where(
                    ReviewReportModel.submission_id.in_(submission_ids)
                )
            )
            for report in report_result.scalars().all():
                report_by_sub[report.submission_id] = report

        submissions_out = [
            WorkspaceSubmissionOut(
                id=s.id,
                milestone_id=s.milestone_id,
                repo_url=s.repo_url,
                file_keys=s.file_keys or [],
                notes=s.notes,
                review_verdict=report_by_sub[s.id].verdict
                if s.id in report_by_sub
                else None,
                review_score=report_by_sub[s.id].score
                if s.id in report_by_sub
                else None,
                created_at=s.created_at,
            )
            for s in submissions
        ]

    return WorkspaceOut(
        gig=WorkspaceGigOut(
            id=gig.id,
            title=gig.title,
            description=gig.description,
            status=gig.status,
            client_id=gig.client_id,
            freelancer_id=gig.freelancer_id,
            currency=gig.currency,
            total_amount=gig.total_amount,
            milestones=milestones_out,
        ),
        submissions=submissions_out,
    )
