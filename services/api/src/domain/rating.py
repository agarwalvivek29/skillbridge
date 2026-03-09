"""
domain/rating.py -- Business logic for blind mutual ratings and reviews.

No FastAPI imports. All DB-interacting functions take an AsyncSession.

Blind-reveal rules:
  - A review starts with is_visible = False.
  - When both parties (client + freelancer) have submitted reviews for a gig,
    both reviews are flipped to is_visible = True.
  - At read time, reviews older than 7 days are treated as visible regardless
    of the is_visible flag (the 7-day window expiry).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infra.models import GigModel, NotificationModel, ReviewModel

logger = logging.getLogger(__name__)

REVIEW_WINDOW_DAYS = 7
_NOTIFICATION_TYPE_REVIEW_RECEIVED = "NOTIFICATION_TYPE_REVIEW_RECEIVED"


class ReviewValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


async def create_review(
    db: AsyncSession,
    gig_id: str,
    reviewer_id: str,
    reviewer_role: str,
    rating: int,
    comment: str,
) -> ReviewModel:
    """
    Create a review for a completed gig.

    - reviewer_id comes from JWT (server-side).
    - reviewee_id is inferred from gig roles.
    - Validates: gig exists, gig COMPLETED, reviewer is participant,
      no duplicate, rating 1-5.
    - Triggers blind-reveal if both parties have now submitted.
    """
    if rating < 1 or rating > 5:
        raise ReviewValidationError("INVALID_RATING", "Rating must be between 1 and 5")

    if len(comment) > 500:
        raise ReviewValidationError(
            "COMMENT_TOO_LONG", "Comment must be 500 characters or fewer"
        )

    gig = await _get_gig(db, gig_id)
    if gig is None:
        raise ReviewValidationError("GIG_NOT_FOUND", f"Gig {gig_id} not found")

    if gig.status != "COMPLETED":
        raise ReviewValidationError(
            "GIG_NOT_COMPLETED",
            f"Reviews are only allowed for completed gigs (current: {gig.status})",
        )

    # Determine reviewer/reviewee based on role in the gig
    if reviewer_id == gig.client_id:
        reviewee_id = gig.freelancer_id
    elif reviewer_id == gig.freelancer_id:
        reviewee_id = gig.client_id
    else:
        raise ReviewValidationError(
            "NOT_GIG_PARTICIPANT",
            "Only the gig's client or freelancer may submit a review",
        )

    if reviewee_id is None:
        raise ReviewValidationError(
            "NO_COUNTERPARTY", "Gig has no assigned counterparty to review"
        )

    # Check for duplicate
    existing = await db.execute(
        select(ReviewModel).where(
            ReviewModel.gig_id == gig_id,
            ReviewModel.reviewer_id == reviewer_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ReviewValidationError(
            "ALREADY_REVIEWED", "You have already submitted a review for this gig"
        )

    review = ReviewModel(
        gig_id=gig_id,
        reviewer_id=reviewer_id,
        reviewee_id=reviewee_id,
        rating=rating,
        comment=comment,
        is_visible=False,
    )
    db.add(review)
    await db.flush()

    # Check if both parties have now submitted -> reveal both
    revealed_reviews = await _try_reveal(db, gig_id)

    # Reload to pick up any visibility change
    await db.refresh(review)

    # If reveal happened, notify all reviewees and update reputations
    if revealed_reviews:
        for r in revealed_reviews:
            await _notify_reviewee(db, r)
            await _try_update_reputation(db, r.reviewee_id)

    return review


async def get_gig_reviews(
    db: AsyncSession,
    gig_id: str,
) -> list[ReviewModel]:
    """Return visible reviews for a gig (applying 7-day window expiry)."""
    result = await db.execute(
        select(ReviewModel)
        .where(ReviewModel.gig_id == gig_id)
        .order_by(ReviewModel.created_at)
    )
    reviews = list(result.scalars().all())
    cutoff = datetime.now(timezone.utc) - timedelta(days=REVIEW_WINDOW_DAYS)
    visible = []
    for r in reviews:
        if r.is_visible or _is_window_expired(r, cutoff):
            visible.append(r)
    return visible


async def get_user_reviews(
    db: AsyncSession,
    user_id: str,
) -> list[ReviewModel]:
    """Return all visible reviews where user_id is the reviewee."""
    result = await db.execute(
        select(ReviewModel)
        .where(ReviewModel.reviewee_id == user_id)
        .order_by(ReviewModel.created_at.desc())
    )
    reviews = list(result.scalars().all())
    cutoff = datetime.now(timezone.utc) - timedelta(days=REVIEW_WINDOW_DAYS)
    return [r for r in reviews if r.is_visible or _is_window_expired(r, cutoff)]


def compute_average_rating_x100(reviews: list[ReviewModel]) -> int:
    """Compute the average rating scaled x100 (e.g. 450 = 4.50 stars)."""
    if not reviews:
        return 0
    total = sum(r.rating for r in reviews)
    return round((total * 100) / len(reviews))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_window_expired(review: ReviewModel, cutoff: datetime) -> bool:
    """Check if the 7-day window has passed since the review was created."""
    created = review.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return created <= cutoff


async def _get_gig(db: AsyncSession, gig_id: str) -> GigModel | None:
    result = await db.execute(select(GigModel).where(GigModel.id == gig_id))
    return result.scalar_one_or_none()


async def _try_reveal(db: AsyncSession, gig_id: str) -> list[ReviewModel]:
    """If both client and freelancer have submitted, set is_visible=True on both.

    Returns the list of newly revealed reviews, or empty list if no reveal occurred.
    """
    result = await db.execute(select(ReviewModel).where(ReviewModel.gig_id == gig_id))
    reviews = list(result.scalars().all())
    if len(reviews) >= 2:
        newly_revealed = []
        for r in reviews:
            if not r.is_visible:
                r.is_visible = True
                newly_revealed.append(r)
        await db.flush()
        return newly_revealed
    return []


async def _notify_reviewee(db: AsyncSession, review: ReviewModel) -> None:
    """Create a REVIEW_RECEIVED notification for the reviewee."""
    payload = json.dumps(
        {
            "gig_id": review.gig_id,
            "review_id": review.id,
            "reviewer_id": review.reviewer_id,
            "rating": review.rating,
        }
    )
    db.add(
        NotificationModel(
            user_id=review.reviewee_id,
            type=_NOTIFICATION_TYPE_REVIEW_RECEIVED,
            payload_json=payload,
        )
    )
    await db.flush()


async def _try_update_reputation(db: AsyncSession, user_id: str) -> None:
    """
    Update average_rating_x100 and rating_count on the reputation table.

    Guarded with try/except: if the reputation table doesn't exist yet
    (issue #10 not merged), log a warning and continue.
    """
    try:
        from src.infra.models import ReputationModel  # noqa: F811

        # Get all visible reviews for this user
        result = await db.execute(
            select(ReviewModel).where(
                ReviewModel.reviewee_id == user_id,
                ReviewModel.is_visible == True,  # noqa: E712
            )
        )
        reviews = list(result.scalars().all())

        if not reviews:
            return

        avg_x100 = compute_average_rating_x100(reviews)
        count = len(reviews)

        rep_result = await db.execute(
            select(ReputationModel).where(ReputationModel.user_id == user_id)
        )
        rep = rep_result.scalar_one_or_none()
        if rep is not None:
            rep.average_rating_x100 = avg_x100
            rep.rating_count = count
            await db.flush()
        else:
            logger.info(
                "reputation record not found for user_id=%s; skipping rating update",
                user_id,
            )
    except Exception:
        logger.warning(
            "Could not update reputation for user_id=%s "
            "(reputation table may not exist yet -- issue #10)",
            user_id,
            exc_info=True,
        )
