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
        "Должен выиграть лейн или уйти вровень против этого состава."
    ),
    "⚠ Loses the likely lane matchup — plan to rotate early or bring a lane partner.": (
        "⚠ Проигрывает вероятный матчап на линии — планируйте раннюю ротацию или возьмите партнёра на лейн."
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
    "chains disables onto you": "накидывает на вас цепочку контроля",
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
    "Hero matchups": "Матчапы героев",
    "Shrunk head-to-head advantage across the enemy draft.": (
        "Усреднённое преимущество в личных матчапах против драфта врага."
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
    "could not read image": "Не удалось прочитать изображение. Загрузите PNG или JPG.",
    "match not available": "матч недоступен",
    "OpenDota rate limit reached — please try again in a moment.": (
        "Достигнут лимит запросов к OpenDota — попробуйте ещё раз через минуту."
    ),
    "Could not reach OpenDota — please try again in a moment.": (
        "Не удалось связаться с OpenDota — попробуйте ещё раз через минуту."
    ),
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
        r"Выигрывает матчап против \1 (усреднённое преимущество из реальных матчей).",
    )
    add(
        r"^Above-average current win rate \(([\d.]+%)\), so you are not fighting the meta\.$",
        r"Винрейт выше среднего (\1), так что вы не идёте против меты.",
    )
    add(r"^Careful: (.+?) counter you on paper\.$", r"Осторожно: \1 контрят вас на бумаге.")
    # Item counter reasons append the enemies that justify them; translate the
    # reason itself and keep the hero names (proper nouns) unchanged.
    add(
        r"^(.+) Answers: (.+?)\.$",
        lambda m: f"{_translate_atomic(m.group(1), 'ru')} Отвечает: {m.group(2)}.",
    )

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

    # ---------------------------------------------------------------------
    # My Hero Strategy
    # ---------------------------------------------------------------------
    add(
        r"^This is a draft you are expected to win: (.+?) holds the stronger side of the matchup maths\.$",
        r"Это драфт, который вы должны выигрывать: у \1 сильная сторона в математике матчапов.",
    )
    add(
        r"^You are slightly ahead in the draft with (.+?), but the margin is thin enough that a lost lane erases it\.$",
        r"Вы немного впереди в драфте с \1, но запас настолько мал, что проигранная линия его стирает.",
    )
    # translate() splits multi-sentence strings on ". ", so each sentence of the
    # assessment needs its own pattern rather than one whole-string pattern.
    add(r"^This is an even draft\.$", "Это ровный драфт.")
    add(
        r"^Nothing in the maths separates (.+?) from this lineup, so timings and execution decide it\.$",
        r"Математика не отделяет \1 от этого состава, поэтому всё решают тайминги и исполнение.",
    )
    add(r"^You are behind on paper\.$", "На бумаге вы позади.")
    add(
        r"^(.+?) has to win through tempo, pickoffs and map control rather than straight fights\.$",
        r"\1 должен выигрывать через темп, пикоффы и контроль карты, а не через прямые бои.",
    )
    add(r"^The draft is against you\.$", "Драфт против вас.")
    add(
        r"^Winning with (.+?) here means punishing mistakes and closing before their advantages compound\.$",
        r"Победить на \1 здесь — значит наказывать ошибки и закрывать игру, пока их преимущества не накопились.",
    )
    add(r"^Respect (.+?) above all others\.$", r"Уважайте \1 больше всех остальных.")
    add(
        r"^Ask for a rotation the moment (.+?) commits their disable with backup — that is when a kill is available\.$",
        r"Просите ротацию, как только \1 потратит контроль с поддержкой — тогда и появляется убийство.",
    )
    add(
        r"^(.+?) has a real kill combo on you in lane — treat every step past the river as a risk\.$",
        r"У \1 есть реальное комбо на убийство против вас на линии — считайте каждый шаг за реку риском.",
    )
    add(
        r"^Brings (\d+) disables? — you will be held in place while their team follows up\.$",
        lambda m: (
            f"Имеет {m.group(1)} "
            f"{_plural(int(m.group(1)), 'контроль', 'контроля', 'контролей')} — вас удержат на месте, пока их команда наносит урон."
        ),
    )
    add(
        r"^You can fight this hero when you (.+)\.$",
        lambda m: f"С этим героем можно драться, когда вы {_hs_fragments_ru(m.group(1))}.",
    )
    add(
        r"^Likely laned in the (.+?)\. (.+)$",
        lambda m: f"Скорее всего, на {RU_LANES.get(m.group(1), m.group(1))}. {translate(m.group(2), 'ru')}",
    )
    add(
        r"^Never stand in the open when (.+?) is unaccounted for — fight only after their initiation is spent, then collapse on their back line\.$",
        r"Никогда не стойте на открытом месте, когда местоположение \1 неизвестно — деритесь только после того, как их инициация потрачена, затем обрушьтесь на их тыл.",
    )
    add(
        r"^Stay near a teammate or a ward when (.+?) is missing; they convert isolation into kills, not straight fights\.$",
        r"Держитесь рядом с союзником или вардом, когда \1 пропал; они превращают изоляцию в убийства, а не в прямые бои.",
    )
    add(
        r"^Close the gap from fog or from behind — walking at (.+?) in a straight line is how you take a full combo before you reach them\.$",
        r"Сокращайте дистанцию из тумана или со спины — идти на \1 по прямой значит съесть полное комбо, не дойдя до него.",
    )
    add(
        r"^Position so (.+?) cannot land their disable without entering your team's range; make them commit into you, not onto you\.$",
        r"Располагайтесь так, чтобы \1 не мог применить контроль, не зайдя в радиус вашей команды; пусть он входит в вас, а не на вас.",
    )
    add(
        r"^Approach (.+?) from the direction they want to escape toward, so their escape is blocked rather than free\.$",
        r"Заходите на \1 со стороны, куда он хочет убежать, чтобы его эскейп был заблокирован, а не свободен.",
    )
    add(
        r"^Trade from the edge of the fight against (.+?): close when their cooldowns are down, disengage when they are up\.$",
        r"Разменивайтесь с \1 с края боя: сближайтесь на их кулдаунах, выходите, когда они готовы.",
    )
    add(
        r"^Play (.+?) to the plan: finish (.+?) on time, kill (.+?) first(.*?) — this matchup is (.+?) \((\d+)% draft win probability\)\.$",
        lambda m: (
            f"Играйте на {m.group(1)} по плану: завершите {m.group(2)} вовремя, убейте {m.group(3)} первым"
            f"{_hs_plan_clause_ru(m.group(4))} — этот матчап {RU_TERMS.get(m.group(5), m.group(5))} "
            f"({m.group(6)}% вероятность победы по драфту)."
        ),
    )
    add(
        r"^(.+?) is a favourable matchup for you on real match data\.$",
        r"\1 — выгодный для вас матчап по реальным данным матчей.",
    )
    add(
        r"^Fighting (.+?) on even terms when you can pick a better angle\.$",
        r"Драться с \1 на равных, когда можно выбрать лучший угол.",
    )

    return p



# ---------------------------------------------------------------------------
# My Hero Strategy catalogue
# ---------------------------------------------------------------------------

HS_EXACT: dict[str, str] = {
    "No single enemy hard-counters you — this game is decided by execution, not the draft.":
        "Ни один враг жёстко вас не контрит — исход решают исполнение и решения, а не драфт.",
    "You bring illusions they cannot clear efficiently.":
        "У вас есть иллюзии, которые враг не может эффективно зачистить.",
    "You can win the map without winning fights — split push is a real win condition.":
        "Вы можете выиграть карту без побед в замесах — сплитпуш здесь реальное условие победы.",
    "Your sustain outlasts their damage in extended fights.":
        "Ваш отхил переживает их урон в затяжных замесах.",
    "You convert won fights into buildings faster than they can.":
        "Вы превращаете выигранные бои в башни быстрее, чем они успевают ответить.",
    "Walking into fog alone: their lock-down turns one mistake into a death.":
        "Заходить в туман одному: их контроль превращает одну ошибку в смерть.",
    "Building single-target damage against an army you cannot clear.":
        "Собирать урон по одной цели против армии, которую вы не можете зачистить.",
    "Taking long fights before you have healing reduction.":
        "Затягивать бои, пока у вас нет снижения лечения.",
    "Farming without truesight — their invisibility ganks punish it every time.":
        "Фармить без трусайта — их ганги из невидимости наказывают это каждый раз.",
    "Waiting for late game: your win rate falls as the clock runs, so force objectives early.":
        "Ждать позднюю игру: ваш винрейт падает со временем, поэтому навязывайте цели рано.",
    "Over-committing to early fights instead of farming toward your scaling window.":
        "Слишком вкладываться в ранние бои вместо фарма к вашему окну силы.",
    "Buying your standard build without checking the counters listed in Section 4.":
        "Собирать стандартную сборку, не проверив контр-предметы из раздела 4.",
    "Level 1: take your highest-value ability (see Section 3) and secure the first rune if you can do it safely.":
        "Уровень 1: берите самую ценную способность (см. раздел 3) и забирайте первый рун, если это безопасно.",
    "Levels 2-3: contest last hits; your first item should be a lane sustain item, not a greedy component.":
        "Уровни 2-3: боритесь за добивания; первый предмет — на выживание на линии, а не жадный компонент.",
    "Levels 4-5: do not contest the lane — pull the side camp, farm the jungle camp, and wait for a support rotation.":
        "Уровни 4-5: не боритесь за линию — отводите боковой лагерь, фармите лагерь в лесу и ждите ротацию саппорта.",
    "If you are zoned below 50% HP, buy out and rotate rather than feeding kills.":
        "Если вас выдавили ниже 50% здоровья, откупитесь и смените линию, а не отдавайтесь на убийства.",
    "Levels 4-5: trade when their kill spell is on cooldown, then shove the wave and take the rune.":
        "Уровни 4-5: разменивайтесь, когда их убийственная способность на кулдауне, затем пушьте волну и забирайте рун.",
    "Levels 4-5: hold the lane, deny their farm and push toward their tower to force a rotation.":
        "Уровни 4-5: держите линию, мешайте их фарму и пушьте к их башне, чтобы вынудить ротацию.",
    "Levels 6-8: with your ultimate up, look for the first kill or a rotation to the mid lane.":
        "Уровни 6-8: с готовой ультой ищите первое убийство или ротацию на мид.",
    "Use your farm acceleration to clear the stacked camps once you own your first item — this is where you pull ahead.":
        "Используйте ускорение фарма, чтобы зачищать застанкованные лагеря после первого предмета — здесь вы вырываетесь вперёд.",
    "Play defensively until you have your level 6 and first item. You are not the lane's win condition — surviving it at even net worth is a won lane for you. Only go forward when your support is present and their key spell is down.":
        "Играйте от обороны, пока не получите 6-й уровень и первый предмет. Вы не главное условие победы на линии — пережить её при равном нетворсе для вас уже победа. Идите вперёд только когда рядом саппорт и их ключевая способность на кулдауне.",
    "Play even: trade on their cooldowns, push when they leave, and never dive past the tower line without vision of a rotation. A slight lane loss is fine because you scale better.":
        "Играйте вровень: разменивайтесь на их кулдаунах, пушьте, когда они уходят, и не лезьте за линию башни без вижена ротации. Небольшая потеря линии нормальна — вы скейлитесь лучше.",
    "Play aggressively: you win this lane, so deny their farm, shove the wave and take the enemy tower early. Push your advantage into a rotation rather than sitting on a won lane.":
        "Играйте агрессивно: вы выигрываете эту линию, поэтому мешайте их фарму, пушьте волну и забирайте башню рано. Превращайте преимущество в ротацию, а не сидите на выигранной линии.",
    "Your escape is your life — never use it to farm or to chase unless the kill is certain.":
        "Ваш эскейп — это ваша жизнь: не используйте его для фарма или погони, если убийство не гарантировано.",
    "You have no reliable escape, so positioning is your escape: stay on the safe side of the creep wave.":
        "У вас нет надёжного эскейпа, поэтому ваша защита — позиция: держитесь безопасной стороны волны.",
    "Buy a Magic Wand and a Cloak early, and ferry regen rather than walking to base.":
        "Купите Magic Wand и Cloak рано и подвозите реген, а не ходите на базу пешком.",
    "If the lane is unplayable, jungle and let the support soak — a level behind is better than three deaths.":
        "Если линия непроходима, уходите в лес и отдайте опыт саппорту — отстать на уровень лучше, чем умереть трижды.",
    "Keep a TP scroll at all times so you can join a fight or escape a collapsed lane.":
        "Всегда держите TP — чтобы присоединиться к бою или уйти из провалившейся линии.",
    "Call for help if you are pushed under your tower with no regen, or if the enemy support leaves the lane to gank.":
        "Зовите на помощь, если вас загнали под башню без регена или если вражеский саппорт ушёл гангать.",
    "Ping when their disable is used on you — your team has a free window to punish them.":
        "Пингуйте, когда их контроль потрачен на вас — у команды есть свободное окно, чтобы наказать их.",
    "They need to land a disable before their damage; standing behind your creep wave breaks the angle.":
        "Им нужно попасть контролем до урона; стойте за волной крипов — это ломает их угол.",
    "Their burst is magical — a Cloak or early Magic Wand charges is what keeps you alive.":
        "Их бурст магический — Cloak или ранние заряды Magic Wand держат вас живым.",
    "They can silence your escape — keep a dispel or fight only with your support next to you.":
        "Они могут засайленсить ваш эскейп — держите диспел или деритесь только с саппортом рядом.",
    "You win this lane on paper — push the wave, take the rune and force them off the creeps.":
        "На бумаге вы выигрываете эту линию — пушьте волну, забирайте рун и выгоняйте их с крипов.",
    "Even lane: trade when their spells are down, and farm the pull camp when the wave is pushed.":
        "Ровная линия: разменивайтесь, когда их способности на кулдауне, и фармите лагерь, когда волна отпушена.",
    "Standard lane: contest every last hit and rotate out the moment they get a level advantage.":
        "Обычная линия: боритесь за каждое добивание и уходите с линии, как только они получают преимущество по уровням.",
    "Trade aggressively only while your escape and their key spell are both down — otherwise last-hit and let them over-extend.":
        "Разменивайтесь агрессивно только когда и ваш эскейп, и их ключевая способность на кулдауне — иначе добивайте и дайте им растянуться.",
    "Do not trade into their spells: you have no reliable escape, so every trade must be one you win cleanly or you skip it.":
        "Не лезьте в размен под их способности: у вас нет надёжного эскейпа, поэтому любой размен должен быть выигрышным, иначе пропускайте его.",
    "As the ranged hero you should deny and harass from max range, never stand in melee range to last-hit.":
        "Как дальнобойный герой вы должны мешать и харасить с максимальной дистанции, никогда не вставая вплотную к крипам.",
    "Their illusions and summons die to your area damage — this ability is your answer to them.":
        "Их иллюзии и призывы умирают от вашего урона по площади — эта способность ваш ответ на них.",
    "Your disable is the tool that survives their silence window.":
        "Ваш контроль — это инструмент, который переживает их окно сайленса.",
    "This ability pierces spell immunity, which is rare value against a BKB-heavy draft.":
        "Эта способность пробивает неуязвимость к магии — редкая ценность против драфта с BKB.",
    "Trading burst with their burst is how you win the early fights — level it for the damage.":
        "Размен бурста на бурст — так вы выигрываете ранние бои; качайте её ради урона.",
    "Damage that does not need a target helps you fight invisible heroes.":
        "Урон, которому не нужна цель, помогает драться с невидимыми героями.",
    "Matchup note: level your area damage before your single-target ability — their army is the win condition.":
        "Заметка по матчапу: качайте урон по площади раньше способности по одной цели — их армия и есть условие победы.",
    "Matchup note: your defensive ability (if you have one) is worth points earlier than the standard order suggests.":
        "Заметка по матчапу: ваша защитная способность (если она есть) стоит очков раньше, чем подсказывает стандартный порядок.",
    "Matchup note: physical burst means armour and stats beat raw damage early.":
        "Заметка по матчапу: физический бурст — значит, ранняя броня и статы лучше чистого урона.",
    "Matchup note: you cannot out-sustain them — level damage and look for one-shot windows instead.":
        "Заметка по матчапу: вы не пересидите их по отхилу — качайте урон и ищите окна для мгновенного убийства.",
    "Has a stun, which sets up their damage and interrupts your channel or escape.":
        "Имеет стан, который подготавливает их урон и прерывает ваш канал или эскейп.",
    "Has a silence, so it can shut down your spell-dependent plan before a fight starts.":
        "Имеет сайленс, поэтому может отключить ваш план на способностях ещё до начала боя.",
    "Its control pierces spell immunity — Black King Bar alone will not break the chain.":
        "Его контроль пробивает неуязвимость к магии — одного Black King Bar не хватит, чтобы разорвать цепочку.",
    "Deals pure damage, so magic resistance and armour do nothing against it.":
        "Наносит чистый урон — магическое сопротивление и броня против него бесполезны.",
    "Its damage comes as one magical burst — you die in the window before you can react.":
        "Его урон приходит одним магическим бурстом — вы умираете в окне, где не успеваете отреагировать.",
    "Its physical burst shreds a low-armour hero before you can disengage.":
        "Его физический бурст разрывает героя с низкой бронёй до того, как вы успеете выйти из боя.",
    "Creates illusions, which win the map even when you win the fight.":
        "Создаёт иллюзии, которые выигрывают карту, даже когда вы выигрываете бой.",
    "Summons push and soak damage, forcing you to split your attention.":
        "Призывы пушут и впитывают урон, заставляя вас разрываться.",
    "Heals the whole team, so damage without healing reduction is refunded.":
        "Лечит всю команду, поэтому урон без снижения лечения просто откатывается.",
    "Has evasion, so a large share of your attacks simply miss.":
        "Имеет уклонение — значительная часть ваших атак просто промахивается.",
    "Can turn invisible, which makes it a pickoff threat whenever you are alone.":
        "Может уходить в невидимость — это делает его угрозой пикоффа, когда вы один.",
    "Is built to neutralise a carry — expect it to target you specifically.":
        "Собран, чтобы нейтрализовать керри — ждите, что он нацелится именно на вас.",
    "Wins by splitting the map, so it can beat you without ever fighting you.":
        "Выигрывает через сплит карты — может победить вас, вообще не вступая в бой.",
    "Has global presence, so a fight anywhere becomes a fight everywhere.":
        "Имеет глобальное присутствие — бой в любой точке становится боем везде.",
    "Can save an ally from your kill, wasting your cooldowns.":
        "Может спасти союзника от вашего убийства, потратив ваши кулдауны впустую.",
    "No single dominant threat — it contributes through damage and utility rather than one win condition.":
        "Нет одной доминирующей угрозы — он вредит уроном и полезностью, а не одним условием победы.",
    "Stay out of their cast range until their disable is used — walk in behind a teammate or from fog.":
        "Держитесь вне радиуса применения, пока их контроль не потрачен — заходите за союзником или из тумана.",
    "Do not stand in the open below ~60% HP; their combo needs one clean angle to kill you.":
        "Не стойте на открытом месте ниже ~60% здоровья; их комбо нужно всего одно чистое окно, чтобы убить вас.",
    "Carry truesight when you farm alone; their invisibility is only lethal when you cannot see it coming.":
        "Носите трусайт, когда фармите один; их невидимость смертельна, только когда вы её не видите.",
    "Do not trade damage with them without anti-heal — you lose the exchange in the long run.":
        "Не разменивайтесь с ними без анти-хила — в долгую вы проигрываете размен.",
    "Do not commit your escape first — bait theirs, then use yours to close the distance.":
        "Не тратьте эскейп первым — выманите их, затем своим сокращайте дистанцию.",
    "Do not chase their split push with your whole team; send one hero and keep pressure elsewhere.":
        "Не гоняйтесь за их сплитпушем всей командой; отправьте одного героя и держите давление в другом месте.",
    "Trade with it only when your cooldowns are up and you have vision of its team.":
        "Разменивайтесь с ним только когда ваши кулдауны готовы и вы видите его команду.",
    "You or your initiator must land the first spell. Fight only with vision and with your team behind you — an initiation into fog with no follow-up is how drafts like this lose.":
        "Вы или ваш инициатор должны нанести первое заклинание. Деритесь только с виженом и с командой за спиной — инициация в туман без поддержки — так и проигрывают такие драфты.",
    "Neither side has a clean initiator, so the fight starts with a pickoff or an objective. Do not open the fight yourself.":
        "Ни у одной стороны нет чистого инициатора, поэтому бой начинается с пикоффа или цели. Не начинайте бой сами.",
    "Wait for their save to be used on someone else, or kill the saver first; committing into a live save wastes your cooldowns.":
        "Дождитесь, пока их спасение потратят на другого, или убейте спасающего первым; вложение в живое спасение тратит ваши кулдауны впустую.",
    "Wait for their lock-down to be spent on someone else — that is your window to walk in and do damage.":
        "Дождитесь, пока их контроль потратят на другого — это ваше окно, чтобы зайти и нанести урон.",
    "Wait for their burst to land on your front line before you commit; walking in first means eating it yourself.":
        "Дождитесь, пока их бурст прилетит в вашу переднюю линию, прежде чем входить; если зайдёте первым, съедите его сами.",
    "Survive the first two seconds: an early BKB, Glimmer or Aeon Disk is worth more than a damage item against this draft.":
        "Переживите первые две секунды: ранний BKB, Glimmer или Aeon Disk против этого драфта ценнее предмета на урон.",
    "Survive by positioning: keep a teammate between you and their damage and disengage the moment the fight turns.":
        "Выживайте за счёт позиции: держите союзника между собой и их уроном и выходите из боя, как только он повернётся.",
    "Stand at the back of your team, at max attack range, and step forward only when their gap-closers are on cooldown.":
        "Стойте в тылу команды, на максимальной дистанции атаки, и выходите вперёд только когда их сближающие способности на кулдауне.",
    "Stand at the front and absorb the first spell, but only with a defensive item up and your team within follow-up range.":
        "Стойте впереди и впитывайте первое заклинание, но только с активным защитным предметом и командой в радиусе поддержки.",
    "Stand on the flank, out of their initiation range, and enter the fight from the side once it starts.":
        "Стойте на фланге, вне радиуса их инициации, и заходите в бой сбоку, как только он начнётся.",
    "They are the stronger straight-up teamfight draft: win with a pickoff or an objective, not a 5v5.":
        "Они сильнее в прямом замесе 5 на 5: выигрывайте через пикофф или цель, а не через размен.",
    "Do not chase their split pusher with five heroes — trade the opposite lane and keep your own pressure.":
        "Не гоняйтесь за их сплитпушером пятью героями — разменяйте противоположную линию и держите своё давление.",
    "Expect a fight to become a fight everywhere: account for their global heroes before you commit to a long chase.":
        "Ждите, что бой станет боем везде: учитывайте их глобальных героев, прежде чем пускаться в долгую погоню.",
    "Clear the army before the hero: killing the illusions is often worth more than the damage you would deal to the real target.":
        "Зачищайте армию раньше героя: убить иллюзии часто ценнее, чем урон по настоящей цели.",
    "Apply healing reduction before the fight, not during it — anti-heal after the first heal is already late.":
        "Применяйте снижение лечения до боя, а не во время — анти-хил после первого лечения уже опоздал.",
    "This hero has no compiled ability data, so ability-level advice is limited.":
        "У этого героя нет собранных данных о способностях, поэтому советы по способностям ограничены.",
    "The draft maths are close to even, so treat the win probability as a coin flip rather than a prediction.":
        "Математика драфта почти равна, поэтому относитесь к вероятности победы как к монетке, а не как к предсказанию.",
    "At least one enemy has no compiled ability data; its dossier falls back to capability counters.":
        "У какого-то врага нет собранных данных о способностях; его досье опирается на счётчики возможностей.",
    "Hero and item names are shown in English, matching community convention.":
        "Имена героев и предметов показаны на английском — так принято в сообществе Dota 2.",
    "head-to-head matchup advantage (shrunk OpenDota matrix)":
        "преимущество в личных матчапах (сглаженная матрица OpenDota)",
    "hero win rate at this patch": "винрейт героя на этом патче",
    "empirical win rate by game duration": "эмпирический винрейт по длительности игры",
    "ability damage types and disable counts (Valve hero constants)":
        "типы урона способностей и количество контролей (константы героев Valve)",
    "lane assignment and lane opponents": "распределение по линиям и соперники на линии",
    "teamfight positioning": "позиционирование в замесах",
    # item answers (one per archetype)
    "Targeted lock-down chains are how this draft kills you — spell immunity or an auto-dispel breaks the chain.":
        "Цепочки одиночного контроля — так этот драфт убивает вас; неуязвимость к магии или авто-диспел разрывает цепочку.",
    "Their control pierces spell immunity, so BKB alone will not save you — you need a linken-style block or raw HP.":
        "Их контроль пробивает неуязвимость к магии, поэтому одного BKB не хватит — нужен блок в стиле Linken или запас здоровья.",
    "Their damage arrives as one magical combo; magic resistance or BKB removes it entirely.":
        "Их урон приходит одной магической комбинацией; магическое сопротивление или BKB полностью его убирают.",
    "Most of their damage is magical, so magic resistance is worth more than armour or HP here.":
        "Большая часть их урона магическая, поэтому сопротивление магии здесь ценнее брони или здоровья.",
    "They kill with physical burst; armour and attack-slow cut it far harder than raw HP.":
        "Они убивают физическим бурстом; броня и замедление атаки режут его куда сильнее, чем чистое здоровье.",
    "Their DPS is physical, so armour and attack speed slows are your cheapest survivability.":
        "Их ДПС физический, поэтому броня и замедление скорости атаки — самая дешёвая выживаемость.",
    "Pure damage ignores resistance — only raw HP, an Aeon Disk buffer or lifesteal actually answer it.":
        "Чистый урон игнорирует сопротивление — против него работают только запас здоровья, щит Aeon Disk или лайфстил.",
    "Illusion armies melt to area damage; a single-target build loses to them no matter how farmed you are.":
        "Армии иллюзий тают от урона по площади; сборка по одной цели проигрывает им, как бы вы ни были нафармлены.",
    "Summons are cleared by area damage and slowed by an armour aura — kill the army, not the hero.":
        "Призывы зачищаются уроном по площади и замедляются аурой брони — убивайте армию, а не героя.",
    "Their plan is to out-sustain you; healing reduction turns their whole draft off.":
        "Их план — пересидеть вас по отхилу; снижение лечения полностью выключает их драфт.",
    "Their sustain lets them win long fights — anti-heal or a hard burst window is the answer.":
        "Их отхил позволяет им выигрывать затяжные бои — ответ это анти-хил или окно под жёсткий бурст.",
    "True strike is the only reliable answer to evasion — otherwise a third of your attacks miss.":
        "Точный удар — единственный надёжный ответ на уклонение, иначе треть ваших атак промахивается.",
    "You cannot fight what you cannot see; truesight turns their invisibility pickoff into your kill.":
        "Нельзя драться с тем, чего не видишь; трусайт превращает их пикофф из невидимости в ваше убийство.",
    "A silence stops you casting your escape or ultimate — a dispel removes it instantly.":
        "Сайленс не даёт применить эскейп или ульту — диспел снимает его мгновенно.",
    "They win by keeping you at range; a gap-closer or reposition tool is worth more than more damage.":
        "Они выигрывают, держа вас на дистанции; сближение или инструмент репозиции ценнее дополнительного урона.",
    "Their escape is how they survive your gank — a silence, root or disarm stops the escape, not the damage.":
        "Их эскейп — так они выживают в вашем ганге; остановить эскейп помогает сайленс, рут или обезоруживание, а не урон.",
    "They reposition out of every fight; hard control that lands before they move is the answer.":
        "Они перепозиционируются в каждом бою; ответ — жёсткий контроль, который попадает раньше их движения.",
    "Their save turns your kill into a wasted cooldown — silence the saver or burst through the window.":
        "Их спасение превращает ваше убийство в потраченный кулдаун — засайленсьте спасающего или продавите окно бурстом.",
    "Raw HP needs percentage or armour-reduction damage, not another damage item.":
        "Против чистого запаса здоровья нужен процентный урон или снижение брони, а не ещё один предмет на урон.",
    "They are built to neutralise a carry — buy the item that denies their one combo and keep farming.":
        "Они собраны, чтобы нейтрализовать керри — купите предмет, который отменяет их единственное комбо, и продолжайте фармить.",
    "They punish magic damage, so lean into physical or immunity rather than more spells.":
        "Они наказывают магический урон, поэтому делайте ставку на физический урон или неуязвимость, а не на новые заклинания.",
    "They cut your healing, so burst windows matter more than drawn-out fights.":
        "Они режут ваше лечение, поэтому окна бурста важнее затяжных боёв.",
    "They clear illusions instantly — if you rely on them, fight around your cooldowns, not your army.":
        "Они мгновенно зачищают иллюзии — если вы на них опираетесь, играйте вокруг кулдаунов, а не вокруг армии.",
    "They win by splitting the map; you need the mobility to answer a lane without losing your own.":
        "Они выигрывают через сплит карты; вам нужна мобильность, чтобы отвечать на линии, не теряя свою.",
    "They win by taking buildings early — defensive auras let you fight in front of your own tower.":
        "Они выигрывают, забирая башни рано — защитные ауры позволяют драться у своей башни.",
    "They hunt isolated heroes; vision and an auto-triggering buffer are what stop the gank.":
        "Они охотятся на одиноких героев; ганг останавливают вижен и автоматически срабатывающий щит.",
    "Their initiation decides the fight — survive the first two seconds and the fight is yours.":
        "Их инициация решает бой — переживите первые две секунды, и бой ваш.",
    "They are stronger in a straight 5v5; an aura or immunity item lets you contest the fight at all.":
        "Они сильнее в прямом замесе 5 на 5; аура или предмет на неуязвимость позволяют хотя бы навязать бой.",
    # items to avoid
    "Pure armour does almost nothing against a magical draft.":
        "Чистая броня почти бесполезна против магического драфта.",
    "Armour does not reduce magical burst — the gold is better spent on magic resistance.":
        "Броня не снижает магический бурст — золото лучше потратить на сопротивление магии.",
    "Pure damage ignores resistance, so resistance items are wasted gold.":
        "Чистый урон игнорирует сопротивление, поэтому предметы на сопротивление — выброшенное золото.",
    "Stacking more evasion does not beat an enemy that already ignores yours.":
        "Ещё больше уклонения не поможет против врага, который и так его игнорирует.",
    "Long-cooldown sustain loses the attrition war to a healing draft.":
        "Предметы на отхил с долгим кулдауном проигрывают войну на истощение драфту с лечением.",
    "They punish magic damage, so more of it is the worst possible purchase.":
        "Они наказывают магический урон, поэтому больше магии — худшая возможная покупка.",
    "Magic resistance does nothing against a physical draft.":
        "Сопротивление магии бесполезно против физического драфта.",
    "which item answers which threat": "какой предмет отвечает на какую угрозу",
    "_hs_item_catalogue_done": "",
}

# The My Hero Strategy catalogue is an exact-match table like RU_EXACT, so it
# is merged into the single lookup the translator already consults.
RU_EXACT.update(HS_EXACT)

# Lane names, used inside the "likely laned in the X" sentence.
RU_LANES = {
    "safelane": "безопасной линии",
    "mid": "средней линии",
    "offlane": "сложной линии",
    "support": "линии поддержки",
    "jungle": "лесу",
}

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
    "heavy burst damage": "мощный бурст-урон",
    "heavy teamfight": "мощные замесы",
    "heavy push": "мощный пуш",
    "heavy sustain": "мощный отхил",
    "healing reduction needed": "нужно снижение лечения",
    "targeted disables": "одиночный контроль",
}


