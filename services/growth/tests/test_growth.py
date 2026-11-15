"""Growth engine tests.

These assert the properties the whole design rests on: determinism, safety by
default, no repetition, and a feedback loop that actually changes future
decisions.
"""
from __future__ import annotations

import json

from draftmaster_growth.content import ContentEngine, VARIANTS
from draftmaster_growth.models import MetricSample
from draftmaster_growth.optimizer import Optimizer
from draftmaster_growth.store import GrowthStore
from draftmaster_growth.topics import build_topic_pool, select_topics
from draftmaster_growth.video import VideoEngine, build_ffmpeg_command


# --- topics -----------------------------------------------------------------
def test_topic_pool_is_non_trivial_and_stable(dataset):
    pool = build_topic_pool(dataset, "en")
    assert len(pool) > 100  # one guide + one matchup per hero, plus meta
    keys = [t.key for t in pool]
    assert keys[0] == "meta.winners"
    assert any(k.startswith("guide.") for k in keys)
    assert any(k.startswith("matchup.") for k in keys)
    # Same dataset -> same order (determinism).
    assert keys == [t.key for t in build_topic_pool(dataset, "en")]


def test_select_topics_skips_seen_and_rotates(dataset):
    pool = build_topic_pool(dataset, "en")
    first = select_topics(pool, seen=set(), limit=3, offset=0)
    assert len(first) == 3
    seen = {t.signature() for t in first}
    nxt = select_topics(pool, seen=seen, limit=3, offset=0)
    # Nothing already published is selected again.
    assert not (seen & {t.signature() for t in nxt})
    # A rotated offset surfaces a different slice.
    rotated = select_topics(pool, seen=set(), limit=3, offset=10)
    assert [t.key for t in rotated] != [t.key for t in first]


# --- content ----------------------------------------------------------------
def test_render_is_deterministic_and_data_backed(dataset):
    engine = ContentEngine(dataset)
    pool = build_topic_pool(dataset, "en")
    topic = next(t for t in pool if t.kind == "meta")
    a = engine.render(topic, variant="hook-first")
    b = engine.render(topic, variant="hook-first")
    assert a.item_id == b.item_id
    assert a.body == b.body
    # The body must contain a real hero name from the dataset.
    names = [h["localized_name"] for h in dataset.heroes]
    assert any(n in a.body for n in names)


def test_variant_changes_the_rendering(dataset):
    engine = ContentEngine(dataset)
    topic = next(t for t in build_topic_pool(dataset, "en") if t.kind == "matchup")
    bodies = {v: engine.render(topic, variant=v).body for v in ("hook-first", "data-led", "question")}
    # Different frames must produce different text, and different ids.
    assert len(set(bodies.values())) >= 2
    ids = {v: engine.render(topic, variant=v).item_id for v in VARIANTS}
    assert len(set(ids.values())) == len(VARIANTS)


def test_russian_rendering_is_actually_russian(dataset):
    engine = ContentEngine(dataset)
    topic = next(t for t in build_topic_pool(dataset, "ru") if t.kind == "meta")
    item = engine.render(topic, variant="hook-first")
    assert any("\u0400" <= ch <= "\u04ff" for ch in item.body)  # cyrillic present
    assert item.locale == "ru"


def test_every_topic_kind_renders_in_both_locales(dataset):
    engine = ContentEngine(dataset)
    for locale in ("en", "ru"):
        pool = build_topic_pool(dataset, locale)
        seen_kinds = set()
        for topic in pool:
            if topic.kind in seen_kinds:
                continue
            seen_kinds.add(topic.kind)
            item = engine.render(topic, variant="hook-first")
            assert item.title and item.body
            assert item.links["home"].startswith("https://")
        assert seen_kinds == {"meta", "matchup", "guide", "panic"}


# --- safety -----------------------------------------------------------------
def test_publishing_is_dry_run_without_credentials(agent):
    report = agent.run_cycle(posts=2, videos=0, outreach=False)
    assert report["allow_publish"] is False
    # The blog channel is live (it writes files); social channels are dry.
    assert report["published_live"] >= 1
    assert report["published_dry"] >= 1
    for res in report["publish_results"]:
        if res["channel"] != "blog":
            assert res["live"] is False
            assert "dry run" in res["detail"]


def test_live_flag_alone_does_not_send_without_credentials(agent):
    agent.settings.allow_publish = True
    # Twitter is enabled=False and uncredentialed; it must still be a dry run.
    channel = agent.channels["twitter"]
    item = agent.content.render(build_topic_pool(agent.ds, "en")[0])
    res = channel.publish(item)
    assert res.live is False


# --- feedback loop ----------------------------------------------------------
def test_optimizer_proves_unseen_variants_first(tmp_path):
    store = GrowthStore(tmp_path / "opt.json")
    opt = Optimizer(store, exploration_rate=0.2, min_samples=2)
    # With no data, it rotates through the untested variants.
    picks = {opt.choose(observation_index=i) for i in range(len(VARIANTS))}
    assert picks == set(VARIANTS)


def test_optimizer_exploits_the_winner_once_proven(tmp_path):
    store = GrowthStore(tmp_path / "s.json")
    opt = Optimizer(store, exploration_rate=0.0, min_samples=1)
    samples = []
    # Give every variant some signal so none is "unproven"; hook-first wins.
    for v in VARIANTS:
        samples.append(MetricSample("a", v, "t", "blog", impressions=100, clicks=2, conversions=0))
    for _ in range(10):
        samples.append(MetricSample("i1", "hook-first", "t", "blog", impressions=100, clicks=30, conversions=1))
    store.record_metrics(samples)
    assert opt.choose(observation_index=3) == "hook-first"
    assert opt.ranking()[0]["variant"] == "hook-first"


