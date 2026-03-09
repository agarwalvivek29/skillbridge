"""E2E tests for GET /v1/reputation/{wallet_address}."""

from __future__ import annotations
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from src.domain.reputation import upsert_reputation

_TEST_WALLET = "0x" + "a" * 40


async def _seed_reputation(db_engine, wallet=_TEST_WALLET, **kwargs):
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        record = await upsert_reputation(session, wallet, **kwargs)
        await session.commit()
        return record


class TestGetReputationEndpoint:
    @pytest.mark.asyncio
    async def test_returns_reputation(self, client: AsyncClient, db_engine):
        await _seed_reputation(
            db_engine,
            gigs_completed=5,
            total_earned="5000000000000000000",
            average_ai_score=85,
        )
        resp = await client.get(f"/v1/reputation/{_TEST_WALLET}")
        assert resp.status_code == 200
        rep = resp.json()["reputation"]
        assert rep["gigs_completed"] == 5

    @pytest.mark.asyncio
    async def test_returns_zeroed_default_for_unknown(self, client: AsyncClient):
        resp = await client.get("/v1/reputation/0x" + "c" * 40)
        assert resp.status_code == 200
        assert resp.json()["reputation"]["gigs_completed"] == 0

    @pytest.mark.asyncio
    async def test_returns_400_for_invalid_wallet(self, client: AsyncClient):
        resp = await client.get("/v1/reputation/not-a-wallet")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_public_no_auth_required(self, client: AsyncClient, db_engine):
        await _seed_reputation(db_engine)
        resp = await client.get(f"/v1/reputation/{_TEST_WALLET}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_default_fields(self, client: AsyncClient, db_engine):
        await _seed_reputation(db_engine)
        rep = (await client.get(f"/v1/reputation/{_TEST_WALLET}")).json()["reputation"]
        assert rep["gigs_completed"] == 0
        assert rep["total_earned"] == "0"
