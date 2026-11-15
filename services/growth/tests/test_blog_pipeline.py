"""Tests for the growth -> web blog pipeline.

`build_blog.py` is the bridge that turns the agent's git-ignored Markdown into a
committed dataset the web app serves. If it silently produces nothing, the blog
ships empty and the acquisition channel is dead without any error — so the
contract (parse, slug, dedupe, newest-wins) is pinned here.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location(
    "build_blog", ROOT / "tools" / "pipeline" / "build_blog.py"
)
assert _SPEC and _SPEC.loader
build_blog = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(build_blog)


def _write_post(dir_: Path, item_id: str, locale: str, topic: str, title: str, created: str, body: str) -> None:
    out = dir_ / "blog" / locale
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{item_id}.md").write_text(
        "---\n"
        f'title: "{title}"\n'
        f"topic: {topic}\n"
        "variant: data-led\n"
        f"locale: {locale}\n"
        f"created_at: {created}\n"
        "---\n\n"
        f"{body}\n",
        encoding="utf-8",
    )


@pytest.fixture()
def out_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(build_blog, "SRC", tmp_path / "blog")
    return tmp_path


def test_parses_markdown_into_a_post(out_dir):
    _write_post(out_dir, "abc123", "en", "meta.winners", "Patch winners", "2026-11-15T09:00:00+00:00", "Wraith King wins.")
    data = build_blog.build()
    assert len(data["posts"]) == 1
    post = data["posts"][0]
    assert post["slug"] == "meta-winners-en"
    assert post["title"] == "Patch winners"
    assert post["locale"] == "en"
    assert "Wraith King" in post["body"]


def test_empty_output_dir_yields_empty_dataset(out_dir):
    # The web app must still build with no posts; an empty list is valid.
    assert build_blog.build()["posts"] == []


def test_same_topic_and_locale_share_a_slug_newest_wins(out_dir):
    _write_post(out_dir, "old", "en", "meta.winners", "Old title", "2026-11-01T00:00:00+00:00", "old body")
    _write_post(out_dir, "new", "en", "meta.winners", "New title", "2026-11-15T00:00:00+00:00", "new body")
    posts = build_blog.build()["posts"]
    assert len(posts) == 1
    assert posts[0]["title"] == "New title"
    assert posts[0]["body"] == "new body"


def test_locales_get_distinct_slugs(out_dir):
    _write_post(out_dir, "a", "en", "meta.winners", "Patch winners", "2026-11-15T00:00:00+00:00", "en body")
    _write_post(out_dir, "b", "ru", "meta.winners", "Победители", "2026-11-15T00:00:00+00:00", "ru body")
    slugs = {p["slug"] for p in build_blog.build()["posts"]}
    assert slugs == {"meta-winners-en", "meta-winners-ru"}


def test_posts_are_ordered_newest_first(out_dir):
    _write_post(out_dir, "a", "en", "meta.winners", "A", "2026-11-01T00:00:00+00:00", "a")
    _write_post(out_dir, "b", "en", "meta.losers", "B", "2026-11-15T00:00:00+00:00", "b")
    posts = build_blog.build()["posts"]
    assert [p["title"] for p in posts] == ["B", "A"]


def test_excerpt_strips_markup_and_urls(out_dir):
    _write_post(out_dir, "a", "en", "meta.winners", "A", "2026-11-15T00:00:00+00:00", "• Wraith King — 55%\n\n → https://www.draftmaster.wiki")
    post = build_blog.build()["posts"][0]
    assert "http" not in post["excerpt"]
    assert "Wraith King" in post["excerpt"]
