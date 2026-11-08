"""Match plan generators: skill build, talents, target priority, power spikes,
timeline, win conditions and the one-sentence win plan.

Everything here is derived from the hero's real ability data (Valve constants),
the shrunk matchup matrix, and the empirical duration curve — no static guides.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .dataset import Dataset
from .threats import ThreatProfile, DIMENSION_LABELS

PHASES = [
    ("0-10", "Laning", 0, 600),
    ("10-20", "Early mid-game", 600, 1200),
    ("20-30", "Mid-game", 1200, 1800),
    ("30-45", "Late mid-game", 1800, 2700),
    ("45+", "Late game", 2700, 10**9),
]


# ---------------------------------------------------------------------------
# Skill build
# ---------------------------------------------------------------------------

def generate_skill_build(ds: Dataset, hero: dict, threats: ThreatProfile | None = None) -> dict:
    """Build a realistic 1-30 skill order.

    Abilities are ordered by value, then points are assigned greedily with each
    ability capped at its real max level. Ultimate lands on 6/12/18 and talents
    on 10/15/20/25, exactly as the game enforces.
    """
    abilities = [a for a in hero.get("abilities", []) if a.get("key")]
    ultimates = [a for a in abilities if a.get("is_ultimate")]
    basics = [a for a in abilities if not a.get("is_ultimate")]
    if not basics:
        return {"levels": [], "notes": ["No ability data available for this hero."]}

    def value(a: dict) -> tuple:
        return (
            1 if a.get("is_nuke") else 0,
            1 if a.get("has_disable") else 0,
            a.get("levels", 1),
        )

    ordered = sorted(basics, key=value, reverse=True)
    ult = ultimates[0] if ultimates else None
    caps = {a["key"]: max(1, min(4, a.get("levels", 1))) for a in ordered}
    spent = {a["key"]: 0 for a in ordered}

    levels: list[dict] = []
    for lvl in range(1, 31):
        if lvl in (10, 15, 20, 25):
            levels.append(
                {
                    "level": lvl,
                    "choice": "Talent",
                    "reason": f"Take the level {lvl} talent (see the Talent Tree section).",
                    "kind": "talent",
                }
            )
            continue
        if lvl in (6, 12, 18) and ult:
            levels.append(
                {
                    "level": lvl,
                    "choice": ult["name"],
                    "reason": "Ultimate comes online — this is your fight-winning button.",
                    "kind": "ultimate",
                }
            )
            continue
        pick = next((a for a in ordered if spent[a["key"]] < caps[a["key"]]), None)
        if pick is None:
            levels.append(
                {
                    "level": lvl,
                    "choice": "Attribute Bonus",
                    "reason": "All abilities are maxed — take stats to scale damage, HP and mana.",
                    "kind": "stats",
                }
            )
            continue
        spent[pick["key"]] += 1
        if pick is ordered[0]:
            reason = "Primary ability — max it first for lane pressure and kills."
        elif len(ordered) > 1 and pick is ordered[1]:
            reason = "Secondary ability — a second damage source or key utility."
        else:
            reason = "Fill remaining points once the core abilities are maxed."
        levels.append({"level": lvl, "choice": pick["name"], "reason": reason, "kind": "basic"})

    notes = []
    if threats:
        if threats.problems.get("heavy_magic_burst", 0) >= 60:
            notes.append(
                "Adaptation: enemy magic burst is high — level any defensive or buff ability earlier than this greedy order."
            )
        if threats.problems.get("illusions_or_summons", 0) >= 60 and any(a.get("is_nuke") for a in abilities):
            notes.append("Adaptation: prioritise your AoE damage ability to clear illusions and summons.")
        if threats.problems.get("heavy_physical", 0) >= 60:
            notes.append("Adaptation: physical-heavy enemy — value survivability talents and stats over damage.")
        if threats.problems.get("heavy_single_target_disable", 0) >= 60:
            notes.append("Adaptation: expect lock-down chains — keep a defensive item, not a greedy skill order.")
    if ult:
        notes.append(f"Alternative: delay {ult['name']} past level 6 only if the lane is already decided.")
    return {
        "levels": levels,
        "notes": notes,
        "primary": ordered[0]["name"],
        "secondary": ordered[1]["name"] if len(ordered) > 1 else ordered[0]["name"],
        "ultimate": ult["name"] if ult else None,
    }


# ---------------------------------------------------------------------------
# Talents
# ---------------------------------------------------------------------------

_OFFENSIVE_HINTS = ("damage", "attack speed", "cooldown", "cast range", "spell", "mana", "move speed", "gold", "gpm")
_DEFENSIVE_HINTS = ("health", "hp", "armor", "magic resist", "evasion", "status resist", "strength", "lifesteal", "heal")


def generate_talents(ds: Dataset, hero: dict, threats: ThreatProfile | None = None) -> list[dict]:
    out = []
    for tier in hero.get("talents", []):
        options = tier.get("options", [])
        if not options:
            continue
        chosen, reason = _choose_talent(options, threats)
        out.append(
            {
                "hero_level": tier["hero_level"],
                "options": [o["desc"] for o in options],
                "recommended": chosen["desc"],
                "reason": reason,
            }
        )
    return out


def _choose_talent(options: list[dict], threats: ThreatProfile | None) -> tuple[dict, str]:
    def is_off(o: dict) -> bool:
        d = o["desc"].lower()
        return any(h in d for h in _OFFENSIVE_HINTS)

    def is_def(o: dict) -> bool:
        d = o["desc"].lower()
        return any(h in d for h in _DEFENSIVE_HINTS)

    defensive_pressure = 0.0
    if threats:
        defensive_pressure = max(
            threats.problems.get("heavy_magic_burst", 0),
            threats.problems.get("heavy_physical", 0),
            threats.problems.get("burst_pure_damage", 0),
            threats.scores.get("burst_damage", 0),
        )

    off = [o for o in options if is_off(o)]
    deff = [o for o in options if is_def(o)]

    if defensive_pressure >= 65 and deff:
        pick = deff[0]
        return pick, "Enemy draft deals heavy burst — take the survivability talent to live through the first combo."
    if off:
        pick = off[0]
        return pick, "Offensive value: this talent directly increases your damage or uptime in fights."
    # Default: prefer the hero-specific ("unique") talent as it is usually stronger.
    unique = [o for o in options if "unique" in o.get("name", "")]
    pick = unique[0] if unique else options[0]
    return pick, "Highest-value option at this tier for a standard build."


# ---------------------------------------------------------------------------
# Target priority
# ---------------------------------------------------------------------------

def generate_target_priority(ds: Dataset, hero_id: int, enemy_ids: list[int]) -> list[dict]:
    """Rank enemies by how much killing them first improves your win chance.

    Blend of three signals: the real head-to-head matchup advantage they hold
    over your hero, their raw lock-down/burst capability, and their role value
    (a farmed carry left alive wins the late game; a support is replaceable).
    """
    rows = []
    for eid in enemy_ids:
        e = ds.by_id.get(eid)
        if not e:
            continue
        caps = e.get("capabilities", {})
        threat_to_you = max(0.0, ds.counter_logit(eid, hero_id)) * 100.0
        disable = caps.get("disable_count", 0) * 16.0
        burst = (caps.get("magic", 0) + caps.get("physical", 0)) * 10.0
        cc = caps.get("cc", 0) * 8.0
        carry_value = 22.0 if "Carry" in e.get("roles", []) else 0.0
        support_value = -10.0 if "Support" in e.get("roles", []) else 0.0
        score = threat_to_you + disable + burst + cc + carry_value + support_value
        rows.append(
            {
                "hero_id": eid,
                "name": e["localized_name"],
                "priority_score": round(score, 1),
                "threat_to_you": round(threat_to_you, 1),
                "disables": caps.get("disable_count", 0),
                "roles": e.get("roles", []),
            }
        )
    rows.sort(key=lambda r: -r["priority_score"])
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
        r["reason"] = _priority_reason(r, i, len(rows))
    return rows


def _priority_reason(r: dict, rank: int, total: int) -> str:
    bits = []
    if r["threat_to_you"] >= 12:
        bits.append("directly counters your hero")
    if r["disables"] >= 2:
        bits.append("chains disables onto you")
    if "Carry" in r["roles"]:
        bits.append("is an enemy core who wins the late game")
    if rank == 1:
        bits.append("kill this one first in every fight")
    elif rank == total:
        bits.append("lowest priority — ignore unless free")
    return ", ".join(bits) if bits else "standard focus priority"


# ---------------------------------------------------------------------------
# Power spikes
# ---------------------------------------------------------------------------

def generate_power_spikes(ds: Dataset, hero_id: int, enemy_ids: list[int]) -> dict:
    hero = ds.by_id.get(hero_id)
    spikes = []
    if hero:
        spikes.append(
            {
                "type": "Hero level",
                "when": "Level 6 / 12 / 18",
                "detail": "Ultimate timing — the moment your kit becomes fully online.",
            }
        )
        key_items = _key_items(ds, hero_id)
        if key_items:
            spikes.append(
                {
                    "type": "Item",
                    "when": f"{key_items[0]['name']} timing",
                    "detail": f"Your first major item. Hit this timing and force a fight immediately.",
                }
            )
        delta = ds.late_game_delta(hero_id)
        if delta > 0.01:
            spikes.append({"type": "Draft", "when": "Late game (35m+)", "detail": "Your win rate rises with game length — you scale."})
        elif delta < -0.01:
            spikes.append({"type": "Draft", "when": "0-25m", "detail": "You fall off late — win before the clock turns."})
        spikes.append({"type": "Teamfight", "when": "First BKB / ultimate item", "detail": "You can now survive the enemy's first combo and fight back."})
        spikes.append({"type": "Objective", "when": "First Roshan / Aegis", "detail": "Convert a won fight into a tower and Roshan, not a base dive."})

    enemy_spikes = []
    for eid in enemy_ids:
        e = ds.by_id.get(eid)
        if not e:
            continue
        curve = ds.hero_durations.get(eid)
        peak = None
        if curve:
            peak = max(curve, key=lambda p: p["winrate"])
        enemy_spikes.append(
            {
                "hero_id": eid,
                "name": e["localized_name"],
                "peak_minutes": peak["minutes"] if peak else None,
                "peak_winrate": peak["winrate"] if peak else None,
                "danger": "Avoid fighting them around this window unless you are ahead.",
            }
        )
    enemy_spikes.sort(key=lambda r: -(r["peak_winrate"] or 0))
    return {"player": spikes, "enemies": enemy_spikes}


def _key_items(ds: Dataset, hero_id: int) -> list[dict]:
    base = ds.hero_builds.get(hero_id, {})
    rows = list(base.get("mid_game", {}).items())[:3]
    out = []
    for item_id_str, share in rows:
        try:
            item_id = int(item_id_str)
        except ValueError:
            continue
        meta = ds.items_by_id.get(item_id)
        if meta:
            out.append({"name": meta["dname"], "share": share, "cost": meta.get("cost")})
    return out


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

def generate_match_plan(ds: Dataset, hero: dict, threats: ThreatProfile) -> list[dict]:
    hero_id = hero["id"]
    delta = ds.late_game_delta(hero_id)
    plan = []
    for label, name, lo, hi in PHASES:
        objectives, farm, fight, movement, towers, roshan, danger = _phase_content(
            label, name, threats, delta
        )
        plan.append(
            {
                "window": label,
                "phase": name,
                "objectives": objectives,
                "farm_focus": farm,
                "fight_focus": fight,
                "map_movement": movement,
                "tower_priority": towers,
                "roshan_priority": roshan,
                "danger_zones": danger,
            }
        )
    return plan


def _phase_content(label: str, name: str, threats: ThreatProfile, delta: float):
    t = threats.scores
    if label == "0-10":
        return (
            ["Secure your lane, hit your level 6 power spike", "Contest the 4/6/8 minute runes if safe"],
            "Prioritise last hits and denies; a 40+ last-hit lane is a won lane.",
            "Only fight if the enemy overextends into your tower or a support rotates.",
            "Stay on your half of the map; ward your jungle entrance.",
            "Take the enemy safelane tower only if you win the lane hard.",
            "Do not attempt Roshan — you lack the damage and sustain.",
            ["Enemy jungle at night", "Rune fights if enemy has level-1 kill threat"],
        )
    if label == "10-20":
        return (
            ["Convert your first item into a tower", "Take T1 towers on the side lanes"],
            "Farm towards your first major item; take ancient stacks if available.",
            "Fight when your ultimate and first item are both up.",
            "Rotate with your team after every won fight; do not farm alone into a push draft.",
            "T1 towers first, T2 only with Aegis or a big man advantage.",
            "Scout Roshan if you have a hero who can solo it; otherwise wait for a won fight.",
            ["Deep enemy jungle without vision", "High ground fights you do not need"],
        )
    if label == "20-30":
        return (
            ["Group and take T2 towers", "First Roshan is the objective that wins this phase"],
            "Farm the enemy jungle after won fights, not your own — starve them.",
            "Force fights around Aegis and your key item timings.",
            "Move as 5 with Aegis; pick off anyone who splits.",
            "Take T2 towers, then the T3 on the weakest lane.",
            "Take Roshan the moment you win a fight near the pit.",
            ["Enemy high ground without Aegis", "Fighting inside enemy base with no buyback"],
        )
    if label == "30-45":
        return (
            ["Break the barracks", "Second Roshan for the high-ground push"],
            "Keep lanes pushed out before every fight; never lose map control.",
            "Only take fights you start, with Aegis, or after a pickoff.",
            "Hold vision around Roshan and the enemy triangle.",
            "Take T3s on the lane where you have Aegis and buybacks.",
            "Second Roshan is mandatory before high ground.",
            ["High ground without Aegis + buybacks", "Chasing kills into their fountain area"],
        )
    return (
        ["Close the game with Aegis and buybacks", "Take barracks, then throne"],
        "Sell early items for a final luxury upgrade; keep buyback gold.",
        "Fight only with full ultimates, Aegis and buybacks available.",
        "Push as 5 with vision; never split alone in the enemy half.",
        "Take the throne in one push, not two half-hearted attempts.",
        "Third Roshan if the game goes this long.",
        ["Any fight without buyback", "Defending with 2+ heroes dead"],
    )


# ---------------------------------------------------------------------------
# Win conditions
# ---------------------------------------------------------------------------

def generate_win_conditions(
    ds: Dataset, hero: dict, threats: ThreatProfile, targets: list[dict], winprob
) -> dict:
    primary_bits = []
    secondary_bits = []
    emergency_bits = []

    top_target = targets[0]["name"] if targets else "the enemy core"
    primary_bits.append(f"Kill {top_target} first in every fight — they are your highest-priority threat.")
    if winprob.player_win_probability < 50:
        primary_bits.append("Do not take 5v5 fights on even terms; win with tempo, split push and pickoffs.")
    else:
        primary_bits.append("Group early, take Roshan off your first won fight, and convert Aegis into a tower.")

    if threats.problems.get("heavy_cc_teamfight", 0) >= 60:
        secondary_bits.append("Force the enemy's key disables out before committing; then re-engage.")
    if threats.problems.get("heal_heavy", 0) >= 60:
        secondary_bits.append("Buy anti-heal (Spirit Vessel/Skadi) before the first big teamfight.")
    if threats.scores.get("split_push", 0) >= 55:
        secondary_bits.append("Answer split push with one mobile hero — never send your whole team.")
    if threats.scores.get("late_game", 0) >= 60:
        secondary_bits.append("Close before 35 minutes; the clock favours the enemy draft.")
    if not secondary_bits:
        secondary_bits.append("Play around Roshan timings and force fights with Aegis advantage.")

    emergency_bits.append("If you lose a fight, do not contest the follow-up objective — trade a tower instead.")
    emergency_bits.append("If the enemy takes Roshan, farm defensively and wait for their Aegis to expire before fighting.")
    emergency_bits.append("If you fall behind, farm the triangle, take safe pickoffs, and force high-ground defence.")

    return {
        "primary": " ".join(primary_bits),
        "secondary": " ".join(secondary_bits),
        "emergency": " ".join(emergency_bits),
    }


# ---------------------------------------------------------------------------
# One-sentence win plan
# ---------------------------------------------------------------------------

def one_sentence_plan(
    ds: Dataset, hero: dict, threats: ThreatProfile, build, targets: list[dict], winprob
) -> str:
    key_item = build.key_counters[0]["name"] if build.key_counters else (
        (build.mid[0]["name"] if build.mid else "your first major item")
    )
    top = targets[0]["name"] if targets else "the enemy core"
    avoid = build.avoid[0]["name"] if build.avoid else None
    tone = "heavily favoured" if winprob.player_win_probability >= 58 else (
        "favoured" if winprob.player_win_probability >= 52 else (
            "a coin flip" if winprob.player_win_probability > 48 else "an uphill draft"
        )
    )
    clause = f"get {key_item} on time, kill {top} first"
    if threats.problems.get("heavy_single_target_disable", 0) >= 60:
        clause += ", avoid enemy initiations until BKB is up"
    if avoid:
        clause += f", and never build {avoid}"
    return f"If you {clause}, this match is {tone} ({winprob.player_win_probability:.0f}% draft win probability)."
