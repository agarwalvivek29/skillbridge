"""Unit tests for nonce creation, expiry, and consumption."""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.auth import (
    _NONCE_ALPHABET,
    _NONCE_LENGTH,
    _generate_nonce,
    consume_nonce,
    create_nonce,
)
from src.infra.database import Base

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_WALLET = "11111111111111111111111111111111"


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


class TestGenerateNonce:
    def test_length_is_correct(self):
        nonce = _generate_nonce()
        assert len(nonce) == _NONCE_LENGTH

    def test_characters_are_alphanumeric(self):
        nonce = _generate_nonce()
        allowed = set(_NONCE_ALPHABET)
        assert all(c in allowed for c in nonce)

    def test_two_nonces_differ(self):
        # Probabilistically guaranteed; collision chance is negligible
        assert _generate_nonce() != _generate_nonce()


class TestCreateNonce:
    @pytest.mark.asyncio
    async def test_creates_record_with_correct_wallet(self, db_session: AsyncSession):
        record = await create_nonce(db_session, _WALLET)
        assert record.wallet_address == _WALLET.lower()

    @pytest.mark.asyncio
    async def test_normalises_wallet_to_lowercase(self, db_session: AsyncSession):
        mixed_case = "ABCDef1234567890abcdef1234567890ab"
        record = await create_nonce(db_session, mixed_case)
        assert record.wallet_address == mixed_case.lower()

    @pytest.mark.asyncio
    async def test_nonce_expires_in_future(self, db_session: AsyncSession):
        record = await create_nonce(db_session, _WALLET)
        now = datetime.now(timezone.utc)
        expires = record.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        assert expires > now

    @pytest.mark.asyncio
    async def test_second_create_overwrites_first(self, db_session: AsyncSession):
        r1 = await create_nonce(db_session, _WALLET)
        r2 = await create_nonce(db_session, _WALLET)
        assert r1.nonce != r2.nonce


class TestConsumeNonce:
    @pytest.mark.asyncio
    async def test_returns_record_for_valid_nonce(self, db_session: AsyncSession):
        await create_nonce(db_session, _WALLET)
        record = await consume_nonce(db_session, _WALLET)
        assert record is not None
        assert record.wallet_address == _WALLET.lower()

    @pytest.mark.asyncio
    async def test_deletes_nonce_on_consumption(self, db_session: AsyncSession):
        await create_nonce(db_session, _WALLET)
        await consume_nonce(db_session, _WALLET)
        # Second consume must return None
        result = await consume_nonce(db_session, _WALLET)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_nonce(self, db_session: AsyncSession):
        result = await consume_nonce(db_session, "22222222222222222222222222222222")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_expired_nonce(self, db_session: AsyncSession):
        """Nonce with expires_at in the past must not be consumed."""
        record = await create_nonce(db_session, _WALLET)
        # Manually backdate the expiry
        record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        await db_session.flush()

        result = await consume_nonce(db_session, _WALLET)
        assert result is None

    @pytest.mark.asyncio
    async def test_normalises_wallet_on_lookup(self, db_session: AsyncSession):
        mixed = "ABCDef1234567890abcdef1234567890ab"
        await create_nonce(db_session, mixed)
        result = await consume_nonce(db_session, mixed.lower())
        assert result is not None
