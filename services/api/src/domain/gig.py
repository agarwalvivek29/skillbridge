"""
domain/gig.py — Pure business logic for gig and milestone management.
No FastAPI imports. All validation + DB operations live here.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.infra.models import GigModel, MilestoneModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_MILESTONES = 10
_MIN_MILESTONES = 1

_MUTABLE_STATUSES = {"GIG_STATUS_DRAFT"}

_VALID_CURRENCIES = {"CURRENCY_ETH", "CURRENCY_USDC"}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


class GigValidationError(ValueError):
    """Raised when gig/milestone input fails business validation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_milestone_count(count: int) -> None:
    """Raise GigValidationError if milestone count is out of range."""
    if count < _MIN_MILESTONES:
        raise GigValidationError(
            "MILESTONE_COUNT_TOO_LOW",
            f"At least {_MIN_MILESTONES} milestone is required.",
        )
    if count > _MAX_MILESTONES:
        raise GigValidationError(
            "MILESTONE_COUNT_TOO_HIGH",
            f"A gig may have at most {_MAX_MILESTONES} milestones.",
        )


def validate_milestone_sum(total_amount: str, milestone_amounts: list[str]) -> None:
    """
    Raise GigValidationError if milestone amounts do not sum to total_amount.
    All values are treated as integer strings (wei / smallest unit).
    """
    try:
        total = int(total_amount)
    except (ValueError, TypeError) as exc:
        raise GigValidationError(
            "INVALID_TOTAL_AMOUNT",
            "total_amount must be a valid integer string.",
        ) from exc

    try:
        milestone_total = sum(int(a) for a in milestone_amounts)
    except (ValueError, TypeError) as exc:
        raise GigValidationError(
            "INVALID_MILESTONE_AMOUNT",
            "Each milestone amount must be a valid integer string.",
        ) from exc

    if milestone_total != total:
        raise GigValidationError(
            "MILESTONE_SUM_MISMATCH",
            f"Milestone amounts sum to {milestone_total} but total_amount is {total}.",
        )


def validate_currency_token(currency: str, token_address: str) -> None:
    """
    Raise GigValidationError if USDC is selected without a token_address,
    or if an unknown currency is supplied.
    """
    if currency not in _VALID_CURRENCIES:
        raise GigValidationError(
            "INVALID_CURRENCY",
            f"currency must be one of {sorted(_VALID_CURRENCIES)}.",
        )
    if currency == "CURRENCY_USDC" and not token_address:
        raise GigValidationError(
            "MISSING_TOKEN_ADDRESS",
            "token_address is required for USDC gigs.",
        )


# ---------------------------------------------------------------------------
# Data transfer objects (thin, no proto dependency in service code)
# ---------------------------------------------------------------------------


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
    token_address: str
    tags: list[str] = field(default_factory=list)
    required_skills: list[str] = field(default_factory=list)
    deadline: Optional[datetime] = None
    milestones: list[MilestoneInput] = field(default_factory=list)


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
# DB operations
# ---------------------------------------------------------------------------


async def create_gig(
    db: AsyncSession,
    client_id: str,
    inp: CreateGigInput,
) -> GigModel:
    """
    Validate and create a gig with its milestones.
    Returns the persisted GigModel with milestones eagerly loaded.
    """
    validate_milestone_count(len(inp.milestones))
    validate_currency_token(inp.currency, inp.token_address)
    validate_milestone_sum(inp.total_amount, [m.amount for m in inp.milestones])

    gig = GigModel(
        client_id=client_id,
        title=inp.title,
        description=inp.description,
        total_amount=inp.total_amount,
        currency=inp.currency,
        token_address=inp.token_address,
        tags=inp.tags,
        required_skills=inp.required_skills,
        deadline=inp.deadline,
        status="GIG_STATUS_DRAFT",
    )
    db.add(gig)
    await db.flush()  # get gig.id

    for ms in inp.milestones:
        milestone = MilestoneModel(
            gig_id=gig.id,
            title=ms.title,
            description=ms.description,
            acceptance_criteria=ms.acceptance_criteria,
            amount=ms.amount,
            order=ms.order,
            due_date=ms.due_date,
            status="MILESTONE_STATUS_PENDING",
        )
        db.add(milestone)

    await db.flush()

    # Re-fetch with milestones eagerly loaded so the relationship is populated
    result = await db.execute(
        select(GigModel)
        .where(GigModel.id == gig.id)
        .options(selectinload(GigModel.milestones))
    )
    loaded = result.scalar_one()
    logger.info("gig_created gig_id=%s client_id=%s", loaded.id, client_id)
    return loaded


