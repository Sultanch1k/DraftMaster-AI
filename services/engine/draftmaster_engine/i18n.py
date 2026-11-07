"""Localisation of engine-generated prose.

The engine is deliberately language-neutral: it produces English sentences from
real data. This module translates those sentences at the API boundary, so the
strategy core stays pure and deterministic while the product speaks the user's
language.

Two lookups are used, in order:

1. an exact-match table for the fixed sentences the engine emits, and
2. ordered regex patterns for sentences that embed data (hero names, item
   names, percentages, level numbers).

Anything unmatched is returned unchanged. That is intentional: an untranslated
English sentence is a cosmetic gap, whereas a wrong translation of a number or
a hero name is a correctness bug.

Hero and item names stay in English on purpose — that is the convention in
every Dota 2 community, and localising them would make the UI harder to read for
the players who use it.
"""
from __future__ import annotations

import re
from typing import Any

SUPPORTED = ("en", "ru")
DEFAULT = "en"


def normalize_locale(value: str | None) -> str:
    """Map an arbitrary locale tag ('ru-RU', 'ru', 'en-GB') to a supported code."""
    if not value:
        return DEFAULT
    base = value.split(",")[0].split(";")[0].strip().lower().replace("_", "-")
    base = base.split("-")[0]
    return base if base in SUPPORTED else DEFAULT


# ---------------------------------------------------------------------------
# Exact-match catalogue
# ---------------------------------------------------------------------------

