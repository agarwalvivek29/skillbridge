"""
E2E tests for milestone approval and fund release endpoints.

Runs against in-memory SQLite via conftest.py fixture.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.models import EscrowContractModel, GigModel, MilestoneModel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CLIENT_PAYLOAD = {
    "email": "client-approval@example.com",
    "password": "strongPass1",
    "name": "Approval Client",
    "role": "USER_ROLE_CLIENT",
}

_FREELANCER_PAYLOAD = {
    "email": "freelancer-approval@example.com",
    "password": "strongPass1",
    "name": "Approval Freelancer",
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
    resp = await client.post("/v1/auth/email/register", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return data["access_token"], data["user_id"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _setup_gig_with_milestone_under_review(
    client: AsyncClient,
    db_session: AsyncSession,
) -> tuple[str, str, str, str]:
    """
    Create a gig with one milestone, assign freelancer, set milestone to UNDER_REVIEW.
    Returns (client_token, freelancer_token, gig_id, milestone_id).
    """
    client_token, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)
    freelancer_token, freelancer_id = await _register_and_get_token(
        client, _FREELANCER_PAYLOAD
    )

    resp = await client.post(
        "/v1/gigs", json=_valid_gig_payload(), headers=_auth(client_token)
    )
    assert resp.status_code == 201, resp.text
    gig_data = resp.json()
    gig_id = gig_data["id"]
    milestone_id = gig_data["milestones"][0]["id"]

    # Force IN_PROGRESS with freelancer assigned
    await db_session.execute(
        sa_update(GigModel)
        .where(GigModel.id == gig_id)
        .values(status="IN_PROGRESS", freelancer_id=freelancer_id)
    )
    await db_session.execute(
        sa_update(MilestoneModel)
        .where(MilestoneModel.id == milestone_id)
        .values(status="UNDER_REVIEW")
    )
    await db_session.flush()

    return client_token, freelancer_token, gig_id, milestone_id


# ---------------------------------------------------------------------------
# POST /approve
# ---------------------------------------------------------------------------


class TestApproveMilestoneEndpoint:
    @pytest.mark.asyncio
    async def test_approve_sets_status_approved(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token, _, _, milestone_id = await _setup_gig_with_milestone_under_review(
            client, db_session
        )

        resp = await client.post(
            f"/v1/milestones/{milestone_id}/approve",
            headers=_auth(client_token),
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "APPROVED"

    @pytest.mark.asyncio
    async def test_approve_requires_client_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        (
            _,
            freelancer_token,
            _,
            milestone_id,
        ) = await _setup_gig_with_milestone_under_review(client, db_session)

        resp = await client.post(
            f"/v1/milestones/{milestone_id}/approve",
            headers=_auth(freelancer_token),
        )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_approve_requires_auth(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        _, _, _, milestone_id = await _setup_gig_with_milestone_under_review(
            client, db_session
        )

        resp = await client.post(f"/v1/milestones/{milestone_id}/approve")

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_approve_disputed_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token, _, _, milestone_id = await _setup_gig_with_milestone_under_review(
            client, db_session
        )
        await db_session.execute(
            sa_update(MilestoneModel)
            .where(MilestoneModel.id == milestone_id)
            .values(status="DISPUTED")
        )
        await db_session.flush()

        resp = await client.post(
            f"/v1/milestones/{milestone_id}/approve",
            headers=_auth(client_token),
        )

        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "MILESTONE_DISPUTED"

    @pytest.mark.asyncio
    async def test_approve_unknown_milestone_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token, _, _, _ = await _setup_gig_with_milestone_under_review(
            client, db_session
        )

        resp = await client.post(
            "/v1/milestones/00000000-0000-0000-0000-000000000000/approve",
            headers=_auth(client_token),
        )

        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /request-revision
# ---------------------------------------------------------------------------


class TestRequestRevisionEndpoint:
    @pytest.mark.asyncio
    async def test_request_revision_sets_status(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token, _, _, milestone_id = await _setup_gig_with_milestone_under_review(
            client, db_session
        )

        resp = await client.post(
            f"/v1/milestones/{milestone_id}/request-revision",
            json={"reason": "Please add unit tests"},
            headers=_auth(client_token),
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "REVISION_REQUESTED"

    @pytest.mark.asyncio
    async def test_request_revision_requires_client_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        (
            _,
            freelancer_token,
            _,
            milestone_id,
        ) = await _setup_gig_with_milestone_under_review(client, db_session)

        resp = await client.post(
            f"/v1/milestones/{milestone_id}/request-revision",
            json={"reason": "reason"},
            headers=_auth(freelancer_token),
        )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_request_revision_pending_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token, _, _, milestone_id = await _setup_gig_with_milestone_under_review(
            client, db_session
        )
        # Reset to PENDING
        await db_session.execute(
            sa_update(MilestoneModel)
            .where(MilestoneModel.id == milestone_id)
            .values(status="PENDING")
        )
        await db_session.flush()

        resp = await client.post(
            f"/v1/milestones/{milestone_id}/request-revision",
            json={"reason": "reason"},
            headers=_auth(client_token),
        )

        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "MILESTONE_NOT_REVISABLE"


# ---------------------------------------------------------------------------
# GET /release-tx
# ---------------------------------------------------------------------------


class TestGetReleaseTxEndpoint:
    @pytest.mark.asyncio
    async def test_returns_calldata_for_approved_milestone(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        (
            client_token,
            _,
            gig_id,
            milestone_id,
        ) = await _setup_gig_with_milestone_under_review(client, db_session)
        await db_session.execute(
            sa_update(MilestoneModel)
            .where(MilestoneModel.id == milestone_id)
            .values(status="APPROVED")
        )
        await db_session.execute(
            sa_update(GigModel)
            .where(GigModel.id == gig_id)
            .values(contract_address="0xABCDEF1234567890AbcdEF1234567890aBcdef12")
        )
        await db_session.flush()

        resp = await client.get(
            f"/v1/milestones/{milestone_id}/release-tx",
            headers=_auth(client_token),
        )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["contract_address"] == "0xABCDEF1234567890AbcdEF1234567890aBcdef12"
        assert data["milestone_index"] == 0
        assert data["calldata"].startswith("0x5a36fb08")
        assert len(data["calldata"]) == 74  # "0x" + 72 hex chars
        assert isinstance(data["chain_id"], int)

    @pytest.mark.asyncio
    async def test_release_tx_requires_client_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        (
            _,
            freelancer_token,
            _,
            milestone_id,
        ) = await _setup_gig_with_milestone_under_review(client, db_session)

        resp = await client.get(
            f"/v1/milestones/{milestone_id}/release-tx",
            headers=_auth(freelancer_token),
        )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_release_tx_under_review_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token, _, _, milestone_id = await _setup_gig_with_milestone_under_review(
            client, db_session
        )

        resp = await client.get(
            f"/v1/milestones/{milestone_id}/release-tx",
            headers=_auth(client_token),
        )

        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "MILESTONE_NOT_APPROVED"

    @pytest.mark.asyncio
    async def test_release_tx_disputed_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        (
            client_token,
            _,
            gig_id,
            milestone_id,
        ) = await _setup_gig_with_milestone_under_review(client, db_session)
        await db_session.execute(
            sa_update(MilestoneModel)
            .where(MilestoneModel.id == milestone_id)
            .values(status="DISPUTED")
        )
        await db_session.execute(
            sa_update(GigModel)
            .where(GigModel.id == gig_id)
            .values(contract_address="0xABCDEF1234567890AbcdEF1234567890aBcdef12")
        )
        await db_session.flush()

        resp = await client.get(
            f"/v1/milestones/{milestone_id}/release-tx",
            headers=_auth(client_token),
        )

        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "MILESTONE_DISPUTED"


# ---------------------------------------------------------------------------
# POST /confirm-release
# ---------------------------------------------------------------------------


async def _insert_escrow_contract(db_session: AsyncSession, gig_id: str) -> None:
    """Insert a minimal EscrowContractModel row so confirm_release can proceed."""
    import uuid

    db_session.add(
        EscrowContractModel(
            id=str(uuid.uuid4()),
            gig_id=gig_id,
            contract_address="0xABCDEF1234567890AbcdEF1234567890aBcdef12",
        )
    )
    await db_session.flush()


class TestConfirmReleaseEndpoint:
    @pytest.mark.asyncio
    async def test_confirm_sets_paid(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        (
            client_token,
            _,
            gig_id,
            milestone_id,
        ) = await _setup_gig_with_milestone_under_review(client, db_session)
        await db_session.execute(
            sa_update(MilestoneModel)
            .where(MilestoneModel.id == milestone_id)
            .values(status="APPROVED")
        )
        await _insert_escrow_contract(db_session, gig_id)

        resp = await client.post(
            f"/v1/milestones/{milestone_id}/confirm-release",
            json={"tx_hash": "0xdeadbeef1234"},
            headers=_auth(client_token),
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "PAID"

    @pytest.mark.asyncio
    async def test_confirm_no_escrow_contract_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token, _, _, milestone_id = await _setup_gig_with_milestone_under_review(
            client, db_session
        )
        await db_session.execute(
            sa_update(MilestoneModel)
            .where(MilestoneModel.id == milestone_id)
            .values(status="APPROVED")
        )
        await db_session.flush()
        # No EscrowContractModel inserted

        resp = await client.post(
            f"/v1/milestones/{milestone_id}/confirm-release",
            json={"tx_hash": "0xdeadbeef1234"},
            headers=_auth(client_token),
        )

        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "NO_CONTRACT_ADDRESS"

    @pytest.mark.asyncio
    async def test_confirm_requires_client_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        (
            _,
            freelancer_token,
            _,
            milestone_id,
        ) = await _setup_gig_with_milestone_under_review(client, db_session)

        resp = await client.post(
            f"/v1/milestones/{milestone_id}/confirm-release",
            json={"tx_hash": "0xdeadbeef"},
            headers=_auth(freelancer_token),
        )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_confirm_not_approved_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token, _, _, milestone_id = await _setup_gig_with_milestone_under_review(
            client, db_session
        )
        # Status is UNDER_REVIEW at this point

        resp = await client.post(
            f"/v1/milestones/{milestone_id}/confirm-release",
            json={"tx_hash": "0xdeadbeef"},
            headers=_auth(client_token),
        )

        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "MILESTONE_NOT_APPROVED"
