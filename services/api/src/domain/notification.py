"""
domain/notification.py — Business logic for notifications.
No FastAPI imports. All side-effect-free helpers + DB-taking functions.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.email import send_notification_email
from src.infra.models import NotificationModel, UserModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid notification types (must match proto enum values)
# ---------------------------------------------------------------------------

VALID_NOTIFICATION_TYPES = {
    "NOTIFICATION_TYPE_GIG_FUNDED",
    "NOTIFICATION_TYPE_GIG_CANCELLED",
    "NOTIFICATION_TYPE_GIG_COMPLETED",
    "NOTIFICATION_TYPE_PROPOSAL_RECEIVED",
    "NOTIFICATION_TYPE_PROPOSAL_ACCEPTED",
    "NOTIFICATION_TYPE_PROPOSAL_REJECTED",
    "NOTIFICATION_TYPE_SUBMISSION_RECEIVED",
    "NOTIFICATION_TYPE_REVISION_REQUESTED",
    "NOTIFICATION_TYPE_MILESTONE_APPROVED",
    "NOTIFICATION_TYPE_FUNDS_RELEASED",
    "NOTIFICATION_TYPE_REVIEW_COMPLETE",
    "NOTIFICATION_TYPE_DISPUTE_RAISED",
    "NOTIFICATION_TYPE_DISPUTE_RESOLVED",
    "NOTIFICATION_TYPE_REVIEW_RECEIVED",
}


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class NotificationError(ValueError):
    """Raised when a notification operation fails a business rule."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Domain functions
# ---------------------------------------------------------------------------


async def create_notification(
    db: AsyncSession,
    user_id: str,
    notification_type: str,
    payload: dict,
) -> NotificationModel:
    """
    Create a notification for a user.

    This is the centralized helper that all domain functions should call
    to emit notifications. It validates the notification type and persists
    the record.

    Returns the created NotificationModel.
    """
    if notification_type not in VALID_NOTIFICATION_TYPES:
        raise NotificationError(
            "INVALID_TYPE",
            f"Unknown notification type: {notification_type}",
        )

    notification = NotificationModel(
        user_id=user_id,
        type=notification_type,
        payload_json=json.dumps(payload),
    )
    db.add(notification)
    await db.flush()

    logger.info(
        "notification created id=%s user_id=%s type=%s",
        notification.id,
        user_id,
        notification_type,
    )

    # Best-effort email delivery (never blocks notification creation)
    try:
        user_result = await db.execute(
            select(UserModel.email).where(UserModel.id == user_id)
        )
        user_email = user_result.scalar_one_or_none()
        if user_email:
            await send_notification_email(user_email, notification_type, payload)
    except Exception:
        logger.exception("failed to send notification email user_id=%s", user_id)

    return notification


async def list_notifications(
    db: AsyncSession,
    user_id: str,
    limit: int = 20,
    offset: int = 0,
    unread_only: bool = False,
) -> tuple[list[NotificationModel], int]:
    """
    Return paginated notifications for a user and the total unread count.

    - limit: max items per page (capped at 100)
    - offset: number of items to skip
    - unread_only: if True, return only notifications with read_at IS NULL
    """
    limit = min(limit, 100)

    where_clauses = [NotificationModel.user_id == user_id]
    if unread_only:
        where_clauses.append(NotificationModel.read_at.is_(None))

    result = await db.execute(
        select(NotificationModel)
        .where(*where_clauses)
        .order_by(NotificationModel.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    notifications = list(result.scalars().all())

    # Always return the total unread count (regardless of unread_only filter)
    unread_result = await db.execute(
        select(func.count())
        .select_from(NotificationModel)
        .where(
            NotificationModel.user_id == user_id,
            NotificationModel.read_at.is_(None),
        )
    )
    unread_count = unread_result.scalar_one()

    return notifications, unread_count


async def mark_read(
    db: AsyncSession,
    notification_id: str,
    user_id: str,
) -> NotificationModel:
    """
    Mark a single notification as read.

    Raises NotificationError if:
    - notification not found
    - notification does not belong to the user
    """
    result = await db.execute(
        select(NotificationModel).where(NotificationModel.id == notification_id)
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        raise NotificationError(
            "NOTIFICATION_NOT_FOUND",
            f"Notification {notification_id} not found",
        )
    if notification.user_id != user_id:
        raise NotificationError(
            "FORBIDDEN",
            "You cannot mark another user's notification as read",
        )

    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        await db.flush()

    # Re-fetch to get server-default timestamps correctly
    result = await db.execute(
        select(NotificationModel).where(NotificationModel.id == notification_id)
    )
    return result.scalar_one()


async def mark_all_read(
    db: AsyncSession,
    user_id: str,
) -> tuple[list[NotificationModel], int]:
    """
    Mark all unread notifications for a user as read.

    Returns the updated list of notifications and the new unread count (0).
    """
    now = datetime.now(timezone.utc)
    await db.execute(
        update(NotificationModel)
        .where(
            NotificationModel.user_id == user_id,
            NotificationModel.read_at.is_(None),
        )
        .values(read_at=now)
    )
    await db.flush()

    # Return updated list (most recent first)
    result = await db.execute(
        select(NotificationModel)
        .where(NotificationModel.user_id == user_id)
        .order_by(NotificationModel.created_at.desc())
    )
    notifications = list(result.scalars().all())

    return notifications, 0


async def get_unread_count(
    db: AsyncSession,
    user_id: str,
) -> int:
    """Return the count of unread notifications for a user."""
    result = await db.execute(
        select(func.count())
        .select_from(NotificationModel)
        .where(
            NotificationModel.user_id == user_id,
            NotificationModel.read_at.is_(None),
        )
    )
    return result.scalar_one()
