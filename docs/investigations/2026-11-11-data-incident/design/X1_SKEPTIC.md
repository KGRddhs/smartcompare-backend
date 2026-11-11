# INC-X1 SIZE-FAIRNESS - SKEPTIC REVIEW of X1_MEASURE.md (read-only round, 2026-11-11)

Role: skeptic. Round class: READ-ONLY. Nothing was run: no pytest, jest, tsc, eslint, network, package manager, production probe or .env read, and no git command. Every file:line below was re-read in this run from the plain exports (backend and OTA client at a74caba7, store client at 683f56c0) and from the record copy. Short names follow X1_MEASURE.md: PS = app/services/price_service.py, SCS = app/services/structured_comparison_service.py, RB = app/services/response_builder.py, SS = app/services/scoring_service.py, ES = app/services/extraction_service.py, KI = app/services/kb_ingest.py, RG = app/services/result_gate.py, HR = app/api/home_routes.py, IR = record/incident/INCIDENT_AND_DATA_PLAN_2026-11-11.md, T1 = record/incident/T1_trace.md. Nothing here says a production problem is fixed; X1 is not built.

Verdict: SOUND WITH CORRECTIONS. The measurement of today's path is accurate in almost every citation, and design (a) remains the safer of the two designs. But the design as written breaks one of its own stated invariants (the verdict prompt), can print a size and a per-100-ml figure taken from a DEFAULT, can compare against a US-converted partner price, leaves the C1 winner decided by the blank while the new card would show the loser is half the price per ml, and its proof cannot pass the incident report's own proof rule. Each is listed with its correction.

## 1. Citations re-read: confirmed

| Claim in X1_MEASURE.md | Re-read | Result |
|---|---|---|
| Sync and stream callers of reconcile_pair_fairness | SCS:4586-4594, SCS:5339-5345 | confirmed; both wrap it in try/except and only log |
| Order: reconcile before scoring, verdict, builder, ingest | SCS:4646, 4677, 4747, 4783, 4878; SCS:5435, 5497, 5538, 5595, 5676, 5797 | confirmed for the FULL path (see 2.3 for the partial path) |
| Fragrances delegate to reconcile_pair_sizes | PS:3346-3351 | confirmed |
| make_pending_price shape | PS:2005-2018 | confirmed; size only when truthy |
| _mark_size_pending discards amount, retailer, url, title, source_method; keeps size only if present | PS:2402-2417 | confirmed |
| effective_pair_size_ml: name, title, size, specs; smallest token; flagship default | PS:2021-2045, PS:2048-2097 | confirmed (the designer helper starts at PS:2098, not 2100; trivial) |
| reselect_to_target_size: exact equality, stock and concentration under the exact gate, is_price_showable, genuine-BH first | PS:2170-2256 | confirmed; NOTE it also accepts converted_usd candidates (docstring PS:2175-2178), which matters for 2.5 |
| reconcile outcomes 1-3 and the target-None branch | PS:2259-2399 | confirmed |
| The chokepoint skips an already-pending price | RB:1711-1716 | confirmed |
| Overview price = public_price_view; legacy alias re-projects and pops _shopping_listing_count by name | RB:1951, RB:2262-2267, PS:9371-9387 | confirmed; only guard_rejected and _-keys are stripped, so a new public key passes through; with ENABLE_EXACT_PRICE_GATE OFF the price is returned unchanged (PS:9381-9382) |
| _price_candidate needs both amounts; price sentences | RB:873-894, RB:1085-1089 | confirmed |
| price_raw None when amount falsy; lone priced side 75; value missing when spec OR price missing; _dim_price limited_data | SS:1768-1778, SS:2449-2470, SS:330-331, SS:3240-3262 | confirmed |
| Verdict projection strips _-keys and re-pends a non-showable price keeping currency, reason and size | ES:2506-2532 | confirmed (and see 2.1) |
| D05 price unknown/no_price for a pend; size known/listing only from price.size | KI:193-218, KI:147-152, RG:213-224 | confirmed |
| OTA renders 'none' for an unavailable price unless the field entry is unknown | fieldStatusView.ts:58 @a74caba7 | confirmed |
| Neither bundle reads price.reason or price.size | grep of both src trees, tests excluded | confirmed: size_mismatch only in comments ResultsContent.tsx:137 @683f56c0 and :190 @a74caba7; record/s80/contract_freeze.json lists only price.amount, price.currency, price.source_method, price.unavailable |
| Pending text and keys | en.json:156 / ar.json:153 @683f56c0; en.json:149 / ar.json:146 and notListed en.json:705 / ar.json:702 @a74caba7 | confirmed |
| pricePending hides price and value bars and the price pill | ResultsContent.tsx:159, :490, :526 @683f56c0; :212, :557, :593 @a74caba7 | confirmed |
| Variant line from specs (volume_ml, concentration) | RB:553-610 | confirmed |
| No per-ml computation; the only per-unit code rejects unit prices | PS:13462-13470 | confirmed by grep |
| Home savings and Profile skip a null amount | HR:167-192, HR:284-290; profile_routes.py:340-346 | confirmed |
| No client reads value_badge; priceDiff computed, never rendered | grep; ResultsScreen.tsx:679/:697 @683f56c0, :718/:736 @a74caba7 | confirmed |

