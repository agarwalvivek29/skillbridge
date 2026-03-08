"""
api/webhooks.py — GitHub webhook receiver.

Endpoints:
  POST /v1/webhooks/github  receive GitHub App events (no auth — verified by HMAC)
"""

from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.domain.review import process_openreview_verdict
from src.infra.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


def _verify_signature(body: bytes, signature_header: str | None) -> None:
    """
    Verify GitHub's X-Hub-Signature-256 HMAC.

    No-ops if github_webhook_secret is not configured (dev mode).
    Raises HTTP 401 on mismatch.
    """
    if not settings.github_webhook_secret:
        return

    if not signature_header or not signature_header.startswith("sha256="):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "MISSING_SIGNATURE",
                "message": "X-Hub-Signature-256 required",
            },
        )

    expected = (
        "sha256="
        + hmac.new(
            settings.github_webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
    )

    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_SIGNATURE",
                "message": "Webhook signature mismatch",
            },
        )


@router.post("/github")
async def github_webhook(
    request: Request,
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Receive GitHub App webhook events."""
    body = await request.body()
    _verify_signature(body, x_hub_signature_256)

    if x_github_event != "pull_request_review":
        return {"status": "ignored", "event": x_github_event}

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_PAYLOAD",
                "message": "request body must be valid JSON",
            },
        )

    review = payload.get("review", {})
    reviewer_login = review.get("user", {}).get("login", "")
    if reviewer_login.lower() != settings.openreview_bot_login.lower():
        logger.info(
            "github webhook: pull_request_review from %s — not openreview bot, ignored",
            reviewer_login,
        )
        return {"status": "ignored", "reason": "not_openreview_bot"}

    state: str = review.get("state", "").lower()
    review_body: str = review.get("body") or ""
    pr_url: str = payload.get("pull_request", {}).get("html_url", "")

    if not pr_url:
        logger.warning(
            "github webhook: pull_request_review missing pull_request.html_url"
        )
        return {"status": "ignored", "reason": "missing_pr_url"}

    await process_openreview_verdict(db, pr_url, state, review_body)
    await db.commit()

    return {"status": "ok"}
