"""My Hero Strategy — engine + API tests.

The feature's whole promise is that the advice is *specific to the chosen hero
and the chosen five enemies*, so the tests assert specificity, not just that the
endpoint returns 200.
"""
from __future__ import annotations

import pytest

from draftmaster_engine.hero_strategy import HeroStrategyEngine


# --- fixtures ---------------------------------------------------------------
@pytest.fixture(scope="session")
def strategy_engine(dataset):
    return HeroStrategyEngine(dataset)


# A real draft: Juggernaut vs Axe / Lion / Shadow Shaman / Phantom Lancer / Necrophos.
ENEMIES = [2, 26, 27, 12, 36]


# --- engine: structure ------------------------------------------------------
def test_strategy_has_all_ten_sections(strategy_engine, hero_ids):
    r = strategy_engine.build(hero_ids["Juggernaut"], ENEMIES, role="carry", rank_tier=80).to_dict()
    for section in (
        "matchup_overview",
        "lane_strategy",
        "skill_build",
        "item_build",
        "enemy_dossiers",
        "teamfight_strategy",
        "target_priority",
        "power_spikes",
        "win_conditions",
        "one_sentence_game_plan",
    ):
        assert r[section], f"section {section} is empty"


def test_dossier_for_every_enemy(strategy_engine, dataset, hero_ids):
    r = strategy_engine.build(hero_ids["Juggernaut"], ENEMIES, role="carry", rank_tier=80).to_dict()
    assert len(r["enemy_dossiers"]) == 5
    names = {d["name"] for d in r["enemy_dossiers"]}
    expected = {dataset.by_id[i]["localized_name"] for i in ENEMIES}
    assert names == expected
    for d in r["enemy_dossiers"]:
        assert d["what_makes_dangerous"]
        assert d["how_to_avoid"]
        assert d["when_can_fight"]
        assert d["positioning"]


# --- engine: specificity ----------------------------------------------------
def test_advice_changes_with_the_hero(strategy_engine, hero_ids):
    """The same enemy draft must produce different plans for different heroes."""
    a = strategy_engine.build(hero_ids["Juggernaut"], ENEMIES, role="carry", rank_tier=80).to_dict()
    b = strategy_engine.build(hero_ids["Crystal Maiden"], ENEMIES, role="hard_support", rank_tier=80).to_dict()
    assert a["one_sentence_game_plan"] != b["one_sentence_game_plan"]
    assert a["matchup_overview"]["win_probability"] != b["matchup_overview"]["win_probability"]
    # The counter items are enemy-driven by design, but the *base* build is
    # hero-specific: a carry and a support do not buy the same items.
    def base_keys(r):
        return {i["key"] for bucket in ("starting", "lane", "early", "mid", "late", "luxury")
                for i in r["item_build"].get(bucket, [])}

    assert base_keys(a) != base_keys(b)


def test_advice_changes_with_the_enemy_draft(strategy_engine, hero_ids):
    """A physical draft and a magic draft must produce different counter items."""
    physical = strategy_engine.build(
        hero_ids["Juggernaut"], [hero_ids["Phantom Assassin"], hero_ids["Drow Ranger"],
                                 hero_ids["Sniper"], hero_ids["Templar Assassin"], hero_ids["Clinkz"]],
        role="carry", rank_tier=80,
    ).to_dict()
    magic = strategy_engine.build(
        hero_ids["Juggernaut"], [hero_ids["Lion"], hero_ids["Zeus"], hero_ids["Lina"],
                                 hero_ids["Skywrath Mage"], hero_ids["Pugna"]],
        role="carry", rank_tier=80,
    ).to_dict()
    phys_counters = {i["key"] for i in physical["item_build"]["key_counters"]}
    magic_counters = {i["key"] for i in magic["item_build"]["key_counters"]}
    assert phys_counters != magic_counters


def test_counter_items_are_attributed_to_enemies(strategy_engine, dataset, hero_ids):
    """Section 4 must say *which* enemy each counter item answers."""
    r = strategy_engine.build(hero_ids["Juggernaut"], ENEMIES, role="carry", rank_tier=80).to_dict()
    counters = r["item_build"]["key_counters"]
    assert counters, "no key counters for a lock-down heavy draft"
    assert any(c.get("answers") for c in counters), "no counter item names the enemy it answers"
    # Every named answer must be one of the five enemies.
    valid = {dataset.by_id[i]["localized_name"] for i in ENEMIES}
    for c in counters:
        for name in c.get("answers", []):
            assert name in valid


def test_lockdown_draft_recommends_bkb(strategy_engine, hero_ids):
    """Axe + Lion + Shadow Shaman is a lock-down draft: BKB must appear."""
    r = strategy_engine.build(hero_ids["Juggernaut"], [2, 26, 27, 3, 5], role="carry", rank_tier=80).to_dict()
    all_items = {
        i["key"]
        for bucket in ("lane", "early", "mid", "late", "luxury", "situational", "emergency", "key_counters")
        for i in r["item_build"].get(bucket, [])
    }
    assert "black_king_bar" in all_items


def test_illusion_draft_recommends_aoe(strategy_engine, hero_ids):
    """Phantom Lancer + Naga Siren need area clear, not single-target damage."""
    r = strategy_engine.build(
        hero_ids["Juggernaut"], [12, 89, 26, 27, 2], role="carry", rank_tier=80
    ).to_dict()
    counter_keys = {i["key"] for i in r["item_build"]["key_counters"]}
    situational = {i["key"] for i in r["item_build"]["situational"]}
    assert counter_keys & {"maelstrom", "mjollnir", "radiance", "shivas_guard", "crimson_guard"} or \
        situational & {"maelstrom", "gleipnir", "shivas_guard", "crimson_guard"}


