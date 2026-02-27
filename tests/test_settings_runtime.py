from pathlib import Path

from autoprofit import settings as settings_module


def test_get_settings_uses_tmp_paths_on_vercel_runtime(monkeypatch) -> None:
    settings_module.get_settings.cache_clear()
    monkeypatch.setenv("VERCEL", "1")

    settings = settings_module.get_settings()

    assert str(settings.data_dir).startswith("/tmp")
    assert str(settings.output_dir).startswith("/tmp")
    if settings.database_provider == "sqlite":
        assert str(settings.db_path).startswith("/tmp")

    settings_module.get_settings.cache_clear()
    monkeypatch.delenv("VERCEL", raising=False)
