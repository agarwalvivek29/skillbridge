"""
domain/portfolio.py — Business logic for portfolio item management.
No FastAPI imports. All side-effect-free helpers + DB-taking functions.

Badge logic:
  is_verified = True  iff  item.verified_gig_id IS NOT NULL
                           AND the linked gig.status == 'COMPLETED'
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import GigStatus
from src.infra.models import GigModel, PortfolioItemModel

logger = logging.getLogger(__name__)

_GIG_COMPLETED_STATUS = GigStatus.COMPLETED

# ---------------------------------------------------------------------------
# Input DTOs
# ---------------------------------------------------------------------------


@dataclass
class CreatePortfolioItemInput:
    title: str
    description: str
    file_keys: list[str] = field(default_factory=list)
    external_url: Optional[str] = None
    github_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    verified_gig_id: Optional[str] = None


@dataclass
class UpdatePortfolioItemInput:
    title: Optional[str] = None
    description: Optional[str] = None
    file_keys: Optional[list[str]] = None
    external_url: Optional[str] = None
    github_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    tags: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Domain error
# ---------------------------------------------------------------------------


class PortfolioValidationError(ValueError):
    """Raised when a portfolio operation fails a business rule."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _compute_is_verified(
    db: AsyncSession, verified_gig_id: Optional[str]
) -> bool:
    """
    Return True iff verified_gig_id is set and the linked gig's status is COMPLETED.
    Returns False for None or missing gig IDs without raising.
    """
    if not verified_gig_id:
        return False
    result = await db.execute(
        select(GigModel.status).where(GigModel.id == verified_gig_id)
    )
    status = result.scalar_one_or_none()
    return status == _GIG_COMPLETED_STATUS


# ---------------------------------------------------------------------------
# Domain functions
# ---------------------------------------------------------------------------


async def create_portfolio_item(
    db: AsyncSession,
    user_id: str,
    data: CreatePortfolioItemInput,
) -> tuple[PortfolioItemModel, bool]:
    """
    Create a portfolio item for the given user.

    If verified_gig_id is provided, it must reference an existing gig.
    Returns (item, is_verified) where is_verified reflects the gig's current status.
    """
    if data.verified_gig_id:
        exists = await db.execute(
            select(GigModel.id).where(GigModel.id == data.verified_gig_id)
        )
        if exists.scalar_one_or_none() is None:
            raise PortfolioValidationError(
                "GIG_NOT_FOUND",
                f"Gig {data.verified_gig_id} not found",
            )

    item = PortfolioItemModel(
        user_id=user_id,
        title=data.title,
        description=data.description,
        file_keys=data.file_keys or [],
        external_url=data.external_url or None,
        github_url=data.github_url or None,
        cover_image_url=data.cover_image_url or None,
        tags=data.tags or [],
        verified_gig_id=data.verified_gig_id or None,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)

    is_verified = await _compute_is_verified(db, item.verified_gig_id)
    logger.info("portfolio item created item_id=%s user_id=%s", item.id, user_id)
    return item, is_verified


async def get_portfolio_items(
    db: AsyncSession,
    user_id: str,
) -> list[tuple[PortfolioItemModel, bool]]:
    """
    Return all portfolio items for a user, ordered by created_at DESC.

    Each tuple is (item, is_verified) where is_verified is True iff
    verified_gig_id is set and the linked gig.status == 'COMPLETED'.

    Uses a single bulk query for the badge check to avoid N+1 queries.
    """
    items_result = await db.execute(
        select(PortfolioItemModel)
        .where(PortfolioItemModel.user_id == user_id)
        .order_by(PortfolioItemModel.created_at.desc())
    )
    items = list(items_result.scalars().all())

    if not items:
        return []

    # Bulk-fetch completed gig IDs in one query (avoids N+1)
    gig_ids = [i.verified_gig_id for i in items if i.verified_gig_id]
    completed_gig_ids: set[str] = set()
    if gig_ids:
        gigs_result = await db.execute(
            select(GigModel.id)
            .where(GigModel.id.in_(gig_ids))
            .where(GigModel.status == _GIG_COMPLETED_STATUS)
        )
        completed_gig_ids = {row for row in gigs_result.scalars().all()}

    return [
        (
            item,
            item.verified_gig_id in completed_gig_ids
            if item.verified_gig_id
            else False,
        )
        for item in items
    ]


async def update_portfolio_item(
    db: AsyncSession,
    item_id: str,
    user_id: str,
    data: UpdatePortfolioItemInput,
) -> tuple[PortfolioItemModel, bool]:
    """
    Update a portfolio item. Raises PortfolioValidationError if:
    - item not found
    - caller is not the item owner

    Returns (item, is_verified).
    """
    result = await db.execute(
        select(PortfolioItemModel).where(PortfolioItemModel.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise PortfolioValidationError(
            "ITEM_NOT_FOUND", f"Portfolio item {item_id} not found"
        )
    if item.user_id != user_id:
        raise PortfolioValidationError(
            "FORBIDDEN", "Only the item owner may update this portfolio item"
        )

    if data.title is not None:
        item.title = data.title
    if data.description is not None:
        item.description = data.description
    if data.file_keys is not None:
        item.file_keys = data.file_keys
    if data.external_url is not None:
        item.external_url = data.external_url
    if data.github_url is not None:
        item.github_url = data.github_url
    if data.cover_image_url is not None:
        item.cover_image_url = data.cover_image_url
    if data.tags is not None:
        item.tags = data.tags

    await db.flush()
    await db.refresh(item)

    is_verified = await _compute_is_verified(db, item.verified_gig_id)
    logger.info("portfolio item updated item_id=%s user_id=%s", item.id, user_id)
    return item, is_verified


async def delete_portfolio_item(
    db: AsyncSession,
    item_id: str,
    user_id: str,
) -> None:
    """
    Delete a portfolio item. Raises PortfolioValidationError if:
    - item not found
    - caller is not the item owner
    """
    result = await db.execute(
        select(PortfolioItemModel).where(PortfolioItemModel.id == item_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        raise PortfolioValidationError(
            "ITEM_NOT_FOUND", f"Portfolio item {item_id} not found"
        )
    if item.user_id != user_id:
        raise PortfolioValidationError(
            "FORBIDDEN", "Only the item owner may delete this portfolio item"
        )

    await db.delete(item)
    await db.flush()
    logger.info("portfolio item deleted item_id=%s user_id=%s", item_id, user_id)
