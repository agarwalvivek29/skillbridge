"""
api/gig.py — Gig and milestone endpoints.

All routes require authentication (JWT Bearer or X-API-Key).
Only the gig creator (client_id == request.state.user_id) may mutate a gig.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain import gig as gig_domain
from src.domain.gig import (
    CreateGigInput,
    GigValidationError,
    MilestoneInput,
    UpdateGigInput,
)
from src.infra.database import get_db
from src.infra.models import GigModel, MilestoneModel

router = APIRouter(prefix="/v1/gigs", tags=["gigs"])


# ---------------------------------------------------------------------------
# Pydantic request / response shapes
# ---------------------------------------------------------------------------


class MilestoneCreateBody(BaseModel):
    title: str
    description: str
    acceptance_criteria: str
    amount: str
    order: int
    due_date: Optional[datetime] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: str) -> str:
        try:
            val = int(v)
        except (ValueError, TypeError) as exc:
            raise ValueError("amount must be a valid integer string") from exc
        if val <= 0:
            raise ValueError("amount must be a positive integer")
        return v

    @field_validator("order")
    @classmethod
    def validate_order(cls, v: int) -> int:
        if v < 1:
            raise ValueError("order must be >= 1")
        return v


class GigCreateBody(BaseModel):
    title: str
    description: str
    total_amount: str
    currency: str = "CURRENCY_ETH"
    token_address: str = ""
    tags: list[str] = []
    required_skills: list[str] = []
    deadline: Optional[datetime] = None
    milestones: list[MilestoneCreateBody]

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        allowed = {"CURRENCY_ETH", "CURRENCY_USDC"}
        if v not in allowed:
            raise ValueError(f"currency must be one of {sorted(allowed)}")
        return v

    @field_validator("total_amount")
    @classmethod
    def validate_total_amount(cls, v: str) -> str:
        try:
            val = int(v)
        except (ValueError, TypeError) as exc:
            raise ValueError("total_amount must be a valid integer string") from exc
        if val <= 0:
            raise ValueError("total_amount must be a positive integer")
        return v

    @field_validator("milestones")
    @classmethod
    def validate_milestones_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("At least one milestone is required")
        return v


class MilestoneUpdateBody(BaseModel):
    title: str
    description: str
    acceptance_criteria: str
    amount: str
    order: int
    due_date: Optional[datetime] = None

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: str) -> str:
        try:
            val = int(v)
        except (ValueError, TypeError) as exc:
            raise ValueError("amount must be a valid integer string") from exc
        if val <= 0:
            raise ValueError("amount must be a positive integer")
        return v


class GigUpdateBody(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    total_amount: Optional[str] = None
    currency: Optional[str] = None
    token_address: Optional[str] = None
    tags: Optional[list[str]] = None
    required_skills: Optional[list[str]] = None
    deadline: Optional[datetime] = None
    milestones: Optional[list[MilestoneUpdateBody]] = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"CURRENCY_ETH", "CURRENCY_USDC"}
        if v not in allowed:
            raise ValueError(f"currency must be one of {sorted(allowed)}")
        return v

    @field_validator("total_amount")
    @classmethod
    def validate_total_amount(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            val = int(v)
        except (ValueError, TypeError) as exc:
            raise ValueError("total_amount must be a valid integer string") from exc
        if val <= 0:
            raise ValueError("total_amount must be a positive integer")
        return v


# ---------------------------------------------------------------------------
# Response shapes
# ---------------------------------------------------------------------------


class MilestoneResponse(BaseModel):
    id: str
    gig_id: str
    title: str
    description: str
    acceptance_criteria: str
    amount: str
    order: int
    status: str
    contract_index: int
    revision_count: int
    due_date: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class GigResponse(BaseModel):
    id: str
    client_id: str
    freelancer_id: Optional[str] = None
    title: str
    description: str
    total_amount: str
    currency: str
    token_address: str
    contract_address: str
    status: str
    tags: list[str]
    required_skills: list[str]
    deadline: Optional[str] = None
    milestones: list[MilestoneResponse]
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class GigsListResponse(BaseModel):
    gigs: list[GigResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dt_to_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _milestone_to_response(ms: MilestoneModel) -> MilestoneResponse:
    return MilestoneResponse(
        id=ms.id,
        gig_id=ms.gig_id,
        title=ms.title,
        description=ms.description,
        acceptance_criteria=ms.acceptance_criteria,
        amount=ms.amount,
        order=ms.order,
        status=ms.status,
        contract_index=ms.contract_index,
        revision_count=ms.revision_count,
        due_date=_dt_to_iso(ms.due_date),
        created_at=_dt_to_iso(ms.created_at),
        updated_at=_dt_to_iso(ms.updated_at),
    )


def _gig_to_response(gig: GigModel) -> GigResponse:
    return GigResponse(
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
        deadline=_dt_to_iso(gig.deadline),
        milestones=[_milestone_to_response(ms) for ms in (gig.milestones or [])],
        created_at=_dt_to_iso(gig.created_at),
        updated_at=_dt_to_iso(gig.updated_at),
    )


def _require_auth(request: Request) -> str:
    """Return authenticated user_id from request state."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required"},
        )
    return user_id


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=GigResponse, status_code=status.HTTP_201_CREATED)
async def create_gig(
    body: GigCreateBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GigResponse:
    """Create a new gig with milestones. Caller must be authenticated."""
    client_id = _require_auth(request)

    milestone_inputs = [
        MilestoneInput(
            title=ms.title,
            description=ms.description,
            acceptance_criteria=ms.acceptance_criteria,
            amount=ms.amount,
            order=ms.order,
            due_date=ms.due_date,
        )
        for ms in body.milestones
    ]

    inp = CreateGigInput(
        title=body.title,
        description=body.description,
        total_amount=body.total_amount,
        currency=body.currency,
        token_address=body.token_address,
        tags=body.tags,
        required_skills=body.required_skills,
        deadline=body.deadline,
        milestones=milestone_inputs,
    )

    try:
        gig = await gig_domain.create_gig(db, client_id, inp)
    except GigValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message, "field_errors": []},
        ) from exc

    return _gig_to_response(gig)


