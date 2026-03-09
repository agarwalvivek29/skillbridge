"""
End-to-end tests for dispute API endpoints.

Uses SQLite in-memory + FastAPI test client.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.auth import create_access_token
from src.infra.models import GigModel, MilestoneModel

_CLIENT_ID = "cccccccc-0000-0000-0000-000000000001"
_FREELANCER_ID = "ffffffff-0000-0000-0000-000000000001"
_ADMIN_ID = "aaaaaaaa-0000-0000-0000-000000000001"
_OTHER_USER_ID = "00000000-0000-0000-0000-999999999999"


def _auth_header(user_id: str, role: str) -> dict[str, str]:
    token, _ = create_access_token(user_id, role)
    return {"Authorization": f"Bearer {token}"}


_CLIENT_HEADERS = _auth_header(_CLIENT_ID, "USER_ROLE_CLIENT")
_FREELANCER_HEADERS = _auth_header(_FREELANCER_ID, "USER_ROLE_FREELANCER")
_ADMIN_HEADERS = _auth_header(_ADMIN_ID, "USER_ROLE_ADMIN")
_OTHER_HEADERS = _auth_header(_OTHER_USER_ID, "USER_ROLE_FREELANCER")


async def _create_gig_with_milestone(
    client: AsyncClient, db_session: AsyncSession
) -> tuple[str, str]:
    """Create a gig with one milestone via API and set it to IN_PROGRESS."""
    resp = await client.post(
        "/v1/gigs",
        headers=_CLIENT_HEADERS,
        json={
            "title": "Test Gig",
            "description": "Test gig description",
            "total_amount": "1000",
            "currency": "ETH",
            "required_skills": ["Python"],
            "milestones": [
                {
                    "title": "M1",
                    "description": "First milestone",
                    "acceptance_criteria": "Tests pass",
                    "amount": "1000",
                    "order": 1,
                }
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    gig_id = data["id"]
    milestone_id = data["milestones"][0]["id"]

    # Set gig to IN_PROGRESS with freelancer assigned
    await db_session.execute(
        sa_update(GigModel)
        .where(GigModel.id == gig_id)
        .values(status="IN_PROGRESS", freelancer_id=_FREELANCER_ID)
    )
    # Set milestone to SUBMITTED
    await db_session.execute(
        sa_update(MilestoneModel)
        .where(MilestoneModel.id == milestone_id)
        .values(status="SUBMITTED")
    )
    await db_session.commit()

    return gig_id, milestone_id


# ---------------------------------------------------------------------------
# POST /v1/milestones/{milestone_id}/dispute
# ---------------------------------------------------------------------------


class TestRaiseDisputeAPI:
    @pytest.mark.asyncio
    async def test_raise_dispute_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, milestone_id = await _create_gig_with_milestone(client, db_session)

        resp = await client.post(
            f"/v1/milestones/{milestone_id}/dispute",
            headers=_CLIENT_HEADERS,
            json={"reason": "Work is incomplete"},
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "OPEN"
        assert data["reason"] == "Work is incomplete"
        assert data["milestone_id"] == milestone_id
        assert data["raised_by_user_id"] == _CLIENT_ID

    @pytest.mark.asyncio
    async def test_raise_dispute_by_freelancer(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, milestone_id = await _create_gig_with_milestone(client, db_session)

        resp = await client.post(
            f"/v1/milestones/{milestone_id}/dispute",
            headers=_FREELANCER_HEADERS,
            json={"reason": "Client not responding"},
        )

        assert resp.status_code == 201
        assert resp.json()["raised_by_user_id"] == _FREELANCER_ID

    @pytest.mark.asyncio
    async def test_raise_dispute_no_auth(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, milestone_id = await _create_gig_with_milestone(client, db_session)

        resp = await client.post(
            f"/v1/milestones/{milestone_id}/dispute",
            json={"reason": "Dispute"},
        )

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_raise_dispute_duplicate(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, milestone_id = await _create_gig_with_milestone(client, db_session)

        resp1 = await client.post(
            f"/v1/milestones/{milestone_id}/dispute",
            headers=_CLIENT_HEADERS,
            json={"reason": "First dispute"},
        )
        assert resp1.status_code == 201

        resp2 = await client.post(
            f"/v1/milestones/{milestone_id}/dispute",
            headers=_FREELANCER_HEADERS,
            json={"reason": "Second dispute"},
        )
        assert resp2.status_code == 409


# ---------------------------------------------------------------------------
# GET /v1/disputes/{dispute_id}
# ---------------------------------------------------------------------------


class TestGetDisputeAPI:
    @pytest.mark.asyncio
    async def test_get_dispute(self, client: AsyncClient, db_session: AsyncSession):
        _, milestone_id = await _create_gig_with_milestone(client, db_session)

        create_resp = await client.post(
            f"/v1/milestones/{milestone_id}/dispute",
            headers=_CLIENT_HEADERS,
            json={"reason": "Incomplete work"},
        )
        dispute_id = create_resp.json()["id"]

        resp = await client.get(
            f"/v1/disputes/{dispute_id}",
            headers=_CLIENT_HEADERS,
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == dispute_id
        assert "messages" in data

    @pytest.mark.asyncio
    async def test_get_dispute_not_found(self, client: AsyncClient):
        resp = await client.get(
            "/v1/disputes/00000000-0000-0000-0000-000000000000",
            headers=_CLIENT_HEADERS,
        )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /v1/milestones/{milestone_id}/dispute
# ---------------------------------------------------------------------------


class TestGetMilestoneDisputeAPI:
    @pytest.mark.asyncio
    async def test_get_milestone_dispute(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, milestone_id = await _create_gig_with_milestone(client, db_session)

        await client.post(
            f"/v1/milestones/{milestone_id}/dispute",
            headers=_CLIENT_HEADERS,
            json={"reason": "Incomplete"},
        )

        resp = await client.get(
            f"/v1/milestones/{milestone_id}/dispute",
            headers=_CLIENT_HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json()["milestone_id"] == milestone_id

    @pytest.mark.asyncio
    async def test_get_milestone_dispute_none_exists(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, milestone_id = await _create_gig_with_milestone(client, db_session)

        resp = await client.get(
            f"/v1/milestones/{milestone_id}/dispute",
            headers=_CLIENT_HEADERS,
        )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /v1/disputes/{dispute_id}/messages
# ---------------------------------------------------------------------------


class TestPostMessageAPI:
    @pytest.mark.asyncio
    async def test_post_message(self, client: AsyncClient, db_session: AsyncSession):
        _, milestone_id = await _create_gig_with_milestone(client, db_session)

        create_resp = await client.post(
            f"/v1/milestones/{milestone_id}/dispute",
            headers=_CLIENT_HEADERS,
            json={"reason": "Incomplete"},
        )
        dispute_id = create_resp.json()["id"]

        resp = await client.post(
            f"/v1/disputes/{dispute_id}/messages",
            headers=_FREELANCER_HEADERS,
            json={"content": "I completed the work as specified"},
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "I completed the work as specified"
        assert data["user_id"] == _FREELANCER_ID

    @pytest.mark.asyncio
    async def test_post_message_no_auth(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, milestone_id = await _create_gig_with_milestone(client, db_session)

        create_resp = await client.post(
            f"/v1/milestones/{milestone_id}/dispute",
            headers=_CLIENT_HEADERS,
            json={"reason": "Incomplete"},
        )
        dispute_id = create_resp.json()["id"]

        resp = await client.post(
            f"/v1/disputes/{dispute_id}/messages",
            json={"content": "Message"},
        )

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /v1/disputes/{dispute_id}/resolve
# ---------------------------------------------------------------------------


class TestResolveDisputeAPI:
    @pytest.mark.asyncio
    async def test_resolve_dispute_admin(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, milestone_id = await _create_gig_with_milestone(client, db_session)

        create_resp = await client.post(
            f"/v1/milestones/{milestone_id}/dispute",
            headers=_CLIENT_HEADERS,
            json={"reason": "Incomplete"},
        )
        dispute_id = create_resp.json()["id"]

        resp = await client.post(
            f"/v1/disputes/{dispute_id}/resolve",
            headers=_ADMIN_HEADERS,
            json={
                "resolution": "DISPUTE_RESOLUTION_PAY_FREELANCER",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "RESOLVED"
        assert data["resolution"] == "DISPUTE_RESOLUTION_PAY_FREELANCER"

    @pytest.mark.asyncio
    async def test_resolve_dispute_non_admin_fails(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, milestone_id = await _create_gig_with_milestone(client, db_session)

        create_resp = await client.post(
            f"/v1/milestones/{milestone_id}/dispute",
            headers=_CLIENT_HEADERS,
            json={"reason": "Incomplete"},
        )
        dispute_id = create_resp.json()["id"]

        resp = await client.post(
            f"/v1/disputes/{dispute_id}/resolve",
            headers=_CLIENT_HEADERS,
            json={
                "resolution": "DISPUTE_RESOLUTION_PAY_FREELANCER",
            },
        )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_resolve_dispute_split(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, milestone_id = await _create_gig_with_milestone(client, db_session)

        create_resp = await client.post(
            f"/v1/milestones/{milestone_id}/dispute",
            headers=_CLIENT_HEADERS,
            json={"reason": "Partial completion"},
        )
        dispute_id = create_resp.json()["id"]

        resp = await client.post(
            f"/v1/disputes/{dispute_id}/resolve",
            headers=_ADMIN_HEADERS,
            json={
                "resolution": "DISPUTE_RESOLUTION_SPLIT",
                "freelancer_split_amount": "500",
            },
        )

        assert resp.status_code == 200
        assert resp.json()["freelancer_split_amount"] == "500"
