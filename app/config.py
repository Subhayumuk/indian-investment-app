import os
from functools import lru_cache


@lru_cache
def get_settings() -> "Settings":
    return Settings()


class Settings:
    """Application settings loaded from environment variables."""

    APP_TITLE: str = "NRI Investment and Tax Planner"
    APP_DESCRIPTION: str = (
        "Multi-country tax and investment planner for NRIs (Non-Resident "
        "Indians) with Indian savings/investments."
    )
    APP_VERSION: str = "2.0.0"

    DEBUG: bool = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes"}
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    STATIC_DIR: str = os.getenv("STATIC_DIR", "frontend/dist")
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]

    GOLD_API_KEY: str = os.getenv("GOLD_API_KEY", "")