@router.get("", response_model=GigsListResponse)
async def list_gigs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    skill: Optional[str] = Query(default=None),
    currency: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> GigsListResponse:
    """List OPEN gigs (discovery board). Paginated."""
    gigs, total = await gig_domain.list_open_gigs(
        db,
        page=page,
        page_size=page_size,
        skill_filter=skill,
        currency_filter=currency,
    )
    return GigsListResponse(
        gigs=[_gig_to_response(g) for g in gigs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{gig_id}", response_model=GigResponse)
async def get_gig(
    gig_id: str,
    db: AsyncSession = Depends(get_db),
) -> GigResponse:
    """Fetch a single gig with its milestones."""
    gig = await gig_domain.get_gig_by_id(db, gig_id)
    if gig is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "GIG_NOT_FOUND", "message": "Gig not found"},
        )
    return _gig_to_response(gig)


@router.put("/{gig_id}", response_model=GigResponse)
async def update_gig(
    gig_id: str,
    body: GigUpdateBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> GigResponse:
    """Update a DRAFT gig. Only the owner may do this."""
    client_id = _require_auth(request)

    gig = await gig_domain.get_gig_by_id(db, gig_id)
    if gig is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "GIG_NOT_FOUND", "message": "Gig not found"},
        )

    milestone_inputs: Optional[list[MilestoneInput]] = None
    if body.milestones is not None:
        milestone_inputs = [
            MilestoneInput(
                title=ms.title,
                description=ms.description,
                acceptance_criteria=ms.acceptance_criteria,
                amount=ms.amount,
                order=ms.order,
                due_date=ms.due_date,
            )
            for ms in body.milestones
        ]

    inp = UpdateGigInput(
        title=body.title,
        description=body.description,
        total_amount=body.total_amount,
        currency=body.currency,
        token_address=body.token_address,
        tags=body.tags,
        required_skills=body.required_skills,
        deadline=body.deadline,
        milestones=milestone_inputs,
    )

    try:
        updated = await gig_domain.update_gig(db, gig, client_id, inp)
    except GigValidationError as exc:
        if exc.code == "NOT_GIG_OWNER":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": exc.code, "message": exc.message, "field_errors": []},
            ) from exc
        if exc.code == "GIG_NOT_EDITABLE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": exc.code, "message": exc.message, "field_errors": []},
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message, "field_errors": []},
        ) from exc

    return _gig_to_response(updated)


@router.delete("/{gig_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gig(
    gig_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a DRAFT gig. Only the owner may do this."""
    client_id = _require_auth(request)

    gig = await gig_domain.get_gig_by_id(db, gig_id)
    if gig is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "GIG_NOT_FOUND", "message": "Gig not found"},
        )

    try:
        await gig_domain.delete_gig(db, gig, client_id)
    except GigValidationError as exc:
        if exc.code == "NOT_GIG_OWNER":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": exc.code, "message": exc.message, "field_errors": []},
            ) from exc
        if exc.code == "GIG_NOT_DELETABLE":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": exc.code, "message": exc.message, "field_errors": []},
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message, "field_errors": []},
        ) from exc
