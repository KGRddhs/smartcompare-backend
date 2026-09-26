# GitHub issues referenced by the W4 rows (fetched 2026-09-26 via REST)

## #100 [closed] [scoring] normalize spec fields per-field before aggregating instead of summing raw cross-unit magnitudes

## Context

`_score_specs` sums raw numbers across incompatible units (mAh + GB + MP + counts) into one score. Because Apple specs battery in hours and Samsung/Xiaomi in mAh, the winner of an electronics comparison is decided by **notation**, not quality — in the largest category of the 200-query gold set (`data/gold_truth_taxonomy_manifest.json` → `category_totals.electronics = 34`). The same raw-magnitude sum makes the sparse-coverage penalty invert: a product whose page yielded one big-number spec beats a fully-captured competitor. M18 findings `PO-rubric-01` and `PO-rubric-02` are the same root cause with two independently observable symptoms, so they are one fix.

## Current behavior

`app/services/scoring_service.py`, `_score_specs` at `:1376-1434`. The schema field list is selected at `:1389-1396` (`CATEGORY_SPEC_SCHEMAS` lives in `app/services/extraction_service.py:108`; `NON_SCORING_SPEC_KEYS` at `scoring_service.py:21`), and the direction sets at `:1398-1399`. Every `HIGHER_IS_BETTER` field then adds its raw magnitude:

```python
numeric = self._extract_number(str(value))   # :1409
if numeric is not None:
    if field in higher:
        total_score += numeric               # :1412  <-- raw mAh, GB, MP, hours
        scored_fields += 1                   # :1413
```

and the coverage penalty divides by the count of *populated* fields:

```python
if scored_fields == 0:
    return None                                                # :1424-1425 (B0-A v2.1 guard)
total_fields = len(schema_fields)                              # :1427
coverage_ratio = scored_fields / total_fields if total_fields > 0 else 0   # :1428
min_coverage = CATEGORY_MIN_COVERAGE.get(schema_key, 0.3)      # :1429  (table at :999-1003)
if coverage_ratio < min_coverage:
    penalty_factor = 0.5 + coverage_ratio                      # :1431
    return (total_score / scored_fields) * penalty_factor      # :1432
return total_score / scored_fields                             # :1434
```

Reproduced offline (no network, no LLM) against the real 11-field electronics schema (`extraction_service.py:109-113`; `battery` is in `HIGHER_IS_BETTER_BY_CATEGORY["electronics"]`, `scoring_service.py:261`):

| Product (identical otherwise) | specs | `spec_raw` | overall | winner |
|---|---|---|---|---|
| Phone M | `battery: "5000mAh"` + 6 more fields | 761.1 | 74.0 | yes |
| Phone H | `battery: "Up to 29 hours video playback"` + same 6 | 51.0 | 57.6 | no |
| Phone M-sparse | `{battery: "5000mAh"}` only (coverage 1/11, penalized) | 2954.5 | 69.7 | yes |
| Phone M-full | full 7-field dict | 761.1 | 55.0 | no |

All four numbers above are **measured** by calling `ScoringService.compute_scores` directly on synthetic products.

- 14.9x notation gap; Phone M wins at equal price **despite a lower rating (4.5 vs 4.7) and fewer reviews**.
- The sparse case computes `(5000 / 1) * (0.5 + 1/11) = 2954.5` — the maximum ~37.5% discount cannot counter a 3.9x concentration, so **thinner extraction wins**, the exact case the penalty exists to punish.
- The magnitude-aware A1 ratio (`:1844-1849`, helper `_magnitude_aware_ratio` at `:370`) then sees a relative gap far past its tolerance and treats the notation artifact as a decisive genuine gap.
- Blast radius: `spec_raw` feeds the `"spec"` and `"spec_secondary"` signals simultaneously (`signal_to_raw_key` at `:1344-1345`) and the value formula's 0.70 spec coefficient (`VALUE_FORMULA_BY_PRIORITY["_default"] = {"spec": 0.7, "price": 0.3}`, `:540`). For electronics that is `performance_score` 0.25 + `feature_score` 0.20 + `value_score` 0.20 = 0.65 of the weighted overall.

## Expected behavior

