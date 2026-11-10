"""Share-link tests.

The security property that matters: a share token is HMAC-signed, so a stranger
can open a shared plan without the paywall becoming an unlimited free analysis
endpoint. These tests run the real signing/verification code and the real quota
enforcement — nothing is stubbed except the outbound Lemon Squeezy call, which
these tests do not touch.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services" / "api"))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DRAFTMASTER_DATABASE_URL", f"sqlite:///{tmp_path/'share.db'}")
    monkeypatch.setenv("DRAFTMASTER_REDIS_URL", "")
    monkeypatch.setenv("DRAFTMASTER_ARTIFACT_PATH", str(ROOT / "data" / "artifacts" / "draftmaster-data.json"))
    monkeypatch.setenv("DRAFTMASTER_SECRET_KEY", "share-signing-secret")
    monkeypatch.setenv("DRAFTMASTER_LEMONSQUEEZY_API_KEY", "")
    monkeypatch.setenv("DRAFTMASTER_LEMONSQUEEZY_STORE_ID", "")
    monkeypatch.setenv("DRAFTMASTER_LEMONSQUEEZY_CHECKOUT_URL", "")

    import draftmaster_api.config as config

    config.get_settings.cache_clear()

    from draftmaster_api.main import create_app

    app = create_app()
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c
    config.get_settings.cache_clear()


def _ids(client) -> dict[str, int]:
    return {h["localized_name"]: h["id"] for h in client.get("/api/heroes").json()}


def test_create_share_returns_signed_token_and_path(client):
    ids = _ids(client)
    r = client.post(
        "/api/share",
        json={"enemy_hero_ids": [ids["Lion"], ids["Axe"]], "role": "carry"},
        headers={"x-user-id": "sharer"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token"] and body["token"].count(".") == 1
    assert body["path"] == f"/share/{body['token']}"
    assert 0 <= body["win_probability"] <= 100


def test_render_share_returns_plan_without_usage_or_quota(client):
    ids = _ids(client)
    created = client.post(
        "/api/share",
        json={"enemy_hero_ids": [ids["Lion"], ids["Axe"]]},
        headers={"x-user-id": "sharer"},
    ).json()

    # A fresh viewer with no headers at all — no auth, no user id, no quota.
    for _ in range(5):
        r = client.get(f"/api/share/{created['token']}")
        assert r.status_code == 200, r.text
        plan = r.json()
        # The advertised pick (used by the OG card) must match the plan shown.
        assert plan["best_hero"]["hero_id"] == _token_hero_id(created["token"])
        # A shared view is read-only: it must not leak a quota count.
        assert "usage" not in plan


def _token_hero_id(token: str) -> int:
    import base64
    import json as _json

    body = token.split(".")[0]
    padded = body + "=" * (-len(body) % 4)
    return _json.loads(base64.urlsafe_b64decode(padded))["p"]["h"]


def test_forged_token_is_rejected(client):
    ids = _ids(client)
    created = client.post(
        "/api/share", json={"enemy_hero_ids": [ids["Lion"]]}, headers={"x-user-id": "sharer"}
    ).json()
    body, _, _sig = created["token"].partition(".")

    # A tampered payload with the original signature must not verify.
    import base64
    import json as _json

    forged_body = base64.urlsafe_b64encode(
        _json.dumps({"p": {"e": [ids["Lion"], ids["Axe"], ids["Lina"]]}, "exp": int(time.time()) + 999}).encode()
    ).decode().rstrip("=")
    assert client.get(f"/api/share/{forged_body}.{_sig}").status_code == 404
    # A garbage signature must not verify.
    assert client.get(f"/api/share/{body}.deadbeef").status_code == 404
    # A structurally invalid token must not verify.
    assert client.get("/api/share/not-a-token").status_code == 404


def test_expired_token_is_rejected(client, monkeypatch):
    from draftmaster_api import share as share_mod

    ids = _ids(client)
    created = client.post(
        "/api/share", json={"enemy_hero_ids": [ids["Lion"]]}, headers={"x-user-id": "sharer"}
    ).json()

    # Verify at a point far in the future.
    real_time = time.time
    monkeypatch.setattr(share_mod.time, "time", lambda: real_time() + share_mod.SHARE_TTL_SECONDS + 10)
    assert client.get(f"/api/share/{created['token']}").status_code == 404


def test_share_is_charged_against_the_daily_quota(client):
    ids = _ids(client)
    heroes = ["Lion", "Axe", "Lina", "Sniper"]
    statuses = [
        client.post(
            "/api/share", json={"enemy_hero_ids": [ids[name]]}, headers={"x-user-id": "quota-user"}
        ).status_code
        for name in heroes
    ]
    # The free plan allows three analyses a day, then the paywall fires.
    assert statuses[:3] == [200, 200, 200]
    assert statuses[3] == 402


def test_resharing_the_same_draft_is_free(client):
    ids = _ids(client)
    payload = {"enemy_hero_ids": [ids["Lion"], ids["Axe"]]}
    headers = {"x-user-id": "repeat-user"}
    for _ in range(6):
        r = client.post("/api/share", json=payload, headers=headers)
        assert r.status_code == 200, r.text


def test_no_signing_key_disables_public_shares(client, monkeypatch):
    """Without a secret key the product runs free-only; minting must not lie."""
    import draftmaster_api.config as config

    config.get_settings.cache_clear()
    monkeypatch.setenv("DRAFTMASTER_SECRET_KEY", "")
    from draftmaster_api.main import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as c:
        ids = {h["localized_name"]: h["id"] for h in c.get("/api/heroes").json()}
        r = c.post("/api/share", json={"enemy_hero_ids": [ids["Lion"]]}, headers={"x-user-id": "x"})
        assert r.status_code == 200
        assert r.json()["token"] == ""
        assert r.json()["path"] == ""
    config.get_settings.cache_clear()
