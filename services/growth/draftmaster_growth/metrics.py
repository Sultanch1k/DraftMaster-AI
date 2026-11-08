"""Outcome ingestion — the other half of the self-improvement loop.

The agent can only improve if it sees what happened. Two sources, in order of
trust:

1. **The product's own analytics** (`/api/metrics`): real impressions, clicks and
   conversions for the links the content carried. Fetched with the operator's
   metrics token.
2. **The published record itself**: even with no analytics, the agent knows what
   it published and when, so it can at least attribute *volume* to variants and
   avoid repeats.

Whatever comes back is normalised into :class:`MetricSample` rows and handed to
the store, which folds them into the per-variant statistics the optimizer reads.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from .config import GrowthConfig
from .models import MetricSample
from .store import GrowthStore

log = logging.getLogger("draftmaster.growth.metrics")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MetricsClient:
    """Pulls outcome data for published items."""

    def __init__(self, settings: GrowthConfig, store: GrowthStore):
        self.settings = settings
        self.store = store

    def fetch_remote(self) -> dict | None:
        """Fetch the product's own metrics summary, if configured."""
        if not self.settings.metrics_url:
            return None
        headers = {}
        if self.settings.metrics_token:
            headers["x-metrics-token"] = self.settings.metrics_token
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(self.settings.metrics_url, headers=headers)
                if resp.status_code >= 300:
                    log.warning("metrics fetch returned %s", resp.status_code)
                    return None
                return resp.json()
        except httpx.HTTPError as exc:
            log.warning("metrics fetch failed: %s", exc)
            return None

    def attribute(self, remote: dict | None) -> list[MetricSample]:
        """Turn a remote metrics payload into per-variant samples.

        The product's analytics are aggregate, so we spread the reported
        funnel numbers across the items we published, weighted by how many items
        each variant contributed. This is honest about its own uncertainty: with
        no per-link attribution the best available signal is per-variant share
        of output, and the agent says so rather than inventing precision.
        """
        published = self.store.published_items()
        live = [p for p in published if p.get("live") or p.get("item")]
        if not live:
            return []

        # Count items per variant.
        by_variant: dict[str, int] = {}
        for row in live:
            item = row.get("item") or {}
            v = item.get("variant") or "unknown"
            by_variant[v] = by_variant.get(v, 0) + 1

        if not remote:
            # No remote signal: record a zero-signal sample per item so the
            # optimizer still sees *volume* and rotates off the least-tested.
            return [
                MetricSample(
                    item_id=row["item_id"],
                    variant=(row.get("item") or {}).get("variant", "unknown"),
                    topic=(row.get("item") or {}).get("topic", ""),
                    channel=row.get("channel", ""),
                    measured_at=_now_iso(),
                )
                for row in live
            ]

        funnel = remote.get("funnel") or {}
        clicks = int(funnel.get("analysis_run", 0)) + int(funnel.get("panic_run", 0))
        conversions = int(remote.get("paying_customers", 0))
        page_views = int(funnel.get("page_view", 0))

        total_items = sum(by_variant.values()) or 1
        samples: list[MetricSample] = []
        for variant, count in by_variant.items():
            share = count / total_items
            samples.append(
                MetricSample(
                    item_id=f"aggregate:{variant}",
                    variant=variant,
                    topic="aggregate",
                    channel="all",
                    impressions=int(page_views * share),
                    clicks=int(clicks * share),
                    conversions=int(round(conversions * share)),
                    extra={"items": count},
                    measured_at=_now_iso(),
                )
            )
        return samples

    def ingest(self, remote: dict | None = None) -> list[MetricSample]:
        """Fetch (if needed), attribute and persist samples."""
        if remote is None:
            remote = self.fetch_remote()
        samples = self.attribute(remote)
        if samples:
            self.store.record_metrics(samples)
        return samples
