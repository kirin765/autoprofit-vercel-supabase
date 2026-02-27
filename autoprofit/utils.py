from __future__ import annotations

import re
from datetime import datetime, timezone


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", value).strip().lower()
    cleaned = re.sub(r"[\s_-]+", "-", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned)
    return cleaned or f"post-{utc_now().strftime('%Y%m%d%H%M%S')}"


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)
