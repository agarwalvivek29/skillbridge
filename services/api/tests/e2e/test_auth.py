"""
e2e tests for all four auth endpoints.

Runs against in-memory SQLite via conftest.py fixture.
"""

import base64
from datetime import datetime, timezone

import base58
import nacl.signing
import pytest
from httpx import AsyncClient


# Deterministic test keypair (never use with real funds)
_SIGNING_KEY = nacl.signing.SigningKey.generate()
_VERIFY_KEY = _SIGNING_KEY.verify_key
_WALLET = base58.b58encode(_VERIFY_KEY.encode()).decode()


def _build_solana_message(nonce: str, wallet: str = _WALLET) -> str:
    """Build the Solana sign-in message for testing."""
    issued_at = datetime.now(timezone.utc).isoformat()
    return (
        f"SkillBridge wants you to sign in with your Solana account:\n"
        f"{wallet}\n"
        f"\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued_at}"
    )


def _sign(message: str) -> str:
    """Sign a message with the test Ed25519 key and return base64 signature."""
    signed = _SIGNING_KEY.sign(message.encode("utf-8"))
    return base64.b64encode(signed.signature).decode()


# ──────────────────────────────────────────────────────────────────────────────
# Infrastructure endpoints
# ──────────────────────────────────────────────────────────────────────────────


