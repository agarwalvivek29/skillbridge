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
    EscrowContractModel,
    GigModel,
    ProposalModel,
    SubmissionModel,
    UserModel,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/gigs", tags=["workspace"])

# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class WorkspaceGigOut(BaseModel):
    id: str
    title: str
    description: str
    status: str
    client_id: str
    freelancer_id: Optional[str]
    currency: str
    total_amount: str

    model_config = {"from_attributes": True}


class WorkspaceSubmissionOut(BaseModel):
    id: str
    freelancer_id: str
    repo_url: Optional[str]
    file_keys: list[str]
    notes: str
    status: str
    revision_number: int
    created_at: datetime

    model_config = {"from_attributes": True}


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
    submissions: list[WorkspaceSubmissionOut]

    model_config = {"from_attributes": True}


class WorkspaceProposalOut(BaseModel):
    freelancer_name: str
    cover_letter: str
    estimated_days: int


class WorkspaceEscrowOut(BaseModel):
    contract_address: str
    created_at: datetime


class WorkspaceOut(BaseModel):
    gig: WorkspaceGigOut
    milestones: list[WorkspaceMilestoneOut]
    proposal: Optional[WorkspaceProposalOut]
    escrow: Optional[WorkspaceEscrowOut]


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

    # Build milestones with recent submissions (latest 3 per milestone)
    milestones_out: list[WorkspaceMilestoneOut] = []
    for m in sorted(gig.milestones, key=lambda x: x.order):
        sub_result = await db.execute(
            select(SubmissionModel)
            .where(SubmissionModel.milestone_id == m.id)
            .order_by(SubmissionModel.created_at.desc())
            .limit(3)
        )
        submissions = list(sub_result.scalars().all())
        milestones_out.append(
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
                submissions=[
                    WorkspaceSubmissionOut(
                        id=s.id,
                        freelancer_id=s.freelancer_id,
                        repo_url=s.repo_url,
                        file_keys=s.file_keys or [],
                        notes=s.notes,
                        status=s.status,
                        revision_number=s.revision_number,
                        created_at=s.created_at,
                    )
                    for s in submissions
                ],
            )
        )

    # Accepted proposal info
    proposal_out: Optional[WorkspaceProposalOut] = None
    proposal_result = await db.execute(
        select(ProposalModel).where(
            ProposalModel.gig_id == gig_id,
            ProposalModel.status == "ACCEPTED",
        )
    )
    proposal = proposal_result.scalar_one_or_none()
    if proposal is not None:
        user_result = await db.execute(
            select(UserModel).where(UserModel.id == proposal.freelancer_id)
        )
        freelancer = user_result.scalar_one_or_none()
        proposal_out = WorkspaceProposalOut(
            freelancer_name=freelancer.name if freelancer else "Unknown",
            cover_letter=proposal.cover_letter,
            estimated_days=proposal.estimated_days,
        )

    # Escrow info
    escrow_out: Optional[WorkspaceEscrowOut] = None
    escrow_result = await db.execute(
        select(EscrowContractModel).where(EscrowContractModel.gig_id == gig_id)
    )
    escrow = escrow_result.scalar_one_or_none()
    if escrow is not None:
        escrow_out = WorkspaceEscrowOut(
            contract_address=escrow.contract_address,
            created_at=escrow.created_at,
        )

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
        ),
        milestones=milestones_out,
        proposal=proposal_out,
        escrow=escrow_out,
    )
