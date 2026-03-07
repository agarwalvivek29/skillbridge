"""
config.py — All environment variables validated at startup.
Import `settings` everywhere; never read os.environ directly.
"""

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

    # Blockchain
    base_rpc_url: str = "https://sepolia.base.org"
    escrow_factory_address: str = ""

    # AWS / S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket: str = "skillbridge-dev"


settings = Settings()
