"""
config.py — All environment variables validated at startup.
Import `settings` everywhere; never read os.environ directly.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    port: int = 8000
    log_level: str = "info"

    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/skillbridge"
    )

    # Redis / Celery
    redis_url: str = "redis://localhost:6379"

    # Auth — REQUIRED
    jwt_secret: str
    jwt_expiry_seconds: int = 3600
    api_key: str
    siwe_domain: str = "skillbridge.agarwalvivek.com"

    # Blockchain
    base_rpc_url: str = "https://sepolia.base.org"
    escrow_factory_address: str = ""

    # AWS / S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket: str = "skillbridge-dev"
    s3_presigned_url_expiry_seconds: int = 300

    @field_validator("s3_bucket")
    @classmethod
    def s3_bucket_required_in_production(cls, v: str) -> str:
        import os

        if os.getenv("APP_ENV", "development") == "production" and not v:
            raise ValueError("s3_bucket must be set in production")
        return v

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("jwt_secret must be at least 32 characters")
        return v

    @field_validator("api_key")
    @classmethod
    def api_key_min_length(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError("api_key must be at least 16 characters")
        return v


settings = Settings()  # type: ignore[call-arg]
