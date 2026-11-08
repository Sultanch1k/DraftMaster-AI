"""First-party funnel analytics.

Why not GA/PostHog: those add a script, a cookie banner problem and an external
dependency, and they are blocked by a meaningful share of this audience (ad
blockers are near-universal among Dota players). A tiny first-party endpoint
records the handful of events that matter for the revenue funnel, stores them in
our own database, and costs nothing. If richer analytics is ever needed the
event stream is already there to forward.

Privacy: no cookies, no cross-site tracking, no PII. `user_id` is a random
localStorage id; `props` is a small dict of counts/ids. The `/api/metrics`
summary is gated behind a shared token so the numbers are not public.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Header, HTTPException, Request

from ..schemas import EventBatch, SubscribeRequest

log = logging.getLogger("draftmaster.events")
router = APIRouter(tags=["analytics"])

# The funnel we care about, in order. Anything else is stored but not ranked.
FUNNEL = [
    "page_view",
    "draft_started",
    "analysis_run",
    "panic_run",
    "report_opened",
    "paywall_hit",
    "upgrade_clicked",
    "checkout_opened",
    "license_activated",
    "share_clicked",
    "email_captured",
]


@router.post("/events")
def ingest(payload: EventBatch, request: Request) -> dict:
    """Record a batch of client events. Never fails the user's flow."""
    rows = [
        {
            "event_id": uuid.uuid4().hex,
            "name": e.name[:64],
            "user_id": (e.user_id or "")[:64] or None,
            "props": e.props,
        }
        for e in payload.events
    ]
    try:
        request.app.state.store.record_events(rows)
    except Exception as exc:  # analytics must never break the product
        log.warning("event ingest failed: %s", exc)
    return {"ok": True, "recorded": len(rows)}


@router.get("/metrics")
def metrics(request: Request, x_metrics_token: str = Header(default="")) -> dict:
    """Private growth dashboard: funnel counts + paying customers.

    Gated by DRAFTMASTER_SECRET_KEY so the operator can read it with
    `curl -H 'x-metrics-token: <secret>' .../api/metrics` without exposing
    business numbers to the public.
    """
    secret = request.app.state.settings.secret_key
    if not secret or x_metrics_token != secret:
        raise HTTPException(status_code=404, detail="not found")

    store = request.app.state.store
    counts = store.event_counts()
    ordered = {name: counts.get(name, 0) for name in FUNNEL}
    extra = {k: v for k, v in counts.items() if k not in FUNNEL}
    return {
        "funnel": ordered,
        "other_events": extra,
        "paying_customers": store.paid_count(),
        "subscribers": store.subscriber_count(),
        "store_backend": store.backend,
        "cache_backend": request.app.state.cache.backend,
    }


@router.post("/subscribe")
def subscribe(payload: SubscribeRequest, request: Request) -> dict:
    """Capture an email with explicit consent.

    Used at the paywall and in the footer: a visitor who is not ready to pay is
    still a lead we can follow up with when a patch drops or a feature lands.
    Consent is stored alongside the address so every send has a lawful basis.
    """
    email = payload.email.strip().lower()
    # Minimal, dependency-free validation — enough to reject obvious junk.
    if "@" not in email or "." not in email.split("@")[-1] or len(email) < 6 or len(email) > 254:
        raise HTTPException(status_code=422, detail="Please enter a valid email address.")
    request.app.state.store.add_subscriber(
        email, user_id=payload.user_id or "", source=payload.source or "web", consent=True
    )
    try:
        request.app.state.store.record_events(
            [{"event_id": uuid.uuid4().hex, "name": "email_captured", "user_id": payload.user_id, "props": {"source": payload.source or "web"}}]
        )
    except Exception:
        pass
    return {"ok": True}