RU_EXACT: dict[str, str] = {
    # --- scoring: pick reasons ------------------------------------------
    "Should win or go even in the lane against this lineup.": (
        "Должен выиграть или отыграть лейн вровень против этого состава."
    ),
    "⚠ Loses the likely lane matchup — plan to rotate early or bring a lane partner.": (
        "⚠ Проигрывает вероятный мап-ап на линии — планируйте раннюю ротацию или возьмите партнёра на лейн."
    ),
    "High comfort pick for you, so you will execute the plan reliably.": (
        "Комфортный для вас пик — план вы отыграете уверенно."
    ),
    "Pairs well with your allied draft.": "Хорошо сочетается с драфтом союзников.",
    "⚠ Mechanically demanding in a fight-heavy game — only pick if you are comfortable.": (
        "⚠ Требует механики в игре с постоянными замесами — берите, только если уверены в себе."
    ),
    "Brings crowd control this enemy draft has to respect in every fight.": (
        "Даёт контроль, с которым драфт врага вынужден считаться в каждом замесе."
    ),
    "Solid all-round pick with no glaring weakness into this draft.": (
        "Крепкий универсальный пик без явных слабостей против этого драфта."
    ),
    # --- plan: skill build ----------------------------------------------
    "Ultimate comes online — this is your fight-winning button.": (
        "Ульта становится доступна — это ваш козырь для победы в замесах."
    ),
    "All abilities are maxed — take stats to scale damage, HP and mana.": (
        "Все способности прокачаны — берите статы для роста урона, здоровья и маны."
    ),
    "Primary ability — max it first for lane pressure and kills.": (
        "Основная способность — качайте её первой для давления на линии и убийств."
    ),
    "Secondary ability — a second damage source or key utility.": (
        "Вторая способность — дополнительный источник урона или ключевая полезность."
    ),
    "Fill remaining points once the core abilities are maxed.": (
        "Добивайте оставшиеся очки, когда ключевые способности прокачаны."
    ),
    "No ability data available for this hero.": "Нет данных о способностях этого героя.",
    "Adaptation: enemy magic burst is high — level any defensive or buff ability earlier than this greedy order.": (
        "Адаптация: у врага много магического бурста — качайте защитную или бафф-способность раньше, чем в этом жадном порядке."
    ),
    "Adaptation: prioritise your AoE damage ability to clear illusions and summons.": (
        "Адаптация: приоритет — способность с уроном по площади для зачистки иллюзий и призывов."
    ),
    "Adaptation: physical-heavy enemy — value survivability talents and stats over damage.": (
        "Адаптация: у врага много физического урона — выбирайте таланты и статы на выживаемость, а не на урон."
    ),
    "Adaptation: expect lock-down chains — keep a defensive item, not a greedy skill order.": (
        "Адаптация: ожидайте цепочки контроля — держите защитный предмет и не жадничайте с прокачкой."
    ),
    # --- plan: talents ---------------------------------------------------
    "Enemy draft deals heavy burst — take the survivability talent to live through the first combo.": (
        "Драфт врага наносит много бурст-урона — берите талант на выживаемость, чтобы пережить первую комбинацию."
    ),
    "Offensive value: this talent directly increases your damage or uptime in fights.": (
        "Атакующая ценность: талант напрямую увеличивает ваш урон или время активности в замесах."
    ),
    "Highest-value option at this tier for a standard build.": (
        "Самый ценный вариант на этом уровне для стандартной сборки."
    ),
    # --- plan: target priority fragments --------------------------------
    "directly counters your hero": "напрямую контрит вашего героя",
    "chains disables onto you": "складывает контроль на вас",
    "is an enemy core who wins the late game": "керри врага, который выигрывает позднюю игру",
    "kill this one first in every fight": "убивайте первым в каждом замесе",
    "lowest priority — ignore unless free": "низший приоритет — игнорируйте, если не по пути",
    "standard focus priority": "обычный приоритет фокуса",
    # --- plan: power spikes ---------------------------------------------
    "Hero level": "Уровень героя",
    "Level 6 / 12 / 18": "Уровень 6 / 12 / 18",
    "Ultimate timing — the moment your kit becomes fully online.": (
        "Тайминг ульты — момент, когда ваш набор способностей полностью раскрывается."
    ),
    "Item": "Предмет",
    "Your first major item. Hit this timing and force a fight immediately.": (
        "Ваш первый ключевой предмет. Выйдите на тайминг и сразу навяжите бой."
    ),
    "Draft": "Драфт",
    "Late game (35m+)": "Поздняя игра (35+ мин)",
    "Your win rate rises with game length — you scale.": (
        "Ваш винрейт растёт с длиной игры — вы скейлитесь."
    ),
    "0-25m": "0–25 мин",
    "You fall off late — win before the clock turns.": (
        "Вы проседаете в поздней игре — заканчивайте матч раньше."
    ),
    "Teamfight": "Замес",
    "First BKB / ultimate item": "Первый BKB / ультимейт-предмет",
    "You can now survive the enemy's first combo and fight back.": (
        "Теперь вы переживаете первую комбинацию врага и можете дать сдачи."
    ),
    "Objective": "Цель",
    "First Roshan / Aegis": "Первый Рошан / Эгида",
    "Convert a won fight into a tower and Roshan, not a base dive.": (
        "Превращайте выигранный бой в башню и Рошана, а не в заход на базу."
    ),
    "Avoid fighting them around this window unless you are ahead.": (
        "Не ввязывайтесь в драку в это окно, если вы не впереди."
    ),
    # --- plan: match phases ---------------------------------------------
    "Laning": "Лейнинг",
    "Early mid-game": "Ранний мидгейм",
    "Mid-game": "Мидгейм",
    "Late mid-game": "Поздний мидгейм",
    "Late game": "Лейтгейм",
    "Secure your lane, hit your level 6 power spike": (
        "Закрепитесь на линии, выйдите на силовой спайк 6-го уровня"
    ),
    "Contest the 4/6/8 minute runes if safe": "Боритесь за руны на 4/6/8 минуте, если это безопасно",
    "Prioritise last hits and denies; a 40+ last-hit lane is a won lane.": (
        "Приоритет — добивания и денаи; лейн с 40+ добиваниями уже выигран."
    ),
    "Only fight if the enemy overextends into your tower or a support rotates.": (
        "Деритесь только если враг заходит под вашу башню или саппорт приходит на ротацию."
    ),
    "Stay on your half of the map; ward your jungle entrance.": (
        "Оставайтесь на своей половине карты; вардите вход в свой лес."
    ),
    "Take the enemy safelane tower only if you win the lane hard.": (
        "Забирайте башню на лёгкой линии врага только при уверенной победе на линии."
    ),
    "Do not attempt Roshan — you lack the damage and sustain.": (
        "Не идите на Рошана — вам не хватает урона и выживаемости."
    ),
    "Enemy jungle at night": "Лес врага ночью",
    "Rune fights if enemy has level-1 kill threat": (
        "Драки за руны, если у врага есть угроза убийства на 1-м уровне"
    ),
    "Convert your first item into a tower": "Превратите первый предмет в башню",
    "Take T1 towers on the side lanes": "Забирайте башни T1 на боковых линиях",
    "Farm towards your first major item; take ancient stacks if available.": (
        "Фармите к первому ключевому предмету; берите стаки асиентов, если есть."
    ),
    "Fight when your ultimate and first item are both up.": (
        "Деритесь, когда готова ульта и первый предмет."
    ),
    "Rotate with your team after every won fight; do not farm alone into a push draft.": (
        "Ротируйтесь с командой после каждого выигранного боя; не фармите в одиночку против пуш-драфта."
    ),
    "T1 towers first, T2 only with Aegis or a big man advantage.": (
        "Сначала башни T1, T2 — только с Эгидой или большим численным перевесом."
    ),
    "Scout Roshan if you have a hero who can solo it; otherwise wait for a won fight.": (
        "Проверяйте Рошана, если есть герой, способный убить его в одиночку; иначе ждите выигранного боя."
    ),
    "Deep enemy jungle without vision": "Глубоко в лесу врага без вижена",
    "High ground fights you do not need": "Хайграунд-бои, которые вам не нужны",
    "Group and take T2 towers": "Соберитесь и заберите башни T2",
    "First Roshan is the objective that wins this phase": (
        "Первый Рошан — цель, которая выигрывает эту стадию"
    ),
    "Farm the enemy jungle after won fights, not your own — starve them.": (
        "Фармите лес врага после выигранных боев, а не свой — лишайте их золота."
    ),
    "Force fights around Aegis and your key item timings.": (
        "Навязывайте бои вокруг Эгиды и таймингов ваших ключевых предметов."
    ),
    "Move as 5 with Aegis; pick off anyone who splits.": (
        "Идите впятером с Эгидой; убивайте любого, кто отделился."
    ),
    "Take T2 towers, then the T3 on the weakest lane.": (
        "Заберите башни T2, затем T3 на самой слабой линии."
    ),
    "Take Roshan the moment you win a fight near the pit.": (
        "Идите на Рошана сразу, как выиграете бой рядом с ямой."
    ),
    "Enemy high ground without Aegis": "Хайграунд врага без Эгиды",
    "Fighting inside enemy base with no buyback": "Бой на базе врага без байбека",
    "Break the barracks": "Сломайте бараки",
    "Second Roshan for the high-ground push": "Второй Рошан для захода на хайграунд",
    "Keep lanes pushed out before every fight; never lose map control.": (
        "Держите линии запушенными перед каждым боем; не теряйте контроль над картой."
    ),
    "Only take fights you start, with Aegis, or after a pickoff.": (
        "Вступайте только в бои, которые начинаете сами, с Эгидой или после пикоффа."
    ),
    "Hold vision around Roshan and the enemy triangle.": (
        "Держите вижен у Рошана и в треугольнике врага."
    ),
    "Take T3s on the lane where you have Aegis and buybacks.": (
        "Забирайте T3 на той линии, где у вас есть Эгида и байбеки."
    ),
    "Second Roshan is mandatory before high ground.": (
        "Второй Рошан обязателен перед заходом на хайграунд."
    ),
    "High ground without Aegis + buybacks": "Хайграунд без Эгиды и байбеков",
    "Chasing kills into their fountain area": "Погоня за убийствами к их фонтану",
    "Close the game with Aegis and buybacks": "Закрывайте игру с Эгидой и байбеками",
    "Take barracks, then throne": "Сначала бараки, затем трон",
    "Sell early items for a final luxury upgrade; keep buyback gold.": (
        "Продайте ранние предметы ради финального апгрейда; держите золото на байбек."
    ),
    "Fight only with full ultimates, Aegis and buybacks available.": (
        "Деритесь только с готовыми ультами, Эгидой и байбеками."
    ),
    "Push as 5 with vision; never split alone in the enemy half.": (
        "Пушите впятером с виженом; не отделяйтесь в одиночку на половине врага."
    ),
    "Take the throne in one push, not two half-hearted attempts.": (
        "Заберите трон одним пушем, а не двумя вялыми попытками."
    ),
    "Third Roshan if the game goes this long.": "Третий Рошан, если игра затянется так долго.",
    "Any fight without buyback": "Любой бой без байбека",
    "Defending with 2+ heroes dead": "Защита, когда погибли 2+ героя",
    # --- plan: win conditions -------------------------------------------
    "Do not take 5v5 fights on even terms; win with tempo, split push and pickoffs.": (
        "Не играйте 5 на 5 на равных; побеждайте темпом, сплитпушем и пикоффами."
    ),
    "Group early, take Roshan off your first won fight, and convert Aegis into a tower.": (
        "Соберитесь рано, заберите Рошана после первого выигранного боя и превратите Эгиду в башню."
    ),
    "Force the enemy's key disables out before committing; then re-engage.": (
        "Выманите ключевой контроль врага до захода в бой, затем переиграйте."
    ),
    "Buy anti-heal (Spirit Vessel/Skadi) before the first big teamfight.": (
        "Купите анти-хил (Spirit Vessel/Skadi) перед первым крупным замесом."
    ),
    "Answer split push with one mobile hero — never send your whole team.": (
        "Отвечайте на сплитпуш одним мобильным героем — не отправляйте всю команду."
    ),
    "Close before 35 minutes; the clock favours the enemy draft.": (
        "Закрывайте игру до 35 минут; время играет на драфт врага."
    ),
    "Play around Roshan timings and force fights with Aegis advantage.": (
        "Играйте вокруг таймингов Рошана и навязывайте бои с преимуществом Эгиды."
    ),
    "If you lose a fight, do not contest the follow-up objective — trade a tower instead.": (
        "Проиграли бой — не боритесь за следующую цель, обменяйте её на башню."
    ),
    "If the enemy takes Roshan, farm defensively and wait for their Aegis to expire before fighting.": (
        "Если враг забрал Рошана, фармите оборонительно и дождитесь окончания их Эгиды перед боем."
    ),
    "If you fall behind, farm the triangle, take safe pickoffs, and force high-ground defence.": (
        "Если отстаёте, фармите треугольник, делайте безопасные пикоффы и заставляйте врага идти на хайграунд."
    ),
    # --- items -----------------------------------------------------------
    "Standard opening for this hero (no per-hero data available).": (
        "Стандартное начало для этого героя (нет данных по герою)."
    ),
    "Instantly becomes immune to physical damage — press it the moment the enemy commits.": (
        "Мгновенно даёт иммунитет к физическому урону — жмите в момент захода врага."
    ),
    "On-demand magic resistance + invisibility to break a burst combo.": (
        "Магическое сопротивление и невидимость по требованию, чтобы разорвать бурст-комбинацию."
    ),
    "Auto-triggers a dispel + shield the instant you drop below 70% HP.": (
        "Автоматически даёт диспел и щит, как только здоровье падает ниже 70%."
    ),
    "If the game turns into one big teamfight, BKB is the only reliable answer.": (
        "Если игра сводится к одному большому замесу, BKB — единственный надёжный ответ."
    ),
    "Lets you answer split push without giving up your own farm.": (
        "Позволяет отвечать на сплитпуш, не жертвуя своим фармом."
    ),
    "Cheapest way to convert an invisible pickoff into a kill.": (
        "Самый дешёвый способ превратить невидимый пикофф в убийство."
    ),
    # --- item counter rules (from the dataset) ---------------------------
    "Enemy draft stacks targeted disables; BKB/Aeon deny the chain that would kill you.": (
        "Драфт врага набирает одиночный контроль; BKB/Aeon разрывают цепочку, которая вас убивает."
    ),
    "Enemy deals most damage as magical burst; magic resistance and BKB are the cheapest survival.": (
        "Основной урон врага — магический бурст; магическое сопротивление и BKB — самый дешёвый способ выжить."
    ),
    "Enemy wins through physical DPS; armor and attack-slow cut their damage far more than HP.": (
        "Враг побеждает за счёт физического ДПС; броня и замедление атаки режут урон сильнее, чем здоровье."
    ),
    "Enemy relies on evasion; true strike removes their defensive layer entirely.": (
        "Враг полагается на уклонение; true strike полностью снимает этот защитный слой."
    ),
    "Illusions and summons are cleared by AoE, not single-target damage.": (
        "Иллюзии и призывы зачищаются уроном по площади, а не одиночными атаками."
    ),
    "Enemy out-sustains you; anti-heal converts their main strength into a weakness.": (
        "Враг переигрывает вас на отхиле; анти-хил превращает их силу в слабость."
    ),
    "Invisible threats are neutralised by detection and a disable that reveals.": (
        "Невидимых врагов нейтрализует детекция плюс контроль, который их раскрывает."
    ),
    "Enemy wants one clean teamfight combo; BKB plus a save item breaks the chain.": (
        "Враг хочет одну чистую комбинацию в замесе; BKB плюс сейв-предмет разрывают её."
    ),
    "Enemy kites you out of fights; mobility items restore your uptime.": (
        "Враг кайтит вас из боев; предметы на мобильность возвращают вам время в бою."
    ),
    "Silence locks your kit; a dispel restores your ability to fight.": (
        "Сайленс отключает ваши способности; диспел возвращает вас в игру."
    ),
    "Pure/burst damage ignores your resistances; raw HP plus BKB is the answer.": (
        "Чистый и бурст-урон игнорируют сопротивление; ответ — запас здоровья и BKB."
    ),
    "Enemy wins by split-pushing; you need global presence and fast wave clear.": (
        "Враг побеждает сплитпушем; вам нужны глобальное присутствие и быстрая зачистка волн."
    ),
    "Pure armor items do almost nothing against a magical-burst draft.": (
        "Чистая броня почти бесполезна против драфта с магическим бурстом."
    ),
    "Stacking more evasion does not answer an enemy that already ignores yours.": (
        "Ещё больше уклонения не поможет против врага, который и так его игнорирует."
    ),
    "Long-cooldown sustain items lose the attrition war to a healing draft.": (
        "Предметы на восстановление с большим откатом проигрывают войну на истощение драфту с лечением."
    ),
    "Single-target items cannot clear a board of illusions or summons.": (
        "Одиночные предметы не зачищают иллюзии и призывы."
    ),
    "Spell amplification does nothing when the enemy kills you with right clicks.": (
        "Усиление заклинаний не поможет, когда враг убивает вас обычными атаками."
    ),
    # --- win probability: verdicts --------------------------------------
    "Favoured draft — press your advantage with the plan below.": (
        "Драфт в вашу пользу — реализуйте преимущество по плану ниже."
    ),
    "Slight draft edge — play your win conditions cleanly.": (
        "Небольшое преимущество драфта — чисто отыграйте условия победы."
    ),
    "Coin-flip draft — execution and timings decide this game.": (
        "Равный драфт — исход решат исполнение и тайминги."
    ),
    "Slight draft deficit — you need to out-play the timings.": (
        "Небольшой дефицит драфта — нужно переиграть соперника на таймингах."
    ),
    "Draft is against you — win with tempo, split push and picks, not 5v5.": (
        "Драфт против вас — побеждайте темпом, сплитпушем и пикоффами, а не в 5 на 5."
    ),
    # --- win probability: factors ---------------------------------------
    "Hero matchups": "Мап-ап героев",
    "Shrunk head-to-head advantage across the enemy draft.": (
        "Усреднённое преимущество в личных мап-апах против драфта врага."
    ),
    "Meta strength": "Сила в мете",
    "Threat mismatch": "Несоответствие угроз",
    "Neither side gains a clear late-game edge.": (
        "Ни одна из сторон не имеет явного преимущества в поздней игре."
    ),
    "Your hero scales better late.": "Ваш герой сильнее в поздней игре.",
    "Enemy draft scales better late — close the game early.": (
        "Драфт врага сильнее в поздней игре — закрывайте игру раньше."
    ),
    "Game clock": "Тайминг игры",
    "Role fit": "Соответствие роли",
    "Execution reliability": "Надёжность исполнения",
    # --- coach ------------------------------------------------------------
    "Won the game and played your role well.": "Игра выиграна, и свою роль вы отыграли хорошо.",
    "Carried your role — this is a repeatable performance.": (
        "Вы вытащили свою роль — это повторяемый результат."
    ),
    "Solid game with clear, fixable leaks.": "Крепкая игра с понятными и исправимыми ошибками.",
    "Below your standard — focus on the two practice points below.": (
        "Ниже вашего уровня — сосредоточьтесь на двух пунктах практики ниже."
    ),
    "No standout strengths detected — work the practice plan.": (
        "Явных сильных сторон не найдено — отработайте план практики."
    ),
    "No critical mistakes detected at this level.": "Критических ошибок на этом уровне не найдено.",
    "Objective timing looks reasonable for this game length.": (
        "Тайминги по целям выглядят разумно для такой длины игры."
    ),
    "Very low tower damage — you are not converting won fights into objectives.": (
        "Очень малый урон по башням — вы не превращаете выигранные бои в цели."
    ),
    "Low hero damage per minute — you may be fighting too late or with the wrong items online.": (
        "Малый урон по героям в минуту — возможно, вы поздно вступаете в бои или у вас не те предметы."
    ),
    "Track your death timer: if you die twice to the same hero, buy a defensive item or change lanes.": (
        "Следите за таймером смертей: если умираете дважды от одного героя, купите защитный предмет или смените линию."
    ),
    "Review the replay at 2x and note every death: was it avoidable?": (
        "Пересмотрите реплей на 2x и отметьте каждую смерть: можно ли было её избежать?"
    ),
    "Practice farming patterns: keep two waves pushed, then rotate to jungle camps in a loop.": (
        "Отработайте паттерны фарма: держите две волны запушенными, затем по кругу уходите в лесные лагеря."
    ),
    "Set one concrete goal for your next game (e.g. 50 LH by 10:00).": (
        "Поставьте одну конкретную цель на следующую игру (например, 50 добиваний к 10:00)."
    ),
    "Do 10 minutes of last-hit drills in the demo hero mode before your next ranked session.": (
        "Потратьте 10 минут на тренировку добиваний в демо-режиме перед следующей рейтинговой сессией."
    ),
    "After every won teamfight, ask: which tower or Roshan is free right now?": (
        "После каждого выигранного замеса спрашивайте: какая башня или Рошан сейчас свободны?"
    ),
    # --- meta panel: data-source attribution -----------------------------
    "OpenDota public match data": "публичным матчам OpenDota",
    # --- screenshot analyzer ---------------------------------------------
    "Detected heroes were auto-fed into the report engine.": (
        "Распознанные герои автоматически переданы в движок отчёта."
    ),
    "No heroes detected — try a clearer, larger screenshot of the draft screen.": (
        "Герои не распознаны — попробуйте более чёткий и крупный скриншот экрана драфта."
    ),
    # --- API error details ------------------------------------------------
    "empty upload": "Пустой файл.",
    "image too large (max 8 MB)": "Изображение слишком большое (максимум 8 МБ).",
    "match not available": "матч недоступен",
}


