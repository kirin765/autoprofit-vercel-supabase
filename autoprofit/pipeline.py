from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from autoprofit import database
from autoprofit.generator import generate_post
from autoprofit.offers import build_offer_url, choose_offer, load_offers
from autoprofit.publisher import render_index, render_post
from autoprofit.settings import Settings
from autoprofit.sources import fetch_trends, load_fallback_trends
from autoprofit.utils import slugify, utc_now


@dataclass
class RunResult:
    created: int
    skipped: int
    failed: int
    posts: list[dict[str, str]]


def _fetch_trends_with_retry(settings: Settings, target_limit: int, max_attempts: int = 3) -> list[Any]:
    for attempt in range(1, max_attempts + 1):
        try:
            trends = fetch_trends(
                rss_url=settings.trends_rss_url,
                timeout_seconds=settings.trends_timeout_seconds,
                limit=max(target_limit * 3, target_limit),
            )
            if trends:
                return trends
        except Exception:
            pass

        if attempt < max_attempts:
            time.sleep(attempt * 2)
    return []


def run_pipeline(settings: Settings, limit: Optional[int] = None, dry_run: bool = False) -> dict[str, Any]:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    if settings.database_provider == "sqlite":
        settings.db_path.parent.mkdir(parents=True, exist_ok=True)

    database.initialize_db(settings.db_target)
    run_id = database.start_run(settings.db_target)

    target_limit = limit or settings.max_posts_per_run
    created = 0
    skipped = 0
    failed = 0
    published_posts: list[dict[str, str]] = []

    try:
        trends = _fetch_trends_with_retry(settings, target_limit)

        fallback_trends = load_fallback_trends(Path("config/fallback_keywords.yaml"), target_limit * 3)
        known_keywords = {item.keyword.lower() for item in trends}
        for item in fallback_trends:
            if item.keyword.lower() not in known_keywords:
                trends.append(item)
                known_keywords.add(item.keyword.lower())

        offers = load_offers(Path("config/offers.yaml"))

        for trend in sorted(trends, key=lambda item: item.score, reverse=True):
            if created >= target_limit:
                break

            base_slug = slugify(trend.keyword)
            slug = base_slug
            if database.has_post_slug(settings.db_target, slug):
                if settings.allow_refresh_existing:
                    refreshed_slug = f"{base_slug}-{utc_now().strftime('%Y%m%d')}"
                    if database.has_post_slug(settings.db_target, refreshed_slug):
                        skipped += 1
                        continue
                    slug = refreshed_slug
                else:
                    skipped += 1
                    continue

            try:
                offer = choose_offer(trend.keyword, offers, min_overlap=1)
                offer_url = build_offer_url(
                    offer,
                    affiliate_tag=settings.affiliate_tag,
                    keyword=trend.keyword,
                    slug=slug,
                )
                draft = generate_post(trend, offer)
                draft.slug = slug

                if draft.word_count < settings.quality_min_word_count:
                    failed += 1
                    continue

                html_path = "dry-run"
                if not dry_run:
                    html_path = render_post(
                        settings.output_dir,
                        post=draft,
                        offer=offer,
                        offer_url=offer_url,
                        disclosure=settings.affiliate_disclosure,
                        api_base_url=settings.effective_api_base_url,
                        stripe_enabled=bool(settings.stripe_price_id),
                    )
                    database.insert_post(
                        settings.db_target,
                        slug=draft.slug,
                        title=draft.title,
                        keyword=draft.keyword,
                        summary=draft.summary,
                        source_url=trend.source_url,
                        offer_name=offer.name,
                        offer_url=offer_url,
                        html_path=html_path,
                        word_count=draft.word_count,
                    )

                published_posts.append(
                    {
                        "slug": draft.slug,
                        "title": draft.title,
                        "summary": draft.summary,
                        "offer_name": offer.name,
                        "html_path": html_path,
                    }
                )
                created += 1
            except Exception:
                failed += 1

        if not dry_run:
            recent = database.list_recent_posts(settings.db_target, limit=100)
            render_index(settings.output_dir, recent)

        result = asdict(RunResult(created=created, skipped=skipped, failed=failed, posts=published_posts))
        status = "success" if failed == 0 else "partial"
        database.finish_run(settings.db_target, run_id=run_id, status=status, summary=result)
        return result
    except Exception as exc:
        result = {
            "created": created,
            "skipped": skipped,
            "failed": failed + 1,
            "posts": published_posts,
            "error": str(exc),
        }
        database.finish_run(settings.db_target, run_id=run_id, status="failed", summary=result)
        return result