async def get_gig_by_id(
    db: AsyncSession,
    gig_id: str,
) -> Optional[GigModel]:
    """Return a gig with milestones, or None if not found."""
    result = await db.execute(
        select(GigModel)
        .where(GigModel.id == gig_id)
        .options(selectinload(GigModel.milestones))
    )
    return result.scalar_one_or_none()


async def list_open_gigs(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    skill_filter: Optional[str] = None,
    currency_filter: Optional[str] = None,
) -> tuple[list[GigModel], int]:
    """
    Return paginated OPEN gigs (discovery board).
    Returns (gigs, total_count).
    """
    from sqlalchemy import func as sa_func

    query = (
        select(GigModel)
        .where(GigModel.status == "GIG_STATUS_OPEN")
        .options(selectinload(GigModel.milestones))
        .order_by(GigModel.created_at.desc())
    )

    count_query = select(sa_func.count(GigModel.id)).where(
        GigModel.status == "GIG_STATUS_OPEN"
    )

    if currency_filter:
        query = query.where(GigModel.currency == currency_filter)
        count_query = count_query.where(GigModel.currency == currency_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    gigs = list(result.scalars().all())

    # Post-filter by skill (JSON array search; cross-dialect compatible)
    if skill_filter:
        gigs = [g for g in gigs if skill_filter in (g.required_skills or [])]
        total = len(gigs)

    return gigs, total


async def update_gig(
    db: AsyncSession,
    gig: GigModel,
    client_id: str,
    inp: UpdateGigInput,
) -> GigModel:
    """
    Update a DRAFT gig. Replaces milestones if provided.
    Raises GigValidationError on constraint violations.
    """
    if gig.status not in _MUTABLE_STATUSES:
        raise GigValidationError(
            "GIG_NOT_EDITABLE",
            f"Gig cannot be edited in status {gig.status}.",
        )
    if gig.client_id != client_id:
        raise GigValidationError(
            "NOT_GIG_OWNER",
            "Only the gig owner can edit this gig.",
        )

    # Apply scalar updates
    if inp.title is not None:
        gig.title = inp.title
    if inp.description is not None:
        gig.description = inp.description
    if inp.total_amount is not None:
        gig.total_amount = inp.total_amount
    if inp.currency is not None:
        gig.currency = inp.currency
    if inp.token_address is not None:
        gig.token_address = inp.token_address
    if inp.tags is not None:
        gig.tags = inp.tags
    if inp.required_skills is not None:
        gig.required_skills = inp.required_skills
    if inp.deadline is not None:
        gig.deadline = inp.deadline

    # Validate currency/token after applying updates
    validate_currency_token(gig.currency, gig.token_address)

    # Replace milestones if provided
    if inp.milestones is not None:
        validate_milestone_count(len(inp.milestones))
        validate_milestone_sum(gig.total_amount, [m.amount for m in inp.milestones])

        # Delete existing milestones using a bulk delete with synchronize_session
        # so the session identity map is updated immediately
        await db.execute(
            delete(MilestoneModel)
            .where(MilestoneModel.gig_id == gig.id)
            .execution_options(synchronize_session="fetch")
        )
        await db.flush()

        for ms in inp.milestones:
            milestone = MilestoneModel(
                gig_id=gig.id,
                title=ms.title,
                description=ms.description,
                acceptance_criteria=ms.acceptance_criteria,
                amount=ms.amount,
                order=ms.order,
                due_date=ms.due_date,
                status="MILESTONE_STATUS_PENDING",
            )
            db.add(milestone)

    await db.flush()

    # Re-fetch with milestones eagerly loaded (populate_existing refreshes cache)
    result = await db.execute(
        select(GigModel)
        .where(GigModel.id == gig.id)
        .options(selectinload(GigModel.milestones))
        .execution_options(populate_existing=True)
    )
    loaded = result.scalar_one()
    logger.info("gig_updated gig_id=%s client_id=%s", loaded.id, client_id)
    return loaded


async def delete_gig(
    db: AsyncSession,
    gig: GigModel,
    client_id: str,
) -> None:
    """
    Delete a DRAFT gig. Cascades to milestones.
    Raises GigValidationError if not DRAFT or not owner.
    """
    if gig.status not in _MUTABLE_STATUSES:
        raise GigValidationError(
            "GIG_NOT_DELETABLE",
            f"Gig cannot be deleted in status {gig.status}.",
        )
    if gig.client_id != client_id:
        raise GigValidationError(
            "NOT_GIG_OWNER",
            "Only the gig owner can delete this gig.",
        )
    await db.delete(gig)
    await db.flush()
    logger.info("gig_deleted gig_id=%s client_id=%s", gig.id, client_id)
