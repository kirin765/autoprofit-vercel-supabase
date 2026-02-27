from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from autoprofit import database, web
from autoprofit.settings import Settings


def test_health_includes_database_provider(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "site",
        db_path=tmp_path / "data" / "db.sqlite3",
    )
    monkeypatch.setattr(web, "get_settings", lambda: settings)
    client = TestClient(web.app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["database_provider"] == "sqlite"


def test_redirect_endpoint_logs_click(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "site",
        db_path=tmp_path / "data" / "db.sqlite3",
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)

    database.initialize_db(settings.db_path)
    database.insert_post(
        settings.db_path,
        slug="sample",
        title="Sample",
        keyword="sample keyword",
        summary="summary",
        source_url="test",
        offer_name="Shopify",
        offer_url="https://example.com/offer",
        html_path="public/posts/sample.html",
        word_count=300,
    )

    monkeypatch.setattr(web, "get_settings", lambda: settings)
    client = TestClient(web.app)

    response = client.get("/go/sample", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/offer"

    metrics = database.get_metrics(settings.db_path)
    assert metrics["clicks"] == 1


def test_cron_requires_token_when_configured(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "site",
        db_path=tmp_path / "data" / "db.sqlite3",
        cron_token="secret-token",
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    database.initialize_db(settings.db_path)

    monkeypatch.setattr(web, "get_settings", lambda: settings)
    client = TestClient(web.app)

    unauthorized = client.post("/api/cron/run")
    assert unauthorized.status_code == 401


def test_stripe_webhook_upserts_subscription(tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        data_dir=tmp_path / "data",
        output_dir=tmp_path / "site",
        db_path=tmp_path / "data" / "db.sqlite3",
        stripe_secret_key="sk_test_demo",
        stripe_webhook_secret="whsec_demo",
    )
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    database.initialize_db(settings.db_path)

    class DummyEvent(dict):
        def to_dict_recursive(self) -> dict[str, Any]:
            return dict(self)

    def fake_construct_event(payload: bytes, sig_header: str, secret: str) -> DummyEvent:
        assert sig_header == "sig_valid"
        assert secret == "whsec_demo"
        return DummyEvent(
            {
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "subscription": "sub_123",
                        "customer_email": "user@example.com",
                        "customer_details": {"email": "user@example.com"},
                    }
                },
            }
        )

    monkeypatch.setattr(web, "get_settings", lambda: settings)
    monkeypatch.setattr(web.stripe.Webhook, "construct_event", fake_construct_event)
    client = TestClient(web.app)

    response = client.post(
        "/api/stripe/webhook",
        headers={"stripe-signature": "sig_valid"},
        content=b"{}",
    )
    assert response.status_code == 200

    status = client.get("/api/subscription/status", params={"email": "user@example.com"})
    assert status.status_code == 200
    payload = status.json()
    assert payload["active"] is True
    assert payload["status"] == "active"
