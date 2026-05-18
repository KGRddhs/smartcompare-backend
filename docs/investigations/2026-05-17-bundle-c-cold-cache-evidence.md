# Bundle C — D.1 Diagnostic Gate Evidence (Cold-Cache Probes)

**Status:** POPULATED 2026-05-18 by qa-bundle-c. Probes run + evidence captured. **§1b root cause CONFIRMED from code inspection; §1a high-confidence diagnosis from probe shape + code trace (Railway log paste pending for final suspect confirmation); §1c high-confidence diagnosis from probe shape.**

**Plan reference:** `docs/superpowers/plans/2026-05-17-bundle-c-scoring-quality.md` Section D.1.
**Spec reference:** `docs/superpowers/specs/2026-05-17-bundle-c-scoring-quality-design.md` §1a / §1b / §1c.
**Branch:** `feature/bundle-c-scoring`.

> **GATE:** A.3.1 (§1a fix), A.3.2 (§1b factual_verdict builder), A.3.3 (§1c price-pipeline fix) MAY NOT land in the codebase until the three "Diagnosed root cause" subsections below are populated AND committed by qa-bundle-c. This file is the commit that opens that gate.

---

## Probe configuration

- Endpoint: `https://web-production-58776.up.railway.app/api/v1/text/compare`
- Query params: `?q=<query>&region=bahrain&nocache=true`
- Railway env var during window (single flag — backend consolidated all three diagnostic groups onto `DEBUG_STAGE_TIMINGS` per `_PROS_CONS_DIAG_FLAG` / `_FACTUAL_VERDICT_DIAG_FLAG` / `_PRICE_PIPELINE_DIAG_FLAG` cached process-init reads, mirroring `structured_comparison_service._DEBUG_STAGE_TIMINGS` pattern):
  - `DEBUG_STAGE_TIMINGS=true` — gates ALL of: PROS_CONS_DIAGNOSTIC (A.2.1, `extraction_service.py:28`), FACTUAL_VERDICT_DIAGNOSTIC (A.2.2, `response_builder.py:30`), PRICE_PIPELINE_DIAG (A.2.3, `firecrawl_service.py:27` + `scrapedo_service.py:26`). Verified by grep — no `DEBUG_VERDICT_RAW` / `DEBUG_FIRECRAWL_INVOCATIONS` / `DEBUG_SCRAPEDO_INVOCATIONS` exists in code.
- Sleep 3s between probes to avoid rate-limit / breaker false trips.

### 6 probe queries (run 2026-05-18T07:27-07:29 UTC by qa-bundle-c)

| Category | Query | Status | Wall (s) | Response bytes |
|---|---|---|---|---|
| electronics | `iPhone+16+vs+Galaxy+S25` | DONE | 16 | 15,496 |
| skincare | `CeraVe+vs+Cetaphil+Moisturizing+Cream` | DONE | 18 | 15,963 |
| supplements | `Centrum+Silver+vs+One+A+Day+Men's` | DONE | 15 | 14,649 |
| fashion | `Zara+blazer+vs+H&M+blazer` | DONE | 14 | 14,096 |
| fragrances | `Tom+Ford+Oud+Wood+vs+Dior+Sauvage` | DONE | 12 | 15,182 |
| grocery | `Almarai+laban+vs+Saudia+laban` | DONE | 14 | 14,736 |

Probe JSON files saved at `/tmp/bundle-c-d1-evidence/<category>.json` (NOT committed — per plan D.1.2 evidence note "do NOT commit raw probe payloads; link via gist or summarize inline").

**Wall sanity check:** All 6 within `STREAM_HARD_CAP_SECONDS=25.0` lock. Mainstream categories (skincare/electronics/supplements) within Session 50 target band (14-17s). Fragrances 12s lowest (Session 51 measurement confirmed — fragrances Firecrawl never fires in current production, falls straight to Tier 3 GPT estimate, fast-fail not slow-fail).

---

## §1a — Pros/cons empty diagnostic

**Symptom (confirmed across all 6 probes):** Every probe returned `products[*].pros = []` AND `products[*].cons = []`. Inspection of `comparison.product_0_pros / product_0_cons / product_1_pros / product_1_cons` shows ALL FOUR keys are `None` (not `[]`).

This is the smoking-gun signal:
- If the verdict GPT had emitted the keys with `[]`, `comparison.pop(key, [])` (`structured_comparison_service.py:720-725`) would return `[]` and `products[*].pros_cons = {"pros": [], "cons": []}` — frontend `.pros` accessor would surface `[]`.
- Instead the keys are MISSING from `comparison` entirely. The `comparison.pop(..., [])` default `[]` IS swallowing the missing-key case — and that's why frontend sees `[]`.
- But the root question is WHY the GPT response is missing the keys.

