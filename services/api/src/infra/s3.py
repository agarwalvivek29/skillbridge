"""S3 presigned URL generation for portfolio file uploads.

Files never pass through the API — clients upload directly to S3 using presigned URLs.
"""

import uuid
from typing import Any

import boto3
from botocore.exceptions import ClientError
from loguru import logger

from src.config import settings

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "application/pdf",
    "video/mp4",
    "video/webm",
}

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB


def _get_s3_client() -> Any:
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )


def generate_presigned_upload_url(filename: str, content_type: str) -> dict[str, str]:
    """Generate a presigned S3 PUT URL for a portfolio file upload.

    Returns a dict with `upload_url` (the presigned URL) and `key` (the S3 object key).
    Raises ValueError for disallowed content types.
    Raises RuntimeError on S3 client errors.
    """
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(
            f"Content type '{content_type}' is not allowed. "
            f"Allowed types: {sorted(ALLOWED_CONTENT_TYPES)}"
        )

    extension = filename.rsplit(".", 1)[-1] if "." in filename else ""
    key = f"portfolio/{uuid.uuid4()}/{filename}"
    if extension:
        key = f"portfolio/{uuid.uuid4()}.{extension}"

    try:
        s3 = _get_s3_client()
        upload_url: str = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.s3_bucket,
                "Key": key,
                "ContentType": content_type,
                "ContentLength": MAX_FILE_SIZE_BYTES,
            },
            ExpiresIn=settings.s3_presign_expiry_seconds,
        )
    except ClientError as exc:
        logger.error("S3 presign error", key=key, error=str(exc))
        raise RuntimeError("Failed to generate upload URL") from exc

    logger.info("S3 presigned URL generated", key=key, content_type=content_type)
    return {"upload_url": upload_url, "key": key}
