from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
    select,
    update,
)
from sqlalchemy.engine import Engine

from autoprofit.utils import utc_now

DBTarget = Union[Path, str]

metadata = MetaData()

posts_table = Table(
    "posts",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("slug", String(255), unique=True, nullable=False),
    Column("title", Text, nullable=False),
    Column("keyword", Text, nullable=False),
    Column("summary", Text, nullable=False),
    Column("source_url", Text, nullable=False),
    Column("offer_name", Text, nullable=False),
    Column("offer_url", Text, nullable=False),
    Column("html_path", Text, nullable=False),
    Column("word_count", Integer, nullable=False),
    Column("created_at", String(64), nullable=False),
)

runs_table = Table(
    "runs",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("started_at", String(64), nullable=False),
    Column("finished_at", String(64), nullable=True),
    Column("status", String(32), nullable=True),
    Column("summary_json", Text, nullable=True),
)

clicks_table = Table(
    "clicks",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("slug", Text, nullable=False),
    Column("destination_url", Text, nullable=False),
    Column("referrer", Text, nullable=True),
    Column("ip_address", Text, nullable=True),
    Column("created_at", String(64), nullable=False),
)

subscriptions_table = Table(
    "subscriptions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("subscription_id", String(255), unique=True, nullable=False),
    Column("customer_email", String(320), nullable=True),
    Column("status", String(64), nullable=False),
    Column("current_period_end", String(64), nullable=True),
    Column("source_event", String(128), nullable=False),
    Column("raw_json", Text, nullable=False),
    Column("updated_at", String(64), nullable=False),
)


def _normalize_db_url(db_target: DBTarget) -> str:
    if isinstance(db_target, Path):
        path = db_target.expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path}"

    target = str(db_target).strip()
    if not target:
        raise ValueError("Database target is empty")

    if target.startswith("postgres://"):
        target = "postgresql://" + target[len("postgres://") :]

    if target.startswith("postgresql://"):
        parsed = urlparse(target)
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        hostname = (parsed.hostname or "").lower()
        is_supabase = "supabase.co" in hostname or "supabase.in" in hostname
        if is_supabase and "sslmode" not in params:
            params["sslmode"] = "require"

        query = urlencode(params)
        postgres_url = urlunparse(parsed._replace(query=query))
        return "postgresql+psycopg://" + postgres_url[len("postgresql://") :]

    if target.startswith("sqlite:///") or target.startswith("postgresql+psycopg://"):
        return target

    # Raw filesystem path fallback.
    path = Path(target).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