**Code trace:**
- Verdict prompt at `extraction_service.py:540-543` explicitly requests `product_0_pros / product_0_cons / product_1_pros / product_1_cons`.
- Verdict prompt RULES at `extraction_service.py:559`: "4-6 pros, 2-4 cons per product -- each MUST include a specific number, percentage, or measurable fact".
- Verdict response parsed at `extraction_service.py:1137` (`json.loads`).
- Diagnostic at `extraction_service.py:1143-1152` logs `PROS_CONS_DIAGNOSTIC empty_side=... comparison_keys=... raw_response=...` ONLY when `DEBUG_STAGE_TIMINGS=true` AND `parsed.get("product_0_pros")` or `parsed.get("product_1_pros")` is empty/missing.
- Since flag is ON AND all 6 probes empty, **6 PROS_CONS_DIAGNOSTIC warnings MUST be in Railway logs right now**.

### Probe evidence per category (CAPTURED 2026-05-18)

| # | Category | `pros_a` len | `cons_a` len | `pros_b` len | `cons_b` len | `comparison.product_0_pros` | Diagnosed cause (high confidence pending Railway log) |
|---|---|---|---|---|---|---|---|
| 1 | electronics | 0 | 0 | 0 | 0 | None (key absent) | Suspect 1 + 2: verdict GPT not emitting pros/cons keys |
| 2 | skincare | 0 | 0 | 0 | 0 | None (key absent) | Suspect 1 + 2 |
| 3 | supplements | 0 | 0 | 0 | 0 | None (key absent) | Suspect 1 + 2 |
| 4 | fashion | 0 | 0 | 0 | 0 | None (key absent) | Suspect 1 + 2 |
| 5 | fragrances | 0 | 0 | 0 | 0 | None (key absent) | Suspect 1 + 2 |
| 6 | grocery | 0 | 0 | 0 | 0 | None (key absent) | Suspect 1 + 2 |

### Diagnosed root cause (HIGH CONFIDENCE — confirms with Railway PROS_CONS_DIAGNOSTIC log paste)

**Root cause:** Verdict GPT response is NOT emitting `product_0_pros` / `product_0_cons` / `product_1_pros` / `product_1_cons` keys in the JSON output. The `comparison.pop("product_0_pros", [])` default at `structured_comparison_service.py:720` then silently swallows the missing keys and writes empty `pros_cons` to `products`.

**Sub-cause hypothesis (suspect 1 OR 2, distinguishable by Railway log inspection):**
- **Suspect 1 (most likely):** Model is omitting fields under pressure. The verdict prompt is LARGE — includes user_preferences block, cohort block, value_context per product, best_for per product, specs_comparison object, personalized_insights array. Even with `gpt-4o` at `temperature=0.1`, with this many required JSON keys, the model is dropping the pros/cons keys to stay within practical response length. This is a known failure mode when the JSON schema includes 12+ named fields + the model has scarce response tokens.
- **Suspect 2 (likely):** `model_router.get_model(priority="high")` returning `gpt-4o-mini` (since `DAILY_4O_CAP` may be exceeded) — mini omits fields more aggressively than 4o under the same prompt load.
- **Suspect 3 (RULED OUT by code trace):** `validate_verdict` is NOT in extraction_service.py at lines 700-701 (those are in middle of a different function); no `validate_verdict` function strips pros/cons before the `comparison.pop` happens. The spec §1a third bullet was a planning-time hypothesis that didn't survive code inspection.
- **Suspect 4 (RULED OUT):** Prompt is CRYSTAL CLEAR — `product_0_pros: ["specific pro with number/fact"]` listed twice (lines 540-543) with explicit RULES at line 559. Not a clarity issue.

**Final-suspect resolution requires:** Railway PROS_CONS_DIAGNOSTIC log lines (`grep "PROS_CONS_DIAGNOSTIC" railway logs` for the 6-probe window) showing:
- `comparison_keys=[...]` — confirms which keys ARE in the parsed JSON.
- `raw_response=...` — shows the actual GPT output, proves which fields were dropped.
- Whether the omitted side is consistently p0 vs p1 vs both (would indicate model token-budget exhaustion on the later-emitted keys).

