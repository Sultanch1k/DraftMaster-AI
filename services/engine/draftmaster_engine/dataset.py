"""In-memory dataset + query helpers over the OpenDota-derived artifact."""
from __future__ import annotations

import json
import math
import os
import threading
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

DEFAULT_ARTIFACT = (
    Path(__file__).resolve().parents[3] / "data" / "artifacts" / "draftmaster-data.json"
)

# Roles the engine reasons about, mapped to the raw OpenDota role strings.
ROLE_MAP = {
    "carry": ["Carry"],
    "mid": ["Nuker", "Escape"],
    "offlane": ["Initiator", "Durable", "Disabler"],
    "support": ["Support", "Disabler"],
    "hard_support": ["Support", "Escape"],
    "roamer": ["Initiator", "Support"],
}

# Attribute/attack-type archetypes used for lane and item reasoning.
MELEE = "Melee"


class Dataset:
    """Read-only, thread-safe view of the compiled strategy artifact."""

    def __init__(self, payload: dict[str, Any]):
        self.payload = payload
        self.generated_at = payload.get("generated_at")
        self.patch = payload.get("patch") or {}
        self.heroes: list[dict] = payload["heroes"]
        self.by_id: dict[int, dict] = {h["id"]: h for h in self.heroes}
        self.by_name: dict[str, dict] = {h["name"]: h for h in self.heroes}
        self.by_loc: dict[str, dict] = {
            h["localized_name"].lower(): h for h in self.heroes
        }
        self.items: dict[str, dict] = payload.get("items", {})
        self.items_by_id: dict[int, dict] = {
            v["id"]: v for v in self.items.values() if "id" in v
        }
        raw_matrix = payload.get("counters", {}).get("matrix", {})
        self.counter: dict[int, dict[int, float]] = {
            int(a): {int(b): float(v) for b, v in row.items()}
            for a, row in raw_matrix.items()
        }
        self.global_prior: dict[int, float] = {
            int(k): float(v)
            for k, v in payload.get("counters", {}).get("global_prior_logit", {}).items()
        }
        self.hero_builds: dict[int, dict] = {
            int(k): v for k, v in payload.get("hero_builds", {}).items()
        }
        self.hero_durations: dict[int, list] = {
            int(k): v for k, v in payload.get("hero_durations", {}).items()
        }
        self.counter_item_rules: list[dict] = payload.get("counter_item_rules", [])
        self.avoid_item_rules: list[dict] = payload.get("avoid_item_rules", [])

    # -- lookups ---------------------------------------------------------
    def hero(self, key: int | str) -> dict | None:
        if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
            return self.by_id.get(int(key))
        k = key.lower()
        return self.by_name.get(k) or self.by_loc.get(k)

    def hero_or_raise(self, key: int | str) -> dict:
        h = self.hero(key)
        if h is None:
            raise KeyError(f"unknown hero: {key}")
        return h

    def item(self, key: str | int) -> dict | None:
        if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
            return self.items_by_id.get(int(key))
        return self.items.get(key)

    # -- counter math ----------------------------------------------------
    def counter_logit(self, a: int, b: int) -> float:
        """Positive => hero A is favoured against hero B."""
        return self.counter.get(a, {}).get(b, 0.0)

    def counter_score(self, a: int, b: int) -> float:
        """Map the logit advantage to a 0..100 'counter score' for hero A vs B."""
        return _logit_to_score(self.counter_logit(a, b))

    def matchup_advantage(self, hero_id: int, enemies: Iterable[int]) -> float:
        """Aggregate shrunk counter advantage of `hero_id` vs an enemy draft.

        Uses a soft-max-ish mean: the average advantage plus the worst single
        matchup, so a hero that is hard-countered by one enemy is penalised even
        if it beats the rest.
        """
        vals = [self.counter_logit(hero_id, e) for e in enemies]
        if not vals:
            return 0.0
        mean = sum(vals) / len(vals)
        worst = min(vals)
        return 0.75 * mean + 0.25 * worst

    def hero_winrate(self, hero_id: int) -> float:
        h = self.by_id.get(hero_id)
        if not h:
            return 0.5
        cm = h.get("cm_winrate") or 0.5
        pub = h.get("pub_winrate") or 0.5
        # Blend pro/CM signal with pub signal; CM is more skill-neutral.
        return 0.6 * cm + 0.4 * pub

    def duration_winrate(self, hero_id: int, minutes: float) -> float | None:
        curve = self.hero_durations.get(hero_id)
        if not curve:
            return None
        best = min(curve, key=lambda p: abs(p["minutes"] - minutes))
        return best["winrate"]

    def late_game_delta(self, hero_id: int) -> float:
        """Winrate delta between late game (>=45m) and early game (~25m)."""
        curve = self.hero_durations.get(hero_id)
        if not curve:
            return 0.0
        early = [p for p in curve if p["minutes"] <= 1800]
        late = [p for p in curve if p["minutes"] >= 2700]
        if not early or not late:
            return 0.0
        e = sum(p["winrate"] * p["games"] for p in early) / sum(p["games"] for p in early)
        l = sum(p["winrate"] * p["games"] for p in late) / sum(p["games"] for p in late)
        return round(l - e, 4)

    def role_affinity(self, hero_id: int, role: str) -> float:
        """0..1 score for how naturally a hero fills a role."""
        h = self.by_id.get(hero_id)
        if not h or role not in ROLE_MAP:
            return 0.5
        roles = set(h.get("roles", []))
        wanted = set(ROLE_MAP[role])
        if not wanted:
            return 0.5
        overlap = len(roles & wanted)
        return min(1.0, 0.35 + 0.35 * overlap)

    def popularity(self, hero_id: int) -> float:
        h = self.by_id.get(hero_id)
        if not h:
            return 0.0
        return float(h.get("pub_pick") or 0)


def _logit_to_score(logit: float, scale: float = 0.18) -> float:
    """Map a logit advantage to a 0..100 score with 50 = even."""
    return round(100.0 / (1.0 + math.exp(-logit / scale)), 2)


_lock = threading.Lock()
_cache: dict[str, Dataset] = {}


def get_dataset(path: str | os.PathLike | None = None) -> Dataset:
    p = Path(path) if path else DEFAULT_ARTIFACT
    key = str(p)
    with _lock:
        if key not in _cache:
            with open(p) as fh:
                _cache[key] = Dataset(json.load(fh))
        return _cache[key]