def test_feedback_loop_changes_future_selection(agent):
    # Simulate outcomes for every variant, with one clear winner, then check the
    # agent prefers it.
    agent.store.record_metrics(
        [MetricSample(f"w{i}", v, "t", "blog", impressions=200, clicks=1, conversions=0) for v in VARIANTS for i in range(6)]
    )
    agent.store.record_metrics(
        [MetricSample(f"i{i}", "listicle", "t", "blog", impressions=200, clicks=60, conversions=2) for i in range(6)]
    )
    assert agent.optimizer.choose(observation_index=3) == "listicle"
    assert "listicle" in agent.optimizer.recommendation()


def test_metrics_ingestion_without_remote_still_records_volume(agent):
    agent.run_cycle(posts=2, videos=0, outreach=False)
    before = len(agent.store.metric_samples())
    samples = agent.metrics.ingest(remote=None)
    assert samples  # one per published item
    assert len(agent.store.metric_samples()) > before


def test_metrics_ingestion_with_remote_attributes_by_variant(agent):
    agent.run_cycle(posts=2, videos=0, outreach=False)
    remote = {"funnel": {"page_view": 1000, "analysis_run": 50, "panic_run": 20}, "paying_customers": 3}
    samples = agent.metrics.attribute(remote)
    assert samples
    assert sum(s.clicks for s in samples) <= 70
    assert any(s.variant for s in samples)


# --- cycle behaviour --------------------------------------------------------
def test_repeated_cycles_do_not_republish_the_same_topic(agent):
    first = agent.run_cycle(posts=3, videos=0, outreach=False)
    second = agent.run_cycle(posts=3, videos=0, outreach=False)
    def topics(report):
        return {r["item"]["topic"] for r in report["publish_results"]}
    assert not (topics(first) & topics(second))


def test_store_roundtrip_and_atomic_write(tmp_path):
    path = tmp_path / "state.json"
    store = GrowthStore(path)
    store.record_run({"started_at": "2026-01-01", "day": "2026-01-01"})
    store.save()
    assert path.exists()
    reloaded = GrowthStore(path)
    assert reloaded.run_count() == 1


def test_corrupt_state_does_not_crash(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{ this is not json", encoding="utf-8")
    store = GrowthStore(path)
    assert store.run_count() == 0
    assert path.with_suffix(".corrupt.json").exists()


# --- video ------------------------------------------------------------------
def test_video_script_has_shots_and_srt(dataset):
    engine = VideoEngine(dataset)
    topic = next(t for t in build_topic_pool(dataset, "en") if t.kind == "meta")
    script = engine.build_script(topic, locale="en")
    assert script.shots
    assert script.duration > 0
    srt = script.to_srt()
    assert "-->" in srt and srt.startswith("1\n")


def test_video_meta_label_matches_topic(dataset):
    engine = VideoEngine(dataset)
    pool = build_topic_pool(dataset, "en")
    winners = next(t for t in pool if t.key == "meta.winners")
    losers = next(t for t in pool if t.key == "meta.losers")
    assert "hero" in engine.build_script(winners, "en").title.lower()
    assert "worst" in engine.build_script(losers, "en").title.lower()


def test_ffmpeg_command_is_well_formed(dataset, tmp_path):
    engine = VideoEngine(dataset)
    topic = next(t for t in build_topic_pool(dataset, "en") if t.kind == "panic")
    script = engine.build_script(topic, "en")
    cmd = build_ffmpeg_command(script, tmp_path / "out.mp4")
    assert cmd[0] == "ffmpeg"
    assert "drawtext" in " ".join(cmd)
    assert str(tmp_path / "out.mp4") == cmd[-1]


def test_video_render_writes_artifacts_without_ffmpeg(dataset, tmp_path):
    engine = VideoEngine(dataset)
    topic = next(t for t in build_topic_pool(dataset, "en") if t.kind == "meta")
    script = engine.build_script(topic, "en")
    result = engine.render(script, tmp_path)
    from pathlib import Path

    assert Path(result["dir"], f"{script.script_id}.srt").exists()
    assert Path(result["dir"], f"{script.script_id}.json").exists()


# --- outreach ---------------------------------------------------------------
def test_outreach_messages_are_personalised(agent):
    result = agent.do_outreach(limit=3)
    assert result["messages"]
    for msg in result["messages"]:
        # Every message names the prospect and a real hero.
        assert msg["prospect"]["name"]
        assert any(h["localized_name"] in msg["body"] for h in agent.ds.heroes)
        assert "DraftMaster AI" in msg["body"] or "DraftMaster AI" in msg["body"]


def test_outreach_respects_cooldown(agent):
    candidates = agent.outreach.candidates(limit=5)
    assert candidates
    first = candidates[0]
    agent.outreach.record_touch(first)
    # Immediately after a touch the prospect is on cooldown.
    keys = {p.key for p in agent.outreach.candidates(limit=5)}
    assert first.key not in keys


def test_post_budget_is_fully_used_across_locales(agent):
    created = agent.create(posts=3, videos=0)
    assert len(created["items"]) == 3
    locales = [i.locale for i in created["items"]]
    assert locales.count("en") >= 1 and locales.count("ru") >= 1


def test_status_reports_channels_and_optimizer(agent):
    status = agent.status()
    assert "variant_ranking" in status
    assert "twitter" in status["channels"]
    assert status["allow_publish"] is False


def test_cycle_report_is_json_serialisable(agent):
    report = agent.run_cycle(posts=2, videos=1, outreach=False)
    # The report is written to state as JSON, so it must serialise cleanly.
    json.dumps(report, default=str)
    assert report["items_created"] >= 1
