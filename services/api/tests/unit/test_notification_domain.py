"""Unit tests for domain/notification.py."""

import json

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infra.database import Base
from src.infra.models import UserModel
from src.domain.notification import (
    NotificationError,
    create_notification,
    get_unread_count,
    list_notifications,
    mark_all_read,
    mark_read,
)

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        # Create a test user
        user = UserModel(
            id="user-1",
            email="test@example.com",
            name="Test User",
            role="USER_ROLE_FREELANCER",
        )
        session.add(user)
        user2 = UserModel(
            id="user-2",
            email="client@example.com",
            name="Client User",
            role="USER_ROLE_CLIENT",
        )
        session.add(user2)
        await session.commit()
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


class TestCreateNotification:
    async def test_create_notification_success(self, db: AsyncSession):
        notif = await create_notification(
            db,
            user_id="user-1",
            notification_type="NOTIFICATION_TYPE_PROPOSAL_ACCEPTED",
            payload={"gig_id": "gig-1", "proposal_id": "prop-1"},
        )
        assert notif.id is not None
        assert notif.user_id == "user-1"
        assert notif.type == "NOTIFICATION_TYPE_PROPOSAL_ACCEPTED"
        assert json.loads(notif.payload_json)["gig_id"] == "gig-1"
        assert notif.read_at is None

    async def test_create_notification_invalid_type(self, db: AsyncSession):
        with pytest.raises(NotificationError) as exc_info:
            await create_notification(
                db,
                user_id="user-1",
                notification_type="INVALID_TYPE",
                payload={},
            )
        assert exc_info.value.code == "INVALID_TYPE"


class TestListNotifications:
    async def test_list_empty(self, db: AsyncSession):
        notifs, unread = await list_notifications(db, "user-1")
        assert notifs == []
        assert unread == 0

    async def test_list_with_notifications(self, db: AsyncSession):
        await create_notification(
            db, "user-1", "NOTIFICATION_TYPE_PROPOSAL_ACCEPTED", {"gig_id": "g1"}
        )
        await create_notification(
            db, "user-1", "NOTIFICATION_TYPE_FUNDS_RELEASED", {"gig_id": "g2"}
        )
        await db.commit()

        notifs, unread = await list_notifications(db, "user-1")
        assert len(notifs) == 2
        assert unread == 2

    async def test_list_unread_only(self, db: AsyncSession):
        n1 = await create_notification(
            db, "user-1", "NOTIFICATION_TYPE_PROPOSAL_ACCEPTED", {"gig_id": "g1"}
        )
        await create_notification(
            db, "user-1", "NOTIFICATION_TYPE_FUNDS_RELEASED", {"gig_id": "g2"}
        )
        await db.commit()

        # Mark one as read
        await mark_read(db, n1.id, "user-1")
        await db.commit()

        notifs, unread = await list_notifications(db, "user-1", unread_only=True)
        assert len(notifs) == 1
        assert unread == 1

    async def test_list_pagination(self, db: AsyncSession):
        for i in range(5):
            await create_notification(
                db,
                "user-1",
                "NOTIFICATION_TYPE_GIG_FUNDED",
                {"gig_id": f"g{i}"},
            )
        await db.commit()

        notifs, unread = await list_notifications(db, "user-1", limit=2, offset=0)
        assert len(notifs) == 2
        assert unread == 5

        notifs2, _ = await list_notifications(db, "user-1", limit=2, offset=2)
        assert len(notifs2) == 2

    async def test_list_user_isolation(self, db: AsyncSession):
        await create_notification(
            db, "user-1", "NOTIFICATION_TYPE_GIG_FUNDED", {"gig_id": "g1"}
        )
        await create_notification(
            db, "user-2", "NOTIFICATION_TYPE_GIG_FUNDED", {"gig_id": "g2"}
        )
        await db.commit()

        notifs, unread = await list_notifications(db, "user-1")
        assert len(notifs) == 1
        assert unread == 1


class TestMarkRead:
    async def test_mark_read_success(self, db: AsyncSession):
        notif = await create_notification(
            db, "user-1", "NOTIFICATION_TYPE_GIG_FUNDED", {"gig_id": "g1"}
        )
        await db.commit()

        updated = await mark_read(db, notif.id, "user-1")
        assert updated.read_at is not None

    async def test_mark_read_idempotent(self, db: AsyncSession):
        notif = await create_notification(
            db, "user-1", "NOTIFICATION_TYPE_GIG_FUNDED", {"gig_id": "g1"}
        )
        await db.commit()

        first = await mark_read(db, notif.id, "user-1")
        await db.commit()
        second = await mark_read(db, notif.id, "user-1")
        assert first.read_at == second.read_at

    async def test_mark_read_not_found(self, db: AsyncSession):
        with pytest.raises(NotificationError) as exc_info:
            await mark_read(db, "nonexistent-id", "user-1")
        assert exc_info.value.code == "NOTIFICATION_NOT_FOUND"

    async def test_mark_read_wrong_user(self, db: AsyncSession):
        notif = await create_notification(
            db, "user-1", "NOTIFICATION_TYPE_GIG_FUNDED", {"gig_id": "g1"}
        )
        await db.commit()

        with pytest.raises(NotificationError) as exc_info:
            await mark_read(db, notif.id, "user-2")
        assert exc_info.value.code == "FORBIDDEN"


class TestMarkAllRead:
    async def test_mark_all_read(self, db: AsyncSession):
        await create_notification(
            db, "user-1", "NOTIFICATION_TYPE_GIG_FUNDED", {"gig_id": "g1"}
        )
        await create_notification(
            db, "user-1", "NOTIFICATION_TYPE_PROPOSAL_ACCEPTED", {"gig_id": "g2"}
        )
        await db.commit()

        notifs, unread = await mark_all_read(db, "user-1")
        assert unread == 0
        for n in notifs:
            assert n.read_at is not None

    async def test_mark_all_read_empty(self, db: AsyncSession):
        notifs, unread = await mark_all_read(db, "user-1")
        assert notifs == []
        assert unread == 0


class TestGetUnreadCount:
    async def test_unread_count(self, db: AsyncSession):
        await create_notification(
            db, "user-1", "NOTIFICATION_TYPE_GIG_FUNDED", {"gig_id": "g1"}
        )
        await create_notification(
            db, "user-1", "NOTIFICATION_TYPE_PROPOSAL_ACCEPTED", {"gig_id": "g2"}
        )
        await db.commit()

        count = await get_unread_count(db, "user-1")
        assert count == 2

        # Mark one read
        notifs, _ = await list_notifications(db, "user-1")
        await mark_read(db, notifs[0].id, "user-1")
        await db.commit()

        count = await get_unread_count(db, "user-1")
        assert count == 1
