"""Publishing channels.

Every channel is an adapter with the same contract: ``publish(item) -> PublishResult``.
An adapter is *live* only when its channel is enabled **and** credentialed; in
every other case it runs a dry run that records exactly what it would have sent
and returns ``ok=True, live=False``. That makes the whole agent safe to run with
no credentials — which is how it runs in CI and on a fresh clone.

Network channels use ``httpx`` (already a dependency) and never raise on a
non-2xx response: a failed post is data, not a crash. The caller decides whether
to retry.
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx

from .config import ChannelConfig, GrowthConfig
from .models import ContentItem, PublishResult


class Channel:
    """Base class: dry-run by default, HTTP helper, uniform result."""

    name = "base"

    def __init__(self, cfg: ChannelConfig, settings: GrowthConfig):
        self.cfg = cfg
        self.settings = settings

    @property
    def live(self) -> bool:
        return self.cfg.live and self.settings.allow_publish

    def _result(self, item: ContentItem, *, live: bool, external_id: str = "", detail: str = "") -> PublishResult:
        preview = (item.title + "\n\n" + item.body)[:280]
        return PublishResult(
            item_id=item.item_id,
            channel=self.name,
            ok=True,
            live=live,
            external_id=external_id,
            detail=detail,
            payload_preview=preview,
        )

    def _post(self, url: str, *, headers: dict | None = None, json_body: dict | None = None, data: dict | None = None):
        with httpx.Client(timeout=30.0) as client:
            return client.post(url, headers=headers, json=json_body, data=data)

    def publish(self, item: ContentItem) -> PublishResult:  # pragma: no cover - overridden
        raise NotImplementedError


class BlogChannel(Channel):
    """Writes the article to disk under the output dir as a Markdown file.

    This is the only channel that is live without a credential: it publishes to
    the repo's own content directory, which a static-site step can pick up. It
    is also the safest place to send the long-form pieces.
    """

    name = "blog"

    def publish(self, item: ContentItem) -> PublishResult:
        out_dir = Path(self.settings.output_dir) / "blog" / item.locale
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{item.item_id}.md"
        front_matter = (
            "---\n"
            f"title: {json.dumps(item.title, ensure_ascii=False)}\n"
            f"topic: {item.topic}\n"
            f"variant: {item.variant}\n"
            f"locale: {item.locale}\n"
            f"created_at: {item.created_at}\n"
            "---\n\n"
        )
        path.write_text(front_matter + item.body, encoding="utf-8")
        return self._result(item, live=True, external_id=str(path), detail="wrote markdown file")


class DiscordChannel(Channel):
    """Posts to a Discord webhook. One message per item."""

    name = "discord"

    def publish(self, item: ContentItem) -> PublishResult:
        webhook = self.cfg.extra.get("webhook_url") or self.cfg.token
        if not self.live:
            return self._result(item, live=False, detail="discord disabled or uncredentialed (dry run)")
        content = item.body
        for tag in item.hashtags:
            content += f" {tag}"
        try:
            resp = self._post(webhook, json_body={"content": content[:1990]})
            ok = resp.status_code < 300
            return self._result(
                item,
                live=True,
                external_id=str(resp.status_code),
                detail="posted" if ok else f"discord returned {resp.status_code}: {resp.text[:200]}",
            )
        except httpx.HTTPError as exc:
            return PublishResult(item.item_id, self.name, ok=False, live=True, detail=str(exc))


class TelegramChannel(Channel):
    """Posts to a Telegram channel via the Bot API.

    ``token`` is the bot token; the chat id is passed in ``extra``.
    """

    name = "telegram"

    def publish(self, item: ContentItem) -> PublishResult:
        chat_id = self.cfg.extra.get("chat_id", "")
        if not self.live or not chat_id:
            return self._result(item, live=False, detail="telegram disabled/uncredentialed (dry run)")
        url = f"https://api.telegram.org/bot{self.cfg.token}/sendMessage"
        try:
            resp = self._post(
                url,
                json_body={"chat_id": chat_id, "text": item.body[:4000], "disable_web_page_preview": False},
            )
            ok = resp.status_code < 300
            return self._result(
                item,
                live=True,
                external_id=str(resp.status_code),
                detail="posted" if ok else f"telegram returned {resp.status_code}",
            )
        except httpx.HTTPError as exc:
            return PublishResult(item.item_id, self.name, ok=False, live=True, detail=str(exc))


class TwitterChannel(Channel):
    """Posts a single tweet via the X API v2.

    The token is expected to be an OAuth2 bearer token with ``tweet.write``.
    """

    name = "twitter"

    def publish(self, item: ContentItem) -> PublishResult:
        if not self.live:
            return self._result(item, live=False, detail="twitter disabled/uncredentialed (dry run)")
        text = item.body
        for tag in item.hashtags:
            text += f" {tag}"
        try:
            resp = self._post(
                "https://api.twitter.com/2/tweets",
                headers={"Authorization": f"Bearer {self.cfg.token}", "Content-Type": "application/json"},
                json_body={"text": text[:280]},
            )
            ok = resp.status_code < 300
            ext = ""
            if ok:
                try:
                    ext = resp.json().get("data", {}).get("id", "")
                except (ValueError, AttributeError):
                    ext = ""
            return self._result(
                item,
                live=True,
                external_id=ext,
                detail="posted" if ok else f"twitter returned {resp.status_code}: {resp.text[:200]}",
            )
        except httpx.HTTPError as exc:
            return PublishResult(item.item_id, self.name, ok=False, live=True, detail=str(exc))


class RedditChannel(Channel):
    """Submits a self-post to a subreddit.

    ``token`` is an OAuth2 bearer token with ``submit`` scope; the subreddit is
    passed in ``extra``.
    """

    name = "reddit"

    def publish(self, item: ContentItem) -> PublishResult:
        subreddit = self.cfg.extra.get("subreddit", "")
        if not self.live or not subreddit:
            return self._result(item, live=False, detail="reddit disabled/uncredentialed (dry run)")
        try:
            resp = self._post(
                "https://oauth.reddit.com/api/submit",
                headers={"Authorization": f"Bearer {self.cfg.token}", "User-Agent": "DraftMasterAI/1.0"},
                data={"sr": subreddit, "kind": "self", "title": item.title[:300], "text": item.body},
            )
            ok = resp.status_code < 300
            return self._result(
                item,
                live=True,
                external_id=str(resp.status_code),
                detail="posted" if ok else f"reddit returned {resp.status_code}: {resp.text[:200]}",
            )
        except httpx.HTTPError as exc:
            return PublishResult(item.item_id, self.name, ok=False, live=True, detail=str(exc))


# Registry: name -> class. Adding a channel is a one-line entry.
CHANNELS: dict[str, type[Channel]] = {
    "blog": BlogChannel,
    "discord": DiscordChannel,
    "telegram": TelegramChannel,
    "twitter": TwitterChannel,
    "reddit": RedditChannel,
}


def build_channels(settings: GrowthConfig) -> dict[str, Channel]:
    """Instantiate every known channel with its configured credentials."""
    out: dict[str, Channel] = {}
    for name, cls in CHANNELS.items():
        out[name] = cls(settings.channel(name), settings)
    return out