**Proposed fix scope (A.3.1) — depends on Railway log:**
- IF model is truncating output (most likely): force `model_router.get_model(priority="critical")` for verdict, OR add `response_format={"type": "json_object"}` to ensure complete JSON, OR shorten the prompt by collapsing redundant RULES lines.
- IF cohort/preference block is bloating prompt past ~3k tokens: gate the cohort block on category-relevant rendering only.
- The spec §1a says: "No fallback re-prompt unless diagnosis proves it. Targeted re-prompts trade cost + latency for completeness; require evidence." Once Railway logs land, the smallest-blast fix lands. NO speculative re-prompt fallback as default.

**Sign-off (qa-bundle-c, high-confidence):** Backend authorized to begin A.3.1 ONLY AFTER Railway PROS_CONS_DIAGNOSTIC logs confirm whether suspect 1 or suspect 2 is firing. The fix MUST target the diagnosed sub-cause (e.g., switch model router priority, or add `response_format`, NOT a brute-force re-prompt fallback).

---

## §1b — `scoring_v2.factual_verdict` is None on every probe

**Symptom (confirmed across all 6 probes):** `scoring_v2.factual_verdict` is MISSING (not None — the key is absent from the dict entirely).

`scoring_v2` keys observed in every probe: `['overall_score', 'win_margin', 'dimensions']`. NO `factual_verdict` key.

### Trace evidence (CONFIRMED by code inspection — `response_builder.py:51-98`)

`_build_scoring_v2` returns this dict (line 66-74):
```python
scoring_v2 = {
    "overall_score": {
        "product_a": score_a,
        "product_b": score_b,
        "winner_idx": winner_index,
    },
    "win_margin": abs(score_a - score_b),
    "dimensions": dimensions,
}
```

**File:line of `_build_scoring_v2`:** `app/services/response_builder.py:51-98`
**Missing builder reference:** NO `_build_factual_verdict()` function exists in `response_builder.py`. The dict literal at line 66-74 simply doesn't include a `factual_verdict` key. There is also NO `factual_verdict` assignment anywhere downstream — `response_builder.py:194-195` builds `pros_cons` per product but never touches `scoring_v2.factual_verdict`.

**Diagnostic confirmation:** The `_factual_verdict_present_in_scoring_v2()` helper at `response_builder.py:35-42` returns False when the key is missing OR when `line1` / `line2` are absent. The diagnostic at line 80-96 fires `FACTUAL_VERDICT_DIAGNOSTIC scoring_v2_emitted_without_factual_verdict ...` warnings on Railway right now (flag is ON, all 6 probes triggered it). The diagnostic itself is informational only — it doesn't fix anything; the genuine absence of the builder is the root cause.

**Existing fields available for template (per spec §1b):**
- `line1` = winner declaration with strongest factual delta (price gap, rating gap, or top dim margin).
- `line2` = runner-up's strongest counter-fact.

Both can be built from EXISTING scoring response keys (no GPT call needed):
- Winner index: `scoring_result["scores"]["winner_idx"]`.
- Per-dim scores: `scoring_result["scores"]["product_0"]` / `["product_1"]`.
- Per-product price: `product_data[i]["price"]["amount"]`.
- Per-product rating: `product_data[i]["rating"]`.

### Diagnosed root cause (CONFIRMED)

**Root cause:** The `_build_scoring_v2` builder at `response_builder.py:51-98` simply does NOT emit a `factual_verdict` key. The function never had one — this is a planning-time omission, not a regression. Pure template fix per spec §1b.

**Proposed fix scope (A.3.2):**
1. Add a new `_build_factual_verdict(product_data, scoring_result, winner_index) -> dict` helper to `response_builder.py`.
2. Compute `line1` from the largest of: price gap (winner cheaper / more expensive by X%), rating gap (winner Y stars higher), top-dim margin (winner Z points ahead on dim Q).
3. Compute `line2` from the strongest counter-fact on the runner-up's best dim (whichever dim the runner-up wins).
4. Both strings respect the FIVE critical rules — no scary copy, no backend internals, no "estimated"/"reference price".
5. Insert `"factual_verdict": _build_factual_verdict(...)` into the `scoring_v2` dict literal at line 66-74.
6. Regression test asserts `scoring_v2["factual_verdict"]["line1"]` non-empty for any populated comparison.

**ZERO GPT cost.** Builder is pure-Python from existing data.

**Sign-off (qa-bundle-c, confirmed):** Backend authorized to begin A.3.2 immediately upon D.1.3 commit landing. No Railway log needed — this is a code-trace-confirmed cause.

---

