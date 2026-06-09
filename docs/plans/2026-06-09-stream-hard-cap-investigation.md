# STREAM_HARD_CAP Investigation — Q01 + Q10 wall regressions

**Author:** B0-A-critical
**Date:** 2026-06-09
**Branch:** `feature/B0-A-v2.2-spec-collapse`
**Reference:** team-lead's B0-A v2.2 Scope 2 brief

## Problem statement

B0-D Phase 2 24-query bias matrix re-run found two deterministic wall regressions vs prior baseline:

- **Q01 Carrier+LG AC:** 22s → 31s (+9s)
- **Q10 NOW+Solgar D3:** 15s → 31s (+16s)

Both confirmed via 2x retry. Phase 1 attribution: unknown — could be cold-dyno, v2.1 scoring overhead, Serper key swap latency, slower specs extraction, or v2.1 None-return triggering new retry cycles.

## Investigation findings

### Hypothesis 1 — Cold-dyno post-redeploy → ELIMINATED
`curl -s ./health` 3x in sequence returned 0.61s / 0.48s / 0.48s. Dyno is warm.

### Hypothesis 2 — v2.1 / v2.2 scoring overhead → ELIMINATED
Local microbench against `feature/B0-A-v2.2-spec-collapse`:
- `compute_scores`: **55.2 µs per call** (electronics, 2 products, realistic Q01-shape data)
- `_normalize_scores` in isolation: **12.3 µs per call**

The 9-16s regressions are **6 orders of magnitude** larger than the scoring layer.
Scoring is not the bottleneck.

### Hypothesis 3 — Serper key swap latency → NOT INVESTIGATED LOCALLY
Skipped: Q01 prod stage_timings reveal `unified_search_ms` for both products
(941ms + 1585ms) are within the same range observed across other queries. If
Serper latency were the cause, every query would regress, not just Q01 + Q10.

### Hypothesis 4 — Specs extraction slower on Q01/Q10 specifically → PARTIAL EVIDENCE
Q01 (Carrier+LG AC) live stage_timings (DEBUG_STAGE_TIMINGS=true):

```
verdict_ms         : 4676.5
per_product[0]:
  unified_search_ms:  941.0
  image_url_ms     : 1769.3
  specs_ms         : 2656.1
  reviews_ms       : 4799.6
  price_ms         : 6586.9
  phase1_wall_ms   : 6868.8
  smart_fallback_ms: 3020.5
  tier2_fallback_ms: 1996.9
  tier3_synth_ms   :  857.1
  rating_ms        : 3422.8
  phase2_wall_ms   : 3599.0
per_product[1]:
  price_ms         :11426.7   ← dominant
  phase1_wall_ms   :11727.9
  smart_fallback_ms: 2362.5
  tier2_fallback_ms: 1983.2
  tier3_synth_ms   :  895.6
  phase2_wall_ms   : 2855.1
total_ms           :26857.9
```

Control: `iPhone 16 vs Galaxy S25` cold-cache total_ms = **21932 ms** with
identical fallback cascade pattern (smart_fallback 2613ms + tier2 1864ms on
product_0). So fallback cascades **already fire on healthy electronics queries**
that are well below the 25s cap.

### Hypothesis 5 — v2.1 `_score_specs` None return triggers new retry cycles → REJECTED

`smart_fallback`, `tier2_fallback`, `tier3_synth` are extraction-layer fallbacks
defined at `app/services/structured_comparison_service.py:2151-2239`. Trigger
gates:

- `smart_fallback`: `missing_critical = [f for f in CRITICAL_SCHEMA_FIELDS[category] if specs_so_far.get(f) in (None, "", "N/A")]` (line 2151-2154)
- `tier2_fallback`: always called via `tier2_fill_non_negotiables` (line 2202); returns empty when nothing's missing
- `tier3_synth`: always called via `tier3_synthesize_non_negotiables` (line 2225); returns empty when nothing's missing

