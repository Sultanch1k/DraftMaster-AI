"""Screenshot hero-detection tests.

These build a *real* draft screenshot by downloading genuine hero portraits
from Valve's CDN and compositing them into a draft-style row, then run the
detector over the result. Nothing is mocked: the portraits are the real images
the game renders, and the detector only ever sees pixels.
"""
from __future__ import annotations

import io
import json
import urllib.request
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
CDN = "https://cdn.cloudflare.steamstatic.com"


@pytest.fixture(scope="module")
def dataset():
    with (ROOT / "data" / "artifacts" / "draftmaster-data.json").open() as fh:
        return json.load(fh)


def _portrait(hero: dict) -> Image.Image:
    url = CDN + (hero.get("img") or "").split("?")[0]
    req = urllib.request.Request(url, headers={"User-Agent": "DraftMasterAI/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return Image.open(io.BytesIO(resp.read())).convert("RGB")


def _draft_screenshot(heroes: list[dict], tile: int = 72, gap: int = 10) -> bytes:
    """Composite heroes into a row on a dark background, like the pick screen."""
    width = gap + len(heroes) * (tile + gap)
    canvas = Image.new("RGB", (width, tile + 2 * gap), (18, 20, 26))
    for i, hero in enumerate(heroes):
        img = _portrait(hero).resize((tile, tile), Image.LANCZOS)
        canvas.paste(img, (gap + i * (tile + gap), gap))
    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


def _heroes_by_name(dataset, names):
    index = {h["localized_name"]: h for h in dataset["heroes"]}
    return [index[n] for n in names]


@pytest.fixture(scope="module")
def analyzer():
    from draftmaster_engine.screenshot import ScreenshotAnalyzer

    a = ScreenshotAnalyzer()
    a._load()
    return a


def test_signatures_cover_the_roster(analyzer):
    assert len(analyzer.signatures) >= 120


def test_detects_a_single_hero_portrait(dataset, analyzer):
    heroes = _heroes_by_name(dataset, ["Axe"])
    shot = _draft_screenshot(heroes)
    result = analyzer.analyse(shot)
    assert result["count"] >= 1
    assert result["hero_ids"][0] == heroes[0]["id"]


def test_detects_a_five_hero_draft_row(dataset, analyzer):
    names = ["Lion", "Axe", "Shadow Shaman", "Sniper", "Huskar"]
    heroes = _heroes_by_name(dataset, names)
    shot = _draft_screenshot(heroes)
    result = analyzer.analyse(shot)
    detected = set(result["hero_ids"])
    expected = {h["id"] for h in heroes}
    # Detection must recover the majority of the row; every hit must be exact.
    assert len(detected & expected) >= 3
    assert detected <= expected | set(), "detector invented a hero not on screen"


def test_detected_heroes_are_high_confidence(dataset, analyzer):
    heroes = _heroes_by_name(dataset, ["Lion", "Axe", "Shadow Shaman"])
    shot = _draft_screenshot(heroes)
    result = analyzer.analyse(shot)
    assert result["detected"]
    for det in result["detected"]:
        assert det["confidence"] >= result["confidence_floor"]


def test_blank_image_detects_nothing(analyzer):
    blank = Image.new("RGB", (600, 200), (12, 12, 12))
    buf = io.BytesIO()
    blank.save(buf, format="PNG")
    result = analyzer.analyse(buf.getvalue())
    assert result["count"] == 0


def test_detection_feeds_the_engine(dataset, analyzer):
    """End-to-end: screenshot -> detection -> full strategy report."""
    from draftmaster_engine import ReportEngine

    heroes = _heroes_by_name(dataset, ["Lion", "Axe", "Shadow Shaman"])
    shot = _draft_screenshot(heroes)
    result = analyzer.analyse(shot)
    assert result["hero_ids"]

    engine = ReportEngine()
    report = engine.analyse(enemy_ids=result["hero_ids"], role="carry")
    assert report.best_picks
    assert report.one_sentence_win_plan.endswith(".")
