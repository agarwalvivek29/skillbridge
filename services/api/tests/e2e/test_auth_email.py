"""E2E tests for email auth: POST /v1/auth/register and POST /v1/auth/login."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRegister:
    async def test_register_returns_201_with_token(self, client: AsyncClient):
        response = await client.post(
            "/v1/auth/register",
            json={"email": "alice@example.com", "password": "password123", "name": "Alice"},
        )
        assert response.status_code == 201
        body = response.json()
        assert "token" in body
        assert len(body["token"]) > 0
        assert body["user"]["email"] == "alice@example.com"
        assert body["user"]["name"] == "Alice"
        assert "USER_STATUS_ACTIVE" in body["user"]["status"]
        assert "USER_ROLE_MEMBER" in body["user"]["role"]
        assert "password" not in body
        assert "password_hash" not in str(body)

    async def test_register_duplicate_email_returns_409(self, client: AsyncClient):
        await client.post(
            "/v1/auth/register",
            json={"email": "dup@example.com", "password": "password123", "name": "Dup"},
        )
        response = await client.post(
            "/v1/auth/register",
            json={"email": "dup@example.com", "password": "password456", "name": "Dup2"},
        )
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "EMAIL_ALREADY_EXISTS"

    async def test_register_short_password_returns_422(self, client: AsyncClient):
        response = await client.post(
            "/v1/auth/register",
            json={"email": "short@example.com", "password": "abc", "name": "Short"},
        )
        assert response.status_code == 422

    async def test_register_invalid_email_returns_422(self, client: AsyncClient):
        response = await client.post(
            "/v1/auth/register",
            json={"email": "not-an-email", "password": "password123", "name": "Bad"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    async def test_login_valid_credentials_returns_200_with_token(self, client: AsyncClient):
        await client.post(
            "/v1/auth/register",
            json={"email": "login@example.com", "password": "pass1234", "name": "Login"},
        )
        response = await client.post(
            "/v1/auth/login",
            json={"email": "login@example.com", "password": "pass1234"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "token" in body
        assert body["user"]["email"] == "login@example.com"

    async def test_login_wrong_password_returns_401(self, client: AsyncClient):
        await client.post(
            "/v1/auth/register",
            json={"email": "wp@example.com", "password": "correct123", "name": "WP"},
        )
        response = await client.post(
            "/v1/auth/login",
            json={"email": "wp@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"

    async def test_login_unknown_email_returns_401(self, client: AsyncClient):
        response = await client.post(
            "/v1/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"
