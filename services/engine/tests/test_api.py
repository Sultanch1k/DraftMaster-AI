"""API integration tests using the real FastAPI app (no mocks).

External-network endpoints (match coach) are tested against the live OpenDota
API only when DRAFTMASTER_LIVE_TESTS=1, so CI stays deterministic while the
core product surface is always exercised for real.
"""
from __future__ import annotations

import os

import pytest

LIVE = os.environ.get("DRAFTMASTER_LIVE_TESTS") == "1"


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["hero_count"] >= 120


def test_root_lists_flagship_endpoints(client):
    r = client.get("/")
    assert r.status_code == 200
    assert any("panic" in f for f in r.json()["flagship"])


def test_heroes_endpoint(client):
    r = client.get("/api/heroes")
    assert r.status_code == 200
    heroes = r.json()
    assert len(heroes) >= 120
    assert {"id", "localized_name", "roles", "icon"} <= set(heroes[0])


def test_hero_detail_and_404(client):
    assert client.get("/api/heroes/1").status_code == 200
    assert client.get("/api/heroes/99999").status_code == 404


def test_hero_matchups_endpoint(client):
    r = client.get("/api/heroes/1/matchups")
    assert r.status_code == 200
    body = r.json()
    assert body["best_against"] and body["worst_against"]
    assert body["best_against"][0]["score"] >= body["worst_against"][0]["score"]


def test_items_endpoint(client):
    r = client.get("/api/items")
    assert r.status_code == 200
    assert any(i["key"] == "black_king_bar" for i in r.json())


def test_meta_endpoint(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    body = r.json()
    assert body["patch"]
    assert len(body["trending"]) == 15


def _ids(client):
    return {h["localized_name"]: h["id"] for h in client.get("/api/heroes").json()}


def test_panic_returns_one_screen_payload(client):
    ids = _ids(client)
    r = client.post(
        "/api/panic",
        json={
            "enemy_hero_ids": [ids["Lion"], ids["Axe"], ids["Shadow Shaman"]],
            "role": "carry",
            "rank_tier": 70,
        },
    )
    assert r.status_code == 200
    body = r.json()
    for key in (
        "best_hero",
        "full_build",
        "danger_heroes",
        "power_spikes",
        "kill_priority",
        "win_conditions",
        "items_to_avoid",
        "one_sentence_win_plan",
        "win_probability",
    ):
        assert key in body, key
    assert body["best_hero"]["localized_name"]
    assert body["one_sentence_win_plan"].endswith(".")


def test_panic_is_fast(client):
    ids = _ids(client)
    r = client.post(
        "/api/panic",
        json={"enemy_hero_ids": [ids["Lion"], ids["Axe"], ids["Shadow Shaman"]]},
    )
    assert r.status_code == 200
    ms = float(r.headers["x-response-time-ms"])
    # The product promise is "under 5 seconds"; the engine target is far lower.
    assert ms < 2000, f"panic took {ms} ms"


def test_analyse_returns_full_report(client):
    ids = _ids(client)
    r = client.post(
        "/api/analyse",
        json={
            "enemy_hero_ids": [ids["Lion"], ids["Axe"], ids["Shadow Shaman"]],
            "hero_id": ids["Juggernaut"],
            "role": "carry",
        },
    )
    assert r.status_code == 200
    report = r.json()["report"]
    assert len(report["best_picks"]) == 5
    assert len(report["skill_build"]["levels"]) == 30
    assert len(report["match_plan"]) == 5
    assert report["target_priority"]
    assert set(report["win_conditions"]) == {"primary", "secondary", "emergency"}


def test_analyse_is_cached_on_second_call(client):
    ids = _ids(client)
    payload = {
        "enemy_hero_ids": [ids["Lion"], ids["Axe"]],
        "hero_id": ids["Juggernaut"],
        "role": "carry",
    }
    first = client.post("/api/analyse", json=payload).json()
    second = client.post("/api/analyse", json=payload).json()
    assert first["cached"] is False
    assert second["cached"] is True


def test_analyse_rejects_unknown_hero(client):
    r = client.post("/api/analyse", json={"enemy_hero_ids": [99999]})
    assert r.status_code == 422


def test_analyse_rejects_empty_draft(client):
    r = client.post("/api/analyse", json={"enemy_hero_ids": []})
    assert r.status_code == 422


def test_analyse_rejects_too_many_enemies(client):
    ids = _ids(client)
    many = [ids[n] for n in ("Lion", "Axe", "Shadow Shaman", "Sniper", "Huskar", "Zeus")]
    r = client.post("/api/analyse", json={"enemy_hero_ids": many})
    assert r.status_code == 422


def test_win_probability_endpoint(client):
    ids = _ids(client)
    r = client.post(
        "/api/win-probability",
        json={"enemy_hero_ids": [ids["Lion"], ids["Axe"]], "hero_id": ids["Juggernaut"], "rank_tier": 70},
    )
    assert r.status_code == 200
    body = r.json()
    assert 0 < body["player_win_probability"] < 100
    assert body["factors"]


def test_threat_analysis_endpoint(client):
    ids = _ids(client)
    r = client.post(
        "/api/threat-analysis",
        json={"enemy_hero_ids": [ids["Lion"], ids["Axe"]], "hero_id": ids["Juggernaut"]},
    )
    assert r.status_code == 200
    assert len(r.json()["scores"]) == 14


def test_free_quota_enforced(client):
    ids = _ids(client)
    payload = {"enemy_hero_ids": [ids["Lion"]]}
    headers = {"x-user-id": "quota-test-user"}
    codes = [client.post("/api/panic", json=payload, headers=headers).status_code for _ in range(4)]
    assert codes[:3] == [200, 200, 200]
    assert codes[3] == 402


def test_premium_token_bypasses_quota(client):
    ids = _ids(client)
    payload = {"enemy_hero_ids": [ids["Lion"]]}
    headers = {"x-user-id": "premium-user", "authorization": "Bearer premium-token"}
    for _ in range(5):
        assert client.post("/api/panic", json=payload, headers=headers).status_code == 200


def test_profile_roundtrip(client):
    payload = {
        "user_id": "u-1",
        "role": "carry",
        "rank_tier": 70,
        "favorite_heroes": [1, 2, 3],
        "comfort": {"1": 0.9},
        "playstyle": "aggressive",
    }
    assert client.put("/api/profile", json=payload).status_code == 200
    got = client.get("/api/profile/u-1").json()
    assert got["role"] == "carry"
    assert client.get("/api/profile/missing").status_code == 404


@pytest.mark.skipif(not LIVE, reason="requires live OpenDota API")
def test_match_summary_live(client):
    # Pull a fresh parsed pro match id, then summarise it.
    import httpx

    pro = httpx.get("https://api.opendota.com/api/proMatches", timeout=30).json()
    mid = pro[0]["match_id"]
    r = client.get(f"/api/match/{mid}")
    assert r.status_code == 200
    assert len(r.json()["players"]) == 10