## 2. Wrong or incomplete claims

### 2.1 The design breaks its own "verdict prompt byte-identical" invariant

Section 5.0 puts the size fill inside `_mark_size_pending` ("fills the existing optional size key from the listing"), while section 5.1 says the projection happens "AFTER scoring and the verdict call, so neither the prompt bytes nor the scores change", and risk (4) says the verdict prompt must stay byte-identical flag ON vs OFF. These contradict each other. `_mark_size_pending` runs inside the reconcile (PS:2402-2417), before `generate_comparison` (SCS:4677, SCS:5538), and the verdict projection copies `price.size` into the pending dict it sends to the model (ES:2529-2532). So flag ON, the Layton prompt carries `"size": "125ml"`; flag OFF it does not. Beyond byte identity, this hands the model an unchecked size fact beside `size_mismatch`, inviting a prose claim no guard checks.

The same early fill also changes, flag ON: the D05 size entry (KI:210-211 turns `known / listing`) and, once the ingest flag is ON, a KB variant row for Layton at 125 ml with no offer (KI:433-440 build the variant row from `_size_ml(price)` before the genuine-method test at KI:443-446). Arguably correct data, but an unlisted side effect.

Correction: do the size fill AND the listing projection in RB at the chokepoint (after the verdict), reading the product-level stash; keep `_mark_size_pending`'s output byte-identical flag ON; pin the verdict user message flag ON vs OFF on the C1 fixture.

### 2.2 The Serper candidate size is not "the smallest ml in the title"

Section 1.4 says the Serper candidate `size` is the smallest ml in the title. The code is `sorted(extract_sizes_ml(title))[0] + "ml"` (PS:10587-10588) over a set of STRINGS (PS:4087-4093): the sort is lexicographic, so "50ml / 100ml" yields "100ml". Also the regex `(\d{1,4})\s*(?:-?\s*)ml\b` (PS:4073) reads "7.5ml" as 5 ml and never matches an Arabic-only title. L4 must re-parse the title itself, never trust a candidate's `size` key, and refuse a decimal before "ml".

### 2.3 "Every consumer only ever sees make_pending_price" is false for the partial path (resolves an UNVERIFIED item)

Measured: the sync stash is the same list object (`self._partial_product_data = product_data`, SCS:4551, before the reconcile at SCS:4586), but `_build_partial_response` (SCS:3798 onward) never calls `reconcile_pair_fairness` (grep: the only callers are SCS:4587 and SCS:5340). The stream hard-cap partial (SCS:5268-5279) fires BEFORE the stream reconcile (SCS:5339) and builds from the early buffer, which counts "specs OR a price" as usable (SCS:3683-3685). So a partial body can carry two sticker prices at different sizes, un-reconciled, through a chokepoint that does not compare sizes. Pre-existing and not X1's by default, but the X1 spec must state it as a limit, and the phone proof must reject a partial body as evidence.

### 2.4 "Layton gets ... a computed value" under design (b)

