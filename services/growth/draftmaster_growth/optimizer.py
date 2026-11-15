"""The self-improvement loop.

A deterministic multi-armed bandit over content *variants*. It is deliberately
not random: exploration is a rotating schedule keyed on the number of samples
seen so far, so two runs over the same state pick the same variant and a dry run
is reproducible. That matters because the whole point of this engine is that a
human can review its decisions.

Selection rule:

* If a variant has fewer than ``min_samples`` observations it is *unproven* and
  gets priority (we cannot judge what we have not tested).
* Otherwise, with probability equal to the exploration rate (implemented as a
  deterministic every-``k``-th-observation rotation) we take the least-sampled
  proven variant; the rest of the time we take the best mean score.
* Ties break on the variant name so the result is stable.
"""
from __future__ import annotations

from dataclasses import dataclass

from .content import DEFAULT_VARIANT, VARIANTS


@dataclass
class VariantStat:
    key: str
    n: int
    impressions: int
    clicks: int
    conversions: int
    score: float

    @property
    def mean(self) -> float:
        return self.score / self.n if self.n else 0.0


class Optimizer:
    """Chooses variants and summarises what the data says."""

    def __init__(self, store, *, exploration_rate: float = 0.2, min_samples: int = 5):
        self.store = store
        self.exploration_rate = max(0.0, min(1.0, exploration_rate))
        self.min_samples = min_samples

    def stats(self) -> dict[str, VariantStat]:
        raw = self.store.variant_stats()
        out: dict[str, VariantStat] = {}
        for key, s in raw.items():
            out[key] = VariantStat(
                key=key,
                n=s.get("n", 0),
                impressions=s.get("impressions", 0),
                clicks=s.get("clicks", 0),
                conversions=s.get("conversions", 0),
                score=s.get("score", 0.0),
            )
        return out

    def _unproven(self, stats: dict[str, VariantStat]) -> list[str]:
        return [k for k in VARIANTS if stats.get(k, VariantStat(k, 0, 0, 0, 0, 0.0)).n < self.min_samples]

    def choose(self, *, observation_index: int | None = None) -> str:
        """Pick the next variant to publish under.

        ``observation_index`` defaults to the total number of metrics samples
        recorded so far; passing it explicitly keeps tests deterministic.
        """
        stats = self.stats()
        if observation_index is None:
            observation_index = sum(s.n for s in stats.values())

        # 1. Prove anything untested first — exploration with a purpose.
        unproven = sorted(self._unproven(stats))
        if unproven:
            # Rotate through the untested set so each gets a fair first look.
            return unproven[observation_index % len(unproven)]

        # 2. Deterministic exploration: every Nth pick, take the least-sampled
        #    proven variant (keeps the second-best alive rather than starving it).
        proven = sorted(k for k in VARIANTS if stats.get(k))
        if proven and self.exploration_rate > 0:
            period = max(2, int(round(1.0 / self.exploration_rate)))
            if observation_index % period == 0:
                return min(proven, key=lambda k: (stats[k].n, k))

        # 3. Exploit: the best mean score, ties broken on name.
        if proven:
            return max(proven, key=lambda k: (stats[k].mean, k))
        return DEFAULT_VARIANT

    def ranking(self) -> list[dict]:
        """Human-readable ranking of variants by mean score."""
        stats = self.stats()
        rows = []
        for k in sorted(VARIANTS):
            s = stats.get(k, VariantStat(k, 0, 0, 0, 0, 0.0))
            rows.append(
                {
                    "variant": k,
                    "samples": s.n,
                    "impressions": s.impressions,
                    "clicks": s.clicks,
                    "conversions": s.conversions,
                    "mean_score": round(s.mean, 3),
                    "ctr": round((s.clicks / s.impressions), 4) if s.impressions else 0.0,
                    "cvr": round((s.conversions / s.clicks), 4) if s.clicks else 0.0,
                    "description": VARIANTS[k]["description"],
                }
            )
        rows.sort(key=lambda r: (-r["mean_score"], r["variant"]))
        return rows

    def recommendation(self) -> str:
        """A one-line, human-readable statement of what the data currently says."""
        rows = self.ranking()
        if not rows or rows[0]["samples"] == 0:
            return "No outcome data yet — publishing across all variants to gather signal."
        best = rows[0]
        return (
            f"Best variant is '{best['variant']}' (mean score {best['mean_score']}, "
            f"CTR {best['ctr']:.1%}, n={best['samples']}). Weight future output toward it."
        )
