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


def test_analyse_includes_full_report_for_every_top_pick(client):
    """Every Top-5 candidate must ship a complete 11-section report.

    This is the highest-priority product requirement: clicking any recommended
    hero shows its full report immediately, and a single analysis never spends
    more than one quota unit on hero switching.
    """
    ids = _ids(client)
    report = client.post(
        "/api/analyse",
        json={
            "enemy_hero_ids": [ids["Lion"], ids["Axe"], ids["Shadow Shaman"]],
            "role": "carry",
        },
    ).json()["report"]

    picks = report["pick_reports"]
    assert set(picks) == {str(p["hero_id"]) for p in report["best_picks"]}
    required = {
        "why_this_hero",
        "threat_analysis",
        "item_build",
        "skill_build",
        "talents",
        "match_plan",
        "win_conditions",
        "target_priority",
        "power_spikes",
        "one_sentence_win_plan",
        "win_probability",
    }
    for hero_id, sub in picks.items():
        assert required <= set(sub), f"hero {hero_id} missing sections"
        assert len(sub["skill_build"]["levels"]) == 30
        assert len(sub["match_plan"]) == 5
        assert sub["item_build"]["hero"] == sub["draft_summary"]["hero"]
    # Each pick's report is hero-specific, not a copy of #1.
    item_heroes = {sub["item_build"]["hero"] for sub in picks.values()}
    assert len(item_heroes) == len(picks)


def test_pick_reports_are_localized_for_russian(client):
    ids = _ids(client)
    report = client.post(
        "/api/analyse",
        json={"enemy_hero_ids": [ids["Lion"], ids["Axe"]], "locale": "ru"},
        headers={"x-locale": "ru"},
    ).json()["report"]
    for sub in report["pick_reports"].values():
        assert sub["threat_analysis"]["labels"]["crowd_control"] == "Контроль"
        assert any("Выигрывает" in s or "лейн" in s or "контрол" in s for s in sub["why_this_hero"])


def test_quota_error_detail_is_localized(client):
    ids = _ids(client)
    headers = {"x-user-id": "ru-quota-user", "x-locale": "ru"}
    codes = [
        client.post("/api/panic", json={"enemy_hero_ids": [hid]}, headers=headers).status_code
        for hid in (ids["Lion"], ids["Axe"], ids["Shadow Shaman"], ids["Sniper"])
    ]
    assert codes[3] == 402
    detail = client.post(
        "/api/panic", json={"enemy_hero_ids": [ids["Sniper"]]}, headers=headers
    ).json()["detail"]
    assert "Бесплатный тариф" in detail


def test_analyse_why_this_hero_describes_the_requested_hero(client):
    """The `why_this_hero` prose must describe the picked hero, not always #1.

    Regression guard: the report used to reuse the top pick's reasoning even
    when the caller asked about a different hero. `best_picks` stays the ranked
    Top-5; the explicit `hero_id` drives the hero-specific sections.
    """
    ids = _ids(client)
    enemies = [ids["Lion"], ids["Axe"], ids["Shadow Shaman"]]
    top = client.post(
        "/api/analyse", json={"enemy_hero_ids": enemies, "role": "carry"}
    ).json()["report"]
    top_why = top["why_this_hero"]
    top_skill = top["skill_build"]

    # Pick the #2 recommendation explicitly and confirm the prose tracks it.
    second = top["best_picks"][1]
    explicit = client.post(
        "/api/analyse",
        json={"enemy_hero_ids": enemies, "hero_id": second["hero_id"], "role": "carry"},
    ).json()["report"]
    # Ranking is unchanged, but sections 2-11 now describe the requested hero.
    assert [p["hero_id"] for p in explicit["best_picks"]] == [
        p["hero_id"] for p in top["best_picks"]
    ]
    assert explicit["why_this_hero"] != top_why
    assert isinstance(explicit["why_this_hero"], list) and explicit["why_this_hero"]
    assert explicit["skill_build"] != top_skill
    assert explicit["item_build"]["hero"] == second["localized_name"]


def test_analyse_locale_russian_translates_prose_not_names(client):
    ids = _ids(client)
    payload = {
        "enemy_hero_ids": [ids["Lion"], ids["Axe"], ids["Shadow Shaman"]],
        "hero_id": ids["Juggernaut"],
        "role": "carry",
    }
    en = client.post("/api/analyse", json=payload).json()["report"]
    ru = client.post(
        "/api/analyse", json={**payload, "locale": "ru"}, headers={"x-locale": "ru"}
    ).json()["report"]

    # Prose is translated...
    assert ru["why_this_hero"] != en["why_this_hero"]
    assert any("Выигрывает" in s or "лейн" in s or "контрол" in s for s in ru["why_this_hero"])
    # ...but hero names and the numeric scores are untouched.
    assert [p["localized_name"] for p in ru["best_picks"]] == [
        p["localized_name"] for p in en["best_picks"]
    ]
    assert [p["final_score"] for p in ru["best_picks"]] == [
        p["final_score"] for p in en["best_picks"]
    ]
    assert ru["threat_analysis"]["labels"]["crowd_control"] == "Контроль"