# ---------------------------------------------------------------------------
# Pattern catalogue (order matters: most specific first)
# ---------------------------------------------------------------------------

# Role identifiers used inside sentences.
RU_ROLES = {
    "carry": "керри",
    "mid": "мид",
    "offlane": "оффлейн",
    "support": "саппорт",
    "hard_support": "хард саппорт",
}

RU_TERMS = {
    "heavily favoured": "с большим перевесом",
    "favoured": "в вашу пользу",
    "a coin flip": "равный",
    "an uphill draft": "тяжёлый",
    "critical": "критично",
    "high": "важно",
}

RU_RANK = {
    "Herald": "Herald",
    "Guardian": "Guardian",
    "Crusader": "Crusader",
    "Archon": "Archon",
    "Legend": "Legend",
    "Ancient": "Ancient",
    "Divine": "Divine",
    "Immortal": "Immortal",
}

RU_DANGER = {"low": "низкая", "medium": "средняя", "high": "высокая"}


def _patterns() -> list[tuple[re.Pattern[str], str]]:
    p: list[tuple[re.Pattern[str], str]] = []

    def add(rx: str, repl: str) -> None:
        p.append((re.compile(rx), repl))

    # scoring -----------------------------------------------------------------
    add(
        r"^Wins the matchup maths against (.+?) \(shrunk counter advantage from real match data\)\.$",
        r"Выигрывает мап-ап против \1 (усреднённое преимущество из реальных матчей).",
    )
    add(
        r"^Above-average current win rate \(([\d.]+%)\), so you are not fighting the meta\.$",
        r"Винрейт выше среднего (\1), так что вы не идёте против меты.",
    )
    add(r"^Careful: (.+?) counter you on paper\.$", r"Осторожно: \1 контрят вас на бумаге.")

    # skill build -------------------------------------------------------------
    add(
        r"^Take the level (\d+) talent \(see the Talent Tree section\)\.$",
        r"Возьмите талант (\1-й уровень) — см. раздел «Дерево талантов».",
    )
    add(
        r"^Alternative: delay (.+?) past level 6 only if the lane is already decided\.$",
        r"Альтернатива: задержите \1 после 6-го уровня, только если лейн уже решён.",
    )

    # power spikes ------------------------------------------------------------
    add(r"^(.+?) timing$", r"Тайминг: \1")

    # win conditions ----------------------------------------------------------
    add(
        r"^Kill (.+?) first in every fight — they are your highest-priority threat\.$",
        r"Убивайте \1 первым в каждом замесе — это ваша главная угроза.",
    )

    # one-sentence plan -------------------------------------------------------
    add(
        r"^If you get (.+?) on time, kill (.+?) first(.*?), this match is (.+?) \((\d+)% draft win probability\)\.$",
        lambda m: (
            f"Если вы вовремя получите {m.group(1)} и убьёте {m.group(2)} первым"
            f"{_clause_ru(m.group(3))}, этот матч {RU_TERMS.get(m.group(4), m.group(4))} "
            f"({m.group(5)}% вероятность победы по драфту)."
        ),
    )

    # items -------------------------------------------------------------------
    add(
        r"^Bought in ([\d.]+%) of games at this stage on this hero \(OpenDota meta data\)\.$",
        r"Покупается в \1 игр на этой стадии на этом герое (данные OpenDota).",
    )
    add(r"^\[(critical|high)\] (.+)$", lambda m: f"[{RU_TERMS[m.group(1)]}] {_translate_body(m.group(2))}")
    add(
        r"^Situational answer to (.+)\.$",
        lambda m: f"Ситуативный ответ на {_problem_ru(m.group(1))}.",
    )

    # win probability ---------------------------------------------------------
    add(
        r"^(.+?) wins ([\d.]+%) of games at this patch\.$",
        r"\1 выигрывает \2 игр на этом патче.",
    )
    add(
        r"^Enemy draft has 0 unanswered high threats\.$",
        "У драфта врага нет неотвеченных серьёзных угроз.",
    )
    add(
        r"^Enemy draft has (\d+) unanswered high threats \((.+?)\)\.$",
        lambda m: (
            f"У драфта врага {m.group(1)} {_plural(int(m.group(1)), 'неотвеченная серьёзная угроза', 'неотвеченные серьёзные угрозы', 'неотвеченных серьёзных угроз')} "
            f"({_problem_ru(m.group(2))})."
        ),
    )
    add(
        r"^Hero fits the (.+?) role (\d+%)\.$",
        lambda m: f"Герой соответствует роли {RU_ROLES.get(m.group(1), m.group(1))} на {m.group(2)}.",
    )
    add(
        r"^(Herald|Guardian|Crusader|Archon|Legend|Ancient|Divine|Immortal): draft edges convert to wins less reliably at lower MMR\.$",
        r"\1: преимущество драфта реже превращается в победу на низком MMR.",
    )

    # coach -------------------------------------------------------------------
    add(
        r"^match (\d+) is not available from OpenDota$",
        r"матч \1 недоступен в OpenDota",
    )
    add(
        r"^Strong farming pace \(([\d.]+) GPM\) — you converted map space into gold efficiently\.$",
        r"Высокий темп фарма (\1 GPM) — вы эффективно превращали пространство карты в золото.",
    )
    add(
        r"^Low farming pace \(([\d.]+) GPM\) for a (\d+)-minute game — you left gold on the map\.$",
        r"Низкий темп фарма (\1 GPM) для игры длиной \2 мин — вы оставили золото на карте.",
    )
    add(
        r"^Excellent last-hit rate \(([\d.]+) LH/min\)\.$",
        r"Отличный показатель добиваний (\1 добиваний/мин).",
    )
    add(
        r"^Low last-hit rate \(([\d.]+) LH/min\) for a carry — prioritise uncontested farm\.$",
        r"Низкий показатель добиваний (\1 добиваний/мин) для керри — приоритет на свободный фарм.",
    )
    add(
        r"^Only (\d+) deaths — excellent positioning and map awareness\.$",
        lambda m: (
            f"Всего {m.group(1)} {_plural(int(m.group(1)), 'смерть', 'смерти', 'смертей')} — "
            "отличное позиционирование и чувство карты."
        ),
    )
    add(
        r"^(\d+) deaths in (\d+) minutes — you are taking fights you cannot win\.$",
        lambda m: (
            f"{m.group(1)} {_plural(int(m.group(1)), 'смерть', 'смерти', 'смертей')} за {m.group(2)} минут — "
            "вы ввязываетесь в бои, которые не можете выиграть."
        ),
    )
    add(
        r"^Item build is close to the current meta build for (.+?)\.$",
        r"Сборка предметов близка к текущей мета-сборке для \1.",
    )
    add(
        r"^(.+?) is an off-meta purchase for (.+?) this patch \(below the top meta choices\) — check whether it actually answered the enemy draft\.$",
        r"\1 — не мета-покупка для \2 на этом патче (ниже топовых мета-вариантов) — проверьте, действительно ли она отвечала на драфт врага.",
    )

    # draft summary -----------------------------------------------------------
    add(r"^(.+?) min$", r"\1 мин")

    return p