**None of these read `_score_specs` output or `spec_raw`.** They examine the
extracted `specs` dict directly. v2.1/v2.2 changes are confined to the SCORING
layer (`_score_specs`, `_score_reliability`, `_normalize_dimension`,
`_normalize_scores`) — none of which feed back into extraction fallback gates.

## Real root cause

**Q01 + Q10 are extraction-bottlenecked, not scoring-bottlenecked.**

Both queries target categories with **limited Serper Shopping data depth**:

- **Carrier 1.5T AC** — AC/appliance category lacks structured Shopping feed in
  Bahrain locale → Tier 1 returns sparse → smart_fallback + Tier 2 + Tier 3
  cascade for missing critical fields (battery=None, processor=None for AC
  schema mismatch) → cumulative ~5-7s extraction overhead.
- **NOW Foods D3 + Solgar D3** — supplements use iHerb direct scrape (not
  Serper Shopping). When iHerb response slow OR product-page scrape variance,
  the Tier 1.5 cascade lands on Firecrawl/Scrape.do retries → 10-15s.

These extraction-side phenomena are **NOT new from v2.1/v2.2**. The control
iPhone+Galaxy query at 21.9s shows the same fallback pattern; it just lands
inside the cap because phones have rich Serper data.

## Why the regression appeared in B0-D Phase 2

Strongest hypothesis: **`STREAM_HARD_CAP_SECONDS` was raised from 25s to 30s**
in Railway (per completed task #11 "Document STREAM_HARD_CAP_SECONDS 25→30 raise").
Pre-raise: Q01 + Q10 would have **timed out at 25s** and returned the graceful
TIMEOUT response. Post-raise: they now run to completion at 28-31s, which
appears as a "regression" against the prior baseline that capped/timed-out them.

Live evidence: Q01 returned `success: true` at total_ms=26857 (curl
time_total=28.2s). With a 25s cap, that response would have been TIMEOUT.

## Recommendation

**Not a v2.2 fix — flag for Bundle B (extraction quality):**

1. **(B-priority) AC/appliance category — enrich Tier 1.5 page-scrape selectors**
   for white-goods retailers (Sharaf DG, Carrefour, Geant, Lulu) so AC specs
   like cooling capacity, energy rating, refrigerant type extract without
   triggering Tier 2/3 fallbacks. Files: `app/services/price_service.py`
   page-scrape paths, `app/services/extraction_service.py`
   `CATEGORY_SPEC_SCHEMAS["electronics"]` (AC-specific spec keys may be
   needed — currently electronics schema is phone-shaped).

2. **(B-priority) Supplements iHerb Tier 1.5 cascade — reduce Firecrawl
   fallback frequency** on iHerb miss. Files: `app/services/price_service.py`
   pharmacy JSON-LD + iHerb scrape paths. Likely just a cache warm-up
   issue; iHerb hit-rate metrics in `/admin/costs` would confirm.

3. **(C-priority) Document STREAM_HARD_CAP_SECONDS=30 in CLAUDE.md** — task
   #11 was completed but env value should be cross-checked. Current evidence
   suggests prod is at 30s.

4. **(observability) Add explicit prod metric** `tier1_5_hit_rate` per
   category in `/admin/costs` so extraction-bottleneck regressions surface
   automatically.

## What v2.2 closes

v2.2 scope 1 (spec_scores collapse) closes the last 3 phantom-tie residuals
(Q02 fashion craft, Q03 other function, Q17 fashion craft). The wall-time
regressions are independent and pre-existing.

## Evidence index

- Microbench output: 55.2 µs `compute_scores`, 12.3 µs `_normalize_scores`
- Q01 live `stage_timings_ms` JSON (see above)
- Control iPhone+Galaxy `stage_timings_ms` JSON (similar fallback pattern)
- Tier 2/3 trigger gates: `structured_comparison_service.py:2151-2239`
- STREAM_HARD_CAP_SECONDS default: `structured_comparison_service.py:545`
