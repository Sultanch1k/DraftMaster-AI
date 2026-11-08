"""Billing flow tests.

The only thing stubbed is the outbound HTTP call to Lemon Squeezy — the real
network edge. Everything else (signing, entitlement storage, quota enforcement,
revocation) runs against the real code.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services" / "api"))


class _FakeResponse:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body

    def json(self) -> dict:
        return self._body


class _FakeAsyncClient:
    """Stands in for httpx.AsyncClient at the Lemon Squeezy boundary."""

    def __init__(self, status_code: int = 200, body: dict | None = None):
        self._status = status_code
        self._body = body or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, *args, **kwargs):
        return _FakeResponse(self._status, self._body)


ACTIVE_LICENSE = {
    "data": {
        "attributes": {
            "status": "active",
            "customer_email": "payer@example.com",
            "variant_id": 123,
            "expires_at": None,
        }
    }
}


@pytest.fixture()
def billing_client(tmp_path, monkeypatch):
    """A client whose server thinks Lemon Squeezy is fully configured."""
    from fastapi.testclient import TestClient

    monkeypatch.setenv("DRAFTMASTER_DATABASE_URL", f"sqlite:///{tmp_path/'billing.db'}")
    monkeypatch.setenv("DRAFTMASTER_REDIS_URL", "")
    monkeypatch.setenv("DRAFTMASTER_ARTIFACT_PATH", str(ROOT / "data" / "artifacts" / "draftmaster-data.json"))
    monkeypatch.setenv("DRAFTMASTER_SECRET_KEY", "test-signing-secret")
    monkeypatch.setenv("DRAFTMASTER_LEMONSQUEEZY_API_KEY", "fake-api-key")
    monkeypatch.setenv("DRAFTMASTER_LEMONSQUEEZY_STORE_ID", "12345")
    monkeypatch.setenv("DRAFTMASTER_LEMONSQUEEZY_CHECKOUT_URL", "https://store.lemonsqueezy.com/checkout/buy/xyz")
    monkeypatch.setenv("DRAFTMASTER_SUPPORT_EMAIL", "support@draftmaster.wiki")

    import draftmaster_api.config as config

    config.get_settings.cache_clear()

    from draftmaster_api.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c
    config.get_settings.cache_clear()


def test_config_enabled_when_credentials_present(billing_client):
    body = billing_client.get("/api/billing/config").json()
    assert body["enabled"] is True
    assert body["checkout_url"].endswith("/xyz")


def test_activate_valid_key_grants_unlimited_analyses(billing_client, monkeypatch):
    """Full happy path: paste a key, get premium, quota stops applying."""
    import draftmaster_api.billing as billing

    monkeypatch.setattr(billing.httpx, "AsyncClient", lambda *a, **k: _FakeAsyncClient(200, ACTIVE_LICENSE))

    ids = {h["localized_name"]: h["id"] for h in billing_client.get("/api/heroes").json()}
    act = billing_client.post("/api/billing/activate", json={"license_key": "REAL-KEY-1234"})
    assert act.status_code == 200
    token = act.json()["token"]
    assert token and act.json()["plan"] == "premium"

    headers = {"x-user-id": "payer", "authorization": f"Bearer {token}"}
    for name in ("Lion", "Axe", "Lina", "Sniper", "Luna", "Pudge"):
        r = billing_client.post("/api/panic", json={"enemy_hero_ids": [ids[name]]}, headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["usage"]["plan"] == "premium"

    # The session endpoint agrees, and the sale is counted.
    session = billing_client.get("/api/billing/session", headers=headers).json()
    assert session["plan"] == "premium"
    metrics = billing_client.get("/api/metrics", headers={"x-metrics-token": "test-signing-secret"}).json()
    assert metrics["paying_customers"] == 1


def test_activate_rejects_inactive_license(billing_client, monkeypatch):
    import draftmaster_api.billing as billing

    body = {"data": {"attributes": {"status": "expired", "customer_email": "x@y.com"}}}
    monkeypatch.setattr(billing.httpx, "AsyncClient", lambda *a, **k: _FakeAsyncClient(200, body))
    r = billing_client.post("/api/billing/activate", json={"license_key": "EXPIRED-KEY"})
    assert r.status_code == 422
    assert "not active" in r.json()["detail"].lower()


def test_activate_survives_provider_outage(billing_client, monkeypatch):
    import draftmaster_api.billing as billing

    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(billing.httpx, "AsyncClient", boom)
    r = billing_client.post("/api/billing/activate", json={"license_key": "ANY-KEY-1234"})
    assert r.status_code == 422
    assert "traceback" not in r.text.lower()


def test_webhook_revokes_entitlement_on_refund(billing_client, monkeypatch):
    """A signed refund webhook must strip premium from the buyer."""
    import hashlib
    import hmac
    import json

    import draftmaster_api.billing as billing

    monkeypatch.setenv("DRAFTMASTER_LEMONSQUEEZY_WEBHOOK_SECRET", "whsec")
    billing_client.app.state.settings.lemonsqueezy_webhook_secret = "whsec"

    monkeypatch.setattr(billing.httpx, "AsyncClient", lambda *a, **k: _FakeAsyncClient(200, ACTIVE_LICENSE))
    token = billing_client.post("/api/billing/activate", json={"license_key": "REFUND-ME"}).json()["token"]
    assert token

    payload = json.dumps(
        {
            "meta": {"event_name": "order_refunded"},
            "data": {"attributes": {"user_email": "payer@example.com"}},
        }
    ).encode()
    sig = hmac.new(b"whsec", payload, hashlib.sha256).hexdigest()
    hook = billing_client.post(
        "/api/billing/webhook", content=payload, headers={"x-signature": sig, "content-type": "application/json"}
    )
    assert hook.status_code == 200

    session = billing_client.get("/api/billing/session", headers={"authorization": f"Bearer {token}"}).json()
    assert session["plan"] == "free"


def test_managed_postgres_url_uses_installed_driver():
    """Render/Heroku inject `postgresql://`; we ship psycopg 3, not psycopg2."""
    sys.path.insert(0, str(ROOT / "services" / "api"))
    from draftmaster_api.infra import normalize_database_url

    assert normalize_database_url("postgres://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"
    assert normalize_database_url("postgresql://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"
    # Explicit driver and non-Postgres URLs must be left alone.
    assert normalize_database_url("postgresql+psycopg://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalize_database_url("sqlite:///x.db") == "sqlite:///x.db"
