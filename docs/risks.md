# DraftMaster AI — Risks & Mitigations

An honest register. Each risk is stated with its likelihood, its impact, the
mitigation already in place, and the residual risk that remains after mitigation.

## 1. Technical risks

### R1 — Data quality from upstream (likelihood: medium · impact: high)
**Risk.** OpenDota's matchup and item data can be sparse for new heroes, and Valve's
patch cadence invalidates models. A hero released mid-patch has almost no head-to-head
sample.

**Mitigation (shipped).** The counter matrix is **shrunk by sample size**, so a hero
with a thin sample regresses toward neutral instead of producing a confident wrong
answer. Confidence labels are surfaced in the UI. Artifacts are versioned with a patch
stamp shown on every report.

**Residual.** Brand-new heroes will be recommended conservatively until sample
accumulates. This is the correct failure mode — silence over confident noise.

### R2 — Model miscalibration (likelihood: medium · impact: high)
**Risk.** The WIN PROBABILITY ENGINE could be systematically overconfident, which
would destroy trust the moment users compare predictions to results.

**Mitigation (shipped).** Rank compression toward 50% is applied explicitly, and every
factor is attributed in percentage points so the user can inspect the reasoning.

**Mitigation (planned).** Phase 2 outcome feedback loop produces a published
reliability curve and recalibrates the model against observed results.

**Residual.** Until enough outcomes are collected, calibration is unproven. The
mitigation is transparency: the UI shows the factors rather than a bare number.

### R3 — Screenshot detection brittleness (likelihood: medium · impact: medium)
**Risk.** Real client screenshots include overlays, tooltips, animations and scaling
that composited test images do not.

**Mitigation (shipped).** Two-stage detection (coarse scan → pixel-level refinement)
gated by both a confidence floor **and** a runner-up margin, which suppresses
false positives from misaligned crops. Tested against genuine portraits downloaded
from Valve's CDN, not synthetic shapes.

**Residual.** Overlay-heavy screenshots may detect fewer heroes than present. The UI
shows per-detection confidence and keeps manual selection available, so the feature
degrades to "assisted input" rather than failing.

### R4 — Upstream API availability (likelihood: medium · impact: medium)
**Risk.** OpenDota rate-limits or goes down; Valve's CDN is unreachable.

**Mitigation (shipped).** The match coach uses an isolated HTTP client with explicit
`502` handling and a 10-minute cache. Portraits fall back to initials. **The draft
engine has no runtime data dependency at all** — it reads a committed artifact — so
the flagship feature is unaffected by any upstream outage.

**Residual.** Match coaching is unavailable during an OpenDota outage. Acceptable:
it is not the time-critical feature.

### R5 — Latency regression (likelihood: low · impact: high)
**Risk.** Panic Mode's entire value proposition is speed. A regression that pushes it
past five seconds makes the product useless in its core use case.

**Mitigation (shipped).** The dataset is loaded once at boot; analysis is pure CPU and
measured in single-digit milliseconds. The UI displays the measured round-trip, making
a regression immediately visible. The test suite exercises the engine end-to-end.

**Residual.** Large screenshots take seconds to analyse, but that is the screenshot
path, not Panic Mode.

### R6 — Single-artifact boot failure (likelihood: low · impact: high)
**Risk.** A corrupt or truncated artifact prevents the engine from starting.

**Mitigation (shipped).** Artifacts are validated by the test suite (hero count,
required fields, load success), fail fast at startup with an explicit log line, and are
committed to git so any version is reproducible.

**Residual.** A bad artifact still requires a redeploy — but it cannot reach
production silently, because the test gate catches it.

## 2. Product risks

### R7 — "Another Dota tool" fatigue (likelihood: high · impact: high)
**Risk.** Players are jaded by counter-pick sites that promise insight and deliver a
table. A new entrant is assumed to be more of the same.

