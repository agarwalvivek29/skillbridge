"""
api/gig.py — Gig and milestone endpoints.

Endpoints:
  POST   /v1/gigs                      create gig (auth required, CLIENT role)
  GET    /v1/gigs                      list open gigs for discovery (public)
  GET    /v1/gigs/{gig_id}             get single gig with milestones (public)
  PUT    /v1/gigs/{gig_id}             update gig (auth required, must be owner, must be DRAFT)
  DELETE /v1/gigs/{gig_id}             delete gig (auth required, must be owner, must be DRAFT)
  GET    /v1/gigs/{gig_id}/escrow-tx   get Solana escrow deposit tx data (CLIENT, owner)
  POST   /v1/gigs/{gig_id}/confirm-escrow  confirm escrow funded on-chain (CLIENT, owner)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.gig import (
    CreateGigInput,
    GigValidationError,
    MilestoneInput,
    UpdateGigInput,
    create_gig,
    delete_gig,
    get_gig,
    list_gigs,
    update_gig,
)
from src.config import settings
from src.infra.database import get_db
from src.infra.models import EscrowContractModel, GigModel, MilestoneModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/gigs", tags=["gigs"])

_CLIENT_ROLE = "USER_ROLE_CLIENT"

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class MilestoneIn(BaseModel):
    title: str
    description: str
    acceptance_criteria: str
    amount: str
    order: int
    due_date: Optional[datetime] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive_integer(cls, v: str) -> str:
        try:
            val = int(v)
        except ValueError as exc:
            raise ValueError(
                "amount must be an integer string (wei/smallest unit)"
            ) from exc
        if val <= 0:
            raise ValueError("amount must be > 0")
        return v

    @field_validator("order")
    @classmethod
    def order_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("order must be >= 1")
        return v


class CreateGigRequest(BaseModel):
    title: str
    description: str
    total_amount: str
    currency: str
    token_address: Optional[str] = None
    tags: list[str] = []
    required_skills: list[str]
    deadline: Optional[datetime] = None
    milestones: list[MilestoneIn]

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        allowed = {"ETH", "USDC"}
        if v not in allowed:
            raise ValueError(f"currency must be one of {allowed}")
        return v

    @field_validator("total_amount")
    @classmethod
    def total_amount_must_be_positive_integer(cls, v: str) -> str:
        try:
            val = int(v)
        except ValueError as exc:
            raise ValueError("total_amount must be an integer string") from exc
        if val <= 0:
            raise ValueError("total_amount must be > 0")
        return v


class UpdateGigRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    total_amount: Optional[str] = None
    currency: Optional[str] = None
    token_address: Optional[str] = None
    tags: Optional[list[str]] = None
    required_skills: Optional[list[str]] = None
    deadline: Optional[datetime] = None
    milestones: Optional[list[MilestoneIn]] = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"ETH", "USDC"}
        if v not in allowed:
            raise ValueError(f"currency must be one of {allowed}")
        return v


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


class GigOut(BaseModel):
    id: str
    client_id: str
    freelancer_id: Optional[str]
    title: str
    description: str
    total_amount: str
    currency: str
    token_address: Optional[str]
    contract_address: Optional[str]
    status: str
    tags: list[str]
    required_skills: list[str]
    deadline: Optional[datetime]
    milestones: list[MilestoneOut]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GigListOut(BaseModel):
    gigs: list[GigOut]
    total: int
    page: int
    page_size: int


class EscrowTxOut(BaseModel):
    program_id: str
    escrow_seeds: list[str]
    amount: str
    currency: str
    token_mint: Optional[str] = None


class ConfirmEscrowBody(BaseModel):
    tx_signature: str
    contract_address: str


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _gig_to_out(gig: GigModel) -> GigOut:
    return GigOut(
        id=gig.id,
        client_id=gig.client_id,
        freelancer_id=gig.freelancer_id,
        title=gig.title,
        description=gig.description,
        total_amount=gig.total_amount,
        currency=gig.currency,
        token_address=gig.token_address,
        contract_address=gig.contract_address,
        status=gig.status,
        tags=gig.tags or [],
        required_skills=gig.required_skills or [],
        deadline=gig.deadline,
        milestones=[
            _milestone_to_out(m) for m in sorted(gig.milestones, key=lambda x: x.order)
        ],
        created_at=gig.created_at,
        updated_at=gig.updated_at,
    )


def _milestone_to_out(m: MilestoneModel) -> MilestoneOut:
    return MilestoneOut(
        id=m.id,
        gig_id=m.gig_id,
        title=m.title,
        description=m.description,
        acceptance_criteria=m.acceptance_criteria,
        amount=m.amount,
        order=m.order,
        due_date=m.due_date,
        status=m.status,
        revision_count=m.revision_count,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _require_client(request: Request) -> str:
    """Extract user_id from request state and verify CLIENT role. Returns user_id."""
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
    """Extract user_id from request state. Returns user_id."""
    user_id: str = getattr(request.state, "user_id", "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required"},
        )
    return user_id


def _handle_validation_error(exc: GigValidationError) -> HTTPException:
    status_map = {
        "GIG_NOT_FOUND": 404,
        "FORBIDDEN": 403,
        "GIG_NOT_EDITABLE": 409,
        "GIG_NOT_DELETABLE": 409,
    }
    http_status = status_map.get(exc.code, 400)
    return HTTPException(
        status_code=http_status,
        detail={"code": exc.code, "message": exc.message, "field_errors": []},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=GigOut, status_code=status.HTTP_201_CREATED)
async def create_gig_endpoint(
    body: CreateGigRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GigOut:
    """Create a gig with milestones. Requires CLIENT role."""
    client_id = _require_client(request)

    milestones = [
        MilestoneInput(
            title=m.title,
            description=m.description,
            acceptance_criteria=m.acceptance_criteria,
            amount=m.amount,
            order=m.order,
            due_date=m.due_date,
        )
        for m in body.milestones
    ]

    gig_input = CreateGigInput(
        title=body.title,
        description=body.description,
        total_amount=body.total_amount,
        currency=body.currency,
        token_address=body.token_address,
        tags=body.tags,
        required_skills=body.required_skills,
        deadline=body.deadline,
        milestones=milestones,
    )

    try:
        gig = await create_gig(db, client_id, gig_input)
    except GigValidationError as exc:
        raise _handle_validation_error(exc)

    logger.info("gig created gig_id=%s client_id=%s", gig.id, client_id)
    return _gig_to_out(gig)


@router.get("", response_model=GigListOut)
async def list_gigs_endpoint(
    status_filter: Optional[str] = Query(
        None, description="Filter by gig status (default: OPEN)"
    ),
    currency: Optional[str] = Query(
        None, description="Filter by currency (ETH or USDC)"
    ),
    skill: Optional[str] = Query(None, description="Filter by required skill"),
    min_amount: Optional[str] = Query(
        None, description="Minimum total_amount (integer string)"
    ),
    max_amount: Optional[str] = Query(
        None, description="Maximum total_amount (integer string)"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> GigListOut:
    """List gigs for the discovery board. No auth required. Defaults to OPEN gigs."""
    gigs, total = await list_gigs(
        db,
        status=status_filter,
        page=page,
        page_size=page_size,
        currency=currency,
        skill=skill,
        min_amount=min_amount,
        max_amount=max_amount,
    )
    return GigListOut(
        gigs=[_gig_to_out(g) for g in gigs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{gig_id}", response_model=GigOut)
async def get_gig_endpoint(
    gig_id: str,
    db: AsyncSession = Depends(get_db),
) -> GigOut:
    """Get a single gig with its milestones. No auth required."""
    gig = await get_gig(db, gig_id)
    if gig is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "GIG_NOT_FOUND", "message": f"Gig {gig_id} not found"},
        )
    return _gig_to_out(gig)


@router.put("/{gig_id}", response_model=GigOut)
async def update_gig_endpoint(
    gig_id: str,
    body: UpdateGigRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GigOut:
    """Update a gig. Auth required; must be gig owner; gig must be in DRAFT."""
    client_id = _require_client(request)

    update_input = UpdateGigInput(
        title=body.title,
        description=body.description,
        total_amount=body.total_amount,
        currency=body.currency,
        token_address=body.token_address,
        tags=body.tags,
        required_skills=body.required_skills,
        deadline=body.deadline,
        milestones=(
            [
                MilestoneInput(
                    title=m.title,
                    description=m.description,
                    acceptance_criteria=m.acceptance_criteria,
                    amount=m.amount,
                    order=m.order,
                    due_date=m.due_date,
                )
                for m in body.milestones
            ]
            if body.milestones is not None
            else None
        ),
    )

    try:
        gig = await update_gig(db, gig_id, client_id, update_input)
    except GigValidationError as exc:
        raise _handle_validation_error(exc)

    return _gig_to_out(gig)


@router.delete("/{gig_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gig_endpoint(
    gig_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a gig. Auth required; must be gig owner; gig must be in DRAFT."""
    client_id = _require_client(request)

    try:
        await delete_gig(db, gig_id, client_id)
    except GigValidationError as exc:
        raise _handle_validation_error(exc)


