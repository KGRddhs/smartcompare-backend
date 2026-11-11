# PAGE INVENTORY: the fragrance result page today (units X4, X5, X6, X7)

Written 2026-11-11 by the inventory-and-design writer of the S92-FIX incident lane. READ-ONLY round: no test, no build, no network, no production probe. Every line number below was measured in this run on the plain source exports (the export line numbers equal the lines at the sha).

## Sources and short names

| Short name | What it is |
|---|---|
| CL | the client at main a74caba7: scratchpad/src/a74caba7/SmartCompareApp/src (byte-identical to the live OTA bundle f1e20c39, per T4_result_page.md header) |
| ST | the STORE binary client 683f56c0: scratchpad/src/683f56c0/SmartCompareApp/src |
| RC | components/results/ResultsContent.tsx |
| RA | components/results/ResultsAccordion.tsx |
| DB | components/results/DimensionBars.tsx |
| RS | screens/ResultsScreen.tsx |
| RB | app/services/response_builder.py at a74caba7 |
| SS | app/services/scoring_service.py at a74caba7 |
| SCS | app/services/structured_comparison_service.py at a74caba7 |
| R1 / R2 / R3 | the three incident rows 441e7b7d (Aventus vs Layton), 5b369372 (YSL Libre vs La Vie Est Belle), e2320ca7 (Acqua di Gio Profumo vs Eros) as read in T1_trace.md and T4_result_page.md (record/incident). Row values are quoted from those extracts; this round did not read the database. |

Files that are byte-identical in CL and ST (measured with cmp in this run): DB, FactualVerdict.tsx, PersonalizationChip.tsx, RunnerUpWinsCard.tsx, ConfidencePills.tsx, CategoryProfile.tsx, _deltaText.ts, primitives/ProductImage.tsx, services/resultHonesty.ts, utils/dimensionLabel.ts. Files that differ: RC (CL 883 lines, ST 811), RA (CL 956, ST 911), RS (CL 1134, ST 1101); services/fieldStatusView.ts exists only in CL (100 lines). So every difference between the two live bundles on this page sits in RC, RA, RS and fieldStatusView.ts.

## (a) Every section, in screen order

The order is the JSX order of RC at CL (pinned by the RC header comment, RC:14-26). "Keys read" are response keys. "Empty" is what the user sees when the data is missing.

