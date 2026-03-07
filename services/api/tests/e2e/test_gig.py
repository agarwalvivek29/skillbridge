"""
E2E tests for gig CRUD endpoints.
Runs against in-memory SQLite via conftest.py fixtures.
"""

import pytest
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REGISTER_URL = "/v1/auth/email/register"
_LOGIN_URL = "/v1/auth/email/login"
_GIGS_URL = "/v1/gigs"


async def _register_client(
    client: AsyncClient, email: str, password: str = "strongPass1"
) -> str:
    """Register a CLIENT user and return the JWT."""
    resp = await client.post(
        _REGISTER_URL,
        json={
            "email": email,
            "password": password,
            "name": "Test Client",
            "role": "USER_ROLE_CLIENT",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


async def _register_freelancer(
    client: AsyncClient, email: str, password: str = "strongPass1"
) -> str:
    """Register a FREELANCER user and return the JWT."""
    resp = await client.post(
        _REGISTER_URL,
        json={
            "email": email,
            "password": password,
            "name": "Test Freelancer",
            "role": "USER_ROLE_FREELANCER",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _sample_gig_body(
    total_amount: str = "1000", milestones: list | None = None
) -> dict:
    if milestones is None:
        milestones = [
            {
                "title": "Milestone 1",
                "description": "First milestone",
                "acceptance_criteria": "## Criteria\n- Feature X works",
                "amount": "600",
                "order": 1,
            },
            {
                "title": "Milestone 2",
                "description": "Second milestone",
                "acceptance_criteria": "## Criteria\n- Feature Y works",
                "amount": "400",
                "order": 2,
            },
        ]
    return {
        "title": "Build a REST API",
        "description": "I need a Python FastAPI service",
        "total_amount": total_amount,
        "currency": "CURRENCY_ETH",
        "token_address": "",
        "tags": ["python", "fastapi"],
        "required_skills": ["Python", "FastAPI"],
        "milestones": milestones,
    }


# ---------------------------------------------------------------------------
# POST /v1/gigs
# ---------------------------------------------------------------------------


class TestCreateGig:
    @pytest.mark.asyncio
    async def test_happy_path_creates_gig_with_milestones(
        self, client: AsyncClient
    ) -> None:
        token = await _register_client(client, "create_gig@test.com")
        body = _sample_gig_body()
        resp = await client.post(_GIGS_URL, json=body, headers=_auth_headers(token))
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["title"] == "Build a REST API"
        assert data["status"] == "GIG_STATUS_DRAFT"
        assert data["currency"] == "CURRENCY_ETH"
        assert len(data["milestones"]) == 2
        assert data["milestones"][0]["order"] == 1
        assert data["milestones"][1]["order"] == 2
        assert data["milestones"][0]["status"] == "MILESTONE_STATUS_PENDING"

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient) -> None:
        resp = await client.post(_GIGS_URL, json=_sample_gig_body())
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_milestone_sum_mismatch_returns_422(
        self, client: AsyncClient
    ) -> None:
        token = await _register_client(client, "sum_mismatch@test.com")
        body = _sample_gig_body(
            total_amount="1000",
            milestones=[
                {
                    "title": "M1",
                    "description": "desc",
                    "acceptance_criteria": "criteria",
                    "amount": "400",
                    "order": 1,
                },
                {
                    "title": "M2",
                    "description": "desc",
                    "acceptance_criteria": "criteria",
                    "amount": "400",  # 400+400=800 != 1000
                    "order": 2,
                },
            ],
        )
        resp = await client.post(_GIGS_URL, json=body, headers=_auth_headers(token))
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "MILESTONE_SUM_MISMATCH"

    @pytest.mark.asyncio
    async def test_too_many_milestones_returns_422(self, client: AsyncClient) -> None:
        token = await _register_client(client, "too_many@test.com")
        # 11 milestones each with amount 10, total 110
        milestones = [
            {
                "title": f"M{i}",
                "description": "desc",
                "acceptance_criteria": "criteria",
                "amount": "10",
                "order": i,
            }
            for i in range(1, 12)
        ]
        body = _sample_gig_body(total_amount="110", milestones=milestones)
        resp = await client.post(_GIGS_URL, json=body, headers=_auth_headers(token))
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_usdc_without_token_address_returns_422(
        self, client: AsyncClient
    ) -> None:
        token = await _register_client(client, "usdc_no_token@test.com")
        body = _sample_gig_body()
        body["currency"] = "CURRENCY_USDC"
        body["token_address"] = ""
        resp = await client.post(_GIGS_URL, json=body, headers=_auth_headers(token))
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "MISSING_TOKEN_ADDRESS"

    @pytest.mark.asyncio
    async def test_usdc_with_token_address_creates_gig(
        self, client: AsyncClient
    ) -> None:
        token = await _register_client(client, "usdc_with_token@test.com")
        body = _sample_gig_body()
        body["currency"] = "CURRENCY_USDC"
        body["token_address"] = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        resp = await client.post(_GIGS_URL, json=body, headers=_auth_headers(token))
        assert resp.status_code == 201
        assert resp.json()["currency"] == "CURRENCY_USDC"
        assert (
            resp.json()["token_address"] == "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        )

    @pytest.mark.asyncio
    async def test_single_milestone_equal_to_total(self, client: AsyncClient) -> None:
        token = await _register_client(client, "single_ms@test.com")
        body = _sample_gig_body(
            total_amount="500",
            milestones=[
                {
                    "title": "Only milestone",
                    "description": "desc",
                    "acceptance_criteria": "criteria",
                    "amount": "500",
                    "order": 1,
                }
            ],
        )
        resp = await client.post(_GIGS_URL, json=body, headers=_auth_headers(token))
        assert resp.status_code == 201
        assert len(resp.json()["milestones"]) == 1


# ---------------------------------------------------------------------------
# GET /v1/gigs (discovery board)
# ---------------------------------------------------------------------------


class TestListGigs:
    @pytest.mark.asyncio
    async def test_draft_gig_not_in_discovery_board(self, client: AsyncClient) -> None:
        token = await _register_client(client, "list_draft@test.com")
        # Create a DRAFT gig
        await client.post(
            _GIGS_URL, json=_sample_gig_body(), headers=_auth_headers(token)
        )
        # Discovery board should not include DRAFT gigs
        resp = await client.get(_GIGS_URL, headers=_auth_headers(token))
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["gigs"] == []

    @pytest.mark.asyncio
    async def test_unauthenticated_list_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get(_GIGS_URL)
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_pagination_fields_present(self, client: AsyncClient) -> None:
        token = await _register_client(client, "paginate@test.com")
        resp = await client.get(_GIGS_URL, headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "page" in data
        assert "page_size" in data
        assert "total" in data
        assert "gigs" in data


# ---------------------------------------------------------------------------
# GET /v1/gigs/{gig_id}
# ---------------------------------------------------------------------------


class TestGetGig:
    @pytest.mark.asyncio
    async def test_owner_can_read_draft_gig(self, client: AsyncClient) -> None:
        token = await _register_client(client, "get_draft@test.com")
        create_resp = await client.post(
            _GIGS_URL, json=_sample_gig_body(), headers=_auth_headers(token)
        )
        gig_id = create_resp.json()["id"]

        resp = await client.get(f"{_GIGS_URL}/{gig_id}", headers=_auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == gig_id
        assert len(data["milestones"]) == 2

    @pytest.mark.asyncio
    async def test_nonexistent_gig_returns_404(self, client: AsyncClient) -> None:
        token = await _register_client(client, "get_404@test.com")
        resp = await client.get(
            f"{_GIGS_URL}/00000000-0000-0000-0000-000000000000",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "GIG_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_unauthenticated_get_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get(f"{_GIGS_URL}/some-id")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# PUT /v1/gigs/{gig_id}
# ---------------------------------------------------------------------------


class TestUpdateGig:
    @pytest.mark.asyncio
    async def test_owner_can_update_draft_gig(self, client: AsyncClient) -> None:
        token = await _register_client(client, "update_draft@test.com")
        create_resp = await client.post(
            _GIGS_URL, json=_sample_gig_body(), headers=_auth_headers(token)
        )
        gig_id = create_resp.json()["id"]

        resp = await client.put(
            f"{_GIGS_URL}/{gig_id}",
            json={"title": "Updated Title"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"
        assert resp.json()["status"] == "GIG_STATUS_DRAFT"

    @pytest.mark.asyncio
    async def test_non_owner_update_returns_403(self, client: AsyncClient) -> None:
        owner_token = await _register_client(client, "owner_update@test.com")
        other_token = await _register_client(client, "other_update@test.com")

        create_resp = await client.post(
            _GIGS_URL, json=_sample_gig_body(), headers=_auth_headers(owner_token)
        )
        gig_id = create_resp.json()["id"]

        resp = await client.put(
            f"{_GIGS_URL}/{gig_id}",
            json={"title": "Hacked Title"},
            headers=_auth_headers(other_token),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "NOT_GIG_OWNER"

    @pytest.mark.asyncio
    async def test_update_nonexistent_gig_returns_404(
        self, client: AsyncClient
    ) -> None:
        token = await _register_client(client, "update_404@test.com")
        resp = await client.put(
            f"{_GIGS_URL}/00000000-0000-0000-0000-000000000000",
            json={"title": "anything"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_milestones_with_sum_mismatch_returns_422(
        self, client: AsyncClient
    ) -> None:
        token = await _register_client(client, "update_sum@test.com")
        create_resp = await client.post(
            _GIGS_URL, json=_sample_gig_body(), headers=_auth_headers(token)
        )
        gig_id = create_resp.json()["id"]

        resp = await client.put(
            f"{_GIGS_URL}/{gig_id}",
            json={
                "milestones": [
                    {
                        "title": "M1",
                        "description": "d",
                        "acceptance_criteria": "c",
                        "amount": "300",  # 300 != 1000
                        "order": 1,
                    }
                ]
            },
            headers=_auth_headers(token),
        )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "MILESTONE_SUM_MISMATCH"

    @pytest.mark.asyncio
    async def test_update_replaces_milestones(self, client: AsyncClient) -> None:
        token = await _register_client(client, "replace_ms@test.com")
        create_resp = await client.post(
            _GIGS_URL, json=_sample_gig_body(), headers=_auth_headers(token)
        )
        gig_id = create_resp.json()["id"]
        assert len(create_resp.json()["milestones"]) == 2

        # Replace with single milestone
        resp = await client.put(
            f"{_GIGS_URL}/{gig_id}",
            json={
                "milestones": [
                    {
                        "title": "Only MS",
                        "description": "desc",
                        "acceptance_criteria": "crit",
                        "amount": "1000",
                        "order": 1,
                    }
                ]
            },
            headers=_auth_headers(token),
        )
        assert resp.status_code == 200
        assert len(resp.json()["milestones"]) == 1
        assert resp.json()["milestones"][0]["title"] == "Only MS"


# ---------------------------------------------------------------------------
# DELETE /v1/gigs/{gig_id}
# ---------------------------------------------------------------------------


class TestDeleteGig:
    @pytest.mark.asyncio
    async def test_owner_can_delete_draft_gig(self, client: AsyncClient) -> None:
        token = await _register_client(client, "delete_draft@test.com")
        create_resp = await client.post(
            _GIGS_URL, json=_sample_gig_body(), headers=_auth_headers(token)
        )
        gig_id = create_resp.json()["id"]

        resp = await client.delete(
            f"{_GIGS_URL}/{gig_id}", headers=_auth_headers(token)
        )
        assert resp.status_code == 204

        # Verify it's gone
        get_resp = await client.get(
            f"{_GIGS_URL}/{gig_id}", headers=_auth_headers(token)
        )
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_non_owner_delete_returns_403(self, client: AsyncClient) -> None:
        owner_token = await _register_client(client, "owner_del@test.com")
        other_token = await _register_client(client, "other_del@test.com")

        create_resp = await client.post(
            _GIGS_URL, json=_sample_gig_body(), headers=_auth_headers(owner_token)
        )
        gig_id = create_resp.json()["id"]

        resp = await client.delete(
            f"{_GIGS_URL}/{gig_id}", headers=_auth_headers(other_token)
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "NOT_GIG_OWNER"

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, client: AsyncClient) -> None:
        token = await _register_client(client, "delete_404@test.com")
        resp = await client.delete(
            f"{_GIGS_URL}/00000000-0000-0000-0000-000000000000",
            headers=_auth_headers(token),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthenticated_delete_returns_401(
        self, client: AsyncClient
    ) -> None:
        resp = await client.delete(f"{_GIGS_URL}/some-id")
        assert resp.status_code == 401
