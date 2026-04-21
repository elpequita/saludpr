"""Application settings, loaded from environment variables.

Uses pydantic-settings so every value is typed and validated at startup.
Fail-fast: if a required var is missing, the app won't boot.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database ---
    database_url: str = Field(
        ...,
        description="PostgreSQL connection URL, e.g. postgresql+psycopg://user:pw@host/db",
    )

    # --- App ---
    app_env: str = Field(default="development")
    app_debug: bool = Field(default=False)
    app_cors_origins: str = Field(
        default="http://localhost:3000",
        description="Comma-separated origins",
    )

    # --- Logging ---
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    # --- Rate limiting ---
    rate_limit_per_minute: int = Field(default=120)

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a clean list."""
        return [o.strip() for o in self.app_cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
