"""Unit test conftest — injects required env vars before any src import."""

import os

os.environ.setdefault("JWT_SECRET", "test-secret-that-is-at-least-32-chars-long!")
os.environ.setdefault("API_KEY", "test-api-key-minimum-16-chars")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