# Problems flags rendered inside sentences.
RU_PROBLEMS = {
    "heavy magic burst": "мощный магический бурст",
    "heavy physical": "мощный физический урон",
    "illusions or summons": "иллюзии и призывы",
    "invisibility": "невидимость",
    "heal heavy": "мощное лечение",
    "heavy single target disable": "цепочки одиночного контроля",
    "burst pure damage": "чистый бурст-урон",
    "silence": "сайленс",
    "kite and slow": "кайт и замедление",
    "split push": "сплитпуш",
    "heavy cc teamfight": "мощный контроль в замесах",
    "evasion or blind": "уклонение и слепота",
}


def _problem_ru(text: str) -> str:
    return RU_PROBLEMS.get(text.strip().lower(), text.strip())


def _plural(n: int, one: str, few: str, many: str) -> str:
    """Russian plural form for a count.

    English has two forms; Russian has three, and getting this wrong reads as
    machine translation immediately, so the count is inflected properly.
    """
    mod10, mod100 = n % 10, n % 100
    if mod10 == 1 and mod100 != 11:
        return one
    if 2 <= mod10 <= 4 and not 12 <= mod100 <= 14:
        return few
    return many


def _clause_ru(clause: str) -> str:
    """Translate the optional trailing clauses of the one-sentence plan.

    The engine can append zero, one or two clauses, so they are translated
    independently rather than matched as a single optional group.
    """
    clause = clause.strip()
    if not clause:
        return ""
    clause = clause.replace(
        ", avoid enemy initiations until BKB is up",
        ", избегайте инициаций врага до появления BKB",
    )
    clause = re.sub(r", and never build (.+)$", r", и никогда не собирайте \1", clause)
    return clause


