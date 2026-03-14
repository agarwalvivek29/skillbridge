"""
E2E tests for:
  GET  /v1/milestones/{milestone_id}         single milestone with gig context
  GET  /v1/gigs/{gig_id}/escrow-tx           escrow deposit tx data
  POST /v1/gigs/{gig_id}/confirm-escrow      confirm escrow funded on-chain

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
    "email": "client-escrow@example.com",
    "password": "strongPass1",
    "name": "Escrow Client",
    "role": "USER_ROLE_CLIENT",
}

_FREELANCER_PAYLOAD = {
    "email": "freelancer-escrow@example.com",
    "password": "strongPass1",
    "name": "Escrow Freelancer",
    "role": "USER_ROLE_FREELANCER",
}


def _valid_gig_payload() -> dict:
    return {
        "title": "Escrow test gig",
        "description": "Testing escrow endpoints",
        "total_amount": "5000",
        "currency": "ETH",
        "required_skills": ["Rust"],
        "milestones": [
            {
                "title": "Phase 1",
                "description": "Initial work",
                "acceptance_criteria": "- Tests pass",
                "amount": "3000",
                "order": 1,
            },
            {
                "title": "Phase 2",
                "description": "Final work",
                "acceptance_criteria": "- Deployed",
                "amount": "2000",
                "order": 2,
            },
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


async def _create_gig(client: AsyncClient, token: str) -> dict:
    resp = await client.post(
        "/v1/gigs", json=_valid_gig_payload(), headers=_auth(token)
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# GET /v1/milestones/{milestone_id}
# ---------------------------------------------------------------------------


class TestGetMilestoneEndpoint:
    @pytest.mark.asyncio
    async def test_returns_milestone_with_gig_context(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        token, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        gig = await _create_gig(client, token)
        milestone_id = gig["milestones"][0]["id"]

        resp = await client.get(f"/v1/milestones/{milestone_id}", headers=_auth(token))

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == milestone_id
        assert data["gig_id"] == gig["id"]
        assert data["gig_title"] == gig["title"]
        assert data["client_id"] == gig["client_id"]
        assert data["freelancer_id"] is None
        assert data["title"] == "Phase 1"
        assert data["amount"] == "3000"
        assert data["order"] == 1

    @pytest.mark.asyncio
    async def test_returns_milestone_with_freelancer_context(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        token, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        _, freelancer_id = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        gig = await _create_gig(client, token)
        milestone_id = gig["milestones"][0]["id"]

        await db_session.execute(
            sa_update(GigModel)
            .where(GigModel.id == gig["id"])
            .values(freelancer_id=freelancer_id, status="IN_PROGRESS")
        )
        await db_session.flush()

        resp = await client.get(f"/v1/milestones/{milestone_id}", headers=_auth(token))

        assert resp.status_code == 200, resp.text
        assert resp.json()["freelancer_id"] == freelancer_id

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient, db_session: AsyncSession):
        token, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        gig = await _create_gig(client, token)
        milestone_id = gig["milestones"][0]["id"]

        resp = await client.get(f"/v1/milestones/{milestone_id}")

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_not_found(self, client: AsyncClient, db_session: AsyncSession):
        token, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)

        resp = await client.get(
            "/v1/milestones/00000000-0000-0000-0000-000000000000",
            headers=_auth(token),
        )

        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "MILESTONE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_freelancer_can_access(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Any authenticated user (not just CLIENT) can read a milestone."""
        client_token, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token, _ = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        gig = await _create_gig(client, client_token)
        milestone_id = gig["milestones"][0]["id"]

        resp = await client.get(
            f"/v1/milestones/{milestone_id}", headers=_auth(freelancer_token)
        )

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /v1/gigs/{gig_id}/escrow-tx
# ---------------------------------------------------------------------------


