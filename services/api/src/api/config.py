from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    port: int = 8000
    log_level: str = "debug"

    database_url: str = Field(
        default=...,
        description="Async PostgreSQL connection URL (postgresql+asyncpg://...)",
    )

    jwt_secret: str = Field(min_length=32, description="HS256 signing secret (min 32 chars)")
    jwt_expiry_seconds: int = 3600
    api_key: str = Field(min_length=16, description="Service-to-service API key (min 16 chars)")

    siwe_domain: str = "localhost"
    siwe_chain_id: int = 84532
    nonce_ttl_seconds: int = 300


settings = Settings()
