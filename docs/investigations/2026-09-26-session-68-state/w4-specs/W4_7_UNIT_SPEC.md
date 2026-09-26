# W4-7 — fact-check honesty: the reliability dimension stops scoring what nobody checked, the pills read ONE computation of the price the user sees, and the fact-check reads the shopping rows `_get_price` actually wrote

Findings `PO-FACTCHECK-CONFIDENCE-01` (P1), `-02` (P1), activation of `-03` (P1, #109) and
`-04` (P1, #106); folds in `-06` (P2, the fabricated listing count) because `-02` cannot be
fixed without it (measured below), and adds ONE defect the review did not find (Part C, the
shopping-cache key drift, measured end to end). Base **`61585c58`** (= origin/main, confirmed
`git rev-parse HEAD` = `61585c581e9deb78213f030260a765080f2e1dff`). Worktree `sc-w4-specs`
(read-only; this file is the only write). Every line anchor below is at `61585c58`; the
review's anchors are from `76ace90` and drifted (table at the end). Every number below was
MEASURED in this run by the real functions through pytest probes under `tests/conftest.py` +
the `qaren_netguard` plugin (`[netguard] blocked 0 network attempt(s)` on every probe run),
pinned venv (fastapi 0.141.1 / pytest 9.1.1), no `LIVE`. Probe sources and raw JSON:
`<session scratchpad>/w47/test_w47_probe{,2,3,4,5,6,7}.py` → `w47_out*.json` (run shape:
`PYTHONPATH=<netguard>;<worktree> python -m pytest -p qaren_netguard -p tests.conftest
--rootdir <worktree> -c pyproject.toml <probe>`, so conftest's credential neutralisation runs
before any `app.*` import).

Three NEW flags, all default OFF, all read PER CALL: `ENABLE_RELIABILITY_UNCHECKED_ABSENCE`
(Part A), `ENABLE_CONFIDENCE_SINGLE_COMPUTATION` (Part B), `ENABLE_FACTCHECK_SHOPPING_KEY`
(Part C). No existing flag changes meaning. The flag decision (and why none of the three rides
`ENABLE_CONFIDENCE_FACTCHECK_WIRING`) is its own section; Fable may overrule it (Open questions).

---

## The defect, measured

### Part A — `PO-FACTCHECK-CONFIDENCE-01`: reliability is a per-product constant moved only by side signals

`ScoringService._score_reliability(fact_check)` (`app/services/scoring_service.py:1957`):
buckets `:1967-1971`, `if total == 0: return None` `:1973-1974` (the B0-A v2 fix covered
ONLY the empty case), formula `(v*1.0 + l*0.7 + u*0.3 + f*0.0)/total` `:1976`,
`+0.1 if price_verified` (truthy) `:1978-1979`, `+0.05 / -0.1` on
`review_sentiment_consistent is True / is False` `:1981-1984`. Consumed by
`_compute_raw_scores` `:1717-1725` (None → `_reliability_missing`), normalized by
`_normalize_direct` `:2387-2392` (`None → MISSING_SCORE = 50` `:297`, else `raw*100`), and the
B0-A v2.1 tie collapse `:2125-2132` turns two EQUAL non-missing reliability scores into
MISSING for both. The reliability signal is exactly one named dimension in each of the 9
categories (`_DIMENSION_SIGNAL_MAP` `:2024-2070`).

Measured, `_score_reliability`, flag `ENABLE_CONFIDENCE_FACTCHECK_WIRING` unset AND `=true`
(identical — #109 does not touch this function):

| fact_check (v/l/u/f, price_verified, sentiment) | value |
|---|---|
| 0/0/1, 0/0/3, 0/0/8, 0/0/11, 0/0/50 (pv False) | **0.3** every size |
| 0/0/8, pv **True** | **0.4** |
| 0/0/8, pv None | 0.3 |
| 0/0/8, sentiment True / False | 0.35 / 0.19999999999999998 |
| 0/0/8, pv True + sentiment True | 0.45 |
| 1/0/7 · 0/1/7 · flagged 1 + 7 unv · flagged 1 only · 2/0/6 | 0.3875 · 0.35 · 0.2625 · 0.0 · 0.475 |
| `{}` · all zeros | None · None |

So on the all-unverified shape (the warm-cache shape: `verify_spec_citations` on cached specs
grades every field `unverified`) the score carries NO information about the specs; only
`price_verified` and the sentiment verdict move it. `price_verified` is fabricated `True`
whenever `verify_price` sees zero rows for a non-estimated price (measured `verify_price(
{25.5 BHD}, []) → {price_verified: True, deviation_pct: None, source_count: 0}`,
`fact_check_service.py:399-407` via `_empty_evidence_verdict` `:56-68`), and Part C shows the
fact-check sees zero rows for every brand-repeating product name.

**It decides the winner, in all 9 categories.** Two products identical except name/brand
(150 BHD `local_bhd`, bolo.bh PDP urls, rating 4.5 / 1000 reviews, the same 5 electronics spec
fields), both fact_checks `0/0/8/0`, ONLY `price_verified` differs (A True, B False),
`compute_scores` run in both input orders:

| category | reliability dim | dim A / B | winner, order AB | winner, order BA | margin |
|---|---|---|---|---|---|
| electronics | build_quality_score | 40.0 / 30.0 | A | A | 1.5 |
| other | build_score | 40.0 / 30.0 | A | A | 1.4 |
| supplements | safety_score | 40.0 / 30.0 | A | A | 2.5 |
| fragrances | versatility_score | 40.0 / 30.0 | A | A | 1.5 |
| fashion | durability_score | 40.0 / 30.0 | A | A | 1.5 |
| grocery | ingredient_score | 40.0 / 30.0 | A | A | 2.0 |
| makeup | skin_compat_score | 40.0 / 30.0 | A | A | 2.0 |
| skincare | evidence_score | 40.0 / 30.0 | A | A | 2.0 |
| haircare | ingredient_score | 40.0 / 30.0 | A | A | 1.5 |

The dim is NOT in `missing_data` at HEAD. With both fact_checks absent instead (the
Part-A-ON shape) every category reads 50 / 50, the dim IS in `missing_data`, and
`win_margin == 0.0` in both orders (the crown then falls to input order — see Honest limits).

**The same class is ALREADY live one-sidedly** (electronics, 150 BHD both, 5 specs):
a product whose fact_check has zero buckets (no spec fields to check) scores the MISSING 50
against a measured side:

| pair (A vs B) | build_quality A / B | winner_index | win_margin | overall A / B |
|---|---|---|---|---|
| zero buckets vs 0/0/8 | 50 / 30.0 | **0 (A, no evidence)** | 3.0 | 67.0 / 64.0 |
| zero buckets vs 2/0/6 | 50 / 47.5 | **0 (A, no evidence)** | 0.4 | 67.0 / 66.6 |
| zero buckets vs 8/0/0 | 50 / 100 | 1 | 7.5 | 67.0 / 74.5 |
| no `fact_check` key vs 0/0/8 | 50 / 30.0 | 0 | 3.0 | 67.0 / 64.0 |

(`dimension_winners[build_quality_score]` names "Beta Two" with `margin None` in all four —
it disagrees with its own numbers.)

**The review's fix, as written, spreads that inversion.** Prototype (monkeypatched
`_score_reliability` → None when `verified+likely+flagged == 0`), electronics pair from probe 1
(300 / 280 BHD, ratings 4.4, 900 / 950 reviews, 8 phone specs); `other`, `supplements`,
`fragrances` gave the same dim values:

| pair | HEAD dim A / B, dim winner | review fix (one-sided None) | pair-symmetric absence (this spec) |
|---|---|---|---|
| 0/0/8 pv T vs 0/0/8 pv F | 40.0 / 30.0, A by 10.0 | 50 / 50, N/A | 50 / 50, N/A |
| 2/0/6 vs 0/0/8 | 47.5 / 30.0, A by 17.5 | **47.5 / 50** (unchecked beats verified) | 50 / 50, N/A |
| flagged 1 + 7 unv vs 0/0/8 | 26.2 / 30.0, B by 3.8 | **26.2 / 50, dim winner = A, the FLAGGED product** | 50 / 50, N/A |
| sentiment T vs F (both 0/0/8) | 35.0 / 20.0, A by 15.0 | 50 / 50, N/A | 50 / 50, N/A |

### Part B — `PO-FACTCHECK-CONFIDENCE-02` (+ `-06`): the pills come from a second, worse-informed computation

Two computations exist. (1) The orchestrator: `ScoringService.compute_confidence(product_data,
shopping_count=len(self._shopping_items_cache), cached=from_cache)` at
`structured_comparison_service.py:3400-3404` (partial), `:4010-4012` (sync), `:4665-4667`
(stream; also shipped in the SSE `scores` event `:4668-4674`); the shim `scoring_service.py:
2660-2678` injects that count into product 0 only; the result is passed to
`build_comparison_response(confidence=...)` (`:3422` / `:4039` / `:4835`) and shipped verbatim
as `overview.confidence` (`response_builder.py:1800`). (2) The builder: `_build_scoring_v2`
(`response_builder.py:1119`) calls `_confidence_legs_and_details(product_data)` `:1190` →
module `compute_confidence(product_data)` `:1077` with NO count and `cached=False`; that is
`scoring_v2.confidence_legs` / `confidence_details` `:1229-1230`, **the only surface the phones
read** (`SmartCompareApp/src/components/results/ResultsContent.tsx:471/:482/:490`; zero client
readers of `overview.confidence` or of the SSE `scores` payload — grep; the client is identical
between the phones' `ab9442ae` and `61585c58`: `git diff --stat ab9442ae 61585c58 --
SmartCompareApp` is empty). Between the two, the builder's price-pending chokepoint
(`response_builder.py:1470-1597`) replaces every non-showable price with
`make_pending_price(...)` IN PLACE (`:1571` / `:1590`) — so computation (2) sees the price the
user sees, computation (1) the pre-pend price (with `ENABLE_PRESCORING_SHOWABLE_GUARD` OFF).

`len(self._shopping_items_cache)` is the number of PRODUCT keys (≤ 2), not listings (`-06`):
supplements write `[]` unconditionally (`:6805-6808`) and still count. Recorded captures on
disk agree: **15 of 15** `overview.confidence.price.source_count` values in
`tests/fixtures/**` are `2` (9 `lane1/*_response.json` + 6 `comparison_baseline_d2*.json`),
including `now_vs_solgar_response.json` (supplements, `converted_usd` × 2) whose recorded
`overview.confidence.legs.price` is `acceptable` while the builder, fed the same products and
the recorded `metadata.fact_check`, returns `weak` / `sources_count 0` / `freshness live`.

Measured through the REAL `build_comparison_response` (exact gate ON), electronics pair
(Sony / Bose, 100 / 200 BHD, fact_check 0/0/8), orchestrator shim `shopping_count=2,
cached=True` (= every live two-product compare), `from_cache=True`:

| shape (both products unless stated) | shown price | `overview.confidence` price leg (source_count, freshness) | `scoring_v2` price leg (sources_count, freshness) | legs equal |
|---|---|---|---|---|
| bolo.bh PDP, `converted_usd` | shown | **acceptable** (2, cached) | **weak** (0, live) | NO — the review's RED |
| bolo.bh PDP, `estimated` | pended | acceptable (2, cached) | weak (0, live) | NO |
| google search link, `local_bhd` | **pended ×2** | **strong** (2, cached) | weak (0, live) | NO |
| bolo.bh PDP, `local_bhd` | shown | strong (2, cached) | strong (0, live) | legs yes, details no |
| PDP + google link, `local_bhd` | shown + pended | strong (2, cached) | strong (0, live) | legs yes, details no |

Sweep through `ScoringService().compute_confidence(shim)` vs the builder, 5 source methods ×
`shopping_count ∈ {0,1,2,3}` × #109 OFF/ON: the builder's price leg is `strong` or `weak` only —
**`acceptable` ("Medium") is unreachable on the pill**; overview reads `acceptable` at count 2
and `strong` at count 3 for non-trust methods; #109 does not change the PRICE leg of either
surface on these inputs (`price_deviation_pct None` → no demotion; its specs-leg effect is the
`-03` row below). B10's expected `{price acceptable, specs weak}` is the measured #109-ON
`compute_confidence` output on the warm shape, not a builder run. Client copy (`en.json:180/:183/:184`): `sources_count > 0` renders "Checked across
{{n}} retail sources."; `freshness live` renders "Pricing checked just now." on every compare
today, cached or not. Freshness truth: `from_cache = not nocache` (`:4009`, `:4664`,
ctx `:3660/:4374`) means "cache allowed", not "served from cache"; the builder already owns the
real signal — `_compute_cache_observability` (`response_builder.py:38-69`, `metadata.cache_hit`,
spread at `:1941`): measured with a showable price carrying `_cached: True` →
`metadata.cache_hit True` while `metadata.cached False` and the pill says `live`.

**Why the review's first-choice fix is wrong** (thread the orchestrator's dict into
`_build_scoring_v2`): on the `google link × 2` row it turns the pill from `weak` to `strong`
beside two "price pending" rows (measured: the orchestrator dict's price leg is `strong`), and on
every supplements compare it publishes "Checked across 2 retail sources." where zero were
checked (the recorded `source_count 2`). Threading makes the persisted and displayed surfaces
agree on the WRONG value.

### Part C (new) — the fact-check reads a shopping-cache key `_get_price` never writes

`_get_price` writes `self._shopping_items_cache[full_name]` (`:6808` / `:6840`) with
`full_name` assembled at `:6169-6172` (`f"{brand} {name}"` when the variant is already in the
name, else `f"{brand} {name} {variant or ''}"`, stripped). `_fetch_product_data` reads the
cache with ITS `full_name` from `_product_display_identity` (`:1247-1263`, via
`dedup_brand_name`, assigned `:5113`) at TWO sites: the spec cross-validation `:5478`
(`cross_validate_specs_with_shopping`) and the price cross-check `:5718-5719`
(`verify_price`). Measured key agreement through the real `_product_display_identity` vs a
verbatim replica of `:6169-6172`: **5 of 10 shapes disagree** — every brand-repeating name
(`Apple / Apple iPhone 15`, `Tom Ford / Tom Ford Oud Wood / 100ml`,
`NOW Foods / NOW Foods Vitamin D3 5000 IU`, vision `Sony / Sony WH-1000XM5`) and a variant
already in the name (`Samsung / Galaxy S24 Ultra / Ultra` → result `…Ultra Ultra`).

End to end through the real `_fetch_product_data` (tiers mocked as in
`tests/test_comparison_response_image_url.py::TestOrchestratorWiring`, cache seeded under the
`_get_price` key with 3 × `"BHD 999.000"`, price 350 BHD `local_bhd`):

| brand / name / variant | keys equal | flags OFF | `ENABLE_FACTCHECK_CURRENCY_NORMALIZATION` | `ENABLE_FACTCHECK_HONEST_ABSENCE` |
|---|---|---|---|---|
| Tom Ford / Oud Wood / 100ml | yes | False, 65.0 | False, 65.0 | False, 65.0 |
| Apple / iPhone 15 / – | yes | False, 65.0 | False, 65.0 | False, 65.0 |
| Tom Ford / Tom Ford Oud Wood / 100ml | **no** | **True, None** | **True, None** | None, None |
| Samsung / Galaxy S24 Ultra / Ultra | **no** | **True, None** | **True, None** | None, None |
| Apple / Apple iPhone 15 / – | **no** | **True, None** | **True, None** | None, None |

(`price_verified`, `price_deviation_pct`.) Three contradicting rows are ignored and the price is
certified; **#106 is inert on these shapes** — which also makes the fabricated `True` feed Part
A's +0.1 and blinds #109's price demotion there.

### Claims `-03` / `-04` (activation), re-measured

* `-03` warm shape (fact_check 0/0/8, `price_verified False`, deviation 89.8, both products):
  `local_bhd` → #109 OFF `{price strong, reviews strong, specs strong}`, overall **high**,
  specs `{verified_pct 0, citation_count 8}`; #109 ON `{price acceptable, reviews strong,
  specs weak}`, overall **low**, `citation_count 0`. `converted_usd` → OFF `{weak, strong,
  strong}` medium; ON `{weak, strong, weak}` low. **HOLDS.**
* `-04` `verify_price`: flags OFF, 250.0 "BHD" vs 3 × `"AED 250.00"` → `True, 0.0`; the correct
  25.5 BHD → `False, 89.8`; #106 ON → `False, 876.6` / `True, 0.4`; real price, zero rows →
  `True` (OFF) / `None` (HONEST_ABSENCE ON); estimate, zero rows → `False` in every state;
  `BHD 25.500` rows vs 25.5 → `True, 0.0` in every state. **HOLDS** (plus Part C: incomplete on
  5-of-10 name shapes).
* Readers: `confidence_factcheck_wiring_enabled` `:970` (reader `:991-993`, truth table
  measured: `true/TRUE/" true "/1/yes/on` → True, `false/""` → False, default False),
  `factcheck_currency_normalization_enabled` `fact_check_service.py:13`,
  `factcheck_honest_absence_enabled` `:30`, `spec_confidence_cache_enabled` `scs.py:371` — all
  per call, all default False here.

---

## What already exists — reuse it, do not reinvent it

* **Flag idiom** — `confidence_factcheck_wiring_enabled()` (`scoring_service.py:970-993`):
  `os.getenv(NAME, "").strip().lower() in ("true", "1", "yes", "on")`, per call, never at
  import. Copy it verbatim for the three new readers; put all three in `scoring_service.py`
  next to it (the builder and the orchestrator already import from `scoring_service`).
* **Absence plumbing** — `_score_reliability → None` → `_compute_raw_scores` sets
  `_reliability_missing` (`:1721-1722`) → `_normalize_direct` returns `MISSING_SCORE` → A.4.9
  silent omission drops the row from `scoring_v2.dimensions` (measured: the electronics rows go
  `price, reviews, value, build_quality, feature, futureproof` → `price, reviews, value,
  feature, futureproof`). The v2.1 tie collapse `:2125-2132` is the exact pattern Part A's
  pair rule copies (set every side to `MISSING_SCORE`, set `_reliability_missing` on every
  `raw_scores` entry).
* **Pill contract** — module `compute_confidence(products, cached)` (`:1057`): per-product
  `shopping_count` read by `_product_shopping_count` (`:712`), price leg `:1093-1105`
  (incl. #109's demotion), legacy detail dicts `:1131-1160` (`source_count` = product 0's
  count, `freshness` from `cached`). Part B changes its INPUTS, never its body.
* **The shown price** — the chokepoint `response_builder.py:1470-1597` already pends in place;
  Part B computes AFTER it, so `ENABLE_PRESCORING_SHOWABLE_GUARD` (W4-3) state does not matter.
* **Real cache hit** — `_compute_cache_observability(product_data)["cache_hit"]`
  (`response_builder.py:38`), already computed for `metadata.cache_hit`.
* **The `_get_price` key** — `:6169-6172`; Part C factors it into ONE module helper that
  `_get_price` also calls (byte-identical string), never a second copy.
* **Harnesses** — the `_fetch_product_data` mock harness of
  `tests/test_comparison_response_image_url.py:84-135`; the Sony/Bose showable/pended shapes of
  `tests/test_prescoring_showable_guard.py:60-160` (`GOOG0/GOOG1/PDP0/PDP1/E0/E1`, `_mk`).

---

## The design

### Flag decision (the row asked: ride `ENABLE_CONFIDENCE_FACTCHECK_WIRING` or not?)

**None of the three rides #109.** Reasons, each measured or source-anchored:

1. **Part A is a SCORE fork, #109 is a PILL fork.** Part A moves `winner_index`,
   `win_margin`, `dimension_winners`, `missing_data` and removes a dimension row (tables above);
   #109 moves only `confidence.legs`. Riding one flag puts two surfaces in one canary window
   (a winner flip and a pill change cannot be attributed) and one rollback (turning off a bad
   winner change would also turn off the pill honesty). CLAUDE.md gives every result fork its
   own window (e.g. `ENABLE_VISIBLE_TEXT_CURRENCY`, `ENABLE_REGION_CURRENCY_GUARD`).
   Part A shares #109's precondition (#107's cache roll), not its surface — it is ordered AFTER
   #109 in the runbook instead.
2. **Part B does not share #109's precondition at all.** It changes which computation the pill
   reads, not what the computation reads; it is correct with #107/#106/#109 in any state and is
   the P1 that is live today. Riding #109 would chain a P1 fix behind a month-long cache roll.
   It still needs a flag: it changes the phones' pill (weak → acceptable at ≥ 2 real listings),
   the sheet copy ("Checked across N…", "Pricing from a recent check."), and the persisted
   `overview.confidence` on every row — a user-visible fork (CLAUDE.md standing rule). The
   review's "unflagged" is overruled by measurement (Part B table, supplements row).
3. **Part C is an evidence-read fork, not a currency one.** It changes `fact_check.
   price_verified` / `price_deviation_pct` and the spec shopping-flags on brand-repeating names
   with #106 OFF as well (the key, not the currency, is the defect). Riding #106 would make a
   #106 canary unable to tell "right currency" from "right rows". Ordered immediately before
   #106.

### Part A — `ENABLE_RELIABILITY_UNCHECKED_ABSENCE` (default OFF; reader `reliability_unchecked_absence_enabled()`)

Flag OFF: `_score_reliability` and `_normalize_scores` execute their exact HEAD bodies.
Flag ON, two changes:

1. `_score_reliability` (`:1957`): after `total` (`:1971`) and the `total == 0` return, add
   `if reliability_unchecked_absence_enabled() and verified + likely + flagged == 0: return None`
   — an all-unverified fact-check is ABSENCE (nothing was checkable), exactly like the empty
   case. `price_verified` / sentiment modifiers are never reached for it. Checked shapes
   (any verified / likely / flagged) are untouched: `0.3875 / 0.35 / 0.2625 / 0.0 / 0.475`.
2. `_normalize_scores` (`:2072`), immediately after `reliability_scores` is built (`:2112`)
   and BEFORE the v2.1 collapse: `if reliability_unchecked_absence_enabled() and
   len(reliability_scores) >= 2 and any(rs.get("reliability_raw") is None for rs in
   raw_scores) and any(rs.get("reliability_raw") is not None for rs in raw_scores):` set every
   entry to `MISSING_SCORE` and `rs["_reliability_missing"] = True` on every `raw_scores`
   entry, and log ONE INFO line `[RELIABILITY] pair-symmetric absence (one side unchecked)`.
   **Pair-symmetric**: a comparative dimension with one side unmeasured is not comparable. This
   is what stops the review's one-sided version from crowning the flagged product
   (Part A table) and it also closes the already-live zero-bucket inversion (one-sided table)
   under the same flag. It fires only when sides DIFFER in presence; two present sides and two
   absent sides behave as today.

What Part A must NOT touch: `_score_specs`, `_normalize_direct`, `MISSING_SCORE`, the v2.1
collapses, `build_fact_check`, `verify_spec_citations`, `compute_confidence`, the
`_DIMENSION_SIGNAL_MAP`.

### Part B — `ENABLE_CONFIDENCE_SINGLE_COMPUTATION` (default OFF; reader `confidence_single_computation_enabled()`)

ONE computation, in the builder, AFTER the price-pending chokepoint, with real per-product
listing counts and the real cache hit; emitted verbatim on BOTH surfaces.

1. **Orchestrator stash** (`_fetch_product_data`, next to the fact-check pass `:5718`): under
   the flag, `result["_shopping_listing_count"] = len(self._shopping_items_cache.get(
   _shopping_cache_key(brand, name, variant)) or [])` (helper from Part C; `brand`, `name`,
   `variant` are the function's own locals `:5101-5103`). Flag OFF: the key is never written.
   Supplements (cache `[]`) → 0.
2. **Builder** (`build_comparison_response`, after the chokepoint `:1597`, before overview
   assembly): under the flag,
   `conf = compute_confidence([{**p, "shopping_count": int(p.get("_shopping_listing_count") or 0)} for p in product_data], cached=_compute_cache_observability(product_data)["cache_hit"])`
   inside `try/except` (fallback: the caller's `confidence`, then `{}` — the builder must never
   raise); `overview.confidence = conf` (replacing the caller's dict), and
   `_build_scoring_v2(..., precomputed_confidence=conf)` → `_confidence_legs_and_details(
   product_data, precomputed=conf)` uses it instead of calling `compute_confidence` again.
   `shopping_count` is set on COPIES only; the product dicts reaching the response are never
   given a `shopping_count` key. Flag OFF: `overview.confidence` is the caller's dict and
   `_confidence_legs_and_details` recomputes exactly as today (`precomputed` defaults None).
3. **Leave alone:** the three orchestrator `compute_confidence` calls, their `shopping_count=`
   argument and the SSE `scores` event payload (no client consumer; changing it widens the
   fork for no reader) — say so in the PR. The caller-facing `build_comparison_response`
   signature gains nothing (the count rides the product dict).
4. `_shopping_listing_count` never reaches the wire: the builder constructs every public
   product dict field by field (pin B7).

Expected ON values (design prototype, same inputs as the Part B table, listing counts per
product): `converted_usd` / `estimated` / `google×2` shapes → `(0,0)` weak/0, `(1,1)` weak/1,
`(2,2)` **acceptable**/2, `(3,0)` strong/3; `local_bhd` PDP and PDP+google → strong at every
count, `source_count` = product 0's count. Both surfaces carry the same dict.

### Part C — `ENABLE_FACTCHECK_SHOPPING_KEY` (default OFF; reader `factcheck_shopping_key_enabled()`)

1. New module helper `_shopping_cache_key(brand, name, variant) -> str` in
   `structured_comparison_service.py`, body = `:6169-6172` verbatim; `_get_price` calls it
   (UNFLAGGED refactor — the string is byte-identical; pin C4).
2. In `_fetch_product_data`, under the flag, BOTH readers use
   `lookup = _shopping_cache_key(brand, name, variant)`: `:5478`
   (`self._shopping_items_cache.get(lookup, [])` — the `full_name` identity ARGUMENT to
   `cross_validate_specs_with_shopping` is unchanged) and `:5718`. Flag OFF: both read
   `full_name` exactly as today.
3. Must NOT touch: `_product_display_identity`, `result["full_name"]`, the M13-10 stash reader
   `:8500` (it keys by its own `full_name` parameter), `verify_price`, `cross_validate_specs_with_shopping`.

### Why OFF is byte-identical

Every new branch is `if <reader>():`; OFF executes HEAD's statements in HEAD's order. The only
unflagged edit is Part C.1's extraction of an expression into a helper returning the identical
string (pinned over 10 shapes). No existing key, value, call or log line changes with all three
flags unset. The corpus harness (`scripts/verify_flag_byte_identity.py`) never enters these
modules — the equality gate below is the proof.

### Client anchors on the phones (561d2cba from ab9442ae)

Unchanged client, backend-only unit. The phones render `scoring_v2.confidence_legs`
(`ConfidencePills.tsx:54-58`: strong→High, acceptable→Medium, weak→Low) and
`confidenceDetailsLines.ts:49-67` (sources line only when `sources_count > 0`; freshness line
`live`/`cached`). Part B ON makes `Medium` reachable and replaces "Pricing checked just now." with
"Pricing from a recent check." exactly when a shown price came from cache. Part A ON removes one
dimension row; the client already renders a variable dimension list (A.4.9). No new key, no
removed key on the wire (Part B replaces a value; `_shopping_listing_count` never ships).
REST and SSE identical.

---

## Files to touch / must NOT touch

Touch: `app/services/scoring_service.py` (three readers; `_score_reliability`;
`_normalize_scores`), `app/services/response_builder.py` (`build_comparison_response`,
`_build_scoring_v2`, `_confidence_legs_and_details`),
`app/services/structured_comparison_service.py` (`_shopping_cache_key`; `_get_price` call;
two readers + the stash in `_fetch_product_data`), three new test files, CLAUDE.md flag rows at
merge. Must NOT touch: `price_service.py`, `fact_check_service.py`, `exchange_rate_service.py`,
the client, migrations, `tests/.pre_impl_failures.txt`, any existing test file.

## Preserve (every file that pins the touched functions; 608 nodes, 608 passed at HEAD, `[netguard] blocked 52` — all pre-existing openai-moderation / `.invalid` supabase attempts)

`tests/test_confidence_thresholds.py` 24 · `test_dim_phantom_tie_followup.py` 28 ·
`test_fact_checking.py` 80 · `test_lane1_integration.py` 4 · `test_m13_04_full_stream_deadline.py` 2
· `test_partial_response_no_fabricated_scores.py` 92 · `test_prescoring_showable_guard.py` 50 ·
`test_price_trust_set_parity.py` 21 · `test_response_builder_price_pending.py` 8 ·
`test_scoring_dimensions_v2.py` 14 · `test_scoring_missing_dim_renormalize.py` 31 ·
`test_scoring_missing_propagates_none.py` 10 · `test_scoring_service.py` 127 ·
`test_scoring_v2_all_nine_categories.py` 54 · `test_scoring_v2_confidence.py` 11 ·
`test_spec_confidence_cache.py` 11 · `test_streaming.py` 23 · `test_winner_prose_reconciliation.py` 18.
Plus `tests/test_comparison_response_image_url.py` (the `_fetch_product_data` harness Part C
edits under) and the four `*_flag_off_golden.json` consumers (`test_behavior_dimension_translation`,
`test_scoring_missing_dim_renormalize`, `test_scoring_spec_field_normalization`,
`test_value_badge_category_dims`) — all run flag-OFF and must stay green.
**Two existing pins are flag-OFF-only by construction** (they compare `_score_reliability` of
an all-unverified input with `<` / `<=`, which is `None` under Part A):
`test_fact_checking.py::…::test_flagged_scores_below_unverified_in_reliability` (`:872`) and
`::test_fabricated_citation_no_longer_outscores_training` (`:885`). Do not edit them; A12 pins
that they run with the Part A flag unset, and the PR says so.

## Red tests

Three new files. Each isolates its flag with `monkeypatch.delenv` of all of:
`ENABLE_RELIABILITY_UNCHECKED_ABSENCE, ENABLE_CONFIDENCE_SINGLE_COMPUTATION,
ENABLE_FACTCHECK_SHOPPING_KEY, ENABLE_CONFIDENCE_FACTCHECK_WIRING,
ENABLE_FACTCHECK_CURRENCY_NORMALIZATION, ENABLE_FACTCHECK_HONEST_ABSENCE,
ENABLE_SPEC_CONFIDENCE_CACHE, ENABLE_CITATION_RUBRIC_V2, ENABLE_BUNDLE_C_SCORING,
ENABLE_MISSING_DIM_RENORM, ENABLE_SPEC_FIELD_NORM, ENABLE_PRESCORING_SHOWABLE_GUARD,
ENABLE_REGION_CURRENCY_GUARD, ENABLE_HONEST_PARTIAL_SCORING` in an autouse fixture, and sets
`ENABLE_EXACT_PRICE_GATE=true` where the builder runs. Every file carries its own socket +
curl_cffi guard (issue #184) until the repo netguard lands. RED = fails at `61585c58` for the
stated reason; PIN = green at `61585c58` and must stay green.

### `tests/test_w4_7_reliability_unchecked_absence.py`

* **A1 RED** `test_a1_unchecked_fact_check_is_absent_flag_on` — parametrized
  `0/0/{1,3,8,11,50}`, `0/0/8 + pv True`, `+ sentiment True`, `+ sentiment False`,
  `+ pv True + sentiment True`: flag ON ⇒ `None`. HEAD: 0.3 ×5, 0.4, 0.35, 0.2, 0.45.
* **A2 PIN** `test_a2_flag_off_values_unchanged` — same inputs, flag unset AND `"false"` ⇒
  `pytest.approx` of the HEAD values.
* **A3 PIN** `test_a3_checked_shapes_identical_both_states` — `1/0/7 → 0.3875`, `0/1/7 → 0.35`,
  `flagged 1 + 7 → 0.2625`, `flagged 1 → 0.0`, `2/0/6 → 0.475`, `{} → None`, zeros → None, flag
  unset and ON.
* **A4 RED** `test_a4_price_verified_alone_cannot_move_the_winner[9 categories]` — the
  identical-pair fixture above, orders AB and BA, flag ON ⇒ the reliability dim is `50` on both
  products, is in BOTH products' `missing_data`, and `win_margin == 0.0` in both orders. HEAD:
  `40.0 / 30.0`, A wins both orders, margins `1.5/1.4/2.5/1.5/1.5/2.0/2.0/2.0/1.5`
  (electronics, other, supplements, fragrances, fashion, grocery, makeup, skincare, haircare).
  Do NOT assert the crown at 0.0 (input-order tie-break is W4-6b's).
* **A5 RED** `test_a5_one_sided_unchecked_is_pair_symmetric[electronics, other, supplements, fragrances]`
  — probe-1 pair: `2/0/6 vs 0/0/8` and `flagged 1 + 7 vs 0/0/8`, flag ON ⇒ dim `50 / 50`,
  `dimension_winners[dim] == {"winner": "N/A", "margin": None}`. HEAD: `47.5/30.0` (A by 17.5)
  and `26.2/30.0` (B by 3.8). Also assert the flagged product is NEVER the dim winner under the
  flag (the review-fix mutation names it).
* **A6 RED** `test_a6_zero_bucket_side_no_longer_outscores_evidence` — probe-4 pairs
  (zero buckets vs `0/0/8`, vs `2/0/6`, no `fact_check` key vs `0/0/8`), flag ON ⇒
  `build_quality_score` `50/50` and in both `missing_data`. HEAD: `50/30.0` winner 0 margin 3.0;
  `50/47.5` winner 0 margin 0.4; `50/30.0` winner 0 margin 3.0 (assert the HEAD numbers in a
  flag-OFF companion, A6b PIN).
* **A7 PIN** `test_a7_equal_and_both_absent_unchanged` — `0/0/8` pv F both ⇒ `50/50 N/A`; both
  `{}` ⇒ `50/50`; flag unset and ON.
* **A8 PIN** `test_a8_flag_off_scores_exact` — electronics probe-1 pair flag unset / `"false"`:
  pv T vs F ⇒ dims `40.0/30.0`, overall `60.8/73.3`, winner 1, margin 12.5; sentiment T vs F ⇒
  `35.0/20.0`, `60.0/71.8`, winner 1, margin 11.8.
* **A9 PIN** `test_a9_reader_truth_table_and_per_call` — `true/TRUE/" true "/1/yes/on` True;
  `false/""/0/no` False; unset False; flip between two calls honoured.
* **A10 PIN** `test_a10_composes_with_missing_dim_renorm` — flag ON + `ENABLE_MISSING_DIM_RENORM=true`
  on the A4 electronics pair: no exception, the dim in both `missing_data`.
* **A11 PIN** `test_a11_honest_absence_composition` — `0/0/8, pv None` ⇒ 0.3 flag OFF, None ON.
* **A13 PIN** `test_a13_two_checked_sides_unchanged_flag_on` — electronics probe-1 pair, flag
  unset AND ON: `2/0/6 vs 1/0/7` ⇒ dims `47.5/38.8`, dim winner Alpha by 8.7, overall
  `61.9/74.7`, winner 1, margin 12.8; `2/0/6 vs flagged 1 + 7` ⇒ `47.5/26.2`, Alpha by 21.3,
  `61.9/72.8`, winner 1, margin 10.9 (both measured; the prototype left them unchanged).
* **A12 PIN** `test_a12_rubric_pins_run_flag_off` — assert the two `test_fact_checking.py`
  pins' inputs give numbers (not None) with the flag unset, documenting why they must not run
  with it set.

### `tests/test_w4_7_confidence_single_computation.py`

Fixture: the Sony/Bose `_mk` of `test_prescoring_showable_guard.py` + fact_check `0/0/8` +
`_shopping_listing_count` per product; `sr = ScoringService().compute_scores(deepcopy(pd))`;
caller confidence = `ScoringService().compute_confidence(deepcopy(pd), shopping_count=2,
cached=True)`; `build_comparison_response(product_data=pd, comparison={}, scoring_result=sr,
confidence=<that>, from_cache=True, query="q", category_used="electronics",
product_names=[SONY, BOSE])`.

* **B1 RED** `test_b1_one_computation_on_both_surfaces[5 shapes × counts (0,0),(1,1),(2,2),(3,0)]`
  — flag ON ⇒ `scoring_v2.confidence_legs == overview.confidence.legs`,
  `confidence_details.price.sources_count == overview.confidence.price.source_count`,
  `confidence_details.price.freshness == overview.confidence.price.freshness`. HEAD: every shape
  differs in `source_count` (2 vs 0) and freshness (cached vs live); the `converted_usd`,
  `estimated` and `google×2` shapes also differ in the leg (acceptable/acceptable/strong vs weak).
* **B2 RED** `test_b2_price_leg_reads_the_shown_price` — `google×2, local_bhd`, counts (0,0),
  flag ON ⇒ BOTH surfaces `price == "weak"`. HEAD: `overview` `strong`. (The thread-the-dict
  mutation M-B2 makes `scoring_v2` `strong` — this row kills it.)
* **B3 RED** `test_b3_real_listing_counts_drive_the_leg` — flag ON, expected
  `(0,0)→weak/0`, `(1,1)→weak/1`, `(2,2)→acceptable/2`, `(3,0)→strong/3` for `converted_usd`,
  `estimated`, `google×2`; `strong` at every count for `local_bhd` PDP and PDP+google.
  HEAD `scoring_v2`: `weak/0` (non-trust) and `strong/0` (trust).
* **B4 RED** `test_b4_freshness_is_the_real_cache_hit` — flag ON: a shown price with
  `_cached: True` ⇒ both surfaces `freshness == "cached"`; no `_cached` ⇒ `"live"` even with
  `from_cache=True`. HEAD `scoring_v2`: `live` in both (measured `cache_hit True`, pill `live`).
* **B5 RED** `test_b5_orchestrator_stashes_real_listing_count` — the `_fetch_product_data`
  harness; flag ON: cache seeded under the `_get_price` key with 3 rows ⇒
  `result["_shopping_listing_count"] == 3` for `Tom Ford / Tom Ford Oud Wood / 100ml` AND for
  `Tom Ford / Oud Wood / 100ml`; supplements category with `[]` ⇒ 0. HEAD: key absent.
* **B6 PIN** `test_b6_flag_off_identical` — flag unset: `overview.confidence` equals the caller's
  dict; `scoring_v2` legs/details equal the HEAD table values for all 20 shape×count rows;
  `_shopping_listing_count` absent from the harness result.
* **B7 PIN** `test_b7_listing_count_never_serialised` — flag ON, `json.dumps(response)` contains no
  `_shopping_listing_count` and no `shopping_count` inside `overview.products` / `products`.
* **B8 PIN** `test_b8_reader_truth_table_and_per_call`.
* **B9 PIN** `test_b9_partial_build_never_raises` — flag ON, `metadata={"partial": True}`,
  `confidence={}`, `scoring_result={}`, with W4-4's flag unset and `"true"`: no exception,
  `overview.confidence["legs"]` has the three keys.
* **B10 PIN** `test_b10_composes_with_factcheck_wiring` — flag ON + #109 ON, warm shape
  (`0/0/8, pv False, 89.8`, PDP `local_bhd`): both surfaces `{price acceptable, specs weak}`
  (the measured #109-ON legs), equal.

### `tests/test_w4_7_factcheck_shopping_key.py`

* **C1 RED** `test_c1_fact_check_reads_the_key_get_price_wrote[3 mismatching shapes]` — the
  probe-5 harness, flag ON ⇒ `price_verified False`, `price_deviation_pct 65.0`. HEAD:
  `True, None`.
* **C2 PIN** `test_c2_matching_shapes_unchanged` — `Tom Ford/Oud Wood/100ml`,
  `Apple/iPhone 15` ⇒ `False, 65.0`, flag unset and ON.
* **C3 PIN** `test_c3_flag_off_keeps_todays_read` — mismatching shapes, flag unset ⇒
  `True, None`; with HONEST_ABSENCE ⇒ `None, None`.
* **C4 PIN** `test_c4_cache_key_helper_is_the_get_price_key` — the 10-shape table
  (`result_full_name` vs key) through `_shopping_cache_key`, plus a spy proving `_get_price`
  writes under `_shopping_cache_key(brand, name, variant)`.
* **C5 RED** `test_c5_spec_cross_validation_reads_the_same_key` — spy on
  `cross_validate_specs_with_shopping`: flag ON, mismatching shape ⇒ called with the 3 seeded
  rows (and `full_name` unchanged as the identity argument); HEAD ⇒ `[]`. (Not run in this
  spec phase — the red agent measures and pastes it; the key facts are C1's.)
* **C6 PIN** `test_c6_reader_truth_table_and_per_call`.

## Gates

1. TDD red-first; every RED observed red at `61585c58` for the stated reason, then green.
2. **Comm gate** — `grep -rlE "scoring_service|response_builder|structured_comparison_service|fact_check_service" tests/ --include=*.py`
   = **238** test files (+ 1 fixture generator, excluded) ∪ the three new files; base
   `61585c58` (detached scratch worktree) vs head, both through the netguard, `comm -13` of
   the sorted FAILED sets EMPTY; accepted base failures = `tests/.pre_impl_failures.txt`.
   Also run the 13 files `grep -rl "SmartCompareApp" tests/` names (standing rule).
3. **Equality gate (flag-OFF identity; the corpus harness is blind to these modules).** A
   scratch pytest file under the guard dumps, per record, `json.dumps(obj, sort_keys=True,
   default=str)` with `metadata.timestamp` removed, of: `compute_scores` and
   `build_comparison_response` for the 9 `tests/fixtures/lane1/*_response.json` inputs
   (`build_inputs` + recorded `metadata.fact_check`); the Part A pair matrix (6 pairs × 9
   categories, both orders); the Part B shape × count matrix (20 rows); the Part C
   `_fetch_product_data` harness × 5 shapes × {flags off, #106 on, honest-absence on}. Run at
   base → head → base2 with all three new flags UNSET; require every record's sha256 equal
   record-by-record (never only an overall digest). Also
   `git diff --stat 61585c58 -- app/services/price_service.py app/services/fact_check_service.py`
   EMPTY. State in the PR that `scripts/verify_flag_byte_identity.py` does not enter this unit.
4. **CI-order pin set** — one invocation, alphabetical: the 18 Preserve files +
   `tests/test_comparison_response_image_url.py` + the three new files, flags unset; then the
   three new files with each flag `=true` in turn.
5. `ruff check --select E9,F63,F7,F82` + `py_compile` on the three modules.
6. Adversarial review on the exact bytes before commit; agents never commit.

## MUTATION CHECKS ARE REQUIRED

| mutation | must redden |
|---|---|
| M-A1 drop the unchecked `return None` | A1, A4, A5, A11(ON) |
| M-A2 drop the pair-symmetric collapse (= the review's one-sided fix) | A5 (flagged product becomes dim winner), A6 |
| M-A3 collapse on ANY pair (not only mixed presence) | A13 |
| M-A4 reader forced True | A2, A6b, A8 |
| M-A5 reader without `.strip().lower()` | A9 |
| M-B1 recompute in `_build_scoring_v2` instead of `precomputed` | B1 |
| M-B2 thread the ORCHESTRATOR's dict (review's first choice) | B1, B2, B3 |
| M-B3 compute BEFORE the chokepoint | B2 |
| M-B4 `cached=from_cache` instead of the cache hit | B4 |
| M-B5 stash `len(self._shopping_items_cache)` (product count) | B3, B5 |
| M-B6 stash under `full_name` instead of the `_get_price` key | B5 |
| M-B7 reader forced True | B6 |
| M-C1 only `:5718` switched, not `:5478` | C5 |
| M-C2 helper body drifts from `:6169-6172` (drop the variant-in-name branch) | C4, C1 (Samsung) |
| M-C3 reader forced True | C3 |

Record each count.

## Activation

Order (one canary per step, never batch): **Part B any time** (independent; recommended
FIRST so every later pill canary reads one surface) → **`ENABLE_SPEC_CONFIDENCE_CACHE` (#107)**
→ wait for the 7 d L1 / 30 d L2 specs cache to roll (`PO-FACTCHECK-CONFIDENCE-05`; cold
extracts write the map at once, the roll is gradual) → **Part C** → **#106
`ENABLE_FACTCHECK_CURRENCY_NORMALIZATION`** (+ `ENABLE_FACTCHECK_HONEST_ABSENCE` in its own
window right after) → **#109 `ENABLE_CONFIDENCE_FACTCHECK_WIRING`** → **Part A** LAST, own
window. The `scoring_service.py:982-989` docstring gets Part C and (Open question 6) #108.
Canary lines/fields: Part B — `scoring_v2.confidence_legs == overview.confidence.legs` on 100 %
of rows, distribution of the price leg (Medium appears), `confidence_details.price.
sources_count` is 0 on every supplements row; Part C — share of `price_verified True` with
`price_deviation_pct None` falls on brand-repeating names; Part A — the
`[RELIABILITY] pair-symmetric absence` INFO count, `metadata.missing_dim_cells` rises by ≤ 2
per comparison, and `winner_index` changes are read from the SSE `scores` event, not only
`complete`. All need OpenAI credit for a live compare (latent until then).

## Honest limits

* The review's `34/46`, `25/46`, `19/46` and `74 %` come from a live Supabase SELECT; nothing
  on disk carries those rows — **unverifiable offline**. What IS measured: the mechanism (all
  tables above) and 15/15 recorded `source_count == 2`.
* Part A on an EXACTLY identical pair leaves `win_margin 0.0` and the crown to input order
  (measured: sym AB → A, BA → B). Honest (a tie) but the crown is W4-6b's order-symmetric
  tie-break (`PO-RUBRIC-10`).
* Until #107's cache roll, Part A removes the reliability dimension from essentially every
  comparison (the warm shape IS all-unverified) — hence LAST.
* Part B follows the §5a contract: a pended price with ≥ 3 real listings still reads `strong`
  (`max_shopping >= 3`). Whether a pill may be strong beside "price pending" is Open question 5.
* The reliability dimension's LABEL ("Build quality", "Safety", "Evidence"…) measures our
  citation verification, not the product — a rubric question for W4-6, not changed here.
* Part C does not touch the M13-10 stash reader `:8500`; vision products whose `name` repeats
  the brand were measured on the key string only (`Sony / Sony WH-1000XM5`), not end to end.
* Part C's HEAD fabrication is not purely a W4-7 matter: it also starves
  `cross_validate_specs_with_shopping` (C5) — the spec half of the fact-check.

## Spec disagreements with the review

1. **-01's fix (return None, one-sided) inverts** — measured: the unchecked side scores 50
   over a partly verified 47.5, and the FLAGGED product becomes the dimension winner
   (26.2 vs 50). This spec makes absence pair-symmetric.
2. **-02's first-choice fix (thread the orchestrator dict) regresses** — measured: `strong`
   pill beside two pended prices; "Checked across 2 retail sources." on supplements. This spec
   computes once, after the chokepoint, with real counts.
3. **-02 "unflagged" → flagged**: it changes the phones' pill, sheet copy and every persisted
   `overview.confidence`.
4. **"inside ENABLE_CONFIDENCE_FACTCHECK_WIRING"** → three own flags (Flag decision).
5. **-04 "pure activation" is incomplete** — #106 is inert on 3 of 5 driven name shapes
   (measured `True, None` with #106 ON); Part C is the missing half.
6. **-12 freshness**: the review's red asks `freshness == 'cached'` when `from_cache=True`;
   `from_cache = not nocache` is "cache allowed" — this spec uses the real cache hit.
7. **-01's "only input that can break the tie"**: sentiment also moves it (0.35 / 0.2), as the
   verifier noted.
8. **Anchors** (review `76ace90` → `61585c58`): `scoring_service.py:1958-1976` → `_score_reliability`
   `:1957-1986` (finding line `:1967` unchanged); `:982-989` unchanged (docstring of
   `confidence_factcheck_wiring_enabled` `:970`); `-03`'s `:1114` unchanged;
   `:1712-1713` → `:1717-1725`; dimension map `:2015-2059` → `:2024-2070`;
   `response_builder.py:1055` → `_confidence_legs_and_details` `:1064`, its call `:1077`, caller
   `:1190`; `fact_check_service.py:441` → `verify_price` `:399`, legacy verdict `:445`, #106
   branch `:417`; `structured_comparison_service.py:2980` → `:3400-3404` / `:4010-4012` /
   `:4665-4667`; `:2978-2980, :3528-3529, :4138-4139` (U11) → the same three.

## OPEN QUESTIONS FOR FABLE

1. **Flags**: accept three own flags, or (a) Part A rides #109 (one flip, one rollback, confounded
   canary), (b) Part C rides #106?
2. **Part A shape**: pair-symmetric absence (this spec) vs the review's one-sided None (measured
   inversions) vs deferring the one-sided case to `ENABLE_MISSING_DIM_RENORM` (#101, blocked on
   Ahmed's call)?
3. **Part B freshness source**: the real cache hit (this spec) or `from_cache` (the review)?
4. **Scope**: keep Part C in W4-7 or split it to W4-7c; include the `:5478` spec reader (C5) or
   price-only?
5. **Product call (Ahmed)**: may the price pill read High/Medium beside a "price pending" row
   when ≥ 2/3 real listings exist (§5a), or cap at Low when every shown price is pending?
6. Add `#108 ENABLE_CITATION_RUBRIC_V2` to the HARD ACTIVATION docstring
   (`PO-FACTCHECK-CONFIDENCE-10`) in this unit, or leave to its own row?
7. `ENABLE_FACTCHECK_HONEST_ABSENCE` placement: its own window right after #106 (this spec), or
   with it?
8. Part A before or after W4-6b's order-symmetric tie-break (Part A manufactures exact ties)?


---

# ADVERSARIAL SPEC REVIEW (2026-09-26, session 68)

Reviewer: adversarial spec reviewer, base `61585c58` (`git rev-parse HEAD` in `sc-w4-specs` =
`61585c581e9deb78213f030260a765080f2e1dff`), spec sha256 before this append
`8ea361fbcd6aedd7dc0e3b6a280c70f190f5bfae945492519e3d8753cf9dfc7a`. Every number below was
re-measured by me through the real functions: pytest probes loaded with `-p qaren_netguard -p
tests.conftest`, pinned venv, no LIVE. Probes and raw JSON: `<scratchpad>/w47adv/test_adv_{a,b,c,d}.py`
-> `adv_{a,b,c,d}.json`. Guard lines: probe a `[netguard] blocked 0` (26 passed), probe b
`blocked 0` (14 passed), probe c `blocked 1` (6 passed; the one attempt is the pre-existing
`neutralized.supabase.invalid` connect on the supplements `_fetch_product_data` path, blocked),
probe d `blocked 0` (1 passed). Preserve run at HEAD: `608 passed`, `[netguard] blocked 52`
(the author's number reproduces exactly); the extra four Preserve files
(`test_comparison_response_image_url`, `test_behavior_dimension_translation`,
`test_scoring_spec_field_normalization`, `test_value_badge_category_dims`): `86 passed`,
`blocked 3`.

## VERDICT: APPROVED_WITH_CORRECTIONS

The measurement core is sound: every Part A number, every Part B HEAD row, both -03/-04
re-measurements and the Part C end-to-end table reproduce to the digit. But the design has one
defect that ships a private key on the wire (Part B stash, below), eight tests labelled PIN are
red at HEAD, Part C covers two of the four wrong-key readers, and Part B's listing count hides a
product decision (raw US Google-Shopping row count) that will turn the price pill High on
nearly every compare. None needs a redesign; all need the corrections below before a red phase.
Part B must not reach red until Fable rules on Q9 (count semantics).

## Claims that HOLD (re-measured, identical)

* `_score_reliability` table: 0.3 for 0/0/{1,3,8,11,50}; 0.4 pv True; 0.3 pv None; 0.35 /
  0.19999999999999998 sentiment True/False; 0.45 pv+sentiment; 0.3875 / 0.35 / 0.2625 / 0.0 /
  0.475 checked shapes; None for `{}` and all-zero.
* 9-category identical pair (150 BHD local_bhd, bolo.bh PDPs, 4.5/1000, E0 specs, 0/0/8, only
  pv differs): dims 40.0/30.0, pv-True product wins in BOTH orders, margins
  1.5/1.4/2.5/1.5/1.5/2.0/2.0/2.0/1.5 (electronics, other, supplements, fragrances, fashion,
  grocery, makeup, skincare, haircare); dim not in `missing_data`. Both absent: 50/50, dim in
  both `missing_data`, win_margin 0.0, crown = input order (AB -> A, BA -> B). My Part A
  prototype (one-sided None + pair-symmetric collapse by monkeypatch) gives the same.
* One-sided zero-bucket table: 50/30.0 winner 0 margin 3.0 (67.0/64.0); 50/47.5 winner 0 margin
  0.4 (67.0/66.6); 50/100 winner 1 margin 7.5 (67.0/74.5); no-key vs 0/0/8 = row 1.
* Review-fix prototype table (electronics/other/supplements/fragrances identical dims):
  47.5/50 and 26.2/50 with the FLAGGED product named dim winner ("Alpha Phone One") — holds.
* A8 (60.8/73.3 winner 1 margin 12.5; 60.0/71.8 margin 11.8) and A13 (47.5/38.8 Alpha by 8.7,
  61.9/74.7, margin 12.8; 47.5/26.2 Alpha by 21.3, 61.9/72.8, margin 10.9) — hold, unchanged
  by the prototype.
* Part B HEAD table, all five rows (overview vs scoring_v2 leg, source_count 2 vs sources_count
  0, cached vs live, shown vs pended) — holds exactly. Orchestrator dict on google x2 =
  `strong`/2/cached (the review's thread-the-dict fix would ship strong beside two pended
  prices) — holds. Builder price leg sweep, 5 methods x counts 0-3 x #109 OFF/ON: builder only
  `strong`/`weak`, overview `acceptable` at 2 / `strong` at 3 for non-trust — holds.
* Part B ON expected values (my prototype = `compute_confidence` on the post-chokepoint product
  dicts with per-product counts, `cached=cache_hit`): converted/estimated/google x2 -> (0,0)
  weak/0, (1,1) weak/1, (2,2) acceptable/2, (3,0) strong/3; local PDP and PDP+google strong at
  every count — holds. `_cached` survives to `_build_scoring_v2` (spy: `[True, True]`,
  `metadata.cache_hit True`); it is stripped only after return (`public_price_view`), so the
  in-builder cache-hit design is feasible.
* B10 (#109 ON, warm shape, PDP local_bhd): both surfaces `{price acceptable, reviews strong,
  specs weak}` at HEAD already — a genuine PIN.
* 15/15 fixture `overview.confidence.price.source_count == 2` (6 `comparison_baseline_d2*` + 9
  `lane1/*`), now_vs_solgar recorded `acceptable` — holds.
* -03 warm shape (local_bhd: OFF {strong,strong,strong} high citation 8; ON
  {acceptable,strong,weak} low citation 0; converted_usd OFF {weak,strong,strong} medium, ON
  {weak,strong,weak} low) and -04 `verify_price` (OFF 250 vs 3x AED -> True 0.0, 25.5 -> False
  89.8; #106 -> False 876.6 / True 0.4; zero rows real -> True / None with honest-absence;
  estimate False; BHD 25.500 rows -> True 0.0 in every state) — hold.
* Reader truth table (`true/TRUE/" true "/1/yes/on` True; `false/""/0/no`/unset False) — holds.
* Part C e2e: matching shapes False/65.0 in all three states; the three listed mismatching
  shapes True/None (OFF and #106) and None/None (honest-absence) — holds. C5's HEAD value
  (spy on `cross_validate_specs_with_shopping`): mismatching shape gets 0 rows, matching 3 —
  C5 is genuinely RED.
* Client anchors: `ResultsContent.tsx:471/482/490`, `ConfidencePills.tsx:56-58`,
  `confidenceDetailsLines.ts:49-67`, `en.json:180/183/184`; zero client readers of
  `overview.confidence`; `onScores` is declared in `api.ts:556/808` with no screen consumer;
  `git diff --stat ab9442ae 61585c58 -- SmartCompareApp` empty — hold.
* Comm-set grep = 239 files incl. `tests/fixtures/_gen_behavioral_flag_off_golden.py` (238 test
  files + 1 generator) — holds; `grep -rl SmartCompareApp tests/` = 13 .py files — holds.
* All other line anchors re-read and hold, except the two trivia below.

## Refuted or drifted claims (with my measurement)

1. **"`_shopping_listing_count` never reaches the wire: the builder constructs every public
   product dict field by field (pin B7)" — REFUTED.** `response_builder.py:2025`
   `result["products"] = product_data` ships the RAW product dicts (only `price` is replaced by
   `public_price_view`). Measured: product dicts carrying `_shopping_listing_count: 3` through
   the real `build_comparison_response` -> `json.dumps(response)` contains
   `_shopping_listing_count` (and `shopping_count`); `result["products"][0]` keys =
   `_shopping_listing_count, _stage_timings_ms, brand, category, category_profile, cons,
   full_name, image_url, name, price, pros, rating, rating_count, review_count, review_praise,
   shopping_count, specs`. No compare route declares a `response_model` (only auth routes do),
   so the key ships on REST, on the SSE `complete` payload and into every persisted response
   row. B7 as written is RED at HEAD with the B fixture AND stays RED after the designed change.
   (`_stage_timings_ms` already leaks the same way — pre-existing, out of scope.) The verdict
   prompt is safe (`extraction_service._verdict_safe_product` drops `_`-keys).
2. **Eight tests labelled PIN are red at `61585c58`:** A9, B8, C6 (the new readers do not exist
   -> AttributeError); C4 (`_shopping_cache_key` does not exist); A10 (at HEAD, flag set is a
   no-op: A4 electronics pair dims 40.0/30.0 and `build_quality_score` NOT in either
   `missing_data` — measured); A11 (the ON half: HEAD returns 0.3, not None); B9 (HEAD with
   `confidence={}` -> `overview.confidence == {}` measured in both W4-4 states, so
   `["legs"]` raises KeyError); B7 (item 1).
3. **Mutation M-B5 "must redden B3, B5" — wrong for B3.** B3 feeds the builder explicit
   `_shopping_listing_count` values; an orchestrator stash mutation cannot reach it. Only B5
   kills M-B5.
4. **Part C "`_fetch_product_data` reads the cache ... at TWO sites" — incomplete: four
   wrong-key readers.** Besides `:5478` and `:5718`: `:5499`
   `collect_retailer_ratings(full_name, self._shopping_items_cache)` (rating_service.py:69
   `shopping_items_cache.get(full_name, [])`) and `:5517` `self._get_verified_rating(full_name)`
   (rating_service `get_verified_rating` reads `shopping_items_cache.get(full_name, [])`).
   Measured end to end (3 seeded rows carrying source+rating): matching shapes
   `collect_retailer_ratings` -> 3 rows and `fact_check.review_sentiment_consistent True`;
   all five mismatching shapes -> 0 rows and `review_sentiment_consistent None`, in every flag
   state. The drift therefore also starves the sentiment verdict — which is one of the two side
   signals Part A's `_score_reliability` reads (+0.05 / -0.1).
5. **"Supplements (cache `[]`) -> 0" and the Part B canary "`sources_count` is 0 on every
   supplements row" — contradicted by code (code-anchored, NOT measured end to end):**
   `_get_price`'s supplement iHerb stage overwrites the same key with a one-row list
   (`scs:7667-7673`, `{"source": "iHerb", "rating": ..., "link", "title"}`, no price) whenever
   iHerb returns a rating, after the `[]` write at `:6808`. Under Part B that is count 1 ->
   "Checked across 1 retail sources." on a row that carried no price.
6. **"5 of 10 name shapes disagree"** is sample-dependent, not wrong; over 13 shapes I measured
   8 disagreeing, including three the spec does not list: vision + variant
   (`Sony / WH-1000XM5 / Black`: the vision identity drops the variant), brand casing
   (`TOM FORD / Tom Ford Oud Wood / 100ml`), lower-case variant already in the name
   (`Samsung / Galaxy S24 Ultra / ultra`). Also measured END TO END (spec: "key string only"):
   vision `Sony / Sony WH-1000XM5` and `NOW Foods / NOW Foods Vitamin D3 5000 IU` -> True/None
   (OFF, #106), None/None (honest-absence).
7. Trivia: `dimension_winners[...]` "disagrees with its own numbers" holds in 3 of the 4
   zero-bucket rows (vs 8/0/0 it names Beta at 100 vs 50, which is right);
   `_compute_cache_observability` spread is `:1942` (`:1941` is its comment).

## Corrections (binding before red)

1. **Part B: strip the stash in the builder.** After the single computation, pop
   `_shopping_listing_count` from every product dict (`pd.pop("_shopping_listing_count", None)`
   unconditionally is a no-op when absent, so flag OFF stays byte-identical) BEFORE
   `result["products"] = product_data`. B7 asserts on `result["products"]`,
   `overview.products` and the full `json.dumps`. Add mutation **M-B8 no strip -> B7**.
2. **Relabel** A9, A10, A11, B7, B8, B9, C4, C6 as RED, or split each into a PIN half that is
   green at HEAD (e.g. A11 OFF=0.3, B9 no-raise) and a RED half.
3. **Mutation table:** M-B5 kills B5 only; add M-B8 (above); if Part C takes the extra readers,
   add M-C4 "switch :5478/:5718 but not :5499" -> the new sentiment test.
4. **A6 must pin the fully-verified row** (zero buckets vs 8/0/0): HEAD 50/100, winner 1,
   margin 7.5, 67.0/74.5; pair-symmetric ON (my prototype) 50/50, **67.0/67.0, winner 0,
   margin 0.0** — the verified product's win is erased and the crown falls to input order.
   Every r3 row goes to an exact 67.0/67.0 tie under Part A ON. State this in Honest limits;
   it is not only the identical-pair case.
5. **C4's table** adds the three extra disagreeing shapes of refutation 6.
6. **Part B canary**: drop "sources_count is 0 on every supplements row" (refutation 5) or
   replace it with "sources_count <= 1 on supplements rows".
7. **CI-order pin set**: add `tests/test_multiplicity_discriminator_policy.py` (block B
   `_full_name` replicates the exact expression Part C.1 extracts; `scs:6166-6168` names it as
   the pin) and the `_get_price` / `_fetch_product_data` source scanners
   (`test_wall_caps_i57`, `test_genuine_price_priority`, `test_discovery_window_i54`,
   `test_category_aware_discovery_i55`, `test_phase1_per_race_timeouts`,
   `test_response_builder_phase1_none_guard`, `test_price_timeout_returns_parked`). All are in
   the comm set already; they are the collision points for the Part C refactor and belong in
   the fast alphabetical run too.
8. **Part C scope (pending Fable Q11):** either route all four readers (`:5478`, `:5499`,
   `:5517`, `:5718`) through `_shopping_cache_key` under `ENABLE_FACTCHECK_SHOPPING_KEY`, with
   a C7 RED (`review_sentiment_consistent` None -> True on the mismatching shapes, flag ON) and
   a C7b PIN (flag OFF None), or state explicitly that sentiment/verified-rating stay drifted
   and that Part A therefore still reads a key-dependent sentiment modifier. Note `:5517`
   passes `full_name` as BOTH the cache key and the rating query string
   (`extract_rating_from_shopping(full_name, ...)`); only the lookup may change.

## Missing items

* The `result["products"]` alias as a Part B leak path (correction 1).
* Readers `:5499` / `:5517` (refutation 4).
* **The same key drift on the PRICE path, outside this row:** `_price_fallback_on_miss` reads
  `self._parked_price` / `self._price_candidates` with the dedup'd `full_name`
  (`scs:5382/5385` -> `:5965-5971`, `:5942`) while `_get_price` writes them under its own key
  (`:6737`, `:6913`, `:6928`, `:7645`, `:7569`). Measured (`_price_fallback_on_miss("price",
  <result full_name>)` with a parked converted 127.8 under the `_get_price` key,
  `ENABLE_GENUINE_PRICE_PRIORITY` unset): `Tom Ford / Oud Wood / 100ml` -> 127.8;
  `Tom Ford / Tom Ford Oud Wood / 100ml`, `Apple / Apple iPhone 15`,
  `Samsung / Galaxy S24 Ultra / Ultra` -> **None** — the timeout rescue of a parked price
  silently fails for brand-repeating names, so the product ships price-pending. `_tier15_routes`
  `:5443` drifts the same way (observability only). This is a price-path defect: a separate
  unit behind its own flag, not folded into W4-7 (the helper `_shopping_cache_key` is the
  shared fix). Existing tests (`test_price_timeout_returns_parked`, `test_genuine_price_priority`)
  seed with non-repeating names and cannot see it.
* A Part A composition pin with `ENABLE_BUNDLE_C_SCORING=true` (the spec's autouse fixture
  deletes it; measured with my prototype: no exception, 2/0/6 vs 0/0/8 -> 50/50 N/A, 62.2/76.3,
  same as flag-unset composition).
* A partial-path note for Part B: the early-specs buffer rows never reach the `:5718` stash, so
  a salvaged partial under Part B ON reads count 0 (weak for non-trust methods) where HEAD's
  overview read 2.

## Design risks

1. **Part B's "real listing count" is the raw Serper Shopping row count.** `_get_price`
   writes `search_results.get("shopping", [])` unfiltered (`scs:6839-6840`); in GCC the list is
   the gl=us fallback by construction (`serper_service.py` skips the gl=bh primary unless
   allow-listed) with `num: 10`. Under Part B ON a typical Tier-1 compare therefore carries
   ~10 rows per product -> price leg `strong` ("High") whatever the shown price, including
   beside two pended prices (measured prototype, google x2 at (3,0): `strong`, source_count 3),
   and the sheet says "Checked across 10 retail sources." about US listings that were never
   identity- or currency-matched (with #106 OFF they are compared currency-blind). That trades
   today's under-claim for an over-claim. The choice of what counts as a "retail source" is a
   product decision the design makes silently (Q9).
2. **Part A erases genuine verified evidence** when the rival has no checkable spec fields
   (correction 4), and turns such pairs into exact ties decided by input order — broader than
   the identical-pair case Honest limits names.
3. **Part C OFF-parity of the unflagged refactor** rests on the helper returning the identical
   string; the spec pins 10 shapes — add the 13 measured here, including casing and vision
   variants.
4. **Phone copy:** Part B makes `sources_count == 1` reachable; `en.json:180` / `ar.json:177`
   have no plural form, so phones would render "Checked across 1 retail sources." Backend-only
   unit — either cap the rendered count semantics (Q9) or queue a client plural key for the
   next OTA.
5. Part A + Part C interplay: until the sentiment readers are keyed correctly, a brand-repeating
   product always has `review_sentiment_consistent None` (no modifier) while its rival can get
   +0.05/-0.1 — Part A's pair-symmetric rule only fires on None `reliability_raw`, so this
   asymmetry survives Part A.

## Questions Fable must rule on (in addition to the author's eight)

9. **Part B count semantics:** raw `len(shopping rows under the _get_price key)` (spec), or the
   rows that actually entered `verify_price`'s median (`_price_verification.source_count`),
   or only rows that pass the identity/currency gates (requires #106/#108), or distinct
   `source` values? Until ruled, Part B's pill will read High on nearly every compare.
10. **Part A on "no checkable fields vs fully verified":** accept that pair-symmetric absence
    removes a fully-verified product's reliability win (winner flips to input order at 0.0), or
    restrict the collapse to the all-unverified side only (keep zero-bucket rows as today)?
11. **Part C readers:** all four (`:5478/:5499/:5517/:5718`) under one flag, or price+spec only?
12. **The parked-price / price-candidate key drift** (Missing items): its own unit and flag
    (recommended), or fold into Part C (it is a price-path fork and would blind Part C's
    canary)?

## Files

Appended this section only; no other file in the worktree touched. Scratch probes:
`<scratchpad>/w47adv/test_adv_a.py`, `test_adv_b.py`, `test_adv_c.py`, `test_adv_d.py` and
their `adv_*.json` outputs, `comm.txt`, `extra*.txt`. No scratch worktree was created.
