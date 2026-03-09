"""
api/notification.py — Notification endpoints.

Endpoints:
  GET    /v1/notifications              list notifications (paginated, with unread_count)
  GET    /v1/notifications/stream       SSE stream for real-time bell updates
  POST   /v1/notifications/{id}/read    mark single notification read
  POST   /v1/notifications/read-all     mark all notifications read
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from src.domain.notification import (
    NotificationError,
    get_unread_count,
    list_notifications,
    mark_all_read,
    mark_read,
)
from src.infra.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])

# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class NotificationOut(BaseModel):
    id: str
    user_id: str
    type: str
    payload_json: str
    read_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListOut(BaseModel):
    notifications: list[NotificationOut]
    unread_count: int


class MarkReadOut(BaseModel):
    notification: NotificationOut


class MarkAllReadOut(BaseModel):
    notifications: list[NotificationOut]
    unread_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_auth(request: Request) -> str:
    """Extract user_id from request state. Returns user_id."""
    user_id: str = getattr(request.state, "user_id", "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required"},
        )
    return user_id


def _handle_notification_error(exc: NotificationError) -> HTTPException:
    status_map = {
        "NOTIFICATION_NOT_FOUND": 404,
        "FORBIDDEN": 403,
        "INVALID_TYPE": 400,
    }
    http_status = status_map.get(exc.code, 400)
    return HTTPException(
        status_code=http_status,
        detail={"code": exc.code, "message": exc.message, "field_errors": []},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=NotificationListOut)
async def list_notifications_endpoint(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    unread: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> NotificationListOut:
    """List notifications for the authenticated user. Paginated with unread_count."""
    user_id = _require_auth(request)

    notifications, unread_count = await list_notifications(
        db, user_id, limit=limit, offset=offset, unread_only=unread
    )

    return NotificationListOut(
        notifications=[NotificationOut.model_validate(n) for n in notifications],
        unread_count=unread_count,
    )


@router.get("/stream")
async def notification_stream(
    request: Request,
    token: str = Query(..., description="JWT token for SSE auth"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    SSE stream that emits unread_count updates.

    EventSource does not support custom headers, so the JWT is passed
    as a query parameter `token`. The auth middleware handles header-based
    auth; for this endpoint, the token is decoded manually.

    Emits: `data: {"unread_count": N}` every 3 seconds if there are changes,
    or a keep-alive comment every 15 seconds.
    """
    from src.domain.auth import decode_access_token
    from jose import JWTError

    try:
        claims = decode_access_token(token)
        user_id = claims.get("sub", "")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token is invalid or expired"},
        )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Token has no subject"},
        )

    async def event_generator():
        last_count = -1
        heartbeat_counter = 0
        try:
            while True:
                if await request.is_disconnected():
                    break

                from src.infra.database import AsyncSessionLocal

                async with AsyncSessionLocal() as session:
                    count = await get_unread_count(session, user_id)

                if count != last_count:
                    last_count = count
                    yield f'data: {{"unread_count": {count}}}\n\n'
                    heartbeat_counter = 0
                else:
                    heartbeat_counter += 1
                    if heartbeat_counter >= 5:
                        yield ": keepalive\n\n"
                        heartbeat_counter = 0

                await asyncio.sleep(3)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{notification_id}/read", response_model=MarkReadOut)
async def mark_read_endpoint(
    notification_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> MarkReadOut:
    """Mark a single notification as read."""
    user_id = _require_auth(request)

    try:
        notification = await mark_read(db, notification_id, user_id)
    except NotificationError as exc:
        raise _handle_notification_error(exc)

    return MarkReadOut(notification=NotificationOut.model_validate(notification))


@router.post("/read-all", response_model=MarkAllReadOut)
async def mark_all_read_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> MarkAllReadOut:
    """Mark all notifications as read for the authenticated user."""
    user_id = _require_auth(request)

    notifications, unread_count = await mark_all_read(db, user_id)

    return MarkAllReadOut(
        notifications=[NotificationOut.model_validate(n) for n in notifications],
        unread_count=unread_count,
    )
