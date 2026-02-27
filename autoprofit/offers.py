from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qsl, urlunparse

import yaml

from autoprofit.models import Offer


def load_offers(path: Path) -> list[Offer]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    offers: list[Offer] = []
    for raw in payload.get("offers", []):
        offers.append(
            Offer(
                name=raw["name"],
                slug=raw["slug"],
                categories=list(raw.get("categories", [])),
                affiliate_url=raw["affiliate_url"],
                fallback_url=raw.get("fallback_url", raw["affiliate_url"]),
                cta_text=raw.get("cta_text", "Check current pricing"),
                commission_rate=float(raw.get("commission_rate", 0.0)),
            )
        )
    return offers


def choose_offer(keyword: str, offers: list[Offer], min_overlap: int = 0) -> Offer:
    if not offers:
        raise ValueError("No offers are configured")

    tokens = set(re.findall(r"[a-zA-Z0-9]+", keyword.lower()))

    def score(offer: Offer) -> tuple[float, float]:
        category_overlap = len(tokens.intersection(set(offer.categories)))
        return (float(category_overlap), offer.commission_rate)

    best_offer = max(offers, key=score)
    best_overlap = len(tokens.intersection(set(best_offer.categories)))
    if best_overlap < min_overlap:
        raise ValueError("No relevant offer match")
    return best_offer


def build_offer_url(
    offer: Offer,
    *,
    affiliate_tag: str,
    keyword: str,
    slug: str,
) -> str:
    base = offer.affiliate_url
    if "{affiliate_tag}" in base and not affiliate_tag:
        base = offer.fallback_url
    elif "{affiliate_tag}" in base:
        base = base.format(affiliate_tag=affiliate_tag)

    parsed = urlparse(base)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params.update(
        {
            "utm_source": "autoprofit",
            "utm_medium": "affiliate",
            "utm_campaign": slug,
            "utm_term": keyword,
        }
    )
    new_query = urlencode(params)
    return urlunparse(parsed._replace(query=new_query))
