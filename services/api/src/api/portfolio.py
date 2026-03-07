"""Portfolio router — CRUD endpoints for freelancer portfolio items."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import (
    CreatePortfolioItemRequest,
    PortfolioItemResponse,
    PortfolioItemsResponse,
    PresignRequest,
    PresignResponse,
    UpdatePortfolioItemRequest,
)
from src.domain.portfolio import (
    compute_is_verified,
    create_portfolio_item,
    delete_portfolio_item,
    fetch_gig_for_item,
    list_portfolio_items,
    update_portfolio_item,
)
from src.infra.database import PortfolioItemModel, get_session
from src.infra.s3 import generate_presigned_upload_url
from src.middleware.auth import require_auth

router = APIRouter(
    prefix="/v1/portfolio",
    tags=["portfolio"],
    dependencies=[Depends(require_auth)],
)


def _build_response(item: PortfolioItemModel, is_verified: bool) -> PortfolioItemResponse:
    return PortfolioItemResponse(
        id=item.id,
        user_id=item.user_id,
        title=item.title,
        description=item.description,
        file_keys=item.file_keys or [],
        external_url=item.external_url or "",
        tags=item.tags or [],
        verified_gig_id=item.verified_gig_id,
        is_verified=is_verified,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post("/presign", response_model=PresignResponse, status_code=status.HTTP_200_OK)
async def generate_upload_url(
    body: PresignRequest,
    auth: dict = Depends(require_auth),  # type: ignore[assignment]
) -> PresignResponse:
    """Generate a presigned S3 URL for a portfolio file upload.

    The client uploads the file directly to S3 using this URL, then includes
    the returned `key` in the CreatePortfolioItemRequest.file_keys list.
    """
    try:
        result = generate_presigned_upload_url(body.filename, body.content_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_CONTENT_TYPE", "message": str(exc)},
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "S3_ERROR", "message": str(exc)},
        ) from exc
    return PresignResponse(**result)


@router.post("", response_model=PortfolioItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    body: CreatePortfolioItemRequest,
    auth: dict = Depends(require_auth),  # type: ignore[assignment]
    session: AsyncSession = Depends(get_session),
) -> PortfolioItemResponse:
    """Create a new portfolio item for the authenticated user."""
    user_id: str = auth["subject"]
    item = await create_portfolio_item(
        session=session,
        user_id=user_id,
        title=body.title,
        description=body.description,
        file_keys=body.file_keys,
        external_url=body.external_url,
        tags=body.tags,
        verified_gig_id=body.verified_gig_id,
    )
    gig = await fetch_gig_for_item(session, item)
    return _build_response(item, compute_is_verified(item, gig))


@router.get("", response_model=PortfolioItemsResponse, status_code=status.HTTP_200_OK)
async def get_items(
    user_id: str,
    auth: dict = Depends(require_auth),  # type: ignore[assignment]
    session: AsyncSession = Depends(get_session),
) -> PortfolioItemsResponse:
    """List all portfolio items for a given user, ordered by creation date (newest first)."""
    items = await list_portfolio_items(session, user_id)
    responses = []
    for item in items:
        gig = await fetch_gig_for_item(session, item)
        responses.append(_build_response(item, compute_is_verified(item, gig)))
    return PortfolioItemsResponse(items=responses)


@router.put("/{item_id}", response_model=PortfolioItemResponse, status_code=status.HTTP_200_OK)
async def update_item(
    item_id: str,
    body: UpdatePortfolioItemRequest,
    auth: dict = Depends(require_auth),  # type: ignore[assignment]
    session: AsyncSession = Depends(get_session),
) -> PortfolioItemResponse:
    """Update a portfolio item. Only the owner can update their own items."""
    user_id: str = auth["subject"]
    try:
        item = await update_portfolio_item(
            session=session,
            item_id=item_id,
            requesting_user_id=user_id,
            title=body.title,
            description=body.description,
            file_keys=body.file_keys,
            external_url=body.external_url,
            tags=body.tags,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": str(exc)},
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": str(exc)},
        ) from exc
    gig = await fetch_gig_for_item(session, item)
    return _build_response(item, compute_is_verified(item, gig))


@router.delete("/{item_id}", response_model=PortfolioItemResponse, status_code=status.HTTP_200_OK)
async def delete_item(
    item_id: str,
    auth: dict = Depends(require_auth),  # type: ignore[assignment]
    session: AsyncSession = Depends(get_session),
) -> PortfolioItemResponse:
    """Delete a portfolio item. Only the owner can delete their own items."""
    user_id: str = auth["subject"]
    try:
        item = await delete_portfolio_item(
            session=session,
            item_id=item_id,
            requesting_user_id=user_id,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": str(exc)},
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": str(exc)},
        ) from exc
    # Gig lookup not needed for deleted item — badge is always false after deletion
    return _build_response(item, is_verified=False)
