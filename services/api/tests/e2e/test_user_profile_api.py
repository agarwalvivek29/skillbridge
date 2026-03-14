"""
E2E tests for user profile endpoints.

Runs against in-memory SQLite via conftest.py fixture.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FREELANCER_PAYLOAD = {
    "email": "profile-freelancer@example.com",
    "password": "strongPass1",
    "name": "Alice Profile",
    "role": "USER_ROLE_FREELANCER",
}


async def _register_and_get_token(
    client: AsyncClient, payload: dict
) -> tuple[str, str]:
    """Register a user and return (access_token, user_id)."""
    resp = await client.post("/v1/auth/email/register", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return data["access_token"], data["user_id"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /v1/users/profile
# ---------------------------------------------------------------------------


class TestUpdateProfile:
    @pytest.mark.asyncio
    async def test_update_name(self, client: AsyncClient):
        token, _ = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        resp = await client.post(
            "/v1/users/profile",
            json={"name": "New Name"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_update_bio(self, client: AsyncClient):
        token, _ = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        resp = await client.post(
            "/v1/users/profile",
            json={"bio": "I build things"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["bio"] == "I build things"

    @pytest.mark.asyncio
    async def test_update_skills_and_rate(self, client: AsyncClient):
        token, _ = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        resp = await client.post(
            "/v1/users/profile",
            json={"skills": ["rust", "python"], "hourly_rate_wei": "50000000000000000"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["skills"] == ["rust", "python"]
        assert data["hourly_rate_wei"] == "50000000000000000"

    @pytest.mark.asyncio
    async def test_update_avatar_url(self, client: AsyncClient):
        token, _ = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        resp = await client.post(
            "/v1/users/profile",
            json={"avatar_url": "https://example.com/avatar.png"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["avatar_url"] == "https://example.com/avatar.png"

    @pytest.mark.asyncio
    async def test_name_too_long(self, client: AsyncClient):
        token, _ = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        resp = await client.post(
            "/v1/users/profile",
            json={"name": "x" * 101},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_bio_too_long(self, client: AsyncClient):
        token, _ = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        resp = await client.post(
            "/v1/users/profile",
            json={"bio": "x" * 501},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_avatar_url(self, client: AsyncClient):
        token, _ = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        resp = await client.post(
            "/v1/users/profile",
            json={"avatar_url": "not-a-url"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_hourly_rate(self, client: AsyncClient):
        token, _ = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        resp = await client.post(
            "/v1/users/profile",
            json={"hourly_rate_wei": "not-a-number"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/v1/users/profile",
            json={"name": "Hacker"},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /v1/users/{address}/profile
# ---------------------------------------------------------------------------


class TestGetProfile:
    @pytest.mark.asyncio
    async def test_get_profile_by_wallet_address(self, client: AsyncClient, db_session):
        """Register via email, manually set wallet_address, then GET by address."""
        from src.infra.models import UserModel
        from sqlalchemy import select

        token, user_id = await _register_and_get_token(client, _FREELANCER_PAYLOAD)

        # set a wallet address on the user directly in db
        result = await db_session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.scalar_one()
        user.wallet_address = "11111111111111111111111111111111"
        db_session.add(user)
        await db_session.commit()

        resp = await client.get("/v1/users/11111111111111111111111111111111/profile")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == user_id
        assert data["wallet_address"] == "11111111111111111111111111111111"
        assert data["name"] == "Alice Profile"
        assert data["role"] == "USER_ROLE_FREELANCER"

    @pytest.mark.asyncio
    async def test_unknown_address_returns_404(self, client: AsyncClient):
        resp = await client.get("/v1/users/UnknownAddressXXXXXXXXXXXXXXXXXXXX/profile")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "USER_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_public_access_no_auth_needed(self, client: AsyncClient):
        """GET profile endpoint should not require auth."""
        resp = await client.get("/v1/users/SomeNonExistentAddr1234567890123/profile")
        # should get 404, not 401
        assert resp.status_code == 404
