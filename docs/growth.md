# DraftMaster AI — Growth & Launch Strategy

## 1. The growth thesis

DraftMaster AI grows through a single mechanism: **Panic Mode is a demonstrable
moment.** In a game where players share screenshots constantly, a one-screen answer
that names the exact hero, the exact item and the exact kill order is inherently
postable. Every share is a product demo.

Growth strategy follows from that: engineer the share, then remove every reason not to
try it.

## 2. The viral loop

```
Player is in a draft
        │
        ├─ opens Panic Mode ──────────────► gets a one-screen plan in <5s
        │
        ├─ the plan wins (or explains a loss)
        │
        └─ shares the screenshot with friends / Discord / stream chat
                        │
                        ▼
              New player sees a concrete result, not a feature list
                        │
                        ▼
              Tries Panic Mode on their own draft (no signup required)
```

**Critical design choices that make the loop work:**
1. **No signup to try it.** The first analysis is anonymous. Requiring an account
   before demonstrating value is the most common way tools like this die.
2. **Screenshot-ready output.** Panic Mode fits one screen by construction, so it can
   be captured and shared without editing.
3. **Instant, visible speed.** The latency chip ("answered in 15 ms") makes the
   product's core claim self-evident.
4. **Auto-rendered share images (Phase 1).** A one-tap "share this plan" that renders
   a branded PNG with the draft and the one-sentence plan. Branding lives in the
   share, not on the site.

## 3. Launch sequence

### Phase 0 — Seeding (2 weeks before launch)
- Post the calibration methodology (shrinkage, rank compression) to r/Dota2 and
  r/TrueDoTA2 as a *technical* write-up, not an ad. The audience that cares about
  statistics is the audience that will audit the product — and survive the audit.
- Recruit 20–30 high-MMR players (Ancient–Immortal) as testers via Discord
  communities. Their feedback fixes accuracy before public scrutiny begins.
- Prepare a 60-second demo: a real draft, real time pressure, a real answer.

### Phase 1 — Launch week
- **Day 1 — Reddit.** r/Dota2 with the technical write-up and a link to a
  no-signup Panic Mode. Lead with the *method*, not the feature list.
- **Day 2 — Content creators.** Send 10 mid-size Dota creators a personalised demo
  of their own recent draft. Not a press release — their draft, their heroes, their
  plan. The conversion rate of a personalised demo is far higher than any cold pitch.
- **Day 3 — Discord.** Post in Dota community servers with the demo GIF.
- **Day 4 — Twitter/X.** Clip-based posts: "the pick timer had 8 seconds left".
- **Day 5 — Product Hunt.** Position as "an AI coach that tells you how to win the
  game, not which hero to pick".

### Phase 2 — Compounding (weeks 2–8)
- **Patch reports.** Publish an automatic meta report within 24 hours of every patch.
  This is a recurring, newsworthy event that costs one script run.
- **Draft-of-the-day.** A public, shareable analysis of a notable pro match draft.
  Free content, constant freshness, real engagement.
- **Calibration transparency.** Publish the reliability curve once there is enough
  outcome data. Nobody else does this, and it converts skeptics.

## 4. Channel priorities

| Channel | Cost | Reach | Trust | Priority |
| --- | --- | --- | --- | --- |
| Reddit technical write-ups | Low | High | Medium | **1** |
| Creator demos (personalised) | Low | Medium | **High** | **1** |
| Discord communities | Low | Medium | High | 2 |
| Product Hunt | Low | Medium | Low | 3 |
| Twitter/X clips | Low | Medium | Medium | 3 |
| SEO (hero pages, "X vs Y") | Medium | **High** | Medium | 2 (long term) |
| Paid ads | High | High | Low | Never (at this stage) |

SEO deserves a note: a page per hero matchup, generated from the same counter matrix,
is a compounding, low-cost acquisition channel that scales with the product's own data.
It is deliberately Phase 2 so the product is proven before content investment begins.

## 5. Activation and retention

**Activation is one event: the first Panic Mode run.** Everything before it is
friction to remove; everything after it is retention to earn.

| Funnel step | Target | How |
| --- | --- | --- |
| Landing → first analysis | 40% | No signup, one-screen input, obvious CTA |
| First analysis → second session | 50% | The plan must visibly change a decision |
| D7 retention | 35% | Session habit: open during the draft |
| D30 retention | 18% | Progress tracking + patch reports |
| Free → Premium | 4% | Paywall hit mid-session at highest intent |

## 6. Community as a moat

- **Public Discord** where patch discussions happen. The people who argue about drafts
  are the ideal users and the best source of validation.
- **Immortal advisors.** Recruit a small group of high-MMR players as named advisors
  whose drafts are analysed publicly. Their credibility transfers to the product, and
  they get an audience.
- **Open methodology.** Publish how the counter matrix and win probability are
  computed. In a niche where everyone claims to have "AI", being auditable is a
  differentiator.

## 7. Launch metrics and kill criteria

**Track from day one:** activated users, Panic Mode runs per user per week, D1/D7/D30
retention, free→premium conversion, shares per 100 runs, and screenshot-detection
confidence distribution.

**Iterate if:** activation < 30% (input is too slow) or D7 < 20% (the plan is not
changing decisions).

**Pivot the positioning if:** usage concentrates in the match-coach feature rather than
draft-time advice — that would mean the audience wants retrospective learning more than
in-draft decisions, which is a different (and equally valid) product.

**Do not do:** pay for installs before retention is proven. Buying users into a leaky
funnel hides the leak and burns the budget that should fund accuracy work.

## 8. The one-sentence growth plan

Make the first analysis free, instant and screenshot-worthy, publish the methodology so
it survives scrutiny, and let the players who win games do the marketing.

## 9. The autonomous growth agent

The recurring parts of this plan — patch reports, matchup content, creator
outreach, SEO upkeep — are executed by a self-improving agent in
`services/growth/`. It shares the strategy dataset with the product, so it can
only publish numbers the product would also produce, and it runs dry by default.

It closes the loop a human-run plan cannot:

* **decides** what to say from the dataset (meta movers, per-hero matchups and
  guides, the Panic demo), never repeating a subject;
* **writes** it bilingually, in a style chosen by a deterministic bandit;
* **publishes** to the blog and any credentialed social channel;
* **measures** the product's own funnel and attributes it back to the styles it
  used, so the next cycle leans into whatever worked.

That turns the growth plan from a to-do list into a background process. See
[`growth-agent.md`](growth-agent.md) for how to run and extend it.
