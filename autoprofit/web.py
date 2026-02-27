from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

import stripe
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from autoprofit import database
from autoprofit.pipeline import run_pipeline
from autoprofit.settings import Settings, get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    database.initialize_db(settings.db_target)
    yield


app = FastAPI(title="Autoprofit API", version="0.2.0", lifespan=lifespan)


def _as_iso_timestamp(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except Exception:
        return None


def _resolve_customer_email(subscription_obj: dict[str, Any], settings: Settings) -> Optional[str]:
    metadata = subscription_obj.get("metadata") or {}
    if metadata.get("email"):
        return str(metadata["email"])

    customer_id = subscription_obj.get("customer")
    if not customer_id:
        return None

    stripe.api_key = settings.stripe_secret_key
    try:
        customer = stripe.Customer.retrieve(customer_id)
        email = customer.get("email")
        if email:
            return str(email)
    except Exception:
        return None
    return None


def _record_checkout_completion(settings: Settings, event: dict[str, Any]) -> None:
    data_object = (event.get("data") or {}).get("object") or {}
    subscription_id = data_object.get("subscription")
    if not subscription_id:
        return

    customer_details = data_object.get("customer_details") or {}
    customer_email = data_object.get("customer_email") or customer_details.get("email")
    normalized_email = str(customer_email).strip().lower() if customer_email else None

    database.upsert_subscription(
        settings.db_target,
        subscription_id=str(subscription_id),
        customer_email=normalized_email,
        status="active",
        current_period_end=None,
        source_event=str(event.get("type", "checkout.session.completed")),
        raw_payload=event,
    )


def _record_subscription_update(settings: Settings, event: dict[str, Any]) -> None:
    data_object = (event.get("data") or {}).get("object") or {}
    subscription_id = data_object.get("id")
    if not subscription_id:
        return

    customer_email = _resolve_customer_email(data_object, settings)
    normalized_email = customer_email.strip().lower() if customer_email else None
    database.upsert_subscription(
        settings.db_target,
        subscription_id=str(subscription_id),
        customer_email=normalized_email,
        status=str(data_object.get("status") or "unknown"),
        current_period_end=_as_iso_timestamp(data_object.get("current_period_end")),
        source_event=str(event.get("type", "customer.subscription.updated")),
        raw_payload=event,
    )


def _handle_stripe_event(settings: Settings, event: dict[str, Any]) -> None:
    event_type = str(event.get("type", ""))

    if event_type == "checkout.session.completed":
        _record_checkout_completion(settings, event)
        return

    if event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        _record_subscription_update(settings, event)


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {"status": "ok", "database_provider": settings.database_provider}


@app.post("/api/cron/run")
def cron_run(x_cron_token: str = Header(default="")) -> dict[str, Any]:
    settings = get_settings()
    if settings.cron_token and x_cron_token != settings.cron_token:
        raise HTTPException(status_code=401, detail="Invalid cron token")
    return run_pipeline(settings)


@app.get("/api/metrics")
def metrics() -> dict[str, int]:
    settings = get_settings()
    return database.get_metrics(settings.db_target)


@app.get("/go/{slug}")
def redirect_affiliate(slug: str, request: Request) -> RedirectResponse:
    settings = get_settings()
    destination = database.get_post_offer_url(settings.db_target, slug)
    if not destination:
        raise HTTPException(status_code=404, detail="Unknown campaign slug")

    database.log_click(
        settings.db_target,
        slug=slug,
        destination_url=destination,
        referrer=request.headers.get("referer", ""),
        ip_address=request.client.host if request.client else "",
    )
    return RedirectResponse(destination, status_code=307)


@app.post("/api/stripe/checkout")
def create_checkout_session(payload: dict[str, Any]) -> JSONResponse:
    settings = get_settings()
    if not settings.stripe_secret_key or not settings.stripe_price_id:
        raise HTTPException(status_code=503, detail="Stripe is not configured")

    stripe.api_key = settings.stripe_secret_key
    email = payload.get("email")

    checkout_payload: dict[str, Any] = {
        "mode": "subscription",
        "success_url": settings.stripe_success_url,
        "cancel_url": settings.stripe_cancel_url,
        "line_items": [{"price": settings.stripe_price_id, "quantity": 1}],
    }
    if email:
        checkout_payload["customer_email"] = str(email)

    try:
        session = stripe.checkout.Session.create(**checkout_payload)
        checkout_url = session.get("url")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Stripe error: {exc}") from exc

    if not checkout_url:
        raise HTTPException(status_code=502, detail="Stripe returned no checkout URL")

    return JSONResponse({"checkout_url": str(checkout_url)})


@app.post("/api/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(default="", alias="stripe-signature"),
) -> JSONResponse:
    settings = get_settings()
    if not settings.stripe_secret_key or not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook is not configured")

    payload = await request.body()

    stripe.api_key = settings.stripe_secret_key
    try:
        event_obj = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.stripe_webhook_secret,
        )
    except stripe.error.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Webhook parsing error: {exc}") from exc

    event = event_obj.to_dict_recursive() if hasattr(event_obj, "to_dict_recursive") else dict(event_obj)
    _handle_stripe_event(settings, event)
    return JSONResponse({"received": True})


@app.get("/api/subscription/status")
def subscription_status(email: str) -> dict[str, Any]:
    settings = get_settings()
    row = database.get_subscription_by_email(settings.db_target, email=email.strip().lower())
    if not row:
        return {
            "email": email,
            "active": False,
            "status": "unknown",
            "subscription_id": None,
            "current_period_end": None,
        }

    status = str(row.get("status") or "unknown")
    return {
        "email": email,
        "active": status in {"active", "trialing"},
        "status": status,
        "subscription_id": row.get("subscription_id"),
        "current_period_end": row.get("current_period_end"),
    }
