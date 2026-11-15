"""Topic selection.

The agent must never publish the same thing twice, and it must not need a human
to tell it what is worth talking about today. Topics are therefore derived from
the data itself — the counter matrix, the meta winrates, the duration curves —
and rotated deterministically by run index so the calendar is reproducible and
never repeats inside a cycle.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Topic:
    """A content subject with the data it needs already resolved."""

    key: str
    kind: str
    locale: str
    # Free-form payload the renderers read; keeps the topic data-driven.
    data: dict[str, Any] = field(default_factory=dict)

    def signature(self) -> str:
        """Stable identity used for dedupe across runs."""
        parts = [self.key, self.kind, self.locale]
        for k in sorted(self.data):
            v = self.data[k]
            if isinstance(v, (list, tuple)):
                parts.append(f"{k}=" + ",".join(str(x) for x in v))
            else:
                parts.append(f"{k}={v}")
        return "|".join(parts)


def _strongest_counter_pair(ds) -> tuple[dict, dict]:
    """The single most lopsided matchup in the matrix, for a spotlight post."""
    best = None
    for a, row in ds.counter.items():
        for b, val in row.items():
            if a == b or a not in ds.by_id or b not in ds.by_id:
                continue
            if best is None or val > best[0]:
                best = (val, a, b)
    if best is None:  # pragma: no cover - an empty matrix is impossible in practice
        h = ds.heroes[0]
        return h, ds.heroes[1]
    return ds.by_id[best[1]], ds.by_id[best[2]]


def build_topic_pool(ds, locale: str = "en") -> list[Topic]:
    """All candidate topics for a locale, in a stable order.

    The order is deterministic (sorted where a sort is meaningful) so the
    rotation is reproducible.
    """
    topics: list[Topic] = []

    # 1. Meta movers — patch winners and losers. Recurs on every patch.
    winners = sorted(ds.heroes, key=lambda h: -(h.get("cm_winrate") or 0))[:5]
    losers = sorted(ds.heroes, key=lambda h: (h.get("cm_winrate") or 1))[:5]
    topics.append(Topic("meta.winners", "meta", locale, {"heroes": [h["id"] for h in winners]}))
    topics.append(Topic("meta.losers", "meta", locale, {"heroes": [h["id"] for h in losers]}))

    # 2. Most-picked heroes — the "what is everyone playing" angle.
    trending = sorted(ds.heroes, key=lambda h: -(h.get("pub_pick") or 0))[:5]
    topics.append(Topic("meta.trending", "meta", locale, {"heroes": [h["id"] for h in trending]}))

    # 3. Matchup spotlights — one per hero, rotated so coverage grows over time.
    for h in ds.heroes:
        row = ds.counter.get(h["id"], {})
        if not row:
            continue
        worst = min(row.items(), key=lambda kv: kv[1])  # the hero's worst matchup
        if worst[0] not in ds.by_id:
            continue
        topics.append(
            Topic(f"matchup.{h['id']}", "matchup", locale, {"hero": h["id"], "enemy": worst[0]})
        )

    # 4. Hero guides — lane + build, one per hero.
    for h in ds.heroes:
        topics.append(Topic(f"guide.{h['id']}", "guide", locale, {"hero": h["id"]}))

    # 5. Panic-mode demo — the flagship, using a real draft.
    a, b = _strongest_counter_pair(ds)
    topics.append(Topic("panic.demo", "panic", locale, {"hero": a["id"], "enemy": b["id"]}))

    return topics


def select_topics(
    pool: list[Topic],
    *,
    seen: set[str],
    limit: int,
    offset: int = 0,
) -> list[Topic]:
    """Pick ``limit`` unseen topics starting at a deterministic offset.

    Skips anything already published (by signature) so the agent never repeats
    itself, and rotates the *starting point* by ``offset`` so each run surfaces
    different subjects instead of always re-walking the same head of the list.
    """
    if not pool or limit <= 0:
        return []
    n = len(pool)
    out: list[Topic] = []
    # Walk the ring from a rotated start so a caller can ask for a fresh slice.
    start = offset % n
    for i in range(n):
        topic = pool[(start + i) % n]
        sig = topic.signature()
        if sig in seen:
            continue
        out.append(topic)
        if len(out) >= limit:
            break
    return out