1. Each schema field contributes a **unit-free 0-1 score relative to the comparison pair**; the product score is the mean of those, so a mAh phone and an hours phone with equivalent battery land at the same tie midpoint.
2. Missing fields **dilute** rather than concentrate: a 1-of-11 capture can never outscore a 7-of-11 capture of the same product.
3. `spec_raw` remains a single `Optional[float]`, so every downstream consumer (`_normalize_dimension` at `:1779`, the `spec`/`spec_secondary` mapping at `:1344-1345`, the value formula) is untouched in shape.
4. `_score_specs` still returns `None` when `scored_fields == 0` (the B0-A v2.1 phantom-tie guard at `:1424-1425`).
5. Flag OFF → scores identical to 593ec1e.

## Implementation notes

File to touch: `app/services/scoring_service.py`.

- `_score_specs(self, specs, category)` is called per-product from `_compute_raw_scores` (def at `:1252`; spec block `:1277-1285`, the call at `:1279`), so it cannot see the pair. Do the pair-relative step where the pair *is* visible — in `_normalize_scores` (def at `:1551`).
- Add `_score_specs_fields(self, specs, category) -> Optional[Tuple[Dict[str, float], int, int]]` returning `({field: signed_numeric}, scored_fields, total_fields)`. Reuse the existing schema/direction selection verbatim from `:1389-1399`; sign lower-is-better fields negative and keep the `+= 1` presence credit for non-numeric values under a reserved key so the coverage math is unchanged.
- In `_compute_raw_scores` at `:1277-1285`, store the tuple on `scores["_spec_fields"]` **in addition to** the existing `scores["spec_raw"]` (`:1280`). Additive only; nothing reads the new key when the flag is OFF.
- In `_normalize_scores`, before `spec_scores = [...]` at `:1583`, when the flag is ON recompute each product's `spec_raw` as: for each field present in **at least one** product, min-max the pair with `_magnitude_aware_ratio(current, min_val, max_val, higher_better=True)` (a field present in only one product scores 1.0 for that product and 0.0 for the other — a genuine advantage, not a notation artifact); average across fields; then apply the coverage discount as `mean * (0.5 + scored_fields / total_fields)` **using `total_fields` as the divisor basis** — that is the `PO-rubric-02` half. Scale the mean in

## #102 [closed] [scoring] resolve the category's value dimension for value_badge instead of hardcoding 'value_score'

## Context

`value_badge` is a user-facing judgment on the product card — `great_value` / `fair_price` / `premium_price` / `overpriced`. Both call sites read a breakdown key that only two of the nine categories emit, so for the other seven the lookup falls back to the literal default `50`, and the `elif value_score >= 50` branch returns `fair_price` unconditionally. The price-tier lookup that feeds the same call is dead too. The feature ships a **constant** for most of the catalog while presenting itself as a computed verdict. M18 finding `PO-rubric-04`.

## Current behavior

Both sites, `app/services/structured_comparison_service.py:3303-3305` (sync) and `:4004-4006` (streaming), are character-identical:

```python
value_score = scoring_result["scores"].get(f"product_{i}", {}).get("breakdown", {}).get("value_score", 50)
price_tier = scoring_result.get("price_tiers", {}).get(product.get("name", ""), "mid")
product["value_badge"] = scoring_service.compute_value_badge(value_score, price_tier)
```

**Defect 1 — the dim key.** `CATEGORY_DIMENSIONS` (`app/services/scoring_service.py:24-61`) names the value dim `value_score` only in `electronics` and `other`:

| category | value-signal dim actually emitted | `"value_score"` present? |
|---|---|---|
| electronics | `value_score` | yes |
| other | `value_score` | yes |
| grocery | `serving_value_score` | no |
| supplements | `serving_value_score` | no |
| makeup | `perf_value_score` | no |
| skincare | `results_value_score` | no |
| haircare | `multi_value_score` | no |
| fragrances | `wear_value_score` | no |
| fashion | `cpw_score` | no |

Reproduced: a fragrance breakdown has no `value_score` key, so `value_score` takes the literal `50` default, and `compute_value_badge` (`scoring_service.py:1961-1975`) takes the `elif value_score >= 50: return "fair_price"` branch at `:1970-1971`. Constant, for 7 of 9 categories.

**Defect 2 — the tier key.** `price_tiers_map` is built keyed on brand+name (`scoring_service.py:1168-1171`):

```python
price_tiers_map = {}                                                     # :1168
for i, product in enumerate(products_data):                              # :1169
    name = f"{product.get('brand', '')} {product.get('name', '')}".strip()   # :1170
    price_tiers_map[name] = price_tiers[i] if i < len(price_tiers) else "mid"  # :1171
```