## §1c — Price pipeline regression (mainstream queries fall to `estimated`)

**Symptom (confirmed across all 6 probes):** Every product on every probe hits `source_method='estimated'`, `estimated=True`, `retailer=None`, `shopping_count=None`, `note="Estimated from training data"`.

Most damning: even `Almarai laban` (mainstream Saudi grocery item, ubiquitous in Bahrain stores) falls to estimated at 0.56 BHD. Even `Centrum Silver` (mass-market supplement). This is system-wide, not luxury-only.

**Stage timings (electronics probe — representative):**
```
per_product[0]: unified_search_ms=461 specs_ms=2990 price_ms=4014 reviews_ms=5872 phase1_wall_ms=5988
per_product[1]: unified_search_ms=471 specs_ms=3722 price_ms=4280 reviews_ms=5563 phase1_wall_ms=5683
```

`unified_search_ms=461` confirms Serper Shopping CALL is happening — but `shopping_count=null` on price means the Serper response either had ZERO items OR the parser isn't pulling them. `price_ms=4014` is 4 seconds in the price pipeline — that's Tier 1 → 1.5a (Firecrawl) → 1.5d (Scrape.do) → 2 → 3 cascade actually walking the tiers, NOT a fast-fail; it's iterating through all of them and STILL landing on estimated.

**Suspect list (per spec §1c, ranked by prior plausibility — updated post-evidence):**
1. **Serper Shopping returning zero items per query** (HIGH LIKELIHOOD). Even if region=bh / GCC market is thin, Almarai + Centrum should have results.
2. **`api_budget_service` reporting exhausted credits** (PLAUSIBLE — Firecrawl 450 lifetime is a small pool).
3. **Circuit breakers tripped from earlier failures** (PLAUSIBLE — 3 fails → 10-min cooldown).
4. **`_validate_price_query` rejecting queries upstream** (LOW LIKELIHOOD — mainstream queries shouldn't trigger garbage-query rejection).
5. **`_extract_price_from_html` parser regression** (LOW — would surface as failed_curl_urls accumulation, but `shopping_count=null` is upstream of HTML parse).

### Per-category root-cause table (CAPTURED 2026-05-18)

> Final `source_method`, retailer, shopping_count, estimated flag captured from probe JSON. Firecrawl/Scrape.do invocation columns require Railway log paste (PRICE_PIPELINE_DIAG lines from `firecrawl_service.py:27` + `scrapedo_service.py:26`).

| Category | Phase 1 wall (ms) | Final `source_method` | Retailer | shopping_count | Firecrawl fired? | Scrape.do fired? | Diagnosed root cause |
|---|---|---|---|---|---|---|---|
| electronics | 5988 / 5683 | estimated | null | null | TBD (await Railway log) | TBD | Suspect 1 + 2 / 3 |
| skincare | TBD | estimated | null | null | TBD | TBD | Suspect 1 + 2 / 3 |
| supplements | TBD | estimated | null | null | TBD | TBD | Suspect 1 (Bahrain pharmacy JSON-LD may also be failing) |
| fashion | TBD | estimated | null | null | TBD | TBD | Suspect 1 + 2 / 3 |
| fragrances | TBD | estimated | null | null | TBD | TBD | Per MEMORY note "Firecrawl never fires in production for fragrances" — Suspect 1 + Tier 1.5a not firing |
| grocery | TBD | estimated | null | null | TBD | TBD | Suspect 1 strongly (Almarai laban) |

### API budget + circuit-breaker snapshot during window

> qa-bundle-c: requires Railway log paste. The `api_budget_service` exposes credit state via the new `get_remaining(provider)` + `get_breaker_state(provider)` helpers added in `28cb90e` (A.2.3 commit) — backend logs these alongside each Firecrawl/Scrape.do invocation.

| Service | Credits remaining | Circuit-breaker state | Last failure timestamp |
|---|---|---|---|
| Firecrawl (lifetime 450) | TBD — Railway log | TBD | TBD |
| Scrape.do (monthly 900) | TBD — Railway log | TBD | TBD |
| Serper (lifetime 2200) | TBD — Railway log | TBD | TBD |

### Diagnosed root cause (HIGH CONFIDENCE pending Railway log — Suspect 1 + 3 most likely)

**Root cause (provisional, needs Railway log confirmation):** The price pipeline IS walking all 5 tiers (Phase 1 wall ~5-6s confirms cascade not fast-fail). But Tier 1 Serper Shopping returns ZERO items (`shopping_count=null` is consistent across ALL 6 categories), tiers 1.5a (Firecrawl) and 1.5d (Scrape.do) likely also fail (either no URL to scrape because Tier 1 had nothing, OR credits exhausted / breaker tripped), Tier 2 GPT extraction from organic search likely no usable data, falls to Tier 3 GPT training estimate.

Three possible distinct sub-causes per probe (Railway log will disambiguate):
1. **Serper API key exhausted or invalid.** `unified_search_ms=461` doesn't prove the response had content — could be a 200 with empty `shopping` array (or a 4xx that's caught and logged). Per MEMORY note: ~2,500 Serper credits remaining as of 2026-02-28 rotation; cumulative usage since then could have depleted.
2. **Firecrawl / Scrape.do credits exhausted or breakers tripped.** Firecrawl 450 lifetime is small; if Bundle E + Session 49-51 testing burned through it, tiers 1.5a/d fail-open → cascade falls through to Tier 3.
3. **Region scoping issue.** `region=bahrain` may be coercing Serper to a country code with thin coverage; loosening to region=GCC or unset might surface results.