@lru_cache(maxsize=8)
def _engine_for_url(db_url: str) -> Engine:
    kwargs: dict[str, Any] = {"future": True, "pool_pre_ping": True}
    if db_url.startswith("sqlite:///"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(db_url, **kwargs)


def _engine(db_target: DBTarget) -> Engine:
    db_url = _normalize_db_url(db_target)
    return _engine_for_url(db_url)


def initialize_db(db_target: DBTarget) -> None:
    metadata.create_all(_engine(db_target))


def has_post_slug(db_target: DBTarget, slug: str) -> bool:
    stmt = select(posts_table.c.id).where(posts_table.c.slug == slug).limit(1)
    with _engine(db_target).begin() as conn:
        row = conn.execute(stmt).first()
    return row is not None


def insert_post(
    db_target: DBTarget,
    *,
    slug: str,
    title: str,
    keyword: str,
    summary: str,
    source_url: str,
    offer_name: str,
    offer_url: str,
    html_path: str,
    word_count: int,
) -> None:
    with _engine(db_target).begin() as conn:
        conn.execute(
            posts_table.insert().values(
                slug=slug,
                title=title,
                keyword=keyword,
                summary=summary,
                source_url=source_url,
                offer_name=offer_name,
                offer_url=offer_url,
                html_path=html_path,
                word_count=word_count,
                created_at=utc_now().isoformat(),
            )
        )


def list_recent_posts(db_target: DBTarget, limit: int = 20) -> list[dict[str, Any]]:
    stmt = (
        select(
            posts_table.c.slug,
            posts_table.c.title,
            posts_table.c.keyword,
            posts_table.c.summary,
            posts_table.c.offer_name,
            posts_table.c.html_path,
            posts_table.c.created_at,
        )
        .order_by(posts_table.c.id.desc())
        .limit(limit)
    )
    with _engine(db_target).begin() as conn:
        rows = conn.execute(stmt).mappings().all()
    return [dict(row) for row in rows]


def get_post_offer_url(db_target: DBTarget, slug: str) -> Optional[str]:
    stmt = select(posts_table.c.offer_url).where(posts_table.c.slug == slug).limit(1)
    with _engine(db_target).begin() as conn:
        offer_url = conn.execute(stmt).scalar_one_or_none()
    if offer_url is None:
        return None
    return str(offer_url)


def log_click(
    db_target: DBTarget,
    *,
    slug: str,
    destination_url: str,
    referrer: str,
    ip_address: str,
) -> None:
    with _engine(db_target).begin() as conn:
        conn.execute(
            clicks_table.insert().values(
                slug=slug,
                destination_url=destination_url,
                referrer=referrer,
                ip_address=ip_address,
                created_at=utc_now().isoformat(),
            )
        )


def start_run(db_target: DBTarget) -> int:
    with _engine(db_target).begin() as conn:
        result = conn.execute(
            runs_table.insert().values(
                started_at=utc_now().isoformat(),
                status="running",
            )
        )
        inserted = result.inserted_primary_key
        if inserted and inserted[0] is not None:
            return int(inserted[0])

        latest = conn.execute(select(runs_table.c.id).order_by(runs_table.c.id.desc()).limit(1)).scalar_one()
        return int(latest)


def finish_run(db_target: DBTarget, run_id: int, status: str, summary: dict[str, Any]) -> None:
    stmt = (
        update(runs_table)
        .where(runs_table.c.id == run_id)
        .values(
            finished_at=utc_now().isoformat(),
            status=status,
            summary_json=json.dumps(summary),
        )
    )
    with _engine(db_target).begin() as conn:
        conn.execute(stmt)


def get_metrics(db_target: DBTarget) -> dict[str, int]:
    with _engine(db_target).begin() as conn:
        posts_count = conn.execute(select(func.count()).select_from(posts_table)).scalar_one()
        clicks_count = conn.execute(select(func.count()).select_from(clicks_table)).scalar_one()
        run_count = conn.execute(select(func.count()).select_from(runs_table)).scalar_one()
    return {
        "posts": int(posts_count),
        "clicks": int(clicks_count),
        "runs": int(run_count),
    }


def upsert_subscription(
    db_target: DBTarget,
    *,
    subscription_id: str,
    customer_email: Optional[str],
    status: str,
    current_period_end: Optional[str],
    source_event: str,
    raw_payload: dict[str, Any],
) -> None:
    with _engine(db_target).begin() as conn:
        existing = conn.execute(
            select(subscriptions_table.c.id, subscriptions_table.c.customer_email).where(
                subscriptions_table.c.subscription_id == subscription_id
            )
        ).first()

        payload = {
            "customer_email": customer_email,
            "status": status,
            "current_period_end": current_period_end,
            "source_event": source_event,
            "raw_json": json.dumps(raw_payload),
            "updated_at": utc_now().isoformat(),
        }

        if existing is None:
            conn.execute(
                subscriptions_table.insert().values(
                    subscription_id=subscription_id,
                    **payload,
                )
            )
            return

        if not payload["customer_email"] and len(existing) > 1:
            payload["customer_email"] = existing[1]

        conn.execute(
            subscriptions_table.update()
            .where(subscriptions_table.c.subscription_id == subscription_id)
            .values(**payload)
        )


def get_subscription_by_email(db_target: DBTarget, email: str) -> Optional[dict[str, Any]]:
    stmt = (
        select(
            subscriptions_table.c.subscription_id,
            subscriptions_table.c.customer_email,
            subscriptions_table.c.status,
            subscriptions_table.c.current_period_end,
            subscriptions_table.c.updated_at,
        )
        .where(subscriptions_table.c.customer_email == email)
        .order_by(subscriptions_table.c.updated_at.desc())
        .limit(1)
    )
    with _engine(db_target).begin() as conn:
        row = conn.execute(stmt).mappings().first()
    if row is None:
        return None
    return dict(row)