| # | Section | Render condition (CL file:line) | Response keys read | When the data is empty | ST 683f56c0 difference |
|---|---|---|---|---|---|
| 0 | Screen states that REPLACE the page (loading, error, category not live, same identity, category conflict) | RS:173-174 (state names), RS:357-366 (set from the error body), RS:818-821 (copy keys) | error body `code`, `reason` | not a result page | the three new error states exist only in CL (T4 section 5 item 4); ST shows its generic error |
| 1 | Header: back, TopMatchBadge, share | always, RC:274-301 | none | always the same | same (ST RC:222-248) |
| 2a | Hero photo per product | always mounted, RC:337-344; ProductImage.tsx:13-16 picks image or placeholder; placeholder node ProductImage.tsx:124 | `overview.products[i].image_url` (RS:431-433 reads `overview.products`, falls back to root `products`) | a grey tone tile with a dimmed icon, NO caption (ProductImage.tsx:6, 21) | same file (cmp equal) |
| 2b | Product name | always, RC:345-347 | `overview.products[i].name` | the typed name always exists | same |
| 2c | Brand line | only if truthy, RC:348-352 | `overview.products[i].brand` | line absent (brand is "" on the explicit-pair path, SCS:4427 per T1) | same (ST RC:294) |
| 2d | Variant line | only if truthy, RC:358-366 | `overview.products[i].variant` (RB:1950 `_compose_variant_string`) | line absent | same (ST RC:304) |
| 2e | Price line | always one line, RC:367-386. If the OTA reader says `kind === 'unknown'` (fieldStatusView.ts:51-84) it prints `results.honest.notListed` (RC:367-374); else `formatPrice` (RC:188-206): `price.unavailable` -> `results.price.pending` (RC:194), null amount -> `results.priceNA` (RC:195), `converted_usd` -> suffix `results.convertedUSD` (RC:204) | `overview.products[i].price.{amount, currency, unavailable, reason, size, source_method, estimated, retailer, as_of}`, `metadata.field_status[i].price` | "No confirmed price yet." / "Price N/A"; the found size (`price.size`, set by `make_pending_price`, price_service.py:2005-2018) is never shown | ST has no honest line and no provenance line (ST RC:135-142 formatPrice, :321 render) |
| 2f | Price provenance line (as of / last seen / listed on / checked earlier) | RC:156-186, rendered RC:387; only for kinds fresh, stale, listed, staleNoDate | `price.as_of`, `price.retailer`, `metadata.field_status[i].price.{state, as_of}` | absent (every body today has neither key, T4 section 5 item 2) | absent in ST |
| 2g | Converted-from-USD caption | RC:392-402 | `price.source_method` | absent | same |
| 3a | "Why this fits you" eyebrow (`results.whyWePicked`) | always, RC:426 | none | always | same (ST RC:357-359) |
| 3b | Partial note (`results.partial.note`) | `metadata.partial === true`, RC:218, 431-438 | `metadata.partial` | absent | same |
| 3c | Degraded note (`results.degraded.note`) | `comparison.error` truthy (resultHonesty.ts `isDegradedComparison`), RC:227, 439-446 | `comparison.error` | absent | same (ST RC:174, 372) |
| 3d | Medical note | supplement detection, RC:232, 447-454 | `category_used`, names | absent | same |
| 3e | Verdict text | RC:463-481: `scoring_v2.factual_verdict.line1` -> FactualVerdict (line1 + italic line2); else, when degraded, nothing (RC:469-471); else `overview.winner.reason` (RC:236-238), dropped when it matches SCORE_INTERNALS_RE (RC:472-478). FactualVerdict renders an empty "contract violation" View if a banned word appears (FactualVerdict.tsx BANNED_WORDS and render) | `scoring_v2.factual_verdict.{line1,line2}`, `overview.winner.reason`, `recommendation` (old format) | on a degraded body WITH a factual verdict (R1-R3): the grey note, then the English template lines (FactualVerdict wins the ternary first) | same (ST RC:396-414) |
| 3f | Personalization chip | `scoring_v2` truthy, RC:489-494; chip returns null when `applied_shifts` is empty (PersonalizationChip.tsx:35) | `scoring_v2.personalization.applied_shifts[*].{dim_display, direction}` | absent | same |
| 4 | "Where the runner-up wins" card | always mounted RC:504-510; self-hides when no runner-up-winning dimension (limited_data excluded, RunnerUpWinsCard.tsx:50-63) and no `key_tradeoff` (RunnerUpWinsCard.tsx:100); `key_tradeoff` is passed only when not degraded (RC:239-241) | `scoring_v2.dimensions`, `overview.winner.key_tradeoff` | absent (hidden in R1-R3, T4 row 4) | same |
| 5 | Score bars | OUTER gate `scoring_v2.dimensions.length >= 3` on the unfiltered list (RC:527); price and value dims removed when ANY price is pending (RC:212, 555-562); INNER filter drops `data_insufficient`, null scores and `caption_key === 'limited_data'` (DB:82-88); a zero score shows a dev-only violation node (DB:95-110); the name legend renders only with >= 1 row (DB:128); 4 rows then "See full breakdown" (DB:115-116). Row label = `results.dimension.<key>` through `localizedDimensionLabel` (utils/dimensionLabel.ts, DB:287); caption = the server `delta_text` VERBATIM through `safeDelta` (DB:288, 334-336), hero caption for price and value (DB:278-290) | `scoring_v2.dimensions[*].{key, label, score_a, score_b, delta_text, confidence, caption_key, winner, is_cross_tier, value_match_a/b, data_insufficient}`, `scoring_v2.comparison_quality` | an EMPTY section (no legend, no row) when every dim is filtered (R1); otherwise only the emitted, non-placeholder dims (R2: 4, R3: 1) | same logic (ST RC:460, 488-499) |
| 6 | "What we know" + confidence pills | `scoring_v2.confidence_legs` truthy, RC:584-598; price pill hidden when any price is estimated or pending (RC:593); a pill renders only if its leg is defined (ConfidencePills.tsx renderable filter); the row is null when no pill remains | `scoring_v2.confidence_legs.{price, reviews, specs}`, `scoring_v2.confidence_details` (sheet) | the price pill vanishes (R1-R3 showed only specs and reviews) | same (ST RC:517-528) |
| 7 | Cohort line "+N shoppers in X leaned the same way" | CL: REMOVED (RC:600-601 comment, R-S11-31) | none in CL | none | ST: always mounted (ST RC:534-543), CohortBadge null unless peer_count > 0 and governorate non-empty; reads `cohort_summary.{peer_count, governorate}` (ST RS resolve helpers about :979-1006, T4 section 3); key `results.cohort_badge` (ST ar.json:756) |
| 8 | Legacy scoring placeholder | `!scoring_v2 && scoring`, RC:621-629 | `scoring` | an empty View | same |
| 9 | "Dig deeper" eyebrow (`results.digDeeper`) | always, RA:302 | none | always | same (ST RA:261) |
| 9a | Accordion row "At a glance" (category profile) | `hasCategoryProfile(products)` (RA:167; CategoryProfile.tsx:76-78) | `products[i].category_profile.fields` | row removed. NOTE: RS passes `overview.products` (RS:431-433) and RB puts `category_profile` only on the ROOT `products` list (RB:2258, root list set at RB:2268); `overview.products` items carry no such key (RB:1944-1995). So on a new-format body this row never renders (code reading; not measured on a device) | same |
| 9b | Accordion row "Reviews" | always, RA:260-276; collapsed sub = review-count-weighted average + total (RA:170-197, 268-275) | `reviews.products[i].{name, rating, review_count, rating_count, review_praise}`, root `products[i].review_praise` fallback | opened body: CL prints `results.honest.notListed` first when `metadata.section_status.reviews === 'unavailable'` (RA:382); per product a block only if praise or rating > 0 (RA:400-455); if no block, `results.accordion.reviewsEmpty` "Reviews are still coming in." (RA:458-461) | ST has no honest line (ST RA:338-418) |
| 9c | Accordion row "Pros & Cons" | removed when `hideProsCons` = degraded (RA:278-288; RC:646) | `overview.products[i].{pros, cons}` | degraded: the whole row is gone. Not degraded but empty: each column shows only the product name (no per-product empty line; RA body after :470) | same removal (ST RA:237; ST RC:588) |
| 9d | Accordion row "Specs" | always, RA:289-297; sub = count of spec keys | `specs.products[i].{name, specs}`, `specs.specs_comparison.rows[*].{field, winner}` (RC:263-270) | opened body: CL honest line when `section_status.specs === 'unavailable'` (RA:551); a header row with the two names; zero rows when both spec objects are empty (RA:206-224); a row known on ONE side only is DROPPED (RA:~598 `return missing !== 1`); CL adds "Size: not listed" / "Concentration: not listed" lines from `metadata.field_status` (RA:135-157) | ST: no honest line, no field lines (ST RA:505-553) |
| 10 | Feedback card | always, RC:672-681 | `comparisonId` | always | same. Unit CL3 (S91) is changing this card in another session; this lane does not touch it |

