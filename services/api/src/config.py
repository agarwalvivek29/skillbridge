from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Auth
    jwt_secret: str = Field(min_length=32)
    jwt_expiry_seconds: int = 3600
    api_key: str = Field(min_length=16)

    # Database
    database_url: str = "postgresql+asyncpg://user:password@localhost:5432/skillbridge"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379"

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    s3_bucket: str = "skillbridge-uploads"
    s3_presign_expiry_seconds: int = 300

    # Base L2 blockchain
    base_rpc_url: str = ""
    escrow_factory_address: str = ""

    # App
    environment: str = "development"
    log_level: str = "DEBUG"

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()  # type: ignore[call-arg]
