"""notification.py — Notification endpoints."""

import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.database import get_db
from src.infra.models import NotificationModel

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: str
    user_id: str
    type: str
    payload_json: str
    read_at: str | None
    created_at: str


class NotificationsResponse(BaseModel):
    notifications: list[NotificationOut]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("", response_model=NotificationsResponse)
async def list_notifications(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    unread: bool = Query(False),
    db: AsyncSession = Depends(get_db),
) -> NotificationsResponse:
    user_id = request.state.user_id

    where = [NotificationModel.user_id == user_id]
    if unread:
        where.append(NotificationModel.read_at.is_(None))

    count_q = select(func.count()).select_from(NotificationModel).where(*where)
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(NotificationModel)
        .where(*where)
        .order_by(NotificationModel.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    rows = (await db.execute(q)).scalars().all()

    return NotificationsResponse(
        notifications=[
            NotificationOut(
                id=r.id,
                user_id=r.user_id,
                type=r.type,
                payload_json=r.payload_json,
                read_at=r.read_at.isoformat() if r.read_at else None,
                created_at=r.created_at.isoformat(),
            )
            for r in rows
        ],
        total=total,
        page=page,
        page_size=limit,
        total_pages=max(1, math.ceil(total / limit)),
    )


@router.put("/read-all")
async def mark_all_read(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await db.execute(
        update(NotificationModel)
        .where(
            NotificationModel.user_id == request.state.user_id,
            NotificationModel.read_at.is_(None),
        )
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"ok": True}


@router.put("/{notification_id}/read")
async def mark_read(
    notification_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await db.execute(
        update(NotificationModel)
        .where(
            NotificationModel.id == notification_id,
            NotificationModel.user_id == request.state.user_id,
        )
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return {"ok": True}
