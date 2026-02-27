from __future__ import annotations

import re
from pathlib import Path

import feedparser
import yaml

from autoprofit.models import TrendItem


BUYER_INTENT_TERMS = {
    "best": 1.2,
    "buy": 1.2,
    "deal": 1.15,
    "price": 1.1,
    "review": 1.05,
    "vs": 1.05,
    "top": 1.0,
}


def _normalize_keyword(raw: str) -> str:
    cleaned = re.sub(r"\s+", " ", raw).strip()
    cleaned = cleaned.replace("#", "")
    return cleaned[:120]


def _intent_score(keyword: str) -> float:
    tokens = set(re.findall(r"[a-zA-Z0-9]+", keyword.lower()))
    score = 1.0
    for token, weight in BUYER_INTENT_TERMS.items():
        if token in tokens:
            score *= weight
    score += min(len(tokens) / 25, 0.5)
    return round(score, 4)


def fetch_trends(rss_url: str, timeout_seconds: float, limit: int) -> list[TrendItem]:
    parsed = feedparser.parse(rss_url, request_headers={"User-Agent": "autoprofit/0.1"})
    trends: list[TrendItem] = []
    for entry in parsed.entries:
        title = _normalize_keyword(getattr(entry, "title", "").strip())
        if not title:
            continue
        trends.append(
            TrendItem(
                title=title,
                keyword=title,
                source_url=getattr(entry, "link", rss_url),
                score=_intent_score(title),
            )
        )
        if len(trends) >= limit:
            break
    return trends


def load_fallback_trends(path: Path, limit: int) -> list[TrendItem]:
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    keywords: list[str] = payload.get("fallback_keywords", [])
    items: list[TrendItem] = []
    for keyword in keywords[:limit]:
        items.append(
            TrendItem(
                title=keyword,
                keyword=keyword,
                source_url="local-fallback",
                score=_intent_score(keyword),
            )
        )
    return items
