"""Module entry point for production: python -m api."""

import uvicorn

from src.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        log_level=settings.log_level.lower(),
        reload=(settings.environment == "development"),
    )
