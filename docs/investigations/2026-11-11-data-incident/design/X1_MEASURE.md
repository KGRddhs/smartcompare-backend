# INC-X1 SIZE-FAIRNESS - MEASURE (read-only round, 2026-11-11)

Unit: INC-X1 (incident report item 4 / fix X1). Role: the measurer. Round class: READ-ONLY. No pytest, jest, tsc, eslint, network, package manager, production probe or .env read was run; every claim below is read from the plain source exports and the record copy. Nothing in this file says a production problem is fixed: X1 is not built, and even once merged it is "merged, NOT yet proven" until the owner's phone shows it (H6).

Sources read (the line numbers of the exports equal the lines at the sha):
- Backend and OTA client at main a74caba7: `<SP>/src/a74caba7/app/` and `<SP>/src/a74caba7/SmartCompareApp/src/` (client = the live OTA bundle f1e20c39). Short names below: PS = app/services/price_service.py, SCS = app/services/structured_comparison_service.py, RB = app/services/response_builder.py, SS = app/services/scoring_service.py, ES = app/services/extraction_service.py, KI = app/services/kb_ingest.py, RG = app/services/result_gate.py, HR = app/api/home_routes.py.
- Store binary JS 683f56c0: `<SP>/src/683f56c0/SmartCompareApp/src/`. Client paths below are relative to `SmartCompareApp/src/`, with the bundle named as `@683f56c0` or `@a74caba7`.
- Record: incident/INCIDENT_AND_DATA_PLAN_2026-11-11.md (IR), incident/T1_trace.md (T1), T2_field_sources.md, T4_result_page.md, s80/PLAN_S80.md section 0, CLAUDE_md_a74caba7.txt lines 579-582 (D20 and stated limit L3).

Incident facts this unit answers (from the record, not re-measured): Layton 85.000 BHD (alibaksh.com, woo_store_api) and YSL Libre 39.000 BHD (fragrancebh.com, woo_store_api) were found and then pended with `price.reason = "size_mismatch"`; Armani's only price was a parked converted_usd GiftBlooms 40 ml fallback (US shopping region, variant_rank 0.0) after a 15 s price-race timeout, also pended (T1 section 4; IR line 38). The exact off-target sizes (125 ml for Layton, 90 ml for Libre) are LIKELY only (IR line 175); the listing titles were not persisted.

## 1. THE PATH AT MAIN

### 1.1 Callers

| Caller | Where | Order around it |
|---|---|---|
| Sync compare | SCS:4586-4594: `reconcile_pair_fairness(product_data, query, category_used, candidates_by_name=self._price_candidates)` in try/except (a failure only logs, SCS:4593-4594) | after the INSUFFICIENT_DATA refusal (SCS:4560-4572); before `apply_prescoring_showable_guard` (SCS:4605-4608), `compute_scores` (SCS:4646), `generate_comparison` (SCS:4677), `apply_value_badges` (SCS:4747), `build_comparison_response` (SCS:4783), `_kb_ingest_tail` (SCS:4878) |
| Streaming compare | SCS:5339-5345, the same call | before the `prices` SSE event (SCS:5435), `compute_scores` (SCS:5497), `generate_comparison` (SCS:5538), `apply_value_badges` (SCS:5595), `build_comparison_response` (SCS:5676), `_kb_ingest_tail` (SCS:5797) |
| `reconcile_pair_fairness` | PS:3301; canonical "fragrances" delegates verbatim to `reconcile_pair_sizes(..., treat_unsized_as_flagship=frag_reconcile_fix_enabled())` (PS:3346-3351) | non-fragrance pairs use `_mark_unit_pending` / reason `unit_mismatch` (PS:3166-3180), out of X1 scope |

No other caller of `reconcile_pair_sizes` exists in app/ (grep: only PS:3347 plus comments). `app/api/text_routes.py:1760-1790` imports `make_pending_price` for the single-product KPI endpoint and never reconciles. The partial-response builder (`_build_partial_response`, SCS:3798; body at SCS:3880) reads `self._partial_product_data`; whether that is the same list object the reconcile mutates in place is UNVERIFIED in this round.

### 1.2 Flags and knobs on the path (defaults at a74caba7)

| Name | Default | Read at | Effect on this path |
|---|---|---|---|
| ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX | OFF | PS:4905-4923, per call | ON: an unsized product on the fragrance path defaults to the 100 ml basis even when its name is not brand-keyword-recognized (PS:2091-2096, PS:2148-2152). T1 says the variable name is set on web; its value is not established and is not probed here (H2). |
| ENABLE_FAIRNESS_IGNORE_ESTIMATE | ON | PS:4926-4938 | an estimate on either side makes the reconcile a no-op (PS:2318-2321) |
| ENABLE_EXACT_PRICE_GATE | ON | PS:4370-4374 | in `reselect_to_target_size` skips out-of-stock and concentration-mismatch candidates (PS:2228-2233); governs `public_price_view` (PS:9382-9387) |
| `_FRAGRANCE_FLAGSHIP_SIZE_ML` | 100.0, a constant, not env | PS:1439 | the flagship target |
| `_CONTINUOUS_TOLERANCE` | 0.15 | PS:2693; fragrance spec PS:2771-2783 | NOT applied by `reconcile_pair_sizes`: 90 ml vs 100 ml is an exact-equality mismatch (PS:2340, PS:2364) |
| ENABLE_PRESCORING_SHOWABLE_GUARD | OFF | after the reconcile (SCS:4605) | never touches a size pend |
| ENABLE_REGION_CURRENCY_GUARD | OFF | RB:1717-1736 | sits after the `unavailable` early continue (RB:1715-1716), so never touches a size pend |

### 1.3 The functions

