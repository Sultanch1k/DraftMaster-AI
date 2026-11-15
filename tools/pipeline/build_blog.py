"""Publish the growth agent's blog output as a committed web dataset.

The growth agent writes Markdown to ``data/growth/out/blog/<locale>/<id>.md``,
which is git-ignored and lives outside ``apps/web`` — so Vercel never sees it.
This step mirrors ``build_seo_pages.py``: it reads that output and writes a
compact JSON dataset into the web app so the ``/blog`` routes can serve the
content as real, indexable pages.

Run after a growth cycle (the GitHub workflow does this automatically):

    python tools/pipeline/build_blog.py

The slug is derived from ``topic`` + ``locale`` only, so a topic re-published on
a later cycle updates the same URL instead of creating a duplicate page.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(os.environ.get("DRAFTMASTER_GROWTH_OUTPUT", str(ROOT / "data" / "growth" / "out"))) / "blog"
OUT = ROOT / "apps" / "web" / "src" / "data" / "blog-posts.json"

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.lower()).strip("-") or "post"


def _excerpt(body: str, limit: int = 200) -> str:
    text = re.sub(r"[#*•\-]", " ", body)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].rstrip() + ("…" if len(text) > limit else "")


def parse_post(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    _, front, body = text.split("---", 2)
    meta: dict[str, str] = {}
    for line in front.strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()

    title = meta.get("title", "")
    if title.startswith('"'):
        try:
            title = json.loads(title)
        except json.JSONDecodeError:
            title = title.strip('"')

    topic = meta.get("topic", path.stem)
    locale = meta.get("locale", "en")
    return {
        "slug": f"{slugify(topic)}-{locale}",
        "title": title,
        "topic": topic,
        "locale": locale,
        "created_at": meta.get("created_at", ""),
        "excerpt": _excerpt(body),
        "body": body.strip(),
    }


def build() -> dict:
    posts: dict[str, dict] = {}
    if SRC.exists():
        for path in sorted(SRC.rglob("*.md")):
            post = parse_post(path)
            if not post:
                continue
            # Newest wins for a given slug, so a refreshed topic keeps its URL.
            existing = posts.get(post["slug"])
            if existing is None or post["created_at"] > existing["created_at"]:
                posts[post["slug"]] = post

    ordered = sorted(posts.values(), key=lambda p: p["created_at"], reverse=True)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "posts": ordered,
    }


def main() -> None:
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {len(data['posts'])} blog posts -> {OUT}")


if __name__ == "__main__":
    main()
