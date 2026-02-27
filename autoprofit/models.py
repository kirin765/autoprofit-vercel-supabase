from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TrendItem:
    title: str
    keyword: str
    source_url: str
    score: float = 0.0


@dataclass
class Offer:
    name: str
    slug: str
    categories: list[str]
    affiliate_url: str
    fallback_url: str
    cta_text: str
    commission_rate: float = 0.0


@dataclass
class DraftPost:
    slug: str
    title: str
    keyword: str
    summary: str
    sections: list[tuple[str, str]] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        total_text = " ".join([self.title, self.summary] + [body for _, body in self.sections])
        return len(total_text.split())
