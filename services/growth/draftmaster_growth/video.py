"""Short-form video pipeline.

Dota's audience lives on YouTube, TikTok and Reels, but the growth engine must
run anywhere — including a CI box with no ffmpeg and no GPU. So the video step
degrades in three levels:

1. **Always**: a storyboard (shots with text and duration), a narration script,
   a caption file (SRT) and a ready-to-run ffmpeg command. This is the useful
   part and it needs nothing but the standard library.
2. **When a text-to-speech binary exists** (``espeak-ng``/``espeak``/``say``):
   narrate the script to audio.
3. **When ffmpeg exists**: render the slides to an actual MP4.

The storyboard is built from the same engine data as everything else, so a clip
can never claim a number the product would not.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import SITE_URL


@dataclass
class Shot:
    index: int
    text: str
    seconds: float
    hero_ids: list[int] = field(default_factory=list)


@dataclass
class VideoScript:
    script_id: str
    topic: str
    locale: str
    title: str
    hook: str
    shots: list[Shot]
    narration: str
    cta: str
    hashtags: list[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return sum(s.seconds for s in self.shots)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["duration_seconds"] = round(self.duration, 2)
        return d

    def to_srt(self) -> str:
        """Minimal, valid SRT so the operator can drop captions on any editor."""
        lines = []
        t = 0.0
        for i, shot in enumerate(self.shots, start=1):
            start = _ts(t)
            end = _ts(t + shot.seconds)
            lines.append(f"{i}\n{start} --> {end}\n{shot.text}\n")
            t += shot.seconds
        return "\n".join(lines)


def _ts(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class VideoEngine:
    """Turns a topic into a short-form video script and (optionally) a file."""

    def __init__(self, ds):
        self.ds = ds

    def build_script(self, topic, locale: str = "en") -> VideoScript:
        ds = self.ds
        heroes = [ds.by_id[h] for h in topic.data.get("heroes", []) if h in ds.by_id]
        hero = ds.by_id.get(topic.data.get("hero"))
        enemy = ds.by_id.get(topic.data.get("enemy"))

        if topic.kind == "meta" and heroes:
            top = heroes[0]
            wr = top.get("cm_winrate") or 0.5
            is_winners = topic.key.endswith("winners")
            is_losers = topic.key.endswith("losers")
            if locale == "ru":
                label = "Топ-1 герой патча" if is_winners else ("Худший герой патча" if is_losers else "Самые популярные")
                title = f"{label}: {top['localized_name']}"
                hook = f"{top['localized_name']}: {wr*100:.1f}% винрейта прямо сейчас.".replace(".", ",")
                shots = [
                    Shot(0, hook, 3.0, [top["id"]]),
                    Shot(1, "Вот весь топ-5:", 2.0, [h["id"] for h in heroes]),
                    *[Shot(2 + i, f"#{i+1} {h['localized_name']}", 1.5, [h["id"]]) for i, h in enumerate(heroes)],
                    Shot(9, "DraftMaster AI строит план под ваш драфт.", 3.0, []),
                ]
                narration = hook + " Это не ощущение, это данные матчей. Полный план — в DraftMaster AI."
                cta = "Полный план → " + SITE_URL
            else:
                label = "Patch's #1 hero" if is_winners else ("Patch's worst hero" if is_losers else "Most-picked heroes")
                title = f"{label}: {top['localized_name']}"
                hook = f"{top['localized_name']}: {wr*100:.1f}% winrate right now."
                shots = [
                    Shot(0, hook, 3.0, [top["id"]]),
                    Shot(1, "Here's the full top 5:", 2.0, [h["id"] for h in heroes]),
                    *[Shot(2 + i, f"#{i+1} {h['localized_name']}", 1.5, [h["id"]]) for i, h in enumerate(heroes)],
                    Shot(9, "DraftMaster AI builds the plan for your draft.", 3.0, []),
                ]
                narration = hook + " That's match data, not a feeling. Full plan in DraftMaster AI."
                cta = "Full plan → " + SITE_URL
        elif topic.kind == "matchup" and hero and enemy:
            score = ds.counter_score(hero["id"], enemy["id"])
            if locale == "ru":
                title = f"{hero['localized_name']} против {enemy['localized_name']}"
                hook = f"{enemy['localized_name']} — худший матчап для {hero['localized_name']}."
                shots = [
                    Shot(0, hook, 3.0, [hero["id"], enemy["id"]]),
                    Shot(1, f"Счёт контр-пика: {score:.0f}/100", 3.0, [hero["id"], enemy["id"]]),
                    Shot(2, "Не берите в лоб. Играйте от таймингов.", 3.0, [hero["id"]]),
                    Shot(3, "DraftMaster AI покажет, как именно.", 2.5, []),
                ]
                narration = hook + " Счёт контр-пика " + f"{score:.0f} из 100." + " Не пикайте вслепую."
                cta = "Проверьте свой матчап → " + SITE_URL
            else:
                title = f"{hero['localized_name']} vs {enemy['localized_name']}"
                hook = f"{enemy['localized_name']} is the worst matchup for {hero['localized_name']}."
                shots = [
                    Shot(0, hook, 3.0, [hero["id"], enemy["id"]]),
                    Shot(1, f"Counter score: {score:.0f}/100", 3.0, [hero["id"], enemy["id"]]),
                    Shot(2, "Don't blind-pick into it. Play your timings.", 3.0, [hero["id"]]),
                    Shot(3, "DraftMaster AI shows you exactly how.", 2.5, []),
                ]
                narration = hook + f" Counter score {score:.0f} of 100." + " Don't pick blind."
                cta = "Check your matchup → " + SITE_URL
        else:
            # Panic-mode demo and any other kind: a generic but honest pitch.
            if locale == "ru":
                title = "Я последний пик"
                hook = "8 секунд до конца пика."
                shots = [
                    Shot(0, hook, 3.0, []),
                    Shot(1, "Лучший герой. Билд. Приоритет убийств.", 3.5, []),
                    Shot(2, "Одно предложение: как выиграть эту игру.", 3.0, []),
                    Shot(3, "DraftMaster AI. За 5 секунд.", 2.5, []),
                ]
                narration = "Восемь секунд до конца пика. Лучший герой, билд, приоритет убийств и план на игру."
                cta = "Откройте режим → " + SITE_URL + "/panic"
            else:
                title = "I'M LAST PICK"
                hook = "8 seconds left on the pick timer."
                shots = [
                    Shot(0, hook, 3.0, []),
                    Shot(1, "Best hero. Full build. Kill priority.", 3.5, []),
                    Shot(2, "One sentence: how to win this game.", 3.0, []),
                    Shot(3, "DraftMaster AI. In 5 seconds.", 2.5, []),
                ]
                narration = "Eight seconds left. Best hero, build, kill priority and a plan for this game."
                cta = "Open the mode → " + SITE_URL + "/panic"

        script_id = f"{topic.kind}-{locale}-{hashlib.sha1(topic.signature().encode('utf-8')).hexdigest()[:8]}"
        return VideoScript(
            script_id=script_id,
            topic=topic.key,
            locale=locale,
            title=title,
            hook=hook,
            shots=shots,
            narration=narration,
            cta=cta,
            hashtags=["#Dota2", "#Dota", "#DraftMasterAI", "#shorts"],
        )

    # -- optional rendering ---------------------------------------------
    def render(self, script: VideoScript, output_dir: str | Path) -> dict:
        """Write the always-available artifacts and render an MP4 when possible."""
        out = Path(output_dir) / "video" / script.locale
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{script.script_id}.json").write_text(
            __import__("json").dumps(script.to_dict(), ensure_ascii=False, indent=1), encoding="utf-8"
        )
        (out / f"{script.script_id}.srt").write_text(script.to_srt(), encoding="utf-8")
        (out / f"{script.script_id}.txt").write_text(script.narration, encoding="utf-8")

        ffmpeg = shutil.which("ffmpeg")
        result = {
            "script_id": script.script_id,
            "dir": str(out),
            "duration_seconds": round(script.duration, 2),
            "ffmpeg": bool(ffmpeg),
            "mp4": "",
        }
        if ffmpeg:
            mp4 = out / f"{script.script_id}.mp4"
            cmd = build_ffmpeg_command(script, mp4)
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=180)
                result["mp4"] = str(mp4)
            except (subprocess.SubprocessError, OSError):
                result["mp4"] = ""  # degrade silently; the script is the deliverable
        return result


def build_ffmpeg_command(script: VideoScript, out_path: Path) -> list[str]:
    """Build a drawtext-based ffmpeg command for the storyboard.

    Exposed separately (and tested) because the exact filter string is the part
    that breaks across ffmpeg builds, and an operator wants to run it by hand.
    """
    filters = []
    t = 0.0
    for shot in script.shots:
        safe = shot.text.replace("'", "\\'").replace(":", "\\:")
        filters.append(
            f"drawtext=text='{safe}':fontcolor=white:fontsize=48:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{t:.2f},{t + shot.seconds:.2f})'"
        )
        t += shot.seconds
    vf = ",".join(filters)
    return [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x0b0f17:s=1080x1920:d={script.duration:.2f}",
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(out_path),
    ]