def test_locale_is_part_of_cache_key(client):
    """EN and RU reports for the same draft must not share a cache entry."""
    ids = _ids(client)
    payload = {
        "enemy_hero_ids": [ids["Lion"], ids["Axe"]],
        "hero_id": ids["Juggernaut"],
        "role": "carry",
    }
    en = client.post("/api/analyse", json=payload).json()
    ru = client.post("/api/analyse", json={**payload, "locale": "ru"}).json()
    assert en["cached"] is False and ru["cached"] is False
    assert en["report"]["why_this_hero"] != ru["report"]["why_this_hero"]


def test_reference_and_winprob_endpoints_are_locale_aware(client):
    """Every prose-bearing endpoint honours `x-locale`, not just /analyse."""
    ids = _ids(client)
    meta_ru = client.get("/api/meta", headers={"x-locale": "ru"}).json()
    assert meta_ru["source"] == "публичным матчам OpenDota"

    body = {"enemy_hero_ids": [ids["Lion"], ids["Axe"]], "hero_id": ids["Juggernaut"]}
    wp_en = client.post("/api/win-probability", json=body).json()
    wp_ru = client.post("/api/win-probability", json=body, headers={"x-locale": "ru"}).json()
    assert wp_en["verdict"] != wp_ru["verdict"]
    assert wp_ru["factors"][0]["name"] == "Матчапы героев"
    # Numbers are identical across locales.
    assert wp_en["player_win_probability"] == wp_ru["player_win_probability"]


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
    headers = {"x-user-id": "quota-test-user"}
    # Distinct drafts consume quota; three are allowed and the fourth is blocked.
    codes = [
        client.post("/api/panic", json={"enemy_hero_ids": [hid]}, headers=headers).status_code
        for hid in (ids["Lion"], ids["Axe"], ids["Shadow Shaman"], ids["Sniper"])
    ]
    assert codes[:3] == [200, 200, 200]
    assert codes[3] == 402


def test_repeating_the_same_draft_does_not_spend_quota(client):
    """Re-requesting one draft (e.g. after a language switch) is free.

    The product promise is "3 analyses per day", meaning three drafts — not
    three HTTP calls. The language switch re-fetches the same draft in another
    locale and must not burn a unit.
    """
    ids = _ids(client)
    headers = {"x-user-id": "idempotent-quota-user"}
    payload = {"enemy_hero_ids": [ids["Lion"], ids["Axe"]]}
    first = client.post("/api/panic", json=payload, headers=headers)
    assert first.status_code == 200
    assert first.json()["usage"]["used_today"] == 1
    for _ in range(5):
        again = client.post("/api/panic", json=payload, headers={**headers, "x-locale": "ru"})
        assert again.status_code == 200
        assert again.json()["usage"]["used_today"] == 1


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


def test_match_coach_maps_upstream_errors_cleanly(client, monkeypatch):
    """A missing match must not leak the raw httpx/OpenDota message to the client."""
    import httpx

    request = httpx.Request("GET", "https://api.opendota.com/api/matches/1")
    response = httpx.Response(404, request=request)

    def fake_coach(match_id, account_id=None):
        raise httpx.HTTPStatusError("boom", request=request, response=response)

    monkeypatch.setattr(client.app.state.coach, "coach", fake_coach)
    r = client.post("/api/match/coach", json={"match_id": 1})
    assert r.status_code == 404
    assert r.json()["detail"] == "match not available"
    # The raw upstream URL must never reach the user.
    assert "opendota" not in r.json()["detail"].lower()
    assert "404" not in r.json()["detail"]


def test_match_coach_upstream_outage_is_502(client, monkeypatch):
    import httpx

    def fake_coach(match_id, account_id=None):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(client.app.state.coach, "coach", fake_coach)
    r = client.post("/api/match/coach", json={"match_id": 1})
    assert r.status_code == 502
    assert "Could not reach OpenDota" in r.json()["detail"]


def test_match_coach_unknown_match_is_localized(client, monkeypatch):
    import httpx

    request = httpx.Request("GET", "https://api.opendota.com/api/matches/1")
    response = httpx.Response(404, request=request)

    def fake_coach(match_id, account_id=None):
        raise httpx.HTTPStatusError("boom", request=request, response=response)

    monkeypatch.setattr(client.app.state.coach, "coach", fake_coach)
    r = client.post("/api/match/coach", json={"match_id": 1}, headers={"x-locale": "ru"})
    assert r.status_code == 404
    assert r.json()["detail"] == "матч недоступен"


def test_screenshot_bad_file_is_localized(client):
    """An unreadable upload returns a clean, translated message — never a Pillow traceback."""
    r = client.post(
        "/api/screenshot/analyse",
        files={"file": ("bad.png", b"not an image", "image/png")},
    )
    assert r.status_code == 422
    assert "could not read image" in r.json()["detail"].lower()
    assert "BytesIO" not in r.json()["detail"]

    r_ru = client.post(
        "/api/screenshot/analyse",
        files={"file": ("bad.png", b"not an image", "image/png")},
        headers={"x-locale": "ru"},
    )
    assert r_ru.status_code == 422
    assert r_ru.json()["detail"].startswith("Не удалось прочитать")
