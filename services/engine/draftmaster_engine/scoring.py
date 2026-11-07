"""Hero recommendation scoring.

Implements the Comfort Pick Engine: every candidate is scored on the seven
axes the product promises (counter, meta, comfort, synergy, difficulty, lane,
final) and every score is paired with a human-readable reason.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Iterable

from .dataset import Dataset

# Final pick score weights (spec: Comfort Pick Engine formula).
WEIGHTS = {
    "counter": 0.40,
    "meta": 0.20,
    "comfort": 0.20,
    "synergy": 0.10,
    "role": 0.10,
}

# Tags that make a hero mechanically harder to execute.
MICRO_TAGS = {"illusion_carry", "summon_heavy", "mobility", "split_push"}
COMPLEX_TAGS = {"steal_ult", "global_presence"}


@dataclass
class Candidate:
    hero_id: int
    name: str
    localized_name: str
    icon: str | None
    img: str | None
    roles: list[str]
    scores: dict[str, float]
    final_score: float
    reasons: list[str] = field(default_factory=list)
    countered_by: list[str] = field(default_factory=list)
    strong_against: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _winrate_to_meta(wr: float) -> float:
    """Map a win rate (0.40..0.60 realistic band) to a 0..100 meta score."""
    return round(max(0.0, min(100.0, (wr - 0.42) / 0.16 * 100.0)), 2)


def _difficulty_score(hero: dict) -> float:
    """100 = easy to execute, 0 = high micro/complexity burden."""
    tags = set(hero.get("tags", []))
    penalty = 0.0
    penalty += 18.0 * len(tags & MICRO_TAGS)
    penalty += 8.0 * len(tags & COMPLEX_TAGS)
    if hero.get("attack_type") == "Melee":
        penalty += 4.0
    return round(max(5.0, 100.0 - penalty), 2)


def _synergy_score(ds: Dataset, hero: dict, allies: list[int]) -> float:
    """Heuristic synergy: complementary tags + lane/role fit with allies.

    OpenDota does not expose ally-pair synergy, so this is an explicit,
    documented heuristic rather than a claimed measurement.
    """
    if not allies:
        return 50.0
    my_tags = set(hero.get("tags", []))
    score = 50.0
    for aid in allies:
        ally = ds.by_id.get(aid)
        if not ally:
            continue
        atags = set(ally.get("tags", []))
        # Allies who lock down + a hero who deals damage is real synergy.
        if (atags & {"disable", "single_target_lockdown", "teamfight", "initiation"}) and (
            my_tags & {"burst_magic", "burst_physical", "nuke", "crit"}
        ):
            score += 8.0
        if (atags & {"save", "heal_heavy"}) and (my_tags & {"burst_physical", "crit", "sustain"}):
            score += 5.0
        if (atags & {"push", "summon_heavy"}) and (my_tags & {"push", "summon_heavy"}):
            score += 4.0
        if set(ally.get("roles", [])) == set(hero.get("roles", [])):
            score -= 3.0  # role clash
    return round(max(0.0, min(100.0, score)), 2)


def _lane_score(ds: Dataset, hero: dict, enemies: list[dict]) -> float:
    """Advantage against the most likely lane opponents (ranged/aggro heroes)."""
    likely = [e for e in enemies if e.get("attack_type") == "Ranged"] or enemies
    vals = [ds.counter_logit(hero["id"], e["id"]) for e in likely]
    if not vals:
        return 50.0
    mean = sum(vals) / len(vals)
    return round(100.0 / (1.0 + math.exp(-mean / 0.15)), 2)


def score_candidates(
    ds: Dataset,
    enemy_ids: list[int],
    role: str | None = None,
    comfort: dict[int, float] | None = None,
    allies: list[int] | None = None,
    exclude: Iterable[int] | None = None,
    limit: int = 5,
) -> list[Candidate]:
    comfort = comfort or {}
    allies = allies or []
    excluded = set(enemy_ids) | set(allies) | set(exclude or [])
    enemies = [ds.by_id[i] for i in enemy_ids if i in ds.by_id]

    results: list[Candidate] = []
    for hero in ds.heroes:
        hid = hero["id"]
        if hid in excluded:
            continue

        adv = ds.matchup_advantage(hid, enemy_ids)
        counter = round(100.0 / (1.0 + math.exp(-adv / 0.18)), 2)
        meta = _winrate_to_meta(ds.hero_winrate(hid))
        cmf = comfort.get(hid, 0.5)
        comfort_score = round(cmf * 100.0, 2)
        synergy = _synergy_score(ds, hero, allies)
        difficulty = _difficulty_score(hero)
        lane = _lane_score(ds, hero, enemies)
        role_score = round(ds.role_affinity(hid, role) * 100.0, 2) if role else 50.0

        final = (
            WEIGHTS["counter"] * counter
            + WEIGHTS["meta"] * meta
            + WEIGHTS["comfort"] * comfort_score
            + WEIGHTS["synergy"] * synergy
            + WEIGHTS["role"] * role_score
        )
        # Difficulty is a confidence modifier, not a headline weight: a hero you
        # cannot execute is worth less than its raw numbers suggest.
        final *= 0.85 + 0.15 * (difficulty / 100.0)

        scores = {
            "counter": counter,
            "meta": meta,
            "comfort": comfort_score,
            "synergy": synergy,
            "difficulty": difficulty,
            "lane": lane,
            "role": role_score,
            "final": round(final, 2),
        }
        strong, weak = _matchup_highlights(ds, hid, enemy_ids)
        reasons = explain_pick(ds, hero, enemy_ids, scores, strong, weak)
        results.append(
            Candidate(
                hero_id=hid,
                name=hero["name"],
                localized_name=hero["localized_name"],
                icon=hero.get("icon"),
                img=hero.get("img"),
                roles=hero.get("roles", []),
                scores=scores,
                final_score=scores["final"],
                reasons=reasons,
                strong_against=strong,
                countered_by=weak,
            )
        )

    results.sort(key=lambda c: -c.final_score)
    return results[:limit]


def _matchup_highlights(ds: Dataset, hid: int, enemy_ids: list[int]) -> tuple[list[str], list[str]]:
    pairs = []
    for eid in enemy_ids:
        if eid in ds.by_id:
            pairs.append((ds.by_id[eid]["localized_name"], ds.counter_logit(hid, eid)))
    pairs.sort(key=lambda p: -p[1])
    strong = [n for n, v in pairs if v > 0.12][:3]
    weak = [n for n, v in pairs if v < -0.12][:3]
    return strong, weak


def explain_pick(
    ds: Dataset,
    hero: dict,
    enemy_ids: list[int],
    scores: dict[str, float],
    strong: list[str],
    weak: list[str],
) -> list[str]:
    reasons: list[str] = []
    if strong:
        reasons.append(
            f"Wins the matchup maths against {', '.join(strong)} "
            f"(shrunk counter advantage from real match data)."
        )
    if scores["meta"] >= 60:
        reasons.append(
            f"Above-average current win rate ({ds.hero_winrate(hero['id']):.1%}), so you are not fighting the meta."
        )
    if scores["lane"] >= 60:
        reasons.append("Should win or go even in the lane against this lineup.")
    if scores["lane"] < 40:
        reasons.append("⚠ Loses the likely lane matchup — plan to rotate early or bring a lane partner.")
    if scores["comfort"] >= 70:
        reasons.append("High comfort pick for you, so you will execute the plan reliably.")
    if scores["synergy"] >= 65:
        reasons.append("Pairs well with your allied draft.")
    if scores["difficulty"] < 55:
        reasons.append("⚠ Mechanically demanding in a fight-heavy game — only pick if you are comfortable.")
    if weak:
        reasons.append(f"Careful: {', '.join(weak)} counter you on paper.")
    caps = hero.get("capabilities", {})
    if caps.get("cc", 0) >= 2 and "heavy_cc_teamfight" in str(scores):
        reasons.append("Brings crowd control, which this enemy draft lacks an answer to.")
    if not reasons:
        reasons.append("Solid all-round pick with no glaring weakness into this draft.")
    return reasons
