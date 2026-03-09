"""api/reputation.py — Reputation endpoint (public)."""

from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.reputation import ReputationError, get_reputation
from src.infra.database import get_db
from src.infra.models import ReputationModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/reputation", tags=["reputation"])


class ReputationOut(BaseModel):
    id: Optional[str] = None
    user_id: Optional[str] = None
    wallet_address: str
    gigs_completed: int
    gigs_as_client: int
    total_earned: str
    average_ai_score: int
    dispute_rate_pct: int
    average_rating_x100: int
    rating_count: int
    last_synced_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


class GetReputationResponse(BaseModel):
    reputation: ReputationOut


def _reputation_to_out(r: ReputationModel) -> ReputationOut:
    return ReputationOut(
        id=r.id,
        user_id=r.user_id,
        wallet_address=r.wallet_address,
        gigs_completed=r.gigs_completed,
        gigs_as_client=r.gigs_as_client,
        total_earned=r.total_earned,
        average_ai_score=r.average_ai_score,
        dispute_rate_pct=r.dispute_rate_pct,
        average_rating_x100=r.average_rating_x100,
        rating_count=r.rating_count,
        last_synced_at=r.last_synced_at,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


def _zeroed_reputation(wallet_address: str) -> ReputationOut:
    return ReputationOut(
        wallet_address=wallet_address.lower(),
        gigs_completed=0,
        gigs_as_client=0,
        total_earned="0",
        average_ai_score=0,
        dispute_rate_pct=0,
        average_rating_x100=0,
        rating_count=0,
    )


@router.get("/{wallet_address}", response_model=GetReputationResponse)
async def get_reputation_endpoint(
    wallet_address: str, db: AsyncSession = Depends(get_db)
) -> GetReputationResponse:
    try:
        record = await get_reputation(db, wallet_address)
    except ReputationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message, "field_errors": []},
        )
    if record is None:
        return GetReputationResponse(reputation=_zeroed_reputation(wallet_address))
    return GetReputationResponse(reputation=_reputation_to_out(record))
