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

---

## Phase 2A Diagnostic Results (captured 2026-05-17, this session)

Cold-cache p50/max stage timings from 3 sequential mainstream benches against Railway production with `DEBUG_STAGE_TIMINGS=true` temporarily enabled. Flag was disabled and gated-off verification PASSED immediately after data capture.

### Bench results

| Query | Total ms | Scoring | Verdict | Response build |
|---|---|---|---|---|
| iPhone 17 vs Galaxy S25 Ultra (electronics) | 18119 | 0.2 | 4164 | 0.1 |
| Centrum Adults vs One A Day Men (supplements) | 22783 | 0.2 | 5811 | 0.1 |
| Garnier Micellar vs Bioderma Sensibio (skincare) | 16785 | 0.1 | 4071 | 0.1 |

### Per-product aggregate (n=6 products)

| Stage | p50 ms | max ms |
|---|---|---|
| unified_search_ms | 1217 | 1579 |
| specs_ms (= Phase 1 wall) | 6238 | 11559 |
| price_ms (= Phase 1 wall) | 6238 | 11559 |
| reviews_ms (= Phase 2 wall) | 3305 | 4412 |
| rating_ms (= Phase 2 wall) | 3305 | 4412 |

Note: `specs_ms` and `price_ms` are equal per product because they are the Phase 1 `asyncio.gather()` wall time (whichever finishes second sets the wall). Same for `reviews_ms`/`rating_ms` in Phase 2. The true bottleneck inside each phase is the slower of the two parallel calls — for Phase 1, that's the specs GPT extraction with full system prompt + drug-context injection (supplements bench hit 11.6s, ~85% of its 22.8s total).

### Bottleneck identification

The dominant cold-cache stage is **Phase 1 (specs + price parallel wall)** at p50 6.2s, max 11.6s across 6 product samples. Phase 1 alone accounts for ~6-12s of the 17-23s total; verdict generation is a distant second at p50 4.2s, max 5.8s. Unified search (~1.2s) is small. Scoring and response build are sub-millisecond — already optimal.

The biggest D2 candidate fix mapping to this bottleneck is **#2: Combine specs + reviews into one structured `response_format=json_schema` call per product**. This would collapse the current 2-phase pipeline (Phase 1 ~6-12s + Phase 2 ~3-4s = ~9-16s of GPT wall time) into a single ~6-10s structured call, saving ~3-6s per product. Combined with **#1 OpenAI prompt caching** on the long static system prompt (free, zero quality risk, ~2-3s additional saving on warm cache hits), the realistic post-D2 total lands at ~10-15s — meeting the stretch goal of ≤15s average.

### Implications for Section 3 design

**Favored:** combination of D2 candidates **#1 (prompt caching) + #2 (combine specs + reviews)**. Prompt caching is the no-brainer first ship (zero quality risk, mechanical change in `extraction_service.py`). The combine-specs-and-reviews work is bigger scope (single JSON-schema call, requires 100% spec parity test from the plan's Phase 2C gate) but maps directly to the dominant bottleneck.

**Ruled out:** Candidate **#4 (drop drug-context for non-supplement queries)** — the supplements bench was the slowest at 22.8s precisely *because* drug-context injection makes the specs prompt heavier; dropping it for electronics/skincare buys very little since those phones/skincare benches were already 17-18s without the drug context. The savings (estimated <500ms) don't justify a separate code path.

**Defer:** Candidate **#3 (stream verdict last for perceived latency)** — verdict at 4-6s is significant but secondary to Phase 1. After #1 + #2 ship, if total wall stays >15s, stream-verdict-last becomes the next lever; until then it's UX polish on a pipeline that's already faster than the user sees today.

---

## Section 3 — D2 mainstream speedup design (2026-05-17, this brainstorm)

