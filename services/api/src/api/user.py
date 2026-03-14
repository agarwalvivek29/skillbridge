"""
api/user.py — User profile endpoints.

POST /v1/users/profile       — update authenticated user's profile (auth required)
GET  /v1/users/{address}/profile — public profile lookup by wallet address
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.database import get_db
from src.infra.models import UserModel

router = APIRouter(prefix="/v1/users", tags=["users"])

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

_URL_RE = re.compile(r"^https?://\S+$")


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    skills: list[str] | None = None
    hourly_rate_wei: str | None = None

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
    display_name: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    role: str
    skills: list[str]
    hourly_rate: str
    created_at: str


def _profile_out(user: UserModel) -> ProfileOut:
    return ProfileOut(
        id=user.id,
        wallet_address=user.wallet_address,
        display_name=user.name,
        bio=user.bio,
        avatar_url=user.avatar_url,
        role=user.role,
        skills=user.skills or [],
        hourly_rate=user.hourly_rate_wei,
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

    if body.display_name is not None:
        user.name = body.display_name
    if body.bio is not None:
        user.bio = body.bio
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url
    if body.skills is not None:
        user.skills = body.skills
    if body.hourly_rate_wei is not None:
        user.hourly_rate_wei = body.hourly_rate_wei

    db.add(user)
    await db.flush()
    await db.refresh(user)
    return _profile_out(user)


@router.get("/{address}/profile", response_model=ProfileOut)
async def get_profile(
    address: str,
    db: AsyncSession = Depends(get_db),
) -> ProfileOut:
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
    return _profile_out(user)
