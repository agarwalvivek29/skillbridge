"""
api/submission.py — Submission endpoints.

Endpoints:
  POST   /v1/milestones/{milestone_id}/submissions  create submission (FREELANCER role)
  GET    /v1/milestones/{milestone_id}/submissions  list submissions for milestone (auth required)
  GET    /v1/submissions/{submission_id}            get single submission (auth required)
  POST   /v1/submissions/upload-url                 generate presigned S3 upload URL (auth required)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.submission import (
    SubmissionValidationError,
    create_submission,
    get_submission_checked,
    list_submissions_checked,
)
from src.infra.database import get_db
from src.infra.models import SubmissionModel
from src.infra.s3 import (
    PRESIGNED_URL_EXPIRY_SECONDS,
    S3Error,
    generate_presigned_upload_url,
)

logger = logging.getLogger(__name__)

milestone_router = APIRouter(prefix="/v1/milestones", tags=["submissions"])
submission_router = APIRouter(prefix="/v1/submissions", tags=["submissions"])

_FREELANCER_ROLE = "USER_ROLE_FREELANCER"
_FILE_KEY_PREFIX = "submissions/"

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class CreateSubmissionRequest(BaseModel):
    repo_url: Optional[str] = None
    file_keys: list[str] = []
    notes: str = ""
    previous_submission_id: Optional[str] = None

    @field_validator("repo_url")
    @classmethod
    def repo_url_must_be_github_pr(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        import re

        # Must be a GitHub PR URL so OpenReview can be triggered on it
        if not re.match(r"^https://github\.com/[^/]+/[^/]+/pull/\d+", v):
            raise ValueError(
                "repo_url must be a GitHub PR URL "
                "(e.g. https://github.com/owner/repo/pull/1)"
            )
        return v

    @field_validator("file_keys")
    @classmethod
    def file_key_must_have_submissions_prefix(cls, v: list[str]) -> list[str]:
        # Prevent clients from referencing arbitrary S3 keys (fix #9)
        for key in v:
            if not key.startswith(_FILE_KEY_PREFIX):
                raise ValueError(f"each file_key must start with '{_FILE_KEY_PREFIX}'")
        return v


class SubmissionOut(BaseModel):
    id: str
    milestone_id: str
    freelancer_id: str
    repo_url: Optional[str]
    file_keys: list[str]
    notes: str
    status: str
    revision_number: int
    previous_submission_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubmissionListOut(BaseModel):
    submissions: list[SubmissionOut]


class UploadUrlRequest(BaseModel):
    filename: str
    content_type: str

    @field_validator("filename")
    @classmethod
    def filename_must_be_safe(cls, v: str) -> str:
        if "/" in v or "\\" in v or ".." in v:
            raise ValueError("filename must not contain path separators")
        if not v.strip():
            raise ValueError("filename must not be empty")
        return v

    @field_validator("content_type")
    @classmethod
    def content_type_must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content_type must not be empty")
        return v


class UploadUrlOut(BaseModel):
    upload_url: str
    file_key: str
    # How long (in seconds) the presigned URL remains valid (fix #8)
    expires_in_seconds: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_freelancer(request: Request) -> str:
    """Extract user_id and verify FREELANCER role. Returns user_id."""
    user_id: str = getattr(request.state, "user_id", "")
    role: str = getattr(request.state, "role", "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required"},
        )
    if role != _FREELANCER_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN",
                "message": "Only FREELANCER-role users may submit work",
            },
        )
    return user_id


def _require_auth(request: Request) -> str:
    """Extract user_id from request state. Returns user_id."""
    user_id: str = getattr(request.state, "user_id", "")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication required"},
        )
    return user_id


def _handle_validation_error(exc: SubmissionValidationError) -> HTTPException:
    status_map = {
        "MILESTONE_NOT_FOUND": 404,
        "GIG_NOT_FOUND": 404,
        "PREVIOUS_SUBMISSION_NOT_FOUND": 404,
        "FORBIDDEN": 403,
        "GIG_NOT_IN_PROGRESS": 409,
        "MILESTONE_NOT_SUBMITTABLE": 409,
        "NO_DELIVERABLE": 400,  # fix #1: explicit entry, not relying on fallback
        "PREVIOUS_SUBMISSION_REQUIRED": 422,
        "INVALID_PREVIOUS_SUBMISSION": 422,
    }
    http_status = status_map.get(exc.code, 400)
    return HTTPException(
        status_code=http_status,
        detail={"code": exc.code, "message": exc.message, "field_errors": []},
    )


def _submission_to_out(s: SubmissionModel) -> SubmissionOut:
    return SubmissionOut(
        id=s.id,
        milestone_id=s.milestone_id,
        freelancer_id=s.freelancer_id,
        repo_url=s.repo_url,
        file_keys=s.file_keys or [],
        notes=s.notes,
        status=s.status,
        revision_number=s.revision_number,
        previous_submission_id=s.previous_submission_id,
        created_at=s.created_at,
        updated_at=s.updated_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@milestone_router.post(
    "/{milestone_id}/submissions",
    response_model=SubmissionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_submission_endpoint(
    milestone_id: str,
    body: CreateSubmissionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SubmissionOut:
    """Submit work for a milestone. Requires FREELANCER role and must be assigned freelancer."""
    freelancer_id = _require_freelancer(request)

    try:
        submission = await create_submission(
            db,
            freelancer_id=freelancer_id,
            milestone_id=milestone_id,
            repo_url=body.repo_url,
            file_keys=body.file_keys,
            notes=body.notes,
            previous_submission_id=body.previous_submission_id,
        )
    except SubmissionValidationError as exc:
        raise _handle_validation_error(exc)

    return _submission_to_out(submission)


@milestone_router.get(
    "/{milestone_id}/submissions",
    response_model=SubmissionListOut,
)
async def list_submissions_endpoint(
    milestone_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SubmissionListOut:
    """List all submissions (revision history) for a milestone.
    Auth required; caller must be the gig's client or assigned freelancer."""
    user_id = _require_auth(request)
    try:
        submissions = await list_submissions_checked(db, milestone_id, user_id)
    except SubmissionValidationError as exc:
        raise _handle_validation_error(exc)
    return SubmissionListOut(submissions=[_submission_to_out(s) for s in submissions])


@submission_router.get(
    "/{submission_id}",
    response_model=SubmissionOut,
)
async def get_submission_endpoint(
    submission_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SubmissionOut:
    """
    Get a single submission by ID.
    Auth required; caller must be the gig's client or assigned freelancer (fix #4).
    """
    user_id = _require_auth(request)
    try:
        submission = await get_submission_checked(db, submission_id, user_id)
    except SubmissionValidationError as exc:
        raise _handle_validation_error(exc)
    if submission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SUBMISSION_NOT_FOUND",
                "message": f"Submission {submission_id} not found",
            },
        )
    return _submission_to_out(submission)


@submission_router.post(
    "/upload-url",
    response_model=UploadUrlOut,
)
async def get_upload_url_endpoint(
    body: UploadUrlRequest,
    request: Request,
) -> UploadUrlOut:
    """Generate a presigned S3 PUT URL for direct browser upload. Auth required."""
    _require_auth(request)

    try:
        upload_url, file_key = generate_presigned_upload_url(
            body.filename, body.content_type
        )
    except S3Error as exc:
        logger.error("s3 upload url generation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "S3_UNAVAILABLE",
                "message": "File upload service is temporarily unavailable",
            },
        )

    return UploadUrlOut(
        upload_url=upload_url,
        file_key=file_key,
        expires_in_seconds=PRESIGNED_URL_EXPIRY_SECONDS,
    )
