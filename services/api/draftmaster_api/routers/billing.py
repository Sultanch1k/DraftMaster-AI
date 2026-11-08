"""Billing endpoints: public pricing config, license activation, session status.

The flow a buyer experiences:

1. Click "Upgrade" → the store opens the Lemon Squeezy checkout URL
   (`GET /api/billing/config` supplies it, so the link lives in config, not code).
2. After paying, Lemon Squeezy emails a license key.
3. The user pastes the key into the app → `POST /api/billing/activate` validates
   it with the provider and returns a signed session token.
4. The browser stores the token and sends it as `Authorization: Bearer <token>`.
   Every paid endpoint re-verifies it server-side.

No account, no password, no OAuth — the smallest possible path from "wants it"
to "has it".
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request

from ..billing import BillingError, is_configured, sign_session, validate_license
from ..locale import localize, resolve_locale
from ..schemas import ActivateRequest, BillingConfigOut, SessionOut

log = logging.getLogger("draftmaster.billing")
router = APIRouter(tags=["billing"])


@router.get("/billing/config", response_model=BillingConfigOut)
def billing_config(request: Request) -> dict:
    """Public billing configuration for the UI.

    Exposes only what the browser needs to render the upgrade panel. When
    `enabled` is false the UI hides purchase affordances instead of showing a
    dead button, which keeps the free experience honest.
    """
    s = request.app.state.settings
    return {
        "enabled": is_configured(s),
        "checkout_url": s.lemonsqueezy_checkout_url,
        "support_email": s.support_email,
        "free_daily_analyses": s.free_daily_analyses,
        "currency": "USD",
        "price_monthly": "$6.99",
        "price_annual": "$49",
    }


@router.post("/billing/activate", response_model=SessionOut)
async def activate(payload: ActivateRequest, request: Request) -> dict:
    """Validate a purchase license key and mint a premium session token."""
    settings = request.app.state.settings
    try:
        info = await validate_license(settings, payload.license_key)
    except BillingError as exc:
        locale = resolve_locale(request)
        raise HTTPException(status_code=422, detail=localize(str(exc), locale))

    token = sign_session(
        settings,
        email=info.get("email", ""),
        plan=info.get("plan", "premium"),
        provider=info.get("provider", "lemonsqueezy"),
        license_key=info.get("license_key", payload.license_key),
    )
    if not token:
        raise HTTPException(status_code=503, detail="Activation is not available yet.")

    request.app.state.store.put_entitlement(
        {
            "session_token": token,
            "email": info.get("email", ""),
            "plan": info.get("plan", "premium"),
            "status": "active",
            "provider": info.get("provider", "lemonsqueezy"),
            "license_key": info.get("license_key", ""),
            "expires_at": None,
        }
    )
    log.info("premium activated for %s", info.get("email") or "unknown")
    return {"token": token, "plan": "premium", "email": info.get("email", ""), "status": "active"}


@router.get("/billing/session", response_model=SessionOut)
def session_status(request: Request) -> dict:
    """Report whether the presented token is a valid premium session."""
    from ..billing import verify_session

    auth = request.headers.get("authorization", "")
    token = auth.split(" ", 1)[1].strip() if auth.lower().startswith("bearer ") else ""
    payload = verify_session(request.app.state.settings, token) if token else None
    row = request.app.state.store.get_entitlement(token) if payload else None
    if not payload or not row or (row.get("status") or "").lower() != "active":
        return {"token": "", "plan": "free", "email": "", "status": "free"}
    return {
        "token": token,
        "plan": payload.get("plan", "premium"),
        "email": payload.get("email", ""),
        "status": "active",
    }


@router.post("/billing/webhook")
async def webhook(request: Request, x_signature: str = Header(default="")) -> dict:
    """Handle Lemon Squeezy subscription lifecycle events.

    The webhook keeps entitlements honest after the sale: a cancellation, expiry
    or refund must revoke premium even if the user never returns to the app. We
    verify the HMAC signature (constant-time) and ignore unsigned calls, so a
    forged POST cannot grant premium.
    """
    import hashlib
    import hmac as _hmac
    import json as _json

    settings = request.app.state.settings
    if not settings.lemonsqueezy_webhook_secret:
        raise HTTPException(status_code=503, detail="webhook not configured")

    raw = await request.body()
    expected = _hmac.new(
        settings.lemonsqueezy_webhook_secret.encode(), raw, hashlib.sha256
    ).hexdigest()
    if not _hmac.compare_digest(expected, x_signature or ""):
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        body = _json.loads(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid payload")

    event = (body.get("meta") or {}).get("event_name", "")
    attrs = ((body.get("data") or {}).get("attributes") or {})
    email = attrs.get("user_email") or attrs.get("customer_email") or ""
    store = request.app.state.store

    revoked_events = {
        "subscription_cancelled",
        "subscription_expired",
        "subscription_paused",
        "order_refunded",
    }
    if event in revoked_events and email:
        row = store.get_entitlement_by_email(email)
        if row:
            store.set_entitlement_status(row["session_token"], "revoked")
            log.info("entitlement revoked for %s (%s)", email, event)

    return {"ok": True, "event": event}