def _problem_ru(text: str) -> str:
    # The engine can join several problems with commas; translate each part.
    parts = [p.strip() for p in text.split(",")]
    return ", ".join(RU_PROBLEMS.get(p.lower(), p) for p in parts)


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



# Fragments used inside "you can fight this hero when you ..." sentences.
RU_FIGHT_FRAGMENTS = {
    "fight after their burst combo is spent": "деритесь после того, как их бурст-комбо потрачено",
    "fight the moment their disable is on cooldown": "деритесь в момент, когда их контроль на кулдауне",
    "fight with healing reduction applied": "деритесь с применённым снижением лечения",
    "fight once you have true strike": "деритесь, когда у вас есть точный удар",
    "fight when you can chain control so it cannot escape": "деритесь, когда можете зацепить контроль, чтобы он не убежал",
    "fight when you have a numbers advantage": "деритесь при численном преимуществе",
}


def _hs_fragments_ru(text: str) -> str:
    """Translate the comma-joined fight-window fragments."""
    parts = [f.strip() for f in text.split(",")]
    return ", ".join(RU_FIGHT_FRAGMENTS.get(part, part) for part in parts)


def _hs_plan_clause_ru(clause: str) -> str:
    """Translate the optional trailing clauses of the one-sentence game plan."""
    clause = clause.strip()
    if not clause:
        return ""
    clause = clause.replace(", and never walk into fog alone", ", и никогда не заходите в туман один")
    clause = clause.replace(
        ", buying healing reduction before the first teamfight",
        ", купив снижение лечения до первого замеса",
    )
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
