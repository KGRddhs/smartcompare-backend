# Comparison Speed Fixes — Design

**Date:** 2026-05-17
**Status:** Approved, ready for implementation plan
**Owner:** Ahmed + Claude
**Scope:** Bucket D from Session 49 triage (cold-cache speed + price quality). Buckets A (history empty / camera Compare not firing / asymmetric specs), B (two-input UX), C (scoring/personalization tuning) are out of scope here — they get separate design docs after D ships.

---

## Goal

Reduce cold-cache wall time so it stops being the dominant complaint:

| Path | Current cold p95 | Target cold p95 |
|---|---|---|
| Mainstream (electronics, supplements, skincare) | ~30-35s | **≤ 15s** (stretch), **≤ 20s** (hard) |
| Luxury (LV, Gucci, Chanel, Hermès) | ~85s, all `estimated` prices | **≤ 30s** with real `firecrawl_brand_domain` / `page_scrape_jsonld` / `scrapedo_rendered` prices |

Hard constraint: **zero quality regression.** A faster comparison that drops fields, hallucinates values, or thins out reviews is a worse comparison.

---

## Bench evidence (Session 49, against Railway production)

All cold-cache, `?nocache=true`, non-streaming endpoint (no `STREAM_HARD_CAP_SECONDS=25.0` truncation):

| Query | Wall time | API calls | Cost | Notable |
|---|---|---|---|---|
| iPhone 17 vs Galaxy S25 Ultra | 30.5s | 18 | $0.011 | `local_bhd` prices, no scrapers |
| Centrum Adults vs One A Day | 35.5s | 18 | $0.012 | `page_scrape` + `estimated` |
| Garnier Micellar vs Bioderma Sensibio | 26.4s | 18 | $0.011 | `local_bhd` + `estimated` |
| **LV Neverfull vs Gucci Marmont** | **85.3s** | **20** | $0.012 | **Both products: `estimated` (all 3 scrapers failed sequentially)** |

Key reads:
- **Mainstream is 26-36s.** Bottleneck is upstream of the luxury scrape cascade — almost certainly the **18 sequential GPT extraction calls** per comparison (specs + reviews + rating + verdict, ×2 products + verdict).
- **Luxury is 85s AND returns fabricated prices.** Bottleneck is the sequential Tier 1.5 cascade (curl → Firecrawl → Scrape.do, each tried in order, all timing out or failing). The parked branch `experiment/scatter-gather-2026-05-16` was built exactly to fix this.

API budget snapshot (provider endpoints, 2026-05-17):
- **Serper (Railway prod):** 987 credits remaining ✅
- **Firecrawl:** 2,260 credits ✅
- **Scrape.do:** 1,000 / 1,000 monthly ✅

No provider is exhausted. The slowness is genuine pipeline behaviour, not credit-induced degradation.

---

## D1 — Luxury parallel scrape race (scatter-gather ship)

**Source:** parked branch `experiment/scatter-gather-2026-05-16`. Two commits on top of base `cdf2c04`:
- `9bf5b44` — 5 RED→GREEN integration tests for the Tier 1.5 cascade race
- `88adf85` — wires `fan_out_price_lookup()` + `_build_luxury_scrapers()` into `_get_price()`'s Tier 1.5 block

What changes in behaviour:
- Old: `_get_price()` tries curl_cffi → if no price, tries Firecrawl → if no price, tries Scrape.do → if no price, falls back to GPT estimate. Each step is sequential. Luxury sites time out at each step → ~85s aggregate.
- New: for each candidate URL (from 3 sequential Serper discovery queries), 1-3 scrapers fire **in parallel** via `fan_out_price_lookup()`. First to land a valid price wins; pending scrapers cancel when 2 sources agree within 5% or a rank≥85 result lands. Counterfeit-domain whitelist gates preserved.
- Tier 3 GPT-training-data fallback now preserves the `gpt_*` source_method instead of collapsing to legacy `estimated` (lets `quality_ranker` weight the tier correctly).

**Merge strategy:** cherry-pick `9bf5b44` + `88adf85` onto main. Base is `cdf2c04`; neither commit touches files that have changed on main since (verified — branch base is 8 commits behind main but those 8 are all docs / EAS / Sentry / mobile, none touch `structured_comparison_service.py` or `tests/test_fan_out_integration.py`). Clean cherry-pick expected.

