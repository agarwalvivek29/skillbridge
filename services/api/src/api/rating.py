"""
api/rating.py -- Rating and review endpoints.

Endpoints:
  POST  /v1/gigs/{gig_id}/review          submit review (auth required, gig participant)
  GET   /v1/gigs/{gig_id}/reviews          list visible reviews for a gig (auth required)
  GET   /v1/users/{user_id}/reviews        list visible reviews for a user (public)
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.rating import (
    ReviewValidationError,
    compute_average_rating_x100,
    create_review,
    get_gig_reviews,
    get_user_reviews,
)
from src.infra.database import get_db
from src.infra.models import ReviewModel

logger = logging.getLogger(__name__)

gig_review_router = APIRouter(prefix="/v1/gigs", tags=["reviews"])
user_review_router = APIRouter(prefix="/v1/users", tags=["reviews"])


# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class CreateReviewRequest(BaseModel):
    rating: int
    comment: str = ""

    @field_validator("rating")
    @classmethod
    def rating_range(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("rating must be between 1 and 5")
        return v

    @field_validator("comment")
    @classmethod
    def comment_length(cls, v: str) -> str:
        if len(v) > 500:
            raise ValueError("comment must be 500 characters or fewer")
        return v


class ReviewOut(BaseModel):
    id: str
    gig_id: str
    reviewer_id: str
    reviewee_id: str
    rating: int
    comment: str
    is_visible: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewListOut(BaseModel):
    reviews: list[ReviewOut]
    average_rating_x100: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_auth(request: Request) -> tuple[str, str]:
    """Extract user_id and role from request state. Returns (user_id, role)."""
    user_id: str = getattr(request.state, "user_id", "")
    role: str = getattr(request.state, "role", "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required"},
        )
    return user_id, role


def _review_to_out(r: ReviewModel) -> ReviewOut:
    return ReviewOut(
        id=r.id,
        gig_id=r.gig_id,
        reviewer_id=r.reviewer_id,
        reviewee_id=r.reviewee_id,
        rating=r.rating,
        comment=r.comment,
        is_visible=r.is_visible,
        created_at=r.created_at,
    )


def _handle_validation_error(exc: ReviewValidationError) -> HTTPException:
    status_map = {
        "GIG_NOT_FOUND": 404,
        "GIG_NOT_COMPLETED": 409,
        "NOT_GIG_PARTICIPANT": 403,
        "ALREADY_REVIEWED": 409,
        "NO_COUNTERPARTY": 409,
        "INVALID_RATING": 422,
        "COMMENT_TOO_LONG": 422,
    }
    http_status = status_map.get(exc.code, 400)
    return HTTPException(
        status_code=http_status,
        detail={"code": exc.code, "message": exc.message, "field_errors": []},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@gig_review_router.post(
    "/{gig_id}/review", response_model=ReviewOut, status_code=status.HTTP_201_CREATED
)
async def create_review_endpoint(
    gig_id: str,
    body: CreateReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ReviewOut:
    """Submit a review for a completed gig. Auth required; must be gig participant."""
    user_id, role = _require_auth(request)

    try:
        review = await create_review(
            db,
            gig_id=gig_id,
            reviewer_id=user_id,
            reviewer_role=role,
            rating=body.rating,
            comment=body.comment,
        )
    except ReviewValidationError as exc:
        raise _handle_validation_error(exc)

    logger.info(
        "review created review_id=%s gig_id=%s reviewer=%s", review.id, gig_id, user_id
    )
    return _review_to_out(review)


@gig_review_router.get("/{gig_id}/reviews", response_model=ReviewListOut)
async def get_gig_reviews_endpoint(
    gig_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ReviewListOut:
    """Get visible reviews for a gig. Auth required."""
    _require_auth(request)

    reviews = await get_gig_reviews(db, gig_id)
    avg = compute_average_rating_x100(reviews)
    return ReviewListOut(
        reviews=[_review_to_out(r) for r in reviews],
        average_rating_x100=avg,
    )


@user_review_router.get("/{user_id}/reviews", response_model=ReviewListOut)
async def get_user_reviews_endpoint(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> ReviewListOut:
    """Get all visible reviews for a user's profile. Public endpoint."""
    reviews = await get_user_reviews(db, user_id)
    avg = compute_average_rating_x100(reviews)
    return ReviewListOut(
        reviews=[_review_to_out(r) for r in reviews],
        average_rating_x100=avg,
    )
