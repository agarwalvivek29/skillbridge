"""
E2E tests for proposal endpoints and enhanced gig discovery filters.

Runs against in-memory SQLite via conftest.py fixture.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.models import GigModel

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

_FREELANCER_2_PAYLOAD = {
    "email": "freelancer2@example.com",
    "password": "strongPass1",
    "name": "Test Freelancer 2",
    "role": "USER_ROLE_FREELANCER",
}


def _valid_gig_payload() -> dict:
    return {
        "title": "Build a widget",
        "description": "Full widget implementation",
        "total_amount": "1000",
        "currency": "SOL",
        "required_skills": ["Python"],
        "tags": ["python"],
        "milestones": [
            {
                "title": "Only Milestone",
                "description": "Do the work",
                "acceptance_criteria": "It passes tests",
                "amount": "1000",
                "order": 1,
            }
        ],
    }


async def _register_and_get_token(client: AsyncClient, payload: dict) -> str:
    resp = await client.post("/v1/auth/email/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_open_gig(
    client: AsyncClient, db_session: AsyncSession, client_token: str
) -> str:
    """Create a gig and set it to OPEN status. Returns gig_id."""
    cr = await client.post(
        "/v1/gigs", json=_valid_gig_payload(), headers=_auth_headers(client_token)
    )
    assert cr.status_code == 201, cr.text
    gig_id = cr.json()["id"]
    # Force to OPEN (escrow funding is issue #4)
    await db_session.execute(
        sa_update(GigModel).where(GigModel.id == gig_id).values(status="OPEN")
    )
    await db_session.commit()
    return gig_id


# ---------------------------------------------------------------------------
# POST /v1/proposals
# ---------------------------------------------------------------------------


class TestCreateProposal:
    @pytest.mark.asyncio
    async def test_freelancer_can_submit_proposal(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        gig_id = await _create_open_gig(client, db_session, client_token)

        resp = await client.post(
            "/v1/proposals",
            json={"gig_id": gig_id, "cover_letter": "I'm great", "estimated_days": 7},
            headers=_auth_headers(freelancer_token),
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["status"] == "PENDING"
        assert data["gig_id"] == gig_id

    @pytest.mark.asyncio
    async def test_client_cannot_submit_proposal(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        gig_id = await _create_open_gig(client, db_session, client_token)

        resp = await client.post(
            "/v1/proposals",
            json={"gig_id": gig_id, "cover_letter": "I'm great", "estimated_days": 7},
            headers=_auth_headers(client_token),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/v1/proposals",
            json={
                "gig_id": "some-id",
                "cover_letter": "Hello",
                "estimated_days": 5,
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_draft_gig_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)

        cr = await client.post(
            "/v1/gigs", json=_valid_gig_payload(), headers=_auth_headers(client_token)
        )
        gig_id = cr.json()["id"]  # still DRAFT

        resp = await client.post(
            "/v1/proposals",
            json={"gig_id": gig_id, "cover_letter": "Hello", "estimated_days": 5},
            headers=_auth_headers(freelancer_token),
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "GIG_NOT_OPEN"

    @pytest.mark.asyncio
    async def test_duplicate_proposal_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        gig_id = await _create_open_gig(client, db_session, client_token)

        await client.post(
            "/v1/proposals",
            json={"gig_id": gig_id, "cover_letter": "First", "estimated_days": 5},
            headers=_auth_headers(freelancer_token),
        )
        resp = await client.post(
            "/v1/proposals",
            json={"gig_id": gig_id, "cover_letter": "Second", "estimated_days": 5},
            headers=_auth_headers(freelancer_token),
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "DUPLICATE_PROPOSAL"


# ---------------------------------------------------------------------------
# GET /v1/gigs/{gig_id}/proposals
# ---------------------------------------------------------------------------


class TestListProposals:
    @pytest.mark.asyncio
    async def test_client_can_list_proposals(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        gig_id = await _create_open_gig(client, db_session, client_token)

        await client.post(
            "/v1/proposals",
            json={"gig_id": gig_id, "cover_letter": "Hello", "estimated_days": 5},
            headers=_auth_headers(freelancer_token),
        )

        resp = await client.get(
            f"/v1/gigs/{gig_id}/proposals", headers=_auth_headers(client_token)
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["proposals"]) == 1

    @pytest.mark.asyncio
    async def test_freelancer_cannot_list_proposals(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        gig_id = await _create_open_gig(client, db_session, client_token)

        resp = await client.get(
            f"/v1/gigs/{gig_id}/proposals", headers=_auth_headers(freelancer_token)
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_non_owner_client_returns_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        other_client_token = await _register_and_get_token(
            client, {**_CLIENT_PAYLOAD, "email": "other@example.com"}
        )
        gig_id = await _create_open_gig(client, db_session, client_token)

        resp = await client.get(
            f"/v1/gigs/{gig_id}/proposals", headers=_auth_headers(other_client_token)
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /v1/proposals/{proposal_id}/accept
# ---------------------------------------------------------------------------


class TestAcceptProposal:
    @pytest.mark.asyncio
    async def test_client_can_accept_proposal(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        gig_id = await _create_open_gig(client, db_session, client_token)

        pr = await client.post(
            "/v1/proposals",
            json={"gig_id": gig_id, "cover_letter": "Hello", "estimated_days": 5},
            headers=_auth_headers(freelancer_token),
        )
        proposal_id = pr.json()["id"]

        resp = await client.post(
            f"/v1/proposals/{proposal_id}/accept",
            headers=_auth_headers(client_token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ACCEPTED"

        # Gig should now be IN_PROGRESS
        gig_resp = await client.get(f"/v1/gigs/{gig_id}")
        assert gig_resp.json()["status"] == "IN_PROGRESS"

    @pytest.mark.asyncio
    async def test_accept_rejects_other_proposals(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        freelancer2_token = await _register_and_get_token(client, _FREELANCER_2_PAYLOAD)
        gig_id = await _create_open_gig(client, db_session, client_token)

        p1 = await client.post(
            "/v1/proposals",
            json={"gig_id": gig_id, "cover_letter": "First", "estimated_days": 5},
            headers=_auth_headers(freelancer_token),
        )
        p2 = await client.post(
            "/v1/proposals",
            json={"gig_id": gig_id, "cover_letter": "Second", "estimated_days": 8},
            headers=_auth_headers(freelancer2_token),
        )

        await client.post(
            f"/v1/proposals/{p1.json()['id']}/accept",
            headers=_auth_headers(client_token),
        )

        proposals_resp = await client.get(
            f"/v1/gigs/{gig_id}/proposals", headers=_auth_headers(client_token)
        )
        proposals = {p["id"]: p for p in proposals_resp.json()["proposals"]}
        assert proposals[p1.json()["id"]]["status"] == "ACCEPTED"
        assert proposals[p2.json()["id"]]["status"] == "REJECTED"

    @pytest.mark.asyncio
    async def test_freelancer_cannot_accept_proposal(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        gig_id = await _create_open_gig(client, db_session, client_token)

        pr = await client.post(
            "/v1/proposals",
            json={"gig_id": gig_id, "cover_letter": "Hello", "estimated_days": 5},
            headers=_auth_headers(freelancer_token),
        )
        proposal_id = pr.json()["id"]

        resp = await client.post(
            f"/v1/proposals/{proposal_id}/accept",
            headers=_auth_headers(freelancer_token),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_accept_not_found_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        resp = await client.post(
            "/v1/proposals/00000000-0000-0000-0000-000000000000/accept",
            headers=_auth_headers(client_token),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /v1/proposals/{proposal_id}/withdraw
# ---------------------------------------------------------------------------


class TestWithdrawProposal:
    @pytest.mark.asyncio
    async def test_freelancer_can_withdraw_proposal(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        gig_id = await _create_open_gig(client, db_session, client_token)

        pr = await client.post(
            "/v1/proposals",
            json={"gig_id": gig_id, "cover_letter": "Hello", "estimated_days": 5},
            headers=_auth_headers(freelancer_token),
        )
        proposal_id = pr.json()["id"]

        resp = await client.post(
            f"/v1/proposals/{proposal_id}/withdraw",
            headers=_auth_headers(freelancer_token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "WITHDRAWN"

    @pytest.mark.asyncio
    async def test_client_cannot_withdraw_proposal(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        gig_id = await _create_open_gig(client, db_session, client_token)

        pr = await client.post(
            "/v1/proposals",
            json={"gig_id": gig_id, "cover_letter": "Hello", "estimated_days": 5},
            headers=_auth_headers(freelancer_token),
        )
        proposal_id = pr.json()["id"]

        resp = await client.post(
            f"/v1/proposals/{proposal_id}/withdraw",
            headers=_auth_headers(client_token),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_withdraw_not_found_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        freelancer_token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        resp = await client.post(
            "/v1/proposals/00000000-0000-0000-0000-000000000000/withdraw",
            headers=_auth_headers(freelancer_token),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /v1/proposals/{proposal_id}/reject
# ---------------------------------------------------------------------------


class TestRejectProposal:
    @pytest.mark.asyncio
    async def test_client_can_reject_proposal(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        gig_id = await _create_open_gig(client, db_session, client_token)

        pr = await client.post(
            "/v1/proposals",
            json={"gig_id": gig_id, "cover_letter": "Hello", "estimated_days": 5},
            headers=_auth_headers(freelancer_token),
        )
        proposal_id = pr.json()["id"]

        resp = await client.post(
            f"/v1/proposals/{proposal_id}/reject",
            headers=_auth_headers(client_token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "REJECTED"

    @pytest.mark.asyncio
    async def test_freelancer_cannot_reject_proposal(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        gig_id = await _create_open_gig(client, db_session, client_token)

        pr = await client.post(
            "/v1/proposals",
            json={"gig_id": gig_id, "cover_letter": "Hello", "estimated_days": 5},
            headers=_auth_headers(freelancer_token),
        )
        proposal_id = pr.json()["id"]

        resp = await client.post(
            f"/v1/proposals/{proposal_id}/reject",
            headers=_auth_headers(freelancer_token),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_reject_not_found_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        resp = await client.post(
            "/v1/proposals/00000000-0000-0000-0000-000000000000/reject",
            headers=_auth_headers(client_token),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_reject_already_accepted_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        gig_id = await _create_open_gig(client, db_session, client_token)

        pr = await client.post(
            "/v1/proposals",
            json={"gig_id": gig_id, "cover_letter": "Hello", "estimated_days": 5},
            headers=_auth_headers(freelancer_token),
        )
        proposal_id = pr.json()["id"]

        await client.post(
            f"/v1/proposals/{proposal_id}/accept",
            headers=_auth_headers(client_token),
        )

        resp = await client.post(
            f"/v1/proposals/{proposal_id}/reject",
            headers=_auth_headers(client_token),
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "PROPOSAL_NOT_PENDING"


# ---------------------------------------------------------------------------
# GET /v1/gigs/{gig_id}/proposals/mine
# ---------------------------------------------------------------------------


class TestGetMyProposal:
    @pytest.mark.asyncio
    async def test_freelancer_can_get_own_proposal(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        gig_id = await _create_open_gig(client, db_session, client_token)

        await client.post(
            "/v1/proposals",
            json={"gig_id": gig_id, "cover_letter": "Hello", "estimated_days": 5},
            headers=_auth_headers(freelancer_token),
        )

        resp = await client.get(
            f"/v1/gigs/{gig_id}/proposals/mine",
            headers=_auth_headers(freelancer_token),
        )
        assert resp.status_code == 200
        assert resp.json()["gig_id"] == gig_id

    @pytest.mark.asyncio
    async def test_returns_404_when_no_proposal(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        gig_id = await _create_open_gig(client, db_session, client_token)

        resp = await client.get(
            f"/v1/gigs/{gig_id}/proposals/mine",
            headers=_auth_headers(freelancer_token),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_client_cannot_use_mine_endpoint(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        gig_id = await _create_open_gig(client, db_session, client_token)

        resp = await client.get(
            f"/v1/gigs/{gig_id}/proposals/mine",
            headers=_auth_headers(client_token),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# GET /v1/gigs with filters
# ---------------------------------------------------------------------------


class TestGigFilters:
    @pytest.mark.asyncio
    async def test_currency_filter(self, client: AsyncClient, db_session: AsyncSession):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)

        # SOL gig (default currency from _valid_gig_payload)
        await _create_open_gig(client, db_session, client_token)

        # USDC gig
        usdc_payload = {
            **_valid_gig_payload(),
            "currency": "USDC",
            "token_address": "0x" + "a" * 40,
            "title": "USDC Gig",
        }
        cr2 = await client.post(
            "/v1/gigs", json=usdc_payload, headers=_auth_headers(client_token)
        )
        gig2_id = cr2.json()["id"]
        await db_session.execute(
            sa_update(GigModel).where(GigModel.id == gig2_id).values(status="OPEN")
        )
        await db_session.commit()

        resp = await client.get("/v1/gigs?currency=SOL")
        assert resp.status_code == 200
        data = resp.json()
        assert all(g["currency"] == "SOL" for g in data["gigs"])

    @pytest.mark.asyncio
    async def test_skill_filter(self, client: AsyncClient, db_session: AsyncSession):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)

        # Python gig (already from _valid_gig_payload)
        await _create_open_gig(client, db_session, client_token)

        # Go gig
        go_payload = {
            **_valid_gig_payload(),
            "required_skills": ["Go"],
            "title": "Go Gig",
        }
        cr2 = await client.post(
            "/v1/gigs", json=go_payload, headers=_auth_headers(client_token)
        )
        gig2_id = cr2.json()["id"]
        await db_session.execute(
            sa_update(GigModel).where(GigModel.id == gig2_id).values(status="OPEN")
        )
        await db_session.commit()

        resp = await client.get("/v1/gigs?skill=Python")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert "Python" in data["gigs"][0]["required_skills"]

    @pytest.mark.asyncio
    async def test_amount_filter(self, client: AsyncClient, db_session: AsyncSession):
        client_token = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        await _create_open_gig(client, db_session, client_token)  # total_amount = 1000

        resp = await client.get("/v1/gigs?min_amount=500&max_amount=2000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1

        resp2 = await client.get("/v1/gigs?min_amount=2000")
        assert resp2.status_code == 200
        assert resp2.json()["total"] == 0
