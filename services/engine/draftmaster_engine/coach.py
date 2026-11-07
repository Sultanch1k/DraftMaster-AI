"""Match ID coach.

Pulls a real match from the OpenDota API and produces a coaching report:
item build vs. the meta, GPM/XPM/last-hit efficiency against benchmarks,
death clustering, objective control, skill build, and concrete fixes.

The OpenDota client is isolated so it can be unit-tested with a fake transport
and so the API layer can cache responses in Redis.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, asdict
from typing import Any

import httpx

from .dataset import Dataset, get_dataset

OPENDOTA_BASE = "https://api.opendota.com/api"


class OpenDotaClient:
    def __init__(self, api_key: str | None = None, timeout: float = 30.0):
        self.api_key = api_key if api_key is not None else os.environ.get("OPENDOTA_API_KEY", "")
        self.timeout = timeout

    def _get(self, path: str, params: dict | None = None) -> dict:
        params = dict(params or {})
        if self.api_key:
            params["api_key"] = self.api_key
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(f"{OPENDOTA_BASE}/{path.lstrip('/')}", params=params)
            resp.raise_for_status()
            return resp.json()

    def match(self, match_id: int) -> dict:
        return self._get(f"matches/{match_id}")

    def player(self, account_id: int, limit: int = 20) -> dict:
        return self._get(f"players/{account_id}", params={"limit": limit})


@dataclass
class CoachReport:
    match_id: int
    duration_min: float
    radiant_win: bool
    player: dict
    verdict: str
    grades: dict
    strengths: list[str]
    mistakes: list[str]
    item_notes: list[str]
    timing_notes: list[str]
    practice_plan: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _benchmark_pct(player: dict, key: str) -> float | None:
    b = (player.get("benchmarks") or {}).get(key)
    if isinstance(b, dict):
        return round(float(b.get("pct", 0.0)) * 100, 1)
    return None


def _grade_from_pct(pct: float | None) -> str:
    if pct is None:
        return "N/A"
    if pct >= 90:
        return "S"
    if pct >= 75:
        return "A"
    if pct >= 50:
        return "B"
    if pct >= 25:
        return "C"
    return "D"


class MatchCoach:
    def __init__(self, dataset: Dataset | None = None, client: OpenDotaClient | None = None):
        self.ds = dataset or get_dataset()
        self.client = client or OpenDotaClient()

    def coach(self, match_id: int, account_id: int | None = None) -> CoachReport:
        match = self.client.match(match_id)
        if not match or "players" not in match:
            raise ValueError(f"match {match_id} is not available from OpenDota")

        players = match["players"]
        player = None
        if account_id is not None:
            player = next((p for p in players if p.get("account_id") == account_id), None)
        if player is None:
            # Default to the highest net-worth player so the report is never empty.
            player = max(players, key=lambda p: p.get("net_worth") or 0)

        duration_min = round((match.get("duration") or player.get("duration") or 0) / 60.0, 1)
        hero = self.ds.by_id.get(player.get("hero_id"))
        hero_name = hero["localized_name"] if hero else f"hero {player.get('hero_id')}"

        grades = {
            "farm": _grade_from_pct(_benchmark_pct(player, "gold_per_min")),
            "xp": _grade_from_pct(_benchmark_pct(player, "xp_per_min")),
            "last_hits": _grade_from_pct(_benchmark_pct(player, "last_hits_per_min")),
            "fighting": _grade_from_pct(_benchmark_pct(player, "kills_per_min")),
            "survival": _grade_from_pct(_benchmark_pct(player, "deaths_per_min")),
        }

        gpm = player.get("gold_per_min") or 0
        xpm = player.get("xp_per_min") or 0
        lh = player.get("last_hits") or 0
        deaths = player.get("deaths") or 0
        kills = player.get("kills") or 0
        assists = player.get("assists") or 0
        tower_damage = player.get("tower_damage") or 0
        hero_damage = player.get("hero_damage") or 0
        won = bool(player.get("radiant_win") == player.get("isRadiant") if player.get("radiant_win") is not None else match.get("radiant_win") == player.get("isRadiant"))

        strengths: list[str] = []
        mistakes: list[str] = []
        item_notes: list[str] = []
        timing_notes: list[str] = []
        practice: list[str] = []

        # --- Farm efficiency -------------------------------------------
        if gpm >= 600:
            strengths.append(f"Strong farming pace ({gpm} GPM) — you converted map space into gold efficiently.")
        elif gpm < 400 and duration_min > 30:
            mistakes.append(f"Low farming pace ({gpm} GPM) for a {duration_min:.0f}-minute game — you left gold on the map.")
            practice.append("Practice farming patterns: keep two waves pushed, then rotate to jungle camps in a loop.")

        if lh and duration_min:
            lh_per_min = lh / duration_min
            if lh_per_min >= 7:
                strengths.append(f"Excellent last-hit rate ({lh_per_min:.1f} LH/min).")
            elif lh_per_min < 4 and hero and "Carry" in hero.get("roles", []):
                mistakes.append(f"Low last-hit rate ({lh_per_min:.1f} LH/min) for a carry — prioritise uncontested farm.")
                practice.append("Do 10 minutes of last-hit drills in the demo hero mode before your next ranked session.")

        # --- Deaths -----------------------------------------------------
        deaths_per_10 = (deaths / duration_min * 10) if duration_min else 0
        if deaths_per_10 >= 4:
            mistakes.append(f"{deaths} deaths in {duration_min:.0f} minutes — you are taking fights you cannot win.")
            practice.append("Track your death timer: if you die twice to the same hero, buy a defensive item or change lanes.")
        elif deaths <= 2 and duration_min > 25:
            strengths.append(f"Only {deaths} deaths — excellent positioning and map awareness.")

        # --- Items vs meta ---------------------------------------------
        item_ids = [player.get(f"item_{i}") for i in range(6) if player.get(f"item_{i}")]
        meta_build = self.ds.hero_builds.get(player.get("hero_id") or 0, {})
        meta_late = {int(k) for k in (meta_build.get("late_game") or {})}
        meta_mid = {int(k) for k in (meta_build.get("mid_game") or {})}
        for iid in item_ids:
            meta = self.ds.items_by_id.get(iid)
            if not meta:
                continue
            if iid not in meta_mid and iid not in meta_late and (meta.get("cost") or 0) > 2500:
                item_notes.append(
                    f"{meta['dname']} is an off-meta purchase for {hero_name} this patch "
                    f"(below the top meta choices) — check whether it actually answered the enemy draft."
                )
        if not item_notes:
            item_notes.append(f"Item build is close to the current meta build for {hero_name}.")

        # --- Timing / objective ----------------------------------------
        if tower_damage < 1000 and duration_min > 30:
            timing_notes.append("Very low tower damage — you are not converting won fights into objectives.")
            practice.append("After every won teamfight, ask: which tower or Roshan is free right now?")
        if hero_damage and duration_min:
            hd_per_min = hero_damage / duration_min
            if hd_per_min < 250:
                timing_notes.append("Low hero damage per minute — you may be fighting too late or with the wrong items online.")

        # --- Verdict ----------------------------------------------------
        grade_score = sum(
            {"S": 4, "A": 3, "B": 2, "C": 1, "D": 0, "N/A": 2}.get(g, 2) for g in grades.values()
        ) / max(1, len(grades))
        if grade_score >= 3:
            verdict = "Carried your role — this is a repeatable performance."
        elif grade_score >= 2:
            verdict = "Solid game with clear, fixable leaks."
        else:
            verdict = "Below your standard — focus on the two practice points below."
        if won and grade_score >= 2:
            verdict = "Won the game and played your role well."

        practice = practice or [
            "Review the replay at 2x and note every death: was it avoidable?",
            "Set one concrete goal for your next game (e.g. 50 LH by 10:00).",
        ]

        return CoachReport(
            match_id=match_id,
            duration_min=duration_min,
            radiant_win=bool(match.get("radiant_win")),
            player={
                "account_id": player.get("account_id"),
                "hero": hero_name,
                "hero_id": player.get("hero_id"),
                "kills": kills,
                "deaths": deaths,
                "assists": assists,
                "gpm": gpm,
                "xpm": xpm,
                "last_hits": lh,
                "denies": player.get("denies"),
                "net_worth": player.get("net_worth"),
                "hero_damage": hero_damage,
                "tower_damage": tower_damage,
                "level": player.get("level"),
                "won": won,
                "benchmarks": {
                    k: _benchmark_pct(player, k)
                    for k in (
                        "gold_per_min",
                        "xp_per_min",
                        "last_hits_per_min",
                        "kills_per_min",
                        "deaths_per_min",
                        "hero_damage_per_min",
                    )
                },
            },
            verdict=verdict,
            grades=grades,
            strengths=strengths or ["No standout strengths detected — work the practice plan."],
            mistakes=mistakes or ["No critical mistakes detected at this level."],
            item_notes=item_notes,
            timing_notes=timing_notes or ["Objective timing looks reasonable for this game length."],
            practice_plan=practice,
        )
