#!/usr/bin/env python3
"""Revenue preflight: verify the money path before you try to take money.

Checks every invariant that must hold for a customer to pay and keep premium.
Exits non-zero if any check fails, so it can gate a release or be run by hand.

    python scripts/preflight.py --api https://draftmaster-ai.onrender.com
    python scripts/preflight.py --api http://127.0.0.1:12001 --metrics-token "$DRAFTMASTER_SECRET_KEY"

Deliberately stdlib-only: it must run anywhere, including CI, with no install.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

PASS, FAIL, WARN = "ok", "FAIL", "warn"


class Result:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def add(self, status: str, label: str, detail: str = "") -> None:
        self.rows.append((status, label, detail))

    @property
    def failed(self) -> bool:
        return any(s == FAIL for s, _, _ in self.rows)

    def render(self) -> None:
        width = max((len(label) for _, label, _ in self.rows), default=0)
        for status, label, detail in self.rows:
            mark = {"ok": "[ok]", "FAIL": "[FAIL]", "warn": "[warn]"}[status]
            line = f"{mark} {label.ljust(width)}"
            if detail:
                line += f"  {detail}"
            print(line)


def get_json(url: str, timeout: float = 20.0) -> tuple[int, dict | None]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - operator-supplied URL
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode() or "{}")
        except Exception:
            return exc.code, None
    except Exception:
        return 0, None


def post_json(url: str, payload: dict, timeout: float = 30.0) -> tuple[int, dict | None]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode() or "{}")
        except Exception:
            return exc.code, None
    except Exception:
        return 0, None


def main() -> int:
    ap = argparse.ArgumentParser(description="DraftMaster revenue preflight")
    ap.add_argument("--api", required=True, help="API origin, e.g. https://draftmaster-ai.onrender.com")
    ap.add_argument("--metrics-token", default="", help="DRAFTMASTER_SECRET_KEY, to read the funnel")
    ap.add_argument("--expect-store", default="postgresql", help="substring the durable store detail must contain")
    args = ap.parse_args()

    api = args.api.rstrip("/")
    r = Result()

    # 1. Reachability + durability --------------------------------------------
    status, health = get_json(f"{api}/health")
    if status != 200 or not health:
        r.add(FAIL, "api reachable", f"GET /health -> {status or 'no response'}")
        r.render()
        print("\nCannot continue: the API did not answer /health.")
        return 1
    r.add(PASS, "api reachable", f"environment={health.get('environment')} patch={health.get('patch')}")

    store_detail = str(health.get("store_detail", ""))
    store_backend = str(health.get("store_backend", ""))
    if args.expect_store in store_detail:
        r.add(PASS, "store is durable", store_detail)
    else:
        r.add(
            FAIL,
            "store is durable",
            f"{store_backend}/{store_detail} -> entitlements lost on deploy (see go-live-runbook §1)",
        )

    if health.get("environment") == "production" and store_backend == "memory":
        r.add(FAIL, "store not in-memory in production", store_backend)

    # 2. Billing surface -------------------------------------------------------
    status, billing = get_json(f"{api}/api/billing/config")
    if status != 200 or not billing:
        r.add(FAIL, "billing config reachable", f"GET /api/billing/config -> {status}")
    else:
        if billing.get("enabled"):
            r.add(PASS, "billing enabled")
        else:
            r.add(FAIL, "billing enabled", "no purchase path exists (see go-live-runbook §3)")
        url = str(billing.get("checkout_url", ""))
        if url.startswith("https://"):
            r.add(PASS, "checkout url present", url)
        else:
            r.add(FAIL, "checkout url present", "the Upgrade button has nowhere to go")
        if not str(billing.get("support_email", "")).strip():
            r.add(WARN, "support email set", "buyers need an address for refunds")

    # 3. Forged keys must not grant premium ------------------------------------
    status, body = post_json(
        f"{api}/api/billing/activate", {"license_key": "DM-FORGED-PREFLIGHT-0000"}
    )
    if status in (400, 422, 401, 403):
        r.add(PASS, "forged license key rejected", f"HTTP {status}")
    elif status == 0:
        r.add(WARN, "forged license key rejected", "no response")
    else:
        r.add(FAIL, "forged license key rejected", f"HTTP {status} — a forged key may grant premium")

    # 4. The flagship engine still returns a full report ------------------------
    status, report = post_json(f"{api}/api/analyse", {"enemy_hero_ids": [19, 2, 27], "role": "carry"})
    if status == 200 and report and "report" in report:
        rep = report["report"]
        n = len(rep.get("pick_reports", []) or [])
        if n > 0:
            r.add(PASS, "flagship report complete", f"{n} pick reports")
        else:
            r.add(WARN, "flagship report complete", "no pick_reports in response")
    else:
        r.add(FAIL, "flagship report complete", f"POST /api/analyse -> {status}")

    # 5. Optional funnel read --------------------------------------------------
    if args.metrics_token:
        req = urllib.request.Request(
            f"{api}/api/metrics", headers={"x-metrics-token": args.metrics_token}
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
                metrics = json.loads(resp.read().decode() or "{}")
            r.add(
                PASS,
                "funnel readable",
                f"paying_customers={metrics.get('paying_customers')} subscribers={metrics.get('subscribers')}",
            )
        except Exception as exc:
            r.add(WARN, "funnel readable", f"could not read /api/metrics: {exc}")

    r.render()

    if r.failed:
        print("\nREVENUE PATH BLOCKED — fix the [FAIL] rows before promoting this deployment.")
        return 1
    print("\nRevenue path looks healthy. Complete the real end-to-end purchase test (runbook §4).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