The value signal is missing whenever the SPEC signal is missing (SS:330-331), and both C1 products had `specs = {}` (T1:110, T1:125; T1:172 "C1 all 6 dims missing for both"). With specs still empty the value dimension stays flagged missing on both sides; only the price signal changes. "Winner LIKELY moves to Layton" may still hold through price, but how today's Aventus wear_value reached 75 while flagged missing (T1:176) is traced in neither document and must be measured at RED before any winner prediction reaches the owner.

### 2.5 The partner's size_ml and per_100ml can come from a default, and the partner can be US-converted or global-tier

Section 5.1's row for the OTHER side says the keys appear when "that side's listing size is known (L4 rules)"; it does not require the partner's OWN listing to state its size. Today a partner is "at target" when `effective_pair_size_ml` returns the 100 ml flagship DEFAULT for an unsized designer name or under the fix flag (PS:2084-2097), and the reconcile treats that as on-basis (`_resolve_to_target`, PS:2364). Reusing the effective size prints "100 ml" and a per-100-ml figure no store listed: a default presented as a fact. The truth tables hide this because both partners happen to carry "100ml" in their stored titles (T1:117 "Aventus EDP 100ml"; T1:140 "L'Eau De Parfum 100ml").

The partner can also be `converted_usd`: `reselect_to_target_size` accepts converted candidates (PS:2175-2178) and `is_price_showable` allows them (PS:1893-1895). Design (a) would print a per-100-ml line for a US-converted partner next to a Bahrain listing; design (b) would compare them per ml and move the winner on it. And L2 tests only membership of `_GENUINE_BH_SOURCE_METHODS` (PS:17065-17087); the apple-phantom guard in `_is_genuine_bh_candidate` (PS:17090-17105) also excludes a registry GLOBAL-tier domain stamped with a genuine method, so a brand's global site stamped `page_scrape_jsonld` or `official_brand` passes L2 as written.

Correction: (i) the partner's `size_ml` / `per_100ml` only when the partner's own listing passes the same L4 one-token test on its own size/title, never from a name, spec or default; (ii) L2 = genuine method AND not global tier (the `_is_genuine_bh_candidate` semantics), applied to BOTH sides: no per-ml line on a converted or global-tier partner, and (b)'s `size_basis` only between two genuine Bahrain listings.

### 2.6 The recommendation hides a default that keeps winning

Section 5.1 calls "scores, verdict and winner unchanged" a virtue and says the C1 weakness is stated. It is in the body, NOT in the owner question. Today's C1 winner was decided because Layton's price was blanked: wear_value 75 vs a 50 default, margin 1.4 (T1:176). The row also carries `winner_evidence` "has a confirmed Bahrain price while the other relies on an indicative figure" (SS:1007-1008, surfaced at RB:1324-1346), false for a size pend; no client bundle reads `winner_evidence` (grep: none), so it is a saved-row falsehood, not a screen one. After the X1 client OTA, design (a) shows Layton at 68.000 BHD per 100 ml beside Aventus at 133.460 BHD per 100 ml under an Aventus crown that partly exists because Layton's price was blanked: a default still winning, now more visible.

Correction: N5b (a) must say the winner stays as today and that today's winner can come from the blank; offer (a2): when one side is a size pend, treat the price signal as missing for BOTH sides in scoring (scores and winners can change on both live bundles; needs its own ruling). The `winner_evidence` price reason must not fire when the runner-up's price is a size pend.

### 2.7 The proof cannot pass the incident report's proof rule as written

Risk (6) catches only the `price.amount not null` conflict with IR:100. It misses:
- IR:162 rule (c): the deploy log for the proof minutes must have none of the targeted failure markers, and it names `size_mismatch`. Under both designs the reason stays `size_mismatch` by construction, so (c) fails forever. Restate the X1 marker (for example: no `size_mismatch` pend WITHOUT the listing block on a LISTABLE side).
- IR:147-149: the completeness score counts a price only when `price.amount` is not null, so C1 stays at 1 price under (a) and (b) and the daily golden-set run (IR S8) never registers X1. The score needs a ruled addition.
- The cache: T1:179 shows bodies are written to cache. A repeat within the TTL can return a pre-flip body (no listing block); after a rollback a flag-ON body keeps being served until its TTL, so rollback is not byte-identical for the TTL (still UNVERIFIED). The proof must cite a row with `cache_hit: false`.

