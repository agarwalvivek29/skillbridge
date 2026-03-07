"""
domain/portfolio.py — Pure business logic for portfolio items.
No FastAPI imports. All side-effect-free helpers + DB-taking functions.
"""

import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.models import PortfolioItemModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Badge / verification helpers
# ---------------------------------------------------------------------------

# Status string for a completed gig (proto enum value)
_GIG_STATUS_COMPLETED = "GIG_STATUS_COMPLETED"


async def compute_is_verified(db: AsyncSession, verified_gig_id: str | None) -> bool:
    """
    Return True only when:
      1. verified_gig_id is set (non-empty), AND
      2. The linked gig exists and has status GIG_STATUS_COMPLETED.

    If the gig is not found (or the table doesn't exist), safely returns False.
    """
    if not verified_gig_id:
        return False

    try:
        from src.infra.models import GigModel

        result = await db.execute(
            select(GigModel).where(GigModel.id == verified_gig_id)
        )
        gig = result.scalar_one_or_none()
        if gig is None:
            return False
        return gig.status == _GIG_STATUS_COMPLETED
    except Exception:  # noqa: BLE001
        # Any DB error (e.g. table doesn't exist in test) → safe default
        return False


# ---------------------------------------------------------------------------
# S3 key helpers
# ---------------------------------------------------------------------------

_UNSAFE_PATH_RE = re.compile(r"[^\w.\-]")


def generate_s3_key(user_id: str, filename: str) -> str:
    """
    Generate a safe S3 key for a portfolio upload.
    Format: portfolio/{user_id}/{uuid4}-{sanitized_filename}
    Prevents path traversal by stripping any non-word characters except `.` and `-`.
    """
    safe_name = _UNSAFE_PATH_RE.sub("_", filename)
    # Prevent any residual path traversal
    safe_name = safe_name.replace("..", "_")
    return f"portfolio/{user_id}/{uuid.uuid4()}-{safe_name}"


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------


async def create_portfolio_item(
    db: AsyncSession,
    user_id: str,
    title: str,
    description: str | None,
    file_keys: list[str],
    external_url: str | None,
    tags: list[str],
    verified_gig_id: str | None,
) -> PortfolioItemModel:
    """Create and persist a new portfolio item. Returns the saved model."""
    item = PortfolioItemModel(
        user_id=user_id,
        title=title,
        description=description,
        file_keys=file_keys,
        external_url=external_url,
        tags=tags,
        verified_gig_id=verified_gig_id,
    )
    db.add(item)
    await db.flush()
    logger.info("portfolio item_id=%s user_id=%s operation=create", item.id, user_id)
    return item


async def get_portfolio_item(
    db: AsyncSession, item_id: str
) -> PortfolioItemModel | None:
    """Fetch a single portfolio item by id. Returns None if not found."""
    result = await db.execute(
        select(PortfolioItemModel).where(PortfolioItemModel.id == item_id)
    )
    return result.scalar_one_or_none()


async def get_portfolio_items_for_user(
    db: AsyncSession, user_id: str
) -> list[PortfolioItemModel]:
    """Return all portfolio items for a user, ordered by created_at DESC."""
    result = await db.execute(
        select(PortfolioItemModel)
        .where(PortfolioItemModel.user_id == user_id)
        .order_by(PortfolioItemModel.created_at.desc())
    )
    return list(result.scalars().all())


async def update_portfolio_item(
    db: AsyncSession,
    item: PortfolioItemModel,
    title: str | None,
    description: str | None,
    file_keys: list[str] | None,
    external_url: str | None,
    tags: list[str] | None,
) -> PortfolioItemModel:
    """Apply partial updates to a portfolio item. Only non-None fields are updated."""
    if title is not None:
        item.title = title
    if description is not None:
        item.description = description
    if file_keys is not None:
        item.file_keys = file_keys
    if external_url is not None:
        item.external_url = external_url
    if tags is not None:
        item.tags = tags
    item.updated_at = datetime.now(timezone.utc)
    await db.flush()
    logger.info(
        "portfolio item_id=%s user_id=%s operation=update", item.id, item.user_id
    )
    return item


async def delete_portfolio_item(db: AsyncSession, item: PortfolioItemModel) -> None:
    """Delete a portfolio item."""
    logger.info(
        "portfolio item_id=%s user_id=%s operation=delete", item.id, item.user_id
    )
    await db.delete(item)
    await db.flush()