### Store binary 683f56c0 versus the live OTA (CL) on this page

| Area | ST 683f56c0 | CL (= OTA f1e20c39) |
|---|---|---|
| Cohort line | shown when `cohort_summary` is present (it is: 53 / Northern on R1-R3) | removed |
| Price honest line and provenance | none | present, but only when `metadata.field_status` or `price.as_of` exist (both absent on every body today) |
| Accordion honest lines | none | present, but only under `metadata.section_status` / `field_status` (flags ENABLE_RESULT_STATUS_METADATA / ENABLE_FIELD_STATUS_METADATA, both OFF) |
| Error states category_not_live, same_identity, category_conflict | none | present |
| Everything else in this table | identical | identical |

So with today's flags the two bundles differ on this page by the cohort line only (T4 section 5).

## (b) Every server-written string a client shows verbatim

"Key-like field beside it" = is there already a machine-readable field in the same object from which the app could build the text itself?

| # | String (English, as written) | Where (file:line at a74caba7) | Inputs | Shown by | Key-like field beside it |
|---|---|---|---|---|---|
| S1 | "{winner} draws far more reviewer attention (~{views} YouTube views, led by {channel})." | RB:1084 | winner name, humanized views, channel; only with ENABLE_YOUTUBE_SOURCE (RB:992-996) | FactualVerdict line1 (RC:463-468) | none: `factual_verdict` is `{line1, line2}` only (RB:1181) |
| S2 | "{winner} comes in {pct}% cheaper." | RB:1088 | winner name, pct from `_price_candidate` (RB:873-894) | line1 | none |
| S3 | "{winner} carries a {pct}% price premium for the upgrade." | RB:1089 | same | line1 | none |
| S4 | "{winner} earns {diff} more stars from reviewers." | RB:1093 | stars diff from `_rating_candidate` (RB:897-917); derived ratings excluded (RB:855-870) | line1 | none |
| S5 | "{winner} edges ahead despite slightly lower reviews." | RB:1094 | winner name | line1 | none |
| S6 | "{winner} leads on {label}." | RB:1097 | winner name, the ENGLISH dimension label of `_top_dim_candidate` (RB:920-950), which skips price/reviews/value but does NOT skip limited or one-side-missing dims | line1 (R3: "Armani Acqua di Gio Profumo leads on Versatility.") | the dimension's `key` exists in `scoring_v2.dimensions`, but the candidate does not carry it |
| S7 | "{winner} comes out on top." | RB:1098 | winner name | line1 | none |
| S8 | "{winner} edges ahead on the overall picture." | RB:1175 (also RB:192 for winner_reason) | winner name; used when no candidate exists | line1 (R1) | none |
| S9 | "{runner} pulls ahead on {label}." | RB:1112 | runner name, English label of `_runner_up_dim_candidate` (RB:953-989) | line2 | none |
| S10 | "{runner} stays {pct}% lighter on the wallet." | RB:1121 | runner name, pct | line2 | none |
| S11 | "{runner} rates a touch higher with shoppers." | RB:1129 | runner name | line2 | none |
| S12 | "{runner} stays in the conversation as a close alternative." | RB:1131 | runner name | line2 (R1-R3: by the code path no runner-up dim, price or real-rating fact exists in any of the three rows; T4 section 4 quotes the line) | none |
| S13 | "{winner} is the stronger overall pick." / "The stronger overall pick." | RB:1414 (`_QUALITATIVE_WINNER_REASON`) | winner name | `overview.winner.reason` -> verdict text only when no factual verdict and not degraded (RC:472-481) | none |
| S14 | "{loser} stays competitive on {dim}." | RB:244 (`deterministic_verdict_fields`) | loser name, raw dim key with `_score` and `_` stripped | `overview.winner.key_tradeoff` -> RunnerUpWinsCard prose when not degraded (RC:239-241) | none (the dim text is a stripped key, English) |
| S15 | Bar captions, core dims: "Price data unavailable" (SS:3246), "{currency} {diff} less" (SS:3260), "Limited review data" (SS:3292), "Same rating" (SS:3300), "{diff} stars higher" (SS:3302), "Limited value data" (SS:3352, 3369), "Comparable value" (SS:3381), "Nearly identical value" (SS:3386), "Slightly higher value here / on the other side" (SS:3393-3394), "Noticeably more per dinar here / on the other side" (SS:3398-3399), "Substantially stronger value ratio / on the other side" (SS:3403-3404), prefix "Across tiers - ..." (SS:3411-3412) | `_dim_price` SS:3240-3269, `_dim_reviews` SS:3272-3311, `_dim_value` SS:3314-3420 | prices, currency, ratings (derived excluded, SS:3280-3288), value ratio, cross-tier flag | `delta_text` -> DB row caption (hero row for price and value, DB:278-290) | `key` (price / reviews / value) and, ONLY on the placeholder path, `caption_key: "limited_data"` (SS:3248, 3294, 3355, 3372). A real caption has no key |
| S16 | Bar captions, fragrance dims: "Comparable" (SS:3615), "+{margin}pt edge" (SS:3617, only with < 2 products), "{hi}h vs {lo}h" (SS:3667), "Longer-lasting" (SS:3668), "{a} vs {b} projection" (SS:3676, the a/b values are free text from specs), "Stronger projection" (SS:3677), "More distinctive" (SS:3679), "More versatile" (SS:3681), "Better presented" (SS:3683), "Better everyday value" (SS:3685) | `_compose_delta_text` SS:3592-3734, called from `_dim_from_category_lookup` SS:3584 | the two scores, the specs `longevity` / `longevity_hours` / `sillage` / `projection` values | DB row caption | `key` only; no caption key |
| S17 | Personalization priority names: "scent character", "longevity", "projection", "versatility", "value per wear", "presentation" | SS:1339-1340 (`DIMENSION_DISPLAY_NAMES`), emitted by `_compute_applied_shifts` SS:686-716 (`dim_display`, SS:711) | the weight deltas vs category defaults | PersonalizationChip inserts them raw into `results.personalization.chip_template` (PersonalizationChip.tsx:44-50); RC reads `scoring_v2.personalization.applied_shifts` (RC:491; built RB:1358; a duplicate at RB:2092 `personalization.applied_shifts`) | `direction` only; the internal dim key is dropped at SS:711 |
| S18 | Region / governorate, e.g. "Northern" | `cohort_summary.governorate` RB:2200-2212 (from the user's demographics, SCS `_build_cohort_summary`, T4 section 3) | the user's stored governorate | ST only: inside `results.cohort_badge` (ST ar.json:756). CL removed the badge | the value is one of a closed set (Capital, Muharraq, Northern, Southern, Other: DemographicsBottomSheet.tsx:62-66), and both bundles already ship Arabic names under `demographics.governorate.*` (CL ar.json:395-399); `metadata.region` ("bahrain", RB:2097) has no client reader (grep in this run) |

Notes on (b):
- Language input already reaching the server: both live bundles send `lang` on the text compare (CL services/api.ts:718-729 and :887-888; ST services/api.ts:690). The route normalizes it (text_routes.py:754, extraction_service.py:2324-2332) and it reaches `build_comparison_response(output_lang=...)` (RB:1489; SCS:3923, 4811, 5704). Today it only changes the AI verdict prose (ENABLE_ARABIC_VERDICT_OUTPUT, extraction_service.py:2317-2320, 2618) and the store label (RB:2375). The camera route passes no language (image_routes.py:610-614 calls `compare_from_text` without `output_lang`; no `lang` read found in image_routes.py by grep), and the link route returns a different body (part d).
- The S80 plan already ruled a server-side by-value localization of these templates (R-A10, record/s80/PLAN_S80.md:31; unit B8, :64; client C2, :75). No such code exists at a74caba7 (grep for a localized factual-verdict template found none). UNVERIFIED: whether B8 was ever specced; the record copy holds no B8 spec.
- A second reader of S1-S8 outside the result page: the Home "smart pick" caption copies `factual_verdict.line1` under ENABLE_SMART_PICK_VERDICT_CAPTION (app/api/home_routes.py:628-643). Its flag state is UNVERIFIED here.
- Not templates, out of X5: the AI prose (`winner_reason`, pros, cons, `review_praise`), product names as typed, spec values as extracted.

## (c) The bars for the fragrance category

### How the list is built

`build_dimensions_v2` (SS:3848-3933) always emits the three CORE dims price, reviews, value (SS:3867-3871) and then walks `CATEGORY_DIMENSIONS["fragrances"]` (SS:50-53), adding up to 5 more (SS:3890) through `_dim_from_category_lookup` (SS:3503-3589). `wear_value_score` is skipped because its key contains "value_" (SS:3896). A contextual dim is OMITTED when both sides are missing (SS:3570-3571) and EMITTED when only one side is missing. Each dim gets a `winner` from `_dim_winner` (SS:3921; SS:3192-3238), which returns None when either side was missing, the confidence is low, or the gap is under 3.0 (SS:3189). The list is capped at 8 (SS:3933).

### Every fragrance dimension

| Public key | Label (SS) | Raw signal (SS:2175-2179) | What that signal really is | Proxy? | Emitted? |
|---|---|---|---|---|---|
| price | "Price" (SS:3263) | price amounts | the two shelf prices | no | always; 75/75 `limited_data` when either price is missing (SS:3244-3248) |
| reviews | "Reviews" (SS:3305) | `rating` | the star rating; a derived rating counts as missing (SS:3280-3288) | no | always; 75/75 `limited_data` when either is missing (SS:3290-3294) |
| value | "Value" (SS:3414) | price and rating | rating per price ratio (SS:3314-3420) | partly (a ratio of two facts) | always; 75/75 `limited_data` when any input is missing (SS:3348-3372) |
| character | "Character" (SS:3482) | `spec` | `_score_specs` (SS:1891-1950): a count / magnitude of filled spec fields, not the scent | YES | when specs exist on >= 1 side |
| longevity | "Longevity" (SS:3464) | `spec_secondary` | 0.6 x spec + 0.4 x review; when specs are missing it is the REVIEW score alone (SS:2339-2353); reordered by real hours when both have hours (SS:2422-2447) | YES (stars) when specs are missing | when specs or a rating exist on >= 1 side |
| projection | "Projection" | `review` | the star rating normalized `(r-1)/4*80+20` (SS:2544-2551) | YES (always stars) | when a rating exists on >= 1 side |
| versatility | "Versatility" | `reliability` | `_score_reliability` (SS:2071-2106): the fact-check verified / unverified share of the extracted specs | YES (data-quality, not wear) | when a fact-check exists on >= 1 side |
| presentation | "Presentation" | `popularity` | `_score_popularity` (SS:2108-2137): log10 of the review count plus a source bonus | YES (rating count) | when a count exists on >= 1 side |
| wear_value | "Wear value" | `value` | spec and price | n/a | NEVER emitted as a bar (SS:3896); it still weighs 0.10 in the overall score (SS:72) |

### The default-50 behaviour

`MISSING_SCORE = 50` (SS:297). A missing raw signal normalizes to 50: review (SS:2546-2548), reliability and popularity (SS:2553-2558), spec_secondary when both inputs are missing (SS:2345-2346). The per-dim missing flag is set from the source signal (SS:2406-2407) and recorded in `scoring.scores.product_i.missing_data`. Consequences when ONE side is missing:
1. The dim is emitted with 50 on the missing side and a real number on the other (SS:3570-3589).
2. `_dim_winner` correctly returns None (SS:3227-3229), BUT the client paints a winner anyway: with `winner` null, DB:262-268 falls back to `score_a > score_b`.
3. The caption is chosen from the scores alone ("More versatile", SS:3681), so it names a direction.
4. The factual verdict picks the dim as its line1 fact: `_top_dim_candidate` (RB:920-950) ignores both `winner` and the missing flags.
5. The 50 also enters the overall score, so a product with ALL six dims missing scores 50 overall (R3: Armani 50 vs Versace 48.3, incident report section 1).

### Which rows of the three incident results were proxies (from T1 section 5 and T4 section 1; the arithmetic re-checked against the code above)

| Row | Dim | Scores | Caption | Real source | Verdict |
|---|---|---|---|---|---|
| R1 | price | 75 / 75 | limited_data | Layton price pended (size_mismatch) | placeholder, filtered |
| R1 | reviews | 75 / 75 | limited_data | both ratings derived | placeholder, filtered |
| R1 | value | 75 / 75 | limited_data | missing inputs | placeholder, filtered |
| R1 | contextual | none | | every signal missing on both sides | not emitted; 0 bars shown |
| R2 | reviews | 88 / 89 | "0.2 stars higher" | real ratings 4.6 (85) and 4.8 (6,600) | REAL |
| R2 | longevity | 92 / 96 | "Longer-lasting" | specs empty, so spec_secondary = review score: (4.6-1)/4*80+20 = 92, (4.8-1)/4*80+20 = 96 | PROXY (stars) |
| R2 | projection | 92 / 96 | "Stronger projection" | the review score | PROXY (stars) |
| R2 | presentation | 64.3 / 100 | "Better presented" | log10(85)/3 = 0.643; log10(6600)/3 > 1, capped 1.0 | PROXY (rating count) |
| R2 | price, value | 75 / 75 | limited_data | YSL price pended | placeholder, removed by pricePending |
| R3 | versatility | 50 / 30 | "More versatile" | Armani: no fact-check data, the 50 default; Versace: 30 = a reliability of 0.3, which is exactly the weight of an all-unverified fact-check (SS:2096); LIKELY one or more unverified specs. Versace's fact_check object itself was not read in this round: UNVERIFIED | DEFAULT-50 WIN; `winner` None, but the bar paints Armani and line1 says "Armani Acqua di Gio Profumo leads on Versatility." |
| R3 | price, reviews, value | 75 / 75 | limited_data | Armani price pended, ratings derived | placeholder, filtered |

So of the five bars the owner saw across three results, one (R2 reviews) came from real data; three were star or count proxies; one was a default-50 against a data-quality score.

## (d) key_differences: every producer and consumer

### Producers

| Path | Where the body is built | What `key_differences` holds | file:line |
|---|---|---|---|
| Text, REST POST / GET | `build_comparison_response` (RB:1461), called at SCS:3880 and SCS:4783 | `[]`, unconditionally, after every other alias is set | RB:2297 |
| Text, stream (SSE) | an early progressive payload sets `"key_differences": []` (SCS:5647); the final body goes through `build_comparison_response` (SCS:5676) | `[]` (RB:2297) | SCS:5647, RB:2297 |
| Camera | image_routes.py:610-614 calls `service.compare_from_text(...)`, which builds through the same RB function | `[]` (RB:2297) | RB:2297 |
| Link (URL) | `compare_from_urls` returns its OWN body (url_extraction_service.py:1500-1509: products, comparison, winner_index, recommendation, key_differences, category_used, source_urls; no `scoring_v2`, no `overview`); a verdict error returns `success:false, code LLM_UNAVAILABLE` (url_extraction_service.py:1483-1493) | flag OFF: `comparison.get("key_differences", [])` (:1498): the AI verdict is not asked for this key (no prompt hit in a grep of app/ for "key_differences"), so LIKELY `[]`; ENABLE_URL_MODE_V2 ON: the English AI `specs_comparison.product_0/1_advantages` strings (`_v2_verdict_fill`, :1534-1565) | url_extraction_service.py:1495-1506 |

The schema classes that declare the key (app/models/schemas.py:51 `List[str]`, app/models/product_schema.py:153) are not used as a `response_model` on any compare route (grep of app/ in this run: `ComparisonResponse` has no user). The ENABLE_URL_MODE_V2 production state is UNVERIFIED here.

### Consumers

| Consumer | What it does | file:line |
|---|---|---|
| CL (= OTA) | reads it into a local constant and never renders it | RS:437 |
| ST 683f56c0 | the same | ST RS:414 |
| Both bundles' types | `key_differences: string[]` | CL types/types.ts:146, 299, 527; ST types/types.ts:144, 297, 517 |
| Both bundles' strings | a heading key already exists and is unused: `results.keyDifferences` = "Key Differences" / "الفروقات الرئيسية" | CL en.json:134, ar.json:131; ST en.json:141, ar.json:138 |
| Server share | the invitee view drops it when the sharer turns reasons off | referral_service.py:178 |
| Web landing / share page outside this repo | UNVERIFIED (not in the export) | n/a |

So NO client bundle renders key differences today, and filling the frozen `string[]` key with any value is invisible on both live bundles' result pages.

### Data that exists at response-build time from which a list can be built WITHOUT an AI call

All of these are on `product_data[i]` or `scoring_result` inside `build_comparison_response` before RB:2297.

| Fact | Field | Deterministic? | Present on R1 / R2 / R3 |
|---|---|---|---|
| Shelf price and currency | `price.amount`, `price.currency` | yes (store readers, T2) | 1 of 2 on each row (the other pended) |
| Bottle size of the found listing | `price.size` (kept on a pended price, price_service.py:2005-2018), name text via `_product_size_text_fields` (price_service.py:2021-2040) | yes | Armani "40ml" (R3); others not established |
| Price per ml | amount / size | yes, when both are known | none today |
| Price source kind | `price.source_method` (genuine BH listing vs converted USD) | yes | yes |
| Real star rating and count | `rating`, `rating_count` / `review_count`, `rating_source`; derived ratings excluded (`rating_derived`, RB:855-870) | yes (Serper shopping rows) | R2 only |
| Concentration | from the name: `extract_concentration` (price_service.py:4076); from specs `concentration` when not a model guess (kb_ingest.py:219-225) | yes from the name | five of the six names carry "EDP"; whether `extract_concentration` reads "Profumo" as a concentration is UNVERIFIED |
| Longevity hours, sillage, scent family, notes, season, occasion | `specs.*` | NO in practice: the specs chain is AI extraction (T2: Redis 7d -> DB 30d -> AI extraction -> Tier 2 -> Tier 3, SCS:6824-6920); Tier 3 values are model knowledge and are marked (kb_ingest.py:166-248 uses `_tier3_fields`) | none (specs empty) |
| Spec rows that differ | `_build_specs_rows` (RB:735-772; both-sides-only rows) | deterministic over whatever specs exist | none |
| Real (non-proxy, both-sides) dimension winners | `scoring_v2.dimensions[*]` with `winner` not None and not `limited_data` | yes | R2 reviews only |
| Photo found or not | `image_url` | yes | R1 both, R2/R3 none |
| Availability in Bahrain | a genuine BHD listing vs none | yes | yes |

Conclusion for (d): without AI, a key-differences list can always state the price facts (amount, size, per-ml when both sizes are known), the rating facts (only when real on both sides), the concentration from the names, and, when specs exist, the spec rows that differ. On today's three rows it would hold one to two lines each (R2: the rating gap and one price; R1 and R3: one price plus the concentration line only if the two concentrations differ, which they do not here). That is the honest ceiling until the AI key works (N1) or the knowledge base serves specs (S5/S6).

## Deferred measurements (READ-ONLY round)

Nothing was run. The checks below are DEFERRED TO RED for the units that use this inventory:
- X6 / X5 / X7 backend: `python <SP>/harness/pyt.py --cwd <worktree> --tag inc-x6-... -- tests/test_inc_x6_*.py` (the runner's exact argument form is in the lane header H3/H5; the unit's brief names the comm set).
- X4 client: the full jest suite in the worktree after the H5(b) probe, plus `npx tsc --noEmit`, both DEFERRED TO RED.
- The claim "the category-profile accordion row never renders on a new-format body" (row 9a) is from code reading only; a jest render of a fixture body with `overview.products` would settle it at RED.
