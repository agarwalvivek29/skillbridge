"""
E2E tests for GET /v1/reputation/{wallet_address}.

Uses SQLite in-memory + FastAPI dependency_overrides.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.domain.reputation import upsert_reputation
from src.infra.models import ReputationModel


_TEST_WALLET = "0x" + "a" * 40
_BEARER = "Bearer "


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"{_BEARER}{token}"}


def _api_key_header() -> dict[str, str]:
    return {"X-API-Key": "test-api-key-minimum-16-chars"}


# ---------------------------------------------------------------------------
# Helpers — seed reputation data directly via domain layer
# ---------------------------------------------------------------------------


async def _seed_reputation(
    db_engine, wallet: str = _TEST_WALLET, **kwargs: object
) -> ReputationModel:
    """Insert a reputation record for testing."""
    factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        record = await upsert_reputation(session, wallet, **kwargs)
        await session.commit()
        return record


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetReputationEndpoint:
    @pytest.mark.asyncio
    async def test_returns_reputation(self, client: AsyncClient, db_engine):
        await _seed_reputation(
            db_engine,
            gigs_completed=5,
            total_earned="5000000000000000000",
            average_ai_score=85,
        )
        resp = await client.get(
            f"/v1/reputation/{_TEST_WALLET}",
            headers=_api_key_header(),
        )
        assert resp.status_code == 200
        data = resp.json()
        rep = data["reputation"]
        assert rep["wallet_address"] == _TEST_WALLET.lower()
        assert rep["gigs_completed"] == 5
        assert rep["total_earned"] == "5000000000000000000"
        assert rep["average_ai_score"] == 85

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_wallet(self, client: AsyncClient):
        unknown = "0x" + "c" * 40
        resp = await client.get(
            f"/v1/reputation/{unknown}",
            headers=_api_key_header(),
        )
        assert resp.status_code == 404
        data = resp.json()
        detail = data["detail"]
        assert detail["code"] == "REPUTATION_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_returns_400_for_invalid_wallet(self, client: AsyncClient):
        resp = await client.get(
            "/v1/reputation/not-a-wallet",
            headers=_api_key_header(),
        )
        assert resp.status_code == 400
        data = resp.json()
        detail = data["detail"]
        assert detail["code"] == "INVALID_WALLET_ADDRESS"

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get(f"/v1/reputation/{_TEST_WALLET}")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_default_fields_for_new_record(self, client: AsyncClient, db_engine):
        await _seed_reputation(db_engine)
        resp = await client.get(
            f"/v1/reputation/{_TEST_WALLET}",
            headers=_api_key_header(),
        )
        assert resp.status_code == 200
        rep = resp.json()["reputation"]
        assert rep["gigs_completed"] == 0
        assert rep["gigs_as_client"] == 0
        assert rep["total_earned"] == "0"
        assert rep["average_ai_score"] == 0
        assert rep["dispute_rate_pct"] == 0
        assert rep["average_rating_x100"] == 0
        assert rep["rating_count"] == 0