A proof that could pass while the problem remains: "Layton shows a BHD price with its size" passes if the size is wrong (2.2), name- or default-derived (2.5), or the listing is the wrong product (the Versace "for Women" class, T1:59). The backing check must assert the listing title contains the exact shown ml token, the listing url host equals the host of the log's direct-hit line for that minute, the method is genuine and not global-tier, and the partner's shown size appears in the partner's own title; and name the bundle of the screenshot (the store binary shows nothing new until it takes the OTA).

### 2.8 Smaller gaps

| # | Gap | Evidence | Correction |
|---|---|---|---|
| G1 | Missing consumer: the Home smart-pick tile renders both sticker prices on both bundles | HR:571-574 (skips a null amount), HR:680-681; HomeEditorialSections.tsx:172-176 and :218-222 in both trees | (a)/(b) keep the amount null, so the row stays skipped: no change. Add it to the (b2) rejection (un-pending prints cross-size prices side by side on Home). The store binary still has the savings banner (HomeEditorialSections.tsx:322-329 @683f56c0; removed @a74caba7, :9-10). |
| G2 | The key name `listed` collides with the D20 provenance kind 'listed' (the "Listed on" line) | fieldStatusView.ts:21, :69; ResultsContent.tsx:168-174 @a74caba7 | Use a distinct name (for example `offsize_listing`). |
| G3 | The D05 change reports a pending price as fresh/stale | KI:193-203; field_status is persisted on compare runs (compare_runs.py:55, :297, :477) | A known price state with a null amount inflates any coverage count read from field_status. Prefer a non-'unknown' state that says other-size (the OTA tests only `state === 'unknown'`, fieldStatusView.ts:52, :58) and rule it. |
| G4 | Digit policy covers only the amount | the proposal routes only the amount via utils/formatNumber.ts:96 | Every number in the new strings (125, 100, the per-100-ml figure) goes through the app digit system. |
| G5 | X1's client half overlaps X4 ("price with size") | IR:103 | One price-card design for both, so the owner reads the Arabic once. |
| G6 | Store-binary claims | the 683f56c0 source | No contradiction found: no fieldStatusView.ts there, the pending key renders, unknown keys are ignored. |
| G7 | Proposed strings vs copy policy | CLAUDE_md_a74caba7.txt:265; services/sourceMethod.ts:13-15 | The English strings contain no forbidden word and duplicate no key (the only size key is results.spec.size). The Arabic is not written yet: UNVERIFIED, goes to the owner's native read. |

## 3. Owner questions: what they hide

- N5 must add: answering "show it" changes nothing on either live app until a client OTA the owner approves (said in section 7, but outside the quoted question).
- N5b (a) must add: the winner stays as today, and today's winner can come from the blank (2.6); offer (a2).
- N5b (b) must add: the moment the flag flips, both live apps can crown a different winner while still showing "No confirmed price yet." for it, with no visible reason, until the client OTA; and it applies only between two genuine Bahrain listings (2.5).
- Silently defaulted: the basis is always the 100 ml flagship (PS:1439) even for a house whose flagship is another size (Layton 125 ml, T1:117). That default is what pends Layton at all; the owner is not asked.

## 4. Assumptions

- The partial-path exposure (2.3) is real but its frequency is unknown: the stream hard cap is a production path with its own handler (SCS:5268-5279), not dead code.
- A RED implementer would reuse `effective_pair_size_ml` for the partner size unless the spec forbids it, since it is the only partner-size function on the path; so 2.5 is a spec correction, not a hypothetical.

## 5. UNVERIFIED in this round

How the C1 wear_value reached 75 while flagged missing; whether the stream early buffer held prices in any incident row; the response-cache TTL; whether any global-tier domain has produced a genuine-method fragrance price in production; the Arabic wording of the new strings; whether the Layton and Libre titles carry an ml token (unchanged from X1_MEASURE.md).