_PATTERNS = _patterns()


def _translate_body(text: str) -> str:
    """Translate a fragment that may itself be a known exact sentence."""
    return RU_EXACT.get(text, text)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def translate(text: str, locale: str) -> str:
    """Translate a single engine sentence.

    Handles three shapes, because the engine emits all of them:

    * a whole sentence  -> exact table, then pattern table;
    * several sentences -> translated independently and rejoined (win
      conditions are built by joining sentences with a space);
    * comma-joined fragments -> translated only if every fragment is known, so
      a partially understood string is left in English rather than half
      translated.

    Anything unmatched passes through unchanged.
    """
    if locale != "ru" or not text:
        return text

    atomic = _translate_atomic(text, locale)
    if atomic != text:
        return atomic

    # Multiple sentences: win conditions are joined with a single space.
    if ". " in text:
        parts = text.split(" ")
        out = []
        buf: list[str] = []
        for word in parts:
            buf.append(word)
            if word.endswith("."):
                out.append(_translate_atomic(" ".join(buf), locale))
                buf = []
        if buf:
            out.append(_translate_atomic(" ".join(buf), locale))
        joined = " ".join(out)
        if joined != text:
            return joined

    # Comma-joined fragments: target-priority reasons.
    if ", " in text:
        frags = text.split(", ")
        translated = [RU_EXACT.get(f, f) for f in frags]
        if all(t != f for t, f in zip(translated, frags)):
            return ", ".join(translated)

    return text


