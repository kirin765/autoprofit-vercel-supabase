from pathlib import Path

from autoprofit.pipeline import run_pipeline
from autoprofit.settings import Settings


def test_pipeline_generates_post(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "db.sqlite3"
    output_dir = tmp_path / "site"
    data_dir = tmp_path / "data"

    settings = Settings(
        data_dir=data_dir,
        output_dir=output_dir,
        db_path=db_path,
        trends_rss_url="https://invalid.local/rss",
        max_posts_per_run=1,
        quality_min_word_count=20,
    )

    def fake_fetch_trends(*args, **kwargs):
        from autoprofit.models import TrendItem

        return [
            TrendItem(
                title="best ecommerce platform",
                keyword="best ecommerce platform",
                source_url="test",
                score=2.0,
            )
        ]

    monkeypatch.setattr("autoprofit.pipeline.fetch_trends", fake_fetch_trends)

    result = run_pipeline(settings, limit=1)
    assert result["created"] == 1
    post_files = list((output_dir / "posts").glob("*.html"))
    assert len(post_files) == 1
