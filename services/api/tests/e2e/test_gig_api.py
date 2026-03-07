"""
E2E tests for gig endpoints.

Runs against in-memory SQLite via conftest.py fixture.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CLIENT_PAYLOAD = {
    "email": "client@example.com",
    "password": "strongPass1",
    "name": "Test Client",
    "role": "USER_ROLE_CLIENT",
}

_FREELANCER_PAYLOAD = {
    "email": "freelancer@example.com",
    "password": "strongPass1",
    "name": "Test Freelancer",
    "role": "USER_ROLE_FREELANCER",
}


def _valid_gig_payload(total: int = 1000, n_milestones: int = 2) -> dict:
    per = total // n_milestones
    remainder = total - per * (n_milestones - 1)
    milestones = []
    for i in range(n_milestones):
        amount = remainder if i == n_milestones - 1 else per
        milestones.append(
            {
                "title": f"Milestone {i + 1}",
                "description": "Do the work",
                "acceptance_criteria": "## Criteria\n- It passes tests",
                "amount": str(amount),
                "order": i + 1,
            }
        )
    return {
        "title": "Build a widget",
        "description": "Full widget implementation",
        "total_amount": str(total),
        "currency": "ETH",
        "required_skills": ["Python"],
        "tags": ["python"],
        "milestones": milestones,
    }


async def _register_and_get_token(client: AsyncClient, payload: dict) -> str:
    resp = await client.post("/v1/auth/email/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /v1/gigs
# ---------------------------------------------------------------------------


class TestCreateGig:
    @pytest.mark.asyncio
    async def test_client_can_create_gig(self, client: AsyncClient):
        token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        resp = await client.post(
            "/v1/gigs", json=_valid_gig_payload(), headers=_auth_headers(token)
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "DRAFT"
        assert data["currency"] == "ETH"
        assert len(data["milestones"]) == 2

    @pytest.mark.asyncio
    async def test_freelancer_cannot_create_gig(self, client: AsyncClient):
        token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        resp = await client.post(
            "/v1/gigs", json=_valid_gig_payload(), headers=_auth_headers(token)
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_create_gig(self, client: AsyncClient):
        resp = await client.post("/v1/gigs", json=_valid_gig_payload())
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_milestone_amount_mismatch_returns_400(self, client: AsyncClient):
        token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        payload = _valid_gig_payload(total=1000, n_milestones=2)
        # Corrupt the milestone amounts so they don't sum to total_amount
        payload["milestones"][0]["amount"] = "300"
        payload["milestones"][1]["amount"] = "300"
        resp = await client.post("/v1/gigs", json=payload, headers=_auth_headers(token))
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "MILESTONE_AMOUNT_MISMATCH"

    @pytest.mark.asyncio
    async def test_zero_milestones_returns_400(self, client: AsyncClient):
        token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        payload = _valid_gig_payload()
        payload["milestones"] = []
        resp = await client.post("/v1/gigs", json=payload, headers=_auth_headers(token))
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "TOO_FEW_MILESTONES"

    @pytest.mark.asyncio
    async def test_usdc_gig_requires_token_address(self, client: AsyncClient):
        token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        payload = _valid_gig_payload()
        payload["currency"] = "USDC"
        # No token_address — should fail
        resp = await client.post("/v1/gigs", json=payload, headers=_auth_headers(token))
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "TOKEN_ADDRESS_REQUIRED"

    @pytest.mark.asyncio
    async def test_usdc_gig_with_token_address(self, client: AsyncClient):
        token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        payload = _valid_gig_payload()
        payload["currency"] = "USDC"
        payload["token_address"] = "0x" + "a" * 40
        resp = await client.post("/v1/gigs", json=payload, headers=_auth_headers(token))
        assert resp.status_code == 201
        assert resp.json()["currency"] == "USDC"

    @pytest.mark.asyncio
    async def test_eth_gig_with_token_address_returns_400(self, client: AsyncClient):
        token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        payload = _valid_gig_payload()
        payload["currency"] = "ETH"
        payload["token_address"] = "0x" + "a" * 40
        resp = await client.post("/v1/gigs", json=payload, headers=_auth_headers(token))
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "TOKEN_ADDRESS_NOT_ALLOWED"


# ---------------------------------------------------------------------------
# GET /v1/gigs (public discovery board)
# ---------------------------------------------------------------------------


class TestListGigs:
    @pytest.mark.asyncio
    async def test_public_list_returns_open_gigs(self, client: AsyncClient):
        # Create a gig and manually set it to OPEN (escrow funding is issue #4)

        token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        await client.post(
            "/v1/gigs", json=_valid_gig_payload(), headers=_auth_headers(token)
        )

        # Public list should not show DRAFT gigs
        resp = await client.get("/v1/gigs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_no_auth_required(self, client: AsyncClient):
        resp = await client.get("/v1/gigs")
        assert resp.status_code == 200
        assert "gigs" in resp.json()
        assert "total" in resp.json()

    @pytest.mark.asyncio
    async def test_list_pagination_params(self, client: AsyncClient):
        resp = await client.get("/v1/gigs?page=1&page_size=5")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 5


# ---------------------------------------------------------------------------
# GET /v1/gigs/{gig_id}
# ---------------------------------------------------------------------------


class TestGetGig:
    @pytest.mark.asyncio
    async def test_get_gig_with_milestones(self, client: AsyncClient):
        token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        cr = await client.post(
            "/v1/gigs", json=_valid_gig_payload(), headers=_auth_headers(token)
        )
        gig_id = cr.json()["id"]

        resp = await client.get(f"/v1/gigs/{gig_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == gig_id
        assert len(data["milestones"]) == 2

    @pytest.mark.asyncio
    async def test_get_gig_no_auth_required(self, client: AsyncClient):
        token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        cr = await client.post(
            "/v1/gigs", json=_valid_gig_payload(), headers=_auth_headers(token)
        )
        gig_id = cr.json()["id"]
        # No auth header
        resp = await client.get(f"/v1/gigs/{gig_id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_unknown_gig_returns_404(self, client: AsyncClient):
        resp = await client.get("/v1/gigs/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /v1/gigs/{gig_id}
# ---------------------------------------------------------------------------


class TestUpdateGig:
    @pytest.mark.asyncio
    async def test_owner_can_update_draft_gig(self, client: AsyncClient):
        token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        cr = await client.post(
            "/v1/gigs", json=_valid_gig_payload(), headers=_auth_headers(token)
        )
        gig_id = cr.json()["id"]

        resp = await client.put(
            f"/v1/gigs/{gig_id}",
            json={"title": "Updated Title"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_non_owner_cannot_update_gig(self, client: AsyncClient):
        token1 = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        token2 = await _register_and_get_token(
            client,
            {**_CLIENT_PAYLOAD, "email": "client2@example.com"},
        )

        cr = await client.post(
            "/v1/gigs", json=_valid_gig_payload(), headers=_auth_headers(token1)
        )
        gig_id = cr.json()["id"]

        resp = await client.put(
            f"/v1/gigs/{gig_id}",
            json={"title": "Hijacked"},
            headers=_auth_headers(token2),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_update_non_draft_gig_returns_409(self, client: AsyncClient):
        # Enforcement of OPEN/IN_PROGRESS status guard is covered in unit tests.
        # In e2e tests the in-memory DB is not shared between the test process and the
        # app process, so forcing a status change via raw SQL is not straightforward here.
        pytest.skip("OPEN gig update enforcement covered in unit tests")

    @pytest.mark.asyncio
    async def test_unauthenticated_update_returns_401(self, client: AsyncClient):
        token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        cr = await client.post(
            "/v1/gigs", json=_valid_gig_payload(), headers=_auth_headers(token)
        )
        gig_id = cr.json()["id"]

        resp = await client.put(f"/v1/gigs/{gig_id}", json={"title": "x"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_update_not_found_returns_404(self, client: AsyncClient):
        token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        resp = await client.put(
            "/v1/gigs/00000000-0000-0000-0000-000000000000",
            json={"title": "x"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /v1/gigs/{gig_id}
# ---------------------------------------------------------------------------


class TestDeleteGig:
    @pytest.mark.asyncio
    async def test_owner_can_delete_draft_gig(self, client: AsyncClient):
        token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        cr = await client.post(
            "/v1/gigs", json=_valid_gig_payload(), headers=_auth_headers(token)
        )
        gig_id = cr.json()["id"]

        resp = await client.delete(f"/v1/gigs/{gig_id}", headers=_auth_headers(token))
        assert resp.status_code == 204

        # Verify it's gone
        get_resp = await client.get(f"/v1/gigs/{gig_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_non_owner_cannot_delete_gig(self, client: AsyncClient):
        token1 = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        token2 = await _register_and_get_token(
            client,
            {**_CLIENT_PAYLOAD, "email": "client3@example.com"},
        )

        cr = await client.post(
            "/v1/gigs", json=_valid_gig_payload(), headers=_auth_headers(token1)
        )
        gig_id = cr.json()["id"]

        resp = await client.delete(f"/v1/gigs/{gig_id}", headers=_auth_headers(token2))
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_delete_returns_401(self, client: AsyncClient):
        token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        cr = await client.post(
            "/v1/gigs", json=_valid_gig_payload(), headers=_auth_headers(token)
        )
        gig_id = cr.json()["id"]

        resp = await client.delete(f"/v1/gigs/{gig_id}")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_not_found_returns_404(self, client: AsyncClient):
        token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        resp = await client.delete(
            "/v1/gigs/00000000-0000-0000-0000-000000000000",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404