class TestGetEscrowTxEndpoint:
    @pytest.mark.asyncio
    async def test_returns_escrow_tx_data(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch
    ):
        token, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        gig = await _create_gig(client, token)

        from src.config import settings

        monkeypatch.setattr(
            settings, "escrow_program_id", "EscrowProgramId1111111111111111111111111111"
        )

        resp = await client.get(f"/v1/gigs/{gig['id']}/escrow-tx", headers=_auth(token))

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["program_id"] == "EscrowProgramId1111111111111111111111111111"
        assert data["escrow_seeds"][0] == "escrow"
        assert data["amount"] == "5000"
        assert data["currency"] == "ETH"
        assert data["token_mint"] is None

    @pytest.mark.asyncio
    async def test_usdc_gig_includes_token_mint(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch
    ):
        token, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        payload = _valid_gig_payload()
        payload["currency"] = "USDC"
        payload["token_address"] = "0x1234567890abcdef1234567890abcdef12345678"
        resp = await client.post("/v1/gigs", json=payload, headers=_auth(token))
        assert resp.status_code == 201, resp.text
        gig = resp.json()

        from src.config import settings

        monkeypatch.setattr(
            settings, "escrow_program_id", "EscrowProgramId1111111111111111111111111111"
        )

        resp = await client.get(f"/v1/gigs/{gig['id']}/escrow-tx", headers=_auth(token))

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["currency"] == "USDC"
        assert data["token_mint"] == "0x1234567890abcdef1234567890abcdef12345678"

    @pytest.mark.asyncio
    async def test_requires_client_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token, _ = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        gig = await _create_gig(client, client_token)

        resp = await client.get(
            f"/v1/gigs/{gig['id']}/escrow-tx", headers=_auth(freelancer_token)
        )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_requires_gig_owner(
        self, client: AsyncClient, db_session: AsyncSession, monkeypatch
    ):
        token1, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        other_client_payload = {
            "email": "other-client-escrow@example.com",
            "password": "strongPass1",
            "name": "Other Client",
            "role": "USER_ROLE_CLIENT",
        }
        token2, _ = await _register_and_get_token(client, other_client_payload)
        gig = await _create_gig(client, token1)

        from src.config import settings

        monkeypatch.setattr(
            settings, "escrow_program_id", "EscrowProgramId1111111111111111111111111111"
        )

        resp = await client.get(
            f"/v1/gigs/{gig['id']}/escrow-tx", headers=_auth(token2)
        )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_gig_not_found(self, client: AsyncClient, db_session: AsyncSession):
        token, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)

        resp = await client.get(
            "/v1/gigs/00000000-0000-0000-0000-000000000000/escrow-tx",
            headers=_auth(token),
        )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient, db_session: AsyncSession):
        resp = await client.get(
            "/v1/gigs/00000000-0000-0000-0000-000000000000/escrow-tx"
        )

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /v1/gigs/{gig_id}/confirm-escrow
# ---------------------------------------------------------------------------


class TestConfirmEscrowEndpoint:
    @pytest.mark.asyncio
    async def test_confirm_creates_escrow_and_updates_gig(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        token, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        gig = await _create_gig(client, token)

        resp = await client.post(
            f"/v1/gigs/{gig['id']}/confirm-escrow",
            json={
                "tx_signature": "5UzVrMBKdLk...",
                "chain_address": "EscrowAddr11111111111111111111111111111111",
            },
            headers=_auth(token),
        )

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "OPEN"
        assert data["escrow_pda"] == "EscrowAddr11111111111111111111111111111111"

    @pytest.mark.asyncio
    async def test_confirm_idempotent_on_open_gig(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Confirming escrow on an already OPEN gig should still work (re-confirm)."""
        token, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        gig = await _create_gig(client, token)

        body = {
            "tx_signature": "5UzVrMBKdLk...",
            "chain_address": "EscrowAddr11111111111111111111111111111111",
        }

        resp1 = await client.post(
            f"/v1/gigs/{gig['id']}/confirm-escrow",
            json=body,
            headers=_auth(token),
        )
        assert resp1.status_code == 200

        # Second confirm with updated address
        body["chain_address"] = "EscrowAddr22222222222222222222222222222222"
        resp2 = await client.post(
            f"/v1/gigs/{gig['id']}/confirm-escrow",
            json=body,
            headers=_auth(token),
        )
        assert resp2.status_code == 200
        assert (
            resp2.json()["escrow_pda"] == "EscrowAddr22222222222222222222222222222222"
        )

    @pytest.mark.asyncio
    async def test_confirm_rejects_in_progress_gig(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        token, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        gig = await _create_gig(client, token)

        await db_session.execute(
            sa_update(GigModel)
            .where(GigModel.id == gig["id"])
            .values(status="IN_PROGRESS")
        )
        await db_session.flush()

        resp = await client.post(
            f"/v1/gigs/{gig['id']}/confirm-escrow",
            json={
                "tx_signature": "5UzVrMBKdLk...",
                "chain_address": "EscrowAddr11111111111111111111111111111111",
            },
            headers=_auth(token),
        )

        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "GIG_NOT_FUNDABLE"

    @pytest.mark.asyncio
    async def test_requires_client_role(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        client_token, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        freelancer_token, _ = await _register_and_get_token(client, _FREELANCER_PAYLOAD)
        gig = await _create_gig(client, client_token)

        resp = await client.post(
            f"/v1/gigs/{gig['id']}/confirm-escrow",
            json={
                "tx_signature": "sig",
                "chain_address": "addr",
            },
            headers=_auth(freelancer_token),
        )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_requires_gig_owner(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        token1, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)
        other = {
            "email": "other-confirm@example.com",
            "password": "strongPass1",
            "name": "Other",
            "role": "USER_ROLE_CLIENT",
        }
        token2, _ = await _register_and_get_token(client, other)
        gig = await _create_gig(client, token1)

        resp = await client.post(
            f"/v1/gigs/{gig['id']}/confirm-escrow",
            json={
                "tx_signature": "sig",
                "chain_address": "addr",
            },
            headers=_auth(token2),
        )

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_gig_not_found(self, client: AsyncClient, db_session: AsyncSession):
        token, _ = await _register_and_get_token(client, _CLIENT_PAYLOAD)

        resp = await client.post(
            "/v1/gigs/00000000-0000-0000-0000-000000000000/confirm-escrow",
            json={
                "tx_signature": "sig",
                "chain_address": "addr",
            },
            headers=_auth(token),
        )

        assert resp.status_code == 404
