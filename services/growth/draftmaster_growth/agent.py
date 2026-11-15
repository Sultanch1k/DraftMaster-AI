"""The growth agent.

One object owns the whole loop. A *cycle* is:

1. **measure** — pull outcome data and fold it into variant statistics,
2. **decide** — choose today's topics (unseen, rotated) and the variant to run
   them under (the bandit's choice),
3. **create** — render content, scripts and outreach messages,
4. **publish** — hand each item to its channel (dry-run unless configured live),
5. **record** — write everything to the store so the next cycle is smarter.

The agent is deterministic given (state, dataset, day). It never raises on a
channel failure: a failed post is recorded and the cycle continues, because one
broken integration must not stop the rest of the growth machine.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from draftmaster_engine import get_dataset

from .channels import build_channels
from .config import GrowthConfig
from .content import ContentEngine
from .metrics import MetricsClient
from .models import ContentItem
from .optimizer import Optimizer
from .outreach import OutreachEngine
from .store import GrowthStore
from .topics import build_topic_pool, select_topics
from .video import VideoEngine

log = logging.getLogger("draftmaster.growth")

# How many recent runs to consider when rotating the topic slice. Each cycle
# advances the ring by the number of items it published, so coverage grows.
LOCALES = ["en", "ru"]


def _utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class GrowthAgent:
    def __init__(self, settings: GrowthConfig | None = None, dataset=None):
        self.settings = settings or GrowthConfig.from_env()
        self.ds = dataset or get_dataset(self.settings.dataset_path)
        self.store = GrowthStore(self.settings.state_path)
        self.content = ContentEngine(self.ds)
        self.video = VideoEngine(self.ds)
        self.optimizer = Optimizer(self.store, exploration_rate=self.settings.exploration_rate)
        self.metrics = MetricsClient(self.settings, self.store)
        self.outreach = OutreachEngine(self.ds, self.settings, self.store)
        self.channels = build_channels(self.settings)

    # -- cycle steps -----------------------------------------------------
    def measure(self, remote: dict | None = None) -> list:
        samples = self.metrics.ingest(remote)
        return samples

    def decide(self, *, limit: int, locale: str = "en"):
        """Choose the next unseen topics and the variant to run them under."""
        pool = build_topic_pool(self.ds, locale)
        seen = self._seen_signatures()
        offset = self.store.counter(f"offset:{locale}")
        topics = select_topics(pool, seen=seen, limit=limit, offset=offset)
        variant = self.optimizer.choose()
        return topics, variant

    def _seen_signatures(self) -> set[str]:
        seen = set()
        for row in self.store.published_items():
            item = row.get("item") or {}
            sig = item.get("signature") or item.get("topic")
            if sig:
                seen.add(sig)
        return seen

    def create(self, *, posts: int | None = None, videos: int | None = None) -> dict:
        """Render today's content across both locales."""
        posts = self.settings.posts_per_day if posts is None else posts
        videos = self.settings.videos_per_day if videos is None else videos
        items: list[ContentItem] = []
        scripts = []
        # Distribute the post budget across locales, handing the remainder to the
        # first locales so `posts=3` yields 2 EN + 1 RU rather than dropping one.
        base, rem = divmod(posts, len(LOCALES))
        for idx, locale in enumerate(LOCALES):
            want = base + (1 if idx < rem else 0)
            topics, variant = self.decide(limit=want + videos, locale=locale)
            for i, topic in enumerate(topics):
                if i < want:
                    item = self.content.render(topic, variant=variant, channel="blog")
                    items.append(item)
                elif len(scripts) < videos * len(LOCALES):
                    scripts.append((topic, locale))
        return {"items": items, "script_topics": scripts}

    def publish(self, items: list[ContentItem]) -> list:
        """Ship each item to its channel(s) and record the result."""
        results = []
        for item in items:
            # Long-form goes to the blog (always live); short-form also fans out
            # to any live social channel.
            targets = ["blog"]
            if len(item.body) <= 1200:
                targets += ["discord", "telegram", "twitter"]
            for name in targets:
                channel = self.channels.get(name)
                if channel is None:
                    continue
                try:
                    res = channel.publish(item)
                except Exception as exc:  # a channel bug must not kill the cycle
                    from .models import PublishResult

                    res = PublishResult(item.item_id, name, ok=False, live=False, detail=f"error: {exc}")
                results.append(res)
                self.store.record_publish(res, item.to_dict())
        return results

    def render_videos(self, script_topics: list[tuple]) -> list[dict]:
        out = []
        for topic, locale in script_topics:
            script = self.video.build_script(topic, locale=locale)
            out.append(self.video.render(script, self.settings.output_dir))
        return out

    def do_outreach(self, limit: int | None = None) -> dict:
        limit = self.settings.outreach_per_day if limit is None else limit
        candidates = self.outreach.candidates(limit=limit)
        messages = [self.outreach.message(p, locale=("ru" if p.platform == "telegram" else "en")) for p in candidates]
        paths = self.outreach.write_messages(messages)
        if self.settings.channel("telegram").live and self.settings.allow_publish:
            # Only the community channel is sent automatically; creator outreach
            # stays human-reviewed because a bad cold email burns a relationship.
            for m in messages:
                if m.prospect.platform == "telegram":
                    self.outreach.record_touch(m.prospect)
        return {"candidates": [p.to_dict() for p in candidates], "messages": [m.to_dict() for m in messages], "paths": paths}

    # -- the loop --------------------------------------------------------
    def run_cycle(self, *, posts: int | None = None, videos: int | None = None, outreach: bool = True, remote_metrics: dict | None = None) -> dict:
        started = _now_iso()
        day = _utc_day()
        log.info("growth cycle start (%s)", day)

        samples = self.measure(remote_metrics)
        created = self.create(posts=posts, videos=videos)
        published = self.publish(created["items"])
        video_results = self.render_videos(created["script_topics"])
        outreach_result = self.do_outreach() if outreach else {"candidates": [], "messages": [], "paths": []}

        # Advance the deterministic rotation so the next cycle picks new topics.
        for locale in LOCALES:
            self.store.bump_counter(f"offset:{locale}", by=max(1, len(created["items"])))

        live_count = sum(1 for r in published if r.live)
        # The stored rows carry the item alongside the result, so the report is
        # self-contained and a reader can see exactly what was published where.
        stored = self.store.published_items()[-len(published):] if published else []
        report = {
            "started_at": started,
            "day": day,
            "metrics_ingested": len(samples),
            "items_created": len(created["items"]),
            "publish_results": stored,
            "published_live": live_count,
            "published_dry": len(published) - live_count,
            "videos": video_results,
            "outreach": {
                "candidates": len(outreach_result["candidates"]),
                "messages": len(outreach_result["messages"]),
                "paths": outreach_result["paths"],
            },
            "variant_chosen": created["items"][0].variant if created["items"] else self.optimizer.choose(),
            "optimizer_note": self.optimizer.recommendation(),
            "allow_publish": self.settings.allow_publish,
        }
        self.store.record_run(report)
        self.store.log({"at": started, "event": "cycle", "summary": {
            "created": report["items_created"], "live": live_count, "dry": report["published_dry"],
        }})
        self.store.save()
        log.info("growth cycle done: %d items, %d live", report["items_created"], live_count)
        return report

    # -- reporting -------------------------------------------------------
    def status(self) -> dict:
        return {
            "runs": self.store.run_count(),
            "published_total": len(self.store.published_items()),
            "variant_ranking": self.optimizer.ranking(),
            "optimizer_note": self.optimizer.recommendation(),
            "prospects": {
                "total": len(self.store.prospects()),
                "by_status": _count_by(self.store.prospects(), "status"),
            },
            "channels": {
                name: {"enabled": ch.cfg.enabled, "live": ch.live}
                for name, ch in self.channels.items()
            },
            "allow_publish": self.settings.allow_publish,
            "state_path": self.settings.state_path,
        }


def _count_by(rows: list[dict], field: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        out[r.get(field, "?")] = out.get(r.get(field, "?"), 0) + 1
    return out
