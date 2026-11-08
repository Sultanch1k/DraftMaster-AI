"""Locale resolution for API responses.

The frontend sends the active locale in an `x-locale` header (and, for POSTs,
in the request body so it participates in the cache key). Anything unsupported
falls back to English.
"""
from __future__ import annotations

from fastapi import Request

from draftmaster_engine.i18n import DEFAULT, localize, localize_report, normalize_locale


def resolve_locale(request: Request, explicit: str | None = None) -> str:
    """Pick the response locale: explicit body value, then header, then default."""
    if explicit:
        return normalize_locale(explicit)
    return normalize_locale(request.headers.get("x-locale") or request.headers.get("accept-language"))


def localize_analysis(payload: dict, locale: str) -> dict:
    """Translate an /analyse response body (report + usage)."""
    if locale == DEFAULT:
        return payload
    if isinstance(payload.get("report"), dict):
        payload["report"] = localize_report(payload["report"], locale)
    return payload


def localize_panic(payload: dict, locale: str) -> dict:
    """Translate an /panic response body."""
    if locale == DEFAULT:
        return payload
    return localize(payload, locale)


def localize_hero_strategy(payload: dict, locale: str) -> dict:
    """Translate a /hero-strategy response body.

    Uses the dimension-aware path so the threat labels the UI renders are
    translated too, exactly as they are for the draft report.
    """
    if locale == DEFAULT:
        return payload
    from draftmaster_engine.i18n import localize_report

    # The strategy body is nested under "strategy", and localize_report expects
    # the report at the top level (it remaps the threat-dimension labels in
    # place), so translate the inner dict rather than the envelope.
    if isinstance(payload.get("strategy"), dict):
        payload["strategy"] = localize_report(payload["strategy"], locale)
    return payload


def localize_coach(payload: dict, locale: str) -> dict:
    """Translate a match-coach response body."""
    if locale == DEFAULT:
        return payload
    return localize(payload, locale)
