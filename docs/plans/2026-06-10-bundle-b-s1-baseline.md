# Bundle B — S1 Eval Baseline Record (2026-06-10)

**This is the regression anchor for the entire bundle.** Every S2/S3 change is gated
against this row via `--mode regression --baseline-run-id`.

## The row

- **eval_runs id:** `4aee8e88-da97-41b3-974b-3e75c2c9c10e`
- **run_kind:** manual · **gold:** 200 ratified queries (ratified_by ahmed, 2026-06-10T08:21:48Z)
- **Engine under test:** main @ `ea4be1b` deployed on Railway (S1 merge train + grader top-up),
  Serper key `3d304e...` (rotated mid-day after depletion; this run is fully post-rotation)
- **Runner config:** concurrency 1 (measurement purity — load-sensitivity proven same day),
  nocache=true, per-query timeout = max_wall+10s
- **Per-query detail:** `.qa-bias-rerun/baseline_s1_per_query.jsonl` + `baseline_console.log`

## Headline

| Metric | Value |
|---|---|
| **Weighted pass rate** | **21.0% (42/200)** vs 95% bundle-exit target |
| axis_avg_price | 0.455 |
| axis_avg_specs | 0.708 |
| axis_avg_winner | **0.360** |
| axis_avg_factual | 0.770 |
| wall p50 / p95 | 23,235 ms / 30,656 ms — **p95 OVER the 30s cap** |

Weights: price .25 / specs .25 / winner .30 / factual .20 (gold `_metadata.axis_weights`,
recorded in the row's `metadata.axis_weights_used`). Per-query pass threshold: 0.80.

## Reading the axes (S2 targeting)

- **factual 0.77 (best):** the engine largely avoids the forbidden-fact traps — the trust
  floor is real. Lift via citation discipline + anti-patterns.
- **specs 0.708:** extraction is serviceable; per-product-type schema growth (S1 added
  electronics.ac coverage) is the lever.
- **price 0.455:** half the answers land outside the Bahrain retail bands. Drivers:
  gl=us-fallback / converted prices vs Bahrain-anchored gold bands, and escalation
  (the Bahrain-source path) frequently not completing inside the cap. B.0 routing can
  only move this number once latency lets escalation finish — see wall.
- **winner 0.360 (headline weakness):** BELOW the two-option coin-flip rate → systematic
  bias, not noise. The engine's pick disagrees with the ratified Bahrain-buyer judgment
  in a patterned way (hypothesis for S2 mining: US-availability/price framing outweighing
  local availability + GCC-market factors). This per-query disagreement set is the raw
  material for S2's few-shot exemplars + anti-pattern injection (Lane I1/I2).
- **wall p95 at the cap:** structural latency debt confirmed at scale (matches the probe
  arithmetic: ~27s non-escalating baseline + 15s escalation race > 30s). S2 perf section
  in `2026-06-10-bundle-b-s2-prep-notes.md` § 2 carries the levers.

## Caveats recorded with the number

- A handful of Railway 502s occurred late in the run (sustained 3.5h cold-cache load that
  day); they grade as failures, consistent with user experience, but a few points of the
  gap are infra-noise rather than engine quality.
- Cap-timeouts (400s) also grade as failures BY DESIGN — users experience them. The
  baseline therefore bundles "accuracy" and "fits the time box" into one honest number.
- This was the day's second attempt: the first baseline run was invalidated mid-flight by
  Serper key depletion (~30 queries in) and discarded; this run is fully post-rotation.

## Standing gate commands (from `docs/runbooks/qaren-eval.md`)

```bash
# pre-merge regression gate vs THIS baseline:
TARGET_BASE_URL=https://web-production-58776.up.railway.app \
  python -m scripts.eval_runner --subset smoke20 --mode regression \
  --baseline-run-id 4aee8e88-da97-41b3-974b-3e75c2c9c10e
```