def _translate_atomic(text: str, locale: str) -> str:
    """Exact table, then pattern table. No composition."""
    exact = RU_EXACT.get(text)
    if exact is not None:
        return exact
    for rx, repl in _PATTERNS:
        m = rx.match(text)
        if m:
            if callable(repl):
                return repl(m)
            return m.expand(repl)
    return text


def localize(value: Any, locale: str) -> Any:
    """Recursively translate every string inside a JSON-like structure.

    Keys are left untouched: they are part of the API contract the frontend
    depends on, and translating them would break every client.
    """
    if locale != "ru":
        return value
    if isinstance(value, str):
        return translate(value, locale)
    if isinstance(value, list):
        return [localize(v, locale) for v in value]
    if isinstance(value, dict):
        return {k: localize(v, locale) for k, v in value.items()}
    return value


# Localised threat dimension labels (the engine ships English ones).
RU_DIMENSIONS = {
    "Magic Damage": "Магический урон",
    "Physical Damage": "Физический урон",
    "Pure Damage": "Чистый урон",
    "Burst Damage": "Бурст-урон",
    "Sustain Damage": "Длительный урон",
    "Crowd Control": "Контроль",
    "Teamfight Potential": "Потенциал в замесах",
    "Pickoff Potential": "Потенциал в пикоффах",
    "Push Strength": "Сила пуша",
    "Split Push Strength": "Сила сплитпуша",
    "Roshan Strength": "Сила на Рошане",
    "Early Game": "Ранняя игра",
    "Mid Game": "Средняя игра",
    "Late Game": "Поздняя игра",
}


def localize_report(report: dict, locale: str) -> dict:
    """Translate a draft report, including the label maps the UI renders."""
    out = localize(report, locale)
    if locale != "ru":
        return out
    _localize_dimensions(out)
    picks = out.get("pick_reports")
    if isinstance(picks, dict):
        for sub in picks.values():
            if isinstance(sub, dict):
                _localize_dimensions(sub)
    return out


def _localize_dimensions(report: dict) -> None:
    """Remap the engine's English threat-dimension labels to Russian in place."""
    ta = report.get("threat_analysis")
    if isinstance(ta, dict) and isinstance(ta.get("labels"), dict):
        ta["labels"] = {k: RU_DIMENSIONS.get(v, v) for k, v in ta["labels"].items()}
    ds = report.get("draft_summary")
    if isinstance(ds, dict) and isinstance(ds.get("headline_threats"), list):
        for item in ds["headline_threats"]:
            if isinstance(item, dict):
                item["dimension"] = RU_DIMENSIONS.get(item.get("dimension", ""), item.get("dimension"))
