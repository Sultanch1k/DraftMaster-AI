"""Report orchestrator — assembles the full 11-section draft report.

This is the single entry point used by the API, the "One Click Win Plan" and
the "I'M LAST PICK" panic flow. All heavy lifting is delegated to the focused
modules (threats, scoring, items, plan, winprob).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .dataset import Dataset, get_dataset
from .items import build_items, BuildPlan
from .plan import (
    generate_match_plan,
    generate_power_spikes,
    generate_skill_build,
    generate_talents,
    generate_target_priority,
    generate_win_conditions,
    one_sentence_plan,
)
from .scoring import score_candidates, score_one, Candidate
from .threats import analyse_threats, ThreatProfile, DIMENSION_LABELS
from .winprob import win_probability, WinProbability


@dataclass
class DraftReport:
    generated_in_ms: int
    patch: str | None
    enemy_draft: list[dict]
    role: str | None
    rank: str
    win_probability: dict
    best_picks: list[dict]
    why_this_hero: list[str]
    threat_analysis: dict
    item_build: dict
    skill_build: dict
    talents: list[dict]
    match_plan: list[dict]
    win_conditions: dict
    target_priority: list[dict]
    power_spikes: dict
    one_sentence_win_plan: str
    draft_summary: dict
    # Full report for every Top-5 candidate, keyed by hero id (as a string for
    # JSON). Lets the UI switch heroes instantly without another API call, which
    # also keeps a single analysis from consuming more than one quota unit.
    pick_reports: dict[str, dict] = field(default_factory=dict)

    def to_dict(self) -> dict:
        # Shallow copy: callers store the dict inside pick_reports, and returning
        # the live __dict__ would create a self-reference when we then assign it.
        return dict(self.__dict__)


class ReportEngine:
    def __init__(self, dataset: Dataset | None = None):
        self.ds = dataset or get_dataset()

    # -- public API ------------------------------------------------------
    def hero_list(self) -> list[dict]:
        return [
            {
                "id": h["id"],
                "name": h["name"],
                "localized_name": h["localized_name"],
                "roles": h.get("roles", []),
                "primary_attr": h.get("primary_attr"),
                "attack_type": h.get("attack_type"),
                "icon": h.get("icon"),
                "img": h.get("img"),
                "tags": h.get("tags", []),
                "pub_winrate": h.get("pub_winrate"),
            }
            for h in self.ds.heroes
        ]

    def item_list(self) -> list[dict]:
        return sorted(
            [
                {
                    "key": v["key"],
                    "id": v["id"],
                    "dname": v["dname"],
                    "cost": v.get("cost"),
                    "qual": v.get("qual"),
                    "img": v.get("img"),
                }
                for v in self.ds.items.values()
            ],
            key=lambda i: i["dname"],
        )

    def analyse(
        self,
        enemy_ids: list[int],
        hero_id: int | None = None,
        role: str | None = None,
        rank_tier: int | None = None,
        comfort: dict[int, float] | None = None,
        allies: list[int] | None = None,
        panic: bool = False,
    ) -> DraftReport:
        started = time.perf_counter()
        enemy_ids = [int(e) for e in enemy_ids]
        allies = [int(a) for a in (allies or [])]

        candidates = score_candidates(
            self.ds, enemy_ids, role=role, comfort=comfort, allies=allies, limit=5
        )
        if hero_id is None:
            hero_id = candidates[0].hero_id if candidates else (enemy_ids[0] if enemy_ids else 1)
        hero = self.ds.hero_or_raise(hero_id)

        sections = self._hero_sections(hero_id, enemy_ids, role, rank_tier, candidates, allies)
        why = self._why_this_hero(hero_id, candidates, hero, enemy_ids, allies)

        report = DraftReport(
            generated_in_ms=int((time.perf_counter() - started) * 1000),
            patch=(self.ds.patch or {}).get("name"),
            enemy_draft=[self._hero_brief(i) for i in enemy_ids],
            role=role,
            rank=sections["win_probability"]["rank_label"],
            best_picks=[c.to_dict() for c in candidates],
            why_this_hero=why,
            **{k: sections[k] for k in (
                "win_probability", "threat_analysis", "item_build", "skill_build",
                "talents", "match_plan", "win_conditions", "target_priority",
                "power_spikes", "one_sentence_win_plan", "draft_summary",
            )},
        )
        # A manual pick (screenshot detection, or a hero outside the Top 5) is the
        # only report we need; otherwise precompute every candidate so the UI can
        # switch heroes with no extra request.
        picks = [c.hero_id for c in candidates]
        if hero_id not in picks:
            report.pick_reports = {str(hero_id): report.to_dict()}
        else:
            report.pick_reports = {str(c.hero_id): self._report_for_pick(
                c.hero_id, enemy_ids, role, rank_tier, candidates, allies
            ) for c in candidates}
        return report

    def _hero_sections(
        self,
        hero_id: int,
        enemy_ids: list[int],
        role: str | None,
        rank_tier: int | None,
        candidates: list[Candidate],
        allies: list[int],
    ) -> dict:
        """Every hero-specific section of the report, for one hero.

        Extracted so the same code produces both the requested hero's report and
        the precomputed reports for the other Top-5 candidates.
        """
        hero = self.ds.hero_or_raise(hero_id)
        threats = analyse_threats(self.ds, enemy_ids, hero_id)
        build = build_items(self.ds, hero_id, threats.problems)
        targets = generate_target_priority(self.ds, hero_id, enemy_ids)
        skill = generate_skill_build(self.ds, hero, threats)
        talents = generate_talents(self.ds, hero, threats)
        timeline = generate_match_plan(self.ds, hero, threats)
        spikes = generate_power_spikes(self.ds, hero_id, enemy_ids)
        winprob = win_probability(self.ds, hero_id, enemy_ids, role, rank_tier)
        win_conditions = generate_win_conditions(self.ds, hero, threats, targets, winprob)
        sentence = one_sentence_plan(self.ds, hero, threats, build, targets, winprob)
        return {
            "win_probability": winprob.to_dict(),
            "threat_analysis": threats.to_dict(),
            "item_build": build.to_dict(),
            "skill_build": skill,
            "talents": talents,
            "match_plan": timeline,
            "win_conditions": win_conditions,
            "target_priority": targets,
            "power_spikes": spikes,
            "one_sentence_win_plan": sentence,
            "draft_summary": self._draft_summary(threats, targets, winprob, hero),
        }

    def _report_for_pick(
        self,
        hero_id: int,
        enemy_ids: list[int],
        role: str | None,
        rank_tier: int | None,
        candidates: list[Candidate],
        allies: list[int],
    ) -> dict:
        """A full 11-section report for one candidate hero (no pick_reports)."""
        hero = self.ds.hero_or_raise(hero_id)
        sections = self._hero_sections(hero_id, enemy_ids, role, rank_tier, candidates, allies)
        why = next(
            (c.reasons for c in candidates if c.hero_id == hero_id),
            score_one(self.ds, hero, enemy_ids, None, None, allies).reasons,
        )
        report = DraftReport(
            generated_in_ms=0,
            patch=(self.ds.patch or {}).get("name"),
            enemy_draft=[self._hero_brief(i) for i in enemy_ids],
            role=role,
            rank=sections["win_probability"]["rank_label"],
            best_picks=[c.to_dict() for c in candidates],
            why_this_hero=why,
            **{k: sections[k] for k in (
                "win_probability", "threat_analysis", "item_build", "skill_build",
                "talents", "match_plan", "win_conditions", "target_priority",
                "power_spikes", "one_sentence_win_plan", "draft_summary",
            )},
        )
        return report.to_dict()

    # -- helpers ---------------------------------------------------------
    def _why_this_hero(
        self,
        hero_id: int,
        candidates: list[Candidate],
        hero: dict,
        enemy_ids: list[int],
        allies: list[int],
    ) -> list[str]:
        """Explanations for the hero the user actually asked about.

        The Top 5 list only holds five scored candidates, so when the requested
        hero falls outside it (a manual pick, a screenshot detection, or a hero
        outside the top five) the reasons are recomputed for that exact hero
        rather than silently describing the #1 recommendation.
        """
        match = next((c for c in candidates if c.hero_id == hero_id), None)
        if match is not None:
            return match.reasons
        return score_one(self.ds, hero, enemy_ids, None, None, allies).reasons

    def _hero_brief(self, hid: int) -> dict:
        h = self.ds.hero(hid)
        if not h:
            return {"id": hid, "localized_name": str(hid)}
        return {
            "id": hid,
            "localized_name": h["localized_name"],
            "icon": h.get("icon"),
            "roles": h.get("roles", []),
            "tags": h.get("tags", []),
            "capabilities": h.get("capabilities", {}),
        }

    def _draft_summary(self, threats: ThreatProfile, targets: list[dict], winprob, hero: dict) -> dict:
        return {
            "headline_threats": [
                {"dimension": DIMENSION_LABELS[k], "score": v, "danger": threats.danger[k]}
                for k, v in sorted(threats.scores.items(), key=lambda kv: -kv[1])[:5]
            ],
            "top_target": targets[0]["name"] if targets else None,
            "win_probability": winprob.player_win_probability,
            "hero": hero["localized_name"],
            "verdict": winprob.verdict,
        }

    def panic(self, enemy_ids: list[int], role: str | None = None, rank_tier: int | None = None,
              comfort: dict[int, float] | None = None) -> dict:
        """The 'I'M LAST PICK' flow: one hero, one build, one plan, one sentence."""
        report = self.analyse(enemy_ids, role=role, rank_tier=rank_tier, comfort=comfort, panic=True)
        best = report.best_picks[0] if report.best_picks else None
        return {
            "best_hero": best,
            "backups": report.best_picks[1:4],
            "win_probability": report.win_probability,
            "full_build": report.item_build,
            "danger_heroes": report.target_priority,
            "power_spikes": report.power_spikes,
            "kill_priority": report.target_priority,
            "win_conditions": report.win_conditions,
            "items_to_avoid": report.item_build["avoid"],
            "one_sentence_win_plan": report.one_sentence_win_plan,
            "why_this_hero": report.why_this_hero,
            "threat_analysis": report.threat_analysis,
            "generated_in_ms": report.generated_in_ms,
        }