**Test gates (all must pass before push):**
1. `pytest tests/test_fan_out_integration.py -v` → 12/12 pass
2. `pytest tests/ -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py` → no new failures vs main baseline
3. `python -m py_compile app/services/structured_comparison_service.py`

**Post-deploy verification:**
4. Cold-cache bench: LV Neverfull vs Gucci Marmont → wall time **< 45s** AND both products' `price.source_method` ∈ {`firecrawl_brand_domain`, `page_scrape_jsonld`, `scrapedo_rendered`} (NOT `estimated`)

**Rollback trigger:** any of (1)-(4) fails → `git revert HEAD~1..HEAD` on main → push → confirm Railway redeploys to pre-D1 state. Branch stays parked, not deleted.

**Budget impact:** ~3-5 Firecrawl credits + ~3-5 Scrape.do credits per post-deploy luxury bench. We have 2,260 + 1,000 respectively. Negligible.

---

## D2 — Mainstream extraction speedup (data-driven)

D2 runs **after** D1 ships so the post-D1 baseline is the reference point for "did D2 actually help?"

### Phase 2A — Diagnosis (Explore agent, ~10 min)

Add additive `time.perf_counter()` markers around the per-product fetch stages in `_fetch_product_data()`:
- `unified_search_ms` (Serper)
- `specs_ms` (`_get_specs` — GPT extraction)
- `price_ms` (`_get_price` — Serper Shopping + maybe scrape cascade)
- `reviews_ms` (`_get_reviews` — GPT extraction)
- `rating_ms` (`_get_verified_rating`)
- `verdict_ms` (gpt-4o verdict generation in main orchestrator)
- `scoring_ms` (deterministic, expected near-zero)
- `response_build_ms`

Emit as `metadata.stage_timings_ms` (additive — no SSE event change, no API contract change). Gate on env flag `DEBUG_STAGE_TIMINGS=true` so the cost is opt-in.

Deploy temporarily with the flag on, run 3 cold mainstream benches (iPhone, Centrum, Garnier), capture per-stage p50/p95. Disable flag after data is captured.

### Phase 2B — Design the fix (this session, after 2A returns)

Section 3 of this design doc gets written AFTER 2A data is in. Candidate interventions ranked by signal-to-effort:

1. **OpenAI prompt caching on long system prompts** (`extraction_service.py`). Native gpt-4o-mini support, ~5× cheaper + faster on cache hits. Zero quality risk. Expected: 2-3s per call. *Pick first if any stage shows >5s and uses a static system prompt.*
2. **Combine specs + reviews into one structured `response_format=json_schema` call per product.** Saves a full GPT round-trip (~5-10s per product, ~10-20s total). Quality risk: bigger prompt may drop fields → strict 100% spec parity test required. *Pick if 2A shows specs + reviews are both major contributors.*
3. **Verdict streamed last (perceived latency only).** User sees scores + verdict block at ~15s while prose finishes at 25s. UX win without pipeline speedup. *Pick if verdict is the dominant stage AND we can't shrink it.*
4. **Drop drug-context lookup for non-supplement queries.** Quick win if it's running unnecessarily. *Pick if 2A shows it adds time to electronics.*

Section 3 picks ONE intervention (or a small combo) and locks the implementation contract. Get explicit user approval before coding.

### Phase 2C — Implementation + tests (this session if scope ≤1 file + new tests, else next session)

**Test gates (non-negotiable):**