def test_items_to_avoid_explained(strategy_engine, hero_ids):
    r = strategy_engine.build(
        hero_ids["Juggernaut"], [hero_ids["Lion"], hero_ids["Zeus"], hero_ids["Lina"],
                                 hero_ids["Skywrath Mage"], hero_ids["Pugna"]],
        role="carry", rank_tier=80,
    ).to_dict()
    avoid = r["item_build"]["avoid"]
    assert avoid, "a full-magic draft should flag items to avoid"
    for item in avoid:
        assert item["reason"]


def test_target_priority_ranks_all_five(strategy_engine, dataset, hero_ids):
    r = strategy_engine.build(hero_ids["Juggernaut"], ENEMIES, role="carry", rank_tier=80).to_dict()
    ranks = [t["rank"] for t in r["target_priority"]]
    assert sorted(ranks) == [1, 2, 3, 4, 5]
    assert r["target_priority"][0]["reason"]


def test_lane_strategy_targets_likely_opponents(strategy_engine, hero_ids):
    r = strategy_engine.build(hero_ids["Juggernaut"], ENEMIES, role="carry", rank_tier=80).to_dict()
    lane = r["lane_strategy"]
    assert lane["lane"] == "safelane"
    assert lane["plan"] and lane["trading"] and lane["survival"]
    assert lane["likely_opponents"]


def test_one_sentence_is_hero_specific_and_short(strategy_engine, hero_ids):
    r = strategy_engine.build(hero_ids["Juggernaut"], ENEMIES, role="carry", rank_tier=80).to_dict()
    s = r["one_sentence_game_plan"]
    assert "Juggernaut" in s
    assert len(s) < 320


def test_win_conditions_present(strategy_engine, hero_ids):
    r = strategy_engine.build(hero_ids["Juggernaut"], ENEMIES, role="carry", rank_tier=80).to_dict()
    wc = r["win_conditions"]
    assert wc["primary"] and wc["secondary"] and wc["emergency"]


def test_data_confidence_discloses_measured_vs_inferred(strategy_engine, hero_ids):
    r = strategy_engine.build(hero_ids["Juggernaut"], ENEMIES, role="carry", rank_tier=80).to_dict()
    conf = r["data_confidence"]
    assert conf["measured"] and conf["inferred"]
    assert conf["notes"]


def test_unknown_hero_raises(strategy_engine):
    with pytest.raises(KeyError):
        strategy_engine.build(999999, ENEMIES, role="carry", rank_tier=80)


# --- API --------------------------------------------------------------------
def _body(hero_id=8, enemies=None, **kw):
    return {"hero_id": hero_id, "enemy_hero_ids": enemies or ENEMIES, "role": "carry", "rank_tier": 80, **kw}


def test_api_hero_strategy_ok(client):
    r = client.post("/api/hero-strategy", json=_body())
    assert r.status_code == 200
    body = r.json()
    assert {"strategy", "usage", "cached"} <= set(body)
    assert body["strategy"]["one_sentence_game_plan"]


def test_api_requires_exactly_five_enemies(client):
    assert client.post("/api/hero-strategy", json=_body(enemies=[2, 26, 27, 12])).status_code == 422
    assert client.post("/api/hero-strategy", json=_body(enemies=[2, 26, 27, 12, 36, 8])).status_code == 422


def test_api_rejects_duplicate_enemies(client):
    assert client.post("/api/hero-strategy", json=_body(enemies=[2, 2, 27, 12, 36])).status_code == 422


def test_api_rejects_hero_in_enemy_list(client):
    assert client.post("/api/hero-strategy", json=_body(hero_id=2, enemies=[2, 26, 27, 12, 36])).status_code == 422


def test_api_rejects_unknown_ids(client):
    assert client.post("/api/hero-strategy", json=_body(enemies=[2, 26, 27, 12, 999999])).status_code == 422


def test_api_rejects_missing_hero(client):
    assert client.post("/api/hero-strategy", json={"enemy_hero_ids": ENEMIES}).status_code == 422


def test_api_rejects_missing_enemies(client):
    assert client.post("/api/hero-strategy", json={"hero_id": 8}).status_code == 422


def test_api_cache_hit_does_not_recharge(client):
    first = client.post("/api/hero-strategy", json=_body())
    assert first.status_code == 200
    assert first.json()["cached"] is False
    second = client.post("/api/hero-strategy", json=_body())
    assert second.json()["cached"] is True
    # The repeat request must not consume another unit of the free quota.
    assert first.json()["usage"]["used_today"] == second.json()["usage"]["used_today"]


def test_api_russian_localization(client):
    r = client.post("/api/hero-strategy", json=_body(locale="ru"))
    assert r.status_code == 200
    s = r.json()["strategy"]
    # Hero names stay English (community convention) but the prose is Russian.
    assert "Играйте на" in s["one_sentence_game_plan"]
    assert s["threat_analysis"]["labels"]["magic_damage"] == "Магический урон"
    assert s["data_confidence"]["measured"][0].startswith("преимущество")


def test_api_counter_pick_still_works(client):
    """The new mode must not have disturbed the existing flagship flow."""
    r = client.post("/api/analyse", json={"enemy_hero_ids": ENEMIES, "role": "carry", "rank_tier": 80})
    assert r.status_code == 200
    report = r.json()["report"]
    assert report["best_picks"]
    assert report["item_build"]["key_counters"] is not None
