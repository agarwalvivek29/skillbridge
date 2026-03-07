"""
infra/celery_client.py — Celery producer for the api service.

The api service only *produces* tasks; the ai-reviewer service consumes them.
All task names must match the task names registered in the ai-reviewer worker.
"""

import logging

from celery import Celery

from src.config import settings

logger = logging.getLogger(__name__)

_REVIEW_TASK_NAME = "review.enqueue"

_celery_app: Celery | None = None


def _get_celery() -> Celery:
    global _celery_app
    if _celery_app is None:
        _celery_app = Celery(broker=settings.redis_url, backend=settings.redis_url)
    return _celery_app


def enqueue_review(submission_id: str) -> None:
    """
    Enqueue a review job for the given submission.

    Sends the Celery task `review.enqueue` to the Redis broker. If Redis is
    unavailable, the error is logged as a warning and the function returns
    without raising so the submission creation is not rolled back.
    """
    try:
        app = _get_celery()
        app.send_task(_REVIEW_TASK_NAME, kwargs={"submission_id": submission_id})
        logger.info("review.enqueue dispatched submission_id=%s", submission_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "celery unavailable, skipping enqueue submission_id=%s error=%s",
            submission_id,
            exc,
        )
