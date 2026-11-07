# DraftMaster AI — AI Integration Strategy

## 1. Position: statistical first, generative second

The defining architectural decision is that **the strategy engine is deterministic and
statistical, and language models are used only where language is genuinely the
product.**

Why this matters. A large language model asked "what should I build against Lion,
Axe and Shadow Shaman?" will produce a fluent answer that is unverifiable, changes
between runs, and cannot be backtested. That is unacceptable for advice a player will
act on in a ranked game. Every recommendation in DraftMaster AI therefore comes from
a computation over real match data, and every number is reproducible: the same draft
always yields the same report.

Generative AI is layered *on top* of that foundation, never underneath it.

## 2. Layer 1 — The statistical core (shipped)

| Component | Method |
| --- | --- |
| Counter matrix | Pairwise log-odds from real head-to-head results, shrunk toward neutral by sample size |
| Meta scores | Public and Captain's Mode win rates from the current patch |
| Threat analysis | Capability aggregation across 14 dimensions |
| Item builder | Item-popularity data mixed with draft-derived counter rules |
| Win probability | Attributed additive model on a 50% baseline, rank-compressed |

Everything here is explainable, testable and reproducible. This layer is what makes
the product trustworthy, and it is the layer competitors cannot copy quickly because
it requires the data pipeline, not just a prompt.

### 2.1 The shrinkage estimator

The central statistical claim. For each ordered hero pair we estimate the matchup
advantage and shrink it by sample size:

```
advantage_shrunk = advantage_raw * n / (n + k)
```

This is a James–Stein-style estimator. Without it, a hero with a small sample and a
lucky streak dominates the recommendations; with it, the engine's picks are stable
and defensible. It is also why the engine can honestly label its own confidence.

### 2.2 Calibration as the north star

The engine outputs a probability, so it can be *scored*. The Phase 2 outcome feedback
loop records actual match results and produces a reliability curve: for every bucket
of predicted probability, what was the observed win rate? A well-calibrated engine
sits on the diagonal. This is the single most credible public proof of quality
available to a product like this, and it is only possible because the core is
statistical.

## 3. Layer 2 — Generative coaching (shipped, bounded)

Language models are used for exactly one job today: **the match-ID coach's practice
plan and mistake narration**, where the input is a concrete, already-computed set of
statistics (grades, death clustering, GPM/XPM percentiles) and the output is prose.

Guardrails:
- The model never invents statistics; it only narrates numbers the engine computed.
- The template path is the default and always available. If the model is unavailable
  or returns something unusable, the deterministic text is used instead, so the
  feature never breaks.
- Output is short, specific and actionable, never motivational filler.

## 4. Layer 3 — Planned generative features

Each of these is additive and none can degrade the statistical core.

### 4.1 Natural-language draft query
"Why is BKB so important this game?" → the model answers *from the structured report
the engine already produced*, with citations to the specific sections. Retrieval is
the report itself, so the answer cannot contradict the engine.

### 4.2 Personalised coaching narrative
Given the player's stored profile, recent matches and the current draft, generate a
two-sentence, personalised framing of the plan. The plan itself remains statistical.

### 4.3 Replay narration
Turn a replay timeline into a spoken-style commentary of the player's key decisions.
The timeline is computed; the language is generated.

### 4.4 Draft conversation for captains
A multi-turn assistant over the draft state for five-stacks, where every factual claim
is grounded in the engine's output.

## 5. Model selection

| Use case | Approach | Rationale |
| --- | --- | --- |
| Core engine | No model | Determinism, backtestability, latency |
| Prose narration | Small, fast hosted model | Cheap, low latency, quality is sufficient |
| NL query over a report | Same model with the report as context | Grounding beats model size |
| Screenshot detection | Perceptual hashing (not a neural net) | Runs on CPU, no GPU cost, fully deterministic, testable |

The screenshot detector deserves a note: a CNN would be more robust in principle, but
it would add a GPU dependency, an inference budget and a black box to a pipeline whose
current accuracy on real portraits is 5/5 at 91–99% confidence with a confidence
*margin* gate. The perceptual approach is fast, free, deterministic and testable — the
right engineering trade-off for this stage. A neural detector is the natural upgrade
path when the input distribution widens to live client screenshots with overlays.

## 6. Data as the moat

The most valuable asset this product accumulates is not a model, it is a dataset:

1. **Draft outcome pairs** — what the engine recommended, and whether the player won.
2. **Which recommendations users act on** — revealed preference.
3. **Calibration curves** — predicted vs observed win rate by bracket and patch.

None of this can be bought or scraped; it comes from having real users. It compounds,
it improves the core engine, and it is what makes a later, more sophisticated model
actually better rather than merely larger.

## 7. Cost control

- Generative calls are confined to features that are explicitly premium and cached
  (match coach reports are cached 10 minutes per match/account).
- The core engine costs nothing per request — no API calls, no tokens, no GPU.
- Prompts are short because the engine has already done the reasoning: the model
  receives structured facts, not a request to think.

## 8. Anti-patterns this design rejects

- **LLM-as-oracle** — asking a model to invent draft advice. Unverifiable, unstable,
  unbacktestable.
- **Hallucinated statistics** — any number not produced by the engine is forbidden.
- **Non-determinism in the hot path** — the same draft must always yield the same
  plan, or users cannot build trust or muscle memory.
- **Motivational filler** — every sentence must change a decision.