**Supersedes the Phase 2A "Implications" recommendation above** — re-examination of `_get_reviews` showed it does NOT actually depend on specs (takes `unified_search` + `retailer_ratings` only), so the Phase 1/Phase 2 split is historical, not required by data dependencies. This unlocks a lower-risk pair than "combine specs+reviews into one JSON call":

| Intervention | Wall-time saving | Quality risk |
|---|---|---|
| **(1) Collapse Phase 1/Phase 2 — move reviews into Phase 1 parallel** | ~1-2s (Phase 2 wall drops from 3.3s to ~1s) | **Zero** (no GPT prompt change, just code shuffle) |
| **(2) OpenAI prompt caching on `extraction_service.py` system prompts** | ~2-5s across 5-6 GPT calls (cache hits on 2nd+ call per category) | **Zero** (caching is transparent — same input, same output) |
| **Combined** | **~3-7s** | **Zero** |

**Math:** post-Bucket-A baseline ~18s p50 - 3.5s mid-estimate = 14.5s ≈ ≤15s target. Best case (both interventions at high estimate): 11s — hits stretch goal.

**Combine-specs+reviews-into-one-JSON-call** (the Phase 2A "favored" path) is **deferred** — kept on the table only if (1)+(2) don't reach the ≤15s p50 bar.

### Section 3.1 — Intervention 1: collapse Phase 1/Phase 2

In `_fetch_product_data` (around line 920-1000 of `app/services/structured_comparison_service.py`):

- **Current:** Phase 1 = `asyncio.gather(specs, price)` ; Phase 2 = `asyncio.gather(reviews, rating, [smart_fallback])`
- **Change:** Phase 1 = `asyncio.gather(specs, price, reviews)` ; Phase 2 = `asyncio.gather(rating, [smart_fallback])`
- `retailer_ratings = collect_retailer_ratings(...)` currently computed between phases — must move BEFORE the new combined Phase 1 since reviews now needs it as input.
- `DEBUG_STAGE_TIMINGS` instrumentation needs updating: `phase1_wall = max(specs_ms, price_ms, reviews_ms)` ; `phase2_wall = max(rating_ms, smart_fallback_ms)`. Both products still run in parallel via outer `gather` (no outer change).

**Verified preconditions:**
- `_get_reviews` signature takes `(brand, name, variant, search_query, nocache, category, retailer_ratings, search_results=unified_search)` — no specs dependency.
- Bucket A's smart-fallback (parallel-to-Phase-2 with 3s `wait_for` cap) stays in Phase 2 alongside rating — no smart-fallback re-architecture needed.

**Test gates:**
- `tests/test_fan_out_integration.py` (12 tests) + `tests/test_stage_timings.py` (2 tests) stay green
- Add `tests/test_phase1_includes_reviews.py::test_phase1_runs_reviews_in_parallel_with_specs_price` asserting Phase 1 wall time ≈ max(specs, price, reviews) (not sum); use `asyncio.sleep` mocks with known durations
- `tests/test_spec_parity.py::test_post_fix_iphone_vs_s25_has_critical_specs` (live bench) still passes
- Review citation count ±2 per product vs current production behaviour (post-Bucket-A baseline)

### Section 3.2 — Intervention 2: OpenAI prompt caching

**Mechanism:** OpenAI's `gpt-4o-mini` auto-caches any prompt prefix >1024 tokens. Subsequent identical prefixes return ~50% faster + cost ~50% less for cached portion. Cache lifetime: ~5-10 min idle, resets on use (max ~1h). No explicit `cache_control` blocks needed (that's Anthropic-style — OpenAI is automatic on size threshold).

**Where it helps:**
- **Within a single comparison:** 2 spec calls + 2 review calls per comparison share the same system prompt per category → 2nd call of each pair hits cache. Savings ~500ms-1s per cached call × ~2 cached calls = ~1-2s per comparison.
- **Across successive comparisons (same category):** more cache hits when bursty traffic to a category (e.g. multiple electronics compares in a window) lands within cache lifetime. Compounding savings.

**Implementation steps:**

