"""
Unit tests for domain/reputation.py.

Uses SQLite in-memory (aiosqlite) — no Docker dependency.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.reputation import (
    ReputationError,
    get_reputation,
    upsert_reputation,
    validate_wallet_address,
)
from src.infra.database import Base

_TEST_WALLET = "0x" + "a" * 40
_TEST_WALLET_2 = "0x" + "b" * 40
_TEST_USER_ID = "aaaaaaaa-0000-0000-0000-000000000001"
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


# ---------------------------------------------------------------------------
# validate_wallet_address
# ---------------------------------------------------------------------------


class TestValidateWalletAddress:
    def test_valid_lowercase(self):
        result = validate_wallet_address(_TEST_WALLET)
        assert result == _TEST_WALLET.lower()

    def test_valid_mixed_case(self):
        addr = "0xAbCdEf1234567890AbCdEf1234567890AbCdEf12"
        result = validate_wallet_address(addr)
        assert result == addr.lower()

    def test_invalid_no_prefix(self):
        with pytest.raises(ReputationError) as exc_info:
            validate_wallet_address("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        assert exc_info.value.code == "INVALID_WALLET_ADDRESS"

    def test_invalid_too_short(self):
        with pytest.raises(ReputationError) as exc_info:
            validate_wallet_address("0xabc")
        assert exc_info.value.code == "INVALID_WALLET_ADDRESS"

    def test_invalid_non_hex(self):
        with pytest.raises(ReputationError) as exc_info:
            validate_wallet_address("0x" + "z" * 40)
        assert exc_info.value.code == "INVALID_WALLET_ADDRESS"


# ---------------------------------------------------------------------------
# get_reputation
# ---------------------------------------------------------------------------


class TestGetReputation:
    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_wallet(self, db: AsyncSession):
        result = await get_reputation(db, _TEST_WALLET)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_record_after_upsert(self, db: AsyncSession):
        await upsert_reputation(db, _TEST_WALLET, gigs_completed=5)
        result = await get_reputation(db, _TEST_WALLET)
        assert result is not None
        assert result.gigs_completed == 5

    @pytest.mark.asyncio
    async def test_case_insensitive_lookup(self, db: AsyncSession):
        await upsert_reputation(db, _TEST_WALLET.upper(), gigs_completed=3)
        result = await get_reputation(db, _TEST_WALLET.lower())
        assert result is not None
        assert result.gigs_completed == 3

    @pytest.mark.asyncio
    async def test_invalid_wallet_raises_error(self, db: AsyncSession):
        with pytest.raises(ReputationError) as exc_info:
            await get_reputation(db, "not-a-wallet")
        assert exc_info.value.code == "INVALID_WALLET_ADDRESS"


# ---------------------------------------------------------------------------
# upsert_reputation
# ---------------------------------------------------------------------------


class TestUpsertReputation:
    @pytest.mark.asyncio
    async def test_creates_new_record(self, db: AsyncSession):
        record = await upsert_reputation(
            db,
            _TEST_WALLET,
            user_id=_TEST_USER_ID,
            gigs_completed=10,
            total_earned="5000000000000000000",
            average_ai_score=85,
        )
        assert record.id is not None
        assert record.wallet_address == _TEST_WALLET.lower()
        assert record.user_id == _TEST_USER_ID
        assert record.gigs_completed == 10
        assert record.total_earned == "5000000000000000000"
        assert record.average_ai_score == 85

    @pytest.mark.asyncio
    async def test_defaults_for_new_record(self, db: AsyncSession):
        record = await upsert_reputation(db, _TEST_WALLET)
        assert record.gigs_completed == 0
        assert record.gigs_as_client == 0
        assert record.total_earned == "0"
        assert record.average_ai_score == 0
        assert record.dispute_rate_pct == 0
        assert record.average_rating_x100 == 0
        assert record.rating_count == 0

    @pytest.mark.asyncio
    async def test_updates_existing_record(self, db: AsyncSession):
        await upsert_reputation(db, _TEST_WALLET, gigs_completed=5)
        updated = await upsert_reputation(db, _TEST_WALLET, gigs_completed=10)
        assert updated.gigs_completed == 10

    @pytest.mark.asyncio
    async def test_partial_update_preserves_other_fields(self, db: AsyncSession):
        await upsert_reputation(
            db,
            _TEST_WALLET,
            gigs_completed=5,
            total_earned="1000",
            average_ai_score=80,
        )
        updated = await upsert_reputation(db, _TEST_WALLET, gigs_completed=10)
        assert updated.gigs_completed == 10
        assert updated.total_earned == "1000"
        assert updated.average_ai_score == 80

    @pytest.mark.asyncio
    async def test_independent_wallets(self, db: AsyncSession):
        await upsert_reputation(db, _TEST_WALLET, gigs_completed=5)
        await upsert_reputation(db, _TEST_WALLET_2, gigs_completed=10)

        r1 = await get_reputation(db, _TEST_WALLET)
        r2 = await get_reputation(db, _TEST_WALLET_2)
        assert r1 is not None and r1.gigs_completed == 5
        assert r2 is not None and r2.gigs_completed == 10

    @pytest.mark.asyncio
    async def test_update_rating_fields(self, db: AsyncSession):
        record = await upsert_reputation(
            db,
            _TEST_WALLET,
            average_rating_x100=450,
            rating_count=10,
        )
        assert record.average_rating_x100 == 450
        assert record.rating_count == 10
