"""
infra/s3.py — S3 presigned URL generation for direct browser-to-S3 uploads.

Files are NEVER routed through the API. The client:
  1. Calls POST /v1/.../upload-url  → receives { url, key }
  2. PUTs the file directly to the presigned URL (S3)
  3. Passes the key in the subsequent API request body (e.g. file_keys)
"""

import logging
import uuid
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

from src.config import settings

logger = logging.getLogger(__name__)

PRESIGNED_URL_EXPIRY_SECONDS = 900  # 15 minutes
_ALLOWED_KEY_PREFIX = "submissions/"


def _s3_client():  # type: ignore[no-untyped-def]
    return boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
        region_name=settings.aws_region,
    )


def generate_portfolio_upload_url(
    content_type: str = "application/octet-stream",
) -> tuple[str, str]:
    """
    Generate a presigned S3 PUT URL for a portfolio file upload.

    Returns (presigned_url, s3_key).
    The key is server-generated (UUID-based) to prevent path traversal.

    Raises RuntimeError if AWS credentials are not configured.
    Raises botocore.exceptions.ClientError on S3 API errors.
    """
    key = f"portfolio/{uuid.uuid4()}"
    client = _s3_client()
    url: str = client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=settings.s3_presigned_url_expiry_seconds,
    )
    return url, key


def generate_presigned_upload_url(filename: str, content_type: str) -> tuple[str, str]:
    """
    Generate a presigned S3 PUT URL for a submission file upload.

    Returns (upload_url, file_key). The file_key should be stored and passed back
    in CreateSubmissionRequest.file_keys after the upload completes.

    Raises S3Error on failure.
    """
    date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
    unique_id = str(uuid.uuid4())
    file_key = f"{_ALLOWED_KEY_PREFIX}{date_prefix}/{unique_id}/{filename}"

    try:
        client = _s3_client()
        upload_url: str = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.s3_bucket,
                "Key": file_key,
                "ContentType": content_type,
            },
            ExpiresIn=PRESIGNED_URL_EXPIRY_SECONDS,
        )
        logger.info("presigned_url generated file_key=%s", file_key)
        return upload_url, file_key
    except ClientError as exc:
        logger.error("s3 presigned url generation failed: %s", exc)
        raise S3Error("Failed to generate upload URL") from exc


class S3Error(RuntimeError):
    """Raised when an S3 operation fails."""