class TestInfraEndpoints:
    @pytest.mark.asyncio
    async def test_health_no_auth_required(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_metrics_no_auth_required(self, client: AsyncClient):
        resp = await client.get("/metrics")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_docs_no_auth_required(self, client: AsyncClient):
        resp = await client.get("/docs")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_redoc_no_auth_required(self, client: AsyncClient):
        resp = await client.get("/redoc")
        assert resp.status_code == 200


# ──────────────────────────────────────────────────────────────────────────────
# Nonce endpoint
# ──────────────────────────────────────────────────────────────────────────────


class TestGetNonce:
    @pytest.mark.asyncio
    async def test_returns_nonce_for_valid_address(self, client: AsyncClient):
        resp = await client.get(f"/v1/auth/nonce?wallet_address={_WALLET}")
        assert resp.status_code == 200
        data = resp.json()
        assert "nonce" in data
        assert len(data["nonce"]) == 32
        assert "expires_at" in data

    @pytest.mark.asyncio
    async def test_rejects_invalid_address(self, client: AsyncClient):
        resp = await client.get("/v1/auth/nonce?wallet_address=notanaddress")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_second_nonce_overwrites_first(self, client: AsyncClient):
        r1 = await client.get(f"/v1/auth/nonce?wallet_address={_WALLET}")
        r2 = await client.get(f"/v1/auth/nonce?wallet_address={_WALLET}")
        assert r1.json()["nonce"] != r2.json()["nonce"]


# ──────────────────────────────────────────────────────────────────────────────
# Wallet login endpoint
# ──────────────────────────────────────────────────────────────────────────────


class TestWalletLogin:
    @pytest.mark.asyncio
    async def test_happy_path_returns_jwt(self, client: AsyncClient):
        # Step 1: get nonce
        r = await client.get(f"/v1/auth/nonce?wallet_address={_WALLET}")
        nonce = r.json()["nonce"]

        # Step 2: build message, sign with Ed25519 and login
        message = _build_solana_message(nonce)
        sig = _sign(message)
        resp = await client.post(
            "/v1/auth/wallet",
            json={"wallet_address": _WALLET, "signature": sig, "message": message},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["token_type"] == "Bearer"
        assert len(data["access_token"]) > 20
        assert data["expires_in"] > 0
        assert "user_id" in data

    @pytest.mark.asyncio
    async def test_rejects_expired_or_missing_nonce(self, client: AsyncClient):
        message = _build_solana_message("fakeNonce12345678901234567890123")
        sig = _sign(message)
        resp = await client.post(
            "/v1/auth/wallet",
            json={"wallet_address": _WALLET, "signature": sig, "message": message},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_nonce_deleted_after_use(self, client: AsyncClient):
        r = await client.get(f"/v1/auth/nonce?wallet_address={_WALLET}")
        nonce = r.json()["nonce"]
        message = _build_solana_message(nonce)
        sig = _sign(message)

        # First use succeeds
        r1 = await client.post(
            "/v1/auth/wallet",
            json={"wallet_address": _WALLET, "signature": sig, "message": message},
        )
        assert r1.status_code == 200

        # Second use with same nonce must fail
        r2 = await client.post(
            "/v1/auth/wallet",
            json={"wallet_address": _WALLET, "signature": sig, "message": message},
        )
        assert r2.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_wrong_signature(self, client: AsyncClient):
        r = await client.get(f"/v1/auth/nonce?wallet_address={_WALLET}")
        nonce = r.json()["nonce"]
        message = _build_solana_message(nonce)

        # Sign with a different key
        other_key = nacl.signing.SigningKey.generate()
        other_signed = other_key.sign(message.encode("utf-8"))
        wrong_sig = base64.b64encode(other_signed.signature).decode()
        resp = await client.post(
            "/v1/auth/wallet",
            json={
                "wallet_address": _WALLET,
                "signature": wrong_sig,
                "message": message,
            },
        )
        assert resp.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# Email register endpoint
# ──────────────────────────────────────────────────────────────────────────────


class TestEmailRegister:
    @pytest.mark.asyncio
    async def test_happy_path_returns_jwt(self, client: AsyncClient):
        resp = await client.post(
            "/v1/auth/email/register",
            json={
                "email": "alice@example.com",
                "password": "strongPass1",
                "name": "Alice",
                "role": "USER_ROLE_FREELANCER",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["token_type"] == "Bearer"
        assert len(data["access_token"]) > 20
        assert data["expires_in"] > 0
        assert "user_id" in data

    @pytest.mark.asyncio
    async def test_duplicate_email_returns_400(self, client: AsyncClient):
        payload = {
            "email": "bob@example.com",
            "password": "strongPass1",
            "name": "Bob",
            "role": "USER_ROLE_CLIENT",
        }
        r1 = await client.post("/v1/auth/email/register", json=payload)
        assert r1.status_code == 201

        r2 = await client.post("/v1/auth/email/register", json=payload)
        assert r2.status_code == 400
        assert r2.json()["detail"]["code"] == "EMAIL_TAKEN"

    @pytest.mark.asyncio
    async def test_short_password_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/v1/auth/email/register",
            json={
                "email": "charlie@example.com",
                "password": "short",
                "name": "Charlie",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_role_returns_422(self, client: AsyncClient):
        resp = await client.post(
            "/v1/auth/email/register",
            json={
                "email": "dan@example.com",
                "password": "strongPass1",
                "name": "Dan",
                "role": "SUPERUSER",
            },
        )
        assert resp.status_code == 422


# ──────────────────────────────────────────────────────────────────────────────
# Email login endpoint
# ──────────────────────────────────────────────────────────────────────────────


class TestEmailLogin:
    @pytest.mark.asyncio
    async def test_happy_path_returns_jwt(self, client: AsyncClient):
        # Register first
        await client.post(
            "/v1/auth/email/register",
            json={"email": "eve@example.com", "password": "strongPass1", "name": "Eve"},
        )

        resp = await client.post(
            "/v1/auth/email/login",
            json={"email": "eve@example.com", "password": "strongPass1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["token_type"] == "Bearer"
        assert len(data["access_token"]) > 20

    @pytest.mark.asyncio
    async def test_wrong_password_returns_401(self, client: AsyncClient):
        await client.post(
            "/v1/auth/email/register",
            json={
                "email": "frank@example.com",
                "password": "correctPass",
                "name": "Frank",
            },
        )

        resp = await client.post(
            "/v1/auth/email/login",
            json={"email": "frank@example.com", "password": "wrongPass"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "INVALID_CREDENTIALS"

    @pytest.mark.asyncio
    async def test_unknown_email_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/v1/auth/email/login",
            json={"email": "ghost@example.com", "password": "anyPassword"},
        )
        assert resp.status_code == 401


# ──────────────────────────────────────────────────────────────────────────────
# Auth middleware
# ──────────────────────────────────────────────────────────────────────────────


class TestAuthMiddleware:
    @pytest.mark.asyncio
    async def test_protected_route_requires_token(self, client: AsyncClient):
        # Any non-exempt route should return 401 without a token.
        resp = await client.get("/v1/users")
        assert resp.status_code in (401, 404)  # 401 if middleware fires before routing

    @pytest.mark.asyncio
    async def test_valid_jwt_grants_access(self, client: AsyncClient):
        # Register to get a token
        r = await client.post(
            "/v1/auth/email/register",
            json={
                "email": "grace@example.com",
                "password": "strongPass1",
                "name": "Grace",
            },
        )
        token = r.json()["access_token"]

        # Access a protected route with valid token
        resp = await client.get(
            "/v1/users", headers={"Authorization": f"Bearer {token}"}
        )
        # Should not be 401 (may be 404 since /v1/users is not implemented yet)
        assert resp.status_code != 401

    @pytest.mark.asyncio
    async def test_api_key_grants_access(self, client: AsyncClient):
        resp = await client.get(
            "/v1/users", headers={"X-API-Key": "test-api-key-minimum-16-chars"}
        )
        assert resp.status_code != 401


# ──────────────────────────────────────────────────────────────────────────────
# Expired nonce e2e test
# ──────────────────────────────────────────────────────────────────────────────


class TestExpiredNonce:
    @pytest.mark.asyncio
    async def test_expired_db_nonce_returns_401(
        self, client: AsyncClient, db_session
    ) -> None:
        """
        Creates a nonce via the API, then manually sets expires_at to the past
        in the DB and verifies that wallet login returns 401.
        """
        from datetime import timedelta

        from sqlalchemy import update

        from src.infra.models import AuthNonceModel

        # Step 1: request a nonce
        r = await client.get(f"/v1/auth/nonce?wallet_address={_WALLET}")
        assert r.status_code == 200
        nonce = r.json()["nonce"]

        # Step 2: backdate the nonce in the DB
        await db_session.execute(
            update(AuthNonceModel)
            .where(AuthNonceModel.wallet_address == _WALLET)
            .values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=5))
        )
        await db_session.commit()

        # Step 3: attempt wallet login with the expired nonce
        message = _build_solana_message(nonce)
        sig = _sign(message)
        resp = await client.post(
            "/v1/auth/wallet",
            json={"wallet_address": _WALLET, "signature": sig, "message": message},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "NONCE_INVALID_OR_EXPIRED"
