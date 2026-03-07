"""E2E tests for wallet auth: GET /v1/auth/nonce and POST /v1/auth/wallet."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestGetNonce:
    async def test_get_nonce_returns_nonce_and_expiry(self, client: AsyncClient):
        response = await client.get(
            "/v1/auth/nonce",
            params={"address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "nonce" in body
        assert len(body["nonce"]) == 64
        assert "expires_at" in body

    async def test_get_nonce_missing_address_returns_422(self, client: AsyncClient):
        response = await client.get("/v1/auth/nonce")
        assert response.status_code == 422


@pytest.mark.asyncio
class TestWalletLogin:
    ADDRESS = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

    async def test_valid_siwe_returns_token(self, client: AsyncClient):
        # Get a nonce
        nonce_resp = await client.get("/v1/auth/nonce", params={"address": self.ADDRESS})
        nonce = nonce_resp.json()["nonce"]

        # Mock the SIWE verification to succeed
        with patch("api.api.auth.verify_siwe_message", return_value=self.ADDRESS):
            with patch("api.api.auth.SiweMessage") as mock_siwe_cls:
                mock_msg = mock_siwe_cls.from_message.return_value
                mock_msg.nonce = nonce
                mock_msg.address = self.ADDRESS

                response = await client.post(
                    "/v1/auth/wallet",
                    json={
                        "message": (
                            f"example.com wants you to sign in with your Ethereum account:"
                            f"\n{self.ADDRESS}\n\nSign in to SkillBridge\n\nNonce: {nonce}"
                        ),
                        "signature": "0xmockedsignature",
                    },
                )

        assert response.status_code == 200
        body = response.json()
        assert "token" in body
        assert body["user"]["wallet_address"] == self.ADDRESS
        assert body["user"]["email"] is None or body["user"]["email"] == ""

    async def test_invalid_nonce_returns_400(self, client: AsyncClient):
        with patch("api.api.auth.SiweMessage") as mock_siwe_cls:
            mock_msg = mock_siwe_cls.from_message.return_value
            mock_msg.nonce = "nonexistent-nonce"
            mock_msg.address = self.ADDRESS

            response = await client.post(
                "/v1/auth/wallet",
                json={
                    "message": "...",
                    "signature": "0xsig",
                },
            )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "NONCE_EXPIRED"

    async def test_invalid_signature_returns_400(self, client: AsyncClient):
        nonce_resp = await client.get("/v1/auth/nonce", params={"address": self.ADDRESS})
        nonce = nonce_resp.json()["nonce"]

        from api.domain.siwe import InvalidSignatureError

        with patch(
            "api.api.auth.verify_siwe_message",
            side_effect=InvalidSignatureError("bad sig"),
        ):
            with patch("api.api.auth.SiweMessage") as mock_siwe_cls:
                mock_msg = mock_siwe_cls.from_message.return_value
                mock_msg.nonce = nonce
                mock_msg.address = self.ADDRESS

                response = await client.post(
                    "/v1/auth/wallet",
                    json={"message": "...", "signature": "0xbadsig"},
                )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "INVALID_SIGNATURE"
