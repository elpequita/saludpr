"""Settings for ETL pipeline. Reads from the backend's .env so we don't duplicate config."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ETL reads the backend .env so DATABASE_URL stays in one place
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV = REPO_ROOT / "backend" / ".env"


class EtlSettings(BaseSettings):
    """ETL pipeline settings (loaded from backend/.env)."""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ENV),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str = Field(
        ...,
        description="PostgreSQL URL (shared with backend)",
    )

    log_level: str = Field(default="INFO")

    # Where raw downloads live. Gitignored.
    data_dir: Path = Field(default=REPO_ROOT / "data")

    @property
    def raw_dir(self) -> Path:
        path = self.data_dir / "raw"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def interim_dir(self) -> Path:
        path = self.data_dir / "interim"
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache(maxsize=1)
def get_settings() -> EtlSettings:
    return EtlSettings()  # type: ignore[call-arg]


settings = get_settings()
