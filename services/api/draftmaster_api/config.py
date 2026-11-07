"""Runtime configuration (12-factor, environment driven)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DRAFTMASTER_", extra="ignore")

    app_name: str = "DraftMaster AI"
    version: str = "1.0.0"
    environment: str = "development"

    # Data
    artifact_path: str = str(ROOT / "data" / "artifacts" / "draftmaster-data.json")
    hero_hashes_path: str = str(ROOT / "data" / "artifacts" / "hero-hashes.json")

    # Infra
    redis_url: str = ""
    database_url: str = ""
    opendota_api_key: str = ""

    # Product
    free_daily_analyses: int = 3
    cache_ttl_seconds: int = 300
    match_cache_ttl_seconds: int = 600

    # CORS
    cors_origins: str = "*"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
