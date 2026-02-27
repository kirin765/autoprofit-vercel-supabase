from __future__ import annotations

import json
import time
from typing import Optional

import typer
import uvicorn

from autoprofit import database
from autoprofit.pipeline import run_pipeline
from autoprofit.settings import get_settings

app = typer.Typer(help="Autoprofit automation CLI")


@app.command()
def init() -> None:
    """Initialize database and output folders."""
    settings = get_settings()
    database.initialize_db(settings.db_target)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    typer.echo(f"Initialized {settings.db_target}")


@app.command("db-check")
def db_check() -> None:
    """Validate DB connectivity (works with SQLite, Postgres, or Supabase)."""
    settings = get_settings()
    database.initialize_db(settings.db_target)
    metrics = database.get_metrics(settings.db_target)
    typer.echo(
        json.dumps(
            {
                "provider": settings.database_provider,
                "connected": True,
                "metrics": metrics,
            },
            indent=2,
        )
    )


@app.command()
def run(limit: Optional[int] = typer.Option(default=None), dry_run: bool = False) -> None:
    """Execute one full automation cycle."""
    settings = get_settings()
    result = run_pipeline(settings, limit=limit, dry_run=dry_run)
    typer.echo(json.dumps(result, indent=2))


@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Serve API endpoints including cron trigger and redirect tracking."""
    uvicorn.run("autoprofit.web:app", host=host, port=port, reload=False)


@app.command()
def loop(interval_minutes: int = 60) -> None:
    """Run automation continuously without human intervention."""
    settings = get_settings()
    typer.echo(f"Starting autonomous loop. Interval={interval_minutes} minutes")
    while True:
        result = run_pipeline(settings)
        typer.echo(json.dumps(result, indent=2))
        time.sleep(max(interval_minutes, 1) * 60)


if __name__ == "__main__":
    app()
