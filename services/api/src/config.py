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

    # GitHub — OpenReview integration
    github_token: str = ""
    github_webhook_secret: str = ""
    openreview_bot_login: str = "openreview-bot"

    # Blockchain (Solana)
    solana_rpc_url: str = "http://localhost:8899"
    escrow_program_id: str = ""
    solana_cluster: str = "localnet"

    # AWS / S3 — REQUIRED for file upload functionality
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-1"
    s3_bucket: str
    s3_presigned_url_expiry_seconds: int = 300

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

    @field_validator("aws_access_key_id")
    @classmethod
    def aws_access_key_id_required(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("aws_access_key_id must not be empty")
        return v

    @field_validator("aws_secret_access_key")
    @classmethod
    def aws_secret_access_key_required(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("aws_secret_access_key must not be empty")
        return v

    @field_validator("s3_bucket")
    @classmethod
    def s3_bucket_required(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("s3_bucket must not be empty")
        return v


settings = Settings()  # type: ignore[call-arg]
