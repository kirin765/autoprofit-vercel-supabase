from pathlib import Path

from autoprofit import database
from autoprofit.settings import Settings


def test_settings_prefers_supabase_db_url_when_database_url_missing() -> None:
    settings = Settings(
        database_url="",
        supabase_db_url="postgresql://postgres:pw@db.example.supabase.co:5432/postgres",
        db_path=Path("data/local.db"),
    )
    assert settings.database_provider == "supabase"
    assert settings.db_target == settings.supabase_db_url


def test_settings_builds_supabase_url_from_parts() -> None:
    settings = Settings(
        database_url="",
        supabase_db_url="",
        supabase_db_host="db.example.supabase.co",
        supabase_db_port=5432,
        supabase_db_name="postgres",
        supabase_db_user="postgres",
        supabase_db_password="p@ss word",
    )
    assert settings.database_provider == "supabase"
    assert "postgresql://" in settings.effective_supabase_db_url
    assert "sslmode=require" in settings.effective_supabase_db_url
    assert "p%40ss%20word" in settings.effective_supabase_db_url


def test_normalize_db_url_enforces_sslmode_for_supabase() -> None:
    raw = "postgresql://postgres:pw@db.project-ref.supabase.co:5432/postgres"
    normalized = database._normalize_db_url(raw)
    assert normalized.startswith("postgresql+psycopg://")
    assert "sslmode=require" in normalized
