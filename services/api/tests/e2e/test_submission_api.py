"""
E2E tests for submission endpoints.

Runs against in-memory SQLite via conftest.py fixture.
Celery and S3 are mocked to avoid external dependencies.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.models import GigModel, MilestoneModel

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
) -> tuple[str, str, str, str]:
    """
    Create a gig, register client and freelancer, assign freelancer to gig.
    Returns (client_token, freelancer_token, gig_id, milestone_id).
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

    # Assign freelancer directly in DB (gig assignment is issue #8)
    await db_session.execute(
        sa_update(GigModel)
        .where(GigModel.id == gig_id)
        .values(status="IN_PROGRESS", freelancer_id=freelancer_id)
    )
    await db_session.commit()

    return client_token, freelancer_token, gig_id, milestone_id


# ---------------------------------------------------------------------------
# POST /v1/milestones/{milestone_id}/submissions
# ---------------------------------------------------------------------------


class TestCreateSubmission:
    @pytest.mark.asyncio
    async def test_freelancer_can_submit(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        with patch("src.domain.submission.enqueue_review"):
            _, fl_token, _, milestone_id = await _setup_in_progress_gig(
                client, db_session
            )
            resp = await client.post(
                f"/v1/milestones/{milestone_id}/submissions",
                json={"repo_url": "https://github.com/user/repo"},
                headers=_auth(fl_token),
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["revision_number"] == 1
        assert data["previous_submission_id"] is None
        assert data["status"] == "UNDER_REVIEW"
        assert data["repo_url"] == "https://github.com/user/repo"

    @pytest.mark.asyncio
    async def test_client_cannot_submit(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        cl_token, _, _, milestone_id = await _setup_in_progress_gig(client, db_session)
        resp = await client.post(
            f"/v1/milestones/{milestone_id}/submissions",
            json={"repo_url": "https://github.com/user/repo"},
            headers=_auth(cl_token),
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "FORBIDDEN"

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, _, _, milestone_id = await _setup_in_progress_gig(client, db_session)
        resp = await client.post(
            f"/v1/milestones/{milestone_id}/submissions",
            json={"repo_url": "https://github.com/user/repo"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_no_deliverable_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, fl_token, _, milestone_id = await _setup_in_progress_gig(client, db_session)
        resp = await client.post(
            f"/v1/milestones/{milestone_id}/submissions",
            json={"notes": "no repo and no files"},
            headers=_auth(fl_token),
        )
        assert resp.status_code == 400
        assert resp.json()["detail"]["code"] == "NO_DELIVERABLE"

    @pytest.mark.asyncio
    async def test_unknown_milestone_returns_404(self, client: AsyncClient):
        fl_token, _ = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        resp = await client.post(
            "/v1/milestones/00000000-0000-0000-0000-000000000000/submissions",
            json={"repo_url": "https://github.com/user/repo"},
            headers=_auth(fl_token),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_repo_url_returns_422(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, fl_token, _, milestone_id = await _setup_in_progress_gig(client, db_session)
        resp = await client.post(
            f"/v1/milestones/{milestone_id}/submissions",
            json={"repo_url": "https://bitbucket.org/user/repo"},
            headers=_auth(fl_token),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_http_repo_url_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """fix #6: HTTP (non-HTTPS) GitHub URLs must be rejected."""
        _, fl_token, _, milestone_id = await _setup_in_progress_gig(client, db_session)
        resp = await client.post(
            f"/v1/milestones/{milestone_id}/submissions",
            json={"repo_url": "http://github.com/user/repo"},
            headers=_auth(fl_token),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_file_key_without_submissions_prefix_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """fix #9: file_keys must start with 'submissions/'."""
        _, fl_token, _, milestone_id = await _setup_in_progress_gig(client, db_session)
        resp = await client.post(
            f"/v1/milestones/{milestone_id}/submissions",
            json={"file_keys": ["uploads/some-file.zip"]},
            headers=_auth(fl_token),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_resubmission_onto_approved_submission_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """fix #5: cannot chain a resubmission onto an APPROVED previous submission."""
        from src.infra.models import SubmissionModel

        with patch("src.domain.submission.enqueue_review"):
            _, fl_token, _, milestone_id = await _setup_in_progress_gig(
                client, db_session
            )
            first_resp = await client.post(
                f"/v1/milestones/{milestone_id}/submissions",
                json={"repo_url": "https://github.com/user/repo"},
                headers=_auth(fl_token),
            )
            assert first_resp.status_code == 201
            first_id = first_resp.json()["id"]

            # Force first submission to APPROVED and milestone to REVISION_REQUESTED
            await db_session.execute(
                sa_update(SubmissionModel)
                .where(SubmissionModel.id == first_id)
                .values(status="APPROVED")
            )
            await db_session.execute(
                sa_update(MilestoneModel)
                .where(MilestoneModel.id == milestone_id)
                .values(status="REVISION_REQUESTED")
            )
            await db_session.commit()

            resp = await client.post(
                f"/v1/milestones/{milestone_id}/submissions",
                json={
                    "repo_url": "https://github.com/user/repo-v2",
                    "previous_submission_id": first_id,
                },
                headers=_auth(fl_token),
            )
        assert resp.status_code == 422
        assert resp.json()["detail"]["code"] == "INVALID_PREVIOUS_SUBMISSION"

    @pytest.mark.asyncio
    async def test_resubmission_increments_revision(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        with patch("src.domain.submission.enqueue_review"):
            _, fl_token, _, milestone_id = await _setup_in_progress_gig(
                client, db_session
            )
            first_resp = await client.post(
                f"/v1/milestones/{milestone_id}/submissions",
                json={"repo_url": "https://github.com/user/repo"},
                headers=_auth(fl_token),
            )
            assert first_resp.status_code == 201
            first_id = first_resp.json()["id"]

            # Simulate revision request
            await db_session.execute(
                sa_update(MilestoneModel)
                .where(MilestoneModel.id == milestone_id)
                .values(status="REVISION_REQUESTED")
            )
            await db_session.commit()

            second_resp = await client.post(
                f"/v1/milestones/{milestone_id}/submissions",
                json={
                    "repo_url": "https://github.com/user/repo-v2",
                    "previous_submission_id": first_id,
                },
                headers=_auth(fl_token),
            )
        assert second_resp.status_code == 201
        data = second_resp.json()
        assert data["revision_number"] == 2
        assert data["previous_submission_id"] == first_id


# ---------------------------------------------------------------------------
# GET /v1/milestones/{milestone_id}/submissions
# ---------------------------------------------------------------------------


class TestListSubmissions:
    @pytest.mark.asyncio
    async def test_list_returns_all_submissions(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        with patch("src.domain.submission.enqueue_review"):
            _, fl_token, _, milestone_id = await _setup_in_progress_gig(
                client, db_session
            )
            await client.post(
                f"/v1/milestones/{milestone_id}/submissions",
                json={"repo_url": "https://github.com/user/repo"},
                headers=_auth(fl_token),
            )

        cl_token, _ = await _register_and_get_token(
            client, {**_CLIENT_PAYLOAD, "email": "cl2@example.com"}
        )
        resp = await client.get(
            f"/v1/milestones/{milestone_id}/submissions",
            headers=_auth(cl_token),
        )
        assert resp.status_code == 200
        assert len(resp.json()["submissions"]) == 1

    @pytest.mark.asyncio
    async def test_list_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.get(
            "/v1/milestones/00000000-0000-0000-0000-000000000000/submissions"
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /v1/submissions/{submission_id}
# ---------------------------------------------------------------------------


class TestGetSubmission:
    @pytest.mark.asyncio
    async def test_get_existing_submission(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        with patch("src.domain.submission.enqueue_review"):
            _, fl_token, _, milestone_id = await _setup_in_progress_gig(
                client, db_session
            )
            create_resp = await client.post(
                f"/v1/milestones/{milestone_id}/submissions",
                json={"repo_url": "https://github.com/user/repo"},
                headers=_auth(fl_token),
            )
        submission_id = create_resp.json()["id"]
        resp = await client.get(
            f"/v1/submissions/{submission_id}", headers=_auth(fl_token)
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == submission_id

    @pytest.mark.asyncio
    async def test_get_unknown_returns_404(self, client: AsyncClient):
        fl_token, _ = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        resp = await client.get(
            "/v1/submissions/00000000-0000-0000-0000-000000000000",
            headers=_auth(fl_token),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.get("/v1/submissions/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unrelated_user_cannot_get_submission(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """fix #4: a user who is neither the gig's client nor freelancer gets 403."""
        with patch("src.domain.submission.enqueue_review"):
            _, fl_token, _, milestone_id = await _setup_in_progress_gig(
                client, db_session
            )
            create_resp = await client.post(
                f"/v1/milestones/{milestone_id}/submissions",
                json={"repo_url": "https://github.com/user/repo"},
                headers=_auth(fl_token),
            )
        submission_id = create_resp.json()["id"]

        # Register a third user unrelated to the gig
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
            f"/v1/submissions/{submission_id}", headers=_auth(third_token)
        )
        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "FORBIDDEN"
