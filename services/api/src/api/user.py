"""
api/user.py — User profile endpoints.

POST /v1/users/profile       — update authenticated user's profile (auth required)
GET  /v1/users/{address}/profile — public profile lookup by wallet address
"""

from __future__ import annotations

import re

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import GigStatus, MilestoneStatus, UserRole
from src.infra.database import get_db
from src.infra.models import (
    GigModel,
    MilestoneModel,
    PortfolioItemModel,
    UserModel,
)

router = APIRouter(prefix="/v1/users", tags=["users"])

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

_URL_RE = re.compile(r"^https?://\S+$")


_VALID_ROLES = {UserRole.CLIENT, UserRole.FREELANCER, "CLIENT", "FREELANCER"}


class ProfileUpdateRequest(BaseModel):
    role: str | None = None
    name: str | None = None
    display_name: str | None = None  # legacy alias, prefer `name`
    bio: str | None = None
    avatar_url: str | None = None
    skills: list[str] | None = None
    hourly_rate_wei: str | None = None
    hourly_rate: float | None = None  # frontend sends this, map to hourly_rate_wei

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_ROLES:
            raise ValueError(f"role must be one of {_VALID_ROLES}")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 100:
            raise ValueError("name must be at most 100 characters")
        return v

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 100:
            raise ValueError("display_name must be at most 100 characters")
        return v

    @field_validator("bio")
    @classmethod
    def validate_bio(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 500:
            raise ValueError("bio must be at most 500 characters")
        return v

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, v: str | None) -> str | None:
        if v is not None and not _URL_RE.match(v):
            raise ValueError("avatar_url must be a valid URL")
        return v

    @field_validator("hourly_rate_wei")
    @classmethod
    def validate_hourly_rate_wei(cls, v: str | None) -> str | None:
        if v is not None and not v.isdigit():
            raise ValueError("hourly_rate_wei must be a numeric string")
        return v


class ProfileOut(BaseModel):
    id: str
    wallet_address: str | None = None
    name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    role: str
    skills: list[str]
    hourly_rate_wei: str
    created_at: str


