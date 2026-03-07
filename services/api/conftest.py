"""
Root conftest — sets environment variables before any module-level settings are instantiated.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-that-is-at-least-32-chars-long")
os.environ.setdefault("API_KEY", "test-api-key-16ch")
os.environ.setdefault("SIWE_DOMAIN", "localhost")
os.environ.setdefault("SIWE_CHAIN_ID", "84532")