# ---------------------------------------------------------------------------
# Escrow endpoints
# ---------------------------------------------------------------------------

# USDC token mint on Solana (mainnet-beta / devnet share this address)
_USDC_TOKEN_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


@router.get(
    "/{gig_id}/escrow-tx",
    response_model=EscrowTxOut,
    status_code=status.HTTP_200_OK,
)
async def get_escrow_tx_endpoint(
    gig_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> EscrowTxOut:
    """
    Return Solana transaction data for escrow deposit.
    CLIENT role only; must be the gig owner.
    """
    client_id = _require_client(request)

    gig = await get_gig(db, gig_id)
    if gig is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "GIG_NOT_FOUND", "message": f"Gig {gig_id} not found"},
        )

    if gig.client_id != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Only the gig owner may request escrow tx data",
            },
        )

    if not settings.escrow_program_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "NO_PROGRAM_ID",
                "message": "Escrow program ID is not configured",
            },
        )

    # Strip hyphens from UUID to fit within Solana's 32-byte seed limit
    # "7ce34a2f-eaf4-4bde-823d-bd067a027d65" → "7ce34a2feaf44bde823dbd067a027d65" (32 chars = 32 bytes)
    gig_id_compact = gig_id.replace("-", "")

    token_mint: str | None = None
    if gig.currency == "USDC":
        token_mint = gig.token_address or _USDC_TOKEN_MINT

    return EscrowTxOut(
        program_id=settings.escrow_program_id,
        escrow_seeds=["escrow", gig_id_compact],
        amount=gig.total_amount,
        currency=gig.currency,
        token_mint=token_mint,
    )


