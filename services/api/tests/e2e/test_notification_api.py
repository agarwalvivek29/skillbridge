"""
E2E tests for notification endpoints.

Runs against in-memory SQLite via conftest.py fixture.
"""

from __future__ import annotations

import json
import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.models import NotificationModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_USER_PAYLOAD = {
    "email": "notif-user@example.com",
    "password": "strongPass1",
    "name": "Notif User",
    "role": "USER_ROLE_FREELANCER",
}


async def _register_user(client: AsyncClient, payload: dict) -> tuple[str, str]:
    """Register a user and return (user_id, token)."""
    resp = await client.post("/v1/auth/email/register", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return data["user_id"], data["access_token"]


async def _seed_notifications(
    db_session: AsyncSession, user_id: str, count: int = 3
) -> list[str]:
    """Insert notifications directly and return their IDs."""
    ids = []
    for i in range(count):
        notif_id = str(uuid.uuid4())
        notif = NotificationModel(
            id=notif_id,
            user_id=user_id,
            type="NOTIFICATION_TYPE_PROPOSAL_ACCEPTED",
            payload_json=json.dumps({"gig_id": f"gig-{i}"}),
        )
        db_session.add(notif)
        ids.append(notif_id)
    await db_session.commit()
    return ids


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestListNotifications:
    async def test_list_empty(self, client: AsyncClient):
        user_id, token = await _register_user(client, _USER_PAYLOAD)
        resp = await client.get(
            "/v1/notifications",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["notifications"] == []
        assert data["unread_count"] == 0

    async def test_list_with_notifications(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user_id, token = await _register_user(client, _USER_PAYLOAD)
        await _seed_notifications(db_session, user_id, count=3)

        resp = await client.get(
            "/v1/notifications",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["notifications"]) == 3
        assert data["unread_count"] == 3

    async def test_list_unread_filter(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user_id, token = await _register_user(client, _USER_PAYLOAD)
        ids = await _seed_notifications(db_session, user_id, count=3)

        # Mark one as read
        resp = await client.post(
            f"/v1/notifications/{ids[0]}/read",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        # Filter unread only
        resp = await client.get(
            "/v1/notifications?unread=true",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["notifications"]) == 2
        assert data["unread_count"] == 2

    async def test_list_pagination(self, client: AsyncClient, db_session: AsyncSession):
        user_id, token = await _register_user(client, _USER_PAYLOAD)
        await _seed_notifications(db_session, user_id, count=5)

        resp = await client.get(
            "/v1/notifications?limit=2&offset=0",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["notifications"]) == 2
        assert data["unread_count"] == 5

    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get("/v1/notifications")
        assert resp.status_code == 401


class TestMarkRead:
    async def test_mark_read_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user_id, token = await _register_user(client, _USER_PAYLOAD)
        ids = await _seed_notifications(db_session, user_id, count=1)

        resp = await client.post(
            f"/v1/notifications/{ids[0]}/read",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["notification"]["read_at"] is not None

    async def test_mark_read_not_found(self, client: AsyncClient):
        _, token = await _register_user(client, _USER_PAYLOAD)
        resp = await client.post(
            "/v1/notifications/nonexistent-id/read",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_mark_read_wrong_user(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user1_id, _ = await _register_user(client, _USER_PAYLOAD)
        ids = await _seed_notifications(db_session, user1_id, count=1)

        # Register a second user
        user2_payload = {
            "email": "other@example.com",
            "password": "strongPass1",
            "name": "Other User",
            "role": "USER_ROLE_FREELANCER",
        }
        _, token2 = await _register_user(client, user2_payload)

        resp = await client.post(
            f"/v1/notifications/{ids[0]}/read",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp.status_code == 403


class TestMarkAllRead:
    async def test_mark_all_read_success(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        user_id, token = await _register_user(client, _USER_PAYLOAD)
        await _seed_notifications(db_session, user_id, count=3)

        resp = await client.post(
            "/v1/notifications/read-all",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["unread_count"] == 0
        for n in data["notifications"]:
            assert n["read_at"] is not None

    async def test_mark_all_read_empty(self, client: AsyncClient):
        _, token = await _register_user(client, _USER_PAYLOAD)
        resp = await client.post(
            "/v1/notifications/read-all",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["notifications"] == []
        assert data["unread_count"] == 0