and shipped as `result["price_tiers"]` at `:1186`. The badge site looks up bare `product.get("name", "")`. Extraction always emits a separate `brand` field (`app/services/extraction_service.py:76`), so the keys never match — probe: map keys `['HouseA ScentA']`, lookup `'ScentA'`. `price_tier` is therefore always `"mid"`, which kills the one branch that consults it — the `luxury -> fair_price` exception at `scoring_service.py:1966-1969`. So even electronics, which *does* emit `value_score`, has a partially dead badge.

## Expected behavior

1. The badge reads the value-signal dimension the product's **category** actually emits.
2. A fragrance pair with genuinely different value can produce a non-`fair_price` badge.
3. `price_tier` resolves for real, so a luxury-tier product with `value_score >= 75` shows `fair_price` rather than `great_value`.
4. When the value dim is genuinely absent (missing data), **no badge** is emitted rather than a defaulted `fair_price` — an absent badge is honest; a defaulted one is a claim.
5. Both call sites behave identically — they are currently copy-paste twins and must not drift.

## Implementation notes

Files to touch: `app/services/structured_comparison_service.py` (both sites), `app/services/scoring_service.py` (one additive result key + one helper).

- **Resolve the dim** via the existing map, not a new literal table. `ScoringService._DIMENSION_SIGNAL_MAP` (`scoring_service.py:1503-1549`) already labels exactly one dim per category with the signal `"value"`. The module-level `_scale_value_weight` (`:713`, inversion loop at `:720-723`) already does this lookup — copy that pattern into a small public helper `ScoringService.value_dim_for(category) -> str` and call it from both badge sites. One source of truth; adding a 10th category or renaming a dim then needs no badge-site edit.
- **Thread the category.** `scoring_result` does not carry it today. Add `"category": category` to the `compute_scores` result dict at `scoring_service.py:1181-1193` (purely additive, next to `"category_weights"` at `:1189`), and have both badge sites read `scoring_result.get("category", "other")`. Note: `category_used` *is* in scope at both sites (used at `:3269` and `:3976`), so threading the local would also work — prefer the result-dict form anyway, because it makes the badge a pure function of `scoring_result` and removes the chance of the two twins reading different category variables, which is exactly how this bug class recurs.
- **Fix the tier key** at both sites: `f"{product.get('brand', '') or ''} {product.get('name', '') or ''}".strip()` — mirroring the expression at `scoring_service.py:1170` so the two can never drift. Better: have `compute_scores` also emit `price_tiers_by_index` (`{"product_0": "luxury", ...}`) in the same result dict and read that; index keys cannot mismatch on a name. Prefer the index form and keep `price_tiers` unchanged for BC.
- **Absent-dim handling**: read with `breakdown.get(dim)` (no literal default), and when the result is `None` skip setting `product["value_badge"]` entirely. Before shipping, confirm `SmartCompareApp` tolerates the key being absent on a product card; if it cannot, set it to `None` explicitly rather than fabricating a tier.
- Flag: `ENABLE_CATEGORY_VALUE_BADGE`, **default OFF**. Use a live reader modeled on `app/services/response_builder.py:108-113` (not the module-cached `_bundle_c_scoring_enabled` at `scoring_service.py:412-421`). Needed because 7 of 9 categories go from a constant to a varying badge in one step.
- Edge case: empty-brand products. `"".strip

## #103 [closed] [scoring] translate behavioral sensitivity into category dimension keys and label scoring_method by what actually moved

## Context

The middle tier of the three-layer personalization system (explicit +/-30% -> behavioral +/-10% -> session +/-5%) is **dead for 8 of 9 categories**: it emits weight deltas in a legacy universal key space that no category dimension set uses. Worse, the payload still reports `scoring_method: "behavioral"`, so the API tells the client the result was personalized when the weights are identical to the anonymous run. That is a false claim in a documented contract, and it also masks the outage — nothing alerts, because the label is keyed on profile *presence*, not effect. M18 finding `PO-rubric-05`.

> Note for the implementer: this may overlap the pre-M13 2026-08-24 audit's "dead behavior-profile" P1 (issue range #46-#81). Check that set before starting; if an issue already exists, fold this spec into it rather than duplicating.

## Current behavior

**Defect 1 — key-space mismatch.** `app/services/behavior_service.py:11-16` emits sensitivity in the legacy universal space:

```python
TAB_DIMENSION_MAP = {
    "specs": "spec_score",
    "reviews": "review_score",
    "overview": "price_score",   # overview attention correlates with price focus
}
```

`apply_behavioral_adjustments` (`app/services/scoring_service.py:2137-2157`) only builds a delta when the key intersects the **category** dims:

```python
sensitivity = behavior_profile.get("dimension_sensitivity", {})   # :2146
if not sensitivity:
    return weights                                                # :2148
