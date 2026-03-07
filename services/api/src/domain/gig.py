"""
domain/gig.py — Business logic for gig and milestone management.
No FastAPI imports. All side-effect-free helpers + DB-taking functions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy import Numeric, Text, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infra.models import GigModel, MilestoneModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain-level data classes (used as input DTOs only — no business entities)
# ---------------------------------------------------------------------------

_MAX_MILESTONES = 10
_MIN_MILESTONES = 1

_EDITABLE_STATUSES = {"DRAFT"}
_DELETABLE_STATUSES = {"DRAFT"}

_VALID_CURRENCIES = {"ETH", "USDC"}
_VALID_GIG_STATUSES = {
    "DRAFT",
    "OPEN",
    "IN_PROGRESS",
    "COMPLETED",
    "CANCELLED",
    "DISPUTED",
}


@dataclass
class MilestoneInput:
    title: str
    description: str
    acceptance_criteria: str
    amount: str
    order: int
    due_date: Optional[datetime] = None


@dataclass
class CreateGigInput:
    title: str
    description: str
    total_amount: str
    currency: str
    required_skills: list[str]
    milestones: list[MilestoneInput]
    token_address: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    deadline: Optional[datetime] = None


@dataclass
class UpdateGigInput:
    title: Optional[str] = None
    description: Optional[str] = None
    total_amount: Optional[str] = None
    currency: Optional[str] = None
    token_address: Optional[str] = None
    tags: Optional[list[str]] = None
    required_skills: Optional[list[str]] = None
    deadline: Optional[datetime] = None
    milestones: Optional[list[MilestoneInput]] = None


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


class GigValidationError(ValueError):
    """Raised when gig or milestone data fails business-rule validation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _validate_milestone_sum(
    total_amount: str, milestones: list[MilestoneInput]
) -> None:
    """Raise GigValidationError if milestone amounts don't sum to total_amount."""
    try:
        total = int(total_amount)
        milestone_sum = sum(int(m.amount) for m in milestones)
    except ValueError as exc:
        raise GigValidationError(
            "INVALID_AMOUNT",
            "total_amount and milestone amounts must be integer strings (wei/smallest unit)",
        ) from exc

    if milestone_sum != total:
        raise GigValidationError(
            "MILESTONE_AMOUNT_MISMATCH",
            f"Milestone amounts sum to {milestone_sum} but total_amount is {total}",
        )


def _validate_milestone_count(milestones: list[MilestoneInput]) -> None:
    count = len(milestones)
    if count < _MIN_MILESTONES:
        raise GigValidationError(
            "TOO_FEW_MILESTONES",
            f"A gig must have at least {_MIN_MILESTONES} milestone",
        )
    if count > _MAX_MILESTONES:
        raise GigValidationError(
            "TOO_MANY_MILESTONES",
            f"A gig may have at most {_MAX_MILESTONES} milestones",
        )


def _validate_currency(currency: str, token_address: Optional[str]) -> None:
    if currency not in _VALID_CURRENCIES:
        raise GigValidationError(
            "INVALID_CURRENCY",
            f"currency must be one of {_VALID_CURRENCIES}",
        )
    if currency == "ETH" and token_address:
        raise GigValidationError(
            "TOKEN_ADDRESS_NOT_ALLOWED",
            "token_address must be empty for ETH gigs",
        )
    if currency == "USDC" and not token_address:
        raise GigValidationError(
            "TOKEN_ADDRESS_REQUIRED",
            "token_address is required for USDC gigs",
        )
    if token_address and (
        not token_address.startswith("0x") or len(token_address) != 42
    ):
        raise GigValidationError(
            "INVALID_TOKEN_ADDRESS",
            "token_address must be a 42-char hex EVM address starting with 0x",
        )


# ---------------------------------------------------------------------------
# Domain functions
# ---------------------------------------------------------------------------


async def create_gig(
    db: AsyncSession,
    client_id: str,
    data: CreateGigInput,
) -> GigModel:
    """
    Create a gig in DRAFT status along with its milestones.

    Validates:
    - currency / token_address consistency
    - milestone count (1–10)
    - milestone amounts sum to total_amount

    Returns the GigModel with milestones pre-loaded.
    """
    _validate_currency(data.currency, data.token_address)
    _validate_milestone_count(data.milestones)
    _validate_milestone_sum(data.total_amount, data.milestones)

    gig = GigModel(
        client_id=client_id,
        title=data.title,
        description=data.description,
        total_amount=data.total_amount,
        currency=data.currency,
        token_address=data.token_address or None,
        status="DRAFT",
        tags=data.tags or [],
        required_skills=data.required_skills,
        deadline=data.deadline,
    )
    db.add(gig)
    await db.flush()  # populate gig.id

    for m in data.milestones:
        milestone = MilestoneModel(
            gig_id=gig.id,
            title=m.title,
            description=m.description,
            acceptance_criteria=m.acceptance_criteria,
            amount=m.amount,
            order=m.order,
            due_date=m.due_date,
            status="PENDING",
            revision_count=0,
        )
        db.add(milestone)

    await db.flush()
    await db.refresh(gig)

    # Eagerly load milestones so callers don't hit lazy-load issues
    result = await db.execute(
        select(GigModel)
        .where(GigModel.id == gig.id)
        .options(selectinload(GigModel.milestones))
    )
    return result.scalar_one()


async def get_gig(db: AsyncSession, gig_id: str) -> GigModel | None:
    """Return a single gig with its milestones, or None if not found."""
    result = await db.execute(
        select(GigModel)
        .where(GigModel.id == gig_id)
        .options(selectinload(GigModel.milestones))
    )
    return result.scalar_one_or_none()


