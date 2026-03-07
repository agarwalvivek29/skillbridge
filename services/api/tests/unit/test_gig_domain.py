"""
Unit tests for domain/gig.py.

Uses SQLite in-memory (aiosqlite) — no Docker dependency.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.gig import (
    CreateGigInput,
    GigValidationError,
    MilestoneInput,
    UpdateGigInput,
    create_gig,
    delete_gig,
    get_gig,
    list_gigs,
    update_gig,
)
from src.infra.database import Base

_TEST_CLIENT_ID = "aaaaaaaa-0000-0000-0000-000000000001"
_TEST_CLIENT_ID_2 = "aaaaaaaa-0000-0000-0000-000000000002"
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


def _make_milestones(n: int = 2, total: int = 1000) -> list[MilestoneInput]:
    per = total // n
    remainder = total - per * (n - 1)
    milestones = []
    for i in range(n):
        amount = remainder if i == n - 1 else per
        milestones.append(
            MilestoneInput(
                title=f"Milestone {i + 1}",
                description="Do the thing",
                acceptance_criteria="## Criteria\n- It works",
                amount=str(amount),
                order=i + 1,
            )
        )
    return milestones


def _make_input(**overrides) -> CreateGigInput:
    defaults = dict(
        title="Build a widget",
        description="Full description here",
        total_amount="1000",
        currency="ETH",
        token_address=None,
        tags=["python", "api"],
        required_skills=["Python", "FastAPI"],
        deadline=None,
        milestones=_make_milestones(2, 1000),
    )
    defaults.update(overrides)
    return CreateGigInput(**defaults)


# ---------------------------------------------------------------------------
# create_gig
# ---------------------------------------------------------------------------


class TestCreateGig:
    @pytest.mark.asyncio
    async def test_happy_path_creates_gig_in_draft(self, db: AsyncSession):
        gig = await create_gig(db, _TEST_CLIENT_ID, _make_input())
        assert gig.id is not None
        assert gig.status == "DRAFT"
        assert gig.client_id == _TEST_CLIENT_ID
        assert len(gig.milestones) == 2

    @pytest.mark.asyncio
    async def test_milestones_ordered_correctly(self, db: AsyncSession):
        gig = await create_gig(db, _TEST_CLIENT_ID, _make_input())
        orders = [m.order for m in gig.milestones]
        assert orders == sorted(orders)

    @pytest.mark.asyncio
    async def test_milestone_amounts_mismatch_raises_error(self, db: AsyncSession):
        bad_milestones = [
            MilestoneInput(
                title="A",
                description="d",
                acceptance_criteria="c",
                amount="300",
                order=1,
            ),
            MilestoneInput(
                title="B",
                description="d",
                acceptance_criteria="c",
                amount="300",
                order=2,
            ),
        ]
        with pytest.raises(GigValidationError) as exc_info:
            await create_gig(
                db, _TEST_CLIENT_ID, _make_input(milestones=bad_milestones)
            )
        assert exc_info.value.code == "MILESTONE_AMOUNT_MISMATCH"

    @pytest.mark.asyncio
    async def test_zero_milestones_raises_error(self, db: AsyncSession):
        with pytest.raises(GigValidationError) as exc_info:
            await create_gig(db, _TEST_CLIENT_ID, _make_input(milestones=[]))
        assert exc_info.value.code == "TOO_FEW_MILESTONES"

    @pytest.mark.asyncio
    async def test_too_many_milestones_raises_error(self, db: AsyncSession):
        milestones = _make_milestones(11, 1100)
        with pytest.raises(GigValidationError) as exc_info:
            await create_gig(
                db,
                _TEST_CLIENT_ID,
                _make_input(milestones=milestones, total_amount="1100"),
            )
        assert exc_info.value.code == "TOO_MANY_MILESTONES"

    @pytest.mark.asyncio
    async def test_eth_with_token_address_raises_error(self, db: AsyncSession):
        with pytest.raises(GigValidationError) as exc_info:
            await create_gig(
                db,
                _TEST_CLIENT_ID,
                _make_input(currency="ETH", token_address="0x" + "a" * 40),
            )
        assert exc_info.value.code == "TOKEN_ADDRESS_NOT_ALLOWED"

    @pytest.mark.asyncio
    async def test_usdc_without_token_address_raises_error(self, db: AsyncSession):
        with pytest.raises(GigValidationError) as exc_info:
            await create_gig(
                db,
                _TEST_CLIENT_ID,
                _make_input(currency="USDC", token_address=None),
            )
        assert exc_info.value.code == "TOKEN_ADDRESS_REQUIRED"

    @pytest.mark.asyncio
    async def test_usdc_with_valid_token_address(self, db: AsyncSession):
        usdc_address = "0x" + "b" * 40
        gig = await create_gig(
            db,
            _TEST_CLIENT_ID,
            _make_input(currency="USDC", token_address=usdc_address),
        )
        assert gig.currency == "USDC"
        assert gig.token_address == usdc_address

    @pytest.mark.asyncio
    async def test_invalid_token_address_format_raises_error(self, db: AsyncSession):
        with pytest.raises(GigValidationError) as exc_info:
            await create_gig(
                db,
                _TEST_CLIENT_ID,
                _make_input(currency="USDC", token_address="not-an-address"),
            )
        assert exc_info.value.code == "INVALID_TOKEN_ADDRESS"


# ---------------------------------------------------------------------------
# get_gig
# ---------------------------------------------------------------------------


class TestGetGig:
    @pytest.mark.asyncio
    async def test_returns_gig_with_milestones(self, db: AsyncSession):
        created = await create_gig(db, _TEST_CLIENT_ID, _make_input())
        fetched = await get_gig(db, created.id)
        assert fetched is not None
        assert fetched.id == created.id
        assert len(fetched.milestones) == 2

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_id(self, db: AsyncSession):
        result = await get_gig(db, "00000000-0000-0000-0000-000000000000")
        assert result is None


# ---------------------------------------------------------------------------
# list_gigs
# ---------------------------------------------------------------------------


class TestListGigs:
    @pytest.mark.asyncio
    async def test_draft_gigs_not_in_open_listing(self, db: AsyncSession):
        await create_gig(db, _TEST_CLIENT_ID, _make_input())
        gigs, total = await list_gigs(db, status="OPEN")
        assert total == 0
        assert gigs == []

    @pytest.mark.asyncio
    async def test_pagination(self, db: AsyncSession):
        # Create 3 DRAFT gigs then manually set them to OPEN for listing
        from sqlalchemy import update
        from src.infra.models import GigModel

        for i in range(3):
            await create_gig(db, _TEST_CLIENT_ID, _make_input(title=f"Gig {i}"))
        await db.execute(update(GigModel).values(status="OPEN"))
        await db.flush()

        page1, total = await list_gigs(db, status="OPEN", page=1, page_size=2)
        assert total == 3
        assert len(page1) == 2

        page2, _ = await list_gigs(db, status="OPEN", page=2, page_size=2)
        assert len(page2) == 1


# ---------------------------------------------------------------------------
# update_gig
# ---------------------------------------------------------------------------


class TestUpdateGig:
    @pytest.mark.asyncio
    async def test_update_title_on_draft_gig(self, db: AsyncSession):
        gig = await create_gig(db, _TEST_CLIENT_ID, _make_input())
        updated = await update_gig(
            db, gig.id, _TEST_CLIENT_ID, UpdateGigInput(title="New Title")
        )
        assert updated.title == "New Title"

    @pytest.mark.asyncio
    async def test_update_forbidden_for_non_owner(self, db: AsyncSession):
        gig = await create_gig(db, _TEST_CLIENT_ID, _make_input())
        with pytest.raises(GigValidationError) as exc_info:
            await update_gig(db, gig.id, _TEST_CLIENT_ID_2, UpdateGigInput(title="x"))
        assert exc_info.value.code == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_update_forbidden_on_open_gig(self, db: AsyncSession):
        from sqlalchemy import update as sa_update
        from src.infra.models import GigModel

        gig = await create_gig(db, _TEST_CLIENT_ID, _make_input())
        await db.execute(
            sa_update(GigModel).where(GigModel.id == gig.id).values(status="OPEN")
        )
        await db.flush()

        with pytest.raises(GigValidationError) as exc_info:
            await update_gig(db, gig.id, _TEST_CLIENT_ID, UpdateGigInput(title="x"))
        assert exc_info.value.code == "GIG_NOT_EDITABLE"

    @pytest.mark.asyncio
    async def test_update_milestones_replaces_existing(self, db: AsyncSession):
        gig = await create_gig(db, _TEST_CLIENT_ID, _make_input())
        new_milestones = [
            MilestoneInput(
                title="Only Milestone",
                description="d",
                acceptance_criteria="c",
                amount="1000",
                order=1,
            )
        ]
        updated = await update_gig(
            db,
            gig.id,
            _TEST_CLIENT_ID,
            UpdateGigInput(milestones=new_milestones),
        )
        assert len(updated.milestones) == 1
        assert updated.milestones[0].title == "Only Milestone"

    @pytest.mark.asyncio
    async def test_update_not_found(self, db: AsyncSession):
        with pytest.raises(GigValidationError) as exc_info:
            await update_gig(
                db,
                "00000000-0000-0000-0000-000000000000",
                _TEST_CLIENT_ID,
                UpdateGigInput(title="x"),
            )
        assert exc_info.value.code == "GIG_NOT_FOUND"


# ---------------------------------------------------------------------------
# delete_gig
# ---------------------------------------------------------------------------


class TestDeleteGig:
    @pytest.mark.asyncio
    async def test_delete_draft_gig(self, db: AsyncSession):
        gig = await create_gig(db, _TEST_CLIENT_ID, _make_input())
        await delete_gig(db, gig.id, _TEST_CLIENT_ID)
        result = await get_gig(db, gig.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_forbidden_for_non_owner(self, db: AsyncSession):
        gig = await create_gig(db, _TEST_CLIENT_ID, _make_input())
        with pytest.raises(GigValidationError) as exc_info:
            await delete_gig(db, gig.id, _TEST_CLIENT_ID_2)
        assert exc_info.value.code == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_delete_forbidden_on_open_gig(self, db: AsyncSession):
        from sqlalchemy import update as sa_update
        from src.infra.models import GigModel

        gig = await create_gig(db, _TEST_CLIENT_ID, _make_input())
        await db.execute(
            sa_update(GigModel).where(GigModel.id == gig.id).values(status="OPEN")
        )
        await db.flush()

        with pytest.raises(GigValidationError) as exc_info:
            await delete_gig(db, gig.id, _TEST_CLIENT_ID)
        assert exc_info.value.code == "GIG_NOT_DELETABLE"

    @pytest.mark.asyncio
    async def test_delete_not_found(self, db: AsyncSession):
        with pytest.raises(GigValidationError) as exc_info:
            await delete_gig(
                db, "00000000-0000-0000-0000-000000000000", _TEST_CLIENT_ID
            )
        assert exc_info.value.code == "GIG_NOT_FOUND"
