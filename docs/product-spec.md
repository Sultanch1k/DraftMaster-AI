# DraftMaster AI — Product Specification

## 1. Vision

DraftMaster AI exists to answer one question better than any human coach can, at the
speed the draft demands: **"How do I win this specific game?"**

The Dota 2 market is saturated with counter-pick websites and static guides. All of
them stop one step short of value. They answer "which hero?" and leave the player to
work out items, timings, target priority and win conditions alone — precisely the
decisions that actually determine the outcome.

DraftMaster AI closes that gap. It converts a draft into a plan.

### Positioning statement

> For competitive Dota 2 players who lose games they were favoured to win,
> DraftMaster AI is an AI draft coach that turns the enemy lineup into a complete,
> actionable win plan in under five seconds. Unlike counter-pick tools, DraftMaster
> AI is built on a statistically shrunk matchup model and a dynamic item engine, so
> its advice changes with *your* draft, *your* role and *your* bracket.

### The insight

Draft advantage is real, measurable, and — critically — **convertible**. A 60/40 draft
is not a 60% win; it is a 60% win only if the player executes the right plan. Existing
tools measure the edge. DraftMaster AI measures it *and* supplies the plan that
converts it. That is the product.

## 2. Target users

| Persona | Rank | Behaviour | What they need |
| --- | --- | --- | --- |
| **The Ranked Climber** (primary) | Legend–Divine | Plays 3–8 ranked games a night, watches replays, uses Overwolf tools | A pre-game edge that compounds across hundreds of games |
| **The Last Picker** | Any | Frequently picks last and must decide in seconds | Panic Mode: a decision, not a report |
| **The Captain** | Ancient–Immortal | Drafts for a five-stack | Full reports, target priority, win conditions |
| **The Learner** | Herald–Archon | Wants to understand *why* | The reasoning on every recommendation |
| **The Content Creator** | Any | Streams drafts | A shareable, screenshot-worthy output |

### Jobs to be done

1. "I have 20 seconds left on the pick timer — tell me what to pick and what to build."
2. "We lost a game we should have won — tell me what went wrong."
3. "I want to climb — give me a repeatable process I can trust."

## 3. Product principles

1. **Speed is a feature.** Panic Mode must return in under five seconds, and it must
   fit on one screen. A perfect answer that arrives after the pick timer is worthless.
2. **Every recommendation is explained.** A number without a reason cannot be learned
   from and will not be trusted.
3. **Dynamic over static.** No hand-written builds. Every item, skill point and plan
   step is generated from the specific enemy draft and live match data.
4. **Honest uncertainty.** Confidence levels, rank compression and explicit
   attributions are shown. Overstating certainty destroys long-term trust.
5. **Mobile first.** Drafts happen on phones as often as on desktop.

## 4. Feature specification

### 4.1 ONE CLICK WIN PLAN™ (flagship)

**Trigger:** one button, after selecting 1–5 enemy heroes.
**Output:** an 11-section report on a single page.
**Latency budget:** < 300 ms server-side (measured: ~2–15 ms for the report itself;
the UI shows total round-trip).

