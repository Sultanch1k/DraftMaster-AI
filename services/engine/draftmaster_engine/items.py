"""Dynamic item builder — the flagship "what do I actually buy" feature.

The builder never emits a static guide. It starts from the hero's *real*
purchase distribution (OpenDota item popularity, bucketed by game phase) and
then injects counter items whose trigger problem actually appears in the enemy
draft, each with an explicit reason. It also produces the negative space:
items to avoid, and emergency reaction items.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

from .dataset import Dataset

# Cost buckets used to place an injected counter item in the right phase.
PHASE_BY_COST = [
    (700, "starting"),
    (1600, "lane"),
    (2600, "early"),
    (4600, "mid"),
    (10**9, "late"),
]

# Problem threshold (0..100) before we inject a counter item.
TRIGGER = 55.0

# Fallback phase templates if OpenDota has no build data for a hero.
FALLBACK = {
    "starting": ["tango", "branches", "quelling_blade", "circlet"],
    "lane": ["magic_wand", "boots", "bracer"],
    "early": ["power_treads", "magic_wand"],
    "mid": ["black_king_bar", "blink"],
    "late": ["butterfly", "satanic"],
}


@dataclass
class ItemPick:
    key: str
    name: str
    cost: int | None
    img: str | None
    reason: str
    source: str  # "meta" | "counter" | "fallback"
    phase: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BuildPlan:
    hero: str
    starting: list[dict] = field(default_factory=list)
    lane: list[dict] = field(default_factory=list)
    early: list[dict] = field(default_factory=list)
    mid: list[dict] = field(default_factory=list)
    late: list[dict] = field(default_factory=list)
    luxury: list[dict] = field(default_factory=list)
    situational: list[dict] = field(default_factory=list)
    emergency: list[dict] = field(default_factory=list)
    avoid: list[dict] = field(default_factory=list)
    key_counters: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _phase_for_cost(cost: int | None) -> str:
    if not cost:
        return "mid"
    for threshold, phase in PHASE_BY_COST:
        if cost <= threshold:
            return phase
    return "late"


def _meta_pick(ds: Dataset, item_id: int, share: float, phase: str) -> ItemPick | None:
    meta = ds.items_by_id.get(item_id)
    if not meta:
        return None
    name = meta["dname"]
    reason = f"Bought in {share:.0%} of games at this stage on this hero (OpenDota meta data)."
    return ItemPick(
        key=meta["key"],
        name=name,
        cost=meta.get("cost"),
        img=meta.get("img"),
        reason=reason,
        source="meta",
        phase=phase,
    )


def _phase_candidates(
    ds: Dataset, hero_id: int, src: str, dst: str, finished_only: bool = False
) -> list[ItemPick]:
    rows = ds.hero_builds.get(hero_id, {}).get(src, {})
    out: list[ItemPick] = []
    for item_id_str, share in rows.items():
        try:
            item_id = int(item_id_str)
        except ValueError:
            continue
        meta = ds.items_by_id.get(item_id)
        if not meta:
            continue
        if finished_only and not meta.get("is_finished"):
            continue
        pick = _meta_pick(ds, item_id, share, dst)
        if pick:
            out.append(pick)
    return out


def _strip_components(ds: Dataset, picks: list[ItemPick]) -> list[ItemPick]:
    """Drop raw components when a finished item they build into is also recommended.

    Prevents the classic "buy Ogre Axe + Hyperstone" noise: if Mjollnir is on the
    list, Hyperstone is implied and should not take a slot.
    """
    finished = {p.key for p in picks if ds.item(p.key) and ds.item(p.key).get("is_finished")}
    implied = set()
    for key in finished:
        meta = ds.item(key) or {}
        implied.update(meta.get("components", []) or [])
    return [p for p in picks if not (p.key in implied and not (ds.item(p.key) or {}).get("is_finished"))]


def _counter_pick(ds: Dataset, key: str, reason: str, phase: str | None = None) -> ItemPick | None:
    meta = ds.item(key)
    if not meta:
        return None
    return ItemPick(
        key=meta["key"],
        name=meta["dname"],
        cost=meta.get("cost"),
        img=meta.get("img"),
        reason=reason,
        source="counter",
        phase=phase or _phase_for_cost(meta.get("cost")),
    )


def build_items(ds: Dataset, hero_id: int, threat_problems: dict[str, float]) -> BuildPlan:
    hero = ds.by_id.get(hero_id)
    hero_name = hero["localized_name"] if hero else str(hero_id)
    plan = BuildPlan(hero=hero_name)

    base = ds.hero_builds.get(hero_id, {})
    if not base:
        for phase, keys in FALLBACK.items():
            bucket = getattr(plan, phase)
            for k in keys:
                meta = ds.item(k)
                if meta:
                    bucket.append(
                        ItemPick(
                            key=meta["key"],
                            name=meta["dname"],
                            cost=meta.get("cost"),
                            img=meta.get("img"),
                            reason="Standard opening for this hero (no per-hero data available).",
                            source="fallback",
                            phase=phase,
                        ).to_dict()
                    )

    # --- Base build from real popularity data ---------------------------
    # Take a generous pool per phase, strip raw components that a finished item
    # on the same list already implies, then keep the top N finished items.
    phase_map = {
        "start_game": ("starting", 6),
        "early_game": ("lane", 6),
        "mid_game": ("mid", 8),
        "late_game": ("late", 8),
    }
    for src, (dst, n) in phase_map.items():
        # Starting items are legitimately consumables/components; every later
        # phase should only contain completed items.
        finished_only = dst != "starting"
        pool = _phase_candidates(ds, hero_id, src, dst, finished_only=finished_only)
        pool = _strip_components(ds, pool)
        setattr(plan, dst, [p.to_dict() for p in pool[:n]])

    # "early" phase = the next tier of finished items after the lane items.
    early_pool = _phase_candidates(ds, hero_id, "early_game", "early", finished_only=True)
    early_pool = _strip_components(ds, early_pool)
    lane_keys = {i["key"] for i in plan.lane}
    plan.early = [p.to_dict() for p in early_pool if p.key not in lane_keys][:6]

    # Luxury = expensive finished items from the late pool.
    late_pool = _phase_candidates(ds, hero_id, "late_game", "luxury", finished_only=True)
    late_pool = _strip_components(ds, late_pool)
    plan.luxury = [p.to_dict() for p in late_pool if (p.cost or 0) >= 4800][:6]

    # --- Counter-item injection ----------------------------------------
    seen = {p["key"] for p in plan.starting + plan.lane + plan.early + plan.mid + plan.late + plan.luxury}
    key_counters: list[ItemPick] = []
    avoid: list[dict] = []

    for rule in ds.counter_item_rules:
        problem = rule["problem"]
        weight = threat_problems.get(problem, 0.0)
        if weight < TRIGGER:
            continue
        severity = "critical" if weight >= 80 else "high"
        for item_key in rule["items"]:
            pick = _counter_pick(ds, item_key, rule["reason"], None)
            if not pick:
                continue
            pick.reason = f"[{severity}] {rule['reason']}"
            target = getattr(plan, pick.phase if pick.phase != "starting" else "early")
            if pick.key not in seen:
                target.append(pick.to_dict())
                seen.add(pick.key)
            if item_key in rule["items"][:2]:
                key_counters.append(pick)

    for rule in ds.avoid_item_rules:
        if threat_problems.get(rule["problem"], 0.0) < TRIGGER:
            continue
        for item_key in rule["items"]:
            meta = ds.item(item_key)
            if meta:
                avoid.append(
                    {
                        "key": meta["key"],
                        "name": meta["dname"],
                        "cost": meta.get("cost"),
                        "img": meta.get("img"),
                        "reason": rule["reason"],
                    }
                )

    # --- Situational + emergency ---------------------------------------
    situational_problems = [
        ("heavy_magic_burst", ["cloak", "hood_of_defiance", "glimmer_cape", "mage_slayer"]),
        ("heavy_physical", ["ghost_scepter", "heavens_halberd", "solar_crest", "assault"]),
        ("illusions_or_summons", ["maelstrom", "gleipnir", "shivas_guard", "crimson_guard"]),
        ("invisibility", ["dust_of_appearance", "gem", "sentry_ward"]),
        ("heal_heavy", ["spirit_vessel", "skadi", "shivas_guard"]),
        ("heavy_single_target_disable", ["aeon_disk", "linkens_sphere", "lotus_orb"]),
        ("burst_pure_damage", ["heart", "aeon_disk", "satanic"]),
        ("silence", ["euls_scepter", "guardian_greaves", "manta_style"]),
        ("kite_and_slow", ["force_staff", "hurricane_pike", "boots_of_bearing"]),
    ]
    emergency = [
        ("heavy_physical", "ghost_scepter", "Instantly becomes immune to physical damage — press it the moment the enemy commits."),
        ("heavy_magic_burst", "glimmer_cape", "On-demand magic resistance + invisibility to break a burst combo."),
        ("heavy_single_target_disable", "aeon_disk", "Auto-triggers a dispel + shield the instant you drop below 70% HP."),
        ("heavy_cc_teamfight", "black_king_bar", "If the game turns into one big teamfight, BKB is the only reliable answer."),
        ("split_push", "boots_of_travel", "Lets you answer split push without giving up your own farm."),
        ("invisibility", "dust_of_appearance", "Cheapest way to convert an invisible pickoff into a kill."),
    ]

    for problem, keys in situational_problems:
        if threat_problems.get(problem, 0.0) < TRIGGER:
            continue
        for k in keys:
            pick = _counter_pick(ds, k, f"Situational answer to {problem.replace('_', ' ')}.", "situational")
            if pick and pick.key not in seen:
                plan.situational.append(pick.to_dict())
                seen.add(pick.key)

    for problem, key, reason in emergency:
        if threat_problems.get(problem, 0.0) < TRIGGER:
            continue
        pick = _counter_pick(ds, key, reason, "emergency")
        if pick and pick.key not in seen:
            plan.emergency.append(pick.to_dict())
            seen.add(pick.key)

    plan.key_counters = _dedupe([p.to_dict() for p in key_counters])[:5]
    plan.avoid = _dedupe(avoid)
    return plan


def _dedupe(rows: list[dict]) -> list[dict]:
    seen, out = set(), []
    for r in rows:
        if r["key"] in seen:
            continue
        seen.add(r["key"])
        out.append(r)
    return out
