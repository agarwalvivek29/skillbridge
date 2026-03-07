"""
s3.py — S3 presigned URL generation for direct browser-to-S3 uploads.

Files are NEVER routed through the API. The client:
  1. Calls POST /v1/portfolio/upload-url  → receives { url, key }
  2. PUTs the file directly to the presigned URL (S3)
  3. Passes the key in the subsequent API request body (e.g. file_keys)

This module is intentionally thin — one function, no state.
"""

import uuid

from src.config import settings


def generate_portfolio_upload_url(
    content_type: str = "application/octet-stream",
) -> tuple[str, str]:
    """
    Generate a presigned S3 PUT URL for a portfolio file upload.

    Returns (presigned_url, s3_key).
    The key is server-generated (UUID-based) to prevent path traversal.
    URL expires in 300 seconds.

    Raises RuntimeError if AWS credentials are not configured.
    Raises botocore.exceptions.ClientError on S3 API errors.
    """
    import boto3  # noqa: PLC0415 — lazy import keeps boto3 optional during tests

    key = f"portfolio/{uuid.uuid4()}"
    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )
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