def _profile_out(user: UserModel) -> ProfileOut:
    return ProfileOut(
        id=user.id,
        wallet_address=user.wallet_address,
        name=user.name,
        bio=user.bio,
        avatar_url=user.avatar_url,
        role=user.role,
        skills=user.skills or [],
        hourly_rate_wei=user.hourly_rate_wei,
        created_at=user.created_at.isoformat() if user.created_at else "",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/profile", response_model=ProfileOut)
async def update_profile(
    body: ProfileUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
    """Update the authenticated user's profile."""
    user_id: str = request.state.user_id

    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    if body.role is not None:
        # Normalise short form to proto enum
        role = body.role
        if role == "CLIENT":
            role = UserRole.CLIENT
        elif role == "FREELANCER":
            role = UserRole.FREELANCER
        user.role = role
    if body.name is not None:
        user.name = body.name
    elif body.display_name is not None:
        user.name = body.display_name
    if body.bio is not None:
        user.bio = body.bio
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url
    if body.skills is not None:
        user.skills = body.skills
    if body.hourly_rate_wei is not None:
        user.hourly_rate_wei = body.hourly_rate_wei
    if body.hourly_rate is not None:
        user.hourly_rate_wei = str(int(body.hourly_rate * 1_000_000_000))

    db.add(user)
    await db.flush()
    await db.refresh(user)
    return _profile_out(user)


class LinkEmailRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class LinkEmailOut(BaseModel):
    ok: bool
    email: str


@router.post("/link-email", response_model=LinkEmailOut)
async def link_email(
    body: LinkEmailRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> LinkEmailOut:
    """Link an email + password to an existing wallet-authenticated user."""
    user_id: str = request.state.user_id

    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "User not found"},
        )

    if user.email is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EMAIL_ALREADY_LINKED",
                "message": "Email is already linked to this account",
            },
        )

    # Check email not taken by another user
    existing = await db.execute(select(UserModel).where(UserModel.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMAIL_TAKEN", "message": "This email is already in use"},
        )

    user.email = body.email
    user.password_hash = bcrypt.hashpw(
        body.password.encode(), bcrypt.gensalt()
    ).decode()
    db.add(user)
    await db.flush()

    return LinkEmailOut(ok=True, email=body.email)


class ActiveGigOut(BaseModel):
    id: str
    title: str
    status: str
    budget: str


class PortfolioItemOut(BaseModel):
    id: str
    title: str
    description: str
    file_keys: list[str]
    external_url: str | None = None
    tags: list[str]
    verified_gig_id: str | None = None
    created_at: str


class PublicProfileOut(BaseModel):
    id: str
    wallet_address: str | None = None
    name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    role: str
    skills: list[str]
    reputation_score: int = 0
    badge_tier: str = "BRONZE"
    gigs_completed: int = 0
    total_earned: str | None = None
    total_spent: str | None = None
    avg_rating: float | None = None
    dispute_rate: float | None = None
    on_chain_badges: list = []
    portfolio_items: list[PortfolioItemOut] = []
    reviews: list = []
    active_gigs: list[ActiveGigOut] = []
    member_since: str = ""


@router.get("/{address}/profile", response_model=PublicProfileOut)
async def get_profile(
    address: str,
    db: AsyncSession = Depends(get_db),
) -> PublicProfileOut:
    """Public endpoint: look up a user profile by wallet address."""
    result = await db.execute(
        select(UserModel).where(UserModel.wallet_address == address)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "USER_NOT_FOUND", "message": "No user with that address"},
        )

    # Gigs completed count
    completed_q = (
        select(func.count())
        .select_from(GigModel)
        .where(
            GigModel.status == GigStatus.COMPLETED,
            (GigModel.client_id == user.id) | (GigModel.freelancer_id == user.id),
        )
    )
    gigs_completed = (await db.execute(completed_q)).scalar() or 0

    # Active gigs
    active_q = select(GigModel).where(
        GigModel.status.in_([GigStatus.OPEN, GigStatus.IN_PROGRESS]),
        (GigModel.client_id == user.id) | (GigModel.freelancer_id == user.id),
    )
    active_gigs_rows = (await db.execute(active_q)).scalars().all()
    active_gigs = [
        ActiveGigOut(id=g.id, title=g.title, status=g.status, budget=g.total_amount)
        for g in active_gigs_rows
    ]

    # Total earned (sum of PAID milestone amounts for freelancer)
    total_earned = None
    if user.role == UserRole.FREELANCER:
        paid_q = (
            select(MilestoneModel.amount)
            .join(GigModel, GigModel.id == MilestoneModel.gig_id)
            .where(
                GigModel.freelancer_id == user.id,
                MilestoneModel.status == MilestoneStatus.PAID,
            )
        )
        paid_rows = (await db.execute(paid_q)).scalars().all()
        total_earned = str(sum(int(a) for a in paid_rows if a.isdigit()))

    # Portfolio items
    portfolio_q = (
        select(PortfolioItemModel)
        .where(PortfolioItemModel.user_id == user.id)
        .order_by(PortfolioItemModel.created_at.desc())
        .limit(10)
    )
    portfolio_rows = (await db.execute(portfolio_q)).scalars().all()
    portfolio_items = [
        PortfolioItemOut(
            id=p.id,
            title=p.title,
            description=p.description,
            file_keys=p.file_keys or [],
            external_url=p.external_url,
            tags=p.tags or [],
            verified_gig_id=p.verified_gig_id,
            created_at=p.created_at.isoformat() if p.created_at else "",
        )
        for p in portfolio_rows
    ]

    return PublicProfileOut(
        id=user.id,
        wallet_address=user.wallet_address,
        name=user.name,
        bio=user.bio,
        avatar_url=user.avatar_url,
        role=user.role,
        skills=user.skills or [],
        gigs_completed=gigs_completed,
        total_earned=total_earned,
        active_gigs=active_gigs,
        portfolio_items=portfolio_items,
        member_since=user.created_at.isoformat() if user.created_at else "",
    )
