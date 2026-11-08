"""Generate the programmatic-SEO dataset for the web app.

Why a committed JSON and not a runtime API call: the Vercel project root is
`apps/web`, so the Python artifact under `data/` is not present at build time.
Emitting a self-contained file means the counter pages prerender statically with
no backend dependency — crawlers get fast HTML, and there is nothing to go down.

Run after any dataset rebuild:

    python tools/pipeline/build_seo_pages.py

It reads `data/artifacts/draftmaster-data.json` and writes
`apps/web/src/data/hero-counters.json`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "data" / "artifacts" / "draftmaster-data.json"
OUT = ROOT / "apps" / "web" / "src" / "data" / "hero-counters.json"

TOP_N = 10


def slugify(name: str) -> str:
    s = name.lower().replace("'", "").replace(".", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def main() -> None:
    data = json.loads(ARTIFACT.read_text())
    heroes = data["heroes"]
    by_id = {h["id"]: h for h in heroes}
    matrix = data["counters"]["matrix"]

    # Item rules are keyed by "problem" — the same problems the engine detects.
    counter_items = {r["problem"]: r["items"] for r in data.get("counter_item_rules", [])}
    avoid_items = {r["problem"]: r["items"] for r in data.get("avoid_item_rules", [])}
    item_names = {k: v.get("dname") or k for k, v in (data.get("items") or {}).items()}

    # A compact problem -> human label map for the page copy.
    PROBLEM_LABEL = {
        "heavy_single_target_disable": "heavy single-target disables",
        "heavy_magic_burst": "heavy magic burst",
        "heavy_physical": "heavy physical damage",
        "evasion_or_blind": "evasion or blind",
        "illusions_or_summons": "illusions and summons",
        "heal_heavy": "heavy healing and sustain",
        "invisibility": "invisibility",
        "heavy_cc_teamfight": "teamfight crowd control",
        "kite_and_slow": "kiting and slows",
        "silence": "silence",
        "burst_pure_damage": "burst pure damage",
        "split_push": "split push",
    }

    pages: dict[str, dict] = {}
    for h in heroes:
        hid = h["id"]
        row = matrix.get(str(hid), {})
        # matrix[a][b] = how much better `a` performs against `b` (logit-ish).
        # Heroes that beat `h` are those with a positive value against it.
        counters = []
        for other_id, val in row.items():
            oid = int(other_id)
            if oid == hid or oid not in by_id or val is None:
                continue
            counters.append((oid, val))
        counters.sort(key=lambda kv: -kv[1])
        best_against = counters[:TOP_N]                       # h performs well vs these
        weak_against = [c for c in counters if c[1] > 0]
        weak_against.sort(key=lambda kv: -kv[1])
        weak_against = weak_against[:TOP_N]                  # these beat h

        caps = h.get("capabilities", {}) or {}
        problems: list[str] = []
        if caps.get("magic", 0) >= 1.2 or caps.get("nuke_count", 0) >= 2:
            problems.append("heavy_magic_burst")
        if caps.get("physical", 0) >= 1.2:
            problems.append("heavy_physical")
        if caps.get("cc", 0) >= 1.5:
            problems.append("heavy_cc_teamfight")
        if caps.get("stun", 0) >= 1 or caps.get("disable_count", 0) >= 2:
            problems.append("heavy_single_target_disable")
        if caps.get("silence", 0):
            problems.append("silence")
        tags = set(h.get("tags", []))
        if "illusions" in tags or "summons" in tags:
            problems.append("illusions_or_summons")
        if "split_push" in tags:
            problems.append("split_push")
        if "sustain" in tags or "heal" in tags:
            problems.append("heal_heavy")
        if "invisibility" in tags:
            problems.append("invisibility")
        problems = list(dict.fromkeys(problems))

        good_items = []
        for p in problems:
            for key in counter_items.get(p, []):
                if key not in good_items:
                    good_items.append(key)
        bad_items = []
        for p in problems:
            for key in avoid_items.get(p, []):
                if key not in bad_items:
                    bad_items.append(key)

        pages[slugify(h["localized_name"])] = {
            "id": hid,
            "name": h["localized_name"],
            "slug": slugify(h["localized_name"]),
            "roles": h.get("roles", []),
            "icon": h.get("icon"),
            "img": h.get("img"),
            "attr": h.get("primary_attr"),
            "pub_winrate": round(float(h.get("pub_winrate") or 0) * 100, 2),
            "cm_winrate": round(float(h.get("cm_winrate") or 0) * 100, 2),
            "counters": [
                {"id": oid, "name": by_id[oid]["localized_name"], "slug": slugify(by_id[oid]["localized_name"]), "score": round(val, 4)}
                for oid, val in weak_against
            ],
            "strong_against": [
                {"id": oid, "name": by_id[oid]["localized_name"], "slug": slugify(by_id[oid]["localized_name"]), "score": round(val, 4)}
                for oid, val in best_against
            ],
            "problems": [PROBLEM_LABEL.get(p, p) for p in problems],
            "good_items": [{"key": k, "name": item_names.get(k, k)} for k in good_items[:10]],
            "bad_items": [{"key": k, "name": item_names.get(k, k)} for k in bad_items[:8]],
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"patch": (data.get("patch") or {}).get("name"), "heroes": pages}, separators=(",", ":")))
    print(f"wrote {len(pages)} hero pages ({OUT.stat().st_size // 1024} KB) -> {OUT}")


if __name__ == "__main__":
    main()
