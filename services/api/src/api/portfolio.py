"""
api/portfolio.py — Portfolio item endpoints.

Endpoints:
  GET    /v1/portfolio/{user_id}     list portfolio items for a user (public)
  POST   /v1/portfolio/upload-url    get S3 presigned PUT URL (auth required, FREELANCER role)
  POST   /v1/portfolio               create portfolio item (auth required, FREELANCER role)
  PUT    /v1/portfolio/{item_id}     update portfolio item (auth required, owner only)
  DELETE /v1/portfolio/{item_id}     delete portfolio item (auth required, owner only)

Note: /upload-url is registered before the generic POST "" to ensure correct routing.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from botocore.exceptions import ClientError as BotocoreClientError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api._roles import ROLE_FREELANCER
from src.domain.portfolio import (
    CreatePortfolioItemInput,
    PortfolioValidationError,
    UpdatePortfolioItemInput,
    create_portfolio_item,
    delete_portfolio_item,
    get_portfolio_items,
    update_portfolio_item,
)
from src.infra import s3 as s3_infra
from src.infra.database import get_db
from src.infra.models import PortfolioItemModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/portfolio", tags=["portfolio"])

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class CreatePortfolioItemRequest(BaseModel):
    title: str
    description: str
    file_keys: list[str] = []
    external_url: Optional[str] = None
    project_url: Optional[str] = None  # alias for external_url from frontend
    github_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    tags: list[str] = []
    verified_gig_id: Optional[str] = None


class UpdatePortfolioItemRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    file_keys: Optional[list[str]] = None
    external_url: Optional[str] = None
    project_url: Optional[str] = None  # alias for external_url from frontend
    github_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    tags: Optional[list[str]] = None


class PortfolioItemOut(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    file_keys: list[str]
    external_url: Optional[str] = None
    project_url: Optional[str] = None
    github_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    tags: list[str]
    verified_gig_id: Optional[str] = None
    is_verified: bool
    verified_delivery: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PortfolioListOut(BaseModel):
    items: list[PortfolioItemOut]


class UploadUrlRequest(BaseModel):
    content_type: str = "application/octet-stream"


class UploadUrlResponse(BaseModel):
    url: str
    key: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _item_to_out(item: PortfolioItemModel, is_verified: bool) -> PortfolioItemOut:
    return PortfolioItemOut(
        id=item.id,
        user_id=item.user_id,
        title=item.title,
        description=item.description,
        file_keys=item.file_keys or [],
        external_url=item.external_url,
        project_url=item.external_url,  # alias for frontend compatibility
        github_url=item.github_url,
        cover_image_url=item.cover_image_url,
        tags=item.tags or [],
        verified_gig_id=item.verified_gig_id,
        is_verified=is_verified,
        verified_delivery=is_verified,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _require_freelancer(request: Request) -> str:
    """Verify authenticated FREELANCER. Returns user_id."""
    user_id: str = getattr(request.state, "user_id", "")
    role: str = getattr(request.state, "role", "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required"},
        )
    if role != ROLE_FREELANCER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Only FREELANCER-role users may perform this action",
            },
        )
    return user_id


def _require_auth(request: Request) -> str:
    """Verify authenticated user (any role). Returns user_id."""
    user_id: str = getattr(request.state, "user_id", "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required"},
        )
    return user_id


def _handle_validation_error(exc: PortfolioValidationError) -> HTTPException:
    status_map = {
        "ITEM_NOT_FOUND": 404,
        "GIG_NOT_FOUND": 404,
        "FORBIDDEN": 403,
    }
    http_status = status_map.get(exc.code, 400)
    return HTTPException(
        status_code=http_status,
        detail={"code": exc.code, "message": exc.message, "field_errors": []},
    )


# ---------------------------------------------------------------------------
# Endpoints  (specific routes registered BEFORE parameterised routes)
# ---------------------------------------------------------------------------


@router.get("/{user_id}", response_model=PortfolioListOut)
async def list_portfolio_items(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> PortfolioListOut:
    """List portfolio items for a user. Public — no auth required."""
    pairs = await get_portfolio_items(db, user_id)
    return PortfolioListOut(items=[_item_to_out(item, iv) for item, iv in pairs])


@router.post("/upload-url", response_model=UploadUrlResponse)
async def get_upload_url(
    body: UploadUrlRequest,
    request: Request,
) -> UploadUrlResponse:
    """
    Generate a presigned S3 PUT URL for direct browser-to-S3 upload.
    Requires FREELANCER role.
    """
    _require_freelancer(request)
    try:
        url, key = s3_infra.generate_portfolio_upload_url(body.content_type)
    except BotocoreClientError as exc:
        logger.error(
            "S3 ClientError generating presigned URL: %s %s",
            exc.response["Error"]["Code"],
            exc.response["Error"]["Message"],
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "S3_UNAVAILABLE",
                "message": "File upload service is temporarily unavailable",
                "field_errors": [],
            },
        )
    except Exception:
        logger.exception("Unexpected error generating presigned URL")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "field_errors": [],
            },
        )
    logger.info("presigned upload URL generated key=%s", key)
    return UploadUrlResponse(url=url, key=key)


@router.post("", response_model=PortfolioItemOut, status_code=status.HTTP_201_CREATED)
async def create_portfolio_item_endpoint(
    body: CreatePortfolioItemRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PortfolioItemOut:
    """Create a portfolio item. Requires FREELANCER role."""
    user_id = _require_freelancer(request)

    inp = CreatePortfolioItemInput(
        title=body.title,
        description=body.description,
        file_keys=body.file_keys,
        external_url=body.project_url or body.external_url,
        github_url=body.github_url,
        cover_image_url=body.cover_image_url,
        tags=body.tags,
        verified_gig_id=body.verified_gig_id,
    )
    try:
        item, is_verified = await create_portfolio_item(db, user_id, inp)
    except PortfolioValidationError as exc:
        raise _handle_validation_error(exc)

    return _item_to_out(item, is_verified)


@router.put("/{item_id}", response_model=PortfolioItemOut)
async def update_portfolio_item_endpoint(
    item_id: str,
    body: UpdatePortfolioItemRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PortfolioItemOut:
    """Update a portfolio item. Auth required; must be item owner."""
    user_id = _require_auth(request)

    inp = UpdatePortfolioItemInput(
        title=body.title,
        description=body.description,
        file_keys=body.file_keys,
        external_url=body.project_url or body.external_url,
        github_url=body.github_url,
        cover_image_url=body.cover_image_url,
        tags=body.tags,
    )
    try:
        item, is_verified = await update_portfolio_item(db, item_id, user_id, inp)
    except PortfolioValidationError as exc:
        raise _handle_validation_error(exc)

    return _item_to_out(item, is_verified)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio_item_endpoint(
    item_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a portfolio item. Auth required; must be item owner."""
    user_id = _require_auth(request)

    try:
        await delete_portfolio_item(db, item_id, user_id)
    except PortfolioValidationError as exc:
        raise _handle_validation_error(exc)