- `effective_pair_size_ml(product, treat_unsized_as_flagship)` (PS:2048-2097): scans, in this order, `full_name`, `name`, `price.title`, `price.size`, then `specs.volume / size / concentration` (`_product_size_text_fields`, PS:2021-2045) for a `\d+ml` token (`extract_sizes_ml`, PS:4087-4093: millilitres only, no oz) and returns the SMALLEST token; else 100.0 for a designer/niche fragrance name (`_is_designer_fragrance_name`, PS:2100-2111); else 100.0 when `treat_unsized_as_flagship`; else None. The product NAME comes first, so a size in the name beats the listing's own size.
- `target_pair_size_ml(user_query, p0, p1, treat_unsized_as_flagship)` (PS:2114-2153): an explicit `\d+ml` in the user query (smallest); else 100.0 when both names are designer fragrances; else 100.0 when the fix flag is ON; else None.
- `reselect_to_target_size(product_name, candidates, target_ml, currency)` (PS:2170-2256): keeps a candidate only when `_candidate_size_ml` (PS:2152-2167: `raw_data.size`, `raw_data.title`, then the candidate's `size`, `title`) equals the target exactly, it is in stock and concentration-consistent (gate ON, PS:2228-2233), and `is_price_showable(product_name, price)` passes (PS:2240); ranks genuine-BH first, then `variant_rank`, then cheapest (PS:2248-2255). No network.
- `reconcile_pair_sizes(product_data, user_query, candidates_by_name, treat_unsized_as_flagship)` (PS:2259-2399): a no-op unless BOTH prices carry a positive amount (PS:2299-2309) and neither is an estimate (PS:2318-2321); a no-op when no size was typed and both effective sizes are equal (PS:2338-2341); target None -> both pended on any divergence (PS:2348-2354); else each side is resolved to the target, re-selecting from `candidates_by_name` (PS:2359-2381). Outcome 1, both at target: both shown (PS:2386-2389). Outcome 2, one at target: only the other pended (PS:2390-2395). Outcome 3, neither: both pended (PS:2397-2398). Returns True iff a price changed.
- `_mark_size_pending(*products)` (PS:2402-2417): replaces `price` with `make_pending_price(currency, reason="size_mismatch", size=price.get("size"))` and nulls `best_price` and `retailer` when those keys exist. The found amount, retailer, url, title and source_method are DISCARDED; the size survives only when the price dict had a `size` key. Measured consequence: the Layton row's pending price has no `size` (T1: `{"amount":null,"reason":"size_mismatch","unavailable":true}`), so the off-target size came from the title and was lost; Armani's survived (`"size":"40ml"`) because a Serper shopping candidate carries `size` (PS:10587-10588).
- `make_pending_price(currency="BHD", reason="pending_genuine", size=None)` (PS:2005-2018). The exact pending shape:

```
{"amount": null, "currency": "<currency, default BHD>", "unavailable": true, "reason": "<reason>"}
plus "size": "<string>" only when size is truthy
```

### 1.4 Where `candidates_by_name` comes from and what a candidate carries

`self._price_candidates` (declared SCS:3364-3370; reset per request at SCS:4331 and SCS:5051), keyed by `full_name`.

| Writer | Where | Candidate keys |
|---|---|---|
| Tier 1.5 fan-out, curl and render waves | SCS:8656-8670 retains `fan_out_price_lookup`'s `best` + `alternates` (PS:17143-17277) | the scraper candidate dict. The reconcile reads only `raw_data.size`, `raw_data.title`, `size`, `title`, `value`, `source_method`, `retailer`, `variant_rank`, `in_stock` (PS:2152-2255). The full scraper candidate shape is UNVERIFIED in this round. |
| Short-circuit seeds, `_seed_shortcircuit_candidates` (SCS:9557-9746), called from the KB path (SCS:6078) and the shopping / Shopify / Algolia / BH-adapter short-circuits (SCS:7815, 7841, 7860, 8027, 8171, 8268); the BH adapter direct hit that found Layton and Libre seeds at SCS:7860 just before its log line | normalized at SCS:9735-9742 | `value`, `size`, `source_method`, `retailer`, `title`, `variant_rank`, `raw_data` (= the whole price dict). Only a price passing `is_price_showable(full_name, price)` enters (SCS:9732). Shopping items are shaped at SCS:9690-9717 (amount, currency, source_method, retailer, url, title, size). |
| Serper shopping candidate | PS:10573-10589 | amount, currency, retailer, url, in_stock, source_method, confidence, match_score, retailer_score, title, `variant_rank` (concentration rank + size rank + flagship bonus, PS:10586), concentration, `size` (smallest ml in the title + "ml") |

Region: no candidate carries a region field. Region appears only through `source_method` (a `gl=us` fallback stamps `converted_usd`, SCS:9597-9599 and PS:10544-10565) and through the registry-tier test in `_is_genuine_bh_candidate` (PS:17090-17105; the genuine set `_GENUINE_BH_SOURCE_METHODS`, PS:17065-17087, includes `woo_store_api`, the method of the Layton and Libre hits). The Armani parked price is `converted_usd` from the US shopping region (T1 C3).

## 2. DOWNSTREAM: every consumer of a pending / size_mismatch price

Ordering fact: the reconcile runs BEFORE scoring, the verdict call and the builder (section 1.1), so every consumer below sees the pending shape, never the found amount.

### 2.1 response_builder (RB)

| Surface | Where | What a size_mismatch price does there |
|---|---|---|
| Price chokepoint | RB:1636-1771 | an already-pending price takes the early `continue` (RB:1711-1716): its reason `size_mismatch` is kept, no `guard_rejected` diag is added |
| `overview.products[i].price` (new shape) | RB:1951 `public_price_view(pd.get("price"))` (PS:9371-9387 strips `guard_rejected` and `_`-keys only) | ships the pending dict as is |
| `products[i]` (legacy flat alias) | RB:2255-2268: the raw product dicts, price re-projected at RB:2263-2264 | ships `price` (pending), `best_price: null`, `retailer: null`; product-level `_`-keys are NOT stripped except those popped by name (RB:2267) |
| `overview.products[i].value_badge` | RB:1958 (default `fair_price`), set by `apply_value_badges` (SS:2671-2704; SCS:4747) | ENABLE_CATEGORY_VALUE_BADGE OFF: a badge is computed for the price-missing side too, from `value_score` default 50 and tier `mid` (SS:2700-2704); ON: no badge when the value dim is absent (SS:2696-2699). Neither client bundle reads `value_badge` (grep: only `types/types.ts`). |
| Confidence | RB:1781-1800 (W4-7 flag): any pending price forces the price leg to `weak`; RB:1205-1240 legs and per-side `method_p0/p1` | price leg weakened |
| Price-adjective drop (C3) | RB:1849-1871 | pros/cons asserting a price adjective are dropped for the pending side |
| Factual verdict line 1 / line 2 | `_safe_price_amount` RB:842-852; `_price_candidate` RB:873-894 (None when either amount is missing); price sentences RB:1085-1089 ("comes in N% cheaper", "carries a N% price premium"); `_format_line2` price fallback RB:1101-1131 | no price fact can be emitted |
| `scoring_v2.dimensions` price / value | built from the post-chokepoint product data (RB:1642-1644 comment) via SS:3240-3270 `_dim_price` and SS:3314 `_dim_value` | `_dim_price`: either amount <= 0 -> both 75, delta "Price data unavailable", confidence low, `caption_key: limited_data` (SS:3243-3248) |
| `metadata.section_status.price` | RB:2322-2329 under ENABLE_RESULT_STATUS_METADATA (RG:86-88); RG:455-474, `price_is_showable` RG:213-224 | `partial` (one side) or `unavailable` (both) |

There is no `price_comparison` / `price_difference` key emitted by the builder at a74caba7 (grep of RB and SCS finds none); the client types declare one (`types/types.ts:147-151 @683f56c0`) that nothing fills.

### 2.2 scoring_service (SS)

| Step | Where | Effect of a pending price (amount null) |
|---|---|---|
| Raw price signal | SS:1768-1778 `_compute_raw_scores` | `price_raw = None`, `_price_missing = True` |
| Price normalization | SS:2449-2469 `_normalize_price` (lower is better, ratio between the pair's min and max) | `MISSING_SCORE` for the missing side (SS:2458-2459); the lone priced side scores 75.0 because one price gives max == min (SS:2465-2467) |
| Value signal | SS:318-333 `_signal_missing_for("value")` = spec OR price missing; SS:1256-1309 `_compute_value_score` | the value dimension is missing for the pending side |
| Fragrance dimensions that read price | the signal map SS:2178: `wear_value_score -> value`; weights SS:72 (`wear_value_score` 0.10) and priority shifts SS:143-150, SS:224-228 | `wear_value_score` lands in that product's `scoring.scores.product_i.missing_data` (SS:1543, SS:2596); a missing dim is filled with the 50 default (T1 C1: wear_value 75 vs 50 decided the C1 winner by margin 1.4) |
| Price authority | SS:810-840 (`_price_authority_delta`), trust set SS:740-760 | reads the price's source_method; a pending dict has none |
| v2 dimensions | SS:3240-3270 `_dim_price`; SS:3314 `_dim_value` (it reads `_get_price` at SS:3328-3329; `_get_price` SS:3171-3175) | `limited_data` rows, which both bundles hide (`DimensionBars.tsx:82-88`) |
| Confidence | SS:1150-1253 `compute_confidence` | price leg from the listing counts and methods; RB:1781-1800 then weakens it when a price is pending (flag W4-7) |

### 2.3 The verdict prompt inputs

`generate_comparison` (ES) dumps each product into the prompt after `_verdict_safe_product` (ES:2466-2534, applied at ES:2631-2632). That projection strips `fact_check` and every product-level `_`-key (ES:2506-2510) and, for a non-showable price (a pending one included), swaps in `make_pending_price(currency, reason, size)` (ES:2529-2532). So the model sees `{amount: null, unavailable: true, reason: "size_mismatch", size?}` and no amount. A product-level `_`-prefixed stash would never reach the prompt; a new public key on a SHOWABLE price would (the showable side is passed through unchanged, ES:2522-2525).

### 2.4 The field-status metadata (D05, dormant)

`KI:165-248 _status_one`, stamped as `metadata.field_status` only under ENABLE_FIELD_STATUS_METADATA (KI:86-88; SCS:3930-3965 `_kb_ingest_tail`). For a size_mismatch pend: `price` -> `{"state": "unknown", "source": null, "reason": "no_price", "as_of": null, "rung": null}` (KI:193-207, because `RG.price_is_showable` refuses `unavailable`, RG:221); `size` -> `known / listing` only when `price.size` matches `\d+ml` (KI:147-152, KI:210-211), which the Layton pend lacks. Section status (RB:2322-2329, ENABLE_RESULT_STATUS_METADATA) reports `price: partial` for the incident pairs (RG:467, RG:472).

MEASURED LATENT DEFECT (independent of X1, dormant): when ENABLE_FIELD_STATUS_METADATA flips, the OTA bundle turns that `unknown` into the honest line "Not listed by the stores we can read yet" in place of the amount (`services/fieldStatusView.ts:45-58 @a74caba7`, `price.unavailable === true` + field unknown -> `kind: 'unknown'`; `components/results/ResultsContent.tsx:366-373 @a74caba7`). For Layton and Libre that sentence is FALSE: a store we read DID list the perfume, at another size. X1 must change the D05 price entry for a size pend (section 5).

### 2.5 The saved row, Home and Profile

- The saved row (`comparisons.full_response`) is the built response body; it carries both `overview.products[i].price` and the legacy `products[i].price` / `best_price` / `retailer`, so a size pend is stored as the pending dict with `reason: size_mismatch` (T1 rows 441e7b7d, 5b369372, e2320ca7). The found amount, store and listing title are not stored anywhere in the row (section 1.3).
- Home savings (`GET /home/savings`, HR:200-300) and the Profile monthly stats (`app/api/profile_routes.py:335-346`) read `full_response.products[winner/loser].price.amount` through `_extract_winner_loser_prices` (HR:167-192) and add `max(0, loser - winner)`; a row with a null amount is skipped (HR:284-290). Under ENABLE_HOME_SAVINGS_AGGREGATE (HR:59-66, OFF by default) the same sum comes from the migration-036 RPC `home_savings_aggregate` (HR:95-110); its SQL is not in the export and is UNVERIFIED here. CONSEQUENCE FOR X1: any design that puts an off-size amount into `price.amount` turns a cross-size difference into "savings" on Home and Profile.
- The `prices` SSE event (SCS:5400-5435) re-projects each price through `public_price_view` and keeps an already-pending reason; both bundles use that event only as a time-to-first-byte marker (`screens/HomeScreen.tsx:425 @683f56c0`, `:471 @a74caba7`; `services/api.ts:880 @683f56c0`, `:959 @a74caba7`).
- The Redis/L1 response cache stores whole bodies (T1: `cached: true`); a flag flip does not rewrite a cached body (its TTL is UNVERIFIED in this round).

## 3. BOTH CLIENT BUNDLES

### 3.1 The component chain that renders a product price

| Step | @683f56c0 (store binary 1.0.0 (3)) | @a74caba7 (= OTA f1e20c39) |
|---|---|---|
| Products source | `screens/ResultsScreen.tsx:408-410`: `overview.products ?? products ?? []` | `screens/ResultsScreen.tsx:431-433`, the same |
| Hero card loop | `components/results/ResultsContent.tsx:260` | `ResultsContent.tsx:313`; per card `prov = provenanceFor(product.price, idx)` (`:315`, `:149-155`) |
| Price text | `formatPrice` `ResultsContent.tsx:135-153`, rendered at `:313-322` | `formatPrice` `:188-206`, rendered at `:375-386` unless `prov.kind === 'unknown'` (`:367-374`, the honest line) |
| Amount format | `utils/formatNumber.ts:96` (`formatPrice(amount, currency, t)`, BHD 3 decimals, app digit policy) | the same file and line |
| Provenance lines | none | `renderProvenanceLine` `:156-185` (as of / last seen / listed on / checked earlier), `:387` |
| Converted caption | `:327-336` | `:392-400` (also suppressed when `prov.kind === 'unknown'`) |

### 3.2 What is shown

| Price state | @683f56c0 | @a74caba7 with no field_status / as_of in the body (every body today) |
|---|---|---|
| Normal genuine price | "85.000" plus the BHD symbol from `formatNumber.ts:96` | identical (`prov.kind` = `none`, D20 OFF identity, CLAUDE.md:579 RB-S11-4) |
| converted_usd price | the amount + " (converted from USD)" / "(محول من الدولار)" inside the price line (`:151`) AND a second caption line with the same key (`:327-336`): the label is shown twice (measured, a cosmetic defect, not X1) | the same twice-label (`:204`, `:392-400`) |
| Pending, ANY reason (`price.unavailable === true`) | `results.price.pending`: en "No confirmed price yet." (`i18n/en.json:156`), ar "لا يوجد سعر مؤكد بعد." (`i18n/ar.json:153`), muted style `productPriceUnavailable` (`:316-318`, `:704`) | the same key (`en.json:149`, `ar.json:146`). If ENABLE_FIELD_STATUS_METADATA is ON and the D05 price entry is `unknown`: "Not listed by the stores we can read yet" / "غير مذكور بعد لدى المتاجر التي نتابعها" (`en.json:705`, `ar.json:702`) instead |
| price null, or amount null without `unavailable` | `results.priceNA` "Price N/A" / "السعر غير متوفر" (`:142`; `en.json:155`, `ar.json:152`) | the same (`:195`; `en.json:148`, `ar.json:145`) |

`price.reason` is never read by either bundle (grep: `size_mismatch` appears only in the comments `ResultsContent.tsx:137 @683f56c0` and `:190 @a74caba7`), so `size_mismatch` and `pending_genuine` render identically.

Consequences of a pending price on the rest of the page (both bundles): `pricePending = products.some(p => p.price?.unavailable === true)` (`:159 @683f56c0`, `:212 @a74caba7`) drops the `price` and `value` bars (`:488-494` / `:555-561`) and hides the price confidence pill (`:526` / `:593`, with `ConfidencePills.tsx`). `DimensionBars.tsx:82-88` (both) also drops any `limited_data` row. `ResultsScreen.getPriceDiff` ("percent less") is computed (`:678-686` / `:717-725`) but its result `priceDiff` (`:697` / `:736`) is never rendered: no client-side cheaper claim exists in either bundle.

### 3.3 Is a bottle size ever shown next to a price?

No, in neither bundle. `price.size` is not read anywhere in either client (grep of both `src/` trees, tests excluded). The only size near the price is the hero-card variant line, prop `product.variant`, rendered when truthy (`ResultsContent.tsx:304-312 @683f56c0`, `:358-366 @a74caba7`), directly above the price line. The server composes it from the product SPECS, not from the price listing: fragrances use `specs.volume_ml` then `specs.concentration` (RB:553-610, keys RB:572-573, "125ml" format RB:603-607). It was empty in all three incident rows (T1 section 4, brand/variant absent). Reusing it to carry the listing size would change the meaning of a frozen key (contract item 4, PLAN_S80.md section 0) and could disagree with a real spec volume; it is not proposed.

### 3.4 The honest lines of S81-11 / D20 and the flags that feed them

Only in @a74caba7 (the store binary has none: `services/fieldStatusView.ts` does not exist @683f56c0). Readers: `fieldStatusView.ts:1-100` (`productFieldStatus`, `priceProvenance` `:45-78`, `sectionNeedsHonestLine`). Lines: the price honest line (`ResultsContent.tsx:367-374`), the as-of / last-seen / listed-on / checked-earlier lines (`:156-185`), "Size: not listed" and "Concentration: not listed" field lines inside the opened Specs body (`ResultsAccordion.tsx:135-157`, only when `field_status[i].size.state === 'unknown'` and no spec row), and the honest first line in an `unavailable` section. Server flags: ENABLE_FIELD_STATUS_METADATA (`metadata.field_status`, KI:86-88, SCS:3949-3963), ENABLE_RESULT_STATUS_METADATA (`metadata.section_status`, RG:86-88, RB:2322-2329), ENABLE_KB_FIRST_SERVE (`price.as_of`). All OFF on web (H2); stated limit L3 says every D20 rendering is dormant until its flag flips (CLAUDE.md:582). No D20 line shows a size next to a price.

## 4. PER-ML: existing computations

| Side | Finding | Where |
|---|---|---|
| Backend | NO per-ml or per-100-ml price is computed anywhere in app/ (grep for per_ml, per ml, price_per, unit_price, per_unit, cost_per, per_100: only cost-per-comparison telemetry in admin/analytics). | grep of the a74caba7 export |
| Backend | The only per-unit logic REJECTS unit prices: `_PER_UNIT_MARKER_RE` (PS:13462-13470) marks "/ 100 ml", "per 100 ml", "Grundpreis" and similar decoys so HTML price parsing never takes a unit price for a shelf price (PS:13533-13563, PS:13619-13620). | PS |
| Backend | Size helpers that a per-ml line can reuse: `extract_sizes_ml` (ml only, PS:4087-4093); an oz-to-ml converter `_SIZE_OZ_RE` / `_ML_PER_FL_OZ = 29.5735` (PS:4099-4101) that the fairness path does NOT use; `_candidate_size_ml` (listing-only reading order, PS:2152-2167). | PS |
| Backend | Fashion `cpw_score` ("cost per wear", SS:56, SS:1343, mapped to the value signal at SS:2183) is a score label, not a per-unit price. Fragrance `wear_value_score` ("value per wear", SS:1340) is folded into the core value bar: `build_dimensions_v2` skips any category key containing `_value_` (SS:3848-3934, the skip at SS:3896-3899). | SS |
| Client @683f56c0 and @a74caba7 | NO per-ml display, helper or string (grep for perMl, per_ml, per ml, unitPrice, pricePer: none). No "ml" unit string exists in either `i18n/en.json` or `ar.json` except the spec labels `results.spec.size` ("Size" / "الحجم", `en.json:793`/`ar.json:790 @683f56c0`; `en.json:796`/`ar.json:793 @a74caba7`). | both trees |

## 5. TWO DESIGNS, one per answer to N5b

### 5.0 Shared parts (both designs need them)

The LISTABLE test for an off-basis price (applied at the moment `_mark_size_pending` would discard it):

| # | Condition | Why |
|---|---|---|
| L1 | the reconcile is pending this side with `size_mismatch` (outcome 2 or 3, PS:2390-2398, or the target-None branch PS:2348-2354) | scope = exactly the incident class |
| L2 | `source_method` is in `_GENUINE_BH_SOURCE_METHODS` (PS:17065-17087), not `converted_usd`, not estimated, currency BHD | a US-converted fallback (Armani) is never shown as a Bahrain price |
| L3 | `is_price_showable(name, price, category, enforce_correctness=True)` passes | the same predicate the display chokepoint (RB:1739) and the verdict projection (ES:2522-2524) apply; the reconcile itself runs before that chokepoint, so a pended price was never checked by it |
| L4 | the listing's OWN size is known: exactly one distinct `\d+ml` token in `price.size` or `price.title` (the `_candidate_size_ml` order, PS:2152-2167), and it equals the size the reconcile used (`effective_pair_size_ml`, which may have read the product NAME first, PS:2021-2045) | a size printed beside a price must be the listing's; a gift set ("100ml + 10ml") or a name-derived size is refused and stays pended as today |

Assumption: L4 refuses two-token titles rather than taking the smallest token as `effective_pair_size_ml` does. Reason it beats the alternative: a wrong per-100-ml figure printed to a user is worse than one more blanked price; the smallest-token rule exists to pick a conservative comparison basis, not to label a bottle.

Shared server mechanics (flag ON only; flag OFF byte-identical):
- `_mark_size_pending` (PS:2402-2417) keeps today's pending dict and, for a LISTABLE side, (i) fills the existing optional `size` key from the listing ("125ml"), and (ii) stashes a copy of the found price on the PRODUCT dict under a `_`-prefixed key (proposed `_size_offbasis_price`). A product-level `_` key never reaches the verdict prompt (ES:2506-2510). It MUST be popped by name in RB before both projections, as RB:2267 does for `_shopping_listing_count`, because the legacy alias ships the raw product dicts (RB:2255-2268).
- RB projects the stash into the public pending dict as `price.listed` (both `overview.products[i].price` and `products[i].price`), at the chokepoint, AFTER scoring and the verdict call, so neither the prompt bytes nor the scores change in design (a).
- KI `_status_one` (KI:193-207): for a pending price carrying `listed`, report the D05 price entry from `listed` (fresh / stale with host and rung, as KI:193-203 does for a showable price) instead of `unknown / no_price`, and `size` as `known / listing`. This removes the false "Not listed by the stores we can read yet" of section 2.4 for both designs. The OTA bundle then renders today's pending line (`fieldStatusView.ts:58`: an `unavailable` price with a non-unknown field entry -> `kind: 'none'`).
- Optional telemetry for the proof: `metadata.size_fairness` = list of `{product_index: int, outcome: "on_basis" | "listed" | "pended"}`.

### 5.1 Design (a): show both prices with their sizes, a per-100-ml line, no cheaper claim

Flag: `ENABLE_SIZE_FAIR_LISTED_PRICE` (new; default OFF; read per call; the name is unused in the a74caba7 export and contains no gitleaks keyword).

Smallest additive server contract:

| Key | Type | Present when | Meaning |
|---|---|---|---|
| `price.listed` (in `overview.products[i].price` and `products[i].price`) | object | the side is pended `size_mismatch` AND LISTABLE (5.0) | the real Bahrain listing that was found for a different bottle size |
| `price.listed.amount` | number (BHD, 3 dp) | with `listed` | the shelf price of that listing |
| `price.listed.currency` | string, "BHD" | with `listed` | |
| `price.listed.size_ml` | integer | with `listed` | the listing's bottle size |
| `price.listed.per_100ml` | number (3 dp) | with `listed` | amount / size_ml * 100 |
| `price.listed.retailer`, `.url`, `.title`, `.source_method` | string | with `listed` | the store, the product page, the listing title (recorded in the saved row, as X1 asks), the genuine method |
| `price.size_ml`, `price.per_100ml` on the OTHER side's normal price | integer, number | the pair has a `listed` side and that side's listing size is known (L4 rules) | the on-basis bottle size and its per-100-ml figure |
| `price.size` on the pending dict | string, existing optional key | LISTABLE | now filled from the listing; meaning unchanged |

Keys that keep their meaning: `price.amount` stays null on the off-basis side (null = no price on the pair's common size); `price.unavailable` stays true; `price.reason` stays `size_mismatch`; product-level `best_price` and `retailer` stay null; every scoring, verdict, badge, confidence and savings key is unchanged.

What scoring does with the off-basis price: nothing. The found price never enters `price.amount`, so `price_raw` stays None, the value / `wear_value_score` dimension stays missing (SS:1768-1778, SS:318-333), `_dim_price` stays `limited_data` (SS:3243-3248), the factual verdict has no price fact (RB:873-894), Home / Profile savings skip the row (HR:167-192, HR:284-290). The C1 winner logic is therefore exactly today's (decided by wear_value 75 vs a 50 default, T1 C1); that weakness is not X1's to change and is stated, not hidden.

What each live bundle displays with NO client change:

| Bundle | Off-basis side (Layton, Libre) | On-basis side | Honest or misleading? |
|---|---|---|---|
| 683f56c0 store | "No confirmed price yet." / "لا يوجد سعر مؤكد بعد." (unchanged; `listed` is an unknown key and ignored) | unchanged | Honest (the sentence is true for the pair's comparison size; no number, no claim), but the new data is invisible: no visible change |
| a74caba7 OTA, FIELD_STATUS OFF | the same pending line | unchanged | Honest, no visible change |
| a74caba7 OTA, FIELD_STATUS ON | the same pending line, because the D05 fix (5.0) keeps the entry non-unknown; without that fix it would be the false "Not listed by the stores we can read yet" | unchanged | Honest only with the D05 fix |

Client change needed (it must wait for an OTA the owner approves; the store binary sees it only after taking that OTA):
- `components/results/ResultsContent.tsx`: in the hero price slot, a branch before `formatPrice` when `price.unavailable && price.reason === 'size_mismatch' && price.listed` passes a pure validity reader: line 1 "85.000 BHD . 125 ml" (amount via `utils/formatNumber.ts:96`), a caption "68.000 BHD per 100 ml", a caption "Different bottle size: prices not compared". The on-basis side adds its size and per-100-ml caption when `price.size_ml` is present. `pricePending` (`:212`) stays true, so the price and value bars and the price pill stay hidden: no cheaper claim anywhere. The new branch must take precedence over `prov.kind === 'unknown'` (`:367-374`).
- `types/types.ts` (`ProductPrice`, `:60-73 @a74caba7`): add `size?`, `reason?`, `size_ml?`, `per_100ml?`, `listed?`.
- New pure reader `services/sizeFairView.ts` and tests under `__tests__/inc_x1/`.
- `i18n/en.json` and `i18n/ar.json`: about three new keys (a size label with the ml count, the per-100-ml template, the different-size caption). Every new Arabic string goes to the owner's native read before the OTA (the S81-11 owner step (6) practice).

Files touched (server): PS (`_mark_size_pending` + the LISTABLE helper + the flag reader), RB (projection + the stash pop + the on-basis keys), KI (`_status_one` D05 price/size entry), SCS only if the stream `prices` payload must carry `listed` (it re-projects through `public_price_view`, SCS:5430-5434, so `listed` rides along with no edit; the bundles use that event only for timing). Tests: `tests/test_inc_x1_*.py`.

Risks: (1) identity: a wrong-product listing now gets a visible number (the Versace "Eros for Women" match in T1 C3 shows the class); L3 is the same gate every shown price passes, no stronger. (2) Size parsing: a size in the listing title that is not the bottle (a "10ml travel spray" add-on line) -> L4's one-token rule. (3) The `_size_offbasis_price` stash leaking through the legacy alias if the pop is missed (pin it). (4) The verdict prompt must stay byte-identical flag ON vs OFF (pin it). (5) Cached bodies built flag OFF keep showing no `listed` until their TTL. (6) The proof text of record conflicts: IR line 100 says "products[1].price.amount not null"; under design (a) the amount stays null by construction and the backing check becomes `products[1].price.listed.amount` not null with `listed.size_ml` stored. The orchestrator must restate that proof before RED.

Truth table, design (a), the three incident products. The sizes 125 ml and 90 ml are LIKELY (IR line 175); if the stored listing title carries no ml token, L4 fails and the row is "as today".

| Product | Today (both bundles) | Server body, flag ON | Store 683f56c0, no client change | OTA a74caba7, no client change | After the client OTA |
|---|---|---|---|---|---|
| Layton (vs Aventus 133.460 BHD noon.com, 100 ml) | "No confirmed price yet."; price/value bars and price pill hidden | `price` = pending `size_mismatch` + `size: "125ml"` + `listed {amount 85.0, currency BHD, size_ml 125, per_100ml 68.0, retailer alibaksh.com, source_method woo_store_api, url, title}`; Aventus price gains `size_ml 100, per_100ml 133.46`; scores unchanged | unchanged | unchanged (pending line; never "Not listed" with the D05 fix) | Layton "85.000 BHD . 125 ml", "68.000 BHD per 100 ml", "Different bottle size: prices not compared"; Aventus "133.460 BHD . 100 ml", "133.460 BHD per 100 ml"; no bar, no pill, no cheaper sentence |
| YSL Libre (vs Lancome 34.000 BHD fragrancebh.com, 100 ml) | the same | `listed {amount 39.0, size_ml 90, per_100ml 43.333, retailer fragrancebh.com, woo_store_api}`; Lancome gains `size_ml 100, per_100ml 34.0` | unchanged | unchanged | Libre "39.000 BHD . 90 ml", "43.333 BHD per 100 ml", the different-size caption; Lancome with its size and per-100-ml line |
| Armani (parked converted_usd GiftBlooms 40 ml, vs Versace 25.000 BHD) | "No confirmed price yet." | NOT LISTABLE (L2: `converted_usd`); pending dict exactly as today (`size: "40ml"` already present); no `listed`; Versace unchanged | unchanged | unchanged | unchanged: no Bahrain price is shown for Armani |

### 5.2 Design (b): compare per 100 ml

Flag: `ENABLE_SIZE_FAIR_PER_ML_BASIS` (new; default OFF; read per call). It REQUIRES everything in 5.0 and 5.1's contract (the per-ml comparison has to be displayed with its sizes anyway), so in practice (b) = (a) + a per-ml basis for the scores.

Rejected variant (b2), un-pend the sticker price: putting the off-size amount back in `price.amount` with `unavailable` false is misleading on BOTH live bundles, measured: the sticker amounts render with no size (3.3); `pricePending` turns false, so the price and value bars and the price pill reappear (`ResultsContent.tsx:488-494`/`:526 @683f56c0`, `:555-561`/`:593 @a74caba7`) with the server's English delta "BHD N less" (SS:3250-3262); the factual verdict can say "comes in N% cheaper" (RB:1085-1089); Home and Profile savings add a cross-size difference (HR:167-192). No client-free version of (b2) is honest.

Smallest additive server contract for (b) (= (a)'s keys, plus):

| Key | Type | Present when | Meaning |
|---|---|---|---|
| `overview.size_basis` | object | both sides are on the per-100-ml basis (each side is on-basis or LISTABLE, both sizes known) AND the sizes differ | the pair compared per 100 ml |
| `overview.size_basis.basis` | string, "per_100ml" | with the block | |
| `overview.size_basis.values` | [number, number] | with the block | per_100ml of product 0 and product 1 |
| `overview.size_basis.sizes_ml` | [integer, integer] | with the block | |
| `overview.size_basis.lower_index` | 0, 1 or null | with the block | the lower per-100-ml side; null when the two values are equal (any wider tie band, for example the 3-point `_DIM_WINNER_TIE_MARGIN` at SS:3189, is a spec choice) |

The legacy keys keep their meaning exactly as in (a): the off-size side's `price.amount` stays null and `unavailable` true. That is what keeps both bundles honest (no bars, no pill, no cheaper sentence, no savings).

What scoring must do with a price that is not on the common basis (b): when the pair carries `size_basis`, the orchestrator hands scoring the per-100-ml figure for BOTH sides (a product-level `_`-key read by `_compute_raw_scores` in place of `price.amount`, SS:1768-1778, under the flag); `_normalize_price` (SS:2449-2470) and the value signal (SS:318-333, SS:1256-1309) then use it. A side that is not on the basis (no listing size, not LISTABLE, the Armani converted fallback) stays missing exactly as today; a sticker price is never mixed with a per-ml price. For EQUAL sizes the per-ml branch is unnecessary: `_normalize_price` is a min-max ratio and `_dim_price` a lo/hi ratio (SS:3250-3256), both unchanged by a common scale factor, so the flag engages only when the sizes differ. `_dim_price` and the factual verdict keep reading `price.amount` (null on the off-size side), so the price bar stays `limited_data` and no price sentence is generated; the verdict prompt is not given the per-ml figure (it would invite an unchecked "cheaper" claim, ES:2466-2534).

What each live bundle displays with NO client change (b): the price slots exactly as in (a) (pending line; bars and pill hidden). BUT the overall scores, `overview.winner` (which build 3 always crowns, PLAN_S80.md section 0 item 1), the winner name in the header and the non-price factual-verdict line can change, because the price and value inputs changed. C1 is the clear case: today Aventus wins by margin 1.4 on wear_value 75 vs a 50 default (T1 C1); under (b) Layton gets a price score (68.0 vs 133.46 per 100 ml) and a computed value, so the winner is LIKELY to move to Layton (NOT computed: scoring is not run in a read-only round; DEFERRED TO RED). The page would then crown Layton while still saying "No confirmed price yet." for it, with no visible reason: not a false sentence, but misleading by omission on both bundles until the client OTA. The compare requests carry no bundle or version signal the server could gate on (grep of `services/api.ts @a74caba7`: only `Authorization`, `:316`, `:891`), so a server change cannot be shown to the OTA bundle only.

Client change needed (b): everything in (a), plus one line under the pair: "Per 100 ml, <name> is lower (68.000 vs 133.460 BHD)" from `overview.size_basis`, which IS a comparative claim, made explicitly on the per-100-ml basis. If the owner wants the price and value bars on that basis too, the server must emit a per-ml price dimension; a new dimension key would leave the 51-key catalog (PLAN_S80.md section 0 item 4) and reusing `price` would retype a frozen key, so either needs a ruling; it is not in the smallest contract. The client half waits for an OTA, as in (a).

Files touched (b): those of (a) plus SS (`_compute_raw_scores` basis read and its flag) and SCS (stash the per-100-ml basis before `compute_scores`, SCS:4646 / SCS:5497, after the reconcile), and RB (the `size_basis` block). Risks: those of (a), plus (1) the winner flip on both live bundles without a visible reason (above); (2) every scoring pin and eval golden that covers a different-size fragrance pair moves under the flag; (3) a per-ml comparison across concentrations or a gift set is still apples to oranges (L3/L4 only bound it); (4) Home / Profile savings stay sticker-based and skip these rows (amount null), so Home never shows a per-ml saving; making it per-ml would touch the migration-036 RPC path (HR:95-110), a FOCUS surface, and is not proposed.

Truth table, design (b), the three incident products (sizes LIKELY, as above):

| Product | Server body, flag ON | Scores | Store 683f56c0 and OTA a74caba7, no client change | After the client OTA |
|---|---|---|---|---|
| Layton vs Aventus | (a)'s keys + `size_basis {basis per_100ml, values [133.46, 68.0], sizes_ml [100, 125], lower_index 1}` | price and value computed per 100 ml for both; winner LIKELY moves from Aventus to Layton (UNVERIFIED) | prices as today; the crowned winner and overall bars may change with no visible price | both prices with sizes and per-100-ml lines, plus "Per 100 ml, Layton is lower (68.000 vs 133.460 BHD)" |
| YSL Libre vs Lancome | `size_basis {values [43.333, 34.0], sizes_ml [90, 100], lower_index 1}` | per 100 ml Lancome is lower, the same direction as the sticker (34.000 < 39.000), so the winner direction on price is unchanged; magnitudes change | as today | both with sizes; "Per 100 ml, Lancome is lower (34.000 vs 43.333 BHD)" |
| Armani vs Versace | no `listed`, no `size_basis` (L2 fails) | exactly today's | as today | as today: no Bahrain price for Armani, no per-ml line |

## 6. CLASS: the FOCUS surfaces each design touches

| FOCUS surface | Design (a) | Design (b) |
|---|---|---|
| auth | no | no |
| quota or billing | no (the compare quota and credit paths are not on this path) | no |
| legal or privacy text | no change. UNVERIFIED: whether the Terms or the store listing promise same-size price comparisons (not read this round; worth a grep at RED) | the same |
| consent | no | no |
| security middleware | no | no |
| migrations | no (no schema change; the new keys are data inside `full_response`, whose column type is UNVERIFIED here) | no, ONLY if Home / Profile savings stay as they are; a per-ml saving would touch the migration-036 RPC path (HR:95-110) |
| Redis or Lua | no code change; cached response bodies carry the new keys as data | the same |
| App-Review-visible client surface | YES: the client half changes the result page's price card and adds Arabic strings (OTA, then the 1.0.1 review sees it) | YES: the same, plus a comparative per-100-ml sentence |
| secrets | no | no |

Not a listed FOCUS surface but production-visible: design (b) changes scores and can change the crowned winner on BOTH live bundles the moment its flag flips (5.2); design (a) changes nothing a live bundle renders. The client copy rule in `services/sourceMethod.ts:13-15` (no "estimated / reference price / indicative" wording) binds the new per-100-ml strings.

## 7. RECOMMENDATION and the owner's decisions

Recommendation: N5 = show the found price with its bottle size; N5b = design (a).

Reasons, in order: (1) design (a) is honest on both live bundles with no client change: they keep today's pending line, and no bar, pill, verdict sentence or Home saving can compare two sizes, because `price.amount` keeps its meaning (5.1). (2) It changes no score and no winner, so the flag flip has one observable effect (new keys in the body and the saved row) and flag-OFF byte identity is simple to pin. (3) It carries the D05 change that stops the dormant D20 path from printing the false "Not listed by the stores we can read yet" for a perfume a store did list (2.4). (4) Its keys are a strict subset of (b)'s, so (b) can be layered on later without renaming anything. Design (b) moves winners on a basis the page does not show until the client OTA lands, and a per-ml bar would need a further ruling on a frozen key.

Stated limit the owner must hear: the server half of either design changes NOTHING on the phone. Layton shows "85.000 BHD . 125 ml" only after a client OTA that the owner approves (and the store binary only after it takes that OTA). Until then the proof is the saved row (`products[1].price.listed.amount` = 85.0, `listed.size_ml` stored) and the deploy log, which is not the owner's proof standard (H6). Armani shows no price under either design, by construction.

The exact wording for the owner:

> N5. When the search finds a real Bahrain price for a different bottle size than the one the pair is compared at (for example Layton at 85.000 BHD, likely a 125 ml bottle, against Aventus at 100 ml), should the app keep hiding it as today ("No confirmed price yet"), or show it together with its bottle size?
>
> N5b. If it is shown, which one: (a) show each price with its bottle size and a "per 100 ml" line, say that the sizes differ, and make no "cheaper" or "better value" claim and no change to the scores or the winner; or (b) compare the two per 100 ml: the price and value scores, and so possibly the winner, use the per-100-ml figure, and the page says which one is lower per 100 ml?
>
> Also decide: (c) the unit shown, per 100 ml (recommended: it reads like a bottle price) or per 10 ml or per 1 ml; (d) that a US-converted price at another size is never shown (recommended: never); (e) which OTA carries the client half (it is not in Friday's LEGAL-V3 bundle unless you rule it in), and you read every new Arabic string first.

## 8. DEFERRED TO RED and UNVERIFIED

DEFERRED TO RED (exact commands; nothing was run this round): the backend RED in the unit worktree, `python <SP>/harness/pyt.py --bound 900 --tag inc-x1-red --log <notes>/inc-x1-red.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-x1 -- tests/test_inc_x1_size_fairness.py -q`; the scoring delta of design (b) on the C1 fixture (same runner, a pinned before/after of `scoring.scores` and `overview.winner`); the client RED, after the H5 jest probe, `npx jest __tests__/inc_x1 --runInBand` in `SmartCompareApp/` of that worktree. The file names are proposals.

UNVERIFIED in this round: the off-target sizes 125 ml / 90 ml (LIKELY, record); whether the Layton and Libre listing titles carry an ml token (if not, L4 fails and design (a) shows nothing new for them: the replay comparison's log or a captured title settles it before RED); the full fan-out scraper candidate shape; whether `_partial_product_data` is the reconciled list; the response-cache TTL; the migration-036 SQL; the `full_response` column type; any Terms or listing wording about same-size comparisons; the actual value of ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX on web (never probed, H2).
