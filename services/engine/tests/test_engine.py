"""Strategy engine unit tests.

These test real behaviour against the real compiled OpenDota artifact — no
mocks. If the artifact is missing the tests fail loudly rather than silently
skipping, because a missing artifact means the product cannot work at all.
"""
from __future__ import annotations

import math

from draftmaster_engine.dataset import Dataset
from draftmaster_engine.items import build_items
from draftmaster_engine.plan import (
    generate_match_plan,
    generate_skill_build,
    generate_target_priority,
    generate_win_conditions,
    one_sentence_plan,
)
from draftmaster_engine.scoring import score_candidates
from draftmaster_engine.threats import analyse_threats, DIMENSIONS
from draftmaster_engine.winprob import rank_coefficient, win_probability


# --------------------------------------------------------------------------
# Dataset integrity
# --------------------------------------------------------------------------

def test_dataset_has_all_heroes(dataset: Dataset):
    assert len(dataset.heroes) >= 120
    assert len(dataset.by_id) == len(dataset.heroes)


def test_counter_matrix_is_antisymmetric(dataset: Dataset):
    """counter(A,B) must be ~= -counter(B,A); the pipeline symmetrises it."""
    checked = 0
    for a, row in dataset.counter.items():
        for b, v in list(row.items())[:20]:
            rev = dataset.counter.get(b, {}).get(a)
            if rev is None:
                continue
            assert math.isclose(v, -rev, abs_tol=1e-3), f"{a} vs {b}: {v} / {rev}"
            checked += 1
    assert checked > 500


def test_counter_values_are_bounded(dataset: Dataset):
    for row in dataset.counter.values():
        for v in row.values():
            assert -2.0 < v < 2.0


def test_every_hero_has_capabilities_and_tags_field(dataset: Dataset):
    for h in dataset.heroes:
        assert "capabilities" in h
        assert isinstance(h.get("tags"), list)
        assert h["capabilities"]["nuke_count"] >= 0


def test_item_index_flags(dataset: Dataset):
    bkb = dataset.item("black_king_bar")
    assert bkb and bkb["is_finished"] is True
    ogre = dataset.item("ogre_axe")
    assert ogre and ogre["is_component"] is True and ogre["is_finished"] is False


# --------------------------------------------------------------------------
# Threat analysis
# --------------------------------------------------------------------------

def test_threat_analysis_returns_all_14_dimensions(dataset, hero_ids):
    enemies = [hero_ids["Lion"], hero_ids["Axe"], hero_ids["Shadow Shaman"]]
    profile = analyse_threats(dataset, enemies)
    assert set(profile.scores) == set(DIMENSIONS)
    for k, v in profile.scores.items():
        assert 0 <= v <= 100, k


def test_disable_heavy_draft_flags_lockdown_problem(dataset, hero_ids):
    enemies = [hero_ids["Lion"], hero_ids["Axe"], hero_ids["Shadow Shaman"]]
    profile = analyse_threats(dataset, enemies)
    assert profile.problems["heavy_single_target_disable"] >= 55


def test_illusion_draft_flags_aoe_problem(dataset, hero_ids):
    enemies = [hero_ids["Phantom Lancer"], hero_ids["Naga Siren"], hero_ids["Terrorblade"]]
    profile = analyse_threats(dataset, enemies)
    assert profile.problems["illusions_or_summons"] >= 55


def test_healing_draft_flags_antiheal_problem(dataset, hero_ids):
    enemies = [hero_ids["Necrophos"], hero_ids["Timbersaw"], hero_ids["Dazzle"]]
    profile = analyse_threats(dataset, enemies)
    assert profile.problems["heal_heavy"] >= 55


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

def test_scoring_weights_match_spec(dataset, hero_ids):
    """Final score must be the documented weighted blend (x difficulty modifier)."""
    enemies = [hero_ids["Lion"], hero_ids["Axe"], hero_ids["Shadow Shaman"]]
    cands = score_candidates(dataset, enemies, role="carry", limit=1)
    c = cands[0]
    s = c.scores
    expected = (
        0.40 * s["counter"]
        + 0.20 * s["meta"]
        + 0.20 * s["comfort"]
        + 0.10 * s["synergy"]
        + 0.10 * s["role"]
    ) * (0.85 + 0.15 * s["difficulty"] / 100.0)
    assert math.isclose(s["final"], expected, abs_tol=0.05)


def test_scoring_never_recommends_an_enemy_hero(dataset, hero_ids):
    enemies = [hero_ids["Lion"], hero_ids["Axe"], hero_ids["Shadow Shaman"]]
    cands = score_candidates(dataset, enemies, limit=10)
    assert not ({c.hero_id for c in cands} & set(enemies))


