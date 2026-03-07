"""Portfolio domain logic — pure business functions with no FastAPI imports.

All functions receive a SQLAlchemy AsyncSession and operate on ORM models.
The badge computation logic lives here: verified_gig_id is set AND the linked
gig has status GIG_STATUS_COMPLETED.
"""

from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.database import GigModel, GigStatus, PortfolioItemModel


def compute_is_verified(item: PortfolioItemModel, gig: GigModel | None) -> bool:
    """Compute the Verified Delivery badge status for a portfolio item.

    Returns True only when:
    1. The item has a verified_gig_id (links to a gig)
    2. That gig exists and has status GIG_STATUS_COMPLETED
    """
    if item.verified_gig_id is None:
        return False
    if gig is None:
        return False
    return gig.status == GigStatus.GIG_STATUS_COMPLETED


async def fetch_gig_for_item(session: AsyncSession, item: PortfolioItemModel) -> GigModel | None:
    """Fetch the linked gig for a portfolio item, if any."""
    if item.verified_gig_id is None:
        return None
    result = await session.execute(select(GigModel).where(GigModel.id == item.verified_gig_id))
    return result.scalar_one_or_none()


async def create_portfolio_item(
    session: AsyncSession,
    user_id: str,
    title: str,
    description: str,
    file_keys: list[str],
    external_url: str,
    tags: list[str],
    verified_gig_id: str | None,
) -> PortfolioItemModel:
    """Create a new portfolio item owned by `user_id`."""
    item = PortfolioItemModel(
        user_id=user_id,
        title=title,
        description=description,
        file_keys=file_keys,
        external_url=external_url,
        tags=tags,
        verified_gig_id=verified_gig_id,
    )
    session.add(item)
    await session.commit()
    await session.refresh(item)
    logger.info("Portfolio item created", item_id=item.id, user_id=user_id)
    return item


async def update_portfolio_item(
    session: AsyncSession,
    item_id: str,
    requesting_user_id: str,
    title: str,
    description: str,
    file_keys: list[str],
    external_url: str,
    tags: list[str],
) -> PortfolioItemModel:
    """Update an existing portfolio item.

    Raises PermissionError if the requesting user is not the owner.
    Raises LookupError if the item does not exist.
    """
    result = await session.execute(
        select(PortfolioItemModel).where(PortfolioItemModel.id == item_id)
    )
    item: PortfolioItemModel | None = result.scalar_one_or_none()
    if item is None:
        raise LookupError(f"Portfolio item {item_id!r} not found")
    if item.user_id != requesting_user_id:
        raise PermissionError(
            f"User {requesting_user_id!r} does not own portfolio item {item_id!r}"
        )

    item.title = title
    item.description = description
    item.file_keys = file_keys
    item.external_url = external_url
    item.tags = tags
    item.updated_at = datetime.now(UTC)  # type: ignore[assignment]
    await session.commit()
    await session.refresh(item)
    logger.info("Portfolio item updated", item_id=item_id, user_id=requesting_user_id)
    return item


async def delete_portfolio_item(
    session: AsyncSession,
    item_id: str,
    requesting_user_id: str,
) -> PortfolioItemModel:
    """Delete a portfolio item.

    Raises PermissionError if the requesting user is not the owner.
    Raises LookupError if the item does not exist.
    Returns the deleted item.
    """
    result = await session.execute(
        select(PortfolioItemModel).where(PortfolioItemModel.id == item_id)
    )
    item: PortfolioItemModel | None = result.scalar_one_or_none()
    if item is None:
        raise LookupError(f"Portfolio item {item_id!r} not found")
    if item.user_id != requesting_user_id:
        raise PermissionError(
            f"User {requesting_user_id!r} does not own portfolio item {item_id!r}"
        )

    await session.delete(item)
    await session.commit()
    logger.info("Portfolio item deleted", item_id=item_id, user_id=requesting_user_id)
    return item


async def list_portfolio_items(session: AsyncSession, user_id: str) -> list[PortfolioItemModel]:
    """List all portfolio items for a given user, newest first."""
    result = await session.execute(
        select(PortfolioItemModel)
        .where(PortfolioItemModel.user_id == user_id)
        .order_by(PortfolioItemModel.created_at.desc())
    )
    return list(result.scalars().all())
