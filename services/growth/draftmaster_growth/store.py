"""Persistent state for the growth engine.

A single JSON file, written atomically (temp file + ``os.replace``) so a crash
mid-write never corrupts state, and guarded by a re-entrant lock so the CLI and
a scheduled run cannot interleave. This deliberately avoids a database: the
growth engine must run from a fresh clone, from CI, and from a GitHub Action
with no infrastructure, and the state is small enough that a diffable JSON file
is more useful than a schema.

Every mutation is explicit and recorded, so the whole history is auditable.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .models import MetricSample, Prospect, PublishResult

SCHEMA_VERSION = 1


def _empty_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": None,
        "runs": [],
        "published": [],
        "metrics": [],
        "prospects": {},
        "variant_stats": {},
        "counters": {},
        "history": [],
    }


class GrowthStore:
    """Thread-safe, atomic, file-backed state store."""

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._state: dict[str, Any] = _empty_state()
        self._load()

    # -- persistence -----------------------------------------------------
    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            with self.path.open() as fh:
                data = json.load(fh)
            if isinstance(data, dict) and data.get("schema_version") == SCHEMA_VERSION:
                self._state = data
            # An unknown/newer schema is ignored rather than migrated blindly;
            # the caller keeps a working empty state instead of crashing.
        except (json.JSONDecodeError, OSError):
            # A corrupt file must not take the agent down: start clean and keep
            # the bad file aside so it can be inspected.
            try:
                self.path.replace(self.path.with_suffix(".corrupt.json"))
            except OSError:
                pass

    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as fh:
                    json.dump(self._state, fh, ensure_ascii=False, indent=1, sort_keys=True)
                os.replace(tmp, self.path)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)

    # -- raw access ------------------------------------------------------
    @property
    def state(self) -> dict[str, Any]:
        return self._state

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    # -- runs ------------------------------------------------------------
    def record_run(self, run: dict) -> None:
        with self._lock:
            self._state["runs"].append(run)
            if self._state["created_at"] is None:
                self._state["created_at"] = run.get("started_at")

    def run_count(self) -> int:
        return len(self._state["runs"])

    # -- publishing ------------------------------------------------------
    def record_publish(self, result: PublishResult, item: dict) -> None:
        with self._lock:
            row = result.to_dict()
            row["item"] = item
            self._state["published"].append(row)

    def published_items(self) -> list[dict]:
        return self._state["published"]

    def published_ids(self) -> set[str]:
        return {row["item_id"] for row in self._state["published"]}

    def count_published_today(self, day: str, channel: str | None = None) -> int:
        n = 0
        for row in self._state["published"]:
            if not row.get("live"):
                continue
            item = row.get("item") or {}
            if not item.get("created_at", "").startswith(day):
                continue
            if channel and row.get("channel") != channel:
                continue
            n += 1
        return n

    # -- metrics + optimizer --------------------------------------------
    def record_metrics(self, samples: list[MetricSample]) -> None:
        with self._lock:
            for s in samples:
                self._state["metrics"].append(s.to_dict())
                stats = self._state["variant_stats"].setdefault(
                    s.variant,
                    {"impressions": 0, "clicks": 0, "conversions": 0, "n": 0, "score": 0.0},
                )
                stats["impressions"] += s.impressions
                stats["clicks"] += s.clicks
                stats["conversions"] += s.conversions
                stats["n"] += 1
                stats["score"] += s.score

    def metric_samples(self) -> list[dict]:
        return self._state["metrics"]

    def variant_stats(self) -> dict[str, dict]:
        return self._state["variant_stats"]

    # -- prospects -------------------------------------------------------
    def upsert_prospect(self, prospect: Prospect) -> None:
        with self._lock:
            self._state["prospects"][prospect.key] = prospect.to_dict()

    def get_prospect(self, key: str) -> dict | None:
        return self._state["prospects"].get(key)

    def prospects(self) -> list[dict]:
        return list(self._state["prospects"].values())

    def set_prospect_status(self, key: str, status: str, note: str = "") -> None:
        with self._lock:
            p = self._state["prospects"].setdefault(
                key, Prospect(key=key, name=key, platform="unknown").to_dict()
            )
            p["status"] = status
            if note:
                p["notes"] = (p.get("notes") or "") + ("\n" if p.get("notes") else "") + note

    # -- generic counters (for dedupe/idempotency) -----------------------
    def bump_counter(self, key: str, by: int = 1) -> int:
        with self._lock:
            self._state["counters"][key] = self._state["counters"].get(key, 0) + by
            return self._state["counters"][key]

    def counter(self, key: str) -> int:
        return self._state["counters"].get(key, 0)

    # -- append-only narrative history ----------------------------------
    def log(self, entry: dict) -> None:
        with self._lock:
            self._state["history"].append(entry)

    def history(self) -> list[dict]:
        return self._state["history"]


def prospect_from_dict(d: dict) -> Prospect:
    return Prospect(**{k: v for k, v in d.items() if k in Prospect.__dataclass_fields__})


def as_public_dict(obj: Any) -> dict:
    return asdict(obj) if hasattr(obj, "__dataclass_fields__") else dict(obj)