**Proposed fix scope (A.3.3) — depends on Railway log:**
- IF Serper credits exhausted: rotate to new free account (Ahmed action, operational not code), or reduce per-comparison Serper call count via cache aggressive on category-key.
- IF Firecrawl/Scrape.do credits exhausted: top-up (Ahmed), or change cascade order to prefer organic-search Tier 2 GPT before Tier 1.5 page-scrape tiers (reduces credit burn for cases where scrape won't help).
- IF Serper coverage genuinely thin for Bahrain: per spec §1c "5 likely causes — narrow to 1-2 actual", may need to accept the regional-gap reality and improve Tier 2 / Tier 3 quality + UX (per §5c "Price pill HIDDEN when any product source_method=estimated").
- IF circuit breakers tripped: probe `api_budget_service` state, reset breakers if false-trip, investigate root failure pattern.

**Sign-off (qa-bundle-c, provisional):** Backend authorized to begin A.3.3 ONLY AFTER Railway PRICE_PIPELINE_DIAG logs confirm WHICH of the 3 sub-causes is firing. NO speculative fix (e.g., "just add more scrape providers") without evidence.

---

## D.1.4 — Diagnostic window closure

**Closed at:** TBD (timestamp once Ahmed unsets the single `DEBUG_STAGE_TIMINGS` env var on Railway — closes all three diagnostic groups in one flip). Window opened approx 2026-05-18T07:00 UTC by Ahmed.

**Verification:** 1 probe run post-closure → `metadata.stage_timings_ms` MUST be absent from the response body.

**Per `memory/feedback_measure_before_optimize.md`:** diagnostic env vars cost zero in production with flag off, but leaving them on long-term invites accidental dependencies. Close the window cleanly AFTER:
1. Railway PROS_CONS_DIAGNOSTIC + FACTUAL_VERDICT_DIAGNOSTIC + PRICE_PIPELINE_DIAG logs captured.
2. A.3.1 / A.3.2 / A.3.3 patches landed in code.
3. 1 verification probe per category confirms pros/cons populated, factual_verdict emits, real prices land.

---

## Next-action ranked list (qa-bundle-c — gate opens conditionally)

1. **A.3.2 (§1b factual_verdict builder) UNBLOCKED IMMEDIATELY** — root cause confirmed by code inspection (no Railway log needed). Backend can begin pure-template builder per the proposed fix scope above.
2. **A.3.1 (§1a pros/cons empty) BLOCKED on Railway PROS_CONS_DIAGNOSTIC log paste** — high-confidence diagnosis points to suspect 1 (verdict model dropping keys under JSON schema pressure) but specific sub-cause (model omits OR mini routing OR token budget) requires log inspection. NO speculative fix.
3. **A.3.3 (§1c price-pipeline) BLOCKED on Railway PRICE_PIPELINE_DIAG log paste** — high-confidence diagnosis points to Serper Shopping returning zero items + Firecrawl/Scrape.do not firing (either credit/breaker exhaust or no upstream URL to scrape). NO speculative fix.

> **For team-lead / Ahmed:** Please run `railway logs --since 30m | grep -E "(PROS_CONS_DIAGNOSTIC|FACTUAL_VERDICT_DIAGNOSTIC|PRICE_PIPELINE_DIAG)"` and paste the output to qa-bundle-c via SendMessage. Once received, qa-bundle-c will append a follow-up commit to this file with the final-suspect resolutions and OPEN gates A.3.1 + A.3.3.
