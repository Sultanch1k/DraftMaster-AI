"""Billing: turn a real payment into a server-verifiable premium entitlement.

Design constraints that shaped this module:

* **Zero fixed cost.** Lemon Squeezy is merchant-of-record, so it handles VAT and
  there is no monthly fee — only a per-transaction cut. That matters more at this
  stage than a lower headline rate.
* **No user accounts required to sell.** The product works anonymously, so
  requiring a signup before purchase would add friction at the exact moment of
  highest intent. Instead a buyer activates with the *license key* Lemon Squeezy
  emails them, and we mint a signed session token the browser stores.
* **Server-authoritative.** The old code trusted a client-side flag
  (`localStorage.draftmaster_premium`). Here the token is HMAC-signed and checked
  against the entitlement store on every request, so premium cannot be forged.
* **Degrade to free.** With no keys configured the app runs fully on the free
  plan and every premium path simply returns "not premium".
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

import httpx

from .config import Settings

log = logging.getLogger("draftmaster.billing")

LEMONSQUEEZY_API = "https://api.lemonsqueezy.com/v1"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 400  # ~13 months; annual plans still fit.


class BillingError(Exception):
    """Raised when a license cannot be validated (message is user-safe)."""


def _b64e(raw: bytes) -> str:
    return urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(text: str) -> bytes:
    return urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign_session(settings: Settings, *, email: str, plan: str, provider: str, license_key: str) -> str:
    """Mint a signed session token. Returns '' when no signing key is configured."""
    if not settings.secret_key:
        return ""
    payload = {
        "sub": hashlib.sha256((email or license_key).encode()).hexdigest()[:16],
        "email": email,
        "plan": plan,
        "provider": provider,
        "iat": int(time.time()),
        "exp": int(time.time()) + SESSION_TTL_SECONDS,
        "nonce": secrets.token_hex(8),
    }
    body = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64e(sig)}"


def verify_session(settings: Settings, token: str) -> dict | None:
    """Return the payload of a valid, unexpired token, else None."""
    if not settings.secret_key or not token or "." not in token:
        return None
    body, _, sig = token.partition(".")
    expected = hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).digest()
    try:
        given = _b64d(sig)
    except Exception:
        return None
    if not hmac.compare_digest(expected, given):
        return None
    try:
        payload = json.loads(_b64d(body))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < time.time():
        return None
    return payload


def is_configured(settings: Settings) -> bool:
    return bool(settings.lemonsqueezy_api_key and settings.lemonsqueezy_store_id and settings.secret_key)


def _license_status_is_active(status: str) -> bool:
    return (status or "").lower() in {"active", "paid"}


async def validate_license(settings: Settings, license_key: str) -> dict:
    """Ask Lemon Squeezy whether a license key is active.

    Returns a normalised dict. Raises BillingError with a user-safe message when
    the key is invalid, the store is unconfigured, or the upstream call fails.
    """
    key = (license_key or "").strip()
    if not key:
        raise BillingError("Please paste the license key from your purchase email.")
    if not is_configured(settings):
        raise BillingError("Activation is not available yet. Please try again later.")

    payload = {"license_key": key, "instance_name": "draftmaster-web"}
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.post(
                f"{LEMONSQUEEZY_API}/licenses/activate",
                headers={
                    "Accept": "application/vnd.api+json",
                    "Content-Type": "application/vnd.api+json",
                    "Authorization": f"Bearer {settings.lemonsqueezy_api_key}",
                },
                json={"data": {"type": "license-keys", "attributes": payload}},
            )
    except Exception as exc:  # network/upstream
        log.warning("license activation upstream error: %s", exc)
        raise BillingError("Could not reach the payment provider. Please try again in a moment.")

    if resp.status_code >= 400:
        # Lemon Squeezy returns 404 for an unknown key; anything 4xx means the
        # key is not usable. Never echo the raw upstream body to the client.
        raise BillingError("That license key was not recognised. Check the key and try again.")

    try:
        data = resp.json().get("data", {})
        attrs = data.get("attributes", {})
    except Exception:
        raise BillingError("Unexpected response from the payment provider. Please try again.")

    status = attrs.get("status", "")
    if not _license_status_is_active(status):
        raise BillingError("That license is not active (it may have expired or been refunded).")

    return {
        "license_key": attrs.get("key", key),
        "status": status,
        "email": attrs.get("customer_email") or attrs.get("email") or "",
        "plan": "premium",
        "provider": "lemonsqueezy",
    }