def test_scoring_is_deterministic(dataset, hero_ids):
    enemies = [hero_ids["Lion"], hero_ids["Axe"]]
    a = score_candidates(dataset, enemies, limit=5)
    b = score_candidates(dataset, enemies, limit=5)
    assert [c.hero_id for c in a] == [c.hero_id for c in b]


def test_comfort_changes_recommendation(dataset, hero_ids):
    enemies = [hero_ids["Lion"], hero_ids["Axe"], hero_ids["Shadow Shaman"]]
    baseline = score_candidates(dataset, enemies, limit=5)
    boosted_id = baseline[4].hero_id
    with_comfort = score_candidates(dataset, enemies, comfort={boosted_id: 1.0}, limit=5)
    assert with_comfort[0].hero_id == boosted_id


# --------------------------------------------------------------------------
# Dynamic item builder
# --------------------------------------------------------------------------

def test_bkb_against_disable_draft(dataset, hero_ids):
    enemies = [hero_ids["Lion"], hero_ids["Axe"], hero_ids["Shadow Shaman"]]
    threats = analyse_threats(dataset, enemies)
    build = build_items(dataset, hero_ids["Juggernaut"], threats.problems)
    all_items = [i["key"] for i in build.mid + build.early + build.late]
    assert "black_king_bar" in all_items


def test_aoe_items_against_illusions(dataset, hero_ids):
    enemies = [hero_ids["Phantom Lancer"], hero_ids["Naga Siren"], hero_ids["Terrorblade"]]
    threats = analyse_threats(dataset, enemies)
    build = build_items(dataset, hero_ids["Sven"], threats.problems)
    keys = {i["key"] for i in build.mid + build.late + build.situational + build.key_counters}
    assert keys & {"mjollnir", "radiance", "battle_fury", "maelstrom", "shivas_guard", "gleipnir"}


def test_antiheal_against_healing_draft(dataset, hero_ids):
    enemies = [hero_ids["Necrophos"], hero_ids["Timbersaw"], hero_ids["Dazzle"]]
    threats = analyse_threats(dataset, enemies)
    build = build_items(dataset, hero_ids["Wraith King"], threats.problems)
    keys = {i["key"] for i in build.mid + build.late + build.situational + build.key_counters}
    assert keys & {"spirit_vessel", "skadi", "eye_of_skadi", "shivas_guard"}


def test_every_item_has_a_reason(dataset, hero_ids):
    enemies = [hero_ids["Lion"], hero_ids["Axe"], hero_ids["Shadow Shaman"]]
    threats = analyse_threats(dataset, enemies)
    build = build_items(dataset, hero_ids["Juggernaut"], threats.problems)
    for phase in ("starting", "lane", "early", "mid", "late", "luxury", "situational", "emergency"):
        for item in getattr(build, phase):
            assert item["reason"], f"{phase} item without reason: {item}"


def test_avoid_list_has_reasons(dataset, hero_ids):
    enemies = [hero_ids["Necrophos"], hero_ids["Timbersaw"], hero_ids["Lion"]]
    threats = analyse_threats(dataset, enemies)
    build = build_items(dataset, hero_ids["Wraith King"], threats.problems)
    assert build.avoid, "healing+magic draft should produce items-to-avoid"
    for item in build.avoid:
        assert item["reason"]


def test_build_has_no_raw_components_in_mid_or_late(dataset, hero_ids):
    enemies = [hero_ids["Lion"], hero_ids["Axe"], hero_ids["Shadow Shaman"]]
    threats = analyse_threats(dataset, enemies)
    build = build_items(dataset, hero_ids["Juggernaut"], threats.problems)
    for phase in ("lane", "early", "mid", "late", "luxury"):
        for item in getattr(build, phase):
            meta = dataset.item(item["key"])
            assert meta is None or meta.get("is_finished"), f"{phase} contains component {item['name']}"


# --------------------------------------------------------------------------
# Skill build / talents / targets
# --------------------------------------------------------------------------

def test_skill_build_covers_levels_1_to_30(dataset, hero_ids):
    hero = dataset.by_id[hero_ids["Juggernaut"]]
    skill = generate_skill_build(dataset, hero)
    levels = [l["level"] for l in skill["levels"]]
    assert levels == list(range(1, 31))


def test_skill_build_respects_ult_and_talent_levels(dataset, hero_ids):
    hero = dataset.by_id[hero_ids["Juggernaut"]]
    skill = generate_skill_build(dataset, hero)
    by_level = {l["level"]: l for l in skill["levels"]}
    for lvl in (6, 12, 18):
        assert by_level[lvl]["kind"] == "ultimate"
    for lvl in (10, 15, 20, 25):
        assert by_level[lvl]["kind"] == "talent"


