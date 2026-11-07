# DraftMaster AI — UI Component Map & Wireframes

## 1. Design direction

Dark, dense, portrait-led. The interface should read like a professional analyst's
tool, not a mobile game: deep slate surfaces, a single green accent for "your side",
a single red accent for "danger", and gold reserved for money and timings.

The one rule that shapes every screen: **the decision comes first, the reasoning
comes second.** Nothing important may sit below the fold during a live draft.

## 2. Design tokens

| Token | Value | Use |
| --- | --- | --- |
| `base.950` | `#07090d` | Page background |
| `base.900/850/800` | `#0b0f16` / `#0f141d` / `#141a25` | Surfaces |
| `base.700/600` | `#1c2431` / `#27313f` | Borders, dividers |
| `radiant` | `#38e07b` | Player side, positive scores, primary CTA |
| `dire` | `#ff4d4d` | Danger, panic CTA, negative scores |
| `gold` | `#f2c14e` | Item cost, timings, premium |
| `magic` | `#7c5cff` | Talents, skill build |

Score colouring is consistent everywhere: **≥ 70 green, 55–69 gold, < 55 red.**
Danger levels are consistent everywhere: **low 0–39, medium 40–64, high 65+.**

Component classes: `.card`, `.card-pad`, `.chip`, `.btn-primary`, `.btn-danger`,
`.btn-ghost`, `.label`, `.section-title`, `.bar`.

## 3. Component tree

```
app/layout.tsx
└── app/page.tsx  (client shell: tab state, hero fetch, analysis actions)
    ├── Header
    │   ├── logo + wordmark
    │   ├── tabs: I'M LAST PICK · Full Report · Screenshot · Match Coach · Meta Intel
    │   ├── patch chip
    │   └── plan toggle (Free ⇄ Premium)
    │
    ├── Hero section (value prop + primary CTAs)
    │   ├── headline + explanation
    │   ├── btn-danger  "I'M LAST PICK"
    │   ├── btn-primary "One Click Win Plan™"
    │   ├── elapsed chip ("answered in 15 ms")
    │   └── DraftSummaryRail
    │       ├── 5 enemy slots (portrait or dashed placeholder)
    │       ├── DraftControls (role chips · rank chips)
    │       └── UsageBar
    │
    ├── Draft workspace (tabs: lastpick | draft)
    │   ├── HeroGrid            ← search, role filters, portrait grid, cap 5
    │   └── ResultPane
    │       ├── ErrorBanner
    │       ├── LoadingCard
    │       ├── EmptyState
    │       ├── PanicView       (lastpick)
    │       └── ReportView      (draft)
    │
    ├── ScreenshotPanel   (tab: screenshot)
    ├── CoachPanel        (tab: coach)
    └── MetaPanel         (tab: meta)
```

### PanicView

```
├── OneSentencePlan              ← the take-away, always first
└── grid lg:2
    ├── decision column
    │   ├── #1 hero portrait + name + roles + pick score
    │   ├── why-this-hero line
    │   ├── WinProbabilityBar (compact)
    │   └── backups #2–#5 (portrait + name + score)
    └── intel column
        ├── Full build chips (hover → reason)
        ├── Key counters
        ├── Kill order | Danger heroes (two columns)
        └── Do-not-build chips
└── three win conditions (primary / secondary / emergency)
└── footer: latency · plan · remaining · "Open the full 11-section report →"
```

### ReportView

```
├── Card  header: analysed hero · one-sentence plan · headline threat chips
│         right:  WinProbabilityBar + WinProbFactors (attributed percentage points)
├── Card  1 · Best Picks            → BestHeroCard ×5
├── Card  2 · Why This Hero Works   → reasons + strong-into chips
├── Card  3 · Complete Threat Analysis → StatRow ×14 + legend
├── Card  4 · Dynamic Item Builder  → key counters, 8 phases, items to avoid
├── grid  5 · Skill Build (1–30 level pills)  |  6 · Talent Tree
├── Card  7 · Match Plan            → 5 windows × 7 fields
├── grid  8 · Win Conditions        |  9 · Target Priority
├── Card 10 · Power Spike Engine    → your spikes | enemy spikes
└── Card 11 · One-Sentence Win Plan
```

### Primitive components

