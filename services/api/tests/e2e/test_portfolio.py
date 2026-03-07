"""
E2E tests for portfolio endpoints.

Runs against in-memory SQLite via conftest.py fixtures.

Endpoints tested:
  POST   /v1/portfolio
  GET    /v1/portfolio/{item_id}
  PUT    /v1/portfolio/{item_id}
  DELETE /v1/portfolio/{item_id}
  GET    /v1/users/{user_id}/portfolio
  POST   /v1/portfolio/upload-url
"""

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(
    client: AsyncClient, email: str, name: str
) -> tuple[str, str]:
    """Register a user and return (token, user_id)."""
    resp = await client.post(
        "/v1/auth/email/register",
        json={"email": email, "password": "strongPass1", "name": name},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return data["access_token"], data["user_id"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /v1/portfolio
# ---------------------------------------------------------------------------


class TestCreatePortfolioItem:
    @pytest.mark.asyncio
    async def test_happy_path_creates_item(self, client: AsyncClient):
        token, user_id = await _register_and_login(client, "alice@example.com", "Alice")
        resp = await client.post(
            "/v1/portfolio",
            json={
                "title": "My Portfolio Item",
                "description": "A great project",
                "tags": ["python", "fastapi"],
            },
            headers=_auth_headers(token),
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["title"] == "My Portfolio Item"
        assert data["description"] == "A great project"
        assert data["tags"] == ["python", "fastapi"]
        assert data["user_id"] == user_id
        assert data["is_verified"] is False
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/v1/portfolio",
            json={"title": "Unauthorized"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_title_is_required(self, client: AsyncClient):
        token, _ = await _register_and_login(client, "bob@example.com", "Bob")
        resp = await client.post(
            "/v1/portfolio",
            json={"description": "Missing title"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_defaults_empty_lists(self, client: AsyncClient):
        token, _ = await _register_and_login(client, "carol@example.com", "Carol")
        resp = await client.post(
            "/v1/portfolio",
            json={"title": "Minimal item"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["file_keys"] == []
        assert data["tags"] == []
        assert data["external_url"] is None
        assert data["verified_gig_id"] is None

    @pytest.mark.asyncio
    async def test_with_external_url_and_file_keys(self, client: AsyncClient):
        token, _ = await _register_and_login(client, "dan@example.com", "Dan")
        resp = await client.post(
            "/v1/portfolio",
            json={
                "title": "Full item",
                "external_url": "https://github.com/dan/project",
                "file_keys": ["portfolio/abc/uuid-screenshot.png"],
            },
            headers=_auth_headers(token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["external_url"] == "https://github.com/dan/project"
        assert data["file_keys"] == ["portfolio/abc/uuid-screenshot.png"]


# ---------------------------------------------------------------------------
# GET /v1/portfolio/{item_id}
# ---------------------------------------------------------------------------


class TestGetPortfolioItem:
    @pytest.mark.asyncio
    async def test_happy_path_returns_item(self, client: AsyncClient):
        token, _ = await _register_and_login(client, "eve@example.com", "Eve")
        # Create item
        cr = await client.post(
            "/v1/portfolio",
            json={"title": "Eve's project"},
            headers=_auth_headers(token),
        )
        item_id = cr.json()["id"]

        resp = await client.get(
            f"/v1/portfolio/{item_id}",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == item_id

    @pytest.mark.asyncio
    async def test_not_found_returns_404(self, client: AsyncClient):
        token, _ = await _register_and_login(client, "frank@example.com", "Frank")
        resp = await client.get(
            "/v1/portfolio/nonexistent-id-12345",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/v1/portfolio/some-id")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /v1/portfolio/{item_id}
# ---------------------------------------------------------------------------


class TestUpdatePortfolioItem:
    @pytest.mark.asyncio
    async def test_owner_can_update(self, client: AsyncClient):
        token, _ = await _register_and_login(client, "grace@example.com", "Grace")
        cr = await client.post(
            "/v1/portfolio",
            json={"title": "Original title"},
            headers=_auth_headers(token),
        )
        item_id = cr.json()["id"]

        resp = await client.put(
            f"/v1/portfolio/{item_id}",
            json={"title": "Updated title", "tags": ["updated"]},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Updated title"
        assert data["tags"] == ["updated"]

    @pytest.mark.asyncio
    async def test_non_owner_gets_403(self, client: AsyncClient):
        token_a, _ = await _register_and_login(client, "henry@example.com", "Henry")
        token_b, _ = await _register_and_login(client, "iris@example.com", "Iris")

        # Henry creates an item
        cr = await client.post(
            "/v1/portfolio",
            json={"title": "Henry's item"},
            headers=_auth_headers(token_a),
        )
        item_id = cr.json()["id"]

        # Iris tries to update it
        resp = await client.put(
            f"/v1/portfolio/{item_id}",
            json={"title": "Iris's takeover"},
            headers=_auth_headers(token_b),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_not_found_returns_404(self, client: AsyncClient):
        token, _ = await _register_and_login(client, "jack@example.com", "Jack")
        resp = await client.put(
            "/v1/portfolio/nonexistent-id",
            json={"title": "Ghost"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_partial_update_preserves_other_fields(self, client: AsyncClient):
        token, _ = await _register_and_login(client, "kate@example.com", "Kate")
        cr = await client.post(
            "/v1/portfolio",
            json={
                "title": "Kate's project",
                "description": "Original description",
                "tags": ["original"],
            },
            headers=_auth_headers(token),
        )
        item_id = cr.json()["id"]

        # Only update title
        resp = await client.put(
            f"/v1/portfolio/{item_id}",
            json={"title": "New title"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "New title"
        # description unchanged (None sent = no update)
        assert data["description"] == "Original description"


# ---------------------------------------------------------------------------
# DELETE /v1/portfolio/{item_id}
# ---------------------------------------------------------------------------


class TestDeletePortfolioItem:
    @pytest.mark.asyncio
    async def test_owner_can_delete(self, client: AsyncClient):
        token, _ = await _register_and_login(client, "liam@example.com", "Liam")
        cr = await client.post(
            "/v1/portfolio",
            json={"title": "To be deleted"},
            headers=_auth_headers(token),
        )
        item_id = cr.json()["id"]

        resp = await client.delete(
            f"/v1/portfolio/{item_id}",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 204

        # Verify gone
        get_resp = await client.get(
            f"/v1/portfolio/{item_id}",
            headers=_auth_headers(token),
        )
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_non_owner_gets_403(self, client: AsyncClient):
        token_a, _ = await _register_and_login(client, "mia@example.com", "Mia")
        token_b, _ = await _register_and_login(client, "noah@example.com", "Noah")

        cr = await client.post(
            "/v1/portfolio",
            json={"title": "Mia's item"},
            headers=_auth_headers(token_a),
        )
        item_id = cr.json()["id"]

        resp = await client.delete(
            f"/v1/portfolio/{item_id}",
            headers=_auth_headers(token_b),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_not_found_returns_404(self, client: AsyncClient):
        token, _ = await _register_and_login(client, "olivia@example.com", "Olivia")
        resp = await client.delete(
            "/v1/portfolio/nonexistent-id",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /v1/users/{user_id}/portfolio
# ---------------------------------------------------------------------------


class TestGetUserPortfolio:
    @pytest.mark.asyncio
    async def test_returns_items_for_user(self, client: AsyncClient):
        token, user_id = await _register_and_login(client, "pete@example.com", "Pete")

        # Create two items
        await client.post(
            "/v1/portfolio",
            json={"title": "Item A"},
            headers=_auth_headers(token),
        )
        await client.post(
            "/v1/portfolio",
            json={"title": "Item B"},
            headers=_auth_headers(token),
        )

        resp = await client.get(
            f"/v1/users/{user_id}/portfolio",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_items_ordered_by_created_at_desc(self, client: AsyncClient):
        """
        Verify that the endpoint returns items ordered by created_at DESC.
        In SQLite in-memory tests two items created in quick succession may share
        the same timestamp, so we check that both items are returned and that
        the created_at values are in non-ascending order (DESC or equal).
        """
        token, user_id = await _register_and_login(client, "quinn@example.com", "Quinn")

        await client.post(
            "/v1/portfolio",
            json={"title": "First"},
            headers=_auth_headers(token),
        )
        await client.post(
            "/v1/portfolio",
            json={"title": "Second"},
            headers=_auth_headers(token),
        )

        resp = await client.get(
            f"/v1/users/{user_id}/portfolio",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 2
        titles = {item["title"] for item in items}
        assert titles == {"First", "Second"}
        # created_at values should be in non-ascending (DESC or equal) order
        assert items[0]["created_at"] >= items[1]["created_at"]

    @pytest.mark.asyncio
    async def test_returns_empty_list_for_user_with_no_items(self, client: AsyncClient):
        token, user_id = await _register_and_login(client, "rose@example.com", "Rose")
        resp = await client.get(
            f"/v1/users/{user_id}/portfolio",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    @pytest.mark.asyncio
    async def test_does_not_return_other_users_items(self, client: AsyncClient):
        token_a, user_id_a = await _register_and_login(client, "sam@example.com", "Sam")
        token_b, user_id_b = await _register_and_login(
            client, "tina@example.com", "Tina"
        )

        await client.post(
            "/v1/portfolio",
            json={"title": "Sam's item"},
            headers=_auth_headers(token_a),
        )

        resp = await client.get(
            f"/v1/users/{user_id_b}/portfolio",
            headers=_auth_headers(token_b),
        )
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/v1/users/some-user-id/portfolio")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /v1/portfolio/upload-url
# ---------------------------------------------------------------------------


class TestGetPresignedUrl:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/v1/portfolio/upload-url",
            json={"filename": "photo.png", "content_type": "image/png"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_returns_s3_key_on_success_or_503_when_no_credentials(
        self, client: AsyncClient
    ):
        """
        In test environment AWS credentials are not set.
        The endpoint should either return a presigned URL (if mock S3 is available)
        or return 503 SERVICE_UNAVAILABLE with code S3_UNAVAILABLE.
        Both are acceptable in CI without real AWS credentials.
        """
        token, _ = await _register_and_login(client, "uma@example.com", "Uma")
        resp = await client.post(
            "/v1/portfolio/upload-url",
            json={"filename": "screenshot.png", "content_type": "image/png"},
            headers=_auth_headers(token),
        )
        # Without AWS credentials: 503 is expected in test env
        assert resp.status_code in (200, 503)
        if resp.status_code == 200:
            data = resp.json()
            assert "upload_url" in data
            assert "s3_key" in data
            assert "screenshot.png" in data["s3_key"]
        else:
            assert resp.json()["detail"]["code"] == "S3_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_missing_filename_returns_422(self, client: AsyncClient):
        token, _ = await _register_and_login(client, "vera@example.com", "Vera")
        resp = await client.post(
            "/v1/portfolio/upload-url",
            json={"content_type": "image/png"},  # missing filename
            headers=_auth_headers(token),
        )
        assert resp.status_code == 422
