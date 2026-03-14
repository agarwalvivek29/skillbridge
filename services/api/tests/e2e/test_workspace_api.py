"""
E2E tests for workspace and review-report endpoints.

Runs against in-memory SQLite via conftest.py fixture.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.models import (
    GigModel,
    ReviewReportModel,
)

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


def _valid_gig_payload() -> dict:
    return {
        "title": "Build a widget",
        "description": "Full widget implementation",
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


async def _setup_in_progress_gig(
    client: AsyncClient,
    db_session: AsyncSession,
) -> tuple[str, str, str, str, str]:
    """
    Create a gig, register client and freelancer, assign freelancer to gig.
    Returns (client_token, freelancer_token, freelancer_id, gig_id, milestone_id).
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
    milestone_id = gig_resp.json()["milestones"][0]["id"]

    # Assign freelancer directly in DB
    await db_session.execute(
        sa_update(GigModel)
        .where(GigModel.id == gig_id)
        .values(status="IN_PROGRESS", freelancer_id=freelancer_id)
    )
    await db_session.commit()

    return client_token, freelancer_token, freelancer_id, gig_id, milestone_id


# ---------------------------------------------------------------------------
# GET /v1/gigs/{gig_id}/workspace
# ---------------------------------------------------------------------------


class TestGetWorkspace:
    @pytest.mark.asyncio
    async def test_client_can_access_workspace(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        cl_token, _, _, gig_id, _ = await _setup_in_progress_gig(client, db_session)
        resp = await client.get(f"/v1/gigs/{gig_id}/workspace", headers=_auth(cl_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["gig"]["id"] == gig_id
        assert len(data["gig"]["milestones"]) == 1
        assert data["submissions"] == []

    @pytest.mark.asyncio
    async def test_freelancer_can_access_workspace(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, fl_token, _, gig_id, _ = await _setup_in_progress_gig(client, db_session)
        resp = await client.get(f"/v1/gigs/{gig_id}/workspace", headers=_auth(fl_token))
        assert resp.status_code == 200
        assert resp.json()["gig"]["id"] == gig_id

    @pytest.mark.asyncio
    async def test_unrelated_user_gets_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, _, _, gig_id, _ = await _setup_in_progress_gig(client, db_session)
        third_token, _ = await _register_and_get_token(
            client,
            {
                "email": "third@example.com",
                "password": "strongPass1",
                "name": "Third User",
                "role": "USER_ROLE_CLIENT",
            },
        )
        resp = await client.get(
            f"/v1/gigs/{gig_id}/workspace", headers=_auth(third_token)
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, _, _, gig_id, _ = await _setup_in_progress_gig(client, db_session)
        resp = await client.get(f"/v1/gigs/{gig_id}/workspace")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unknown_gig_returns_404(self, client: AsyncClient):
        token, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        resp = await client.get(
            "/v1/gigs/00000000-0000-0000-0000-000000000000/workspace",
            headers=_auth(token),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_workspace_includes_submissions(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        with patch("src.infra.github.post_openreview_comment", new_callable=AsyncMock):
            cl_token, fl_token, _, gig_id, milestone_id = await _setup_in_progress_gig(
                client, db_session
            )
            await client.post(
                f"/v1/milestones/{milestone_id}/submissions",
                json={"repo_url": "https://github.com/user/repo/pull/1"},
                headers=_auth(fl_token),
            )

        resp = await client.get(f"/v1/gigs/{gig_id}/workspace", headers=_auth(cl_token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["submissions"]) == 1
        sub = data["submissions"][0]
        assert sub["milestone_id"] == milestone_id
        assert sub["review_verdict"] is None
        assert sub["review_score"] is None

    @pytest.mark.asyncio
    async def test_workspace_submissions_include_review_fields(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        with patch("src.infra.github.post_openreview_comment", new_callable=AsyncMock):
            cl_token, fl_token, _, gig_id, milestone_id = await _setup_in_progress_gig(
                client, db_session
            )
            create_resp = await client.post(
                f"/v1/milestones/{milestone_id}/submissions",
                json={"repo_url": "https://github.com/user/repo/pull/1"},
                headers=_auth(fl_token),
            )
        submission_id = create_resp.json()["id"]

        # Insert a review report
        report = ReviewReportModel(
            submission_id=submission_id,
            verdict="PASS",
            score=100,
            body="Looks good!",
            model_version="openreview",
        )
        db_session.add(report)
        await db_session.commit()

        resp = await client.get(f"/v1/gigs/{gig_id}/workspace", headers=_auth(cl_token))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["submissions"]) == 1
        sub = data["submissions"][0]
        assert sub["review_verdict"] == "PASS"
        assert sub["review_score"] == 100


# ---------------------------------------------------------------------------
# GET /v1/submissions/{submission_id}/review-report
# ---------------------------------------------------------------------------


class TestGetReviewReport:
    @pytest.mark.asyncio
    async def test_returns_report_for_participant(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        with patch("src.infra.github.post_openreview_comment", new_callable=AsyncMock):
            cl_token, fl_token, _, _, milestone_id = await _setup_in_progress_gig(
                client, db_session
            )
            create_resp = await client.post(
                f"/v1/milestones/{milestone_id}/submissions",
                json={"repo_url": "https://github.com/user/repo/pull/1"},
                headers=_auth(fl_token),
            )
        submission_id = create_resp.json()["id"]

        # Insert a review report directly in DB
        report = ReviewReportModel(
            submission_id=submission_id,
            verdict="PASS",
            score=100,
            body="Looks good!",
            model_version="openreview",
        )
        db_session.add(report)
        await db_session.commit()

        # Freelancer can access
        resp = await client.get(
            f"/v1/submissions/{submission_id}/review-report",
            headers=_auth(fl_token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["submission_id"] == submission_id
        assert data["verdict"] == "PASS"
        assert data["score"] == 100
        assert data["body"] == "Looks good!"

        # Client can also access
        resp2 = await client.get(
            f"/v1/submissions/{submission_id}/review-report",
            headers=_auth(cl_token),
        )
        assert resp2.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_404_when_no_report(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        with patch("src.infra.github.post_openreview_comment", new_callable=AsyncMock):
            _, fl_token, _, _, milestone_id = await _setup_in_progress_gig(
                client, db_session
            )
            create_resp = await client.post(
                f"/v1/milestones/{milestone_id}/submissions",
                json={"repo_url": "https://github.com/user/repo/pull/1"},
                headers=_auth(fl_token),
            )
        submission_id = create_resp.json()["id"]

        resp = await client.get(
            f"/v1/submissions/{submission_id}/review-report",
            headers=_auth(fl_token),
        )
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "REPORT_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_returns_404_for_unknown_submission(self, client: AsyncClient):
        token, _ = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        resp = await client.get(
            "/v1/submissions/00000000-0000-0000-0000-000000000000/review-report",
            headers=_auth(token),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_unrelated_user_gets_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        with patch("src.infra.github.post_openreview_comment", new_callable=AsyncMock):
            _, fl_token, _, _, milestone_id = await _setup_in_progress_gig(
                client, db_session
            )
            create_resp = await client.post(
                f"/v1/milestones/{milestone_id}/submissions",
                json={"repo_url": "https://github.com/user/repo/pull/1"},
                headers=_auth(fl_token),
            )
        submission_id = create_resp.json()["id"]

        # Insert report
        report = ReviewReportModel(
            submission_id=submission_id,
            verdict="PASS",
            score=100,
            body="Good",
            model_version="openreview",
        )
        db_session.add(report)
        await db_session.commit()

        third_token, _ = await _register_and_get_token(
            client,
            {
                "email": "third@example.com",
                "password": "strongPass1",
                "name": "Third User",
                "role": "USER_ROLE_CLIENT",
            },
        )
        resp = await client.get(
            f"/v1/submissions/{submission_id}/review-report",
            headers=_auth(third_token),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.get(
            "/v1/submissions/00000000-0000-0000-0000-000000000000/review-report"
        )
        assert resp.status_code == 401
