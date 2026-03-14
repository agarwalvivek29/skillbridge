"""
api/proposal.py — Proposal endpoints.

Endpoints:
  POST   /v1/proposals                          submit proposal (FREELANCER role)
  GET    /v1/gigs/{gig_id}/proposals            list proposals for a gig (CLIENT, gig owner)
  GET    /v1/gigs/{gig_id}/proposals/mine       get own proposal for a gig (FREELANCER)
  POST   /v1/proposals/{proposal_id}/accept     accept a proposal (CLIENT, gig owner)
  POST   /v1/proposals/{proposal_id}/reject     reject a proposal (CLIENT, gig owner)
  POST   /v1/proposals/{proposal_id}/withdraw   withdraw a proposal (FREELANCER, proposal owner)
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.proposal import (
    CreateProposalInput,
    ProposalError,
    accept_proposal,
    create_proposal,
    get_my_proposal,
    list_proposals,
    reject_proposal,
    withdraw_proposal,
)
from src.domain.enums import UserRole
from src.infra.database import get_db
from src.infra.models import ProposalModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["proposals"])

_FREELANCER_ROLE = UserRole.FREELANCER
_CLIENT_ROLE = UserRole.CLIENT

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class CreateProposalRequest(BaseModel):
    gig_id: str
    cover_letter: str
    estimated_days: int

    @field_validator("estimated_days")
    @classmethod
    def estimated_days_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("estimated_days must be at least 1")
        return v

    @field_validator("cover_letter")
    @classmethod
    def cover_letter_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("cover_letter must not be empty")
        return v


class ProposalOut(BaseModel):
    id: str
    gig_id: str
    freelancer_id: str
    cover_letter: str
    estimated_days: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProposalListOut(BaseModel):
    proposals: list[ProposalOut]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_freelancer(request: Request) -> str:
    user_id: str = getattr(request.state, "user_id", "")
    role: str = getattr(request.state, "role", "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required"},
        )
    if role != _FREELANCER_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Only FREELANCER-role users may perform this action",
            },
        )
    return user_id


def _require_client(request: Request) -> str:
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


def _handle_proposal_error(exc: ProposalError) -> HTTPException:
    status_map = {
        "GIG_NOT_FOUND": 404,
        "PROPOSAL_NOT_FOUND": 404,
        "FORBIDDEN": 403,
        "GIG_NOT_OPEN": 409,
        "PROPOSAL_NOT_PENDING": 409,
        "DUPLICATE_PROPOSAL": 409,
    }
    http_status = status_map.get(exc.code, 400)
    return HTTPException(
        status_code=http_status,
        detail={"code": exc.code, "message": exc.message, "field_errors": []},
    )


def _proposal_to_out(p: ProposalModel) -> ProposalOut:
    return ProposalOut(
        id=p.id,
        gig_id=p.gig_id,
        freelancer_id=p.freelancer_id,
        cover_letter=p.cover_letter,
        estimated_days=p.estimated_days,
        status=p.status,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/v1/proposals",
    response_model=ProposalOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_proposal_endpoint(
    body: CreateProposalRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ProposalOut:
    """Submit a proposal for an OPEN gig. Requires FREELANCER role."""
    freelancer_id = _require_freelancer(request)

    try:
        proposal = await create_proposal(
            db,
            freelancer_id,
            CreateProposalInput(
                gig_id=body.gig_id,
                cover_letter=body.cover_letter,
                estimated_days=body.estimated_days,
            ),
        )
    except ProposalError as exc:
        raise _handle_proposal_error(exc)

    logger.info(
        "proposal created proposal_id=%s gig_id=%s freelancer_id=%s",
        proposal.id,
        body.gig_id,
        freelancer_id,
    )
    return _proposal_to_out(proposal)


@router.get(
    "/v1/gigs/{gig_id}/proposals",
    response_model=ProposalListOut,
)
async def list_proposals_endpoint(
    gig_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ProposalListOut:
    """List all proposals for a gig. Requires CLIENT role and gig ownership."""
    client_id = _require_client(request)

    try:
        proposals, total = await list_proposals(db, gig_id, client_id, page, page_size)
    except ProposalError as exc:
        raise _handle_proposal_error(exc)

    return ProposalListOut(
        proposals=[_proposal_to_out(p) for p in proposals],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/v1/proposals/{proposal_id}/accept",
    response_model=ProposalOut,
)
async def accept_proposal_endpoint(
    proposal_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ProposalOut:
    """Accept a proposal. Requires CLIENT role and gig ownership."""
    client_id = _require_client(request)

    try:
        proposal = await accept_proposal(db, proposal_id, client_id)
    except ProposalError as exc:
        raise _handle_proposal_error(exc)

    logger.info("proposal accepted proposal_id=%s client_id=%s", proposal.id, client_id)
    return _proposal_to_out(proposal)


@router.get(
    "/v1/gigs/{gig_id}/proposals/mine",
    response_model=ProposalOut,
)
async def get_my_proposal_endpoint(
    gig_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ProposalOut:
    """Get the caller's own proposal for a gig. Requires FREELANCER role."""
    freelancer_id = _require_freelancer(request)

    proposal = await get_my_proposal(db, gig_id, freelancer_id)
    if proposal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "PROPOSAL_NOT_FOUND",
                "message": "You have not submitted a proposal for this gig",
            },
        )

    return _proposal_to_out(proposal)


@router.post(
    "/v1/proposals/{proposal_id}/reject",
    response_model=ProposalOut,
)
async def reject_proposal_endpoint(
    proposal_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ProposalOut:
    """Reject a PENDING proposal. Requires CLIENT role and gig ownership."""
    client_id = _require_client(request)

    try:
        proposal = await reject_proposal(db, proposal_id, client_id)
    except ProposalError as exc:
        raise _handle_proposal_error(exc)

    logger.info("proposal rejected proposal_id=%s client_id=%s", proposal.id, client_id)
    return _proposal_to_out(proposal)


@router.post(
    "/v1/proposals/{proposal_id}/withdraw",
    response_model=ProposalOut,
)
async def withdraw_proposal_endpoint(
    proposal_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ProposalOut:
    """Withdraw a PENDING proposal. Requires FREELANCER role and proposal ownership."""
    freelancer_id = _require_freelancer(request)

    try:
        proposal = await withdraw_proposal(db, proposal_id, freelancer_id)
    except ProposalError as exc:
        raise _handle_proposal_error(exc)

    logger.info(
        "proposal withdrawn proposal_id=%s freelancer_id=%s", proposal.id, freelancer_id
    )
    return _proposal_to_out(proposal)