**Mitigation.** Panic Mode is designed as a demonstrable experience: one button, one
screen, a concrete plan with a named target and a timing. It is inherently shareable,
which is the antidote to being dismissed as yet another tool.

**Residual.** High — this is the central go-to-market challenge, addressed in
`docs/growth.md`.

### R8 — Trust erosion from a wrong call (likelihood: medium · impact: high)
**Risk.** One high-profile, confidently-wrong recommendation can define the product's
reputation.

**Mitigation (shipped).** Every recommendation carries a reason, confidence labels are
honest, and the engine never recommends a hero it cannot justify from the data. The
avoid-list and win conditions are explicit, so the user can evaluate the reasoning
rather than trusting a black box.

**Residual.** Unavoidable in a probabilistic domain; mitigated by transparency and by
the calibration work.

### R9 — Free-tier abuse (likelihood: high · impact: low)
**Risk.** Anonymous `x-user-id` values are trivially rotated to bypass the 3/day free
limit.

**Mitigation (shipped).** The quota is enforced atomically server-side so concurrent
requests cannot exceed it.

**Mitigation (planned).** Real authentication (Steam OpenID) plus IP- and device-level
limits in Phase 1.

**Residual.** Some abuse persists pre-auth. Accepted deliberately: friction at signup
would cost more activation than the abuse costs in compute, which is near zero.

### R10 — Patch velocity (likelihood: high · impact: medium)
**Risk.** Valve patches frequently. Stale recommendations are worse than none, because
they are confidently wrong.

**Mitigation (shipped).** The patch name is stamped on every report and in the header,
so staleness is visible. Rebuilding is a single script invocation.

**Mitigation (planned).** A scheduled job rebuilds artifacts on patch detection and
diffs the recommendations, producing an automatic patch report.

**Residual.** A short window of staleness between a patch and a rebuild, made
acceptable by displaying the patch prominently.

### R11 — Legal and IP exposure (likelihood: low · impact: medium)
**Risk.** Using Valve's hero imagery and OpenDota's data without a licence.

**Mitigation (shipped).** Attribution is explicit in the UI footer and the README:
data © OpenDota / Valve, not affiliated with Valve Corporation, and all hero imagery is
Valve's trademark. The product is free-to-play-friendly: it advises, it never modifies
the client, injects into the process, or automates gameplay.

**Residual.** Low. The usage mirrors established community tools; the mitigation is
attribution and never shipping anything that touches the game client.

### R12 — Privacy of user match data (likelihood: low · impact: high)
**Risk.** Match IDs and account IDs are personal data. A leak would be a serious
breach of trust.

**Mitigation.** Only public match IDs are accepted. The analysis history is scoped per
user id, and the planned schema keeps personal identifiers separate from aggregated
analytics. User data is never sold, and it is anonymised before any aggregate research
use.

**Residual.** Requires disciplined handling as auth and history are added in Phase 1;
it is a design constraint, not an afterthought.

## 3. Risk summary

| Risk | Likelihood | Impact | Residual after mitigation |
| --- | --- | --- | --- |
| R1 Upstream data quality | Medium | High | Medium |
| R2 Miscalibration | Medium | High | Medium (until calibration data exists) |
| R3 Screenshot brittleness | Medium | Medium | Low |
| R4 Upstream availability | Medium | Medium | Low |
| R5 Latency regression | Low | High | Low |
| R6 Artifact boot failure | Low | High | Low |
| R7 Tool fatigue | High | High | High |
| R8 Wrong-call trust erosion | Medium | High | Medium |
| R9 Free-tier abuse | High | Low | Low |
| R10 Patch velocity | High | Medium | Medium |
| R11 Legal/IP | Low | Medium | Low |
| R12 Privacy | Low | High | Low |

The two risks that genuinely threaten the business are **R7 (being dismissed as
another tool)** and **R2 (unproven calibration)**. Both are addressed by the same
strategy: make the product demonstrably, provably different — speed and transparency
now, calibration data next.