| Component | File | Responsibility |
| --- | --- | --- |
| `Card` | `components/Card.tsx` | Titled surface with icon and action slot |
| `Bar` / `StatRow` | `components/Bar.tsx` | Score bar with consistent colouring |
| `HeroPortrait` | `components/HeroPortrait.tsx` | CDN portrait with initials fallback |
| `HeroGrid` | `components/HeroGrid.tsx` | Search + role filter + selection grid |
| `DraftControls` | `components/DraftControls.tsx` | Role and rank chips |
| `WinProbabilityBar` | `components/WinProbability.tsx` | Probability bar + verdict |
| `WinProbFactors` | `components/WinProbability.tsx` | Attributed factor list |
| `BestHeroCard` | `components/ReportCards.tsx` | Ranked pick with sub-scores |
| `ItemBuildCard` | `components/ReportCards.tsx` | Eight-phase build + avoid list |
| `ThreatCard` | `components/ReportCards.tsx` | 14-dimension threat grid |
| `TargetPriorityCard` | `components/ReportCards.tsx` | Ranked kill order |
| `PowerSpikeCard` | `components/ReportCards.tsx` | Player vs enemy spikes |
| `WinConditionsCard` | `components/ReportCards.tsx` | Primary/secondary/emergency |
| `OneSentencePlan` | `components/ReportCards.tsx` | The headline take-away |
| `PanicView` | `components/PanicView.tsx` | One-screen draft answer |
| `ReportView` | `components/ReportView.tsx` | 11-section report |
| `ScreenshotPanel` | `components/panels/ScreenshotPanel.tsx` | Drag-drop + detection results |
| `CoachPanel` | `components/panels/CoachPanel.tsx` | Match-ID coach with grades |
| `MetaPanel` | `components/panels/MetaPanel.tsx` | Trending, winners, losers |
| `UsageBar` | `components/panels/UsageBar.tsx` | Free/premium quota meter |

## 4. Wireframes

### Desktop — Panic Mode (1440px)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ⬡ DraftMaster AI        [🚨 I'M LAST PICK][Full Report][Screenshot]… 7.41 ★ │
├──────────────────────────────────────────────────────────────────────────────┤
│ Your enemy draft is already decided.        │  Enemy draft                   │
│ Now win the game.                           │  [🦁][🪓][🐍][ ][ ]            │
│ DraftMaster AI turns the enemy lineup into  │  Carry  Mid  Off  Sup  HSup    │
│ one actionable plan…                        │  …rank chips…                  │
│ [🚨 I'M LAST PICK] [One Click Win Plan™]    │  ▓▓▓▓░░ 2 of 3 left today      │
├──────────────────────────────────────────────┴───────────────────────────────┤
│ ┌─ Enemy draft input ──────┐ ┌─ ONE-SENTENCE WIN PLAN ─────────────────────┐ │
│ │ 🔍 search…               │ │ "If you get BKB on time, kill Axe first…"    │ │
│ │ [All][Carry][Support]…   │ ├──────────────────────┬───────────────────────┤ │
│ │ [🦁][🪓][🐍][🏹][🐗]…     │ │ #1 BEST PICK         │ FULL BUILD            │ │
│ │  (portrait grid)         │ │  Lone Druid   62.6   │ Mjollnir Maelstrom…   │ │
│ │                          │ │  Carry·Pusher·Dur.   │ KEY COUNTERS          │ │
│ │                          │ │  "Wins the matchup…" │ BKB Aeon Heart        │ │
│ │                          │ │ ▓▓▓▓▓▓▓░░░ 71.7%     │ KILL ORDER | DANGER   │ │
│ │                          │ │ Backups #2 #3 #4     │ 1 Axe      | Axe 44   │ │
│ └──────────────────────────┘ └──────────────────────┴───────────────────────┘ │
│ ┌ Primary WC ────────────┐ ┌ Secondary WC ────────┐ ┌ Emergency WC ────────┐ │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Mobile — Panic Mode (390px)

```
┌─────────────────────────────┐
│ ⬡ DraftMaster AI   [🚨][📊] │
├─────────────────────────────┤
│ One-Sentence Win Plan       │  ← always first
│ "If you get BKB on time…"   │
├─────────────────────────────┤
│ [🦌] #1 BEST PICK     62.6  │  ← the decision, no scroll
│      Lone Druid             │
│      Carry · Pusher         │
│ ▓▓▓▓▓▓▓░░░ 71.7% vs 28.3%   │
├─────────────────────────────┤
│ FULL BUILD                  │
│ Mjollnir · Maelstrom · …    │
│ KEY COUNTERS                │
│ BKB · Aeon Disk · Heart     │
│ KILL ORDER    DANGER HEROES │
│ 1 Axe          Axe 44       │
├─────────────────────────────┤
│ Primary / Secondary /       │
│ Emergency win conditions    │
└─────────────────────────────┘
```

## 5. Interaction details

- **Hero grid** — click toggles selection; selection is capped at five and
  order-preserving, so muscle memory keeps working. Selected heroes show a red ring
  and a check badge.
- **Item chips** — hover (desktop) or tap reveals the written reason. The reason is
  never hidden behind a click on mobile.
- **Skill build pills** — colour-coded by kind (basic / ultimate / talent / stats);
  the tooltip carries the level-by-level reason.
- **Tab switching** — instant; state is client-side, so no refetch occurs.
- **Latency chip** — the measured round-trip is displayed after each analysis. Speed
  is a marketing claim, so it is shown rather than asserted.
- **Plan toggle** — flips the free/premium header state and persists it locally;
  drives the `authorization` header sent to the API.

## 6. Accessibility

- Semantic landmarks (`header`, `main`, `section`, `footer`, `nav`).
- Visible focus rings on every interactive element (`focus-visible:ring`).
- `aria-pressed` on hero selection buttons; `aria-label` on icon-only buttons.
- Colour is never the sole carrier of meaning: danger levels pair colour with a text
  label, and scores always print the number.
- Touch targets are at least 32×32 px on mobile.