1. **Audit prompt sizes** — script using `tiktoken` to count tokens in `_build_specs_prompt` + `_build_reviews_prompt` + `_build_verdict_prompt` (or wherever verdict is built). Check the STATIC prefix portion (before category interpolation) is >1024 tokens.

2. **If <1024 tokens:** restructure system prompts to push static prefix over 1024. Add only **useful content** — more category guidance, concrete extraction examples, refined output-format rules. Better prompts often perform better; cache compliance is the side benefit. Hard cap on total prompt growth: 2× current size.

3. **Reorder prompt structure** — put ALL static content FIRST (e.g. "You are an expert extractor..." + extraction principles + examples), then dynamic interpolations (`{category}`, `{fields_json}`, `{drug_context}`) AFTER. Currently `_build_specs_prompt` interpolates `{category}` at line 194 (relatively early) — restructure.

4. **Verify cache hits via response telemetry** — log `response.usage.prompt_tokens_cached` after each OpenAI call. If 0 across all calls for 24h post-deploy, caching isn't engaging → debug prefix mismatch.

5. **No explicit cache_control needed** — OpenAI auto-caches; just static-prefix discipline.

**Test gates:**
- Add `tests/test_prompt_caching.py::test_extraction_system_prompts_are_cacheable` — uses `tiktoken` to assert each prompt's static prefix tokenizes to >1024 tokens
- Add `tests/test_prompt_caching.py::test_prompt_caching_hits_logged` — runs 2 sequential extraction calls with same category against mocked OpenAI client returning `usage.prompt_tokens_cached=500` on the 2nd call; asserts cache-hit log line fires
- Spec parity test (Bucket A baseline fixture) must stay green — prompt restructure must not regress spec quality
- Verdict prose manually spot-checked for one iPhone vs S25 comparison post-deploy

**Quality risk + mitigation:**
- Risk: expanding prompts to hit 1024-token threshold degrades GPT focus → output quality drops
- Mitigation: only ADD useful content (examples, principles), NEVER filler; hard cap at 2× current size; spec parity regression test catches the failure mode
- Mitigation: if quality regresses, revert the prompt restructure commit; caching benefit lost, quality restored

### Section 3.3 — Combined verification + ship

- Pre-deploy: all unit tests green; new tests in 3.1 + 3.2 added
- Push both commits to Railway → wait `/health` 200 → run 3 cold mainstream benches (iPhone, Centrum, Garnier)
- **Success criteria:** average total wall ≤17s, p95 ≤20s, p50 ≤15s. Stretch: average ≤13s.
- Re-run `RUN_LIVE_BENCH=1 pytest tests/test_spec_parity.py::test_post_fix_iphone_vs_s25_has_critical_specs` → must still pass (both products have `front_camera` + `water_resistance` populated)
- Inspect Railway logs after 2nd cold compare for OpenAI `usage.prompt_tokens_cached > 0` — confirms caching engaged
- **Rollback:** any failed gate → `git revert <commit>` independently per intervention (don't mass-revert; we can ship one without the other)

### Section 3.4 — Out of scope (for this section)

- Stream-verdict-last (UX polish) — defer until D2 lands and we see if total wall justifies it
- Combine specs+reviews into one JSON-schema call — deferred per supersession note above
- Drop drug-context for non-supplements — savings <500ms, not worth code path divergence
- Reducing the verdict gpt-4o latency — verdict is on the higher-quality model intentionally; not in scope here

### Section 3.5 — References

- Phase 2A diagnostic data (this doc, above appendix)
- Bucket A baseline fixture: `tests/fixtures/comparison_baseline_d2.json` (committed `5aa5c22`)
- Bucket A live bench script: `tests/test_spec_parity.py::test_post_fix_iphone_vs_s25_has_critical_specs`
- OpenAI prompt caching docs (auto-caching, no API change needed for gpt-4o-mini): https://platform.openai.com/docs/guides/prompt-caching
