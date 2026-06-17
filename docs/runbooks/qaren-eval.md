# Qaren Eval Operator Runbook (Bundle B Phase B.6)

The eval loop measures the comparison engine against `data/validation_gold_truth.json`
(200 ratified queries) along 4 axes: price / specs / winner / factual.
Authored by Lane F4, Bundle B Session 1 (2026-06-10).

## Commands

- **Pre-merge gate (smoke20, regression vs baseline):**
  ```bash
  TARGET_BASE_URL=https://web-production-58776.up.railway.app \
    python -m scripts.eval_runner --subset smoke20 --mode regression --baseline-run-id <uuid>
  ```
  Exit 1 if ANY per-axis average drops >2pp vs that eval_runs row. Run this between merges.

- **Absolute gate (bundle-exit):**
  ```bash
  python -m scripts.eval_runner --subset smoke20 --mode absolute --threshold 0.95
  ```
  Exit 1 if pass_rate < threshold.

- **Full-200 baseline (dispatcher-gated):**
  ```bash
  python -m scripts.eval_runner --allow-full --mode absolute --threshold 0.95 --run-kind manual --persist
  ```
  `--allow-full` is REQUIRED (cost guard). A cold-cache full run burns ~600–1,000 Serper
  credits (~half a fresh free key) + GPT — NEVER run without explicit dispatcher GO.

## Baselines (run-ids the gate compares against)

The documented S1 full-200 baseline `4aee8e88-da97-41b3-974b-3e75c2c9c10e` is **subset
`full` (200)** — it MISMATCHES the smoke20 regression gate (long-standing caveat). The
smoke20 gate needs a smoke20 baseline:

- **smoke20 cold baseline (Faithful-Results, 2026-06-17)** — prod = main `2c10cb8`
  (current main; prod stays here until the bundle's Phase-8 deploy). ACTUAL command run
  (the plan's `--mode baseline` was a doc error — there is no `baseline` mode; use
  `absolute --threshold 0.0` to capture+persist without gating):
  ```bash
  TARGET_BASE_URL=https://web-production-58776.up.railway.app python -u -m scripts.eval_runner \
    --subset smoke20 --mode absolute --threshold 0.0 --persist --concurrency 1 --run-kind manual
  ```
  Result: pass_rate **0.0%** (0/20); axis price=0.000 specs=0.988 winner=0.400
  factual=1.000; p50=16656ms p95=21327ms (within 30s cap); 0 errors. The 0% is the honest
  cold-cache price-pending state — current-main pends almost all prices on a cold
  `nocache` run (priced_cells=1/40), so the price axis collapses to 0 and drags weighted
  scores below the 0.80 pass floor. THIS is the genuine-price problem the bundle attacks;
  the A4 `--read-cache` variant is what will measure the warmed state.
  gold_truth_version = `aed2cc9bb7f5d15bd530d5e91c99e3e09860f829`. Run-id:
  **`7a5fc55b-126c-4097-9295-976541a523d0`** (eval_runs, project `qulajmyxdbdkchvecmvc`,
  created_at 2026-06-17 16:54Z) — inserted via Supabase MCP because the eval box can't
  DNS-reach Supabase to `--persist` (`getaddrinfo failed`). **This is the smoke20
  regression anchor; it SUPERSEDES the mismatched full-200 `4aee8e88...` for any
  `--subset smoke20` run.** Post-deploy 7.3 gate:
  `python -m scripts.eval_runner --subset smoke20 --mode regression --baseline-run-id 7a5fc55b-126c-4097-9295-976541a523d0 --concurrency 1`.
  **Gate teeth = the AXES** — specs (0.9875) + factual (1.0) must NOT regress; winner
  (0.4) is the structural baseline; pass_rate is floored at 0 by the cold-pend price
  behavior (so "no pass_rate regression" is trivially true — don't read it as the signal).

## Wave-2 #12 record (Faithful-Results, 2026-06-17)

- **Unit free-unit regression gate: PASS.** `scripts/regression_gate_diff.py` vs QA's
  integrated free-unit suite (HEAD `ad4d25b`) → EXIT 0, FAILED set ⊆ the canonical 48.
  Canonical baseline = QA's `.qa-discovery/BASELINE_FAILURES.txt` (48, creds-present);
  shared `NETWORK_FLAKY_EXCLUDE` = the 2 `test_price_cache_bust_probe::TestPriceReadBypass`
  + `test_rate_limiting_complete::...prices_endpoint_rate_limited` + algolia
  (`test_algolia_service::test_fetch_price_happy_path_genuine_bhd`, mocked-pollution-flaky).
  Parser gotcha fixed (`3a0a427`): pytest `-rf`/`-q` prints BARE nodeids in the
  WARNINGS-summary section (passing tests above their DeprecationWarning) — the gate
  counts ONLY `FAILED `-prefixed lines when the input is pytest output, else treats a
  bare id-list (the baseline mirror) as all-failures.
- **Coverage (per-diff / new-code standard, NOT whole-module):** the new pure-logic
  modules are well-covered (response_builder 71%, scoring_service 66%); price/review/
  extraction whole-module sit 24-28% because ~75% is the live-network/LLM cascade that
  only `live_unit` tests reach (excluded from free-unit — same ceiling on main). Per-diff
  check on the new functions: all covered after filling the one gap — BE's
  `is_haircare_query` had zero coverage (its sibling `is_implausible_low_haircare_price`
  checks premium brands directly, bypassing the predicate) → filled (`20e3c89`).
- **Post-deploy eval (this section's anchor):** prod is `3d870c8` post-merge. The smoke20
  eval regression runs vs `7a5fc55b` AFTER the deploy settles (dispatcher GO-LIVE) — gate
  teeth = the axes above.

## Persistence (`--persist`)

Writes ONE `eval_runs` row (migration 031) via the service-role Supabase client:
pass_rate, 4 per-axis averages, p50/p95 wall, gold_truth_version (git SHA of the gold
blob), and `metadata.axis_weights_used`. Rows are service-role read/write only (no user
SELECT); the admin accuracy dashboard (B.6 S3) aggregates them. Run id prints as
`# eval_runs row: <uuid>`.

## Weights canon

Axis weights come from the gold file's `_metadata.axis_weights` (the SINGLE source of
truth; git-SHA-pinned per run). `load_axis_weights` maps the long keys → short, validates
exactly the 4 axes + sum 1.0±1e-6, and HARD-FAILS (exit 3) on malformed metadata. The
`AXIS_WEIGHTS` module constant (.25/.25/.30/.20) is the FALLBACK only — used with a
logged warning when metadata is absent.

## Concurrency

Default is 3. For a measurement/baseline run prefer `--concurrency 1`: the engine's
wall-time is load-sensitive (S1 finding: concurrency 3 pushed 26s queries past the 30s
cap; sequential re-runs passed 8 of 12 prior failures), and parallel in-flight requests
inflate p95 and can perturb pass/fail near the band edges. Use 1 when the numbers must
be trustworthy; 3 only for a quick smoke.

## Tier 1.5 routing evidence (I5.1, Bundle B S2)

Two surfaces make the registry-vs-legacy escalation attribution observable without
guessing:

1. **Per-domain dashboard line.** `/admin/costs → tier1_5_hit_rate.by_source` is a
   **bucketed** `{"registry": {domain: hits}, "legacy": {domain: hits}}` map (7-day window,
   hit-count descending) built from the `tier15:source_hits:{domain}:{YYYYMMDD}` counters
   that `record_tier15_hit` writes. The winning host is normalized to its registry apex at
   record time (`uae.sharafdg.com` → `sharafdg.com`, G1 finding F2), and the reader probes
   BOTH the registry apexes AND the legacy whitelist so `legacy_fallback` wins
   (farfetch/ssense/net-a-porter-class) are visible (G1 finding F3 — this is what answers
   the F1.7 registry-vs-legacy attribution question). `by_category` (the F1.6 hit-rate
   block) sits beside it. This is the exit-review yield evidence — read it during/after any
   measurement run to see WHICH domains (`shopalmoayyed.com`, `talabat.com`, …) and WHICH
   bucket produced the scraped winners.

2. **Price-only cache-bust probe (`PRICE_CACHE_BUST=true`).** F1.7 §3 found the cold→warm
   double-tap can't surface a registry route because cached Tier-3 GPT estimates
   short-circuit the second run's escalation. Setting `PRICE_CACHE_BUST=true` force-misses
   BOTH the Redis price read and the L2 DB price read in `_get_price`, so the Tier-1.5
   escalation re-runs deterministically. Specs/reviews caches are UNTOUCHED (they gate on
   the unchanged `nocache` arg), so the wall still fits the 30s cap. **It is a probe, not a
   runtime flag — keep it UNSET on Railway normally**; the dispatcher flips it only for a
   routing-evidence pass and unsets it after. The flag is read fresh per call (no process
   cache), so it takes effect without a redeploy. Verify a single product cheaply via
   `GET /api/v1/text/prices/<product>` with the flag on, then read `by_source` to confirm
   the route landed.

## Cost guard

The CLI refuses the full set live without `--allow-full`. smoke20 (20 queries) is the
safe default. All unit/integration tests mock the httpx transport — zero network, zero
cost. Operational lesson (2026-06-10): a full baseline DEPLETED the Serper key mid-run —
before any full run, sanity-check the key's remaining credits, and reconcile
`api_budget_service`'s serper ceiling with the real account balance.

**Serper 80%-burn alert (I5.0, shipped Bundle B S2).** `api_budget_service.record_usage`
fires a WARNING log + `sentry_sdk.capture_message` (level=warning) ONCE when a provider
crosses 80% of its ceiling (serper: 1760/2200), de-duped via a Redis sentinel so it does
not spam. `/admin/costs → serper_burn` surfaces the live `{used, limit, threshold,
fraction, over_threshold}` number — the run-integrity canary to check before a full
gold-200 re-run. The sentinel is **LATCHED with no expiry** for lifetime providers
(serper/firecrawl) so the alert fires exactly once until the key is rotated (the counter
reset on rotation re-arms it); a monthly provider's sentinel is bounded by the
month-stamped key and re-arms next month. (G1 finding F1 fixed an inverted TTL that gave
lifetime providers a 1h sentinel → hourly re-fire.)

**Runway at the 80% trip:** the 20% headroom between the alert (1760) and the 2200 ceiling
is **440 credits ≈ 30–44 escalating cold queries** (post-B.0 escalation-heavy cold ≈
10–15 credits each). So the alert is roughly one smoke20's worth of cushion before
exhaustion — treat it as "rotate before the next measurement run," not "plenty left."

## Nightly cron (deliberately deferred)

`scripts/cron_eval_nightly.py` exists but is gated by `ENABLE_EVAL_CRON` (fail-CLOSED)
and registers NO Railway cron. Registration (schedule `0 2 * * *` = 05:00 GCC, ~$2/night
+ ~600-1,000 Serper credits/night — needs a key-rotation routine first) is a dispatcher
decision deferred to S3 per plan F4.5. To enable: set `ENABLE_EVAL_CRON=true` +
`TARGET_BASE_URL` on Railway and register the cron service running
`python -m scripts.cron_eval_nightly`.

## Relationship to scripts/run_validation_matrix.py

The Sprint A merge-gate script coexists UNTOUCHED (sync requests, prose winner,
fractional scores). This runner is the Bundle B canonical (async, deterministic winner
from scoring_v2, persistence, gate modes). Consolidation decision is S3/Lane S5 scope.

## S2 I2.5 — Review-source consultation flag (ENABLE_REVIEW_SOURCE_CONSULT)

`ENABLE_REVIEW_SOURCE_CONSULT` gates the optional GCC editorial review-source
consultation (Arabic sources sayidaty.net / khaleejtimes.com / gulfnews.com,
registered `usage="review"`). **Default OFF** — promotion decided at G5 on I4's
A/B. Modes (`review_service.review_source_consult_mode`):

- **unset / `false`** → OFF (no consult, zero change). This is prod/eval default.
- **`active`** (EXPLICIT only) → fires ONE budget-gated Serper `site:` search
  across the category's review sources. The ONLY mode that spends a Serper
  credit, so it is deliberately NOT reachable via a generic truthy flip.
- **`passive` / `true` / `1` / `on`** → reuses the already-fetched unified
  search organic for review-domain hits (ZERO extra Serper). A careless `=true`
  flip lands here, not on the credit-spending path (F3 safety).

When ON and quotes are found, they attach to `reviews.review_source_quotes` and
surface in the verdict as a labeled "Regional editorial review notes" block
(supporting signal, not the verdict). **Cache caveat:** review-source quotes are
cached 14 days per product (`review_source_snippets:` key); a cache HIT within
that TTL serves the cached reviews and BYPASSES the consult entirely — so an
A/B toggle won't re-consult a product seen <14d ago unless `nocache=true`. The
baseline extraction is always persisted BEFORE the consult runs, so a consult
timeout never loses the reviews leg.