- **Spec parity (100%):** for the iPhone 17 vs Galaxy S25 Ultra reference comparison, run on pre-D2 baseline (saved to `tests/fixtures/comparison_baseline_d2.json`) and on post-D2 output. Assert: every key present in baseline `specs[i]` is present in post-D2 `specs[i]`. No field allowed to disappear. (Fields may be added; that's fine.)
- **No hallucinated values:** for keys present in BOTH baseline and post-D2, values must match exactly for hard specs (RAM, storage, battery mAh, processor name). Soft fields (description, summary) compared with normalized whitespace.
- **Schema validation:** post-D2 response must validate against `CATEGORY_SPEC_SCHEMAS[category]` (already exists in `extraction_service.py`).
- **Review citation parity:** number of `[N]` citations in each review ±2 vs baseline.
- **Scoring parity:** same dimension names returned (e.g. `performance`, `value`, etc) — values may shift slightly but no dimension disappears.
- **Bench:** 3 cold mainstream benches post-deploy → average ≤20s, p95 ≤25s. Stretch goal: average ≤15s.
- **Unit suite:** `pytest tests/ -m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py` → no new failures vs post-D1 baseline.

### Phase 2D — Verification + ship

- Pre-deploy: all Phase 2C test gates green.
- Push to Railway, watch `/health` until 200.
- Re-bench 5 cold queries: 3 mainstream + 1 luxury (LV vs Gucci) + 1 supplement.
- Combined Bucket D success criteria: mainstream avg ≤20s, luxury ≤30s, luxury prices NOT `estimated`, all unit tests green, no quality regression on the baseline fixture.
- **Rollback trigger:** any failure → `git revert` immediately, push, verify Railway rolls back.

---

## Sequencing

Strict sequential (not parallel) because concurrent Railway deploys + benches would make perf-regression attribution impossible:

1. Write + commit this design doc (now)
2. Write implementation plan via `writing-plans` skill (next)
3. Execute D1 (cherry-pick → tests → push → verify luxury bench)
4. Execute Phase 2A (deploy timing instrumentation → bench → capture data → disable flag)
5. Brainstorm + lock Section 3 (D2 fix design) based on 2A data
6. Execute Phase 2C+2D (implement → test → push → verify combined bench)

After D ships:
7. New brainstorm session for **Bucket A** (history empty + camera Compare not firing + asymmetric specs). Note: the asymmetric specs may resolve naturally if D2's extraction-quality work happens to fix Serper-data-thin queries — diagnose during Bucket A.

---

## Out of scope (explicit non-goals)

- Bucket B (two-input text/URL UX redesign) — separate design session, large frontend scope.
- Bucket C (value-scoring tuning, personalization slider behaviour, pros/cons quality) — depends on D2 quality work to land first.
- Changing the deterministic scoring algorithm itself — scoring is `category_weighted`, not the cause of the 30s/85s.
- Removing the `STREAM_HARD_CAP_SECONDS=25.0` cap on streaming. The cap is a safety net for the streaming SSE endpoint; D's real fix is making the pipeline genuinely faster, not removing the cap.
- Rotating the Railway Serper key. Production has 987 credits — flag for rotation before launch traffic ramps, not now.

---

## Open risks

- **Cherry-pick conflict.** If the branch's `_get_price()` diff overlaps with any unmerged hotfix on main, the cherry-pick will fail. Mitigation: dry-run with `git cherry-pick --no-commit` first; if conflicts, manual three-way merge with branch author context.
- **Post-D1 luxury bench still returns `estimated`.** Would mean the scrapers themselves are broken (not just the cascade ordering). Mitigation: inspect Firecrawl + Scrape.do response logs from the test; if both return 0 results, the URLs being passed to them are bad (Serper discovery problem) and scatter-gather can't help. Falls into Bucket A diagnostic queue.
- **Phase 2A diagnostic adds noticeable overhead.** `time.perf_counter()` is sub-microsecond; safe. The risk is the env-flag-gated logging firing in prod by accident. Mitigation: read env var ONCE at request start, default false.
- **D2 quality regression test (100% spec parity) too strict.** May block a fix that's genuinely better but renames a key (e.g. "Front Camera" → "Selfie Camera"). Mitigation: if this happens, design a key-normalization layer before failing the test.

---

## References

- Parked branch: `experiment/scatter-gather-2026-05-16` (commits `9bf5b44`, `88adf85`)
- Original scatter-gather design: `docs/plans/2026-05-13-results-quality-overhaul-design.md` § Decision 8
- Session 48 entry: `docs/SESSION_BUNDLES.md` ("next session: bench Railway cold-cache p95, if >15s ship the scatter-gather rewrite")
- Memory follow-up: `MEMORY.md` → Pending follow-ups → "Scatter-gather scoping"