async def list_gigs(
    db: AsyncSession,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    currency: Optional[str] = None,
    skill: Optional[str] = None,
    min_amount: Optional[str] = None,
    max_amount: Optional[str] = None,
) -> tuple[list[GigModel], int]:
    """
    Return a paginated list of gigs and the total count.

    - status: filter by GIG_STATUS string; defaults to "OPEN" (discovery board)
    - currency: filter by currency ("ETH" or "USDC")
    - skill: filter by required skill (case-sensitive substring match)
    - min_amount: minimum total_amount (inclusive, integer string)
    - max_amount: maximum total_amount (inclusive, integer string)
    - page: 1-indexed
    - page_size: max 100
    """
    page_size = min(page_size, 100)
    offset = (page - 1) * page_size
    effective_status = status if status else "OPEN"

    base_where = [GigModel.status == effective_status]
    if currency:
        base_where.append(GigModel.currency == currency)
    if min_amount is not None:
        try:
            base_where.append(cast(GigModel.total_amount, Numeric) >= int(min_amount))
        except ValueError:
            pass
    if max_amount is not None:
        try:
            base_where.append(cast(GigModel.total_amount, Numeric) <= int(max_amount))
        except ValueError:
            pass

    if skill:
        # Cast the JSON column to text and use LIKE to search for the skill value.
        # JSON arrays are stored as e.g. '["Python", "FastAPI"]' in both PostgreSQL
        # and SQLite, so searching for '"<skill>"' (with quotes) avoids false positives
        # from partial matches (e.g. "Java" matching "JavaScript").
        base_where.append(cast(GigModel.required_skills, Text).like(f'%"{skill}"%'))

    count_result = await db.execute(
        select(func.count()).select_from(GigModel).where(*base_where)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(GigModel)
        .where(*base_where)
        .options(selectinload(GigModel.milestones))
        .order_by(GigModel.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    gigs = list(result.scalars().all())

    return gigs, total


async def update_gig(
    db: AsyncSession,
    gig_id: str,
    client_id: str,
    data: UpdateGigInput,
) -> GigModel:
    """
    Update a gig. Raises GigValidationError if:
    - gig not found
    - caller is not the gig owner
    - gig is not in DRAFT status

    If milestones are provided, existing milestones are replaced.
    """
    result = await db.execute(
        select(GigModel)
        .where(GigModel.id == gig_id)
        .options(selectinload(GigModel.milestones))
    )
    gig = result.scalar_one_or_none()

    if gig is None:
        raise GigValidationError("GIG_NOT_FOUND", f"Gig {gig_id} not found")
    if gig.client_id != client_id:
        raise GigValidationError("FORBIDDEN", "Only the gig owner may update this gig")
    if gig.status not in _EDITABLE_STATUSES:
        raise GigValidationError(
            "GIG_NOT_EDITABLE",
            f"Gig cannot be edited in status {gig.status}",
        )

    if data.title is not None:
        gig.title = data.title
    if data.description is not None:
        gig.description = data.description
    if data.tags is not None:
        gig.tags = data.tags
    if data.required_skills is not None:
        gig.required_skills = data.required_skills
    if data.deadline is not None:
        gig.deadline = data.deadline

    # Currency + token_address updates must be validated together
    new_currency = data.currency if data.currency is not None else gig.currency
    new_token = (
        data.token_address if data.token_address is not None else gig.token_address
    )
    if data.currency is not None or data.token_address is not None:
        _validate_currency(new_currency, new_token)
        gig.currency = new_currency
        gig.token_address = new_token or None

    if data.total_amount is not None:
        gig.total_amount = data.total_amount

    # Replace milestones if provided
    if data.milestones is not None:
        effective_total = (
            data.total_amount if data.total_amount is not None else gig.total_amount
        )
        _validate_milestone_count(data.milestones)
        _validate_milestone_sum(effective_total, data.milestones)

        # Delete existing milestones by their IDs to avoid lazy-load issues
        milestone_ids = [ms.id for ms in gig.milestones]
        for mid in milestone_ids:
            ms = await db.get(MilestoneModel, mid)
            if ms is not None:
                await db.delete(ms)
        await db.flush()

        for m in data.milestones:
            milestone = MilestoneModel(
                gig_id=gig.id,
                title=m.title,
                description=m.description,
                acceptance_criteria=m.acceptance_criteria,
                amount=m.amount,
                order=m.order,
                due_date=m.due_date,
                status="PENDING",
                revision_count=0,
            )
            db.add(milestone)

    await db.flush()

    # Re-fetch with fresh milestones, bypassing the session identity map cache
    result2 = await db.execute(
        select(GigModel)
        .where(GigModel.id == gig_id)
        .options(selectinload(GigModel.milestones))
        .execution_options(populate_existing=True)
    )
    return result2.scalar_one()


async def delete_gig(
    db: AsyncSession,
    gig_id: str,
    client_id: str,
) -> None:
    """
    Delete a gig. Raises GigValidationError if:
    - gig not found
    - caller is not the gig owner
    - gig is not in DRAFT status
    """
    result = await db.execute(select(GigModel).where(GigModel.id == gig_id))
    gig = result.scalar_one_or_none()

    if gig is None:
        raise GigValidationError("GIG_NOT_FOUND", f"Gig {gig_id} not found")
    if gig.client_id != client_id:
        raise GigValidationError("FORBIDDEN", "Only the gig owner may delete this gig")
    if gig.status not in _DELETABLE_STATUSES:
        raise GigValidationError(
            "GIG_NOT_DELETABLE",
            f"Gig cannot be deleted in status {gig.status}",
        )

    await db.delete(gig)
    await db.flush()
    logger.info("gig deleted gig_id=%s client_id=%s", gig_id, client_id)
