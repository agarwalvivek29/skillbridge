"""Unit test conftest — injects required env vars before any src import."""

import os

os.environ.setdefault("JWT_SECRET", "test-secret-that-is-at-least-32-chars-long!")
os.environ.setdefault("API_KEY", "test-api-key-minimum-16-chars")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test-access-key-id")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test-secret-access-key")
os.environ.setdefault("S3_BUCKET", "test-bucket")
