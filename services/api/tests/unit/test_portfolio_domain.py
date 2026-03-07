"""
Unit tests for domain/portfolio.py.

Uses SQLite in-memory (aiosqlite) — no Docker dependency.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.portfolio import (
    CreatePortfolioItemInput,
    PortfolioValidationError,
    UpdatePortfolioItemInput,
    create_portfolio_item,
    delete_portfolio_item,
    get_portfolio_items,
    update_portfolio_item,
)
from src.infra.database import Base
from src.infra.models import GigModel, UserModel

_TEST_USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
_TEST_USER_ID_2 = "aaaaaaaa-0000-0000-0000-000000000002"
_TEST_GIG_ID = "bbbbbbbb-0000-0000-0000-000000000001"
_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _seed_user(db: AsyncSession, user_id: str) -> UserModel:
    user = UserModel(
        id=user_id,
        name="Test User",
        email=f"{user_id}@example.com",
        role="USER_ROLE_FREELANCER",
    )
    db.add(user)
    await db.flush()
    return user


async def _seed_gig(db: AsyncSession, status: str = "COMPLETED") -> GigModel:
    gig = GigModel(
        id=_TEST_GIG_ID,
        client_id=_TEST_USER_ID,
        title="Test Gig",
        description="Test gig description",
        total_amount="1000",
        currency="ETH",
        status=status,
        tags=[],
        required_skills=[],
    )
    db.add(gig)
    await db.flush()
    return gig


def _make_create_input(**overrides) -> CreatePortfolioItemInput:
    defaults = dict(
        title="My Portfolio Item",
        description="A detailed description of my work",
        file_keys=["portfolio/file1.pdf"],
        external_url="https://github.com/example/project",
        tags=["python", "fastapi"],
        verified_gig_id=None,
    )
    defaults.update(overrides)
    return CreatePortfolioItemInput(**defaults)


# ---------------------------------------------------------------------------
# create_portfolio_item
# ---------------------------------------------------------------------------


class TestCreatePortfolioItem:
    @pytest.mark.asyncio
    async def test_happy_path_creates_item(self, db: AsyncSession):
        await _seed_user(db, _TEST_USER_ID)
        item, is_verified = await create_portfolio_item(
            db, _TEST_USER_ID, _make_create_input()
        )
        assert item.id is not None
        assert item.user_id == _TEST_USER_ID
        assert item.title == "My Portfolio Item"
        assert is_verified is False

    @pytest.mark.asyncio
    async def test_creates_item_with_default_empty_lists(self, db: AsyncSession):
        await _seed_user(db, _TEST_USER_ID)
        inp = CreatePortfolioItemInput(title="T", description="D")
        item, _ = await create_portfolio_item(db, _TEST_USER_ID, inp)
        assert item.file_keys == []
        assert item.tags == []

    @pytest.mark.asyncio
    async def test_linked_to_completed_gig_is_verified(self, db: AsyncSession):
        await _seed_user(db, _TEST_USER_ID)
        await _seed_gig(db, status="COMPLETED")
        item, is_verified = await create_portfolio_item(
            db, _TEST_USER_ID, _make_create_input(verified_gig_id=_TEST_GIG_ID)
        )
        assert item.verified_gig_id == _TEST_GIG_ID
        assert is_verified is True

    @pytest.mark.asyncio
    async def test_linked_to_in_progress_gig_not_verified(self, db: AsyncSession):
        await _seed_user(db, _TEST_USER_ID)
        await _seed_gig(db, status="IN_PROGRESS")
        item, is_verified = await create_portfolio_item(
            db, _TEST_USER_ID, _make_create_input(verified_gig_id=_TEST_GIG_ID)
        )
        assert is_verified is False

    @pytest.mark.asyncio
    async def test_unknown_verified_gig_id_raises_error(self, db: AsyncSession):
        await _seed_user(db, _TEST_USER_ID)
        with pytest.raises(PortfolioValidationError) as exc_info:
            await create_portfolio_item(
                db,
                _TEST_USER_ID,
                _make_create_input(
                    verified_gig_id="00000000-0000-0000-0000-000000000000"
                ),
            )
        assert exc_info.value.code == "GIG_NOT_FOUND"


# ---------------------------------------------------------------------------
# get_portfolio_items
# ---------------------------------------------------------------------------


class TestGetPortfolioItems:
    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_user(self, db: AsyncSession):
        result = await get_portfolio_items(db, "00000000-0000-0000-0000-000000000000")
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_items_ordered_by_created_at_desc(self, db: AsyncSession):
        await _seed_user(db, _TEST_USER_ID)
        for i in range(3):
            await create_portfolio_item(
                db,
                _TEST_USER_ID,
                CreatePortfolioItemInput(title=f"Item {i}", description="d"),
            )

        pairs = await get_portfolio_items(db, _TEST_USER_ID)
        assert len(pairs) == 3
        # SQLite stores created_at with second precision; items created within the same
        # second may have equal timestamps. Just verify all 3 are returned.
        titles = [item.title for item, _ in pairs]
        assert set(titles) == {"Item 0", "Item 1", "Item 2"}

    @pytest.mark.asyncio
    async def test_badge_true_for_completed_gig(self, db: AsyncSession):
        await _seed_user(db, _TEST_USER_ID)
        await _seed_gig(db, status="COMPLETED")
        await create_portfolio_item(
            db, _TEST_USER_ID, _make_create_input(verified_gig_id=_TEST_GIG_ID)
        )

        pairs = await get_portfolio_items(db, _TEST_USER_ID)
        assert len(pairs) == 1
        _, is_verified = pairs[0]
        assert is_verified is True

    @pytest.mark.asyncio
    async def test_badge_false_for_non_completed_gig(self, db: AsyncSession):
        await _seed_user(db, _TEST_USER_ID)
        await _seed_gig(db, status="OPEN")
        await create_portfolio_item(
            db, _TEST_USER_ID, _make_create_input(verified_gig_id=_TEST_GIG_ID)
        )

        pairs = await get_portfolio_items(db, _TEST_USER_ID)
        _, is_verified = pairs[0]
        assert is_verified is False

    @pytest.mark.asyncio
    async def test_badge_false_when_no_verified_gig_id(self, db: AsyncSession):
        await _seed_user(db, _TEST_USER_ID)
        await create_portfolio_item(db, _TEST_USER_ID, _make_create_input())

        pairs = await get_portfolio_items(db, _TEST_USER_ID)
        _, is_verified = pairs[0]
        assert is_verified is False

    @pytest.mark.asyncio
    async def test_only_returns_items_for_requested_user(self, db: AsyncSession):
        await _seed_user(db, _TEST_USER_ID)
        await _seed_user(db, _TEST_USER_ID_2)
        await create_portfolio_item(
            db, _TEST_USER_ID, _make_create_input(title="User1")
        )
        await create_portfolio_item(
            db, _TEST_USER_ID_2, _make_create_input(title="User2")
        )

        pairs = await get_portfolio_items(db, _TEST_USER_ID)
        assert len(pairs) == 1
        assert pairs[0][0].title == "User1"


# ---------------------------------------------------------------------------
# update_portfolio_item
# ---------------------------------------------------------------------------


class TestUpdatePortfolioItem:
    @pytest.mark.asyncio
    async def test_owner_can_update_title(self, db: AsyncSession):
        await _seed_user(db, _TEST_USER_ID)
        item, _ = await create_portfolio_item(db, _TEST_USER_ID, _make_create_input())

        updated, _ = await update_portfolio_item(
            db, item.id, _TEST_USER_ID, UpdatePortfolioItemInput(title="New Title")
        )
        assert updated.title == "New Title"

    @pytest.mark.asyncio
    async def test_owner_can_update_file_keys(self, db: AsyncSession):
        await _seed_user(db, _TEST_USER_ID)
        item, _ = await create_portfolio_item(db, _TEST_USER_ID, _make_create_input())

        updated, _ = await update_portfolio_item(
            db,
            item.id,
            _TEST_USER_ID,
            UpdatePortfolioItemInput(file_keys=["portfolio/new.pdf"]),
        )
        assert updated.file_keys == ["portfolio/new.pdf"]

    @pytest.mark.asyncio
    async def test_non_owner_cannot_update(self, db: AsyncSession):
        await _seed_user(db, _TEST_USER_ID)
        await _seed_user(db, _TEST_USER_ID_2)
        item, _ = await create_portfolio_item(db, _TEST_USER_ID, _make_create_input())

        with pytest.raises(PortfolioValidationError) as exc_info:
            await update_portfolio_item(
                db, item.id, _TEST_USER_ID_2, UpdatePortfolioItemInput(title="x")
            )
        assert exc_info.value.code == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_unknown_item_raises_not_found(self, db: AsyncSession):
        with pytest.raises(PortfolioValidationError) as exc_info:
            await update_portfolio_item(
                db,
                "00000000-0000-0000-0000-000000000000",
                _TEST_USER_ID,
                UpdatePortfolioItemInput(title="x"),
            )
        assert exc_info.value.code == "ITEM_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_preserves_verified_gig_id(self, db: AsyncSession):
        await _seed_user(db, _TEST_USER_ID)
        await _seed_gig(db, status="COMPLETED")
        item, _ = await create_portfolio_item(
            db, _TEST_USER_ID, _make_create_input(verified_gig_id=_TEST_GIG_ID)
        )

        updated, is_verified = await update_portfolio_item(
            db, item.id, _TEST_USER_ID, UpdatePortfolioItemInput(title="Updated")
        )
        assert updated.verified_gig_id == _TEST_GIG_ID
        assert is_verified is True


# ---------------------------------------------------------------------------
# delete_portfolio_item
# ---------------------------------------------------------------------------


class TestDeletePortfolioItem:
    @pytest.mark.asyncio
    async def test_owner_can_delete(self, db: AsyncSession):
        await _seed_user(db, _TEST_USER_ID)
        item, _ = await create_portfolio_item(db, _TEST_USER_ID, _make_create_input())

        await delete_portfolio_item(db, item.id, _TEST_USER_ID)

        pairs = await get_portfolio_items(db, _TEST_USER_ID)
        assert pairs == []

    @pytest.mark.asyncio
    async def test_non_owner_cannot_delete(self, db: AsyncSession):
        await _seed_user(db, _TEST_USER_ID)
        await _seed_user(db, _TEST_USER_ID_2)
        item, _ = await create_portfolio_item(db, _TEST_USER_ID, _make_create_input())

        with pytest.raises(PortfolioValidationError) as exc_info:
            await delete_portfolio_item(db, item.id, _TEST_USER_ID_2)
        assert exc_info.value.code == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_unknown_item_raises_not_found(self, db: AsyncSession):
        with pytest.raises(PortfolioValidationError) as exc_info:
            await delete_portfolio_item(
                db, "00000000-0000-0000-0000-000000000000", _TEST_USER_ID
            )
        assert exc_info.value.code == "ITEM_NOT_FOUND"