def test_skill_build_never_exceeds_ability_max_levels(dataset, hero_ids):
    for name in ("Juggernaut", "Meepo", "Invoker", "Drow Ranger"):
        hero = dataset.by_id[hero_ids[name]]
        skill = generate_skill_build(dataset, hero)
        counts: dict[str, int] = {}
        for lvl in skill["levels"]:
            if lvl["kind"] == "basic":
                counts[lvl["choice"]] = counts.get(lvl["choice"], 0) + 1
        for ab in hero["abilities"]:
            if ab["name"] in counts:
                assert counts[ab["name"]] <= max(1, min(4, ab.get("levels", 1))), (name, ab["name"])


def test_ultimate_detected_for_tricky_heroes(dataset, hero_ids):
    expectations = {
        "Juggernaut": "Omnislash",
        "Lion": "Finger of Death",
        "Sven": "God's Strength",
        "Drow Ranger": "Marksmanship",
        "Bristleback": "Warpath",
        "Meepo": "Divided We Stand",
        "Invoker": "Invoke",
    }
    for name, ult in expectations.items():
        hero = dataset.by_id[hero_ids[name]]
        found = [a["name"] for a in hero["abilities"] if a["is_ultimate"]]
        assert found == [ult], f"{name}: {found}"


def test_talent_trees_are_real_and_resolved(dataset):
    unresolved = 0
    heroes_with_talents = 0
    for h in dataset.heroes:
        if h.get("talents"):
            heroes_with_talents += 1
        for tier in h.get("talents", []):
            for opt in tier["options"]:
                if "{s:bonus" in opt["desc"]:
                    unresolved += 1
    assert heroes_with_talents >= 100
    assert unresolved == 0


def test_target_priority_ranks_all_enemies(dataset, hero_ids):
    enemies = [hero_ids["Lion"], hero_ids["Axe"], hero_ids["Shadow Shaman"]]
    rows = generate_target_priority(dataset, hero_ids["Juggernaut"], enemies)
    assert [r["rank"] for r in rows] == [1, 2, 3]
    assert all(r["reason"] for r in rows)


# --------------------------------------------------------------------------
# Win probability
# --------------------------------------------------------------------------

def test_win_probability_is_complementary(dataset, hero_ids):
    result = win_probability(
        dataset, hero_ids["Juggernaut"], [hero_ids["Lion"], hero_ids["Axe"]], "carry", 70
    )
    assert math.isclose(
        result.player_win_probability + result.enemy_win_probability, 100.0, abs_tol=0.2
    )


def test_win_probability_is_within_bounds(dataset, hero_ids):
    for name in ("Juggernaut", "Sniper", "Phantom Assassin", "Crystal Maiden"):
        result = win_probability(
            dataset, hero_ids[name], [hero_ids["Lion"], hero_ids["Axe"], hero_ids["Shadow Shaman"]]
        )
        assert 1.0 <= result.player_win_probability <= 99.0


def test_rank_coefficient_monotonic():
    _, herald = rank_coefficient(10)
    _, immortal = rank_coefficient(80)
    assert herald < immortal


def test_higher_rank_shows_larger_draft_edges(dataset, hero_ids):
    """Rank should compress draft advantage toward 50%, not reverse it."""
    hero = hero_ids["Juggernaut"]
    enemies = [hero_ids["Lion"], hero_ids["Axe"], hero_ids["Shadow Shaman"]]
    low = win_probability(dataset, hero, enemies, "carry", 10)
    high = win_probability(dataset, hero, enemies, "carry", 80)
    assert abs(high.player_win_probability - 50) >= abs(low.player_win_probability - 50)


def test_win_probability_exposes_factors(dataset, hero_ids):
    result = win_probability(dataset, hero_ids["Juggernaut"], [hero_ids["Lion"]], "carry", 60)
    names = {f["name"] for f in result.factors}
    assert {"Hero matchups", "Meta strength", "Threat mismatch", "Game clock"} <= names
    assert result.verdict


# --------------------------------------------------------------------------
# Match plan / win conditions / sentence
# --------------------------------------------------------------------------

def test_match_plan_has_five_phases(dataset, hero_ids):
    enemies = [hero_ids["Lion"], hero_ids["Axe"], hero_ids["Shadow Shaman"]]
    hero = dataset.by_id[hero_ids["Juggernaut"]]
    threats = analyse_threats(dataset, enemies)
    plan = generate_match_plan(dataset, hero, threats)
    assert [p["window"] for p in plan] == ["0-10", "10-20", "20-30", "30-45", "45+"]
    for phase in plan:
        for key in ("objectives", "farm_focus", "fight_focus", "map_movement", "tower_priority", "roshan_priority", "danger_zones"):
            assert phase[key]


