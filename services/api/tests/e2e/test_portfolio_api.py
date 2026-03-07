"""
E2E tests for portfolio endpoints.

Runs against in-memory SQLite via conftest.py fixture.
S3 calls are patched to avoid real AWS interactions.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_FREELANCER_PAYLOAD = {
    "email": "freelancer@portfolio.example.com",
    "password": "strongPass1",
    "name": "Alice Freelancer",
    "role": "USER_ROLE_FREELANCER",
}

_CLIENT_PAYLOAD = {
    "email": "client@portfolio.example.com",
    "password": "strongPass1",
    "name": "Bob Client",
    "role": "USER_ROLE_CLIENT",
}

_FREELANCER_2_PAYLOAD = {
    "email": "freelancer2@portfolio.example.com",
    "password": "strongPass1",
    "name": "Carol Freelancer",
    "role": "USER_ROLE_FREELANCER",
}


async def _register_and_get_token(client: AsyncClient, payload: dict) -> str:
    resp = await client.post("/v1/auth/email/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _valid_item_payload(**overrides) -> dict:
    base = {
        "title": "My E-commerce Platform",
        "description": "Built with FastAPI and React",
        "file_keys": ["portfolio/screenshot.png"],
        "external_url": "https://github.com/example/project",
        "tags": ["python", "react"],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# POST /v1/portfolio
# ---------------------------------------------------------------------------


class TestCreatePortfolioItem:
    @pytest.mark.asyncio
    async def test_freelancer_can_create_item(self, client: AsyncClient):
        token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        resp = await client.post(
            "/v1/portfolio", json=_valid_item_payload(), headers=_auth_headers(token)
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "My E-commerce Platform"
        assert data["is_verified"] is False
        assert data["verified_gig_id"] is None

    @pytest.mark.asyncio
    async def test_client_cannot_create_item(self, client: AsyncClient):
        token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        resp = await client.post(
            "/v1/portfolio", json=_valid_item_payload(), headers=_auth_headers(token)
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_create_item(self, client: AsyncClient):
        resp = await client.post("/v1/portfolio", json=_valid_item_payload())
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_create_returns_file_keys_and_tags(self, client: AsyncClient):
        token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        payload = _valid_item_payload(file_keys=["portfolio/a.pdf", "portfolio/b.png"])
        resp = await client.post(
            "/v1/portfolio", json=payload, headers=_auth_headers(token)
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["file_keys"] == ["portfolio/a.pdf", "portfolio/b.png"]
        assert data["tags"] == ["python", "react"]

    @pytest.mark.asyncio
    async def test_unknown_verified_gig_id_returns_404(self, client: AsyncClient):
        token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        payload = _valid_item_payload(
            verified_gig_id="00000000-0000-0000-0000-000000000000"
        )
        resp = await client.post(
            "/v1/portfolio", json=payload, headers=_auth_headers(token)
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "GIG_NOT_FOUND"


# ---------------------------------------------------------------------------
# GET /v1/portfolio/{user_id}
# ---------------------------------------------------------------------------


class TestGetPortfolioItems:
    @pytest.mark.asyncio
    async def test_public_access_no_auth_needed(self, client: AsyncClient):
        token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        create_resp = await client.post(
            "/v1/portfolio", json=_valid_item_payload(), headers=_auth_headers(token)
        )
        user_id = create_resp.json()["user_id"]

        # Access without auth header
        resp = await client.get(f"/v1/portfolio/{user_id}")
        assert resp.status_code == 200
        assert "items" in resp.json()

    @pytest.mark.asyncio
    async def test_returns_items_for_user(self, client: AsyncClient):
        token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        create_resp = await client.post(
            "/v1/portfolio", json=_valid_item_payload(), headers=_auth_headers(token)
        )
        user_id = create_resp.json()["user_id"]

        resp = await client.get(f"/v1/portfolio/{user_id}")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) >= 1
        assert items[0]["title"] == "My E-commerce Platform"

    @pytest.mark.asyncio
    async def test_unknown_user_returns_empty_list(self, client: AsyncClient):
        resp = await client.get("/v1/portfolio/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    @pytest.mark.asyncio
    async def test_items_include_is_verified_field(self, client: AsyncClient):
        token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        create_resp = await client.post(
            "/v1/portfolio", json=_valid_item_payload(), headers=_auth_headers(token)
        )
        user_id = create_resp.json()["user_id"]

        resp = await client.get(f"/v1/portfolio/{user_id}")
        item = resp.json()["items"][0]
        assert "is_verified" in item
        assert item["is_verified"] is False

    @pytest.mark.asyncio
    async def test_does_not_return_other_users_items(self, client: AsyncClient):
        token1 = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        token2 = await _register_and_get_token(client, _FREELANCER_2_PAYLOAD)

        cr1 = await client.post(
            "/v1/portfolio",
            json=_valid_item_payload(title="User1 Item"),
            headers=_auth_headers(token1),
        )
        user1_id = cr1.json()["user_id"]

        cr2 = await client.post(
            "/v1/portfolio",
            json=_valid_item_payload(title="User2 Item"),
            headers=_auth_headers(token2),
        )
        user2_id = cr2.json()["user_id"]

        resp = await client.get(f"/v1/portfolio/{user1_id}")
        titles = [i["title"] for i in resp.json()["items"]]
        assert "User1 Item" in titles
        assert "User2 Item" not in titles

        resp2 = await client.get(f"/v1/portfolio/{user2_id}")
        titles2 = [i["title"] for i in resp2.json()["items"]]
        assert "User2 Item" in titles2
        assert "User1 Item" not in titles2


# ---------------------------------------------------------------------------
# PUT /v1/portfolio/{item_id}
# ---------------------------------------------------------------------------


class TestUpdatePortfolioItem:
    @pytest.mark.asyncio
    async def test_owner_can_update_item(self, client: AsyncClient):
        token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        cr = await client.post(
            "/v1/portfolio", json=_valid_item_payload(), headers=_auth_headers(token)
        )
        item_id = cr.json()["id"]

        resp = await client.put(
            f"/v1/portfolio/{item_id}",
            json={"title": "Updated Title"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_non_owner_cannot_update(self, client: AsyncClient):
        token1 = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        token2 = await _register_and_get_token(client, _FREELANCER_2_PAYLOAD)
        cr = await client.post(
            "/v1/portfolio", json=_valid_item_payload(), headers=_auth_headers(token1)
        )
        item_id = cr.json()["id"]

        resp = await client.put(
            f"/v1/portfolio/{item_id}",
            json={"title": "Hijacked"},
            headers=_auth_headers(token2),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_unauthenticated_update_returns_401(self, client: AsyncClient):
        token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        cr = await client.post(
            "/v1/portfolio", json=_valid_item_payload(), headers=_auth_headers(token)
        )
        item_id = cr.json()["id"]

        resp = await client.put(f"/v1/portfolio/{item_id}", json={"title": "x"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_update_not_found_returns_404(self, client: AsyncClient):
        token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        resp = await client.put(
            "/v1/portfolio/00000000-0000-0000-0000-000000000000",
            json={"title": "x"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /v1/portfolio/{item_id}
# ---------------------------------------------------------------------------


class TestDeletePortfolioItem:
    @pytest.mark.asyncio
    async def test_owner_can_delete_item(self, client: AsyncClient):
        token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        cr = await client.post(
            "/v1/portfolio", json=_valid_item_payload(), headers=_auth_headers(token)
        )
        item_id = cr.json()["id"]
        user_id = cr.json()["user_id"]

        resp = await client.delete(
            f"/v1/portfolio/{item_id}", headers=_auth_headers(token)
        )
        assert resp.status_code == 204

        # Verify gone
        get_resp = await client.get(f"/v1/portfolio/{user_id}")
        assert get_resp.json()["items"] == []

    @pytest.mark.asyncio
    async def test_non_owner_cannot_delete(self, client: AsyncClient):
        token1 = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        token2 = await _register_and_get_token(client, _FREELANCER_2_PAYLOAD)
        cr = await client.post(
            "/v1/portfolio", json=_valid_item_payload(), headers=_auth_headers(token1)
        )
        item_id = cr.json()["id"]

        resp = await client.delete(
            f"/v1/portfolio/{item_id}", headers=_auth_headers(token2)
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_delete_returns_401(self, client: AsyncClient):
        token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        cr = await client.post(
            "/v1/portfolio", json=_valid_item_payload(), headers=_auth_headers(token)
        )
        item_id = cr.json()["id"]

        resp = await client.delete(f"/v1/portfolio/{item_id}")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_not_found_returns_404(self, client: AsyncClient):
        token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        resp = await client.delete(
            "/v1/portfolio/00000000-0000-0000-0000-000000000000",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /v1/portfolio/upload-url
# ---------------------------------------------------------------------------


class TestUploadUrl:
    @pytest.mark.asyncio
    async def test_freelancer_gets_presigned_url(self, client: AsyncClient):
        token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        with patch(
            "src.api.portfolio.s3_infra.generate_portfolio_upload_url",
            return_value=("https://s3.example.com/presigned", "portfolio/fake-uuid"),
        ):
            resp = await client.post(
                "/v1/portfolio/upload-url",
                json={"content_type": "image/png"},
                headers=_auth_headers(token),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "https://s3.example.com/presigned"
        assert data["key"] == "portfolio/fake-uuid"

    @pytest.mark.asyncio
    async def test_unauthenticated_upload_url_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/v1/portfolio/upload-url", json={"content_type": "image/png"}
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_client_cannot_get_upload_url(self, client: AsyncClient):
        token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        resp = await client.post(
            "/v1/portfolio/upload-url",
            json={"content_type": "image/png"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_s3_failure_returns_503(self, client: AsyncClient):
        token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        with patch(
            "src.api.portfolio.s3_infra.generate_portfolio_upload_url",
            side_effect=RuntimeError("S3 unavailable"),
        ):
            resp = await client.post(
                "/v1/portfolio/upload-url",
                json={"content_type": "image/png"},
                headers=_auth_headers(token),
            )
        assert resp.status_code == 503
        assert resp.json()["detail"]["code"] == "S3_UNAVAILABLE"
