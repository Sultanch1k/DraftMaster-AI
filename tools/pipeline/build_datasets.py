#!/usr/bin/env python3
"""DraftMaster AI data pipeline.

Pulls live data from the OpenDota API, computes a statistically shrunk hero
counter matrix, meta win rates and hero capability profiles, then emits a single
compact artifact consumed by the strategy engine.

Design notes
------------
* Counter relationships are estimated with an *empirical-Bayes shrunk logit*:
  each hero-vs-hero cell is pulled toward the hero's global matchup prior based
  on how many games were observed. This avoids the classic trap of trusting a
  40-game 70% matchup.
* Damage/CC profiles are derived from the real Valve ability constants
  (`dmg_type`, `bkbpierce`, `behavior`) rather than hand-waved labels, and are
  then fused with curated tactical tags for mechanics the constants cannot
  express (e.g. "summons heavy", "needs early BKB").
* Everything is cached to data/raw so the pipeline is re-runnable offline.

Usage:
    python tools/pipeline/build_datasets.py            # use cache if present
    python tools/pipeline/build_datasets.py --refresh   # force re-download
"""
from __future__ import annotations

import argparse
import json
import re
import math
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
ARTIFACTS = ROOT / "data" / "artifacts"
RAW.mkdir(parents=True, exist_ok=True)
ARTIFACTS.mkdir(parents=True, exist_ok=True)

API = "https://api.opendota.com/api"
API_KEY = os.environ.get("OPENDOTA_API_KEY", "").strip()


def _url(path: str) -> str:
    base = f"{API}/{path.lstrip('/')}"
    if API_KEY:
        sep = "&" if "?" in base else "?"
        base = f"{base}{sep}api_key={API_KEY}"
    return base


