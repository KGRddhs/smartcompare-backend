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

## Cost guard

The CLI refuses the full set live without `--allow-full`. smoke20 (20 queries) is the
safe default. All unit/integration tests mock the httpx transport — zero network, zero
cost. Operational lesson (2026-06-10): a full baseline DEPLETED the Serper key mid-run —
before any full run, sanity-check the key's remaining credits, and reconcile
`api_budget_service`'s serper ceiling with the real account balance (S2 item: 80%-burn
alert).

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
