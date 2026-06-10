# Bundle B — Session 2 "Intelligence" Prep Notes

> **S2.0 opens with this doc** (the way S1 opened with `2026-06-09-bundle-b-kickoff-prep.md`).
> Compiled at S1 close (2026-06-10) from lane carry-overs + dispatcher rulings. S2 scope
> outline lives in `docs/plans/2026-06-10-bundle-b-intelligence-layer-plan.md` § SESSION 2;
> design context in `2026-06-10-bundle-b-intelligence-layer-design.md` § 4.

**S2 baseline anchor:** the S1 eval_runs row (run_kind=manual, 2026-06-10 — id in
`docs/plans/2026-06-10-bundle-b-s1-baseline.md`). Every S2 prompt/reasoning change is
regression-gated against it (smoke20, >2pp per-axis drop fails).

---

## 0. BINDING TABLE — every S1 finding → an owning task with an exit criterion (Ahmed directive 2026-06-10)

> Ahmed's standing directive: **estimates and uncertainty are unacceptable as answers.**
> Every finding below is BOUND to a session/lane — none are "noted for later."
> S2.0's FIRST act: structure S2 with FIVE lanes (the original 4 + a new **Lane I5
> "Yield & Wall"**) so the scrape-yield and latency work are first-class, not riders.

| S1 finding (evidence) | Bound to | Exit criterion |
|---|---|---|
| **Electronics/AC scrape yield 0/14** (F1.7 §2) | **S2 Lane I5** — Shopify JSON-LD selector check vs shopalmoayyed/bh.asgharali markup; Firecrawl-rendered tier for lulu/carrefour SPAs; verify bahrain discovery returns candidate URLs at all | electronics tier1_5 hit_rate > 0; AC pairs (elec-013/014/015 class) price with `source_method != estimated` |
| **Winner agreement 0.360 — below coin-flip** (baseline) | **S2 Lanes I1+I2** — few-shot exemplars + anti-patterns mined from the 158 baseline failures | winner axis ≥ 0.60 by S2 exit (measured vs row 4aee8e88) |
| **Wall p95 30.7s OVER cap; ~27s pre-escalation baseline** (probe+baseline) | **S2 Lane I5** — reviews/verdict latency reduction (the ~9-10s sequential pair), fan_out cap decision, re-measure supplements post-F2.2 | p95 < 30s on the full-200 re-run; the 4 persistent-slow queries complete |
| **Price axis 0.455 / estimate share** (baseline) | **S2 I5 (yield+wall) + S3 Lanes S1-S4 (new sources)** — estimates starve as real sources land | price axis ≥ 0.70 by S3 exit; estimate share tracked per run in eval metadata |
| **Registry-vs-legacy attribution unknown** (F1.7 disposition) | **S2 Lane I5, first task (~10 min)** — per-source `tier15:source_hits:{domain}` line in `/admin/costs` | dashboard shows per-domain hits; registry domains visibly winning or the registry entries get fixed |
| **Double-tap can't re-probe (estimates cache too)** (F1.7 §3) | **S2 Lane I5** — probe-only price-scoped cache-bust flag | deterministic routing-evidence probe documented in the eval runbook |
| **Serper budget breaker didn't trip before depletion** (incident) | **S2 Lane I5** — reconcile ceiling with real account balance + 80%-burn Sentry alert | alert fires in a drill before the tank empties |
| **Serper gl=bh shopping yield thin (upstream)** (F1.7 §2) | **S3** — new sources reduce dependence; the standing long-term item remains a real Bahrain merchant feed (`memory/project_bahrain_shopping_feed_gap.md`) | tracked; estimate-share trend is the proxy metric |

S2 does NOT close the bundle: the **95% absolute gate binds at S3 exit**, and S3's lanes
(Reddit/YouTube/Apify/direct scrapers + accuracy dashboard + production sampling) are the
second half of the same binding. If any S2 exit criterion above is missed, it carries into
S3 scope explicitly — nothing silently drops.

---

## 1. Arabic content sources + `Source.usage` field (Lane I2 enabler — F1 carry-over)

DEFERRED from F1.5 (Ahmed-ratified). 3 verified-real Arabic review-content sources NOT in
SOURCE_REGISTRY: **sayidaty.net, khaleejtimes.com (AR), gulfnews.com (AR)**. Reason: the
registry today feeds ONLY Tier 1.5 price-discovery (`_harvest_candidate_urls` admits any
domain scoring ≥1.5 into the scrape pool); news sites have no prices → pure scrape-budget
burn.

**Design (build in I2):** add `usage: "price" | "review" | "both"` to the `Source`
dataclass, default `"price"` on all 37 existing entries (zero behavior change).
`_harvest_candidate_urls` filters to `usage in ("price","both")`; the NEW review-content
path consumes `usage in ("review","both")`. Then register the 3 Arabic sources as
`usage="review"`, gcc weight, review categories (fashion/makeup/skincare/haircare/
fragrances). Tests: price-harvest invariants unchanged; review path consults Arabic
sources. (Also recorded in-plan at commit 3874b16.)

## 2. Latency debt — the S2 perf target (F1 carry-over, probe-measured)

Cold-cache walls from the post-merge prod probes (main @ ea4be1b):
- **Non-escalating baseline** (Phase-1 + scoring + verdict, NO Tier 1.5): min 22.4s /
  mean 27.0s / max 30.1s → only ~3s headroom under the 30s cap before escalation even starts.
