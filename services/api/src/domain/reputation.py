"""
domain/reputation.py — Business logic for reputation queries and upserts.
No FastAPI imports. Pure domain functions taking an AsyncSession.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.models import ReputationModel

logger = logging.getLogger(__name__)

_WALLET_RE = re.compile(r"^0x[0-9a-fA-F]{40}$", re.IGNORECASE)


class ReputationError(ValueError):
    """Raised when a reputation operation fails validation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_wallet_address(wallet_address: str) -> str:
    """Validate and normalize a wallet address. Returns lowercased address."""
    if not _WALLET_RE.match(wallet_address):
        raise ReputationError(
            "INVALID_WALLET_ADDRESS",
            "wallet_address must be a 42-char hex EVM address starting with 0x",
        )
    return wallet_address.lower()


async def get_reputation(
    db: AsyncSession, wallet_address: str
) -> ReputationModel | None:
    """Return the reputation record for a wallet address, or None if not found."""
    normalized = validate_wallet_address(wallet_address)
    result = await db.execute(
        select(ReputationModel).where(ReputationModel.wallet_address == normalized)
    )
    return result.scalar_one_or_none()


async def upsert_reputation(
    db: AsyncSession,
    wallet_address: str,
    *,
    user_id: str | None = None,
    gigs_completed: int | None = None,
    gigs_as_client: int | None = None,
    total_earned: str | None = None,
    average_ai_score: int | None = None,
    dispute_rate_pct: int | None = None,
    average_rating_x100: int | None = None,
    rating_count: int | None = None,
) -> ReputationModel:
    """
    Create or update a reputation record for the given wallet address.
    Only provided fields are updated; None fields are left unchanged.
    """
    normalized = validate_wallet_address(wallet_address)

    result = await db.execute(
        select(ReputationModel).where(ReputationModel.wallet_address == normalized)
    )
    record = result.scalar_one_or_none()

    if record is None:
        record = ReputationModel(
            wallet_address=normalized,
            user_id=user_id,
            gigs_completed=gigs_completed or 0,
            gigs_as_client=gigs_as_client or 0,
            total_earned=total_earned or "0",
            average_ai_score=average_ai_score or 0,
            dispute_rate_pct=dispute_rate_pct or 0,
            average_rating_x100=average_rating_x100 or 0,
            rating_count=rating_count or 0,
        )
        db.add(record)
    else:
        if user_id is not None:
            record.user_id = user_id
        if gigs_completed is not None:
            record.gigs_completed = gigs_completed
        if gigs_as_client is not None:
            record.gigs_as_client = gigs_as_client
        if total_earned is not None:
            record.total_earned = total_earned
        if average_ai_score is not None:
            record.average_ai_score = average_ai_score
        if dispute_rate_pct is not None:
            record.dispute_rate_pct = dispute_rate_pct
        if average_rating_x100 is not None:
            record.average_rating_x100 = average_rating_x100
        if rating_count is not None:
            record.rating_count = rating_count

    await db.flush()
    await db.refresh(record)
    return record
