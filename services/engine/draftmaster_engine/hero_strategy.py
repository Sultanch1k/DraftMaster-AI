"""My Hero Strategy — personalised strategy for a hero the user already picked.

This is the second flagship mode. The counter-pick assistant answers "which hero
should I pick?"; this module answers "I am playing *this* hero against *these
five* enemies — how do I win?".

Every sentence is derived from real data:

* per-hero ability data (Valve constants: damage type, disable, ultimate),
* the hero capability counters (magic / physical / pure / cc / disables),
* the archetype tags compiled from those abilities,
* the shrunk head-to-head matchup matrix,
* the empirical duration curve (who does the clock favour).

Nothing is a static guide and nothing is invented. Where a claim is a documented
heuristic rather than a measurement (lane assignment, positioning), the section
says so via ``confidence``.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Iterable

from .dataset import Dataset
from .items import build_items
from .plan import (
    generate_power_spikes,
    generate_skill_build,
    generate_target_priority,
    generate_win_conditions,
    one_sentence_plan,
)
from .threats import analyse_threats
from .winprob import win_probability

# ---------------------------------------------------------------------------
# Archetypes
# ---------------------------------------------------------------------------
# An archetype is a fact about a hero that changes how a game is played. We read
# them from the compiled tags/capabilities rather than hand-listing heroes, so
# new heroes and balance patches flow through automatically.

TAG_ARCHETYPES = {
    "escape": "escape",
    "mobility": "mobility",
    "invis": "invisibility",
    "illusion_carry": "illusions",
    "summon_heavy": "summons",
    "heal_heavy": "healing",
    "sustain": "sustain",
    "tanky": "tanky",
    "evasion": "evasion",
    "silence": "silence",
    "split_push": "split_push",
    "push": "push",
    "global_presence": "global",
    "initiation": "initiation",
    "teamfight": "teamfight",
    "pickoff": "pickoff",
    "save": "save",
    "anti_carry": "anti_carry",
    "anti_magic": "anti_magic",
    "anti_heal": "anti_heal",
    "anti_illusion": "anti_illusion",
    "farm_accelerator": "farm_accelerator",
    "late_game": "late_game",
    "roshan": "roshan",
    "needs_aoe_clear": "aoe_damage",
    "cleave": "cleave",
    "crit": "crit",
    "truesight": "truesight",
    "vision_denial": "vision_denial",
    "duel": "duel",
    "steal_ult": "steal_ult",
    "aura": "aura",
    "kite": "kite",
    "burst_magic": "burst_magic",
    "burst_physical": "burst_physical",
    "nuke": "nuke",
    "single_target_lockdown": "lockdown",
    "disable": "disable",
    "gold_swing": "gold_swing",
    "attack_speed": "attack_speed",
    "anti_push": "anti_push",
    "anti_magic_sustain": "anti_magic_sustain",
}

# Hero roles that imply where a hero is usually laned. Used only for the lane
# section, and always labelled as an inference.
LANE_BY_ROLE = {
    "Carry": "safelane",
    "Support": "support",
    "Nuker": "mid",
    "Escape": "mid",
    "Initiator": "offlane",
    "Durable": "offlane",
    "Disabler": "offlane",
    "Pusher": "offlane",
    "Jungler": "jungle",
}

# Which enemy lanes threaten which of our lanes.
LANE_OPPONENTS = {
    "carry": ("offlane",),
    "mid": ("mid",),
    "offlane": ("safelane", "support"),
    "support": ("offlane", "support"),
    "hard_support": ("offlane", "support"),
}


def _arch(hero: dict) -> set[str]:
    """The archetype set for a hero, from its tags and capability counters."""
    out: set[str] = set()
    for tag in hero.get("tags", []):
        if tag in TAG_ARCHETYPES:
            out.add(TAG_ARCHETYPES[tag])
    caps = hero.get("capabilities", {}) or {}
    if caps.get("pure", 0) > 0:
        out.add("pure_damage")
    if caps.get("bkbpierce_cc", 0) > 0:
        out.add("bkbpierce_cc")
    if caps.get("silence", 0) > 0:
        out.add("silence")
    if caps.get("magic", 0) >= 3:
        out.add("magic_heavy")
    if caps.get("physical", 0) >= 2:
        out.add("physical_heavy")
    if hero.get("attack_type") == "Ranged":
        out.add("ranged")
    else:
        out.add("melee")
    return out


def _lane_of(hero: dict) -> str:
    for role in ("Carry", "Nuker", "Escape", "Initiator", "Durable", "Disabler", "Pusher", "Support"):
        if role in hero.get("roles", []):
            return LANE_BY_ROLE.get(role, "unknown")
    return "unknown"


def _top_abilities(hero: dict, limit: int = 3) -> list[dict]:
    """The abilities that actually decide fights: ultimates and disables first."""
    abilities = [a for a in hero.get("abilities", []) if a.get("key")]

    def weight(a: dict) -> tuple:
        return (
            1 if a.get("is_ultimate") else 0,
            1 if a.get("has_disable") else 0,
            1 if a.get("bkbpierce") else 0,
            1 if a.get("is_nuke") else 0,
            a.get("levels", 1),
        )

    return sorted(abilities, key=weight, reverse=True)[:limit]


def _ability_brief(a: dict) -> dict:
    return {
        "name": a.get("name"),
        "dmg_type": a.get("dmg_type"),
        "is_ultimate": bool(a.get("is_ultimate")),
        "has_disable": bool(a.get("has_disable")),
        "bkbpierce": bool(a.get("bkbpierce")),
        "desc": (a.get("desc") or "").strip(),
    }


# ---------------------------------------------------------------------------
# Item answers, keyed by the enemy archetype that triggers them
# ---------------------------------------------------------------------------
# Each entry: enemy archetype -> (items, why). Item keys are verified against the
# compiled dataset; a key that does not resolve is silently skipped so a patch
# that removes an item degrades instead of crashing.

ITEM_ANSWERS: dict[str, tuple[list[str], str]] = {
    "lockdown": (
        ["black_king_bar", "aeon_disk", "sphere", "lotus_orb"],
        "Targeted lock-down chains are how this draft kills you — spell immunity or an auto-dispel breaks the chain.",
    ),
    "bkbpierce_cc": (
        ["sphere", "aeon_disk", "lotus_orb", "heart"],
        "Their control pierces spell immunity, so BKB alone will not save you — you need a linken-style block or raw HP.",
    ),
    "burst_magic": (
        ["black_king_bar", "pipe", "mage_slayer", "cloak", "glimmer_cape"],
        "Their damage arrives as one magical combo; magic resistance or BKB removes it entirely.",
    ),
    "magic_heavy": (
        ["black_king_bar", "pipe", "cloak", "mage_slayer", "eternal_shroud"],
        "Most of their damage is magical, so magic resistance is worth more than armour or HP here.",
    ),
    "burst_physical": (
        ["ghost", "assault", "crimson_guard", "solar_crest", "heavens_halberd"],
        "They kill with physical burst; armour and attack-slow cut it far harder than raw HP.",
    ),
    "physical_heavy": (
        ["assault", "crimson_guard", "shivas_guard", "solar_crest", "heavens_halberd"],
        "Their DPS is physical, so armour and attack speed slows are your cheapest survivability.",
    ),
    "pure_damage": (
        ["heart", "aeon_disk", "satanic"],
        "Pure damage ignores resistance — only raw HP, an Aeon Disk buffer or lifesteal actually answer it.",
    ),
    "illusions": (
        ["maelstrom", "mjollnir", "shivas_guard", "crimson_guard", "radiance"],
        "Illusion armies melt to area damage; a single-target build loses to them no matter how farmed you are.",
    ),
    "summons": (
        ["maelstrom", "mjollnir", "shivas_guard", "crimson_guard"],
        "Summons are cleared by area damage and slowed by an armour aura — kill the army, not the hero.",
    ),
    "healing": (
        ["spirit_vessel", "skadi", "shivas_guard", "eye_of_skadi"],
        "Their plan is to out-sustain you; healing reduction turns their whole draft off.",
    ),
    "sustain": (
        ["spirit_vessel", "skadi", "shivas_guard"],
        "Their sustain lets them win long fights — anti-heal or a hard burst window is the answer.",
    ),
    "evasion": (
        ["monkey_king_bar"],
        "True strike is the only reliable answer to evasion — otherwise a third of your attacks miss.",
    ),
    "invisibility": (
        ["dust", "ward_sentry", "gem"],
        "You cannot fight what you cannot see; truesight turns their invisibility pickoff into your kill.",
    ),
    "silence": (
        ["cyclone", "manta", "guardian_greaves", "lotus_orb"],
        "A silence stops you casting your escape or ultimate — a dispel removes it instantly.",
    ),
    "kite": (
        ["force_staff", "hurricane_pike", "travel_boots"],
        "They win by keeping you at range; a gap-closer or reposition tool is worth more than more damage.",
    ),
    "escape": (
        ["orchid", "bloodthorn", "sheepstick", "abyssal_blade", "nullifier"],
        "Their escape is how they survive your gank — a silence, root or disarm stops the escape, not the damage.",
    ),
    "mobility": (
        ["orchid", "sheepstick", "abyssal_blade", "nullifier"],
        "They reposition out of every fight; hard control that lands before they move is the answer.",
    ),
    "save": (
        ["orchid", "bloodthorn", "sheepstick", "nullifier"],
        "Their save turns your kill into a wasted cooldown — silence the saver or burst through the window.",
    ),
    "tanky": (
        ["diffusal_blade", "skadi", "desolator"],
        "Raw HP needs percentage or armour-reduction damage, not another damage item.",
    ),
    "anti_carry": (
        ["black_king_bar", "aeon_disk", "sphere", "satanic"],
        "They are built to neutralise a carry — buy the item that denies their one combo and keep farming.",
    ),
    "anti_magic": (
        ["black_king_bar", "assault", "monkey_king_bar"],
        "They punish magic damage, so lean into physical or immunity rather than more spells.",
    ),
    "anti_heal": (
        ["black_king_bar", "satanic"],
        "They cut your healing, so burst windows matter more than drawn-out fights.",
    ),
    "anti_illusion": (
        ["black_king_bar", "satanic"],
        "They clear illusions instantly — if you rely on them, fight around your cooldowns, not your army.",
    ),
    "split_push": (
        ["travel_boots", "black_king_bar"],
        "They win by splitting the map; you need the mobility to answer a lane without losing your own.",
    ),
    "push": (
        ["crimson_guard", "pipe", "shivas_guard"],
        "They win by taking buildings early — defensive auras let you fight in front of your own tower.",
    ),
    "pickoff": (
        ["aeon_disk", "black_king_bar", "ward_observer", "ward_sentry"],
        "They hunt isolated heroes; vision and an auto-triggering buffer are what stop the gank.",
    ),
    "initiation": (
        ["black_king_bar", "aeon_disk", "glimmer_cape"],
        "Their initiation decides the fight — survive the first two seconds and the fight is yours.",
    ),
    "teamfight": (
        ["black_king_bar", "pipe", "guardian_greaves", "crimson_guard"],
        "They are stronger in a straight 5v5; an aura or immunity item lets you contest the fight at all.",
    ),
}

# Items that actively lose value against a given enemy archetype.
ITEM_AVOID: dict[str, tuple[list[str], str]] = {
    "magic_heavy": (
        ["assault", "butterfly", "solar_crest"],
        "Pure armour does almost nothing against a magical draft.",
    ),
    "burst_magic": (
        ["assault", "butterfly"],
        "Armour does not reduce magical burst — the gold is better spent on magic resistance.",
    ),
    "pure_damage": (
        ["assault", "cloak", "hood_of_defiance", "pipe"],
        "Pure damage ignores resistance, so resistance items are wasted gold.",
    ),
    "evasion": (
        ["butterfly", "heavens_halberd"],
        "Stacking more evasion does not beat an enemy that already ignores yours.",
    ),
    "healing": (
        ["octarine_core", "refresher"],
        "Long-cooldown sustain loses the attrition war to a healing draft.",
    ),
    "anti_magic": (
        ["dagon", "ethereal_blade"],
        "They punish magic damage, so more of it is the worst possible purchase.",
    ),
    "physical_heavy": (
        ["cloak", "hood_of_defiance"],
        "Magic resistance does nothing against a physical draft.",
    ),
}


@dataclass
class EnemyDossier:
    hero_id: int
    name: str
    icon: str | None
    roles: list[str]
    danger_score: float
    threat_to_you: float
    # Signed head-to-head logit for OUR hero vs this enemy (positive = we win it).
    matchup_logit: float
    what_makes_dangerous: list[str]
    abilities_to_watch: list[dict]
    how_to_avoid: list[str]
    when_can_fight: str
    items_that_help: list[dict]
    positioning: str
    lane_risk: str
    lane_advice: str
    # The enemy's archetype set. Kept on the dossier so later sections can reason
    # about it without recomputing from the dataset.
    arch: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class HeroStrategy:
    hero: dict
    role: str | None
    rank: str
    patch: str | None
    generated_in_ms: int
    enemy_draft: list[dict]
    matchup_overview: dict
    lane_strategy: dict
    skill_build: dict
    item_build: dict
    enemy_dossiers: list[dict]
    teamfight_strategy: dict
    target_priority: list[dict]
    power_spikes: dict
    win_conditions: dict
    one_sentence_game_plan: str
    win_probability: dict
    threat_analysis: dict
    data_confidence: dict

    def to_dict(self) -> dict:
        return asdict(self)


class HeroStrategyEngine:
    """Builds a My Hero Strategy report for one chosen hero."""

    def __init__(self, dataset: Dataset | None = None):
        from .dataset import get_dataset

        self.ds = dataset or get_dataset()

    def build(
        self,
        hero_id: int,
        enemy_ids: list[int],
        role: str | None = None,
        rank_tier: int | None = None,
    ) -> HeroStrategy:
        import time

        started = time.perf_counter()
        ds = self.ds
        hero = ds.hero_or_raise(hero_id)
        enemy_ids = [int(e) for e in enemy_ids]
        enemies = [ds.by_id[e] for e in enemy_ids if e in ds.by_id]
        if not enemies:
            raise ValueError("hero strategy needs at least one known enemy hero")

        threats = analyse_threats(ds, enemy_ids, hero_id)
        problems = threats.problems
        my_arch = _arch(hero)
        dossiers = [self._dossier(hero, e, hero_id) for e in enemies]
        dossiers.sort(key=lambda d: -d.danger_score)
        winprob = win_probability(ds, hero_id, enemy_ids, role, rank_tier)

        # The item build reuses the counter-item engine, then attributes every
        # injected item to the specific enemy heroes that justify it.
        build = build_items(ds, hero_id, problems)
        build_dict = build.to_dict()
        self._attribute_items(build_dict, enemies, my_arch)

        targets = generate_target_priority(ds, hero_id, enemy_ids)
        skill = generate_skill_build(ds, hero, threats)
        skill = self._personalise_skill(skill, hero, enemies, my_arch)
        spikes = generate_power_spikes(ds, hero_id, enemy_ids)
        win_conditions = generate_win_conditions(ds, hero, threats, targets, winprob)
        sentence = self._game_plan_sentence(hero, dossiers, build_dict, targets, winprob, my_arch)

        return HeroStrategy(
            hero=self._hero_brief(hero),
            role=role,
            rank=winprob.rank_label,
            patch=(ds.patch or {}).get("name"),
            generated_in_ms=int((time.perf_counter() - started) * 1000),
            enemy_draft=[self._hero_brief(e) for e in enemies],
            matchup_overview=self._matchup_overview(hero, enemies, dossiers, winprob, my_arch),
            lane_strategy=self._lane_strategy(hero, enemies, role, my_arch),
            skill_build=skill,
            item_build=build_dict,
            enemy_dossiers=[d.to_dict() for d in dossiers],
            teamfight_strategy=self._teamfight(hero, enemies, dossiers, my_arch, winprob),
            target_priority=targets,
            power_spikes=spikes,
            win_conditions=win_conditions,
            one_sentence_game_plan=sentence,
            win_probability=winprob.to_dict(),
            threat_analysis=threats.to_dict(),
            data_confidence=self._confidence(hero, enemies, winprob, problems),
        )

    # -- helpers ---------------------------------------------------------
    def _hero_brief(self, hero: dict) -> dict:
        return {
            "id": hero["id"],
            "localized_name": hero["localized_name"],
            "name": hero.get("name"),
            "icon": hero.get("icon"),
            "img": hero.get("img"),
            "roles": hero.get("roles", []),
            "tags": hero.get("tags", []),
            "attack_type": hero.get("attack_type"),
            "primary_attr": hero.get("primary_attr"),
            "capabilities": hero.get("capabilities", {}),
            "abilities": [_ability_brief(a) for a in _top_abilities(hero, 4)],
            "lane": _lane_of(hero),
            "pub_winrate": hero.get("pub_winrate"),
        }

    # -- 1. matchup overview ---------------------------------------------
    def _matchup_overview(
        self, hero: dict, enemies: list[dict], dossiers: list[EnemyDossier], winprob, my_arch: set[str]
    ) -> dict:
        ds = self.ds
        hid = hero["id"]
        adv = ds.matchup_advantage(hid, [e["id"] for e in enemies])
        # Signed: positive logit means we beat that hero head-to-head.
        favourable = [d.name for d in dossiers if d.matchup_logit >= 0.10]
        unfavourable = [d.name for d in dossiers if d.matchup_logit <= -0.10]

        # Difficulty is anchored to the win-probability engine, then described.
        p = winprob.player_win_probability
        if p >= 56:
            difficulty, label = 1, "Easy"
        elif p >= 52:
            difficulty, label = 2, "Favourable"
        elif p > 48:
            difficulty, label = 3, "Even"
        elif p > 44:
            difficulty, label = 4, "Hard"
        else:
            difficulty, label = 5, "Very hard"

        advantages: list[str] = []
        for d in dossiers:
            if d.matchup_logit >= 0.10:
                advantages.append(f"{d.name} is a favourable matchup for you on real match data.")
        if "illusions" in my_arch and "anti_illusion" not in _arch_many(enemies):
            advantages.append("You bring illusions they cannot clear efficiently.")
        if "split_push" in my_arch:
            advantages.append("You can win the map without winning fights — split push is a real win condition.")
        if "heal_heavy" in my_arch and "anti_heal" not in _arch_many(enemies):
            advantages.append("Your sustain outlasts their damage in extended fights.")
        if "push" in my_arch:
            advantages.append("You convert won fights into buildings faster than they can.")
        if not advantages:
            advantages.append("No single enemy hard-counters you — this game is decided by execution, not the draft.")

        mistakes: list[str] = []
        if any("lockdown" in d.arch for d in dossiers):
            mistakes.append("Walking into fog alone: their lock-down turns one mistake into a death.")
        if any("illusion" in d.arch or "summons" in d.arch for d in dossiers):
            mistakes.append("Building single-target damage against an army you cannot clear.")
        if any("heal" in d.arch or "sustain" in d.arch for d in dossiers):
            mistakes.append("Taking long fights before you have healing reduction.")
        if any("invisibility" in d.arch for d in dossiers):
            mistakes.append("Farming without truesight — their invisibility ganks punish it every time.")
        if "late_game" in my_arch and ds.late_game_delta(hid) < -0.005:
            mistakes.append("Waiting for late game: your win rate falls as the clock runs, so force objectives early.")
        if ds.late_game_delta(hid) > 0.005:
            mistakes.append("Over-committing to early fights instead of farming toward your scaling window.")
        mistakes.append("Buying your standard build without checking the counters listed in Section 4.")
        if unfavourable:
            mistakes.append(f"Fighting {unfavourable[0]} on even terms when you can pick a better angle.")

        return {
            "difficulty": difficulty,
            "difficulty_label": label,
            "win_probability": p,
            "confidence": winprob.confidence,
            "matchup_advantage": round(adv, 3),
            "main_threats": [{"hero_id": d.hero_id, "name": d.name, "danger_score": d.danger_score} for d in dossiers[:3]],
            "advantages": advantages[:4],
            "biggest_mistakes": mistakes[:5],
            "favourable_matchups": favourable[:3],
            "unfavourable_matchups": unfavourable[:3],
            "assessment": self._assessment(hero, enemies, winprob, dossiers, my_arch),
            "factors": winprob.factors,
        }

    def _assessment(self, hero: dict, enemies: list[dict], winprob, dossiers: list[EnemyDossier], my_arch: set[str]) -> str:
        p = winprob.player_win_probability
        top = dossiers[0].name if dossiers else "the enemy core"
        if p >= 56:
            base = f"This is a draft you are expected to win: {hero['localized_name']} holds the stronger side of the matchup maths."
        elif p >= 52:
            base = f"You are slightly ahead in the draft with {hero['localized_name']}, but the margin is thin enough that a lost lane erases it."
        elif p > 48:
            base = f"This is an even draft. Nothing in the maths separates {hero['localized_name']} from this lineup, so timings and execution decide it."
        elif p > 44:
            base = f"You are behind on paper. {hero['localized_name']} has to win through tempo, pickoffs and map control rather than straight fights."
        else:
            base = f"The draft is against you. Winning with {hero['localized_name']} here means punishing mistakes and closing before their advantages compound."
        return f"{base} Respect {top} above all others."

    # -- 2. lane strategy ------------------------------------------------
    def _lane_strategy(self, hero: dict, enemies: list[dict], role: str | None, my_arch: set[str]) -> dict:
        ds = self.ds
        hid = hero["id"]
        my_lane = _lane_of(hero)
        wanted = LANE_OPPONENTS.get(role or "", ())
        opponents = [e for e in enemies if _lane_of(e) in wanted] if wanted else []
        if not opponents:
            opponents = sorted(enemies, key=lambda e: -ds.counter_logit(e["id"], hid))[:2]

        rows = []
        for e in opponents:
            logit = ds.counter_logit(e["id"], hid)  # >0 means the enemy beats you
            earch = _arch(e)
            kill_threat = (
                ("stun" in earch or "lockdown" in earch or "disable" in earch)
                and ("burst_magic" in earch or "burst_physical" in earch or "nuke" in earch)
            )
            if logit >= 0.15 or (kill_threat and "escape" not in my_arch):
                risk = "high"
            elif logit >= -0.05 or kill_threat:
                risk = "medium"
            else:
                risk = "low"
            rows.append(
                {
                    "hero_id": e["id"],
                    "name": e["localized_name"],
                    "lane": _lane_of(e),
                    "risk": risk,
                    "kill_threat": kill_threat,
                    "matchup_logit": round(logit, 3),
                    "advice": self._lane_matchup_advice(e, risk, kill_threat, my_arch, hero),
                }
            )
        rows.sort(key=lambda r: -{"high": 3, "medium": 2, "low": 1}[r["risk"]])

        worst = rows[0]["risk"] if rows else "medium"
        trading = (
            "Trade aggressively only while your escape and their key spell are both down — otherwise last-hit and let them over-extend."
            if "escape" in my_arch
            else "Do not trade into their spells: you have no reliable escape, so every trade must be one you win cleanly or you skip it."
        )
        if "ranged" in my_arch and any("melee" in _arch(e) for e in opponents):
            trading += " As the ranged hero you should deny and harass from max range, never stand in melee range to last-hit."

        return {
            "phase": "0-10",
            "lane": my_lane,
            "lane_inferred": True,
            "difficulty": worst,
            "likely_opponents": rows,
            "plan": self._lane_plan(hero, rows, worst, my_arch),
            "trading": trading,
            "aggression": self._lane_aggression(worst, my_arch),
            "survival": self._lane_survival(worst, my_arch, hero),
            "when_to_call_help": self._call_help(rows, my_arch),
        }

    def _lane_matchup_advice(self, enemy: dict, risk: str, kill_threat: bool, my_arch: set[str], hero: dict) -> str:
        earch = _arch(enemy)
        bits = []
        if kill_threat:
            bits.append(
                f"{enemy['localized_name']} has a real kill combo on you in lane — treat every step past the river as a risk."
            )
        if "lockdown" in earch or "disable" in earch:
            bits.append("They need to land a disable before their damage; standing behind your creep wave breaks the angle.")
        if "burst_magic" in earch and "escape" not in my_arch:
            bits.append("Their burst is magical — a Cloak or early Magic Wand charges is what keeps you alive.")
        if "silence" in earch:
            bits.append("They can silence your escape — keep a dispel or fight only with your support next to you.")
        if risk == "low":
            bits.append("You win this lane on paper — push the wave, take the rune and force them off the creeps.")
        elif risk == "medium":
            bits.append("Even lane: trade when their spells are down, and farm the pull camp when the wave is pushed.")
        if not bits:
            bits.append("Standard lane: contest every last hit and rotate out the moment they get a level advantage.")
        return " ".join(bits)

    def _lane_plan(self, hero: dict, rows: list[dict], worst: str, my_arch: set[str]) -> list[str]:
        out = [
            "Level 1: take your highest-value ability (see Section 3) and secure the first rune if you can do it safely.",
            "Levels 2-3: contest last hits; your first item should be a lane sustain item, not a greedy component.",
        ]
        if worst == "high":
            out.append("Levels 4-5: do not contest the lane — pull the side camp, farm the jungle camp, and wait for a support rotation.")
            out.append("If you are zoned below 50% HP, buy out and rotate rather than feeding kills.")
        elif worst == "medium":
            out.append("Levels 4-5: trade when their kill spell is on cooldown, then shove the wave and take the rune.")
        else:
            out.append("Levels 4-5: hold the lane, deny their farm and push toward their tower to force a rotation.")
        out.append("Levels 6-8: with your ultimate up, look for the first kill or a rotation to the mid lane.")
        if "farm_accelerator" in my_arch:
            out.append("Use your farm acceleration to clear the stacked camps once you own your first item — this is where you pull ahead.")
        return out

    def _lane_aggression(self, worst: str, my_arch: set[str]) -> str:
        if worst == "high":
            return (
                "Play defensively until you have your level 6 and first item. You are not the lane's win condition — surviving it at even "
                "net worth is a won lane for you. Only go forward when your support is present and their key spell is down."
            )
        if worst == "medium":
            return (
                "Play even: trade on their cooldowns, push when they leave, and never dive past the tower line without vision of a "
                "rotation. A slight lane loss is fine because you scale better."
            )
        return (
            "Play aggressively: you win this lane, so deny their farm, shove the wave and take the enemy tower early. Push your advantage "
            "into a rotation rather than sitting on a won lane."
        )

    def _lane_survival(self, worst: str, my_arch: set[str], hero: dict) -> str:
        bits = []
        if "escape" in my_arch:
            bits.append("Your escape is your life — never use it to farm or to chase unless the kill is certain.")
        else:
            bits.append("You have no reliable escape, so positioning is your escape: stay on the safe side of the creep wave.")
        if worst == "high":
            bits.append("Buy a Magic Wand and a Cloak early, and ferry regen rather than walking to base.")
            bits.append("If the lane is unplayable, jungle and let the support soak — a level behind is better than three deaths.")
        bits.append("Keep a TP scroll at all times so you can join a fight or escape a collapsed lane.")
        return " ".join(bits)

    def _call_help(self, rows: list[dict], my_arch: set[str]) -> list[str]:
        out = []
        high = [r["name"] for r in rows if r["risk"] == "high"]
        if high:
            out.append(f"Ask for a rotation the moment {high[0]} commits their disable with backup — that is when a kill is available.")
        out.append("Call for help if you are pushed under your tower with no regen, or if the enemy support leaves the lane to gank.")
        if "escape" not in my_arch:
            out.append("Ping when their disable is used on you — your team has a free window to punish them.")
        return out

    # -- 3. skill build --------------------------------------------------
    def _personalise_skill(self, skill: dict, hero: dict, enemies: list[dict], my_arch: set[str]) -> dict:
        """Add matchup-specific reasons to the generic skill order."""
        notes = list(skill.get("notes", []))
        earch = _arch_many(enemies)
        abilities = hero.get("abilities", [])

        # Which of *my* abilities matter most against this lineup.
        key_abilities: list[dict] = []
        for a in abilities:
            if not a.get("key"):
                continue
            reason = None
            if "illusions" in earch or "summons" in earch:
                if a.get("is_nuke") and (a.get("dmg_type") == "Magical" or a.get("levels", 1) >= 3):
                    reason = "Their illusions and summons die to your area damage — this ability is your answer to them."
            if "silence" in earch and a.get("has_disable"):
                reason = "Your disable is the tool that survives their silence window."
            if "lockdown" in earch and a.get("bkbpierce"):
                reason = "This ability pierces spell immunity, which is rare value against a BKB-heavy draft."
            if "burst_magic" in earch and a.get("dmg_type") == "Magical" and a.get("is_nuke"):
                reason = "Trading burst with their burst is how you win the early fights — level it for the damage."
            if "invisibility" in earch and a.get("is_nuke"):
                reason = "Damage that does not need a target helps you fight invisible heroes."
            if reason:
                key_abilities.append({"name": a.get("name"), "reason": reason, "dmg_type": a.get("dmg_type")})
        # De-duplicate by name, keeping the first (highest-priority) reason.
        seen = set()
        key_abilities = [k for k in key_abilities if not (k["name"] in seen or seen.add(k["name"]))][:3]

        if "illusions" in earch or "summons" in earch:
            notes.append("Matchup note: level your area damage before your single-target ability — their army is the win condition.")
        if "lockdown" in earch:
            notes.append("Matchup note: your defensive ability (if you have one) is worth points earlier than the standard order suggests.")
        if "burst_physical" in earch:
            notes.append("Matchup note: physical burst means armour and stats beat raw damage early.")
        if "healing" in earch or "sustain" in earch:
            notes.append("Matchup note: you cannot out-sustain them — level damage and look for one-shot windows instead.")
        skill = dict(skill)
        skill["notes"] = notes
        skill["key_abilities"] = key_abilities
        return skill

    # -- 5. enemy dossiers ----------------------------------------------
    def _dossier(self, hero: dict, enemy: dict, hero_id: int) -> EnemyDossier:
        ds = self.ds
        eid = enemy["id"]
        earch = _arch(enemy)
        my_arch = _arch(hero)
        caps = enemy.get("capabilities", {}) or {}
        # How much this enemy personally beats us (from the real matchup matrix).
        threat_to_you = max(0.0, ds.counter_logit(eid, hero_id)) * 100.0

        dangerous: list[str] = []
        if caps.get("disable_count", 0) >= 1:
            dangerous.append(f"Brings {caps.get('disable_count')} disable(s) — you will be held in place while their team follows up.")
        if caps.get("stun", 0) >= 1:
            dangerous.append("Has a stun, which sets up their damage and interrupts your channel or escape.")
        if caps.get("silence", 0) >= 1:
            dangerous.append("Has a silence, so it can shut down your spell-dependent plan before a fight starts.")
        if caps.get("bkbpierce_cc", 0) >= 1:
            dangerous.append("Its control pierces spell immunity — Black King Bar alone will not break the chain.")
        if caps.get("pure", 0) >= 1:
            dangerous.append("Deals pure damage, so magic resistance and armour do nothing against it.")
        if "burst_magic" in earch:
            dangerous.append("Its damage comes as one magical burst — you die in the window before you can react.")
        if "burst_physical" in earch:
            dangerous.append("Its physical burst shreds a low-armour hero before you can disengage.")
        if "illusions" in earch:
            dangerous.append("Creates illusions, which win the map even when you win the fight.")
        if "summons" in earch:
            dangerous.append("Summons push and soak damage, forcing you to split your attention.")
        if "healing" in earch:
            dangerous.append("Heals the whole team, so damage without healing reduction is refunded.")
        if "evasion" in earch:
            dangerous.append("Has evasion, so a large share of your attacks simply miss.")
        if "invisibility" in earch:
            dangerous.append("Can turn invisible, which makes it a pickoff threat whenever you are alone.")
        if "anti_carry" in earch:
            dangerous.append("Is built to neutralise a carry — expect it to target you specifically.")
        if "split_push" in earch:
            dangerous.append("Wins by splitting the map, so it can beat you without ever fighting you.")
        if "global" in earch:
            dangerous.append("Has global presence, so a fight anywhere becomes a fight everywhere.")
        if "save" in earch:
            dangerous.append("Can save an ally from your kill, wasting your cooldowns.")
        if not dangerous:
            dangerous.append("No single dominant threat — it contributes through damage and utility rather than one win condition.")

        # Which abilities to watch, and how to beat them.
        watch = [_ability_brief(a) for a in _top_abilities(enemy, 3)]
        avoid: list[str] = []
        if caps.get("disable_count", 0) >= 1 or "lockdown" in earch:
            avoid.append("Stay out of their cast range until their disable is used — walk in behind a teammate or from fog.")
        if "burst_magic" in earch:
            avoid.append("Do not stand in the open below ~60% HP; their combo needs one clean angle to kill you.")
        if "invisibility" in earch:
            avoid.append("Carry truesight when you farm alone; their invisibility is only lethal when you cannot see it coming.")
        if "healing" in earch:
            avoid.append("Do not trade damage with them without anti-heal — you lose the exchange in the long run.")
        if "escape" in earch or "mobility" in earch:
            avoid.append("Do not commit your escape first — bait theirs, then use yours to close the distance.")
        if "split_push" in earch:
            avoid.append("Do not chase their split push with your whole team; send one hero and keep pressure elsewhere.")
        if not avoid:
            avoid.append("Trade with it only when your cooldowns are up and you have vision of its team.")

        # When can we actually fight it?
        fight_now: list[str] = []
        if "burst_magic" in earch or "burst_physical" in earch:
            fight_now.append("fight after their burst combo is spent")
        if caps.get("disable_count", 0) >= 1:
            fight_now.append("fight the moment their disable is on cooldown")
        if "healing" in earch:
            fight_now.append("fight with healing reduction applied")
        if "evasion" in earch:
            fight_now.append("fight once you have true strike")
        if "escape" in earch:
            fight_now.append("fight when you can chain control so it cannot escape")
        if not fight_now:
            fight_now.append("fight when you have a numbers advantage")
        when = "You can fight this hero when you " + ", ".join(fight_now) + "."

        items_help = self._items_for(earch, my_arch)
        positioning = self._positioning(enemy, earch, my_arch)

        lane = _lane_of(enemy)
        lane_risk = "high" if ds.counter_logit(eid, hero_id) >= 0.15 else (
            "medium" if ds.counter_logit(eid, hero_id) >= -0.05 else "low"
        )
        lane_advice = (
            f"Likely laned in the {lane}. " + self._lane_matchup_advice(enemy, lane_risk, "burst_magic" in earch or "lockdown" in earch, my_arch, hero)
        )

        danger = min(100.0, threat_to_you * 2.0 + caps.get("disable_count", 0) * 14.0
                     + (caps.get("magic", 0) + caps.get("physical", 0)) * 7.0
                     + (22.0 if "Carry" in enemy.get("roles", []) else 0.0))

        return EnemyDossier(
            hero_id=eid,
            name=enemy["localized_name"],
            icon=enemy.get("icon"),
            roles=enemy.get("roles", []),
            danger_score=round(danger, 1),
            threat_to_you=round(threat_to_you, 1),
            matchup_logit=round(ds.counter_logit(hero_id, eid), 3),
            what_makes_dangerous=dangerous[:4],
            abilities_to_watch=watch,
            how_to_avoid=avoid[:4],
            when_can_fight=when,
            items_that_help=items_help,
            positioning=positioning,
            lane_risk=lane_risk,
            lane_advice=lane_advice,
            arch=sorted(earch),
        )

    def _items_for(self, earch: set[str], my_arch: set[str]) -> list[dict]:
        """Resolve the item answers for one enemy's archetypes."""
        out: list[dict] = []
        seen: set[str] = set()
        for arch in ARCH_ORDER:
            if arch not in earch:
                continue
            rule = ITEM_ANSWERS.get(arch)
            if not rule:
                continue
            keys, why = rule
            for key in keys[:3]:
                meta = self.ds.item(key)
                if not meta or meta["key"] in seen:
                    continue
                seen.add(meta["key"])
                out.append(
                    {
                        "key": meta["key"],
                        "name": meta["dname"],
                        "cost": meta.get("cost"),
                        "img": meta.get("img"),
                        "reason": why,
                    }
                )
        return out[:5]

    def _positioning(self, enemy: dict, earch: set[str], my_arch: set[str]) -> str:
        name = enemy["localized_name"]
        if "initiation" in earch:
            return f"Never stand in the open when {name} is unaccounted for — fight only after their initiation is spent, then collapse on their back line."
        if "pickoff" in earch or "invisibility" in earch:
            return f"Stay near a teammate or a ward when {name} is missing; they convert isolation into kills, not straight fights."
        if "ranged" in earch and "melee" in my_arch:
            return f"Close the gap from fog or from behind — walking at {name} in a straight line is how you take a full combo before you reach them."
        if "lockdown" in earch:
            return f"Position so {name} cannot land their disable without entering your team's range; make them commit into you, not onto you."
        if "escape" in earch:
            return f"Approach {name} from the direction they want to escape toward, so their escape is blocked rather than free."
        return f"Trade from the edge of the fight against {name}: close when their cooldowns are down, disengage when they are up."

    # -- item attribution ------------------------------------------------
    def _attribute_items(self, build: dict, enemies: list[dict], my_arch: set[str]) -> None:
        """Tag each recommended counter item with the enemies that justify it.

        This is what makes Section 4 specific: instead of "buy BKB", the player
        sees "Black King Bar — answers Lion and Shadow Shaman's lock-down".
        """
        enemy_arch = [(e, _arch(e)) for e in enemies]
        for bucket in ("starting", "lane", "early", "mid", "late", "luxury", "situational", "emergency", "key_counters", "avoid"):
            for item in build.get(bucket, []) or []:
                triggers = [
                    e["localized_name"]
                    for e, earch in enemy_arch
                    if self._item_answers(item["key"], earch)
                ]
                item["answers"] = triggers[:4]
                if triggers:
                    item["reason"] = f"{item['reason']} Answers: {', '.join(triggers[:3])}."

    def _item_answers(self, item_key: str, earch: set[str]) -> bool:
        for arch in earch:
            rule = ITEM_ANSWERS.get(arch)
            if rule and item_key in rule[0]:
                return True
        return False

    # -- 6. teamfight ----------------------------------------------------
    def _teamfight(self, hero: dict, enemies: list[dict], dossiers: list[EnemyDossier], my_arch: set[str], winprob) -> dict:
        earch = _arch_many(enemies)
        top = dossiers[0] if dossiers else None

        if "initiation" in my_arch or "initiation" in earch:
            initiate = (
                "You or your initiator must land the first spell. Fight only with vision and with your team behind you — an initiation "
                "into fog with no follow-up is how drafts like this lose."
            )
        else:
            initiate = "Neither side has a clean initiator, so the fight starts with a pickoff or an objective. Do not open the fight yourself."

        if "save" in earch:
            wait = "Wait for their save to be used on someone else, or kill the saver first; committing into a live save wastes your cooldowns."
        elif "lockdown" in earch:
            wait = "Wait for their lock-down to be spent on someone else — that is your window to walk in and do damage."
        else:
            wait = "Wait for their burst to land on your front line before you commit; walking in first means eating it yourself."

        if "burst_magic" in earch or "burst_physical" in earch:
            survive = "Survive the first two seconds: an early BKB, Glimmer or Aeon Disk is worth more than a damage item against this draft."
        else:
            survive = "Survive by positioning: keep a teammate between you and their damage and disengage the moment the fight turns."

        if "ranged" in my_arch:
            stand = "Stand at the back of your team, at max attack range, and step forward only when their gap-closers are on cooldown."
        elif "tanky" in my_arch or "initiation" in my_arch:
            stand = "Stand at the front and absorb the first spell, but only with a defensive item up and your team within follow-up range."
        else:
            stand = "Stand on the flank, out of their initiation range, and enter the fight from the side once it starts."

        # The two enemies that punish our hero hardest — always populated so the
        # section is never empty, even in a soft draft.
        avoid_targets = [d.name for d in dossiers[:2]]
        kill_first = top.name if top else "the enemy core"

        return {
            "where_to_stand": stand,
            "target_first": kill_first,
            "avoid": avoid_targets,
            "when_to_initiate": initiate,
            "when_to_wait": wait,
            "how_to_survive": survive,
            "notes": self._teamfight_notes(earch, my_arch, winprob),
        }

    def _teamfight_notes(self, earch: set[str], my_arch: set[str], winprob) -> list[str]:
        out = []
        if "teamfight" in earch and winprob.player_win_probability < 50:
            out.append("They are the stronger straight-up teamfight draft: win with a pickoff or an objective, not a 5v5.")
        if "split_push" in earch:
            out.append("Do not chase their split pusher with five heroes — trade the opposite lane and keep your own pressure.")
        if "global" in earch:
            out.append("Expect a fight to become a fight everywhere: account for their global heroes before you commit to a long chase.")
        if "illusions" in earch or "summons" in earch:
            out.append("Clear the army before the hero: killing the illusions is often worth more than the damage you would deal to the real target.")
        if "healing" in earch:
            out.append("Apply healing reduction before the fight, not during it — anti-heal after the first heal is already late.")
        return out

    # -- one-sentence game plan -----------------------------------------
    def _game_plan_sentence(self, hero: dict, dossiers: list[EnemyDossier], build: dict, targets: list[dict], winprob, my_arch: set[str]) -> str:
        key_item = None
        for bucket in ("key_counters", "mid", "early", "lane"):
            if build.get(bucket):
                key_item = build[bucket][0]["name"]
                break
        if not key_item:
            key_item = "your first core item"
        top = targets[0]["name"] if targets else (dossiers[0].name if dossiers else "the enemy core")
        tone = (
            "heavily favoured" if winprob.player_win_probability >= 58
            else "favoured" if winprob.player_win_probability >= 52
            else "a coin flip" if winprob.player_win_probability > 48
            else "an uphill game"
        )
        clause = f"finish {key_item} on time, kill {top} first"
        if any("lockdown" in d.arch for d in dossiers):
            clause += ", and never walk into fog alone"
        if any("healing" in d.arch for d in dossiers):
            clause += ", buying healing reduction before the first teamfight"
        return (
            f"Play {hero['localized_name']} to the plan: {clause} — this matchup is {tone} "
            f"({winprob.player_win_probability:.0f}% draft win probability)."
        )

    # -- confidence ------------------------------------------------------
    def _confidence(self, hero: dict, enemies: list[dict], winprob, problems: dict) -> dict:
        measured = [
            "head-to-head matchup advantage (shrunk OpenDota matrix)",
            "hero win rate at this patch",
            "empirical win rate by game duration",
            "ability damage types and disable counts (Valve hero constants)",
        ]
        inferred = [
            "lane assignment and lane opponents",
            "teamfight positioning",
            "which item answers which threat",
        ]
        notes = []
        if not hero.get("abilities"):
            notes.append("This hero has no compiled ability data, so ability-level advice is limited.")
        if winprob.confidence == "low":
            notes.append("The draft maths are close to even, so treat the win probability as a coin flip rather than a prediction.")
        if any(not e.get("abilities") for e in enemies):
            notes.append("At least one enemy has no compiled ability data; its dossier falls back to capability counters.")
        notes.append("Hero and item names are shown in English, matching community convention.")
        return {
            "measured": measured,
            "inferred": inferred,
            "notes": notes,
            "patch": (self.ds.patch or {}).get("name"),
            "dataset_generated_at": self.ds.generated_at,
        }


# Order in which archetypes are considered when listing item answers, so the
# most decisive threat is named first.
ARCH_ORDER = [
    "lockdown",
    "bkbpierce_cc",
    "burst_magic",
    "magic_heavy",
    "burst_physical",
    "physical_heavy",
    "pure_damage",
    "illusions",
    "summons",
    "healing",
    "sustain",
    "evasion",
    "invisibility",
    "silence",
    "kite",
    "escape",
    "mobility",
    "save",
    "tanky",
    "anti_carry",
    "anti_magic",
    "anti_heal",
    "anti_illusion",
    "split_push",
    "push",
    "pickoff",
    "initiation",
    "teamfight",
]


def _arch_many(heroes: Iterable[dict]) -> set[str]:
    out: set[str] = set()
    for h in heroes:
        out |= _arch(h)
    return out


def _arch_by_id(ds: Dataset, hero_id: int) -> set[str]:
    h = ds.by_id.get(hero_id)
    return _arch(h) if h else set()
