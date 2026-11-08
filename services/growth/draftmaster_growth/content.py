"""Content generation.

Deterministic, data-driven, bilingual. Every number a post contains comes from
the strategy dataset — the same rule the product's engine follows. The engine
renders a :class:`Topic` into a :class:`ContentItem` under a chosen *variant*
(style), which is what the optimizer experiments with.

Templates are plain functions, one per (kind, locale), so adding a format is
adding a function and a registry entry rather than editing a template string.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from .config import SITE_URL
from .models import ContentItem
from .topics import Topic

# The style variants the optimizer chooses between. Each is a small knob set the
# renderers honour, so a new variant only has to declare what it changes.
VARIANTS: dict[str, dict] = {
    "hook-first": {
        "description": "Punchy one-line hook, then the payload.",
        "opener": "hook",
        "cta": "Play the draft, not the hero.",
    },
    "data-led": {
        "description": "Lead with the statistic, then explain it.",
        "opener": "stat",
        "cta": "The numbers are public — the plan is the product.",
    },
    "question": {
        "description": "Open with a question the reader answers in their head.",
        "opener": "question",
        "cta": "What would you have picked?",
    },
    "listicle": {
        "description": "Numbered, scannable.",
        "opener": "list",
        "cta": "Save this for your next draft.",
    },
    "story": {
        "description": "A short narrative frame around the data.",
        "opener": "story",
        "cta": "Draft it, then tell me I'm wrong.",
    },
}

DEFAULT_VARIANT = "hook-first"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _item_id(kind: str, topic: Topic, variant: str) -> str:
    raw = f"{kind}|{topic.signature()}|{variant}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _pct(x: float | None) -> str:
    if x is None:
        return "n/a"
    return f"{x * 100:.1f}%"


def _pct_ru(x: float | None) -> str:
    if x is None:
        return "н/д"
    # Russian convention uses a comma as the decimal separator.
    return f"{x * 100:.1f}%".replace(".", ",")


class ContentEngine:
    """Renders topics into publishable items."""

    def __init__(self, ds):
        self.ds = ds
        self.by_id = ds.by_id

    # -- helpers ---------------------------------------------------------
    def _hero(self, hero_id: int) -> dict:
        return self.by_id[hero_id]

    def _name(self, hero_id: int) -> str:
        return self._hero(hero_id)["localized_name"]

    def _links(self, path: str = "") -> dict[str, str]:
        base = SITE_URL.rstrip("/")
        return {"site": base + path, "home": base}

    def _hashtags(self, *extra: str) -> list[str]:
        base = ["#Dota2", "#Dota", "#DraftMasterAI"]
        return base + [e for e in extra if e]

    # -- public API ------------------------------------------------------
    def render(self, topic: Topic, variant: str = DEFAULT_VARIANT, channel: str = "blog") -> ContentItem:
        style = VARIANTS.get(variant, VARIANTS[DEFAULT_VARIANT])
        renderer = RENDERERS.get((topic.kind, topic.locale))
        if renderer is None:
            renderer = RENDERERS[(topic.kind, "en")]
        title, body, media, links = renderer(self, topic, style)
        return ContentItem(
            item_id=_item_id(topic.kind, topic, variant),
            kind="post" if topic.kind in {"meta", "matchup", "panic"} else topic.kind,
            topic=topic.key,
            signature=topic.signature(),
            title=title,
            body=body,
            locale=topic.locale,
            variant=variant,
            channel=channel,
            hashtags=self._hashtags("#Patch" if topic.kind == "meta" else ""),
            media=media,
            links=links,
            created_at=_now_iso(),
        )


# --------------------------------------------------------------------------
# Openers — shared across renderers so a variant changes the *frame*, not the
# facts.
# --------------------------------------------------------------------------
def _open_en(style: dict, stat: str, question: str) -> str:
    kind = style.get("opener")
    if kind == "stat":
        return f"{stat}\n\n"
    if kind == "question":
        return f"{question}\n\n"
    if kind == "list":
        return ""
    if kind == "story":
        return ""
    return f"{stat}\n\n"  # hook-first: the stat *is* the hook


def _open_ru(style: dict, stat: str, question: str) -> str:
    kind = style.get("opener")
    if kind == "stat":
        return f"{stat}\n\n"
    if kind == "question":
        return f"{question}\n\n"
    return f"{stat}\n\n"


def _cta_en(style: dict, links: dict) -> str:
    return f"\n\n{style.get('cta', '')} → {links['home']}"


def _cta_ru(style: dict, links: dict) -> str:
    cta = {
        "hook-first": "Играйте драфт, а не героя.",
        "data-led": "Цифры открыты — продукт это план.",
        "question": "А что выбрали бы вы?",
        "listicle": "Сохраните это к следующему драфту.",
        "story": "Соберите драфт и попробуйте меня опровергнуть.",
    }
    return f"\n\n{cta.get(style.get('opener', 'hook-first'), '')} → {links['home']}"


# --------------------------------------------------------------------------
# Renderers
# --------------------------------------------------------------------------
def _render_meta(engine: ContentEngine, topic: Topic, style: dict, locale: str):
    ds = engine.ds
    heroes = [engine._hero(h) for h in topic.data["heroes"]]
    links = engine._links("/meta")
    is_winners = topic.key.endswith("winners")
    is_losers = topic.key.endswith("losers")

    if locale == "ru":
        label = "Победители патча" if is_winners else "Проигравшие патча" if is_losers else "Самые популярные"
        stat = f"{label}: {heroes[0]['localized_name']} — {_pct_ru(heroes[0].get('cm_winrate'))} винрейта."
        question = "Знаете, кто сейчас выигрывает драфты больше всех?"
        lines = [f"• {h['localized_name']} — {_pct_ru(h.get('cm_winrate'))}" for h in heroes]
        body = _open_ru(style, stat, question) + "\n".join(lines) + _cta_ru(style, links)
        title = f"{label} — патч {ds.patch.get('name', '')}".strip()
    else:
        label = "Patch winners" if is_winners else "Patch losers" if is_losers else "Most-picked heroes"
        stat = f"{label}: {heroes[0]['localized_name']} sits at {_pct(heroes[0].get('cm_winrate'))} winrate."
        question = "Who is actually winning drafts this patch?"
        lines = [f"• {h['localized_name']} — {_pct(h.get('cm_winrate'))}" for h in heroes]
        body = _open_en(style, stat, question) + "\n".join(lines) + _cta_en(style, links)
        title = f"{label} — patch {ds.patch.get('name', '')}".strip()

    media = {"hero_ids": [h["id"] for h in heroes], "hero_names": [h["localized_name"] for h in heroes]}
    return title, body, media, links


def _render_matchup(engine: ContentEngine, topic: Topic, style: dict, locale: str):
    hero = engine._hero(topic.data["hero"])
    enemy = engine._hero(topic.data["enemy"])
    score = engine.ds.counter_score(topic.data["hero"], topic.data["enemy"])
    links = engine._links(f"/counter/{hero['localized_name'].lower().replace(' ', '-')}")

    if locale == "ru":
        stat = f"{enemy['localized_name']} — худший матчап для {hero['localized_name']} ({score:.0f}/100)."
        question = f"Почему {hero['localized_name']} проигрывает {enemy['localized_name']}?"
        body = (
            _open_ru(style, stat, question)
            + f"Счёт контр-пика {score:.0f} из 100 — это реальная разница по данным матчей, "
            f"а не ощущение.\n\n"
            f"Что делать: не берите {hero['localized_name']} в этот матчап, "
            f"если у вас есть выбор. Если уже взяли — играйте от фарма и ждите свои тайминги, "
            f"а не разменивайтесь в лоб."
            + _cta_ru(style, links)
        )
        title = f"{hero['localized_name']} против {enemy['localized_name']}: разбор матчапа"
    else:
        stat = f"{enemy['localized_name']} is the worst matchup for {hero['localized_name']} ({score:.0f}/100)."
        question = f"Why does {hero['localized_name']} lose to {enemy['localized_name']}?"
        body = (
            _open_en(style, stat, question)
            + f"The counter score is {score:.0f} out of 100 — that is measured across real matches, "
            f"not a vibe.\n\n"
            f"What to do: do not blind-pick {hero['localized_name']} into this, and if you are already "
            f"in it, play for your own timings instead of trading straight up."
            + _cta_en(style, links)
        )
        title = f"{hero['localized_name']} vs {enemy['localized_name']}: the matchup breakdown"

    media = {"hero_ids": [hero["id"], enemy["id"]], "hero_names": [hero["localized_name"], enemy["localized_name"]]}
    return title, body, media, links


def _render_guide(engine: ContentEngine, topic: Topic, style: dict, locale: str):
    hero = engine._hero(topic.data["hero"])
    build = engine.ds.hero_builds.get(hero["id"], {})
    top_early = _top_items(engine, build.get("early_game", {}), 3)
    links = engine._links(f"/hero/{hero['localized_name'].lower().replace(' ', '-')}")

    if locale == "ru":
        stat = f"{hero['localized_name']}: {_pct_ru(hero.get('cm_winrate'))} винрейта на текущем патче."
        question = f"Как играть за {hero['localized_name']} в этой мете?"
        items = ", ".join(top_early) if top_early else "по ситуации"
        body = (
            _open_ru(style, stat, question)
            + f"Ранняя игра обычно строится вокруг: {items}.\n\n"
            f"Дальше важны тайминги, а не шаблонный билд — DraftMaster AI подбирает предметы "
            f"под конкретный вражеский драфт, а не по дефолтному гайду."
            + _cta_ru(style, links)
        )
        title = f"Гайд: {hero['localized_name']} в патче {engine.ds.patch.get('name', '')}".strip()
    else:
        stat = f"{hero['localized_name']}: {_pct(hero.get('cm_winrate'))} winrate this patch."
        question = f"How do you actually play {hero['localized_name']} right now?"
        items = ", ".join(top_early) if top_early else "situational"
        body = (
            _open_en(style, stat, question)
            + f"Early game usually builds around: {items}.\n\n"
            f"After that it is about timings, not a fixed build — DraftMaster AI generates the item "
            f"list from the enemy draft instead of a default guide."
            + _cta_en(style, links)
        )
        title = f"Guide: {hero['localized_name']} on patch {engine.ds.patch.get('name', '')}".strip()

    media = {"hero_ids": [hero["id"]], "hero_names": [hero["localized_name"]]}
    return title, body, media, links


def _render_panic(engine: ContentEngine, topic: Topic, style: dict, locale: str):
    hero = engine._hero(topic.data["hero"])
    enemy = engine._hero(topic.data["enemy"])
    links = engine._links("/panic")
    if locale == "ru":
        stat = f"8 секунд до конца пика. Враг взял {enemy['localized_name']}. Что брать?"
        question = "Что делать, когда таймер пика уже горит?"
        body = (
            _open_ru(style, stat, question)
            + "Режим «Я последний пик» отвечает за секунды: лучший герой, билд, "
            "приоритет убийств и одно предложение — как выиграть именно эту игру."
            + _cta_ru(style, links)
        )
        title = "Я последний пик: как выиграть драфт за 5 секунд"
    else:
        stat = "8 seconds left on the pick timer. They picked " + enemy["localized_name"] + "."
        question = "What do you do when the pick timer is already burning?"
        body = (
            _open_en(style, stat, question)
            + "Panic Mode answers in seconds: the best hero, the build, the kill priority, and one "
            "sentence that tells you how to win this exact game."
            + _cta_en(style, links)
        )
        title = "I'M LAST PICK: win the draft in 5 seconds"
    media = {"hero_ids": [hero["id"], enemy["id"]], "hero_names": [hero["localized_name"], enemy["localized_name"]]}
    return title, body, media, links


def _top_items(engine: ContentEngine, pop: dict, n: int) -> list[str]:
    """Turn an item-popularity dict (item_id -> share) into display names."""
    if not pop:
        return []
    ranked = sorted(pop.items(), key=lambda kv: -kv[1])[:n]
    out = []
    for item_id, _share in ranked:
        try:
            item = engine.ds.items_by_id.get(int(item_id))
        except (TypeError, ValueError):
            item = None
        if item:
            out.append(item.get("dname") or item.get("key") or str(item_id))
    return out


def _meta_renderer(locale: str):
    def fn(engine, topic, style):
        return _render_meta(engine, topic, style, locale)

    return fn


def _matchup_renderer(locale: str):
    def fn(engine, topic, style):
        return _render_matchup(engine, topic, style, locale)

    return fn


def _guide_renderer(locale: str):
    def fn(engine, topic, style):
        return _render_guide(engine, topic, style, locale)

    return fn


def _panic_renderer(locale: str):
    def fn(engine, topic, style):
        return _render_panic(engine, topic, style, locale)

    return fn


RENDERERS = {
    ("meta", "en"): _meta_renderer("en"),
    ("meta", "ru"): _meta_renderer("ru"),
    ("matchup", "en"): _matchup_renderer("en"),
    ("matchup", "ru"): _matchup_renderer("ru"),
    ("guide", "en"): _guide_renderer("en"),
    ("guide", "ru"): _guide_renderer("ru"),
    ("panic", "en"): _panic_renderer("en"),
    ("panic", "ru"): _panic_renderer("ru"),
}