Sections: best picks (#1–#5 with eight scores each), why this hero works, threat
analysis (14 dimensions), dynamic item builder, skill build 1–30, talent tree, match
plan (5 windows), win conditions (primary/secondary/emergency), target priority,
power spike engine, one-sentence win plan.

**Acceptance criteria**
- Every section renders for any 1–5 hero enemy draft and any role.
- No section is empty; when data is unavailable the section states why.
- The one-sentence win plan always names a concrete timing, a target and a condition.

### 4.2 PANIC MODE — "I'M LAST PICK" 🚨

**Trigger:** a dedicated red button.
**Output:** `#1 hero`, `full build`, `danger heroes`, `power spikes`, `kill priority`,
`win condition`, `items to avoid`, `one-sentence win plan`.
**Constraint:** the entire decision must be visible without scrolling on a 390×844
viewport.

**Why it is the viral feature:** it solves the single most stressful, most time-boxed
moment in the game, and its output is inherently screenshot-worthy. It is the feature
people will tell their friends about.

### 4.3 Enemy draft input

- Visual portrait grid of all 127 heroes, 5–12 per row by breakpoint.
- Instant name search (localised name and internal name).
- Role filter chips.
- Selection capped at 5, order-preserving, with a counter.
- Full keyboard/desktop and touch/mobile support.
- **Target:** five heroes selected in under five seconds.

### 4.4 Threat analysis

Fourteen scored dimensions with per-dimension danger levels: magic, physical, pure,
burst, sustain, crowd control, teamfight potential, pickoff potential, push, split
push, Roshan, early game, mid game, late game.

### 4.5 Dynamic item builder

Phases: starting, lane, early, mid, late, luxury, situational, emergency — plus
**items to avoid**. Every item carries a written reason and its source (meta
popularity or counter to the enemy draft). Counter items are derived, not curated:
the engine detects disable chains, illusion reliance, heal reliance, evasion, invis
and split-push, and proposes the corresponding answer with an explanation.

### 4.6 Skill build, talents, match plan, win conditions, target priority, power spikes

As described in the README. The match plan covers five time windows and, for each,
objectives, farm focus, fight focus, map movement, tower priority, Roshan priority
and danger zones.

### 4.7 WIN PROBABILITY ENGINE™

Input: enemy draft, player hero, role, rank.
Output: player win probability, enemy win probability, a confidence label, an
attributed factor list (percentage points), and a verdict sentence.

Factors: hero matchups, meta strength, threat mismatch, game clock, role fit, and
execution reliability (rank compression). The attribution is the differentiator: the
user sees *why* the number is what it is.

### 4.8 Screenshot analyzer

Upload a draft screenshot → heroes are detected → the full report is generated
automatically. Detection is a two-stage perceptual pipeline (coarse scan, then
pixel-level refinement) gated by both a confidence floor and a runner-up margin.
Measured: 5/5 correct on a composited five-hero draft row at 91–99% confidence.

### 4.9 Match-ID coach

Enter a public match ID → the engine pulls the match from OpenDota and returns a
verdict, letter grades for farm / XP / last hits / fighting / survival, strengths,
mistakes, item notes, timing notes and a practice plan. Cached per match.

### 4.10 Personal AI coach & comfort pick engine

Stored profile: role, rank, favourite heroes, comfort scores, playstyle, recent
matches. Recommendations re-weight automatically. Comfort feeds 20% of the final
pick score, so the engine recommends heroes the player can actually play.

### 4.11 Meta intelligence

Trending heroes by pick rate; patch winners and losers by Captain's Mode win rate;
patch stamp. Refreshed by re-running the pipeline.

## 5. User flows

### 5.1 Panic Mode (the critical path)

```
Draft screen open
   │
   ├─ tap "I'M LAST PICK"            (0.5 s)
   ├─ tap 3–5 enemy portraits         (2–3 s)
   ├─ tap "I'M LAST PICK" again       (0.2 s)
   │
   └─► one-screen plan                (< 5 s total, target met)
```

### 5.2 Full report

```
Select enemies → select role + rank → "One Click Win Plan" → scroll 11 sections
→ copy the one-sentence plan into team chat
```

### 5.3 Screenshot

```
Capture draft → open Screenshot tab → drop image → detected heroes render with
confidence → full report appears below
```

### 5.4 Match review

```
Copy match ID → Match Coach tab → paste → grades + practice plan
```

### 5.5 Free → premium conversion

```
Free user hits 3 analyses → 402 with an explicit upgrade message → Premium toggle
```

## 6. Non-functional requirements

| Requirement | Target |
| --- | --- |
| Panic Mode latency (server) | < 300 ms p95 (measured ~2–15 ms) |
| Full report latency (server) | < 500 ms p95 |
| Screenshot analysis | < 5 s p95 for a 1600px image |
| Cold start | < 3 s (dataset loaded once at boot) |
| Availability | 99.5% monthly |
| Mobile | Fully usable at 360px width |
| Accessibility | Visible focus rings, semantic landmarks, AA contrast on body text |
| Zero-dependency local run | SQLite + in-memory cache with no configuration |

## 7. Out of scope (v1)

Live in-game overlay, real-time GSI integration, hero-voice lines, native mobile
apps, tournament-grade scrim tooling, and any form of automated gameplay input.
DraftMaster AI advises; it never plays the game for the user.

## 8. Success metrics

| Metric | Definition | 90-day target |
| --- | --- | --- |
| Activation | % of signups who run one analysis | 70% |
| Panic Mode usage | Panic runs per active user per week | ≥ 5 |
| Retention | D7 / D30 | 35% / 18% |
| Conversion | Free → Premium | 4% |
| Virality | Shares per 100 Panic runs | ≥ 8 |
| Accuracy proxy | User-reported "advice matched my game" | ≥ 80% |
