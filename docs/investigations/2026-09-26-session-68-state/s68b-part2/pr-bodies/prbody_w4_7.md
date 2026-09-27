## W4-7: fact-check honesty (three dark flags)

Scope: the reliability dimension stops scoring what nobody checked, the confidence pills read ONE computation of the price the user sees, and the fact-check reads the shopping rows `_get_price` actually wrote.

Findings: PO-FACTCHECK-CONFIDENCE-01 (P1), -02 (P1) + -06 (P2), the activation of -03 (#109) and -04 (#106), -10 (#108 in the activation docstring), and one defect the review did not find (Part C, the shopping-cache key drift).

Anchor drift: the spec was measured at 61585c58. This branch sits at 15e1fb89 (main minus the docs-only #214; it already contains W4-6a #212 and W4-12 #213). Every anchor was re-located by symbol:
- scoring_service moved +62..+129 lines
- response_builder moved about +109..+127
- structured_comparison_service moved about +26..+40
- the four wrong-key readers moved from :5478/:5499/:5517/:5718 to :5518/:5539/:5557/:5758 at 15e1fb89 (on this branch they sit inside `_fetch_product_data` at the spec cross-validation, `collect_retailer_ratings`, `_get_verified_rating` and `verify_price` lookups)
- the `_get_price` key assembly moved from :6169-6172 to :6209-6212 and is now the helper `_shopping_cache_key`
- The client (SmartCompareApp) is unchanged between 61585c58 and 15e1fb89.

W4-11 (#223, now on main 8a1e0d55) also edits structured_comparison_service.py, in different functions. This branch is rebased after the verdict and its unit files are re-run on the rebased bytes.

### Defects
- **Part A:** `_score_reliability` scores an all-unverified fact-check (the warm-cache shape) at 0.3. Only side signals move it: `price_verified` +0.1 and sentiment +0.05 / -0.1. On an otherwise identical pair, a fabricated `price_verified` alone decides the winner in all 9 categories (dims 40.0 / 30.0, margins 1.4-2.5).
- **Part B:** two confidence computations ship.
  - `overview.confidence` comes from the orchestrator. It uses the PRE-pend price, `shopping_count = len(self._shopping_items_cache)` (the number of product KEYS, not listings) and `cached = from_cache` ("cache allowed", not "served from cache").
  - `scoring_v2.confidence_legs` / `confidence_details` is the only surface the phones read. It is a second computation with count 0 and `cached=False`.
  - Result: "Medium" is unreachable on the pill, and "Pricing checked just now." shows on every compare.
- **Part C:** `_fetch_product_data` reads `_shopping_items_cache[full_name]` with the display identity, while `_get_price` writes under its own key. 8 of 13 measured name shapes disagree. On those shapes all four readers see ZERO rows:
  - `verify_price` certifies the price (`True, None`), and #106 is inert.
  - The spec cross-validation gets `[]`.
  - `collect_retailer_ratings` gets nothing, so `review_sentiment_consistent` is None.
  - The `_get_verified_rating` cache lookup gets nothing.

### Design
Every new branch sits under a per-call reader (the `confidence_factcheck_wiring_enabled` idiom: `os.getenv(NAME, "").strip().lower() in ("true", "1", "yes", "on")`). All three flags are default OFF, none has a knob, and none rides #109 or #106.

| Flag | Default | Effect ON | OFF identity |
|---|---|---|---|
| `ENABLE_RELIABILITY_UNCHECKED_ABSENCE` (Part A, `reliability_unchecked_absence_enabled()`) | OFF, per call | **Coupled:** the reader returns False unless `ENABLE_MISSING_DIM_RENORM` is also ON (pinned both ways). `_score_reliability` returns None when verified+likely+flagged == 0. That is a ONE-SIDED None (R2), with no pair collapse. `price_verified` and sentiment are never reached for an unchecked fact-check. Checked shapes are untouched. | The branch is skipped |
| `ENABLE_CONFIDENCE_SINGLE_COMPUTATION` (Part B, `confidence_single_computation_enabled()`) | OFF, per call | See the Part B list below. | The caller's dict ships and scoring_v2 recomputes exactly as before; no stash, no captured bookkeeping |
| `ENABLE_FACTCHECK_SHOPPING_KEY` (Part C, `factcheck_shopping_key_enabled()`) | OFF, per call | See the Part C list below. | Every call is byte-identical, including the positional `_get_verified_rating(full_name)` |

**Part A, the honest cost:** under renorm, zero-bucket vs 8/0/0 excludes reliability for the pair, and the crown falls to the other dimensions (67.0/67.0 on the spec's pair). A flagged-vs-unchecked pair equals its empty-side equivalent. Part A with renorm OFF is inert, pinned by A1b.

**Part B, effect ON:**
- **The stash.** `_fetch_product_data` stashes `result["_shopping_listing_count"]`: the identity-matched count under the `_get_price` key. Each row is judged alone by the REAL `extract_price_from_shopping`, with the region's currency and the orchestrator category (R4/R13). A row the extractor raises on is skipped and never counted (R26b).
- **A count only where rows exist (R25, R29, R31a).** A pool is CAPTURED iff the shopping list returned for this product this request is NON-EMPTY. A count of 0 therefore means "rows exist and none matched" (R13), and only such a 0 caps the leg. Every EMPTY pool stashes None (unknown), whatever its cause, because production cannot tell the causes apart from the return shape:
  - a real price-cache hit (`_get_price` returns before it writes `_shopping_items_cache`) and a partial build (no key for the product);
  - a real empty Serper Shopping 200: `search_product_prices` returns `{'shopping': [], 'shopping_region': 'us_fallback'}` for the GCC region code;
  - a failed search: `_do_serper_shopping` returns `{}` on any non-200 (403/429/5xx), on Serper's own httpx timeout and on a network error or exception, and `search_product_prices` then returns the SAME empty `us_fallback` dict. A failed search never raises out of `search_product_prices`;
  - no Serper key, or the #60 budget exhausted: `{'shopping': [], ..., 'error': ...}` with NO call made;
  - the Tier-1 clamp timeout: the genuine-priority clamp times the search out and substitutes `{'shopping': []}`;
  - the supplements path: no shopping call is made and `_get_price` writes a synthetic `[]` under the key (and, when iHerb returns a rating, later overwrites it with a one-row rating list; the key stays unknown).
  - The `shopping_region` and `error` keys are NOT consulted: they cannot distinguish these cases.
  - Implementation: the flag-OFF `_shopping_items_cache` writes are byte-identical (other readers iterate that list). Under the flag only, `_get_price` records each write in a per-service set `_shopping_uncaptured_keys` through `_mark_shopping_pool_captured(service, key, captured)`: after the Tier-1 write `captured = bool(shopping_items)` (the non-empty test; for a list it equals `len(shopping) > 0`), and after the supplements `[]` write `captured = False`. A non-empty return clears an earlier mark (the last write for a key wins). The stash reads None when the key is absent from the cache (R25) or present in that set.
  - The bookkeeping is keyed by the `_get_price` key (`_lc_key`), never the display identity (R31b, B18: a brand-repeating name whose two keys differ).
  - The check is per PRODUCT KEY, never "the cache is empty" (R29): on one service instance where the cache holds the OTHER product's key, this product stashes None while the other stashes its count (B17).
  - In the builder, a product with an unknown count enters the single computation EXACTLY as the flag-OFF path passes it, so its price leg equals the flag-OFF leg. A product with a count, 0 included, rides a copy as `shopping_count`.
  - What this costs: Part B's improvement (the identity-matched count instead of the raw row count) applies exactly where rows exist. On an empty pool the flag-OFF computation sees the same absence of listings, so nothing is lost there.
- **The replay is log-silent (R19).** A ContextVar-scoped `logging.Filter` drops only records created inside the synchronous replay window.
  - The var is set with a token and reset in a `finally`.
  - The filter is installed idempotently on five loggers (price_service, content_safety_service, exchange_rate_service, source_router, extraction_service), and only on a flag-ON count. It is never installed at import.
  - Other threads and contexts are never filtered.
  - One record per logger is pinned: dropped inside the window, emitted outside it (R26a, B12g).
- **One computation.** After the price-pending chokepoint, `build_comparison_response` runs ONE `compute_confidence` on COPIES, with `cached =` the REAL cache hit (`_compute_cache_observability(...)["cache_hit"]`, R3).
- **The R12 cap.** When ANY product has no shown price, the price leg is capped at `weak` and `overall` is recomputed. "No shown price" means `unavailable`, amount None, or a raw None price left by a degraded chokepoint (R26c). A NON-DICT price (99.0, 'BHD 99', 0) never reaches the cap as such: with the chokepoint healthy it normalises the price to `{amount: None, unavailable: True, reason: pending_genuine}` BEFORE the cap, so the cap fires (Part B ON: weak; flag OFF: strong). With the chokepoint degraded (`get_region_currency` raising), a non-dict raw price makes the builder raise AttributeError at `p.get("price", {}).get("source_method")` (response_builder.py:1863 on this branch), at BASE as well and in both flag states: a pre-existing limit of the builder, not of this unit (measured by adversary r4: [pyt] tag=a5-probe 11:06:08-11:06:12 OK; tag=a5-probe2 11:06:39-11:06:42, 4 of 4 nodes raised at :1863).
- **Both surfaces.** The dict ships verbatim on `overview.confidence` AND is threaded K12-style into `_build_scoring_v2(precomputed_confidence=)` -> `_confidence_legs_and_details(precomputed=)`. An EMPTY precomputed dict is honoured as "computed, no legs" (R22e).
- **Failure path (R20).** If the single computation raises, the flag-OFF path runs EXACTLY: nothing is threaded, overview ships the caller's dict, and ONE `WARNING [W4-7] single confidence computation failed: <ExceptionType>` is logged, type only (never str(e), never exc_info).
- **The R16 pop.** `_shopping_listing_count` is popped UNCONDITIONALLY before `result["products"]`. Exact identity claim: flag-OFF output is byte-identical for every input that does not already carry `_shopping_listing_count`, and only the flagged orchestrator writes it.
- **Left alone:** the three orchestrator `compute_confidence` calls and the SSE `scores` payload (no client reader). price_service and serper_service are untouched (R9/R10).

**Part C, effect ON:**
- A new module helper `_shopping_cache_key(brand, name, variant)` holds the `_get_price` key verbatim. `_get_price` builds its key through it. This is an UNFLAGGED refactor that produces a byte-identical string, pinned over 13 shapes plus a source pin.
- Under the flag, the four readers use that key through `_shopping_cache_key_or(..., fallback=full_name)`:
  - the spec cross-validation lookup (its identity argument is unchanged)
  - `collect_retailer_ratings(full_name, {full_name: rows})`
  - `_get_verified_rating(full_name, cache_view={full_name: rows})`. R15: the new optional kwarg defaults to None, which means today's cache; any dict, even an empty one, is the view; `full_name` stays the rating query; rating_service.py is untouched.
  - the `verify_price` lookup
- **The wrapper (R24).** `_shopping_cache_key_or` returns `full_name` when the identity is malformed (a non-str variant, a None name). `_get_price` keeps calling the raw helper, so its flag-OFF path is byte-identical. For those inputs `_get_price` itself raises inside the Phase-1 gather, so nothing is cached under ANY key, and the wrapper's fallback key can never match a cache entry. A flag-ON fetch therefore completes wherever a flag-OFF fetch completes (C10 on ('Apple', 'iPhone 15', 256) and ('Samsung', None, 'Ultra')).
- **HARD ACTIVATION docstring** (`confidence_factcheck_wiring_enabled`): Part C goes immediately BEFORE #106. #108 ENABLE_CITATION_RUBRIC_V2 is added to the same chain (R8, docstring only).

**Rejected alternatives for R19:**
- `logging.disable` / `logger.setLevel`: both are process-global and would drop other coroutines' and threads' lines.
- Any price_service change: forbidden by R9/R10.
- Computing the count from a re-implemented acceptance: R13 forbids a second acceptance.

Files: app/services/scoring_service.py (+37), app/services/response_builder.py (+59/-6), app/services/structured_comparison_service.py (+149/-11); 245 insertions, 17 deletions across the three. Three new test files (326 nodes).

### Gates (measured on the final bytes)
- **Unit files: 326 passed in SIX states**, about 4 s each, `[netguard] blocked 0`, `[hermeticity] sentinel checked 326`:
  - all unset
  - A = absence + renorm
  - A-without-renorm (inert)
  - B
  - C
  - ALL = the three flags + renorm
- **Mutation matrix** (this replaces any "every line is covered" claim): 117 rows on the final bytes, from byte snapshots, every restore sha256-verified.
  - Sources of the rows: adversary r5's 110-row table verbatim (adversary r3's 87 rows, adversary r4's 9 V rows, the fixer-r5 8 R28 rows, adversary r5's Q1-Q6) and 7 R31 rows.
  - **107 killed**, each by a named node. The rows closed in the last rounds:
    - R31a: R31-E1 / R31-E2 (an empty pool treated as captured: `True` / `len(shopping_items) >= 0`) by 8 nodes each (B15e real empty `us_fallback`, B16 failed search `raises` / `http_fail` through the REAL `search_product_prices`, B16 error no-call shape `stub_no_key` / `real_no_key` / `real_budget_out`, B16 clamp timeout, B18 empty); R31-N1 (a non-empty pool treated as unknown) by B16 real returns (zero_matches and three_matches), B17 and B18 three_matches; R31-OLD (the round-5 region predicate reinstated) by 7 nodes (every Tier-1 empty-pool row except the clamp timeout, which the old predicate also marked); R31-Q5x (a `us_fallback` return marked uncaptured, adversary r5's Q5 re-expressed on the new line) by the four non-empty rows; R31-S1 (the supplements mark removed) by B16 supplements and B18 supplements.
    - R31b: adversary r5's Q1 (the uncaptured check reads the display `full_name`) by B18 (empty `us_fallback` and supplements rows, 2 nodes).
    - R28: R28a (the supplements `[]` marked captured) by B16 supplements; R28d (the stash ignores the uncaptured set) by the empty-pool rows; R28e (a non-empty return no longer clears an earlier mark) by B16 last-write-wins; R28f (the Tier-1 bookkeeping never runs) by the empty-pool rows; R28g / R28h (the bookkeeping unguarded, i.e. written with the flag OFF) by the B16 flag-OFF pin. Adversary r5's Q2, Q3, Q4 are killed.
    - R29: V1 (the captured check reads the whole cache, not this product's key) by B17.
    - Adversary r4's other V rows: V3 (A13), V6 (B5), V10 (C7), V11 (C8), V14 (C5), V15 (C1), V16 (B8), V17 (B13).
    - R25: Z1 and W5 (the cache-hit stash forced to 0) by B15/B16/B17; Z2 (None treated as 0) by B15b[own_count_3]; Z3 (a falsy count treated as unknown) by B15c; W2 by B15b/B15d; W3 by B5; W6 (the unknown product dropped from a mixed pair) by B15d.
    - R26a: Y1/Y2/Y3 (exchange_rate / source_router / extraction logger removed from the filter) by B12g; X2/X2b by B12/B12b.
    - R19: F1/F1b/X1/X17/R19b by B12/B12b/B12c; W4 by B12c; R19c by B12d; R19d/R19i by B12e/B12f.
    - R20: R20a/b/c by B11b; N4/F3 by B11.
    - R12: M-R12 by B3/B3b/B3c; N2 by B3e; X18 by B3g; R12n by B3f; Y4 by B3/B3c; Y12 by B3d.
    - R22: N5 by B13/B13b; N6 by B13/B13c; N7 by B14; N14 by B4/B15b; N1/N17 by B3d.
    - R15: X19 by C9b; X3 (the wrapper re-raises) by C10.
    - The per-row guard: X4/X4b by B13d.
  - **5 survive, each accepted as equivalent on reachable inputs:**
    - Y5 (the except branch keeps a partial `_single_conf`): after `_single_conf` is assigned, nothing in the branch can raise on `compute_confidence`'s dict contract, so the branch is only reached with `_single_conf` still None.
    - Y6 (the count replays an empty pool instead of returning early): an empty loop counts 0 and creates no record inside the window.
    - Y10 (the wrapper's fallback is `""` instead of `full_name`): R24. `_get_price` raised for that identity, so neither key can match a cache entry.
    - W1 (the R25 check `key not in cache` -> `not cache.get(key)`): under R31a every empty pool is already marked uncaptured by the flag-ON writer, so reading an empty pool as unknown at the stash changes nothing. The two forms differ only if an empty pool reaches the stash unmarked (see Stated limits). W1 was killed by B15e before R31 moved that pin.
    - R31-Q6x (a return carrying an `error` key also marked uncaptured, adversary r5's Q6 re-expressed): every production `error` return carries an empty shopping list, which is already uncaptured.
  - **4 not applicable** (their pattern no longer exists; each is re-expressed and killed above): R28b and adversary r5's Q5 and Q6 targeted the removed `shopping_region != "clamp_timeout"` predicate; R28c ("a real EMPTY return marked uncaptured") is now the ruled behaviour. Adversary r5's Q5 reading (a `us_fallback` return treated as uncaptured) is N/A by construction: the region is never consulted.
  - **1 dropped:** X22. Its line (a no-op `confidence = ... else {}`) was removed in round 2.
  - Known weak rows: B15b's two `no_count` rows pass on the pre-R25 bytes as well, because on production shapes None and 0 give the same leg. They pin the production reading only. The unknown-count semantics are carried by B15b[own_count_3], B15, B15c, B15d, B15e, B16, B17 and B18 (the B15e/B16 leg checks use products carrying the flag-OFF evidence `shopping_count` 3, where None and 0 give different legs).
- **The R31 pins run the REAL `_get_price`** inside the real `_fetch_product_data`, to its Tier-1 pool write (network seams stubbed; the extractor call that follows the write raises a sentinel so the run ends right after it). Search stubs use PRODUCTION shapes (`shopping_region: 'us_fallback'`, never the invented `'us'`), and the failure rows run the REAL `serper_service.search_product_prices` with only its seams patched:
  - a non-empty return with zero identity matches -> 0 -> weak (flag OFF strong on the same evidence);
  - a non-empty return with three matches -> 3;
  - a real empty `us_fallback` return -> None -> the flag-OFF leg (B15e, rewritten from the round-5 "empty return -> 0");
  - a failed search: the HTTP layer raising, or a 503, inside the REAL `_do_serper_shopping` -> the empty `us_fallback` dict -> None -> the flag-OFF leg (`test_b16_non_timeout_serper_exception_stashes_unknown`, REWRITTEN: the round-5 version raised out of a stub, which production cannot do);
  - the `error` no-call shape: the stub `{'shopping': [], 'error': 'no_key'}` and the REAL function with no key or the budget out, no call made -> None;
  - the supplements branch -> None; the clamp timeout -> None; a cache hit -> None (B15 stands);
  - R31b: ('Tom Ford', 'Tom Ford Oud Wood', '100ml'), whose `_get_price` key 'Tom Ford Tom Ford Oud Wood 100ml' differs from the display name: empty `us_fallback` -> None, supplements -> None, three matches -> 3 (B18);
  - flag OFF: the same pool writes, no bookkeeping, no stash.
- **Flag-OFF equality gate:** 167 records (lane1 18, Part A 108, Part B 20, Part C 21), run base 15e1fb89 (detached scratch worktree, unit files copied in for their fixtures) -> head -> base2, with all W4-7 flags unset. Every record is equal base == head == base2, 0 mismatches.
  - Overall digest `c8e532de9dd69026cfcac1f6564124cc695d56278ece0244a903648fe12fab78` on base, head and base2; the head digest equals the base.
  - Method: the probe copy pops the C test helper's `listing_count` capture key. The red's probe run verbatim gives 0 mismatches and `0873b4765e221919bba48c30bda22f564886d3614e8f1b9d7d8078f1fe478733` on all three.
  - The gate's records mock `_get_price`; the new `_get_price` lines are all inside `if confidence_single_computation_enabled():`, and their flag-OFF inertness is pinned separately (B16 flag-OFF, 3 nodes; mutants R28g/R28h).
- **Corpus harness:** `scripts/verify_flag_byte_identity.py` never enters these modules, so it is blind to this unit.
- **CI-order set** (35 files, alphabetical, one process per state, CI deselects):
  - Unset, B and C: 1304 passed, `[netguard] blocked 67 attempt(s) from 25 node(s)`. That is 978 base nodes + 326 unit nodes.
  - Netguard ratchet OK (25 attempting nodes vs baseline 205) in all six states.
  - A and ALL: 4 failed. A-without-renorm: 1 failed. These are the pins adjudicated at base: the two `test_fact_checking.py` CitationRubricV2 pins (flag-OFF-only by construction, A12), `test_scoring_rubric_truth.py::test_flags_off_record_digests` (its generator flips renorm on internally; the A-without-renorm failure), and the pre-existing renorm failure `test_scoring_service.py::TestEdgeCases::test_all_missing_data`.
- **Comm gate** (HEAD, 253 files in 11 chunks of at most 25, conftest guard): 8,417 passed, 4 failed, 582 blocked attempts. The failed set EQUALS the accepted four `.pre_impl_failures.txt` nodes (2 test_page_scraping, 2 test_personalization_bundle_c), so `comm -13` is empty by construction. The 13 files that grep `SmartCompareApp` are all inside the set.
- **Diff gates:** `git diff --stat 15e1fb89 -- app/services/price_service.py app/services/fact_check_service.py app/services/rating_service.py` is EMPTY (R14/R15). `git diff --stat -- app/` shows only the three files (245 insertions, 17 deletions, no whole-file CRLF diff).
- ruff E9,F63,F7,F82 is clean and py_compile passes on all six files.

### Activation (one canary per step, never batch)
- **Part B** any time, recommended FIRST.
- **#107** -> wait for the cache roll -> **Part C** (immediately before #106) -> **#106** (+ `ENABLE_FACTCHECK_HONEST_ABSENCE` in its own window right after) -> **#109**.
- **Part A LAST**, in this order: W4-6b's order-symmetric tie-break -> `ENABLE_MISSING_DIM_RENORM` -> Part A.

### Canaries
- **Part A:** the count of pairs whose reliability dimension was excluded (the dimension in `missing_data` / `metadata.missing_dim_cells`).
- **Part B:**
  - `scoring_v2.confidence_legs == overview.confidence.legs` on 100% of rows.
  - The confidence-leg distribution shift (Medium appears), read PER PRICE SOURCE (a shopping-search product, a supplements product, a price-cache hit) AND PER POOL STATE (a non-empty pool returned this request / an empty pool). Only products with a non-empty pool carry a count; every empty pool keeps today's evidence, so a shift is only expected in the non-empty-pool bucket. An outage (Serper 403/429/5xx, no key, budget out) empties the pool and therefore reads as today's evidence, not as a weak shift. `metadata.cache_hit` is True when ANY product's price is `_cached`, so the "hit" bucket also holds mixed pairs, and on a mixed pair the leg CAN move: the miss product's real count counts (measured, pinned by B15d). Some MISSES carry an unknown count too: a Tier-1.5 short-circuit such as the BH-adapter direct hit returns before any shopping-cache write. On the all-products-cached subset the scoring_v2 price leg equals the flag-OFF leg except where the R12 cap fires (a pending shown price), so read that subset as the control.
  - `confidence_details.price.sources_count == 0` on price-less rating rows.
  - The W4-1 / W4-2 canary line counts must NOT move when Part B flips (R19).
- **Part C:** the shopping-cache hit rate on variant / brand-repeating products (the share of `price_verified True` with deviation None falls).

All three need OpenAI credit for a live compare.

### Stated limits
- **R25 / R31a, the unknown count:** the listing count is unknown whenever no non-empty shopping pool was returned this request: a real empty search, a failed or timed-out search, no key or budget, the supplements path, a cache hit, a partial build. The leg then falls back to today's evidence. A truthful count on cache hits and on failed searches needs the count persisted beside the cached price and a search-status signal from price_service: follow-ups **W4-7f** and **W4-7g**.
  - Measured on a mixed pair (product 0 a cached converted price with an unknown count, product 1 a miss with 3 matched rows): flag OFF scoring_v2 reads weak, Part B ON reads strong, with `metadata.cache_hit` True.
  - On that pair, the price DETAIL `confidence_details.price.sources_count` / `overview.confidence.price.source_count` is product 0's count (`_product_shopping_count(product0)` in `compute_confidence`, pre-existing scoping). Beside a strong pill it reads 0, so the "Checked across N retail sources." line is absent. This is not a regression (flag-OFF scoring_v2 already reads 0) and is filed with W4-7f.
  - The bookkeeping is written by the two writers `_get_price` has today (the Tier-1 write records the non-empty test, the supplements `[]` write records uncaptured). A future writer of `_shopping_items_cache` must call `_mark_shopping_pool_captured(...)` too, or its pool will read as captured (an unmarked empty pool would stash 0).
  - The flag is read per call. If Part B flips ON between a product's Tier-1 write and its stash in the same request, the write carries no mark and an empty pool would stash 0 for that one product. The window is one request at the flip instant.
- **R11:** under renorm, a one-sided missing dimension already ships `dimension_winners[dim] = {winner: <the only side with data>, margin: None}`, and Part A inherits it. Follow-up **W4-7d**.
- **R13:** the count is per-row identity acceptance. The extractor's pool-level tier filter (drop retailer_score < 0.5 when a tier-1/2 candidate exists) is NOT replayed, so the count may EXCEED the extractor's final pool.
  - Fragrance harness: 3 identity-matched rows + a phone case + a 30 ml bottle + a price-less iHerb row -> 3. Only rejected rows -> 0.
  - The supplements path carries no count (unknown), so its end-to-end count question is moot under Part B.
- **R22(c), measured:** the per-row acceptance DEPENDS on category and on the ask currency. Both flips are pinned through the real count.
  - Category: 'Adidas Superstar White Sneakers' counts under None / fashion / other and not under fragrances / electronics / supplements.
  - Currency: with `ENABLE_SHOPPING_STRICT_CURRENCY` ON, an AED-glyph row counts under the uae ask only. With strict OFF it also counts under BHD (the pre-M13-09 mislabel).
- **R12:** the spec's 'PDP+google strong at every count' is superseded: any missing shown price caps the leg at weak. Ahmed may loosen this later; record it in DECISIONS.
- **R12 / R30a, a non-dict price:** handled by the chokepoint (normalised to pending, then capped) when it is healthy; with the chokepoint degraded the builder raises on a non-dict raw price at `p.get("price", {}).get("source_method")`, at base too and in both flag states. A pre-existing builder limit, not introduced or changed by this unit.
- **R5:** a partial (early buffer) never reaches the stash. Its count is unknown, so it gets the flag-OFF evidence.
- **Client:** 'Checked across 1 retail sources.' has no plural form. This is a mobile-lane follow-up.
- **Part A:** until #107's cache roll, Part A removes the reliability dimension from essentially every comparison, hence LAST. The crown can fall to input order at 0.0 margin (W4-6b).
- **Part C:** the vision+variant shape was checked on the key string only, not end to end.

### Follow-ups
- **W4-7d (R11):** a renorm-excluded dimension ships N/A, not a winner. This is a display-contract change that belongs with W4-6b once #101 is answered.
- **W4-7e (R6):** the price-path `_price_fallback_on_miss` / `_parked_price` / `_price_candidates` key drift. A parked price is recovered for one shape and lost for three. It needs its own flagged unit; `_shopping_cache_key` is the shared fix.
- **W4-7f (R25/R31c):** persist the identity-matched listing count beside the cached price, so a cache hit carries a truthful count. Include the product-0 scoping of `sources_count` on mixed pairs.
- **W4-7g (R31c):** a search-status signal from price_service / serper_service (searched-and-empty vs failed / timed out / no key / budget out), so a real empty search can carry a truthful 0.
- The client plural key.
- The pre-existing renorm-ON failure of `test_scoring_service.py::test_all_missing_data`.
- The pre-existing builder crash on a non-dict raw price when the chokepoint is degraded (response_builder `price_methods`).

### CLAUDE.md corrections for the docs PR
- Add the three flag rows above to Feature Flags.
  - Part A's row carries the renorm coupling, the activation order and the one-sided None cost.
  - Part B's row carries the R31a unknown-count rule (a count only where a non-empty shopping pool was returned; every empty pool, an outage included, keeps today's evidence), W4-7f / W4-7g, the R12 cap, the R16 pop, the R19 log-silent replay, the R20 WARNING and the per-price-source + per-pool-state canary with its mixed-pair caveat.
  - Part C's row carries the four readers, the R24 wrapper and the R15 kwarg.
- Under ENABLE_MISSING_DIM_RENORM, note that with Part A live, `test_fact_checking.py`'s two rubric pins and the rubric-truth digest test are flag-OFF-only by construction.
- The spec's 'two readers' becomes four readers.
- The comm set is 253 files at 15e1fb89.

Issues: PO-FACTCHECK-CONFIDENCE-01/-02/-03/-04/-06/-10, #106, #107, #108, #109, #101 (W4-6b).

### Orchestrator addendum (Fable, ship time 2026-09-27)
- **Pipeline (six fix rounds, seven adversaries):** red (123 reds / 119 pins / 20 kills at `15e1fb89`) -> Fable red-gate rulings R11-R18 -> green -> adversary r0 DEFECTIVE (the Part B listing replay emitted the W4-1 / W4-2 canary log lines) -> Fable R19-R23 (a ContextVar-gated logging filter installed lazily on the price-path loggers; the except branch falls back to the exact flag-OFF path; a never-raising key wrapper) -> fix r1 -> adversary r1 DEFECTIVE only on the rulings it had not seen -> Fable R24-R27 (the wrapper form ratified; **the cache-hit count is UNKNOWN, not 0** - with Part B on, every warm compare would have read a weak price pill) -> fix r2 -> adversary r2 SOUND -> fix r3 -> adversary r3 (4 minors) -> fix r4 -> adversary r4 SOUND -> Fable R28-R30 (a synthetic empty pool is not a captured pool) -> fix r5 -> adversary r5 DEFECTIVE (price_service never raises on a failed search, so the return shape cannot tell a failed search from a real empty one) -> Fable R31 (**captured = a NON-EMPTY pool returned this request**; every empty pool falls back to today's confidence leg) -> fix r6 -> adversary r6 SOUND (2 pin gaps). Every adversary left the worktree byte-identical to the fixer's reported shas. Rulings: `.qa-s68/RULINGS_W4_7*.md` (archived in the session state folder).
- **Adversary r6's pin gaps closed by the orchestrator (test rows only, no app change):** `tests/test_w4_7_confidence_single_computation.py::test_b16_real_returned_pool_counts_identity_matches` gained `one_row_match` (a ONE-row non-empty pool is captured; count 1) and `one_unpriced_row` (a pool whose only row carries no price is captured; count 0 -> weak). The R31a boundary mutants now redden: A7-1 (`len > 1`) 2 failed, A7-5 (`any(priced)`) 1 failed; every restore sha-verified. The three unit files: 328 passed in each of the six states, `[netguard] blocked 0`.
- **pr_text correction (adversary r6):** `_get_price` writes `_shopping_items_cache` at THREE sites today, not two - the Tier-1 supplements `[]` (marked not-captured), the Tier-1 search return (marked by the non-empty test), and the Tier-2 iHerb one-row rating overwrite inside `if is_supplement:` (not marked; it always follows the supplements mark in the same call, so the key stays unknown). The stated-limit sentence above that says "the two writers" should be read as "the two Tier-1 writers"; the Part B design list and residual-risk item 3 describe the third.
- **Post-rebase ship checks** (onto main; W4-11 landed in `structured_comparison_service.py` in different functions): the three unit files and the 35-file CI-order set in ONE process per state (six states; the four adjudicated flag-ON reds and the one A-without-renorm red stay as adjudicated), the netguard ratchet, the R14 diff gate (price_service / fact_check_service / rating_service untouched), ruff E9,F63,F7,F82 and py_compile - results in the PR's first comment if they differ from the fixer's numbers above.
- **Flags on main after this merge (default OFF, read per call):** `ENABLE_RELIABILITY_UNCHECKED_ABSENCE` (coupled: False while `ENABLE_MISSING_DIM_RENORM` is OFF), `ENABLE_CONFIDENCE_SINGLE_COMPUTATION`, `ENABLE_FACTCHECK_SHOPPING_KEY`. Nothing is flipped; Railway and Supabase untouched. Activation order: W4-6b's order-symmetric tie-break -> renorm -> A; B alone with its canary read per price source and per pool state; C after B. Follow-ups W4-7d (with W4-6b, issue #219), W4-7e, W4-7f, W4-7g.

- **Post-rebase ship checks, measured (main `8a1e0d55`, commit `0fb6295d`):** the three unit files 328 passed in each of the six states; the 35-file CI-order set in ONE process per state: unset / B / C 1306 passed, A and ALL 4 failed / 1302 passed (the four adjudicated flag-ON reds: the two `test_fact_checking` CitationRubricV2 pins, the `test_scoring_rubric_truth` digests and `test_scoring_service::test_all_missing_data`, all flag-OFF-only by construction and pre-existing under renorm), A-without-renorm 1 failed / 1305 passed (`test_flags_off_record_digests`, adjudicated); the netguard ratchet OK (25 attempting nodes, baseline 205) in all six states; ruff / py_compile clean; the R14 diff gate EMPTY (price_service / fact_check_service / rating_service untouched); `git diff --stat -- app/` = the three files (245+/17-).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