оriginal = dict(weights)                                          # :2150
avg_sensitivity = sum(sensitivity.values()) / len(sensitivity) if sensitivity else 0   # :2151
deltas: Dict[str, float] = {}                                     # :2152
for dim in weights:                                               # :2153
    if dim in sensitivity:                                        # :2154
        deltas[dim] = (sensitivity[dim] - avg_sensitivity) * weights[dim]   # :2155
return self._apply_capped_adjustments(weights, deltas, original, MAX_BEHAVIORAL_SHIFT_RATIO)  # :2157
```

`CATEGORY_DIMENSIONS` (`scoring_service.py:24-61`) contains `review_score` only in `other`; `spec_score` and `price_score` appear in **no** category. Probe: electronics weights come back unchanged with a fully populated sensitivity dict; `other` moves only via the `review_score` name coincidence.

**Defect 2 — the label lies.** `scoring_service.py:1158-1165`:

```python
if behavior_profile or session_signals:
    scoring_method = "behavioral"     # :1159  keyed on PRESENCE, not effect
elif preferences:
    scoring_method = "personalized"   # :1161
elif cohort_applied:
    scoring_method = "cohort"         # :1163  <- not in the documented enum
else:
    scoring_method = "category_weighted"   # :1165
```

Probe: `compute_scores` with a behavior profile returns `scoring_method="behavioral"` with `weights_used` (rounded at `:1115`) identical to the no-profile run. The same branch also **shadows** `"personalized"`: a user with explicit +/-30% prefs *and* any behavior profile is labeled `"behavioral"` even though only the explicit layer moved anything. Two values escape the documented enum: `"cohort"` at `:1163`, and `"default"` emitted by `_empty_result` at `:1911`. The documented enum is `category_weighted` / `personalized` / `behavioral` / `invitee_quiz` — `CLAUDE.md:215` and `.claude/skills/qaren-scoring/SKILL.md:36`.

**Defect 3 (noted, lower blast radius).** `behavior_service.py:65-74` tiers price with flat BHD breakpoints 11 / 57 / 189 (`elif p < 189` at `:71`, `luxury` at `:73-74`), so every electronics comparison above 189 BHD marks the user a `luxury` shopper — while the category-aware scoring tiers put electronics `luxury` far higher (`PRICE_TIERS_BY_CATEGORY`, `scoring_service.py:429`).

## Expected behavior

1. A behavior profile with a populated `dimension_sensitivity` measurably shifts the weights in **every** category, within the existing +/-10% cap.
2. `scoring_method` describes what actually changed the weights, and explicit preferences take label precedence over an inferred profile.
3. A profile that produced no weight change does **not** get labeled `"behavioral"`.
4. Every value the code can emit is in the documented enum — `"cohort"` and `"default"` are either added to the docs or changed to documented values. Code and contract agree.
5. Behavioral price tiering uses the same category-aware breakpoints as scoring.

## Implementation notes

Files to touch: `app/services/scoring_service.py`, `app/services/behavior_service.py`, `CLAUDE.md`, `.claude/skills/qaren-scoring/SKILL.md`.

- **Translate at application time, not at emission time.** Keep `TAB_DIMENSION_MAP` in the legacy space (stored profiles in the DB already use those keys; rewriting the emitter would strand every existing profile). Instead, at the top of `apply_behavioral_adjustments` (`:2137`), map legacy key -> signal -> category dim: `{"spec_score": "spec", "review_score": "review", "price_score": "value"}`, then invert `ScoringService._DIMENSION_SIGNAL_MAP[category]` (`:1503-1549`) to find the dim carrying that signal. The module-level `_scale_value_weight` (`:713`, inversion loop `:720-723`) is the existing pattern — copy it. This requires adding a `category: str = "other"` parameter to `apply_behavioral_adjustments`, exactly as `apply_cohort_adjustments` already declares at `:2163`, which keeps existing callers and tests working unchanged.
- Assumption: `spec_score` maps to the `"spec"` dim **only**, not also `"spec_secondary"`. Splitting one tab's dwell across two dims would double-count the signal inside a +/-10% budget and make the cap meaningless. Single primary dim per legacy key.
- Compute `avg_sensitivity` (`:2151`) over the **translated** dict so the mean is taken over the same three values that produce deltas. Leave `_apply_capped_adjustments(..., MAX_BEHAVIORAL_SHIFT_RATIO)` at `:2157` untouche

## #106 [closed] [fact-check] normalize shopping-row currency before the price cross-check

## Context

M18 review, finding **PO-fact-check-01**. `verify_price` is the zero-cost guard that is supposed to catch a wrong price before we show it. It is currency-blind: it strips shopping price strings to bare numerals and compares them to the final BHD amount. Because the GCC `gl=<country>` shopping leg is a known-empty leg that is no longer purchased (`_shopping_primary_countries()` returns an empty frozenset when `SERPER_SHOPPING_PRIMARY_COUNTRIES` is unset, which is the default — `serper_service.py:687`, `:710-717`), the rows it compares against are predominantly `gl=us` USD. The check therefore **passes the exact wrong-currency class the whole correctness program exists to kill, and flags the correct conversions as unverified**.

## Current behavior

`app/services/fact_check_service.py:137-177`:

```python
for item in shopping_items:                      # :151
    p = item.get("price")
    if isinstance(p, (int, float)) and p > 0:
        shopping_prices.append(p)
    elif isinstance(p, str):
        nums = re.findall(r'[\d.]+', p.replace(',', ''))   # :156 — bare numerals, zero currency handling
        ...
