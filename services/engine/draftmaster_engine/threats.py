"""Threat analysis: turns an enemy draft into scored threat dimensions.

All 14 dimensions required by the product spec are produced here, plus the
derived "problem flags" that drive the dynamic item builder. Scores are 0..100
and calibrated so that a balanced 5-hero draft lands near 40-60 on most axes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .dataset import Dataset

# Contribution weights for the raw capability counters. Tuned so a single
# nuker does not read as "critical magic damage".
MAGIC_UNIT = 14.0
PHYS_UNIT = 12.0
PURE_UNIT = 26.0
CC_UNIT = 13.0
DISABLE_UNIT = 9.0

DIMENSIONS = [
    "magic_damage",
    "physical_damage",
    "pure_damage",
    "burst_damage",
    "sustain_damage",
    "crowd_control",
    "teamfight",
    "pickoff",
    "push",
    "split_push",
    "roshan",
    "early_game",
    "mid_game",
    "late_game",
]

DIMENSION_LABELS = {
    "magic_damage": "Magic Damage",
    "physical_damage": "Physical Damage",
    "pure_damage": "Pure Damage",
    "burst_damage": "Burst Damage",
    "sustain_damage": "Sustain Damage",
    "crowd_control": "Crowd Control",
    "teamfight": "Teamfight Potential",
    "pickoff": "Pickoff Potential",
    "push": "Push Strength",
    "split_push": "Split Push Strength",
    "roshan": "Roshan Strength",
    "early_game": "Early Game",
    "mid_game": "Mid Game",
    "late_game": "Late Game",
}

TAG_WEIGHTS = {
    "teamfight": {"teamfight": 20.0, "initiation": 16.0},
    "pickoff": {"pickoff": 22.0, "invis": 12.0, "single_target_lockdown": 14.0, "mobility": 8.0},
    "push": {"push": 24.0, "summon_heavy": 14.0, "global_presence": 8.0},
    "split_push": {"split_push": 30.0, "illusion_carry": 12.0, "global_presence": 10.0},
    "roshan": {"roshan": 30.0, "summon_heavy": 8.0, "sustain": 6.0},
    "burst_damage": {"burst_magic": 20.0, "burst_physical": 20.0, "nuke": 12.0},
    "sustain_damage": {"sustain": 18.0, "heal_heavy": 14.0, "attack_speed": 8.0},
}


@dataclass
class ThreatProfile:
    scores: dict[str, float]
    danger: dict[str, str]
    problems: dict[str, float] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=lambda: dict(DIMENSION_LABELS))

    def top(self, n: int = 5) -> list[tuple[str, float, str]]:
        ranked = sorted(self.scores.items(), key=lambda kv: -kv[1])
        return [(DIMENSION_LABELS.get(k, k), v, self.danger.get(k, "low")) for k, v in ranked[:n]]

    def to_dict(self) -> dict:
        return {
            "scores": self.scores,
            "labels": self.labels,
            "danger": self.danger,
            "problems": self.problems,
        }


def _danger(score: float) -> str:
    if score >= 78:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 38:
        return "medium"
    return "low"


def _tag_score(heroes: list[dict], mapping: dict[str, float]) -> float:
    total = 0.0
    for h in heroes:
        tags = set(h.get("tags", []))
        for tag, weight in mapping.items():
            if tag in tags:
                total += weight
    return total


def analyse_threats(ds: Dataset, enemy_ids: Iterable[int], own_id: int | None = None) -> ThreatProfile:
    enemies = [ds.by_id[i] for i in enemy_ids if i in ds.by_id]
    if not enemies:
        return ThreatProfile(scores={d: 0.0 for d in DIMENSIONS}, danger={d: "low" for d in DIMENSIONS})

    magic = sum(h["capabilities"].get("magic", 0) for h in enemies) * MAGIC_UNIT
    physical = sum(h["capabilities"].get("physical", 0) for h in enemies) * PHYS_UNIT
    pure = sum(h["capabilities"].get("pure", 0) for h in enemies) * PURE_UNIT
    cc = sum(h["capabilities"].get("cc", 0) for h in enemies) * CC_UNIT
    disables = sum(h["capabilities"].get("disable_count", 0) for h in enemies) * DISABLE_UNIT

    burst = _tag_score(enemies, TAG_WEIGHTS["burst_damage"])
    sustain = _tag_score(enemies, TAG_WEIGHTS["sustain_damage"])
    teamfight = _tag_score(enemies, TAG_WEIGHTS["teamfight"])
    pickoff = _tag_score(enemies, TAG_WEIGHTS["pickoff"])
    push = _tag_score(enemies, TAG_WEIGHTS["push"])
    split_push = _tag_score(enemies, TAG_WEIGHTS["split_push"])
    roshan = _tag_score(enemies, TAG_WEIGHTS["roshan"])

    # Lane/aggression phases from lane presence and duration curves.
    early = 18.0
    mid = 20.0
    late = 18.0
    for h in enemies:
        hid = h["id"]
        delta = ds.late_game_delta(hid)
        late += max(0.0, delta * 220.0)
        early += max(0.0, -delta * 200.0)
        if "farm_accelerator" in h.get("tags", []):
            mid += 6.0
        if "late_game" in h.get("tags", []):
            late += 10.0
        if "push" in h.get("tags", []):
            early += 6.0
            mid += 6.0
        if h.get("attack_type") == "Ranged":
            mid += 1.5

    raw = {
        "magic_damage": magic,
        "physical_damage": physical,
        "pure_damage": pure,
        "burst_damage": burst,
        "sustain_damage": sustain,
        "crowd_control": cc + disables * 0.5,
        "teamfight": teamfight,
        "pickoff": pickoff,
        "push": push,
        "split_push": split_push,
        "roshan": roshan,
        "early_game": early,
        "mid_game": mid,
        "late_game": late,
    }

    scores = {k: round(min(100.0, v), 1) for k, v in raw.items()}
    danger = {k: _danger(v) for k, v in scores.items()}
    problems = detect_problems(ds, enemies)
    return ThreatProfile(scores=scores, danger=danger, problems=problems)


def detect_problems(ds: Dataset, enemies: list[dict]) -> dict[str, float]:
    """Detect the tactical problems that the dynamic item builder answers."""
    problems: dict[str, float] = {}

    def tags_any(*tags: str) -> int:
        return sum(1 for h in enemies if set(h.get("tags", [])) & set(tags))

    def caps(key: str) -> float:
        return sum(h["capabilities"].get(key, 0) for h in enemies)

    targeted_disable = sum(
        1
        for h in enemies
        if "single_target_lockdown" in h.get("tags", []) or h["capabilities"].get("disable_count", 0) >= 2
    )
    magic = caps("magic")
    physical = caps("physical")
    cc = caps("cc")
    silence = caps("silence")

    problems["heavy_single_target_disable"] = min(100.0, targeted_disable * 26.0 + cc * 4.0)
    problems["heavy_magic_burst"] = min(100.0, magic * 11.0)
    problems["heavy_physical"] = min(100.0, physical * 11.0)
    problems["burst_pure_damage"] = min(100.0, caps("pure") * 30.0 + _tag_score(enemies, {"burst_magic": 8.0, "burst_physical": 8.0}) * 0.6)
    problems["evasion_or_blind"] = min(100.0, tags_any("evasion") * 45.0)
    problems["illusions_or_summons"] = min(100.0, tags_any("illusion_carry", "summon_heavy") * 34.0)
    problems["heal_heavy"] = min(100.0, tags_any("heal_heavy") * 34.0 + caps("magic") * 1.5)
    problems["invisibility"] = min(100.0, tags_any("invis") * 45.0)
    problems["heavy_cc_teamfight"] = min(100.0, cc * 6.0 + _tag_score(enemies, {"teamfight": 9.0, "initiation": 8.0}) * 0.8)
    problems["kite_and_slow"] = min(100.0, tags_any("kite") * 40.0 + _tag_score(enemies, {"mobility": 10.0, "escape": 6.0}) * 0.8)
    problems["silence"] = min(100.0, silence * 30.0)
    problems["split_push"] = min(100.0, tags_any("split_push") * 40.0 + _tag_score(enemies, {"push": 8.0}) * 0.5)

    return {k: round(v, 1) for k, v in problems.items()}


def threat_summary(profile: ThreatProfile, threshold: float = 60.0) -> list[str]:
    out = []
    for dim, score in sorted(profile.scores.items(), key=lambda kv: -kv[1]):
        if score >= threshold:
            out.append(f"{DIMENSION_LABELS[dim]} {score:.0f} ({profile.danger[dim]})")
    return out