def fetch(path: str, cache_name: str, refresh: bool = False, retries: int = 4):
    """Fetch a JSON endpoint with on-disk caching and 429 backoff."""
    dest = RAW / cache_name
    if dest.exists() and not refresh:
        with dest.open() as fh:
            return json.load(fh)
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                _url(path), headers={"User-Agent": "DraftMasterAI/1.0"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            with dest.open("w") as fh:
                json.dump(data, fh)
            return data
        except urllib.error.HTTPError as exc:  # pragma: no cover - network
            last_err = exc
            if exc.code == 429:
                # OpenDota throttles aggressively; back off hard and retry.
                time.sleep(30.0 * (attempt + 1))
                continue
            if exc.code >= 500:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
        except Exception as exc:  # pragma: no cover - network
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
    if dest.exists():
        with dest.open() as fh:
            return json.load(fh)
    raise RuntimeError(f"failed to fetch {path}: {last_err}")


# ---------------------------------------------------------------------------
# Hero capability profile derivation
# ---------------------------------------------------------------------------

# Tags that cannot be inferred from ability constants. Kept deliberately small
# and auditable; every entry maps to an observable mechanical fact.
TACTICAL_TAGS: dict[str, list[str]] = {
    # Physical / illusion / summon pressure
    "npc_dota_hero_phantom_lancer": ["illusion_carry", "needs_aoe_clear"],
    "npc_dota_hero_naga_siren": ["illusion_carry", "needs_aoe_clear", "split_push"],
    "npc_dota_hero_terrorblade": ["illusion_carry", "needs_aoe_clear"],
    "npc_dota_hero_arc_warden": ["illusion_carry", "needs_aoe_clear", "split_push"],
    "npc_dota_hero_meepo": ["illusion_carry", "needs_aoe_clear", "split_push"],
    "npc_dota_hero_lycan": ["summon_heavy", "needs_aoe_clear", "push"],
    "npc_dota_hero_broodmother": ["summon_heavy", "needs_aoe_clear", "split_push"],
    "npc_dota_hero_natures_prophet": ["summon_heavy", "split_push", "push"],
    "npc_dota_hero_beastmaster": ["summon_heavy", "push"],
    "npc_dota_hero_visage": ["summon_heavy", "push"],
    "npc_dota_hero_enigma": ["summon_heavy", "teamfight"],
    "npc_dota_hero_chen": ["summon_heavy", "push"],
    # Healing / regen dependent
    "npc_dota_hero_necrolyte": ["heal_heavy", "sustain", "tanky"],
    "npc_dota_hero_timbersaw": ["heal_heavy", "sustain", "tanky", "escape"],
    "npc_dota_hero_huskar": ["heal_heavy", "sustain", "anti_magic_sustain"],
    "npc_dota_hero_alchemist": ["heal_heavy", "sustain", "farm_accelerator"],
    "npc_dota_hero_oracle": ["heal_heavy", "save"],
    "npc_dota_hero_dazzle": ["heal_heavy", "save"],
    "npc_dota_hero_io": ["heal_heavy", "save", "global_presence"],
    "npc_dota_hero_wisp": ["heal_heavy", "save", "global_presence"],
    "npc_dota_hero_abaddon": ["heal_heavy", "save", "tanky"],
    "npc_dota_hero_treant": ["heal_heavy", "save", "teamfight"],
    "npc_dota_hero_warlock": ["heal_heavy", "teamfight", "summon_heavy"],
    "npc_dota_hero_undying": ["heal_heavy", "sustain", "teamfight"],
    "npc_dota_hero_winter_wyvern": ["heal_heavy", "save"],
    "npc_dota_hero_morphling": ["heal_heavy", "sustain", "tanky", "escape"],
    "npc_dota_hero_life_stealer": ["heal_heavy", "sustain", "tanky"],
    "npc_dota_hero_legion_commander": ["heal_heavy", "duel", "pickoff"],
    # Evasion / blind / physical immunity
    "npc_dota_hero_phantom_assassin": ["evasion", "crit", "burst_physical"],
    "npc_dota_hero_troll_warlord": ["evasion", "sustain", "attack_speed"],
    "npc_dota_hero_windrunner": ["evasion", "escape"],
    "npc_dota_hero_faceless_void": ["evasion", "teamfight", "burst_physical"],
    "npc_dota_hero_brewmaster": ["evasion", "teamfight"],
    # Heavy physical damage cores
    "npc_dota_hero_ursa": ["burst_physical", "sustain", "roshan"],
    "npc_dota_hero_sven": ["burst_physical", "teamfight", "cleave"],
    "npc_dota_hero_templar_assassin": ["burst_physical", "pickoff"],
    "npc_dota_hero_luna": ["burst_physical", "teamfight", "push"],
    "npc_dota_hero_gyrocopter": ["burst_physical", "teamfight", "needs_aoe_clear"],
    "npc_dota_hero_medusa": ["burst_physical", "tanky", "teamfight"],
    "npc_dota_hero_drow_ranger": ["burst_physical", "push", "kite"],
    "npc_dota_hero_clinkz": ["burst_physical", "pickoff", "invis"],
    "npc_dota_hero_slark": ["burst_physical", "sustain", "escape", "pickoff"],
    "npc_dota_hero_riki": ["burst_physical", "invis", "pickoff"],
    "npc_dota_hero_bounty_hunter": ["invis", "pickoff", "gold_swing"],
    # Magic burst
    "npc_dota_hero_lina": ["burst_magic", "nuke"],
    "npc_dota_hero_leshrac": ["burst_magic", "push", "nuke"],
    "npc_dota_hero_zeus": ["burst_magic", "nuke", "global_presence", "truesight"],
    "npc_dota_hero_skywrath_mage": ["burst_magic", "silence", "nuke"],
    "npc_dota_hero_lion": ["burst_magic", "single_target_lockdown", "disable", "nuke"],
    "npc_dota_hero_shadow_shaman": ["disable", "single_target_lockdown", "push", "nuke"],
    "npc_dota_hero_ancient_apparition": ["burst_magic", "anti_heal", "nuke"],
    "npc_dota_hero_pugna": ["burst_magic", "nuke", "push", "anti_magic"],
    "npc_dota_hero_tinker": ["burst_magic", "nuke", "push"],
    "npc_dota_hero_storm_spirit": ["burst_magic", "mobility", "teamfight"],
    "npc_dota_hero_queenofpain": ["burst_magic", "mobility", "nuke"],
    "npc_dota_hero_puck": ["burst_magic", "mobility", "teamfight", "initiation"],
    "npc_dota_hero_outworld_destroyer": ["burst_magic", "anti_magic"],
    "npc_dota_hero_obsidian_destroyer": ["burst_magic", "anti_magic"],
    "npc_dota_hero_necrolyte_2": ["burst_magic"],
    # Teamfight / initiation
    "npc_dota_hero_enigma_2": ["teamfight", "initiation"],
    "npc_dota_hero_magnataur": ["teamfight", "initiation", "disable"],
    "npc_dota_hero_tidehunter": ["teamfight", "initiation", "disable"],
    "npc_dota_hero_axe": ["teamfight", "initiation", "disable", "tanky"],
    "npc_dota_hero_earthshaker": ["teamfight", "initiation", "disable", "burst_magic"],
    "npc_dota_hero_faceless_void_2": ["teamfight", "initiation"],
    "npc_dota_hero_sand_king": ["teamfight", "initiation", "disable", "nuke"],
    "npc_dota_hero_centaur": ["teamfight", "initiation", "tanky", "burst_magic"],
    "npc_dota_hero_slardar": ["teamfight", "initiation", "single_target_lockdown", "tanky"],
    "npc_dota_hero_batrider": ["initiation", "single_target_lockdown", "disable"],
    "npc_dota_hero_beastmaster_2": ["teamfight", "initiation"],
    "npc_dota_hero_dark_seer": ["teamfight", "push", "save"],
    "npc_dota_hero_doom_bringer": ["single_target_lockdown", "disable", "tanky", "sustain"],
    "npc_dota_hero_shadow_demon": ["save", "disable", "single_target_lockdown"],
    "npc_dota_hero_bane": ["disable", "single_target_lockdown", "anti_carry"],
    "npc_dota_hero_rubick": ["disable", "save", "steal_ult"],
    "npc_dota_hero_invoker": ["burst_magic", "teamfight", "disable"],
    "npc_dota_hero_zeus_2": ["burst_magic"],
    "npc_dota_hero_witch_doctor": ["disable", "teamfight", "heal_heavy", "nuke"],
    "npc_dota_hero_grimstroke": ["teamfight", "disable", "silence", "save"],
    "npc_dota_hero_dawnbreaker": ["teamfight", "heal_heavy", "global_presence"],
    "npc_dota_hero_primal_beast": ["initiation", "tanky", "teamfight"],
    "npc_dota_hero_marci": ["initiation", "single_target_lockdown", "burst_physical"],
    "npc_dota_hero_mars": ["teamfight", "initiation", "disable", "tanky"],
    "npc_dota_hero_elder_titan": ["teamfight", "initiation", "anti_illusion"],
    "npc_dota_hero_kunkka": ["teamfight", "cleave", "burst_magic"],
    "npc_dota_hero_earth_spirit": ["initiation", "disable", "teamfight", "mobility"],
    "npc_dota_hero_snapfire": ["disable", "save", "nuke"],
    "npc_dota_hero_hoodwink": ["nuke", "escape", "disable"],
    "npc_dota_hero_muerta": ["nuke", "burst_physical"],
    # Mobility / pickoff
    "npc_dota_hero_ember_spirit": ["mobility", "burst_magic", "pickoff"],
    "npc_dota_hero_void_spirit": ["mobility", "teamfight", "burst_magic"],
    "npc_dota_hero_weaver": ["mobility", "escape", "burst_physical"],
    "npc_dota_hero_anti_mage": ["mobility", "farm_accelerator", "split_push"],
    "npc_dota_hero_terrorblade_2": ["mobility"],
    "npc_dota_hero_monkey_king": ["mobility", "burst_physical", "pickoff"],
    "npc_dota_hero_spectre": ["global_presence", "tanky", "late_game"],
    "npc_dota_hero_zuus": ["global_presence"],
    "npc_dota_hero_furion": ["global_presence", "split_push", "push"],
    "npc_dota_hero_spirit_breaker": ["global_presence", "initiation", "single_target_lockdown"],
    "npc_dota_hero_night_stalker": ["initiation", "pickoff", "vision_denial"],
    "npc_dota_hero_bounty_hunter_2": ["vision_denial"],
    "npc_dota_hero_templar_assassin_2": ["vision_denial"],
    "npc_dota_hero_slark_2": ["vision_denial"],
    # Push / objectives
    "npc_dota_hero_death_prophet": ["push", "sustain", "teamfight"],
    "npc_dota_hero_jakiro": ["push", "teamfight", "nuke"],
    "npc_dota_hero_undying_2": ["teamfight"],
    "npc_dota_hero_warlock_2": ["teamfight"],
    "npc_dota_hero_luna_2": ["push"],
    "npc_dota_hero_tiny": ["burst_magic", "burst_physical", "push", "roshan"],
    "npc_dota_hero_chaos_knight": ["illusion_carry", "single_target_lockdown", "tanky"],
    "npc_dota_hero_lifestealer": ["sustain", "tanky", "anti_carry"],
    "npc_dota_hero_omniknight": ["save", "heal_heavy", "anti_magic"],
    "npc_dota_hero_wisp_2": ["save"],
    "npc_dota_hero_treant_protector": ["save", "heal_heavy"],
    "npc_dota_hero_shredder": ["heal_heavy", "escape", "tanky"],
    "npc_dota_hero_vengefulspirit": ["save", "initiation"],
    "npc_dota_hero_sven_2": ["cleave"],
    "npc_dota_hero_huskar_2": ["heal_heavy"],
    "npc_dota_hero_windrunner_2": ["evasion"],
    "npc_dota_hero_medusa_2": ["tanky"],
    "npc_dota_hero_undying_3": ["teamfight"],
    "npc_dota_hero_tidehunter_2": ["teamfight"],
    "npc_dota_hero_skywrath_mage_2": ["silence"],
    "npc_dota_hero_disruptor": ["disable", "teamfight", "anti_carry"],
    "npc_dota_hero_vengefulspirit_2": ["initiation"],
    "npc_dota_hero_lich": ["nuke", "teamfight", "anti_carry"],
    "npc_dota_hero_wyvern": ["save"],
    "npc_dota_hero_ogre_magi": ["disable", "nuke", "tanky"],
    "npc_dota_hero_crystal_maiden": ["disable", "teamfight", "nuke", "aura"],
    "npc_dota_hero_dazzle_2": ["save"],
    "npc_dota_hero_wisp_3": ["save"],
    "npc_dota_hero_sniper": ["push", "kite", "late_game", "burst_physical"],
    "npc_dota_hero_razor": ["anti_carry", "sustain", "teamfight"],
    "npc_dota_hero_viper": ["anti_carry", "sustain", "kite"],
    "npc_dota_hero_venomancer": ["push", "anti_heal", "summon_heavy"],
    "npc_dota_hero_dark_willow": ["disable", "save", "invis"],
    "npc_dota_hero_mirana": ["escape", "nuke", "disable"],
    "npc_dota_hero_pudge": ["single_target_lockdown", "pickoff", "tanky", "heal_heavy"],
    "npc_dota_hero_techies": ["push", "anti_push", "nuke"],
    "npc_dota_hero_tusk": ["initiation", "single_target_lockdown", "save"],
    "npc_dota_hero_undying_4": ["teamfight"],
    "npc_dota_hero_wisp_4": ["save"],
}

# Canonicalisation: some curated keys use legacy/alias names or numeric variant
# suffixes that do not match OpenDota's hero `name`. Normalise them so every
# curated tag actually lands on a real hero.
_HERO_ALIASES = {
    "npc_dota_hero_anti_mage": "npc_dota_hero_antimage",
    "npc_dota_hero_natures_prophet": "npc_dota_hero_furion",
    "npc_dota_hero_outworld_destroyer": "npc_dota_hero_obsidian_destroyer",
    "npc_dota_hero_timbersaw": "npc_dota_hero_shredder",
    "npc_dota_hero_treant_protector": "npc_dota_hero_treant",
    "npc_dota_hero_zeus": "npc_dota_hero_zuus",
    "npc_dota_hero_io": "npc_dota_hero_wisp",
    "npc_dota_hero_lifestealer": "npc_dota_hero_life_stealer",
    "npc_dota_hero_wyvern": "npc_dota_hero_winter_wyvern",
}


def canon_hero_key(key: str) -> str:
    k = _HERO_ALIASES.get(key, key)
    k = re.sub(r"_\d+$", "", k)
    return _HERO_ALIASES.get(k, k)


def _normalise_tags(raw: dict[str, list[str]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for key, tags in raw.items():
        out.setdefault(canon_hero_key(key), [])
        for t in tags:
            if t not in out[canon_hero_key(key)]:
                out[canon_hero_key(key)].append(t)
    return out


TACTICAL_TAGS = _normalise_tags(TACTICAL_TAGS)


# Curated recommended item answers per tactical problem. These are *principles*
# the dynamic item builder applies when the enemy draft exhibits the problem.
COUNTER_ITEM_RULES: list[dict] = [
    {
        "problem": "heavy_single_target_disable",
        "items": ["black_king_bar", "aeon_disk", "linkens_sphere"],
        "reason": "Enemy draft stacks targeted disables; BKB/Aeon deny the chain that would kill you.",
    },
    {
        "problem": "heavy_magic_burst",
        "items": ["black_king_bar", "pipe", "mage_slayer", "cloak"],
        "reason": "Enemy deals most damage as magical burst; magic resistance and BKB are the cheapest survival.",
    },
    {
        "problem": "heavy_physical",
        "items": ["assault", "shivas_guard", "crimson_guard", "solar_crest", "heavens_halberd"],
        "reason": "Enemy wins through physical DPS; armor and attack-slow cut their damage far more than HP.",
    },
    {
        "problem": "evasion_or_blind",
        "items": ["monkey_king_bar", "bloodthorn", "nullifier"],
        "reason": "Enemy relies on evasion; true strike removes their defensive layer entirely.",
    },
    {
        "problem": "illusions_or_summons",
        "items": ["mjollnir", "radiance", "battle_fury", "shivas_guard", "maelstrom", "gleipnir"],
        "reason": "Illusions and summons are cleared by AoE, not single-target damage.",
    },
    {
        "problem": "heal_heavy",
        "items": ["spirit_vessel", "skadi", "shivas_guard", "eye_of_skadi"],
        "reason": "Enemy out-sustains you; anti-heal converts their main strength into a weakness.",
    },
    {
        "problem": "invisibility",
        "items": ["dust_of_appearance", "gem", "sentry_ward", "nullifier"],
        "reason": "Invisible threats are neutralised by detection and a disable that reveals.",
    },
    {
        "problem": "heavy_cc_teamfight",
        "items": ["black_king_bar", "satanic", "linkens_sphere", "glimmer_cape", "pipe"],
        "reason": "Enemy wants one clean teamfight combo; BKB plus a save item breaks the chain.",
    },
    {
        "problem": "kite_and_slow",
        "items": ["boots_of_bearing", "phase_boots", "force_staff", "hurricane_pike", "euls_scepter"],
        "reason": "Enemy kites you out of fights; mobility items restore your uptime.",
    },
    {
        "problem": "silence",
        "items": ["black_king_bar", "euls_scepter", "manta_style", "guardian_greaves"],
        "reason": "Silence locks your kit; a dispel restores your ability to fight.",
    },
    {
        "problem": "burst_pure_damage",
        "items": ["black_king_bar", "heart", "satanic", "aeon_disk"],
        "reason": "Pure/burst damage ignores your resistances; raw HP plus BKB is the answer.",
    },
    {
        "problem": "split_push",
        "items": ["boots_of_travel", "manta_style", "radiance", "shivas_guard"],
        "reason": "Enemy wins by split-pushing; you need global presence and fast wave clear.",
    },
]

# Items that are actively bad into specific problems (the "Items To Avoid" box).
AVOID_ITEM_RULES: list[dict] = [
    {
        "problem": "heavy_magic_burst",
        "items": ["assault", "butterfly", "solar_crest"],
        "reason": "Pure armor items do almost nothing against a magical-burst draft.",
    },
    {
        "problem": "evasion_or_blind",
        "items": ["butterfly", "heavens_halberd"],
        "reason": "Stacking more evasion does not answer an enemy that already ignores yours.",
    },
    {
        "problem": "heal_heavy",
        "items": ["octarine_core", "refresher"],
        "reason": "Long-cooldown sustain items lose the attrition war to a healing draft.",
    },
    {
        "problem": "illusion_or_summons",
        "items": ["desolator", "skull_basher"],
        "reason": "Single-target items cannot clear a board of illusions or summons.",
    },
    {
        "problem": "heavy_physical",
        "items": ["kaya_and_sange"],
        "reason": "Spell amplification does nothing when the enemy kills you with right clicks.",
    },
]


def _norm_hero_key(hero_name: str) -> str:
    return hero_name


# Internal placeholder abilities that are never skillable or displayed.
_PLACEHOLDER_ABILITY = re.compile(r"(_empty\d*|_hidden\d*|_land\b|^generic_|attribute_bonus$)")


def _iter_abilities(payload: dict):
    """Yield real ability names, flattening nested lists (Monkey King's forms)."""
    for entry in payload.get("abilities", []):
        entries = [entry] if isinstance(entry, str) else list(entry or [])
        for name in entries:
            if isinstance(name, str) and not _PLACEHOLDER_ABILITY.search(name):
                yield name


def parse_ability_flags(abilities: dict, hero_abilities: dict) -> dict[str, dict]:
    """Aggregate real ability constants into per-hero damage/CC capability flags."""
    out: dict[str, dict] = {}
    for hero_key, payload in hero_abilities.items():
        flags = {
            "magic": 0.0,
            "physical": 0.0,
            "pure": 0.0,
            "cc": 0.0,
            "bkbpierce_cc": 0.0,
            "nuke_count": 0,
            "disable_count": 0,
            "silence": 0,
            "stun": 0,
        }
        for ab_name in _iter_abilities(payload):
            ab = abilities.get(ab_name)
            if not ab:
                continue
            dmg = (ab.get("dmg_type") or "").lower()
            behavior = ab.get("behavior") or []
            if isinstance(behavior, str):
                behavior = [behavior]
            behavior_l = " ".join(b.lower() for b in behavior)
            desc = (ab.get("desc") or "").lower()

            is_damage = any(k in behavior_l for k in ("target", "aoe", "no target")) and (
                "damage" in desc or dmg in ("magical", "physical", "pure")
            )
            if is_damage:
                if dmg == "magical":
                    flags["magic"] += 1.0
                elif dmg == "physical":
                    flags["physical"] += 1.0
                elif dmg == "pure":
                    flags["pure"] += 1.0
                if "damage" in desc:
                    flags["nuke_count"] += 1

            is_disable = any(
                k in desc
                for k in (
                    "stun",
                    "stunned",
                    "root",
                    "rooted",
                    "hex",
                    "silence",
                    "silenced",
                    "leash",
                    "taunt",
                    "fear",
                    "berserk",
                    "slow",
                    "slowed",
                    "bind",
                )
            )
            if is_disable:
                flags["disable_count"] += 1
                if "silence" in desc:
                    flags["silence"] += 1
                if "stun" in desc or "hex" in desc or "root" in desc:
                    flags["stun"] += 1
                weight = 1.0 if ("stun" in desc or "hex" in desc or "root" in desc) else 0.6
                flags["cc"] += weight
                if str(ab.get("bkbpierce", "")).lower() == "yes":
                    flags["bkbpierce_cc"] += weight
        out[hero_key] = flags
    return out


def _ability_level_count(ab: dict) -> int:
    """Number of levelled values (1/3/4) inferred from any array-valued field."""
    best = 1
    for k in ("mc", "cd", "dmg", "duration"):
        v = ab.get(k)
        if isinstance(v, list):
            best = max(best, len(v))
    return best


# Heroes whose ultimate cannot be inferred from level counts alone.
_ULT_OVERRIDES = {
    "npc_dota_hero_invoker": "invoker_invoke",
    "npc_dota_hero_meepo": "meepo_divided_we_stand",
    "npc_dota_hero_riki": "riki_tricks_of_the_trade",
    "npc_dota_hero_bristleback": "bristleback_warpath",
    "npc_dota_hero_kez": "kez_ravens_veil",
    "npc_dota_hero_largo": "largo_song_good_vibrations",
}


def _heuristic_ultimate(names: list[str], abilities: dict, hero_key: str | None = None) -> str | None:
    """Valve exposes no explicit 'ultimate' flag, so infer it.

    Rule: the last ability that has exactly three levels is the ultimate for
    essentially every hero; a small number of heroes (Drow, PA, Bristleback,
    Medusa, ...) have single-level ultimates, which are detected by matching the
    internal ability name against the hero's own name stem.
    """
    override = _ULT_OVERRIDES.get(hero_key or "")
    if override and override in names:
        return override
    three = [n for n in names if _ability_level_count(abilities[n]) == 3]
    if three:
        return three[-1]
    stem = names[0].split("_")[0] if names else ""
    for n in reversed(names):
        if n.startswith(stem + "_") and n.count("_") >= 2:
            return n
    return names[-1] if names else None


def parse_hero_ability_meta(abilities: dict, hero_abilities: dict) -> dict[str, list[dict]]:
    """Per-hero ordered ability metadata (for skill builds and lane plans)."""
    out: dict[str, list[dict]] = {}
    for hero_key, payload in hero_abilities.items():
        rows = []
        names = [
            n
            for n in _iter_abilities(payload)
            if not n.startswith("generic_") and n != "attribute_bonus" and abilities.get(n)
        ]
        ult = _heuristic_ultimate(names, abilities, hero_key)
        for ab_name in names:
            ab = abilities[ab_name]
            desc = ab.get("desc") or ""
            dl = desc.lower()
            rows.append(
                {
                    "key": ab_name,
                    "name": ab.get("dname") or ab_name,
                    "dmg_type": (ab.get("dmg_type") or "None"),
                    "bkbpierce": str(ab.get("bkbpierce", "No")).lower() == "yes",
                    "levels": _ability_level_count(ab),
                    "is_ultimate": ab_name == ult,
                    "has_disable": any(
                        k in dl for k in ("stun", "root", "hex", "silence", "leash", "taunt", "fear", "slow")
                    ),
                    "is_nuke": "damage" in dl,
                    "desc": desc[:220],
                }
            )
        out[hero_key] = rows
    return out


def _bonus_map(hero_key: str, hero_abilities: dict, abilities: dict) -> dict[str, str]:
    """Map bonus_* keys used in talent descriptions to concrete values."""
    out: dict[str, str] = {}
    payload = hero_abilities.get(hero_key, {})
    for ab_name in _iter_abilities(payload):
        ab = abilities.get(ab_name)
        if not ab:
            continue
        for attrib in ab.get("attrib", []) or []:
            key = attrib.get("key")
            val = attrib.get("value")
            if not key or val is None:
                continue
            if isinstance(val, list):
                val = val[0] if val else ""
            out[key] = str(val).split(" / ")[0]
        # Generic placeholders used by talent text but absent from `attrib`.
        cd = ab.get("cd")
        mc = ab.get("mc")
        if isinstance(cd, list) and cd:
            out.setdefault("AbilityCooldown", str(cd[0]))
        elif isinstance(cd, (str, int)):
            out.setdefault("AbilityCooldown", str(cd))
        if isinstance(mc, list) and mc:
            out.setdefault("AbilityManaCost", str(mc[0]))
        for attrib in ab.get("attrib", []) or []:
            if attrib.get("key") == "abilitycastrange":
                out.setdefault("AbilityCastRange", str(attrib.get("value", "")).split(" / ")[0])
    return out


_PLACEHOLDER = re.compile(r"\{s:bonus_([A-Za-z0-9_]+)\}")


def _resolve_talent_desc(desc: str, bonus: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        key = m.group(1)
        if key in bonus:
            return bonus[key]
        return key.replace("_", " ")
    return _PLACEHOLDER.sub(repl, desc).replace("%%", "%")


def parse_talents(abilities: dict, hero_abilities: dict) -> dict[str, list[dict]]:
    """Extract the real talent tree (level 10/15/20/25 pairs) per hero."""
    out: dict[str, list[dict]] = {}
    for hero_key, payload in hero_abilities.items():
        bonus = _bonus_map(hero_key, hero_abilities, abilities)
        tiers: dict[int, list[dict]] = {}
        for t in payload.get("talents", []):
            name = t.get("name", "")
            level = t.get("level")
            meta = abilities.get(name) or {}
            desc = meta.get("dname") or name.replace("special_bonus_", "").replace("_", " ")
            desc = _resolve_talent_desc(desc, bonus)
            tiers.setdefault(level, []).append({"name": name, "desc": desc})
        if tiers:
            out[hero_key] = [
                {"tier": lvl, "hero_level": 10 + (lvl - 1) * 5, "options": tiers[lvl]}
                for lvl in sorted(tiers)
            ]
    return out


def build_counter_matrix(hero_stats: list[dict], matchups: dict[int, list], refresh: bool) -> dict:
    """Empirical-Bayes shrunk counter scores.

    For hero A vs hero B we observe games_played / wins from A's perspective.
    We shrink log((w+1)/(g-w+1)) toward A's global matchup prior with weight k.
    The resulting value is A's advantage against B on a ~[-1, 1] logit scale.
    """
    K = 300.0  # shrinkage strength (in pseudo-games)
    per_hero: dict[int, dict[int, float]] = {}
    global_prior: dict[int, float] = {}

    for h in hero_stats:
        hid = h["id"]
        rows = matchups.get(hid, [])
        tot_g = sum(r["games_played"] for r in rows)
        tot_w = sum(r["wins"] for r in rows)
        if tot_g > 0:
            base = (tot_w + 1) / (tot_g + 2)
        else:
            base = 0.5
        global_prior[hid] = math.log(base / (1 - base))

    for h in hero_stats:
        hid = h["id"]
        prior = global_prior[hid]
        per_hero[hid] = {}
        for row in matchups.get(hid, []):
            opp = row["hero_id"]
            g = row["games_played"]
            w = row["wins"]
            if g <= 0:
                continue
            raw = math.log((w + 0.5) / (g - w + 0.5))
            shrunk = (raw * g + prior * K) / (g + K)
            per_hero[hid][opp] = round(shrunk, 4)

    # Symmetrise: counter[A][B] = -counter[B][A] (average both observations).
    sym: dict[int, dict[int, float]] = {hid: {} for hid in per_hero}
    ids = list(per_hero.keys())
    for a in ids:
        for b, v in per_hero[a].items():
            rev = per_hero.get(b, {}).get(a)
            if rev is None:
                sym[a][b] = round(v, 4)
            else:
                sym[a][b] = round((v - rev) / 2.0, 4)
    return {
        "shrinkage_k": K,
        "global_prior_logit": {str(k): round(v, 4) for k, v in global_prior.items()},
        "matrix": {str(a): {str(b): v for b, v in row.items()} for a, row in sym.items()},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    refresh = args.refresh

    print("Fetching heroStats ...")
    hero_stats = fetch("heroStats", "heroStats.json", refresh)
    hero_stats = [h for h in hero_stats if h.get("id")]
    hero_stats.sort(key=lambda h: h["id"])
    print(f"  {len(hero_stats)} heroes")

    print("Fetching constants (abilities, items, hero_abilities, patch) ...")
    abilities = fetch("constants/abilities", "constants_abilities.json", refresh)
    items = fetch("constants/items", "constants_items.json", refresh)
    hero_abilities = fetch("constants/hero_abilities", "constants_hero_abilities.json", refresh)
    patches = fetch("constants/patch", "constants_patch.json", refresh)

    print("Fetching per-hero matchups + item popularity + duration curves ...")
    matchups: dict[int, list] = {}
    item_pop: dict[int, dict] = {}
    durations: dict[int, list] = {}
    fetched_this_run = 0
    for i, h in enumerate(hero_stats):
        hid = h["id"]
        cached = (RAW / f"matchups_{hid}.json").exists()
        try:
            matchups[hid] = fetch(f"heroes/{hid}/matchups", f"matchups_{hid}.json", refresh)
        except Exception as exc:  # keep going; a hero with no data just falls back to prior
            print(f"  ! matchup fetch failed for {h['localized_name']} ({hid}): {exc}")
            matchups[hid] = []
        if not cached:
            fetched_this_run += 1
            # OpenDota free tier allows ~60 req/min; pace new downloads.
            time.sleep(1.6)
        try:
            item_pop[hid] = fetch(
                f"heroes/{hid}/itemPopularity", f"itempop_{hid}.json", refresh
            )
        except Exception as exc:
            print(f"  ! item popularity failed for {h['localized_name']} ({hid}): {exc}")
            item_pop[hid] = {}
        try:
            durations[hid] = fetch(
                f"heroes/{hid}/durations", f"durations_{hid}.json", refresh
            )
        except Exception as exc:
            print(f"  ! durations failed for {h['localized_name']} ({hid}): {exc}")
            durations[hid] = []
        if i % 25 == 0:
            print(f"  {i}/{len(hero_stats)} ({fetched_this_run} new this run)")

    print("Deriving capability flags + talent trees from ability constants ...")
    ability_flags = parse_ability_flags(abilities, hero_abilities)
    talents = parse_talents(abilities, hero_abilities)
    ability_meta = parse_hero_ability_meta(abilities, hero_abilities)

    heroes = []
    for h in hero_stats:
        key = h["name"]
        flag = ability_flags.get(key, {})
        tags = sorted(set(TACTICAL_TAGS.get(key, [])))
        picks = sum(h.get(f"{i}_pick", 0) or 0 for i in range(1, 9))
        wins = sum(h.get(f"{i}_win", 0) or 0 for i in range(1, 9))
        pub_win = h.get("pub_win") or 0
        pub_pick = h.get("pub_pick") or 0
        heroes.append(
            {
                "id": h["id"],
                "name": key,
                "localized_name": h["localized_name"],
                "primary_attr": h["primary_attr"],
                "attack_type": h["attack_type"],
                "roles": h.get("roles", []),
                "img": h.get("img"),
                "icon": h.get("icon"),
                "base_health": h.get("base_health"),
                "base_mana": h.get("base_mana"),
                "base_armor": h.get("base_armor"),
                "base_attack_min": h.get("base_attack_min"),
                "base_attack_max": h.get("base_attack_max"),
                "base_str": h.get("base_str"),
                "base_agi": h.get("base_agi"),
                "base_int": h.get("base_int"),
                "str_gain": h.get("str_gain"),
                "agi_gain": h.get("agi_gain"),
                "int_gain": h.get("int_gain"),
                "move_speed": h.get("move_speed"),
                "attack_range": h.get("attack_range"),
                "legs": h.get("legs"),
                "pro_win": h.get("pro_win") or 0,
                "pro_pick": h.get("pro_pick") or 0,
                "pro_ban": h.get("pro_ban") or 0,
                "pub_win": pub_win,
                "pub_pick": pub_pick,
                "pub_winrate": round(pub_win / pub_pick, 4) if pub_pick else 0.5,
                "cm_pick": picks,
                "cm_win": wins,
                "cm_winrate": round(wins / picks, 4) if picks else 0.5,
                "capabilities": {
                    "magic": round(flag.get("magic", 0.0), 2),
                    "physical": round(flag.get("physical", 0.0), 2),
                    "pure": round(flag.get("pure", 0.0), 2),
                    "cc": round(flag.get("cc", 0.0), 2),
                    "bkbpierce_cc": round(flag.get("bkbpierce_cc", 0.0), 2),
                    "nuke_count": int(flag.get("nuke_count", 0)),
                    "disable_count": int(flag.get("disable_count", 0)),
                    "silence": int(flag.get("silence", 0)),
                    "stun": int(flag.get("stun", 0)),
                },
                "tags": tags,
                "talents": talents.get(key, []),
                "abilities": ability_meta.get(key, []),
            }
        )

    print("Building shrunk counter matrix ...")
    counters = build_counter_matrix(hero_stats, matchups, refresh)

    # An item is a "component" if some other item lists it in `components`.
    component_keys = set()
    parents: dict[str, list[str]] = {}
    for k, v in items.items():
        if not isinstance(v, dict):
            continue
        for c in v.get("components", []) or []:
            component_keys.add(c)
            parents.setdefault(c, []).append(k)

    item_index = {}
    for k, v in items.items():
        if not isinstance(v, dict) or "id" not in v:
            continue
        item_index[k] = {
            "id": v["id"],
            "key": k,
            "dname": v.get("dname", k),
            "cost": v.get("cost"),
            "qual": v.get("qual"),
            "img": v.get("img"),
            "components": v.get("components", []),
            "is_component": k in component_keys,
            "is_finished": bool(v.get("created")),
            "upgrades_to": [p for p in parents.get(k, []) if items.get(p, {}).get("created")],
            "notes": (v.get("notes") or "")[:200],
        }

    # Normalise raw pick counts into 0..1 popularity shares per phase.
    hero_builds = {}
    for hid, pop in item_pop.items():
        if not isinstance(pop, dict):
            continue
        phases = {}
        for phase in ("start_game_items", "early_game_items", "mid_game_items", "late_game_items"):
            raw = pop.get(phase) or {}
            total = sum(raw.values()) or 1
            phases[phase.replace("_items", "")] = {
                str(k): round(v / total, 4)
                for k, v in sorted(raw.items(), key=lambda kv: -kv[1])[:24]
            }
        hero_builds[str(hid)] = phases

    # Win rate by game length bucket -> empirically derived power-spike curve.
    hero_durations = {}
    for hid, rows in durations.items():
        if not isinstance(rows, list) or not rows:
            continue
        curve = []
        for row in sorted(rows, key=lambda r: r.get("duration_bin", 0)):
            g = row.get("games_played", 0)
            if g < 20:
                continue
            curve.append(
                {
                    "minutes": round(row["duration_bin"] / 60.0, 1),
                    "games": g,
                    "winrate": round(row["wins"] / g, 4),
                }
            )
        if curve:
            hero_durations[str(hid)] = curve

    latest_patch = None
    if isinstance(patches, list) and patches:
        latest_patch = max(patches, key=lambda p: p.get("id", 0))

    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "opendota",
        "patch": latest_patch,
        "hero_count": len(heroes),
        "heroes": heroes,
        "counters": counters,
        "hero_builds": hero_builds,
        "hero_durations": hero_durations,
        "items": item_index,
        "counter_item_rules": COUNTER_ITEM_RULES,
        "avoid_item_rules": AVOID_ITEM_RULES,
    }

    out = ARTIFACTS / "draftmaster-data.json"
    with out.open("w") as fh:
        json.dump(bundle, fh)
    size_mb = out.stat().st_size / 1e6
    print(f"Wrote {out} ({size_mb:.2f} MB)")
    print(f"Heroes: {len(heroes)} | items: {len(item_index)} | patch: {latest_patch and latest_patch.get('name')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
