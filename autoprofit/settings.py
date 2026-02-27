from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Union
from urllib.parse import quote

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "autoprofit"
    env: str = "dev"

    data_dir: Path = Path("data")
    output_dir: Path = Path("public")
    db_path: Path = Path("data/autoprofit.db")
    database_url: str = ""
    supabase_db_url: str = ""
    supabase_db_host: str = ""
    supabase_db_port: int = 5432
    supabase_db_name: str = "postgres"
    supabase_db_user: str = ""
    supabase_db_password: str = ""
    supabase_db_sslmode: str = "require"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    trends_rss_url: str = "https://trends.google.com/trending/rss?geo=US"
    trends_timeout_seconds: float = 15.0
    max_posts_per_run: int = 3
    allow_refresh_existing: bool = True

    domain_url: str = "http://localhost:8000"
    api_base_url: str = ""
    cron_token: str = ""

    affiliate_tag: str = ""
    affiliate_disclosure: str = (
        "Disclosure: Some links are affiliate links. If you buy through them, "
        "we may earn a commission at no extra cost to you."
    )

    stripe_secret_key: str = ""
    stripe_price_id: str = ""
    stripe_webhook_secret: str = ""
    stripe_success_url: str = "http://localhost:8000/success"
    stripe_cancel_url: str = "http://localhost:8000/cancel"

    quality_min_word_count: int = 260

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def has_supabase_db_config(self) -> bool:
        return bool(self.supabase_db_host and self.supabase_db_user and self.supabase_db_password)

    @property
    def effective_supabase_db_url(self) -> str:
        if self.supabase_db_url:
            return self.supabase_db_url
        if not self.has_supabase_db_config:
            return ""
        user = quote(self.supabase_db_user, safe="")
        password = quote(self.supabase_db_password, safe="")
        return (
            f"postgresql://{user}:{password}"
            f"@{self.supabase_db_host}:{self.supabase_db_port}/{self.supabase_db_name}"
            f"?sslmode={self.supabase_db_sslmode}"
        )

    @property
    def db_target(self) -> Union[Path, str]:
        if self.database_url:
            return self.database_url
        if self.effective_supabase_db_url:
            return self.effective_supabase_db_url
        return self.db_path

    @property
    def effective_api_base_url(self) -> str:
        base = self.api_base_url or self.domain_url
        return base.rstrip("/")

    @property
    def database_provider(self) -> str:
        if self.database_url:
            return "postgres"
        if self.effective_supabase_db_url:
            return "supabase"
        return "sqlite"


def _ensure_writable_dir(path: Path, fallback: Path) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()

    is_vercel_runtime = bool(os.getenv("VERCEL"))
    if is_vercel_runtime:
        if not settings.data_dir.is_absolute():
            settings.data_dir = Path("/tmp") / settings.data_dir
        if not settings.output_dir.is_absolute():
            settings.output_dir = Path("/tmp") / settings.output_dir
        if settings.database_provider == "sqlite" and not settings.db_path.is_absolute():
            settings.db_path = Path("/tmp") / settings.db_path

    settings.data_dir = _ensure_writable_dir(settings.data_dir, Path("/tmp/autoprofit-data"))
    settings.output_dir = _ensure_writable_dir(settings.output_dir, Path("/tmp/autoprofit-public"))

    if settings.database_provider == "sqlite":
        parent = settings.db_path.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            settings.db_path = settings.data_dir / "autoprofit.db"
            settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
