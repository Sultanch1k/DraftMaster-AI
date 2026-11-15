"""Signed share tokens for public win-plan links.

A share link must render the full plan for anyone who opens it, including a
stranger who has never used the product — that is the whole point of the loop.
But an unsigned "render any draft" endpoint would be an unlimited free analysis
endpoint and would leak the paywall entirely.

The compromise: the *creator* pays the normal quota to mint a share token (and
pays nothing when re-sharing a draft they already analysed today, because the
quota signature matches). The token is HMAC-signed by the server, so it cannot
be fabricated, and the public render endpoint trusts the token instead of
re-charging quota. A forged or edited token is rejected.

Tokens carry an expiry so a leaked link is not permanent.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

from .config import Settings

SHARE_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 days


def _b64e(raw: bytes) -> str:
    return urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(text: str) -> bytes:
    return urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(secret: str, body: str) -> str:
    return _b64e(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())


def sign_share(settings: Settings, payload: dict) -> str:
    """Mint a signed share token. Returns '' when no signing key is configured."""
    if not settings.secret_key:
        return ""
    body = _b64e(
        json.dumps(
            {"p": payload, "iat": int(time.time()), "exp": int(time.time()) + SHARE_TTL_SECONDS},
            separators=(",", ":"),
        ).encode()
    )
    return f"{body}.{_sign(settings.secret_key, body)}"


def verify_share(settings: Settings, token: str) -> dict | None:
    """Return the payload of a valid, unexpired share token, else None."""
    if not settings.secret_key or not token or "." not in token:
        return None
    body, _, sig = token.partition(".")
    if not hmac.compare_digest(_sign(settings.secret_key, body), sig):
        return None
    try:
        wrapper = json.loads(_b64d(body))
    except Exception:
        return None
    if int(wrapper.get("exp", 0)) < time.time():
        return None
    payload = wrapper.get("p")
    if not isinstance(payload, dict):
        return None
    enemies = payload.get("e")
    if not isinstance(enemies, list) or not (1 <= len(enemies) <= 5):
        return None
    if not all(isinstance(i, int) and i > 0 for i in enemies):
        return None
    return payload
