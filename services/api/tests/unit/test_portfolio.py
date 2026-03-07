"""Unit tests for portfolio domain logic.

These tests cover pure functions with no I/O. Database interactions are mocked
using AsyncMock / MagicMock to keep tests fast and isolated.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.domain.portfolio import (
    compute_is_verified,
    create_portfolio_item,
    delete_portfolio_item,
    list_portfolio_items,
    update_portfolio_item,
)
from src.infra.database import GigModel, GigStatus, PortfolioItemModel

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_item(
    *,
    item_id: str = "item-1",
    user_id: str = "user-1",
    verified_gig_id: str | None = None,
) -> PortfolioItemModel:
    item = MagicMock(spec=PortfolioItemModel)
    item.id = item_id
    item.user_id = user_id
    item.title = "My Project"
    item.description = "A great project"
    item.file_keys = []
    item.external_url = ""
    item.tags = []
    item.verified_gig_id = verified_gig_id
    item.created_at = datetime.now(UTC)
    item.updated_at = datetime.now(UTC)
    return item


def _make_gig(*, status: GigStatus = GigStatus.GIG_STATUS_COMPLETED) -> GigModel:
    gig = MagicMock(spec=GigModel)
    gig.id = "gig-1"
    gig.status = status
    return gig


# ─── compute_is_verified tests ────────────────────────────────────────────────


def test_compute_is_verified_with_completed_gig() -> None:
    item = _make_item(verified_gig_id="gig-1")
    gig = _make_gig(status=GigStatus.GIG_STATUS_COMPLETED)
    assert compute_is_verified(item, gig) is True


def test_compute_is_verified_with_non_completed_gig() -> None:
    item = _make_item(verified_gig_id="gig-1")
    for non_terminal_status in [
        GigStatus.GIG_STATUS_OPEN,
        GigStatus.GIG_STATUS_IN_PROGRESS,
        GigStatus.GIG_STATUS_DRAFT,
        GigStatus.GIG_STATUS_DISPUTED,
        GigStatus.GIG_STATUS_CANCELLED,
    ]:
        gig = _make_gig(status=non_terminal_status)
        assert compute_is_verified(item, gig) is False, (
            f"Expected False for status {non_terminal_status}"
        )


def test_compute_is_verified_with_no_gig_id() -> None:
    item = _make_item(verified_gig_id=None)
    assert compute_is_verified(item, None) is False


def test_compute_is_verified_with_missing_gig() -> None:
    """verified_gig_id set but gig record does not exist in DB."""
    item = _make_item(verified_gig_id="nonexistent-gig")
    assert compute_is_verified(item, None) is False


# ─── create_portfolio_item tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_portfolio_item_returns_item() -> None:
    session = AsyncMock()
    session.add = MagicMock()  # synchronous — not a coroutine
    created_item = _make_item(user_id="user-42")
    session.refresh = AsyncMock()

    with patch("src.domain.portfolio.PortfolioItemModel", return_value=created_item):
        result = await create_portfolio_item(
            session=session,
            user_id="user-42",
            title="My Project",
            description="A description",
            file_keys=["uploads/img.png"],
            external_url="https://github.com/user/project",
            tags=["python", "fastapi"],
            verified_gig_id=None,
        )

    session.add.assert_called_once()
    session.commit.assert_awaited_once()
    assert result.user_id == "user-42"


# ─── update_portfolio_item tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_portfolio_item_by_owner() -> None:
    session = AsyncMock()
    item = _make_item(user_id="user-1")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = item
    session.execute = AsyncMock(return_value=mock_result)

    result = await update_portfolio_item(
        session=session,
        item_id="item-1",
        requesting_user_id="user-1",
        title="Updated Title",
        description="Updated",
        file_keys=[],
        external_url="",
        tags=[],
    )

    session.commit.assert_awaited_once()
    assert result.title == "Updated Title"


@pytest.mark.asyncio
async def test_update_portfolio_item_raises_permission_error_for_non_owner() -> None:
    session = AsyncMock()
    item = _make_item(user_id="user-1")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = item
    session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(PermissionError):
        await update_portfolio_item(
            session=session,
            item_id="item-1",
            requesting_user_id="attacker-99",
            title="Hacked",
            description="",
            file_keys=[],
            external_url="",
            tags=[],
        )


@pytest.mark.asyncio
async def test_update_portfolio_item_raises_lookup_error_if_not_found() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(LookupError):
        await update_portfolio_item(
            session=session,
            item_id="nonexistent",
            requesting_user_id="user-1",
            title="",
            description="",
            file_keys=[],
            external_url="",
            tags=[],
        )


# ─── delete_portfolio_item tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_portfolio_item_by_owner() -> None:
    session = AsyncMock()
    item = _make_item(user_id="user-1")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = item
    session.execute = AsyncMock(return_value=mock_result)

    result = await delete_portfolio_item(
        session=session,
        item_id="item-1",
        requesting_user_id="user-1",
    )

    session.delete.assert_awaited_once_with(item)
    session.commit.assert_awaited_once()
    assert result is item


@pytest.mark.asyncio
async def test_delete_portfolio_item_raises_permission_error_for_non_owner() -> None:
    session = AsyncMock()
    item = _make_item(user_id="user-1")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = item
    session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(PermissionError):
        await delete_portfolio_item(
            session=session,
            item_id="item-1",
            requesting_user_id="attacker-99",
        )


@pytest.mark.asyncio
async def test_delete_portfolio_item_raises_lookup_error_if_not_found() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(LookupError):
        await delete_portfolio_item(
            session=session,
            item_id="nonexistent",
            requesting_user_id="user-1",
        )


# ─── list_portfolio_items tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_portfolio_items_returns_ordered_list() -> None:
    session = AsyncMock()
    items = [_make_item(item_id=f"item-{i}") for i in range(3)]
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = items
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    session.execute = AsyncMock(return_value=mock_result)

    result = await list_portfolio_items(session, "user-1")

    assert len(result) == 3
    assert result == items
