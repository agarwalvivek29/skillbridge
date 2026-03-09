"""
E2E tests for rating/review endpoints.

Runs against in-memory SQLite via conftest.py fixture.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.models import GigModel, ReviewModel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CLIENT_PAYLOAD = {
    "email": "client-review@example.com",
    "password": "strongPass1",
    "name": "Review Client",
    "role": "USER_ROLE_CLIENT",
}

_FREELANCER_PAYLOAD = {
    "email": "freelancer-review@example.com",
    "password": "strongPass1",
    "name": "Review Freelancer",
    "role": "USER_ROLE_FREELANCER",
}


def _valid_gig_payload() -> dict:
    return {
        "title": "Review Test Gig",
        "description": "Gig for testing reviews",
        "total_amount": "1000",
        "currency": "ETH",
        "required_skills": ["Python"],
        "milestones": [
            {
                "title": "Milestone 1",
                "description": "Do the work",
                "acceptance_criteria": "## Criteria\n- Tests pass",
                "amount": "1000",
                "order": 1,
            }
        ],
    }


async def _register_and_get_token(
    client: AsyncClient, payload: dict
) -> tuple[str, str]:
    """Register a user and return (token, user_id)."""
    resp = await client.post("/v1/auth/email/register", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return data["access_token"], data["user_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _setup_completed_gig(
    client: AsyncClient,
    db_session: AsyncSession,
) -> tuple[str, str, str, str]:
    """
    Create a COMPLETED gig with client + freelancer.
    Returns (client_token, freelancer_token, gig_id, freelancer_id).
    """
    client_token, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)
    freelancer_token, freelancer_id = await _register_and_get_token(
        client, _FREELANCER_PAYLOAD
    )

    gig_resp = await client.post(
        "/v1/gigs", json=_valid_gig_payload(), headers=_auth(client_token)
    )
    assert gig_resp.status_code == 201
    gig_id = gig_resp.json()["id"]

    await db_session.execute(
        sa_update(GigModel)
        .where(GigModel.id == gig_id)
        .values(status="COMPLETED", freelancer_id=freelancer_id)
    )
    await db_session.commit()

    return client_token, freelancer_token, gig_id, freelancer_id


# ---------------------------------------------------------------------------
# POST /v1/gigs/{gig_id}/review
# ---------------------------------------------------------------------------


class TestCreateReview:
    @pytest.mark.asyncio
    async def test_client_can_submit_review(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        cl_token, _, gig_id, _ = await _setup_completed_gig(client, db_session)
        resp = await client.post(
            f"/v1/gigs/{gig_id}/review",
            json={"rating": 4, "comment": "Good work!"},
            headers=_auth(cl_token),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["rating"] == 4
        assert data["comment"] == "Good work!"
        assert data["is_visible"] is False

    @pytest.mark.asyncio
    async def test_both_submit_reveals_reviews(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        cl_token, fl_token, gig_id, _ = await _setup_completed_gig(client, db_session)

        resp1 = await client.post(
            f"/v1/gigs/{gig_id}/review",
            json={"rating": 4, "comment": ""},
            headers=_auth(cl_token),
        )
        assert resp1.status_code == 201
        assert resp1.json()["is_visible"] is False

        resp2 = await client.post(
            f"/v1/gigs/{gig_id}/review",
            json={"rating": 5, "comment": ""},
            headers=_auth(fl_token),
        )
        assert resp2.status_code == 201
        assert resp2.json()["is_visible"] is True

    @pytest.mark.asyncio
    async def test_duplicate_review_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        cl_token, _, gig_id, _ = await _setup_completed_gig(client, db_session)
        await client.post(
            f"/v1/gigs/{gig_id}/review",
            json={"rating": 4, "comment": ""},
            headers=_auth(cl_token),
        )
        resp = await client.post(
            f"/v1/gigs/{gig_id}/review",
            json={"rating": 5, "comment": "Changed mind"},
            headers=_auth(cl_token),
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "ALREADY_REVIEWED"

    @pytest.mark.asyncio
    async def test_non_participant_returns_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, _, gig_id, _ = await _setup_completed_gig(client, db_session)
        third_token, _ = await _register_and_get_token(
            client,
            {
                "email": "third-review@example.com",
                "password": "strongPass1",
                "name": "Third User",
                "role": "USER_ROLE_CLIENT",
            },
        )
        resp = await client.post(
            f"/v1/gigs/{gig_id}/review",
            json={"rating": 4, "comment": ""},
            headers=_auth(third_token),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "NOT_GIG_PARTICIPANT"

    @pytest.mark.asyncio
    async def test_non_completed_gig_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        cl_token, _ = await _register_and_get_token(
            client,
            {
                "email": "client-draft@example.com",
                "password": "strongPass1",
                "name": "Draft Client",
                "role": "USER_ROLE_CLIENT",
            },
        )
        gig_resp = await client.post(
            "/v1/gigs", json=_valid_gig_payload(), headers=_auth(cl_token)
        )
        gig_id = gig_resp.json()["id"]

        resp = await client.post(
            f"/v1/gigs/{gig_id}/review",
            json={"rating": 4, "comment": ""},
            headers=_auth(cl_token),
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "GIG_NOT_COMPLETED"

    @pytest.mark.asyncio
    async def test_invalid_rating_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        cl_token, _, gig_id, _ = await _setup_completed_gig(client, db_session)
        resp = await client.post(
            f"/v1/gigs/{gig_id}/review",
            json={"rating": 0, "comment": ""},
            headers=_auth(cl_token),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, _, gig_id, _ = await _setup_completed_gig(client, db_session)
        resp = await client.post(
            f"/v1/gigs/{gig_id}/review",
            json={"rating": 4, "comment": ""},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /v1/gigs/{gig_id}/reviews
# ---------------------------------------------------------------------------


class TestGetGigReviews:
    @pytest.mark.asyncio
    async def test_returns_visible_reviews(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        cl_token, fl_token, gig_id, _ = await _setup_completed_gig(client, db_session)

        # Submit both reviews
        await client.post(
            f"/v1/gigs/{gig_id}/review",
            json={"rating": 4, "comment": ""},
            headers=_auth(cl_token),
        )
        await client.post(
            f"/v1/gigs/{gig_id}/review",
            json={"rating": 5, "comment": ""},
            headers=_auth(fl_token),
        )

        resp = await client.get(
            f"/v1/gigs/{gig_id}/reviews",
            headers=_auth(cl_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["reviews"]) == 2
        assert data["average_rating_x100"] == 450

    @pytest.mark.asyncio
    async def test_hidden_reviews_not_returned(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        cl_token, _, gig_id, _ = await _setup_completed_gig(client, db_session)
        await client.post(
            f"/v1/gigs/{gig_id}/review",
            json={"rating": 4, "comment": ""},
            headers=_auth(cl_token),
        )
        resp = await client.get(
            f"/v1/gigs/{gig_id}/reviews",
            headers=_auth(cl_token),
        )
        assert resp.status_code == 200
        assert len(resp.json()["reviews"]) == 0

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, _, gig_id, _ = await _setup_completed_gig(client, db_session)
        resp = await client.get(f"/v1/gigs/{gig_id}/reviews")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /v1/users/{user_id}/reviews
# ---------------------------------------------------------------------------


class TestGetUserReviews:
    @pytest.mark.asyncio
    async def test_public_user_reviews(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        cl_token, fl_token, gig_id, fl_id = await _setup_completed_gig(
            client, db_session
        )

        # Both submit
        await client.post(
            f"/v1/gigs/{gig_id}/review",
            json={"rating": 4, "comment": ""},
            headers=_auth(cl_token),
        )
        await client.post(
            f"/v1/gigs/{gig_id}/review",
            json={"rating": 5, "comment": ""},
            headers=_auth(fl_token),
        )

        # Public endpoint - no auth needed
        resp = await client.get(f"/v1/users/{fl_id}/reviews")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["reviews"]) == 1
        assert data["reviews"][0]["reviewee_id"] == fl_id
        assert data["average_rating_x100"] == 400

    @pytest.mark.asyncio
    async def test_7day_window_reveals(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        cl_token, _, gig_id, fl_id = await _setup_completed_gig(client, db_session)

        await client.post(
            f"/v1/gigs/{gig_id}/review",
            json={"rating": 3, "comment": ""},
            headers=_auth(cl_token),
        )

        # Backdate to 8 days ago
        old_time = datetime.now(timezone.utc) - timedelta(days=8)
        await db_session.execute(
            sa_update(ReviewModel)
            .where(ReviewModel.gig_id == gig_id)
            .values(created_at=old_time)
        )
        await db_session.commit()

        resp = await client.get(f"/v1/users/{fl_id}/reviews")
        assert resp.status_code == 200
        assert len(resp.json()["reviews"]) == 1