- **Arithmetic:** escalating query = ~27s baseline + up to 15s fan_out race = guaranteed
  cap-breach cold. The registry can't demonstrate live routing until this fits.
- **4 persistent-slow queries (sequential, concurrency 1):** supp-003 (NOW vs Solgar D3)
  49–55s and supp-002 (Optimum vs Dymatize) 37s — iHerb path (F2.2's merged microdata
  fallback should pull these down; re-measure in S2); groc-001 33.9s; elec-010 32.8s.
- **Load sensitivity:** concurrency 3 pushed 26s queries past the cap (12/24 errors);
  sequential passed 8 of those 12. Measurement runs MUST use concurrency 1
  (now in `docs/runbooks/qaren-eval.md`).
- **Levers (in order):** (1) Phase-1/verdict baseline reduction — reviews ~4-5s + verdict
  ~4-5s sequential are the prime targets (D2-era findings still hold); (2) consider
  trimming the 15s fan_out cap to 10-12s for escalating queries (trades scrape success
  for wall — escalation-owner decision); (3) re-measure supplements post-F2.2.
- **Standing principle:** `memory/feedback_never_blind_the_instrument.md` — never
  suppress escalation to make walls fit.

## 3. Two UX decisions for Ahmed at S2 kickoff (F2 carry-over, decision-ready)

**DECISION A — Dimension display cap: 6 rows vs 8.**
Current: 3 core dims + up to 3 category dims = 6 rows; electronics has 5 surfaceable
category dims so `ecosystem`/`futureproof` are computed but never shown. Options: keep 6,
or raise to 8 (FE already supports it — HERO_CAP=4 + "see full breakdown" expander).
F2 RECOMMENDS: **raise to 8.** Cost ~30 min: `build_dimensions_v2` cap change + 2 test
updates (test_dimensions_builder.py:415, test_scoring_v2_models.py:289). All 9 categories
gain 2 rows consistently.

**DECISION B — One-sided MISSING_SCORE dim-winner: keep vs suppress.**
Current: a real score beats a missing-data side (MISSING_SCORE=50) and takes the emerald
win on that row — data absence reads as a competitive loss. Options: keep
(contract-consistent, simplest) or suppress (winner=None when exactly one side is
MISSING). F2 RECOMMENDS: **lean suppress, low-priority** — needs a per-side "was_missing"
flag plumbed into `_dim_winner` (~45 min). Decide AFTER the S1-close device walk: if the
emerald row doesn't mislead in practice, keep.

## 4. Eval/budget operations (S1 incident-driven)

- **Serper budget-breaker reconciliation + 80%-burn alert.** The key DEPLETED mid-baseline
  on 2026-06-10 (rotated to `3d304e...`). `api_budget_service`'s serper ceiling did not
  cut off calls before hard depletion — reconcile the ceiling constant with the REAL
  account balance at each rotation, and add an alert (log/Sentry) at 80% burn.
  Note: escalation-heavy cold queries now burn more credits each (the bahrain discovery
  adds a 4th per-product discovery call) — budget math must use post-B.0 per-query costs.
- **Nightly eval cron:** deliberately unregistered (ENABLE_EVAL_CRON fail-closed).
  Registering costs ~$2/night + ~600-1,000 Serper credits/night → needs the rotation
  routine FIRST. Revisit in S3 (plan F4.5; runbook documents the command).
- **run_validation_matrix.py consolidation** into eval_runner: S3/Lane S5 scope.

## 5. Suite hygiene (pre-existing, surfaced by S1 gates)

- `tests/test_value_math.py` — 24 RED-by-design TDD stubs importing unimplemented
  Bundle C v1.1 functions (`_classify_budget_mismatch` etc.). Implement-or-skip decision
  belongs to whoever picks up A.6.2-A.6.5.
- Network-dependent tests inside the "free" tier (e.g. `test_rate_limiting_complete.py`
  does a real GET) — hang in no-egress sandboxes and once wedged a networked run via the
  anyio portal (see `memory/feedback_testclient_blocking_redis_hang.md`). Mark them
  `live_unit` or mock; until then, gate batches must exclude them.
- Stale comment at `SmartCompareApp/src/services/authService.ts:455-460` contradicts the
  landed no-nonce logic (cosmetic; fold into any future auth touch).

## 6. Cross-lane security advisor (pre-existing, NOT S1 scope)

Supabase linter shows ERROR-level `security_definer_view` on the cohort views
(e.g. `vw_cohort_feedback_lift`) — predates Bundle B. Owner: whoever next touches cohort
analytics. The INFO-level `rls_enabled_no_policy` on `eval_runs`/`verdict_critiques` is
BY DESIGN (service-role-only tables) — do not "fix".

## 7. S2 unblocked-prerequisite checklist

- ✅ o3-mini access confirmed on Ahmed's org (2026-06-10) — Lane I4 unblocked
- ✅ Migration 027 live → `winner_correct` feedback accumulating for I1 few-shot curation
- ✅ eval pipeline + ratified gold-200 + S1 baseline row → I2 anti-patterns + all promotion gates
- ✅ `verdict_critiques` (030) live → I3 self-critique persistence ready
- ✅ Cost envelope arithmetic: self-critique ≤$0.002 and multi-agent (+~$0.005) cannot BOTH
  promote inside the $0.015 ceiling — at most one, or the editor absorbs critique (design § 4)
- ⬜ Ahmed during S2 week: create Reddit OAuth app + YouTube Data API key (~10 min, unblocks S3)