_FUNDABLE_STATUSES = {"DRAFT", "OPEN"}


@router.post(
    "/{gig_id}/confirm-escrow",
    response_model=GigOut,
    status_code=status.HTTP_200_OK,
)
async def confirm_escrow_endpoint(
    gig_id: str,
    body: ConfirmEscrowBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GigOut:
    """
    Confirm that the escrow was funded on-chain.
    Creates/updates EscrowContractModel and transitions gig status.
    CLIENT role only; must be the gig owner.
    """
    client_id = _require_client(request)

    gig = await get_gig(db, gig_id)
    if gig is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "GIG_NOT_FOUND", "message": f"Gig {gig_id} not found"},
        )

    if gig.client_id != client_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Only the gig owner may confirm escrow",
            },
        )

    if gig.status not in _FUNDABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "GIG_NOT_FUNDABLE",
                "message": f"Gig cannot be funded in status {gig.status}",
            },
        )

    # Create or update EscrowContractModel
    escrow_result = await db.execute(
        select(EscrowContractModel).where(EscrowContractModel.gig_id == gig_id)
    )
    escrow = escrow_result.scalar_one_or_none()
    if escrow is None:
        escrow = EscrowContractModel(
            gig_id=gig_id,
            contract_address=body.contract_address,
            tx_signature=body.tx_signature,
        )
        db.add(escrow)
    else:
        escrow.contract_address = body.contract_address
        escrow.tx_signature = body.tx_signature

    # Update gig with contract_address and status
    gig.contract_address = body.contract_address
    gig.status = "OPEN"
    await db.flush()

    # Re-fetch to get updated state
    refreshed = await get_gig(db, gig_id)
    return _gig_to_out(refreshed)  # type: ignore[arg-type]