median = sorted(shopping_prices)[len(shopping_prices) // 2]           # :170
deviation_pct = abs(final_amount - median) / median * 100 if median > 0 else None
return {
    "price_verified": deviation_pct is not None and deviation_pct <= 30 and not price.get("estimated", False),  # :174
    ...
}
```

Call site: `app/services/structured_comparison_service.py:4921-4922`:

```python
shopping_items = self._shopping_items_cache.get(full_name, [])
result["_price_verification"] = verify_price(result.get("price"), shopping_items)
```

Thin wrapper `_verify_price` at `:2621-2622` (this is the entry point every test in `tests/test_fact_checking.py` uses, via the `service` fixture at `tests/test_fact_checking.py:16-18`).

Measured offline against the real function (no network, no paid calls):

| final price | shopping rows | `price_verified` | `deviation_pct` | correct? |
| --- | --- | --- | --- | --- |
| `1399` stamped `BHD` (raw AED amount) | AED rows | **true** | 0.0% | wrong — endorses the defect |
| `142.9` BHD (the correct conversion of those rows) | same AED rows | **false** | 89.8% | wrong — flags the right answer |

Production corroboration (SELECT-only spot-check): recorded row `2bf16403-9ce1-4da7-9ca5-ddac4fd7c3bf` carries genuine `local_bhd` prices 450.82 / 292.33 BHD with `price_verified=false` at 75.6% / 67.1% deviation against the USD-numeral median.

The 30% tolerance at `:174` cannot rescue this — a USD/BHD basis mismatch is ~2.65x and an AED/BHD one ~9.8x, both far outside it, so the verdict is systematically inverted rather than noisy.

## Expected behavior

- Every shopping row is converted into the final price's own currency before the median is taken, using the same currency detection the pricing tier already uses.
- A wrong-currency final price (raw AED/USD amount stamped BHD) comes back `price_verified=False` with a large deviation.
- A correctly converted final price against foreign rows comes back `price_verified=True` with a small deviation.
- When no row's currency can be resolved, the function returns **no verdict** (`price_verified: None`) rather than a confident wrong one.
- Flag OFF, the returned dict is byte-identical to today's for every input.

## Implementation notes

**Files to touch**
- `app/services/fact_check_service.py` — `verify_price` (`:137-177`).
- `tests/test_fact_checking.py` — extend `class TestVerifyPrice` (`:322`).

**Pattern to copy — `price_service.extract_price_from_shopping` (def at `:9397`), specifically `:9455-9490`.** That function already solves exactly this problem on the same rows:

```python
detected_cur = detect_currency(price_str)                          # :9455
...
amount = parse_price_string(price_str, detected_cur, display_text=True)   # :9475
...
if detected_cur and detected_cur != currency:                      # :9485
    amount = _convert_to_bhd(amount, detected_cur)
    if currency != "BHD":
        bhd_rate = _convert_to_bhd(1.0, currency)
        if bhd_rate > 0:
            amount = amount / bhd_rate
```

Mirror it row-for-row. Import lazily inside the function (`from app.services.price_service import detect_currency, parse_price_string, _convert_to_bhd`) — `fact_check_service` is deliberately dependency-light (its only imports today are `re`, `logging`, `typing`) and a module-level import of `price_service` would pull the whole pricing stack into every importer.

**Contract**
- Target currency = `price.get("currency") or "BHD"`.
- Numeric `item["price"]` (no string to inspect): treat as already in the target currency, as today.
- String row: `detect_currency` → `parse_price_string(..., display_text=True)` → convert if the detected currency differs from the target. Passing the detected currency into `parse_price_string` also fixes a second latent bug — `re.findall(r'[\d.]+', ...)` at `:156` takes the FIRST numeral run of a comma-stripped string, so `"BHD 12.500"` and price-range strings parse wrong today.
- Row whose currency cannot be resolved **and** whose numeral is ambiguous: **drop it** from the median rather than assume the target currency.
- Zero usable rows survive → return the existing no-usable-rows shape at `:161-166` (`price_verified = not price.get("estimated", False)`, `deviation_pct None`, `source_count 0`).
- Rows survive but from **mixed unresolvable currencies** → return `price_verified: None`, `deviation_pct: None`, `source_count: <n>`.

**`None` is safe for every existing consumer — audited at `593ec1e`:**
- `build_fact_check:195` is `price_verification.get("price_verified", False)`; the key exists with value `None`, so `fact_check["price_verified"] = None` (no crash, no coercion to `False`).
- `ScoringService._score_reliability` (`scoring_service.py:1436`, class `ScoringService` at `:1037`) line `:1457` is 

## #107 [closed] [fact-check] carry spec citation confidence across the specs cache so the citation layer runs on warm traffic

## Context

M18 review, finding **PO-fact-check-02**. Spec-citation verification is the advertised layer that decides whether a spec was actually cited from a search snippet or invented. It is dead on every cache hit — and with a 7d L1 / 30d L2 specs TTL, cache hits are the normal case. A SELECT-only spot-check of the 12 most recent `schema_version=2` comparisons (all `metadata.cached=true`) shows `specs_verified=0` **and** `specs_likely=0` on all 24 product sides. The layer produces nothing in production, and everything downstream that reads it (`ScoringService._score_reliability`, the specs confidence pill) is scoring against a constant.

## Current behavior

In `app/services/structured_comparison_service.py::_get_specs` (`:4960-5034`):

- `:5021-5030` writes the specs dict to L1 (and fires the L2 save) — **before** `:5032` attaches `specs["_search_snippets"] = raw_snippets`.
- The L1 cache-hit early return at `:4966-4969` and the L2 restore at `:4972-4979` therefore return a dict with **no `_search_snippets` key**.
- The enriched re-cache at `:4861-4874` explicitly strips the key (`:4865`).

On the fact-check pass, `:4681-4693`:

```python
raw_specs = result["specs"]
search_snippets = raw_specs.pop("_search_snippets", [])   # :4683 → [] on every cache hit
citation_confidence = verify_spec_citations(raw_specs, search_snippets)   # :4684
...
result["_spec_confidence"] = spec_confidence               # :4693
```

`fact_check_service.verify_spec_citations:36-38` then evaluates `0 <= idx < len(search_snippets)` against an empty list, so every `snippet_N`-cited field falls to the `else` at `:63-64` and is marked `"unverified"`. `build_fact_check` (`fact_check_service.py:180`, called at `structured_comparison_service.py:4952`) counts zero verified, zero likely.

Recorded rows `9a24786f`, `2bf16403`, `289eb5e9` and nine more: `specs_verified=0`, `specs_likely=0`, 24/24 sides.

One nuance that does not change the verdict: the L2 save at `:5027-5030` is fire-and-forget on the same dict object and typically runs *after* `:5032`, so an L2-restore path can carry stale snippets from a previous request — which is worse than useless (it would verify this request's citations against another request's snippets). The dominant 7d L1 path returns none at all.

## Expected behavior

- A warm (cached-specs) comparison produces the same per-field spec confidence a cold one does, with no extra API call.
- `fact_check.specs_verified + specs_likely` is non-zero on a warm comparison whose specs carry `snippet_N` sources.
- Citations are never scored against a *different* request's snippets.
- Flag OFF, both cold and warm paths are byte-identical to today.

## Implementation notes

**Approach: persist the derived citation-confidence map, not the raw snippets.** Reason it beats caching `_search_snippets`: the snippet digest is up to 3000 chars per product and would be written to Redis *and* to the `product_specs` JSON column on every save, for a value that is only ever consumed to produce a small `{field: "verified|likely|unverified|flagged"}` map. Caching the derived map is far smaller, removes the recompute entirely on warm traffic, and — decisively — makes it **impossible** to score this request's citations against another request's snippets, which is the failure mode the fire-and-forget L2 write at `:5027-5030` can otherwise produce.

**Name the cached key `_spec_citation_confidence`, NOT `_spec_confidence`.** Reason: `_spec_confidence` is already taken as a **product-level** key — set at `structured_comparison_service.py:4693` on `result` and popped by `fact_check_service.build_fact_check:186` off `product`. The new key lives in a *different* dict (`result["specs"]`) and holds the pre-shopping-merge citation verdicts only. Reusing the name would make every grep ambiguous and invite an implementer to pop the wrong one.

**Precedent to copy**: `_field_confidence` is already an underscore-prefixed derived map that lives inside the cached specs dict — created by `_clean_specs` (`:2558`, re-attached at `:2589-2590`), extended at `:4840`, deliberately *not* in the enriched re-cache's strip list at `:4865`, and filtered out of the API response by `response_builder.py:441` (`if field in _SPEC_INTERNAL_FIELDS or field.startswith("_")`). `_spec_citation_confidence` follows the identical lifecycle.

**Files to touch**
- `app/services/structured_comparison_service.py`
  - `_get_specs` (`:4960-5034`): after `search_context, raw_snippets = ...` (`:4994`) and after the spine merge (`:5018-5019`), compute `specs["_spec_citation_confidence"] = verify_spec_citations(specs, raw_snippets)` **before** the cache write at `:5021`. `verify_spec_citations` is already imported at `:1057`.
  - **`_clean_specs` (`:2549-2591`) — the trap.** Line `:2578` (`if key.startswith("_"): continue`) strips ALL underscore keys, and only `_field_confidence` is re-added (`:2589-2590`). `result["specs"] = self._clean_specs(result["specs"])` runs at `:4695-4696`, i.e. AFTER the fact-check block reads the key but BEFORE the enriched re-cache at `:4861-4874` reads `result.get("specs")`. Without a fix, an enriched re-cache would **overwrite a good cache entry with one missing the key**, silently re-killing the layer for that product. Add `_spec_citation_confidence` to the re-add path next to `_field_confidence` (carry it through from the input dict, do not recompute).
  - Fact-check pass (`:4681-4693`): prefer a cached `raw_specs.get("_spec_citation_confidence")` when it is a non-empty dict; fall back to computing from the popped `_search_snippets` when absent (cold path and any legacy cache entry). Use `.get`, not `.pop` — `_clean_specs` removes it from the display dict anyway and the re-cache needs it. Keep the shopping-flag merge at `:4685-4692` exactly as-is — it must still run per request against fresh shopping rows.
  - Enriched re-cache (`:4861-4874`): leave `_spec_citation_confidence` in the persiste

## #109 [closed] [scoring] wire fact_check verification into the confidence pills

## Context

M18 review, finding **PO-fact-check-04**. The three confidence pills are what a user reads to decide how much to trust the answer. On every recorded row they are uncorrelated with the fact-check's own truth signals, because the two systems are not wired together: unverified spec fields are counted as "citations", so any product with four spec fields can never show a weak specs pill; and the price pill never reads `price_verified` at all, so a comparison can ship a **strong** price pill while its own fact-check recorded `price_verified=false` at 75% deviation. The answer to *"does high confidence correlate with truth"* is currently **no** — by construction.

## Current behavior

**Specs leg counts unverified fields as citations.** `app/services/scoring_service.py:828-834`:

```python
verified   = int(fc.get("specs_verified") or 0)
likely     = int(fc.get("specs_likely") or 0)
unverified = int(fc.get("specs_unverified") or 0)
flagged    = int(fc.get("specs_flagged") or 0)
total = verified + likely + unverified + flagged
verified_pct = round((verified / total) * 100) if total > 0 else 0
return verified_pct, total          # ← `total` is returned as citation_count
```

`compute_confidence:894-895`:

```python
specs_strong     = best_pct >= 40 or best_citations >= 8
specs_acceptable = best_pct >= 20 or best_citations >= 4
```

So `citation_count` is really "number of spec fields", and ≥4 fields guarantees at least `acceptable` regardless of verification. Recorded row `289eb5e9` renders specs **strong** with `verified_pct=0` and all 11 fields unverified; all 12 spot-checked rows are acceptable-or-strong at 0% verified.

**Price leg never reads the fact-check.** `compute_confidence:882-885`:

```python
any_trust_method = any(_product_source_method(p) in _PRICE_TRUST_SET for p in products)
max_shopping = max((_product_shopping_count(p) for p in products), default=0)
price_strong = any_trust_method or max_shopping >= 3
price_acceptable = max_shopping >= 2
```

`fact_check.price_verified` / `price_deviation_pct` appear nowhere in the function (`:846-940`). Recorded row `2bf16403` ships a **strong** price pill while its own fact_check has `price_verified=false` with 75.6% / 67.1% deviations.

These legs reach the client verbatim through `response_builder._confidence_legs_and_details` (`:870-922`) → `scoring_v2.confidence_legs`.

## Expected behavior

- The specs pill reflects how much was actually verified, not how many fields exist.
- A product whose own fact-check says the price contradicts the cross-check cannot render a **strong** price pill.
- A genuine, verified comparison keeps its strong pills — no across-the-board downgrade of honest results.
- Flag OFF, `compute_confidence` returns byte-identical output for every input.

## Implementation notes

**Files to touch**
- `app/services/scoring_service.py` — `_product_fact_check_pcts` (`:819-834`), `compute_confidence` (`:846-940`).
- `tests/test_confidence_thresholds.py` — extend; it already has the lazy-import helper `_compute_confidence` (`:19-28`) and is the home of the § 5a threshold contract.

**Specs half.** Change `_product_fact_check_pcts` to return `verified + likely` as the citation count (keep `verified_pct` computed over the full `total` — the denominator is still "fields we tried to verify"). Reason this beats re-thresholding on `verified_pct` alone: the `>= 8` / `>= 4` thresholds were written to mean "enough citations to trust", and `likely` is a real citation that merely could not be fully cross-checked; counting `unverified` and `flagged` as citations is the actual defect. Leave the `"verified_pct" in fc or "citation_count" in fc` early-return branch at `:826-827` untouched — it is an external contract for a differently-shaped payload.

**Price half.** After computing `price_strong` / `price_acceptable` at `:884-885`, demote when the fact-check contradicts:

- if ANY product has `fact_check.price_verified is False` AND `fact_check.price_deviation_pct is not None` AND `>= 30` (the check's own tolerance, `fact_check_service.py:174`) → cap the price leg at `"acceptable"`.
- `price_verified is None` (the unknown verdict introduced by PO-fact-check-01) must NOT demote — unknown is not contradiction. Note this requires an explicit `is False` identity test, not a falsy test.
- `price_deviation_pct is None` must NOT demote — there were no comparable rows.

Read the fact-check through a small helper placed next to `_product_fact_check_pcts` so the `fc = p.get("fact_check") or {}` / `isinstance` defensiveness at `:823-825` is reused rather than re-written.

**Feature flag: `ENABLE_CONFIDENCE_FACTCHECK_WIRING`, default OFF.** Read PER CALL via `os.getenv` (copy the `price_service.exact_gate_enabled()` idiom at `price_service.py:4033-4037`). Flag OFF: `_product_fact_check_pcts` returns `total` and the price demotion block is skipped — byte-identical. Reason for a flag: this is the highest-blast-radius item in the group (it changes a pill on every comparison, in both directions), and it must not be flipped before its two upstream dependencies.

**⛔ HARD ACTIVATION ORDER — do not flip this flag until both are on and canaried:**
1. `ENABLE_SPEC_CONFIDENCE_CACHE` (PO-fact-check-02). Until it is on, `specs_verified + specs_likely` is **0** on every warm comparison, so the specs half of this change would render a weak specs pill on essentially all production traffic. That would be *honest*, but it is a whole-product UX change, not the correlation fix this issue asks for.
2. `ENABLE_FACTCHECK_CURRENCY_NORMALIZATION` (PO-fact-check-01). Until it is on, `price_verified=False` fires on **correct** genuine BHD prices compared against USD shopping rows, so the price demotion would punish exactly the prices the correctness program produces.

Record both in the ACTIVATION-ORDER runbook alongside the existing wave couplings.

**Adjacent unit, do not merge**: PO-fact-check-0
