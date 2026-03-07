"""
infra/s3.py — Boto3 S3 client and presigned URL generation.

In local development (when AWS credentials are not set), presigned URL
generation is not available — callers should handle the exception gracefully.
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from src.config import settings

# Presigned PUT URL TTL in seconds
_PRESIGNED_EXPIRY_SECONDS = 300


def _get_s3_client():
    """Return a boto3 S3 client configured from settings."""
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
    )


def generate_presigned_put_url(s3_key: str, content_type: str) -> str:
    """
    Generate a presigned S3 PUT URL for direct browser upload.

    Raises:
        NoCredentialsError: if AWS credentials are not configured
        ClientError: on any S3 API error
    """
    client = _get_s3_client()
    try:
        url = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.s3_bucket,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=_PRESIGNED_EXPIRY_SECONDS,
            HttpMethod="PUT",
        )
    except (NoCredentialsError, ClientError) as exc:
        raise exc
    return url
