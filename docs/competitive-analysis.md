# DraftMaster AI — Competitive Analysis

## 1. The landscape

| Competitor | Category | Strength | Gap DraftMaster AI attacks |
| --- | --- | --- | --- |
| **Dotabuff** | Stats site | Authoritative match and hero data; trusted brand | Tells you *what happened*, not *what to do*; no draft-time advice |
| **OpenDota** | Open API/data | Free, comprehensive, the source of truth | Raw data with no interpretation; unusable during a draft |
| **Stratz** | Stats + analytics | Deep analytics, good visualisations | Analytical, retrospective; not a decision tool under time pressure |
| **Dota Plus** | Valve's assistant | First-party, in-client, hero suggestions | Hero suggestions only; no items, timings, target priority or win conditions |
| **Overwolf apps** (Dota Coach, etc.) | In-game overlays | In-client presence, live overlays | Mostly static or rule-based advice; no dynamic build generation or probability engine |
| **Counter-pick websites** | Counter lookup | Instant, simple, well-indexed | A single recommendation with no reasoning, no build, no plan |
| **YouTube / guide sites** | Content | High trust, human insight | Patch-lagged, generic, not draft-specific, not searchable in 5 seconds |
| **A generic LLM chat** | AI | Fluent, flexible | Unverifiable, non-reproducible, cannot be backtested, hallucinates statistics |

## 2. The real competitor

The genuine competitor is not any of the above. It is **"I'll just pick what I know."**

The majority of ranked players, under time pressure, pick a comfort hero and buy a
familiar build. Beating that behaviour requires the alternative to be *faster* than
doing nothing — which is why the sub-5-second budget and the one-screen constraint are
product requirements, not polish.

## 3. Positioning

```
                    High trust / verifiable
                              ▲
                              │
              Dotabuff ●      │      ● DraftMaster AI
              OpenDota ●      │      ● Stratz (analytics)
              Dota Plus ●     │
                              │
   Retrospective ◄────────────┼────────────► Actionable / in-the-moment
                              │
        Guides ●              │      ● Counter-pick sites
        YouTube ●             │      ● Overwolf apps
                              │      ● LLM chat
                              ▼
                    Low trust / unverifiable
```

DraftMaster AI aims to be the only product in the top-right quadrant: verifiable
(because it is statistical and backtestable) **and** actionable in the moment.

## 4. Defensibility

### 4.1 What is easy to copy
- The UI. Anyone can build a dark hero grid in a week.
- The feature list. "Best picks, items, win conditions" is a checklist.
- Prompting a model to write draft advice. Trivial to build, impossible to trust.

### 4.2 What is hard to copy
1. **The shrinkage-calibrated counter matrix.** Raw matchup tables are published
   everywhere; a properly shrunk estimator, validated against outcomes, is not.
2. **The dynamic item engine.** Static builds are copyable. Deriving a build from
   draft-derived threats *with a written reason for each item* requires the capability
   model and the item-popularity pipeline.
3. **Calibration data.** Predicted-vs-observed curves require real users playing real
   games. This compounds and cannot be bought.
4. **The outcome feedback loop.** Knowing which recommendations were followed *and*
   whether the game was won is a proprietary dataset.
5. **Speed.** Sub-5-second, one-screen output is an engineering constraint that
   competitors with heavier architectures cannot match by adding a feature.

### 4.3 The moat in one sentence
Competitors publish statistics; DraftMaster AI accumulates **validated
recommendations** — and the validation is what compounds.

## 5. Feature comparison

| Capability | Dotabuff | Stratz | Dota Plus | Overwolf apps | Counter sites | DraftMaster AI |
| --- | --- | --- | --- | --- | --- | --- |
| Hero suggestion | partial | partial | ✅ | ✅ | ✅ | ✅ |
| Explanation of *why* | — | partial | — | partial | — | ✅ |
| Dynamic item build | — | — | partial | partial | — | ✅ |
| Items to avoid | — | — | — | — | — | ✅ |
| Skill build & talents | — | — | — | ✅ | — | ✅ |
| Match timeline plan | — | — | — | — | — | ✅ |
| Win conditions | — | — | — | — | — | ✅ |
| Kill priority | — | — | — | — | — | ✅ |
| Power spikes | — | partial | — | — | — | ✅ |
| Win probability + attribution | — | partial | — | — | — | ✅ |
| Screenshot detection | — | — | — | — | — | ✅ |
| Match-ID coaching | ✅ (data) | ✅ | partial | partial | — | ✅ (graded + plan) |
| Sub-5s one-screen mode | — | — | ✅ | ✅ | ✅ | ✅ |
| Reproducible / backtestable | ✅ | ✅ | ✅ | — | — | ✅ |

## 6. Threats and responses

| Threat | Likelihood | Response |
| --- | --- | --- |
| Valve ships draft advice in Dota Plus | Medium | Go deeper than first-party ever will (attribution, dynamic items, coaching) and move faster on patch changes |
| An existing stats site adds an "AI" feature | High | They add a wrapper; we own the calibration data and the feedback loop |
| An LLM vendor ships a general Dota agent | Medium | Grounding and validation still require the pipeline; we integrate models rather than compete with them |
| Data access is restricted by Valve/OpenDota | Low–Medium | The pipeline is source-agnostic; artifacts are versioned and committed, and the engine has no runtime data dependency |
| A free clone appears | High | Feature parity is cheap; accuracy and calibration are not. Publish the calibration curve as public proof. |

## 7. Why now

1. **OpenDota and Valve's APIs are rich and free**, making a real statistical
   foundation accessible to a small team.
2. **Player sophistication is rising.** Ranked players increasingly understand that
   draft and itemisation decide games, which creates demand for the specific
   "how do I win this one" answer.
3. **Generative AI makes narration cheap**, so the remaining engineering effort goes
   into the part that actually creates value — the statistics.
4. **No incumbent occupies the top-right quadrant.** Stats sites are retrospective,
   overlay apps are shallow, counter sites are one-liners, and LLM chat is
   unverifiable.

The window exists because the hard part — a validated, calibrated, dynamic
recommendation engine — is not something a weekend project can credibly fake.
