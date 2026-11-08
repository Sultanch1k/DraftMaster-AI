# DraftMaster AI — Monetization & Revenue Roadmap

## 1. Pricing

| Tier | Price | Limits |
| --- | --- | --- |
| **Free** | $0 | 3 analyses/day, full report for those analyses, meta intel, screenshot detection |
| **Premium** | **$6.99/month** or **$49/year** | Unlimited analyses, unlimited match coaching, personal AI coach, patch reports, advanced strategy analysis, priority processing |
| **Team** | **$19.99/month** | Everything in Premium for up to 5 accounts, five-stack captain mode, shared scrim history, opponent scouting |
| **API** | usage-based | Draft analysis and win probability as a service for streamers, community sites and bots |

### Why $6.99

- Below the impulse threshold: cheaper than one Dota Plus month, comparable to a
  single cosmetic.
- A committed ranked player plays 30–60 games a month. At $6.99 the cost is well under
  $0.25 per game, and the value is a higher win rate — a concrete, quantifiable
  benefit.
- High enough to fund the pipeline (OpenDota rate limits, hosting) and low enough that
  conversion does not require deliberation.

### Why a 3/day free limit

Three analyses covers "a few ranked games tonight" without covering a grind session.
The limit is deliberately reached *during* an actual session, at the moment the user
has already felt the value — the point of highest conversion intent.

## 2. The conversion moment

The paywall is not a locked screen; it is a **narrative interrupt**. When the fourth
analysis of the day is requested, the API returns `402` with an explicit message, and
the UI shows:

> You've used your 3 free analyses today. Unlock unlimited Panic Mode, match
> coaching and the personal AI coach for $6.99/month.

The user is, at that exact moment, mid-draft and blocked. This is the highest-intent
state the product will ever see.

## 3. Revenue roadmap

### Phase 1 — Consumer subscriptions (months 1–6)
- Launch free + Premium.
- Instrument the funnel: signup → first analysis → Panic Mode repeat → paywall hit →
  conversion.
- Target: 4% free→premium conversion, ~$4 ARPU on active free users.

### Phase 2 — Annual and gifting (months 6–12)
- Annual plan at a 40% discount (7 months for the price of 12), which converts
  cash up front and reduces churn.
- Gift subscriptions — the natural viral mechanic for a game where people play in
  five-stacks.
- Target: 30% of new subscribers on annual.

### Phase 3 — Team and API (months 12–24)
- Team plans for stacks and amateur organisations.
- A paid public API for community sites and streamers, priced per 1,000 analyses.
- Sponsorships with Dota content creators, where the sponsorship is a real integration
  (a "DraftMaster pick" overlay segment) rather than an ad read.
- Target: 20% of revenue from non-consumer sources.

## 4. Unit economics

| Line item | Free user / month | Premium user / month |
| --- | --- | --- |
| Compute (analysis) | ~$0.001 | ~$0.004 |
| Cache/DB | ~$0.002 | ~$0.003 |
| Generative AI (narration) | $0 | ~$0.03 |
| Bandwidth/CDN | ~$0.002 | ~$0.003 |
| **Direct cost** | **~$0.005** | **~$0.04** |

Gross margin on Premium is therefore above 99%, because the core engine is pure CPU
over a 1.1 MB artifact. Infrastructure cost is essentially fixed and amortised across
all users — the product scales almost perfectly.

The economic risk is not cost of goods, it is **churn**. A tool that does not
visibly improve win rate is cancelled within two months, which is why calibration and
accuracy work (Phase 2 of the roadmap) is a revenue investment, not an engineering
vanity project.

## 5. Retention mechanics

1. **Panic Mode as habit** — the tool must be open *during* the draft. That is a
   session habit, and session habits retain far better than weekly-report habits.
2. **Patch reports** — every patch generates a new meta report, giving lapsed users a
   concrete reason to return.
3. **Personal progress** — a climbing MMR chart tied to advice actually followed.
4. **Streaks and history** — analysis history makes the tool feel like an archive of
   the user's own improvement, which raises switching cost.
5. **Team accounts** — social accountability; leaving means abandoning a shared asset.

## 6. Pricing experiments to run

| Experiment | Hypothesis |
| --- | --- |
| 3/day vs 5/day free limit | A higher limit may increase D7 retention enough to offset lower conversion |
| $4.99 vs $6.99 | Price elasticity at the impulse threshold |
| Weekly plan ($1.99) | Captures players who want one weekend of ranked |
| Paywall timing | Blocking at the 4th analysis vs after a "premium preview" of the 4th |
| Annual default | Pre-selecting annual raises revenue per subscriber and lowers churn |

## 7. What we will not do

- **Loot boxes or cosmetics.** The product sells an edge, not gambling.
- **Selling user data.** Draft history is a competitive asset and a privacy liability;
  it is never sold, and it is anonymised for any aggregate research.
- **Pay-to-win within the product.** Free users get the same *quality* of advice as
  premium users; they get less *volume*. Gating accuracy would poison trust.
- **Advertising.** It would slow the one thing the product promises: speed.
