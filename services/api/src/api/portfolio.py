"""
api/portfolio.py — Portfolio item CRUD + S3 presigned URL endpoints.

All endpoints require authentication (JWT or API key) via AuthMiddleware.
Owner-mutating endpoints (PUT, DELETE) additionally enforce ownership (403).
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain import portfolio as portfolio_domain
from src.infra.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["portfolio"])


# ---------------------------------------------------------------------------
# Request / Response Pydantic models
# ---------------------------------------------------------------------------


class PortfolioItemResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str | None
    file_keys: list[str]
    external_url: str | None
    tags: list[str]
    verified_gig_id: str | None
    is_verified: bool
    created_at: str  # ISO-8601
    updated_at: str  # ISO-8601


class CreatePortfolioItemRequest(BaseModel):
    title: str
    description: str | None = None
    file_keys: list[str] = []
    external_url: str | None = None
    tags: list[str] = []
    verified_gig_id: str | None = None


class UpdatePortfolioItemRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    file_keys: list[str] | None = None
    external_url: str | None = None
    tags: list[str] | None = None


class GetUserPortfolioResponse(BaseModel):
    items: list[PortfolioItemResponse]


class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str = "application/octet-stream"


class PresignedUrlResponse(BaseModel):
    upload_url: str
    s3_key: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_dt(dt: datetime) -> str:
    """Format a datetime as ISO-8601 UTC string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


async def _build_response(
    db: AsyncSession,
    item,  # PortfolioItemModel
) -> PortfolioItemResponse:
    is_verified = await portfolio_domain.compute_is_verified(db, item.verified_gig_id)
    return PortfolioItemResponse(
        id=item.id,
        user_id=item.user_id,
        title=item.title,
        description=item.description,
        file_keys=item.file_keys or [],
        external_url=item.external_url,
        tags=item.tags or [],
        verified_gig_id=item.verified_gig_id,
        is_verified=is_verified,
        created_at=_fmt_dt(item.created_at),
        updated_at=_fmt_dt(item.updated_at),
    )


def _get_current_user_id(request: Request) -> str:
    """Extract authenticated user_id from request state (set by AuthMiddleware)."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required"},
        )
    return user_id


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/portfolio",
    response_model=PortfolioItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_portfolio_item(
    body: CreatePortfolioItemRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PortfolioItemResponse:
    """Create a new portfolio item for the authenticated user."""
    user_id = _get_current_user_id(request)
    item = await portfolio_domain.create_portfolio_item(
        db=db,
        user_id=user_id,
        title=body.title,
        description=body.description,
        file_keys=body.file_keys,
        external_url=body.external_url,
        tags=body.tags,
        verified_gig_id=body.verified_gig_id,
    )
    return await _build_response(db, item)


@router.get("/portfolio/{item_id}", response_model=PortfolioItemResponse)
async def get_portfolio_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
) -> PortfolioItemResponse:
    """Fetch a single portfolio item by id."""
    item = await portfolio_domain.get_portfolio_item(db, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Portfolio item not found"},
        )
    return await _build_response(db, item)


@router.put("/portfolio/{item_id}", response_model=PortfolioItemResponse)
async def update_portfolio_item(
    item_id: str,
    body: UpdatePortfolioItemRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PortfolioItemResponse:
    """Update a portfolio item. Only the owner may update."""
    user_id = _get_current_user_id(request)
    item = await portfolio_domain.get_portfolio_item(db, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Portfolio item not found"},
        )
    if item.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "You do not own this portfolio item",
            },
        )
    item = await portfolio_domain.update_portfolio_item(
        db=db,
        item=item,
        title=body.title,
        description=body.description,
        file_keys=body.file_keys,
        external_url=body.external_url,
        tags=body.tags,
    )
    return await _build_response(db, item)


@router.delete("/portfolio/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio_item(
    item_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a portfolio item. Only the owner may delete."""
    user_id = _get_current_user_id(request)
    item = await portfolio_domain.get_portfolio_item(db, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Portfolio item not found"},
        )
    if item.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "You do not own this portfolio item",
            },
        )
    await portfolio_domain.delete_portfolio_item(db, item)


@router.get("/users/{user_id}/portfolio", response_model=GetUserPortfolioResponse)
async def get_user_portfolio(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> GetUserPortfolioResponse:
    """Return all portfolio items for a user, ordered by created_at DESC."""
    items = await portfolio_domain.get_portfolio_items_for_user(db, user_id)
    responses = []
    for item in items:
        responses.append(await _build_response(db, item))
    return GetUserPortfolioResponse(items=responses)


@router.post("/portfolio/upload-url", response_model=PresignedUrlResponse)
async def get_upload_url(
    body: PresignedUrlRequest,
    request: Request,
) -> PresignedUrlResponse:
    """
    Generate a presigned S3 PUT URL for direct browser upload.
    The file is uploaded directly to S3 — it never passes through the API.
    Returns the S3 key (store this in file_keys when creating a portfolio item).
    """
    user_id = _get_current_user_id(request)
    s3_key = portfolio_domain.generate_s3_key(user_id, body.filename)

    try:
        from src.infra.s3 import generate_presigned_put_url

        upload_url = generate_presigned_put_url(
            s3_key=s3_key,
            content_type=body.content_type,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Failed to generate presigned URL for user_id=%s s3_key=%s: %s",
            user_id,
            s3_key,
            exc,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "S3_UNAVAILABLE",
                "message": "Could not generate upload URL. Try again later.",
            },
        )

    logger.info("presigned_url generated user_id=%s s3_key=%s", user_id, s3_key)
    return PresignedUrlResponse(upload_url=upload_url, s3_key=s3_key)