def test_match_plan_adapts_to_enemy_draft(dataset, hero_ids):
    """The timeline must be draft-specific, not a static guide.

    Two drafts with different threat profiles must produce different plans for
    the same hero; otherwise the flagship "plan for this exact game" claim is
    false and the report is just a renamed static guide.
    """
    hero = dataset.by_id[hero_ids["Juggernaut"]]

    # Heavy targeted-disable + teamfight draft.
    lockdown = [hero_ids["Lion"], hero_ids["Shadow Shaman"], hero_ids["Axe"]]
    # Invisibility + evasion draft.
    evasive = [hero_ids["Riki"], hero_ids["Phantom Assassin"], hero_ids["Bounty Hunter"]]

    plan_a = generate_match_plan(dataset, hero, analyse_threats(dataset, lockdown))
    plan_b = generate_match_plan(dataset, hero, analyse_threats(dataset, evasive))

    text_a = " ".join(
        f"{p['fight_focus']} {' '.join(p['danger_zones'])} {p['farm_focus']} {p['roshan_priority']} {p['objectives']}"
        for p in plan_a
    )
    text_b = " ".join(
        f"{p['fight_focus']} {' '.join(p['danger_zones'])} {p['farm_focus']} {p['roshan_priority']} {p['objectives']}"
        for p in plan_b
    )
    assert text_a != text_b, "match plan is identical for two very different enemy drafts"


def test_win_conditions_have_three_tiers(dataset, hero_ids):
    enemies = [hero_ids["Lion"], hero_ids["Axe"], hero_ids["Shadow Shaman"]]
    hero = dataset.by_id[hero_ids["Juggernaut"]]
    threats = analyse_threats(dataset, enemies)
    targets = generate_target_priority(dataset, hero_ids["Juggernaut"], enemies)
    wp = win_probability(dataset, hero_ids["Juggernaut"], enemies, "carry", 60)
    cond = generate_win_conditions(dataset, hero, threats, targets, wp)
    assert set(cond) == {"primary", "secondary", "emergency"}
    assert all(cond.values())


def test_one_sentence_plan_is_a_single_sentence(dataset, hero_ids):
    enemies = [hero_ids["Lion"], hero_ids["Axe"], hero_ids["Shadow Shaman"]]
    hero = dataset.by_id[hero_ids["Juggernaut"]]
    threats = analyse_threats(dataset, enemies)
    build = build_items(dataset, hero_ids["Juggernaut"], threats.problems)
    targets = generate_target_priority(dataset, hero_ids["Juggernaut"], enemies)
    wp = win_probability(dataset, hero_ids["Juggernaut"], enemies, "carry", 60)
    sentence = one_sentence_plan(dataset, hero, threats, build, targets, wp)
    assert sentence.endswith(".")
    assert sentence.count(".") == 1
    assert "%" in sentence


def test_slow_abilities_do_not_count_as_disables(dataset, hero_ids):
    """A movement slow is soft CC, not a lock-down.

    Sniper has three abilities that mention "slow" and one mini-stun, but he is
    not a three-disable hero. Counting slows as disables inflated his
    disable_count and produced threat prose like "brings 5 disables" plus a
    wrongly recommended BKB/Aeon package.
    """
    sniper = dataset.by_id[hero_ids["Sniper"]]["capabilities"]
    assert sniper["disable_count"] <= 1, sniper
    # The crowd-control weight still reflects the slows, so nothing is lost.
    assert sniper["cc"] >= 1.0

    for name in ("Shadow Shaman", "Lion", "Necrophos"):
        caps = dataset.by_id[hero_ids[name]]["capabilities"]
        assert caps["disable_count"] >= 1, name
        assert caps["disable_count"] <= 2, (name, caps)


def test_enemy_power_spike_ignores_thin_samples(dataset, hero_ids):
    """A peak must come from a game-length bin with a real sample size.

    The raw duration curve has bins backed by a single game; an unweighted
    maximum reported nonsense like "peak ~75m" for Lion.
    """
    from draftmaster_engine.plan import generate_power_spikes

    enemies = [hero_ids["Lion"], hero_ids["Sniper"], hero_ids["Axe"]]
    spikes = generate_power_spikes(dataset, hero_ids["Juggernaut"], enemies)
    assert len(spikes["enemies"]) == len(enemies)
    for row in spikes["enemies"]:
        assert row["peak_minutes"] is not None
        assert 0 < row["peak_minutes"] <= 60
