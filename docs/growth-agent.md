# Autonomous growth agent

DraftMaster AI ships with a growth engine that runs the acquisition loop by
itself: it decides what to say, writes it, publishes it, measures what happened
and changes its own future behaviour based on the result. It lives in
`services/growth/` and shares the strategy dataset with the product, so every
number it publishes is one the product would also produce.

This document is the operator's manual. For the *strategy* behind it see
[`growth.md`](growth.md).

## Why an agent and not a checklist

The growth plan in `growth.md` is a sequence of tasks: post the methodology,
demo creators, publish patch reports, keep SEO fresh. Every one of those is
recurring, data-driven and low-judgement — exactly the kind of work that rots
when it depends on a human remembering to do it. The agent exists so the plan
executes on a schedule whether or not anyone is watching.

It is deliberately *not* a large language model in the loop for the facts. The
engine is deterministic: the same day, dataset and state produce the same plan.
A language model can be added later to vary the prose, but the numbers and the
decisions come from code that can be tested and audited.

## The loop

```
        ┌─────────────────────────────────────────────────────────┐
        │                                                         │
        ▼                                                         │
   ┌─────────┐   ┌────────┐   ┌────────┐   ┌─────────┐   ┌────────┴──────┐
   │ measure │──▶│ decide │──▶│ create │──▶│ publish │──▶│ record/learn  │
   └─────────┘   └────────┘   └────────┘   └─────────┘   └───────────────┘
    outcomes      topics +     content +    channels       store + bandit
    → variants    variant      scripts      (dry or live)  → next choice
```

1. **measure** — pull the product's own funnel numbers (`/api/metrics`) and
   attribute them to content variants. With no analytics configured, it records
   publication volume so the bandit still rotates off the least-tested variant.
2. **decide** — build the topic pool from the dataset (meta movers, per-hero
   matchups, per-hero guides, the Panic demo), drop anything already published,
   rotate to a fresh slice, and pick the variant the bandit currently favours.
3. **create** — render each topic into a `ContentItem`, build video scripts,
   and generate personalised outreach messages.
4. **publish** — hand each item to its channel. The blog channel always writes
   files; social channels only send when enabled *and* credentialed *and* the
   global publish switch is on.
5. **record/learn** — persist everything to the state file and update per-variant
   statistics that the bandit reads next cycle.

## Determinism

The engine never calls `random`. Exploration is a deterministic rotation keyed
on the number of observations seen so far. Two runs over the same state pick the
same variant; the topic ring advances by a counter, not a clock. This is what
makes a dry run reviewable and the tests meaningful — `plan` twice and diff.

## Safety model

| Layer | Default | How to enable |
| --- | --- | --- |
| Global publish switch | **off** | `DRAFTMASTER_GROWTH_ALLOW_PUBLISH=true` or `--live` |
| Per-channel enable | **off** | `DRAFTMASTER_GROWTH_<CHANNEL>_ENABLED=true` |
| Per-channel credential | **empty** | `DRAFTMASTER_GROWTH_<CHANNEL>_TOKEN=<token>` |
| Blog channel | on (writes files) | always |

A channel is *live* only when all three of its own gates are satisfied. Enabling
a channel without a token does not send anything — it records a dry run. This is
why a fresh clone, CI and the scheduled workflow can all run the full loop with
no secrets and produce useful, inspectable output.

## Channels

| Channel | Credential | Sends |
| --- | --- | --- |
| `blog` | none (writes Markdown) | long-form articles under `data/growth/out/blog/` |
| `discord` | webhook URL in `_TOKEN` | one message per short item |
| `telegram` | bot token in `_TOKEN` (+ `chat_id`) | one message per short item |
| `twitter` | OAuth2 bearer in `_TOKEN` | one tweet per short item |
| `reddit` | OAuth2 bearer in `_TOKEN` (+ `subreddit`) | one self-post |

Adding a channel is a class in `channels.py` and one entry in the `CHANNELS`
registry.

## The self-improvement loop

Each piece is published under a **variant** — a style, not a subject: `hook-first`,
`data-led`, `question`, `listicle`, `story`. Outcomes are folded into per-variant
statistics and the optimizer (`optimizer.py`) chooses the next variant with a
deterministic bandit:

* any variant with fewer than `min_samples` observations is *unproven* and gets
  priority — you cannot judge what you have not tested;
* otherwise, every `1 / exploration_rate`-th pick takes the least-sampled proven
  variant, and the rest exploit the best mean score;
* ties break on the variant name, so the choice is stable.

The score is `clicks + 10 × conversions`: traffic is the lever, a paying customer
is worth an order of magnitude more. `status` prints the ranking and a one-line
recommendation of what the data currently says.

## Operating it

```bash
# Everything below defaults to dry run.
python -m draftmaster_growth plan       # what it would publish today, no side effects
python -m draftmaster_growth run        # one full cycle (dry)
python -m draftmaster_growth run --live # one full cycle, publish to live channels
python -m draftmaster_growth status     # variant ranking, channels, prospects
python -m draftmaster_growth outreach   # generate + review creator messages
python -m draftmaster_growth report     # the latest cycle report

# Useful flags
--state PATH        # override the state file
--out PATH          # override the output directory
--exploration 0.1   # bandit exploration rate
--posts N / --videos N / --no-outreach
```

## Scheduled operation

`.github/workflows/growth.yml` runs a cycle daily at 09:00 UTC, uploads the
output as a build artifact, and commits the state file back to the branch so the
next run continues the rotation and the learning. It runs dry unless the
`live` input is set on a manual dispatch, and real channels stay dark until the
repository secrets are populated. Because the workflow commits `data/growth/`,
that directory (minus generated `out/`) is tracked.

## Extension points

* **New content format** — add a renderer in `content.py` and register it in
  `RENDERERS` under `(kind, locale)`.
* **New topic source** — add a builder in `topics.py`; the selector handles
  dedupe and rotation for free.
* **New channel** — subclass `Channel` in `channels.py`.
* **New metric** — extend `MetricSample.score`; the optimizer picks it up.
* **LLM narration** — the `ContentEngine` renders facts; a post-processor could
  rewrite `body` per variant without touching the numbers. The engine must stay
  the source of every figure.
