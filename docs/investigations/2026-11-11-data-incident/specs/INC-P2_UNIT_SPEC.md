# INC-P2 PRICE-NOT-LOST - unit spec (measured, READ-ONLY round)

- Unit: INC-P2 PRICE-NOT-LOST (absorbs INC-P1 and INC-X1). Closes investigation 2026-11-15 rows 4, 5, 6 and the guard part of row 7; T3-01, T3-02, T3-03, T3-04, T3-06, T3-07, T3-08, T3-10 (T3_prices.md; V2 section 3, missed points 6, 8, 9).
- Flag ruling (P2-1): ONE new dark flag `ENABLE_PRICE_NOT_LOST` (default OFF, house idiom, read per call as the FIRST statement of every predicate that uses it). Flag OFF is byte-identical in every response key, status, cache write and log line EXCEPT the three unflagged INFO lines of P2-11 (`PRICE_OUTCOME`, `PRICE_CACHE_HIT`, `PRICE_CACHE_SKIP`). No knob: none was measured as needed (section 2.1).
- Worktree `C:/Users/SynAckITPC/Documents/AI/sc-inc-p2` (detached), branch GREEN creates `fix/inc-p2-price-not-lost`. Base sha `b0ad260363e0cf0074e4ee596b140d073466e92a` (origin/main, the merge of #410 INC-R1). `git rev-parse HEAD` = the base sha; `git status --short` EMPTY at the start and after every probe of this round (the only file written in the worktree is this spec under the gitignored `.qa-s80/`; `.gitignore:72 .qa-*/`).
- Evidence pointers: the orchestrator brief `<SP>/INC-P2/INC_P2_BRIEF.md` (P2-1..P2-16, Q1..Q10); the investigation `.../investigation-2026-11-15/` FINDINGS_AND_FIX_PLAN_2026-11-15.md (section 2 rows 4-7, section 4 INC-P2), T3_prices.md, V2_adversarial_review_pictures_prices_speed.md, T7_client.md (all cited at 6104eebd, every line re-measured here at b0ad2603); the INC-X1 record (`<SP>/docsx/.../specs/INC-X1_UNIT_SPEC.md`, `INC-X1_SPEC_REVIEW.md`, `RULINGS_INC_X1.md`: X1-R1, X1-R3, X1-R7, X1-R9, X1-R11, X1-R12 carried over as P2-5 restates them); INC-R1 as merged (`app/services/product_resolver.py::apply_resolution`); `<SP>/record/inc/PAGE_DESIGN_V2.md`; `<SP>/record/s80/PLAN_S80.md` section 0 + `contract_freeze.json` (re-read before section 2: the frozen price paths are only `price.amount`, `price.currency`, `price.source_method`, `price.unavailable`; `metadata` and `metadata.partial` frozen as present; additive only; never a bare 503); RULINGS_INC_R0 (R0-1 proof standard, R0-9 read-only rounds).
- Measurement location `<SP>/INC-P2/spec/`: `base/` (plain `git show HEAD:<path>` exports of the read modules, LF; deleted at the end of the round, re-creatable with the same command), `probe_re.py` + `probe_re.out` (the size-token probes on the pinned CPython 3.12.9 `re`, run with `-I`, no pytest), `all_tests.txt`, `comm_set_full.txt` (sha256 b6545390e3f84fad0ad3831d49830ca5d9258c6ba4cb463bd4721d5dcd98f067), `caplog.txt`. No pytest, jest, tsc or eslint was run (H5 c); every run below is DEFERRED TO RED with its command.
- Sister units and contracts: INC-I2 (main lane, S96) OWNS `app/services/image_relevance.py`, `app/services/image_service.py` and SCS Phase 1 (`_fetch_product_data`, SCS:6018-6906 at base, the Phase-1 race about 6030-6450): this unit edits none of them (Q6); the second lane to merge rebases. INC-C1 / the X4 price card (client): the size label and the per-ml line ride there (P2-16); this unit ships keys only. INC-L1 owns the 15 s race timing (P2-16). INC-S1 owns the Claude JSON parse. INC-R1 (merged, dark): `ENABLE_PRODUCT_RESOLVER` changes the Step-1 dicts this unit reads (Q1). D03 (`ENABLE_DATA_GUARDS_V2`, absent on web): its deny list is NOT reused (Q3). S81-17 D05 / S81-18 KB-FIRST-SERVE: read only (Q8).
- Personal-data rule: no personal value anywhere. Test hosts are `*.example.com` (store-a / store-b / reseller-c) except the seller NAMES the guard must match (`Whatnot`, `eBay`), which are public marketplace names, and public perfume names with the logged prices of P2-14. No real listing URL, no account id, no key-shaped literal; any digest is built at run time; every file pure ASCII and LF.
- Short names: PS = app/services/price_service.py, SCS = app/services/structured_comparison_service.py, RB = app/services/response_builder.py, TR = app/api/text_routes.py, PR = app/services/product_resolver.py, SS = app/services/scoring_service.py, ES = app/services/extraction_service.py. Every file:line below was read at b0ad2603 in this round.

## 0. What the unit does

Today, after both prices are found, the fragrance pair check `reconcile_pair_sizes` (PS:2259-2399) takes ONE target for both perfumes: the SMALLEST ml in the combined "A vs B" text, else a fixed 100 ml (PS:2325-2329, PS:2142-2148), and REPLACES the found price of any side that cannot be re-selected to exactly that size with a pending dict (PS:2402-2417, reason `size_mismatch`). The phone then shows "No confirmed price yet". A re-selected price is never cached (a cache hit carries no candidates, SCS:7188-7190), a typed "100 ML" makes `numbers_match` (PS:3871-3877) reject every listing title without a bare "100", a genuine Shopify reseller hit lives only in a local and is lost on a race miss (SCS:8177, 8268), and the converted race-miss fallback can be an auction seller (Whatnot). None of these seams prints a line.

Behind `ENABLE_PRICE_NOT_LOST` this unit:
1. (P2-2, P2-3) replaces the fragrance branch of the reconcile with `reconcile_pair_sizes_v2`: each side keeps its OWN typed size (read from that side's own name, equal with the resolver ON and OFF); with no typed size it keeps today's common-size re-selection when both sides reach a common size (100 ml preferred, else the largest common size); otherwise NEITHER side is pended for size: each keeps its found showable price;
2. (P2-4) projects, for every server consumer that compares the two amounts, exactly the inputs it receives today when one side is size-pended (the pended dicts flag OFF would have produced), and keeps the real shown price in a private product key that RB restores only into the wire copies (overview, legacy alias, SSE `prices`), after running the chokepoint's own checks on it;
3. (P2-5) stamps additive `price.size_ml` and `price.per_ml` on every shown fragrance price whose own listing yields exactly one strict size token, and the pair marker `metadata.pair_price_sizes` (same step in every build, partials included);
4. (P2-7) writes a re-selected shown price to the price cache under the key the next identical request reads, through `should_cache_price` and the existing TTLs;
5. (P2-8) makes `numbers_match` ignore ml / oz size numbers on the product side, for every caller;
6. (P2-9) parks a genuine Shopify reseller hit ahead of a converted park and seeds it as a candidate;
7. (P2-10) skips auction / marketplace sellers in the Tier-1 Shopping pick, in the converted parks and in the re-selection;
and, UNFLAGGED (P2-11), prints `PRICE_OUTCOME` once per product per build at the RB chokepoint, `PRICE_CACHE_HIT` on every L1 / L2 price hit and `PRICE_CACHE_SKIP` with the refusal reason at the two genuine cache-write sites.

Nothing on any phone changes until the relay flips the flag (both bundles read `price.amount` and `price.unavailable` only; neither reads `size_ml`, `per_ml` or the pair marker: Q2). After the flip the phone shows a found price instead of "No confirmed price yet" where this unit's rules keep it; that is the proof of section 8b, not a suite.

## 1. Base state (measured at b0ad2603)

### 1.1 The fragrance reconcile (PS)

| what | where | measured fact |
|---|---|---|
| pending shape | PS:2005-2018 `make_pending_price(currency, reason, size)` | `{"amount": None, "currency": currency or "BHD", "unavailable": True, "reason": reason}` + `size` only when truthy. |
| size fields | PS:2021-2045 `_product_size_text_fields` | order: `full_name`, `name`, `price.title`, `price.size`, `specs.volume/size/concentration`. |
| effective size | PS:2048-2095 `effective_pair_size_ml(p, treat_unsized_as_flagship)` | the MIN `extract_sizes_ml` token of the FIRST field holding one; none: 100.0 for a designer name (`_is_designer_fragrance_name`, PS:2098-2111) or under the fix flag, else None. Reads `full_name` FIRST, so a typed size in the name wins over the listing's own size. |
| target | PS:2114-2148 `target_pair_size_ml(user_query, p0, p1, flag)` | `min(extract_sizes_ml(user_query))` of the WHOLE query; else 100.0 (`_FRAGRANCE_FLAGSHIP_SIZE_ML`, PS:1439) when both names are designer or under the fix flag; else None. |
| candidate size | PS:2151-2166 `_candidate_size_ml` | raw_data then candidate, `size` then `title`, min ml token. |
| re-selection | PS:2169-2256 `reselect_to_target_size(name, cands, target_ml, currency)` | pure; exact `size == target_ml` (PS:2197-2198); under the exact gate skips OOS and concentration mismatch (PS:2234-2239); requires `is_price_showable(name, price)` (PS:2246); ranks genuine-BH, `variant_rank`, cheapest. Includes `converted_usd` candidates. |
| the reconcile | PS:2259-2399 | no-op unless both amounts > 0 (PS:2302-2309) and no estimate side (PS:2318-2321); `user_size = min(extract_sizes_ml(user_query))` (PS:2325-2329); fair already when no user size and `eff0 == eff1` (PS:2338-2341); target None -> legacy compare, both pend on any difference (PS:2346-2354); else `_resolve_to_target` per side (PS:2359-2381, swaps `p["price"]`, `best_price`, `retailer` in place) and outcomes 1-3 (PS:2383-2399). No logger call. |
| the pend | PS:2402-2417 `_mark_size_pending` | `p["price"] = make_pending_price(currency, "size_mismatch", size=price.size)`; `best_price` / `retailer` -> None when present. The found price is dropped. |
| fragrance entry | PS:3301-3351 `reconcile_pair_fairness` | `canon == "fragrances"` -> `reconcile_pair_sizes(..., treat_unsized_as_flagship=frag_reconcile_fix_enabled())` (PS:3346-3351). |
| fix flag | PS:4905-4923 `frag_reconcile_fix_enabled` | `os.getenv("ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX", "false").strip().lower() in ("true","1","yes","on")`: the house idiom. |
| ml / oz readers | PS:4073 `_SIZE_ML_RE`, PS:4087-4093 `extract_sizes_ml`, PS:4099 `_SIZE_OZ_RE`, PS:4122-4145 `extract_size_ml_any` (ml plus oz snapped to a standard bottle, min) | `extract_size_ml_any` is what PR uses for `side.size_ml` (PR:672). |
| numbers_match | PS:3871-3877 | a 2+ digit word-bounded number set over the product name; empty -> True; else any shared number with the title. "100ml" yields no token, "100 ML" yields {100} (probe_re.out). |
| exact gate | PS:4370-4374 `exact_gate_enabled` | default ON. |
| cache gate | PS:9343-9423 `should_cache_price(request_name, price, category, *, warm_context)` | True when the exact gate is OFF; False on a non-dict, no title, no url or a listing url, `in_stock is False`, an electronics accessory, a failed `_selection_match` + `_structured_code_cache_override`, a failed `_brand_evidence_ok`, or `warmer_write_veto`. Returns a bare bool: no reason is exposed. |
| public view | PS:9426-9438 `public_price_view` | the SAME object when the exact gate is OFF; else a NEW dict without `guard_rejected` and `_` keys. |
| cache key | PS:9487-9542 `build_size_aware_price_cache_key(brand, name, variant, region, identity_text, category)` | gate ON: `_identity_cache_token(name variant identity)`; none -> `get_price_cache_key`; else `generate_cache_key("price", brand, _strip_identity_axes(name), ..., region, token)`. |
| Tier-1 pick | PS:10407-10660 `extract_price_from_shopping` | D03 drop only under `data_guards_v2_enabled()` (PS:10435-10438); loop PS:10466; `retailer = item.get("source")` PS:10568; `is_marketplace_reseller` only LOWERS `retailer_score` (PS:10581-10583); candidate dict PS:10629-10646 (`size` = min ml of the title). |
| marketplace names | PS:376-380 (retailer score tier 3), PS:9621-9626 (`_THIRD_PARTY_HOST_MARKETPLACES`, `_USED_GOODS_MARKETPLACES`), PS:9629-9654 `is_marketplace_reseller`; ES:934-939 (prompt text) | no "whatnot" anywhere in app/ (git grep). |

### 1.2 Where the reconcile runs and where the body is built (SCS, TR)

| what | where | measured fact |
|---|---|---|
| phone route | TR:959-1060 GET `/compare` (`q` or `product_a` + `product_b` -> `explicit_pair`, TR:996-998); POST TR:734-815; stream TR:1171-1340 | both bundles call GET `/api/v1/text/compare` with `{product_a, product_b}` or legacy `q` (api.ts 683f56c0:639-703, HEAD:672-742); the stream URL only when the client stream flag is on (683f56c0:828-844, HEAD:882-899). |
| explicit-pair dicts | SCS:4478-4493 (sync), SCS:5193-5206 (stream), SCS:1966-1978 | `{"brand": "", "name": safe, "variant": None, "category", "search_query": safe, "_explicit": True}`; then INC-R1's hook under `ENABLE_PRODUCT_RESOLVER` (SCS:4497-4503 / 5210-5216 -> `apply_resolution`, PR:1303-1328: brand, name = line, variant = "<CONC> <n>ml" or None, search_query = brand + line + concentration, never the size). |
| product dict | SCS:6018-6053 `_fetch_product_data` (INC-I2's region; read only) | `full_name, display_name = _product_display_identity(...)` (SCS:1377-1393: text path `full = dedup_brand_name(brand, name + " " + variant)`, display = `name`); `result = {"brand", "name": display_name, "full_name", "variant", "category", "query": search_query}`; `_get_price(brand, name, variant, region, search_query, nocache, category)` at SCS:6138 with `category = canonicalize_category(product_info.get("category"))`. No later write to `full_name` / `name` in SCS or RB (git grep). |
| per-request state | init SCS:3393, 3400; reset SCS:4393-4394 (sync impl), SCS:5127-5128 (stream) | `self._parked_price`, `self._price_candidates`, keyed by `_shopping_cache_key(brand, name, variant)` (SCS:1287-1294, used at SCS:7324). |
| sync reconcile | SCS:4660-4667 | `reconcile_pair_fairness(product_data, query, category_used, candidates_by_name=self._price_candidates)` in try / except WARNING; `query` = the combined "A vs B" text. `self._partial_product_data = product_data` at SCS:4626, before it (same objects). |
| sync consumers | SCS:4668-4700 (prescoring guard, region guard), 4721-4724 `compute_scores`, 4743-4749 `log_verdict_key`, 4752-4761 `generate_comparison`, 4788 `validate_verdict`, 4823 `apply_value_badges`, 4826-4834 `compute_tradeoff_pairs`, `compute_confidence`, 4859-4888 `build_comparison_response` | all read `product_data` in place. |
| stream reconcile | SCS:5428-5434 | the same call. |
| SSE prices | SCS:5495-5518 | per product a NEW payload `{"brand","name","price": public_price_view(_price),"best_price","currency","retailer"}` after its own showable check. |
| builders | SCS:3910 (`_build_partial_response`, def SCS:3828), SCS:4859 (sync), SCS:5766 (stream) | every body with products is built by `build_comparison_response`; the sync partial reads `self._partial_product_data` (the reconciled objects); stream partials read the early buffer (not reconciled). |
| entry | SCS:4172 `compare_from_text`; `asyncio.wait_for(self._compare_from_text_impl(...))` SCS:4238; timeout partial SCS:4271-4272 in the OUTER context | the impl runs in the wait_for task (a context copy). |

### 1.3 The price path and its cache (SCS, price region)

| what | where | measured fact |
|---|---|---|
| cache key | SCS:7176-7178 | `cache_key = build_size_aware_price_cache_key(brand, name, variant, region, search_query, category=category)`. |
| L1 hit | SCS:7182-7190 | `_cache_get_async`; a poisoned entry dropped with an INFO line; a hit sets `cached["_cached"] = True` and RETURNS SILENTLY. |
| L2 hit | SCS:7192-7262 | `get_cached_price(cache_key, region)`; promotion lines only on refuse / skip; `_l2_age` popped (SCS:7240); `db_price["_cached"] = True`, `["_cache_source"] = "db"`, return (SCS:7260-7262). |
| race-miss fallback | SCS:7060-7141 `_price_fallback_on_miss` | under `ENABLE_GENUINE_PRICE_PRIORITY` a completed genuine candidate from `self._price_candidates` first (SCS:7080-7119); else the parked price (SCS:7120-7127, INFO "race miss ... returning parked"). The returned dict carries no marker that says "parked". |
| adapter direct hit | SCS:7940-7960 | seeds observed alternates; `if should_cache_price(full_name, best, category):` cache + DB, else SILENT (SCS:7950-7953). |
| converted park (adapters) | SCS:7885-7897 | `_conv_best = select_best(converted observed)`, parked only when nothing is parked by this local (`converted_fallback is None`). |
| Tier-1 park | SCS:8079-8101 | a `converted_usd` Tier-1 pick parked at SCS:8086; a genuine listing-url Tier-1 under `_park_listing_url_tier1_enabled()` parked at SCS:8101. |
| Shopify reseller | SCS:8177 `shopify_fallback = None`; SCS:8266-8272 (reseller hit kept in the LOCAL, INFO line); SCS:8763-8787 used only after the waves | not parked on self, not seeded (the official branch seeds `shop_results` at SCS:8251-8254). |
| persist helper | SCS:9415-9431 `_persist_genuine_price` | `if not should_cache_price(full_name, price_obj, category): return` SILENT; else `_cache_price_and_clear_sentinel` (L1 at `price_cache_ttl(price)`) + `_save_price_to_db` (L2). |
| KB serve | SCS:6115-6139 (INC-I2's region; read only) | under `ENABLE_KB_FIRST_SERVE` a KB price replaces `_get_price` and its eligible offers are seeded as candidates (SCS:6133-6134); `kb_serve._price_dict` (kb_serve.py:216-235) sets `title` "<brand> <name> <conc> <n>ml", `size` "<n>ml", `_cached` True, `_cache_source` "kb". |

### 1.4 The builder (RB)

| what | where | measured fact |
|---|---|---|
| chokepoint | RB:1636-1766 | per product: non-dict -> pending; harvests; `if _price.get("unavailable") is True: continue` (a size pend keeps its reason); region guard (pending_genuine); `is_price_showable(_name, _price, _cat, enforce_correctness=True)` else pending_genuine; whole loop in try / except WARNING. |
| comparing consumers in RB | RB:842-852 `_safe_price_amount`, RB:873-894 `_price_candidate`, RB:1101-1132 `_format_line2`, RB:1243-1390 `_build_scoring_v2` (RB:1309 `build_dimensions_v2(product_data, ...)` -> SS:3240 `_dim_price`, SS:3314 `_dim_value`; RB:1312 `_build_factual_verdict`) called at RB:2079 | all read `product_data[i]["price"]` AFTER the chokepoint. One side without an amount: `_dim_price` / `_dim_value` -> neutral scores + `caption_key: "limited_data"` (SS:3244-3249, SS:3349-3357); `_price_candidate` -> None. |
| overview price | RB:1951 `"price": public_price_view(pd.get("price"))` | the phone reads `overview.products` (ResultsScreen 683f56c0:408, HEAD:430). |
| metadata | RB:2095-2144, caller merge RB:2180-2181 | caller wins on a conflict. |
| legacy alias | RB:2227-2268 | ships the RAW product dicts: `pd["price"] = public_price_view(pd["price"])` IN PLACE (RB:2263-2264), `pd.pop("_shopping_listing_count", None)` (RB:2267), `result["products"] = product_data` (RB:2268). |
| cache flag | RB:49-81 `_compute_cache_observability` | `cache_hit` from `_cached` on any product price. |

### 1.5 What the two live bundles draw (P2-6, Q2; store binary JS 683f56c0 and the newest client commit on main 82172383 = the SmartCompareApp/src of the base)

| read | 683f56c0 | HEAD (82172383) | what it does |
|---|---|---|---|
| price line | ResultsContent.tsx:141-151 | :192-203 | `unavailable` -> "No confirmed price yet"; `amount === null` -> "Price N/A"; else amount + currency (+ the converted label). No size key is read anywhere in src (git grep `price?.size`, `size_ml`, `per_ml`: zero). |
| pending gate | ResultsContent.tsx:159 | :211 | `pricePending = products.some(p => p.price?.unavailable === true)`; when true the `price` and `value` bars are filtered out (:488-494 / :538-544) and the price pill hidden (:526 / :576). |
| bars | DimensionBars.tsx:82-88 (both) | same | every dim with `caption_key === 'limited_data'` (or a null score) is dropped, pending or not; RunnerUpWinsCard.tsx:57 (HEAD) drops it too. |
| value caption | DimensionBars.tsx:367-388 (both) | same | "cheaper of the two" etc. from SERVER `value_match_a/b` only. |
| client-side cheaper | ResultsScreen.tsx:678-686 `getPriceDiff` (cheaperIndex, percent from the two amounts), :697 `const priceDiff = getPriceDiff()` | :716-724, :735 | `priceDiff` is NEVER READ after its declaration in either bundle (git grep `priceDiff`: the two lines only). Dead code: nothing is drawn from it. |
| winner_evidence | not read (git grep) | not read | server-only (saved row). |

Plain words (the gate report quotes this): neither bundle computes or draws a "cheaper", savings, best-value or smart-pick claim from the two amounts itself; the only client price computation (`getPriceDiff`) is dead. Every comparison the screen draws (the price and value bars, the price pill, the value caption, the verdict text) comes from SERVER keys, and both bundles already drop a dim marked `limited_data`. So the server alone can stop a cheaper claim across unequal sizes (P2-4's projection makes the price and value dims `limited_data`); no STOP is needed. A residual: with both amounts shown, `pricePending` is false, so the bundles show the price CONFIDENCE pill from `scoring_v2.confidence_legs` (a confidence statement, not a cheaper claim; SL7). The Home "smart pick" card reads `/home/smart-pick` (HomeEditorialSections.tsx:64-125), a separate server route this unit does not touch.

### 1.6 Every server consumer that compares the two prices (P2-4, Q5)

| consumer | where | reads | one side size-pended today |
|---|---|---|---|
| raw price signal | SS:1760-1775 `_compute_raw_scores` | `price.amount` | that side `price_raw` absent -> MISSING path |
| normalized price / value | SS:2222-2240, SS:2360-2376, SS:1256-1310 `_compute_value_score` | price scores per side | missing side drops the price term |
| winner evidence | SS:988-1030 `build_winner_evidence` via SS:1627 | `_has_real_price` | may add the price-provenance sentence (not drawn by either bundle) |
| dims | SS:3240-3270 `_dim_price`, SS:3314-3360 `_dim_value` via RB:1309 | amounts | `limited_data`, neutral |
| factual verdict | RB:873-894 `_price_candidate`, RB:1101-1132 `_format_line2` | `_safe_price_amount` | None / no price line |
| verdict prompt | ES:2482-2549 `_verdict_safe_product` + the prompt rule ES:1093 ("PENDING PRICE ... do NOT make ANY price, value, cheaper ... claim") | the dumped product | the pended side has `amount: null` |
| fact-check of the verdict | trust_validation_service.validate_verdict (SCS:4788) | scoring + products | today's |
| value badges | SS:2671-2704 `apply_value_badges` (SCS:4823) | scores | today's |
| confidence | SS:1150-1253 `compute_confidence` (SCS:4834), RB:1772-1790 | price presence | today's (never High beside a pending price) |
| verdict cache key | kb_serve.py:420-461 `log_verdict_key` (SCS:4743) | product identity + scores | today's |

Smallest seam (measured): ONE projection applied in PS at the end of the flag-ON reconcile (before every consumer above): the side(s) flag OFF would pend carry exactly flag OFF's pending dict in `price`, the real shown price rides a private product key, and RB restores it only into the wire copies after `_build_scoring_v2` has used the projected view. No SS, ES or trust_validation edit (P2-12 ownership). The alternative (one helper read by each consumer) needs edits in SS (five sites) and ES: rejected.

### 1.7 numbers_match callers (Q7)

PS:3871 is called at PS:8867 (`_structured_code_cache_override`, i.e. inside `should_cache_price`), PS:9847 (`shopping_listing_matches`), PS:10534 (`extract_price_from_shopping`), PS:11800 (`extract_jsonld_price`), PS:15655 (`_match_shopify_product`), PS:15888 (`_bolo_jsonld_main_price`), PS:16348 (`_match_nasser_product`), PS:16820 (`_w04_parse_block`); algolia_service.py:642, :721; magento_graphql_service.py:938; noon_service.py:233; occ_service.py:154; rating_service.py:167 (`extract_rating_from_shopping`); rest_json_service.py:131; salla_service.py:162; shopify_pdp_service.py:1029; sitemap_discovery_service.py:802 (slug match); unbxd_service.py:136; woocommerce_service.py:213; zyte_service.py:374, :574; SCS:3499-3500 (`_numbers_match` static wrapper); scripts/diag_zyte_match.py:86 (diagnostic script). Effect of P2-8 (probe_re.out, pinned CPython 3.12.9): a product-side number inside an ml / oz token no longer has to appear in the title ("Dior Sauvage 100 ML Edp" now passes "Sauvage EDP 100ml", "Dior Sauvage EDP 100ml/3.4oz", "DIOR Sauvage Eau de Parfum Spray"); every other number still must ("Baccarat Rouge 540 70 ML" still needs 540; "Le Labo Santal 33 100 ML" still needs 33; "Creed Aventus 100 ML 2024" still needs 2024); a product name with no ml / oz token is unchanged byte for byte ("iPhone 16 256GB", "NOW D-3 360 Softgels"). Every caller follows; rating_service's Shopping rating pick follows too (V2 missed point 9). One consequence (SL3): a typed "50 ML" no longer rejects a "100 ml" title at this gate; the size axis of the later gates (`_selection_match`, the identity backstop, the reconcile) decides.

### 1.8 Flag-reader idiom, names, libraries

House reader: `os.getenv("ENABLE_X", "false").strip().lower() in ("true", "1", "yes", "on")` read per call (PS:4905-4923). `git grep` at base: no `PRICE_NOT_LOST`, `price_not_lost`, `PRICE_OUTCOME`, `PRICE_CACHE_HIT`, `PRICE_CACHE_SKIP`, `pair_price_sizes`, `per_ml` in app/, tests/, scripts/, .github/ or SmartCompareApp/src. `price_basis` IS taken: a PRICE-level key of shopify_pdp_service.py:493-532 (`"price_basis": "available_variant_min"` ...); so P2-5's pair marker is named `metadata.pair_price_sizes` (refined, additive). No new name contains access / auth / api / credential / creds / key / password / secret / token. Libraries: the standard library only (`re`, `copy`, `contextvars`, `logging`, `os`, `urllib.parse`); no dependency change. Pinned venv `.venv-qaren`, CPython 3.12.9.

### 1.9 Guards the new code must not trip

| guard | where | rule |
|---|---|---|
| AST import census | tests/test_s81_s15_registry_robots.py (`test_p6_scoring_never_reads_partner`) | RB adds no module-level import; every new RB import is function-local `from app.services.price_service import ...` (the RB:1648 style). |
| KB census | tests/test_s81_kb_schema.py P01 / P02 | PS / RB / SCS import nothing new from kb_*. |
| llm_pricing by module attribute | tests/test_s81_s03_llm_ledger_v2.py BL4 | no from-import of llm_pricing. |
| genuine-set parity | tests/test_eval_genuine_methods_parity.py, tests/test_genuine_predicate_parity.py | `_GENUINE_BH_SOURCE_METHODS` / `_is_genuine_bh_candidate` read, never edited. |
| shopping-key pin | tests/test_multiplicity_discriminator_policy.py block B | `_shopping_cache_key` and its assembly at SCS:7324 unedited. |
| source-scanning pins | test_model_config*.py, test_prompt_fence.py, test_u3c_store_false_pin.py, test_start_command.py, test_migration_index_predicate_immutability.py, test_openai_key_log_hygiene_s69.py, test_sentry_channels_u8d_unit.py | no LLM call, prompt text, migration, Sentry channel or key log. The verdict prompt bytes do not change flag OFF (the projection is flag-ON only, and the trace never touches a dict the prompt dumps). |
| exact log-count asserts | tests/test_s81_s04_spend_breaker.py, tests/test_s81_s20_result_gate.py, tests/test_w4_7_confidence_single_computation.py (assert record counts and read RB / the price path) | the new unflagged INFO lines must not change a counted logger: the RED agent reads each assert at base and records whether it counts `app.services.response_builder` / SCS INFO records; any that does becomes an E-row for the orchestrator BEFORE GREEN (4.1). |
| gitleaks / added-line sweep | .githooks | no 64-hex, no long digit run, no keyword-named constant. |
| black allowlist | .github/black-clean-paths.txt | PS / RB / SCS not listed (checked by GREEN with `grep -c`). |
| S81-04c statements | ES, image_routes.py, url_extraction_service.py | not touched. |
| INC-I2 region | SCS:6018-6906 | not touched (Q6). |

### 1.10 Line endings and the base pass state (DEFERRED TO RED: nothing was run in this round)

`core.autocrlf=true`; PS, RB, SCS and CLAUDE.md are CRLF in the working copy (one CR per line: 17332 / 2387 / 10055 / 1167 CRs measured with `tr -cd '\r' | wc -c`) and LF in the index. GREEN edits with the Edit tool (preserves CRLF); `git diff --stat` must show hunks only. New test files are written LF, pure ASCII, bytes > 127 = 0 checked after every write.

Every run goes through `<SP>/harness/gate.py` (H12 e; same arguments as the runner, tags `inc-p2-`), the pinned venv, ONE pytest at a time. The RED agent records each `[pyt]` line here before writing the RED files:

| # | set | command (exact) |
|---|---|---|
| B-1 | the files nearest the edits | `PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe <SP>/harness/gate.py --bound 1200 --tag inc-p2-base-direct --log <SP>/INC-P2/red/base-direct.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-p2 -- tests/test_pair_size_basis_fairness.py tests/test_pair_size_reselection.py tests/test_price_size_reconcile.py tests/test_fragrance_size_reconcile_fix.py tests/test_category_fairness.py tests/test_fairness_target_rules.py tests/test_fairness_skip_estimate.py tests/test_correctness_consume_and_fairness.py tests/test_correctness_concentration_size.py tests/test_response_builder_price_pending.py tests/test_prescoring_showable_guard.py tests/test_ws5_honesty.py tests/test_error_paths.py tests/test_bolo_adapter.py tests/test_noon_adapter.py tests/test_woocommerce_adapter.py tests/test_variant_discrimination.py tests/test_exact_match_contract.py tests/test_genuine_reach_cascade.py tests/test_adapter_prefetch_hook.py -q` |
| B-2 | identity and stream digests | `... gate.py --bound 1200 --tag inc-p2-base-ident --log <SP>/INC-P2/red/base-ident.log --cwd <W> -- tests/test_s75_fanout_identity.py tests/test_streaming.py tests/test_m13_04_full_stream_deadline.py tests/test_s81_s18_kb_first_serve.py tests/test_s81_s17_kb_ingest.py tests/test_m18_region_guard_prescoring.py tests/test_inc_r1_seam.py tests/test_multiplicity_discriminator_policy.py -q` |
| B-3 | the comm set (section 7, 750 files) | 30 chunks of at most 25 files, `--bound 1200` each, tags `inc-p2-base-cNN`; or the LC-6 reuse of a stored record under `<SP>/harness/base_records/b0ad260363e0cf0074e4ee596b140d073466e92a/<set-sha256>.txt` when one matches the set hash (none exists for b0ad2603 at this writing: H12 b). |
| B-4 | the three exact log-count files of 1.9 | `... gate.py --bound 600 --tag inc-p2-base-logcount --log <SP>/INC-P2/red/base-logcount.log --cwd <W> -- tests/test_s81_s04_spend_breaker.py tests/test_s81_s20_result_gate.py tests/test_w4_7_confidence_single_computation.py -q` |
| B-5 | the fourteen backend-scanning client fences (LC-5; app/ moves) | after the H5 jest probe and `gate.py --wait-only`, from `<W>/SmartCompareApp` through the orchestrator's junction: `timeout -k 15 600 node node_modules/jest/bin/jest.js --ci <the fourteen paths of the common brief, each confirmed with git ls-files first>`; accepted base failures: the four nativeBundle.w37 drift nodes. |

Known environmental base noise to record identically at base and head: tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable and ::test_render_digests_match_base_except_the_fence (cold tiktoken cache); the deselected nodes of tests/.pre_impl_failures.txt.

## 2. Contract

### 2.1 Flag and knobs

- `ENABLE_PRICE_NOT_LOST`: PS `price_not_lost_enabled() -> bool`, the house idiom (`os.getenv("ENABLE_PRICE_NOT_LOST", "false").strip().lower() in ("true", "1", "yes", "on")`), never cached. It is the FIRST statement of: the fragrance branch of `reconcile_pair_fairness`; `numbers_match`; the per-item skip in `extract_price_from_shopping`; RB `_p2_wire_prices`; SCS `_p2_cache_reselected`; the SSE `prices` restore; the reseller park; the adapter converted park filter. Default OFF everywhere (H13 c: not set on web).
- Knobs: none. Measured reason: every number the unit needs is an existing constant (`_FRAGRANCE_FLAGSHIP_SIZE_ML` 100.0, the existing TTLs `GENUINE_PRICE_CACHE_TTL` / `PRICE_CACHE_TTL` through `price_cache_ttl`, the strict parser's 1..9999 range, per-ml rounding 4 places by X1-R11).
- Production values walked (H12 c + H13 c): `ENABLE_PRODUCT_RESOLVER` OFF (both values walked), `ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX` and `ENABLE_GENUINE_PRICE_PRIORITY` UNKNOWN (both values walked), `ENABLE_EXACT_PRICE_GATE` default ON (OFF walked), `ENABLE_KB_FIRST_SERVE` OFF (ON walked), `ENABLE_DATA_GUARDS_V2` absent (both walked for the Tier-1 pick), `ENABLE_REGION_CURRENCY_GUARD` / `ENABLE_PRESCORING_SHOWABLE_GUARD` default OFF (ON walked once for the restore checks).

### 2.2 New PS symbols (pure unless stated; no network)

| symbol | signature | contract |
|---|---|---|
| `price_not_lost_enabled` | `() -> bool` | 2.1. |
| `typed_size_ml` | `(product: dict) -> Optional[int]` | `extract_size_ml_any(product.get("full_name") or product.get("name") or "")` for a dict, else None. Reads ONLY the side's own name (never `user_query`, `price`, `specs`). Equal with the resolver ON and OFF for the same typed half (Q1). |
| `_P2_STRICT_ML_RE` + `listing_size_ml` | `(price: Any) -> Optional[int]` | X1-R7: `re.compile(r"(?<![0-9.,])([0-9]{1,4})[ -]?ml\b", re.I)` over `price["title"]`; when the title holds no token, over `price["size"]` (str only); the DISTINCT values in 1..9999; exactly one -> int, else None (probe_re.out: "Libre EDP 90ml" 90, "50ml / 100ml" None, "7.5ml" None, "100  ml" None, "3.4 oz" None). |
| `_P2_SIZE_TOKEN_RE` | module constant | `re.compile(r"(?<![\d.,])\d+(?:[.,]\d+)?\s*-?\s*(?:ml|fl\.?\s*oz|oz)\b", re.I)` (probe_re.out). |
| `_P2_MARKETPLACE_SELLERS` | `FrozenSet[str]` | the auction / peer-marketplace names: "whatnot" (new, the logged seller) and the names the code base already carries (PS:376-380, PS:9621-9626, ES:934-939): "ebay", "aliexpress", "alibaba", "temu", "wish", "dhgate", "banggood", "gearbest", "etsy", "mercari", "swappa", "backmarket", "back market", "gazelle", "decluttr", "reebelo", "poshmark", "unclaimed baggage", "stockx", "therealreal", "vestiaire". |
| `is_auction_marketplace_seller` | `(retailer: Any, url: Any) -> bool` | True iff a whole-token (or the two multi-word phrases) match of the lower-cased retailer name ("Whatnot", "eBay - seller x", "Back Market") OR the registrable label of the URL host (`deny_hosts.normalize_host` + the label before the public suffix: `www.ebay.co.uk` -> "ebay", `whatnot.com` -> "whatnot"). Never raises; non-str -> False. "Wishlist Perfumes" is False (token, not substring). |
| `price_cache_refusal_reason` | `(request_name, price, category=None, *, warm_context=False) -> Optional[str]` | the body of today's `should_cache_price` (PS:9343-9423) returning the FIRST failing check's name or None: `not_dict`, `no_title`, `no_url`, `listing_url`, `out_of_stock`, `accessory`, `identity`, `brand_evidence`, `warmer_veto`; None also when the exact gate is OFF or `request_name` is empty (today's True paths). `should_cache_price(...)` becomes `price_cache_refusal_reason(...) is None`: the same truth table, unflagged (pinned, A33). |
| `reconcile_pair_sizes_v2` | `(product_data, user_query=None, candidates_by_name=None, treat_unsized_as_flagship=False) -> bool` | 2.3. |
| `P2_SHOWN_KEY` / `P2_RESELECTED_KEY` | `"_p2_shown_price"`, `"_p2_reselected"` | private PRODUCT-level keys, flag ON only. |
| `p2_wire_price` | `(pd, category, region_currency, region_guard_on) -> Tuple[Any, Any, Any]` | 2.5: the (price view, best_price, retailer) a wire copy carries. |
| `pair_price_sizes` | `(wire_prices: list) -> dict` | 2.5. |
| `_PRICE_TRACE` + `price_trace_bind` / `price_trace_note` / `price_trace_get` | `ContextVar("price_outcome_trace", default=None)` | 2.7; log-only, unflagged, never raises. |

### 2.3 `reconcile_pair_sizes_v2` (PS; called only from the fragrance branch of `reconcile_pair_fairness` when the flag is ON)

The fragrance branch becomes: `if price_not_lost_enabled(): changed = reconcile_pair_sizes_v2(...) else: changed = reconcile_pair_sizes(...)` (same arguments, same `frag_reconcile_fix_enabled()` value), followed by the unflagged trace note of 2.7. Steps:

1. Guards: exactly today's no-op guards (PS:2296-2321: list of 2, both prices dicts, both amounts numbers > 0, the estimate skip under `_fairness_ignore_estimate_enabled()`); a guard hit returns False and writes nothing.
2. Today's decision, dry: `shadow = [{**p, "price": dict(p["price"])} for p in (p0, p1)]`; `reconcile_pair_sizes(shadow, user_query, candidates_by_name, flag)` (today's code, mutating only the copies; `reselect_to_target_size` is pure); `today_pend = [i for i in (0, 1) if shadow[i]["price"].get("unavailable") is True and shadow[i]["price"].get("reason") == "size_mismatch"]`.
3. Candidates per side: today's lookup (`candidates_by_name.get(full_name) or .get(name)`) MINUS every candidate for which `is_auction_marketplace_seller(raw.retailer or c.retailer, raw.url or c.url)` (P2-10).
4. Typed sizes `t = (typed_size_ml(p0), typed_size_ml(p1))`.
   - (a) any side typed: side i's target is `t[i]` when typed, else the other side's typed size. When `listing_size_ml(p_i.price)` is known and differs from the target, `reselect_to_target_size(name_i, cands_i, float(target), currency)`; a result swaps `price` (+ `best_price` / `retailer` when present, today's PS:2373-2380 mechanics) and sets `p_i["_p2_reselected"] = True` unless the replaced price carried `_cache_source == "kb"`. No result, or an unknown listing size: the side keeps its found price. NEVER a pend.
   - (b) no side typed: `eff = effective_pair_size_ml(p_i, flag)` (today's flagship default for an unknown size). Equal and not None: no-op (today's PS:2338-2341). Else `reach_i = {eff_i} - {None}` plus every candidate size `_candidate_size_ml(c)` for which `reselect_to_target_size(name_i, [c], size, currency)` is not None; `common = reach0 & reach1`. Non-empty: `target = 100.0 if 100.0 in common else max(common)` and each side not already at it is re-selected exactly as `_resolve_to_target` does (it succeeds by construction), with the `_p2_reselected` mark of (a). Empty: NEITHER side changes.
5. Comparability on the FINAL prices, `s_i = listing_size_ml(p_i.price)`: comparable when 4(b) ended at a common size or on the equal-effective no-op; otherwise comparable iff `s0 == s1 is not None`, or both None, or exactly one None and the other == 100 (the flagship default; P2-4's wording).
6. Not comparable (P2-4 projection): `P = today_pend` when non-empty, else `[0, 1]`. For i in P: `p_i["_p2_shown_price"] = p_i["price"]` (the shown object), then `p_i["price"] = shadow[i]["price"]` when i was in today_pend (flag OFF's own pending dict, byte for byte), else `make_pending_price(currency, "size_mismatch", size=price.get("size"))` (flag OFF's outcome-3 shape); `best_price` / `retailer` -> None when present (today's `_mark_size_pending`). Every consumer of 1.6 therefore receives exactly what it receives with the flag OFF on a one-side (or both-side) size pend.
7. Return True iff any swap or projection happened.

Never pended for size under the flag: a side is only ever PROJECTED, and RB restores it (2.5) unless the chokepoint's own checks refuse it. Every other pend (the C1 showability chokepoint, estimates, out of stock, the region guard, the display check) is unchanged.

### 2.4 numbers_match and the Tier-1 pick (PS)

- `numbers_match(product_name, title)`: first statement `if price_not_lost_enabled(): product_name = _P2_SIZE_TOKEN_RE.sub(" ", product_name or "")`; the rest byte-identical. Every caller of 1.7 follows (A23-A26).
- `extract_price_from_shopping`: inside the item loop, right after `retailer = item.get("source", "")` (PS:10568): `if price_not_lost_enabled() and is_auction_marketplace_seller(retailer, item.get("link")): continue` (the item is skipped as if absent; the D03 drop at PS:10435-10438 is untouched).

### 2.5 The builder step (RB) and the wire copies

Right after the chokepoint loop (after RB:1766) RB computes `_p2_wire = _p2_wire_prices(product_data, category_used, _region_currency, _region_guard_on)` (a module-level RB function whose FIRST statement is `if not price_not_lost_enabled(): return None`; function-local PS import; any exception -> WARNING by type only and None, so a failure ships the flag-OFF body). For each product it returns `p2_wire_price(pd, ...)`:

- base = `pd["_p2_shown_price"]` when present, else `pd["price"]`.
- A restored base must pass, on a `copy.deepcopy`, the chokepoint's own checks: the region guard (when on, currency equal to the region currency) and `is_price_showable(name, copy, cat, enforce_correctness=True)`; refused -> the side ships `pd["price"]` (today's pending dict) unchanged.
- view = `dict(public_price_view(base))` (always a NEW dict, also when the exact gate is OFF and `public_price_view` returns its input).
- When view is a shown price (amount number > 0, `unavailable` not True) and the product is a fragrance (`canonicalize_category(pd.category or category_used) == "fragrances"`) and `listing_size_ml(base)` is an int n: `view["size_ml"] = n`, `view["per_ml"] = round(float(amount) / n, 4)` (X1-R11; in the price's currency per ml).
- best_price = the view's amount when restored, else `pd.get("best_price")`; retailer = `base.get("retailer")` when restored, else `pd.get("retailer")`.

Wire sites (flag ON only; flag OFF the base expressions run unchanged):
- RB:1951 `"price": public_price_view(pd.get("price"))` -> `_p2_wire[i][0] if _p2_wire else public_price_view(pd.get("price"))`.
- RB:2268 `result["products"] = product_data` -> under `_p2_wire`: a list of shallow COPIES of the (already alias-processed) product dicts, every `_p2_`-prefixed key dropped, `price` / `best_price` / `retailer` from `_p2_wire` (the latter two only when the key exists). `product_data` itself keeps the projected price and the stash, so every LATER build on the same dicts (the sync moderation-window partial, a re-build) projects and restores again identically (X1-R1), and `_kb_ingest_tail` / compare_runs read today's values.
- `metadata.pair_price_sizes` (after RB:2144, fragrance pairs of exactly two products): `{"mode": m, "sizes_ml": [s0, s1]}` with `s_i = view_i.get("size_ml")` (int or null) and m = "same_size" (s0 == s1 not null), "different_sizes" (both known and unequal, or one null and the other known and != 100), else "unknown". Additive.
- `scoring_v2` (RB:2079), the factual verdict, the confidence block (RB:1772-1790) and every other reader keep reading the PROJECTED `product_data`: the restore never mutates a product dict or a price dict.

SSE (SCS:5495-5518, flag ON): `prices_payload[key]`'s `price` / `best_price` / `retailer` come from `p2_wire_price` for that product (the same helper); flag OFF unchanged.

### 2.6 SCS edits (all in the price region or the reconcile call sites; Q6)

| edit | where | what |
|---|---|---|
| trace bind | after SCS:4394 and after SCS:5128 | `price_trace_bind()` (unflagged; binds a fresh dict for this request). |
| cache what is shown (P2-7) | after the reconcile try blocks, SCS:4667 and SCS:5434 | `if price_not_lost_enabled(): await self._p2_cache_reselected(products, product_data, region)`; inside its own try / except WARNING by type. |
| `_p2_cache_reselected` | new method after `_persist_genuine_price` (SCS:9431) | for i in 0, 1 with `pd.get("_p2_reselected") is True`: shown = `pd.get("_p2_shown_price") or pd.get("price")`; skip unless a dict with amount > 0, not `unavailable`, not an estimate (`_is_estimate_price`), not `_cache_source == "kb"`, not a marketplace seller; mirror `_fetch_product_data`'s `_get_price` arguments from the Step-1 dict `info = products[i]`: `brand = info.get("brand", "")`, `name = info.get("name", "")`, `variant = info.get("variant")`, `category = canonicalize_category(info.get("category"))`, `search_query = info.get("search_query", f"{brand} {name} {variant or ''}")`; `key = build_size_aware_price_cache_key(brand, name, variant, region, search_query, category=category)`; `await self._persist_genuine_price(key, {k: v for k, v in shown.items() if not str(k).startswith("_")}, brand, name, variant, region, _shopping_cache_key(brand, name, variant), category)` (the identity gate, the source-keyed TTL, the L2 save). |
| reseller park (P2-9) | after SCS:8268 `shopify_fallback = shop_best` | flag ON: `sm = shop_best.get("source_method") or "shopify_json"`; when `sm` is in `_GENUINE_BH_SOURCE_METHODS` (it holds "shopify_json", PS:17122) and the seller is not a marketplace: park `dict(shop_best, source_method=sm)` on `self._parked_price[full_name]` when nothing is parked or the parked price is `converted_usd` or estimated (never over another genuine park), and `self._seed_shortcircuit_candidates(full_name, kind="price_dicts", currency=currency, price_dicts=shop_results)` (the official branch's call, SCS:8251-8254). |
| adapter converted park (P2-10) | SCS:7889-7893 | flag ON: the rows passed to `select_best` also drop `is_auction_marketplace_seller(r.retailer, r.url)`. |
| race-miss trace | SCS:7104-7119 and SCS:7122-7127 | `price_trace_note("recovered", id(best))` / `price_trace_note("parked", id(parked))` before each return (unflagged, log-only). |
| PRICE_CACHE_HIT | SCS:7188-7190 (L1) and SCS:7258-7262 (L2) | 2.7 (2). |
| PRICE_CACHE_SKIP | SCS:9428 (`_persist_genuine_price`) and SCS:7950 (adapter direct hit) | 2.7 (3): the reason from `price_cache_refusal_reason`, which replaces the bare `should_cache_price` call at these two sites only (same truth value). |

### 2.7 Log lines (P2-11; UNFLAGGED, INFO, plain words first, names and numbers only)

The trace: `_PRICE_TRACE` holds `None` or one dict per request `{"reconcile": {0: str, 1: str}, "parked": set of ids, "recovered": set of ids}`. `price_trace_bind()` sets a fresh dict (SCS:4394 / 5128, inside the impl task and the stream generator, so the Phase-1 gather children share the same dict object). `price_trace_note` mutates it when bound and never raises. The fragrance branch of `reconcile_pair_fairness` notes per index after the call (both flag values): `pend` when the final price is `unavailable` with reason `size_mismatch` and the side was not projected by V2; `both_shown` when the side carries `_p2_shown_price`; `reselect` when the price object changed identity; else `none`. A body built where the trace is unbound (the sync timeout partial, built in the outer context of SCS:4271) logs `reconcile=unknown`.

1. RB, once per product per build, right after `_p2_wire` (both flag values; the wire values when ON, `pd["price"]` when OFF): `logger.info("PRICE_OUTCOME product=%d method=%s amount=%s currency=%s size_ml=%s cache=%s reconcile=%s reason=%s host=%s name=%s", ...)`: `method` = source_method or `none`; `amount` = `%.3f` or `none`; `size_ml` = `listing_size_ml(base)` or `none`; `cache` = `parked` / `recovered` (object id in the trace), else `l2` (`_cache_source == "db"`), `kb`, `negative`, `l1` (`_cached is True`), `live` (`_cached is False`), `none` (pending or no marker); `reconcile` from the trace; `reason` = the pending reason or `none`; `host` = `urlsplit(url).hostname` or `none` (never the path or the query); `name` = the product's display `name`. Inside its own try / except (a failure logs nothing more and never touches the body).
2. SCS `_get_price`: L1 hit `logger.info("PRICE_CACHE_HIT layer=l1 age_s=unknown product=%s %s", brand, name)`; L2 hit `logger.info("PRICE_CACHE_HIT layer=l2 age_s=%d product=%s %s", _l2_age, brand, name)` (the age already popped at SCS:7240).
3. SCS: `logger.info("PRICE_CACHE_SKIP reason=%s site=%s product=%s", reason, site, full_name)` with site `persist` (SCS:9428) or `direct_hit` (SCS:7950), only when a refusal reason exists.

Readers and pins of these lines (Q-measure): `git grep` of app/, tests/, scripts/, .github/ finds no reader of `PRICE_OUTCOME`, `PRICE_CACHE_HIT` or `PRICE_CACHE_SKIP`; the Railway filter needs no bracket (feedback rule). Three test files count log records near these paths (1.9, B-4): measured at RED.

### 2.8 New keys (additive; contract_freeze lists only price.amount / currency / source_method / unavailable)

| key | type | where | when |
|---|---|---|---|
| `price.size_ml` | int | overview.products[i].price, products[i].price, the SSE prices payload | flag ON, a shown fragrance price whose listing yields exactly one strict size token |
| `price.per_ml` | float (4 places) | same | with `size_ml` |
| `metadata.pair_price_sizes` | `{"mode": "same_size" | "different_sizes" | "unknown", "sizes_ml": [int or null, int or null]}` | metadata | flag ON, a fragrance pair of two |
| product keys `_p2_shown_price`, `_p2_reselected` | private | product dicts in memory only | never on the wire (the alias copies drop them; the overview never copies product keys) |

Existing keys keep their types: `price.amount` stays a number or null; `price.unavailable` / `price.reason` keep today's values on every side that still pends; a restored side carries exactly the found price's keys (as `public_price_view` projects them) plus the two additive keys. No status code changes; no new error path; never a bare 503.

### 2.9 Failure table (flag ON)

| failure | effect |
|---|---|
| V2 raises | caught by the call site's existing try / except (SCS:4665-4667, 5432-5434: WARNING "fairness reconciliation skipped"); the product dicts are whatever V2 had written: V2 writes the projection LAST (step 6) after all swaps, so a raise before step 6 leaves found prices showable (no pend), never a half projection. |
| `_p2_wire_prices` raises | WARNING by type, returns None: the body is the flag-OFF body for that build (projected side shows today's pending line). |
| restored price refused by the chokepoint checks | that side ships today's pending dict (reason `size_mismatch` or the dry-run's own). |
| `_p2_cache_reselected` raises / Redis down | WARNING by type; the response is unaffected; the write is simply absent (next run repeats the re-selection). |
| `should_cache_price` refusal | no write; `PRICE_CACHE_SKIP reason=... site=persist`. |
| trace unbound / raises | log fields `unknown`; never an exception into the request. |
| flag flipped mid-request | each predicate reads per call; a request may mix (e.g. V2 projected, RB read OFF): RB OFF ships the projected pending dict = today's body; no crash. Stated (SL9). |

### 2.10 Flag-OFF identity and the deploy-visible delta (the main invariant)

With `ENABLE_PRICE_NOT_LOST` unset / false and every other flag at its production value (H12 c + H13 c), every response body (sync GET / POST, the stream events, every partial), status, cache write (L1, L2, negative), DB price row, KB job, verdict prompt and log line is byte-identical to base EXCEPT exactly:
1. `PRICE_OUTCOME` INFO lines: one per product per `build_comparison_response` call (normally two per compare; four when a moderation-window partial is also built);
2. `PRICE_CACHE_HIT` INFO lines: one per price L1 or L2 hit in `_get_price`;
3. `PRICE_CACHE_SKIP` INFO lines: one per `should_cache_price` refusal at the persist and direct-hit sites (refusals were silent).
The unflagged code that produces them (the trace ContextVar, the fragrance-branch note, `price_cache_refusal_reason`) writes no response byte, no cache entry and no prompt byte; `should_cache_price` keeps its truth table (A33).

### 2.11 Test seams (production values in brackets)

`ENABLE_PRICE_NOT_LOST` [unset]; `ENABLE_PRODUCT_RESOLVER` [OFF]; `ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX` [unknown: both]; `ENABLE_GENUINE_PRICE_PRIORITY` [unknown: both]; `ENABLE_EXACT_PRICE_GATE` [default ON]; `ENABLE_KB_FIRST_SERVE` [OFF]; `ENABLE_DATA_GUARDS_V2` [absent]; `ENABLE_ANTHROPIC_TEXT` / `ENABLE_ANTHROPIC_VERDICT` / `ENABLE_OPENAI_EGRESS_STOP` / `ENABLE_OPENAI_PRE_V3` / `ENABLE_LLM_LEDGER_V2` / `ENABLE_LLM_SPEND_BREAKER` / `ENABLE_REQUEST_CONTEXT_HEADERS` / `ENABLE_LEGACY_FINGERPRINT_READER` / `ENABLE_CONSENT_PERSIST` [ON]; the S81 pre-flags of ledger line 316 at their recorded values; recorders on `_cache_set_async`, `_save_price_to_db`, `generate_comparison` (its two product arguments), `ScoringService.compute_scores` (its product list) and the `app.services.response_builder` / SCS loggers. The pure rows build product dicts by hand in the measured shapes of 1.2 (resolver OFF: brand "", name = full_name = the typed half, variant None, query = the half; resolver ON: the `apply_resolution` shape run through `_product_display_identity`).

## 3. Change list (the order GREEN applies it)

1. Byte copies (Python `shutil.copyfile`) of PS, RB, SCS and CLAUDE.md into `<SP>/INC-P2/green/orig/`, sha256 recorded; the mutation lock rule of the common brief for section 6.
2. PS (Edit tool, CRLF kept): (a) near `frag_reconcile_fix_enabled` (PS:4905): `price_not_lost_enabled`; (b) after `extract_size_ml_any` (PS:4145): `_P2_STRICT_ML_RE`, `listing_size_ml`, `typed_size_ml`, `_P2_SIZE_TOKEN_RE`; (c) after `is_marketplace_reseller` (PS:9654): `_P2_MARKETPLACE_SELLERS`, `is_auction_marketplace_seller` (function-local `from app.services.deny_hosts import normalize_host`); (d) `numbers_match` (PS:3871-3877): the flag-ON product-side strip as its first statement; (e) after `_mark_size_pending` (PS:2417): `reconcile_pair_sizes_v2`, `P2_SHOWN_KEY`, `P2_RESELECTED_KEY`, `p2_wire_price`, `pair_price_sizes`; (f) `reconcile_pair_fairness` fragrance branch (PS:3346-3351): the flag split + the unflagged trace note (2.3, 2.7); (g) `should_cache_price` (PS:9343-9423): body moved into `price_cache_refusal_reason`, `should_cache_price` returns `... is None`; (h) `extract_price_from_shopping` (after PS:10568): the flag-ON marketplace skip; (i) the trace ContextVar and its three helpers (module level, near the other ContextVar `set_resolved_price_category`). No other PS line.
3. RB: (a) `_p2_wire_prices` module function (near `_compute_cache_observability`, RB:49-81); (b) after RB:1766: `_p2_wire = _p2_wire_prices(...)` and the `PRICE_OUTCOME` loop; (c) RB:1951 the overview price expression; (d) after RB:2144 the `metadata.pair_price_sizes` stamp; (e) RB:2268 the flag-ON alias copies. Function-local PS imports only.
4. SCS: the edits of 2.6, in file order: 4394, 4667, 5128, 5434, 5495-5518, 7104-7127, 7188-7190, 7258-7262, 7889-7893, 7950, 8268, 9428, the new `_p2_cache_reselected` after 9431; the imports it needs are added to the existing `from app.services.price_service import (...)` block (SCS:1440-1520). Nothing in SCS:6018-6906.
5. CLAUDE.md: the block of section 8 after the INC-R1 block (CLAUDE.md:699-703), before `## Tests` (CLAUDE.md:705).
6. New tests: `tests/test_inc_p2_price_not_lost.py` (pure rows A01-A34) and `tests/test_inc_p2_seam.py` (pipeline / route rows B01-B18), written by the RED agent, frozen at the gate (GREEN never edits them).
7. Restore check: `git diff --stat` shows only the four files plus the two new tests; whole-file diffs = defect; bytes > 127 in the new tests = 0.

No other file. (No client file, no migration, no requirements change, no processors.json row: no new external host.)

## 4. Existing pins

### 4.1 Pins that change deliberately

None measured. Every existing pin of the reconcile, the `size_mismatch` pend, the 100 ml target and `numbers_match` runs with `ENABLE_PRICE_NOT_LOST` unset and stays byte-identical (Q9). One conditional E-row slot: if a B-4 file counts INFO records of `app.services.response_builder` or SCS on a path that now prints `PRICE_OUTCOME` / `PRICE_CACHE_HIT` / `PRICE_CACHE_SKIP`, the RED agent writes it as E1 (the reason: P2-11's ruled unflagged lines) and the orchestrator rules it BEFORE GREEN.

### 4.2 Pins that must stay green and unedited (flag OFF; Q9)

- size_mismatch / target / reconcile: tests/test_pair_size_basis_fairness.py, test_pair_size_reselection.py, test_price_size_reconcile.py, test_fragrance_size_reconcile_fix.py, test_category_fairness.py, test_fairness_target_rules.py, test_fairness_skip_estimate.py, test_correctness_consume_and_fairness.py, test_correctness_concentration_size.py, test_response_builder_price_pending.py, test_prescoring_showable_guard.py, test_m18_region_guard_prescoring.py, test_ws5_honesty.py, test_exact_match_contract.py, test_frag_size_capture.py, test_genuine_reach_cascade.py, test_adapter_prefetch_hook.py, test_arabic_verdict_output_w414.py, test_inc_x8_phase2_cached_rating.py, test_inc_x9_cohort_line_retire.py, test_m13_04_full_stream_deadline.py, test_m6_c1_normalize_and_sitemap_match.py, test_s75_fanout_identity.py, test_s81_d14_live_robots.py, test_s81_s17_kb_ingest.py, test_s81_s18_kb_first_serve.py, test_sitemap_discovery.py (the 27 files `git grep` finds for size_mismatch / reconcile_pair_* / target_pair_size_ml / _FRAGRANCE_FLAGSHIP_SIZE_ML).
- numbers_match: tests/test_error_paths.py::TestNumbersMatch (six rows, all non-ml), test_bolo_adapter.py:136-163 (the vacuous "100ml" row: still True), test_algolia_service.py, test_noon_adapter.py, test_woocommerce_adapter.py, test_variant_discrimination.py, test_eyewear_code_tolerance.py, test_selection_primary_acceptance.py, test_shopify_discovery_l13.py, test_sixthstreet_revival.py, test_correctness_coverage_review_findings.py.
- cache / identity: tests/test_multiplicity_discriminator_policy.py, every `should_cache_price` reader (the truth table is unchanged, A33).
- the guards of 1.9 and the whole comm set of section 7.

## 5. RED tests (hermetic: no network, no live marker, no .env; flags set with monkeypatch per row; missing symbols read with `getattr(module, name, None)` and asserted, so a RED fails on an AssertionError only)

Fixtures (P2-14, public names and logged prices; hosts `*.example.com` except the marketplace names under test): TED (resolver OFF: name = full_name = "Ted Baker M 30ml"; ON: brand "Ted Baker", name "M", variant "30ml"), price woo 9.500 BHD title "Ted Baker M Eau De Toilette 30ml"; DIOR (OFF: "Dior Sauvage 100 ML Edp"; ON: brand "Dior", name "Sauvage", variant "EDP 100ml"), price noon 58.110 BHD title "Dior Sauvage EDP 100ml"; YSL "YSL Libre EDP" fragrancebh 39.000 title "YSL Libre Eau de Parfum 90ml"; LVEB "Lancome La Vie Est Belle EDP" fragrancebh 34.000 title "... 100ml"; BR540 "Baccarat Rouge 540" noon 129.280 title "... 70ml"; SAUV "Sauvage EDP" noon 58.110 100ml; BLEU "Bleu de Chanel EDP" woo 70.000 title "Bleu de Chanel EDP 150ml" with a candidate noon 91.780 "Bleu de Chanel EDP 100ml"; WHATNOT a Shopping item source "Whatnot" link "https://www.whatnot.com/x" 50.76 converted. Query strings are the combined "A vs B" text.

### 5.1 `tests/test_inc_p2_price_not_lost.py` (pure; PS / RB)

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| A01 | flag reader | `price_not_lost_enabled` exists; unset / "false" / "0" / "maybe" -> False; "TRUE", " on ", "1", "yes" -> True; read per call (monkeypatch between two calls) | RED | 2.1 |
| A02 | typed size, both modes | `typed_size_ml` exists; TED OFF and ON -> 30; DIOR OFF and ON -> 100; "Sauvage 3.4 oz" -> 100; a dict with only a price title "90ml" -> None | RED | 2.2 |
| A03 | listing size | `listing_size_ml`: "Libre EDP 90ml" 90; "50ml / 100ml" None; "7.5ml" None; "EDP100ml" 100; title absent + size "100ml" 100; "100ml 100 ml" 100 | RED | 2.2 |
| A04 | T3-01 resolver OFF | flag ON, fix flag both values: `reconcile_pair_fairness([TED, DIOR], "Ted Baker M 30ml vs Dior Sauvage 100 ML Edp", "fragrances")`; then `build_comparison_response`: overview prices 9.500 and 58.110, neither `unavailable`, `size_ml` 30 and 100, `metadata.pair_price_sizes == {"mode": "different_sizes", "sizes_ml": [30, 100]}` | RED (Dior pended) | 2.3 (a), 2.5 |
| A05 | T3-01 resolver ON | A04 with the ON dicts: the same body values | RED | 2.3 (a) |
| A06 | own typed size re-selection | DIOR's price a 50ml listing, candidates hold a genuine 100ml noon: the shown Dior price is the 100ml candidate, `_p2_reselected` True | RED | 2.3 (a) |
| A07 | one side typed | DIOR typed vs SAUV-style untyped side with a 100ml candidate: the untyped side re-selected to 100; mode same_size | RED | 2.3 (a) |
| A08 | no pend when no candidate | DIOR typed with only a 50ml listing and no candidate: shown at 50, `size_ml` 50, no `size_mismatch` on the wire | RED | 2.3 (a) |
| A09 | YSL / Lancome (T3-02) | no typed size, no candidates: both shown, `size_ml` 90 / 100, mode different_sizes | RED | 2.3 (b) |
| A10 | Baccarat at 70 ml | BR540 vs a 100ml partner: both shown, `per_ml` == round(129.280 / 70, 4) | RED | 2.3 (b), 2.5 |
| A11 | common 100 kept (PIN) | SAUV vs BLEU with the noon 100ml candidate, flag ON: BLEU re-selected to 91.780, no pend (today's re-selection; green at base because flag ON = today there; the marker of this case is asserted in A20) | PIN | 2.3 (b) |
| A12 | common 50 | both sides reach 50 only (a 50ml candidate each, current prices 75ml / 125ml): both re-selected to 50 | RED (base pends both) | 2.3 (b) |
| A13 | 100 preferred over a larger common | both reach 50, 100 and 125: target 100 | RED | 2.3 (b) |
| A14 | unknown keeps the flagship default (PIN) | one side has no size anywhere (designer name), the other 100ml: no swap, no projection, both amounts shown, no `size_mismatch` (today's values; the marker is asserted in A20) | PIN | 2.3 (b) |
| A15 | legacy branch | fix flag OFF, two non-designer houses at 50ml / 100ml: flag ON shows both; flag OFF both pend (today) | RED | 2.3 (b) |
| A16 | other pends unchanged (PIN) | an estimate side -> no-op both flags; an `unavailable` pending_genuine side -> untouched; an out-of-stock candidate never re-selected | PIN | 2.3 step 1 |
| A17 | projection = today's inputs | flag ON vs flag OFF on [TED, DIOR] with the full configuration: after the reconcile, for every index today pends, `product_data[i]["price"]` (flag ON) == flag OFF's pending dict (dict equality and `json.dumps(sort_keys=False)` byte equality), `_p2_shown_price` holds the found price; the other side carries the shown price | RED | 2.3 step 6 |
| A18 | consumers see no comparison | flag ON, A04's pair through `build_comparison_response`: `scoring_v2.dimensions` price and value carry `caption_key == "limited_data"`; no factual-verdict price line; while both overview prices carry amounts | RED | 2.3 step 6, 2.5 |
| A19 | both projected when today pends nothing | both typed 30 / 100, DIOR holds a 30ml candidate (today re-selects Dior to 30, no pend) and V2 keeps Dior at 100: BOTH sides projected (`make_pending_price(..., "size_mismatch", size)` for each) and both restored on the wire | RED | 2.3 step 6 |
| A20 | marker modes | same_size (A11 pair), different_sizes (A09), unknown (A14), and `sizes_ml` null for a side with no strict token | RED | 2.5 |
| A21 | size / per-ml stamp | every shown fragrance price with one strict token carries `size_ml` / `per_ml` (58.110 / 100 -> 0.5811; 39.000 / 90 -> 0.4333); "50ml / 100ml" title and "3.4 oz" title -> neither key; an electronics pair -> neither key nor the marker; a pending side -> neither key | RED | 2.5 |
| A22 | restore runs the chokepoint checks | a projected side whose stash is out of stock (or a listing URL, exact gate ON) ships today's pending dict, not the amount | RED | 2.5 |
| A23 | numbers_match, fragrance (T3-04) | flag ON: "Dior Sauvage 100 ML Edp" vs "Sauvage EDP 100ml", "Dior Sauvage EDP 100ml/3.4oz", "DIOR Sauvage Eau de Parfum Spray" -> True; "Sauvage 100 ML 3.4 FL OZ" vs "Sauvage EDT" -> True | RED | 2.4 |
| A24 | numbers_match, other numbers kept (PIN) | flag ON: "iPhone 16 256GB" vs "Apple iPhone 15 256GB" False; "NOW D-3 360 Softgels" vs "... 120 Softgels" False; "Baccarat Rouge 540 70 ML" vs "Baccarat Rouge Extrait 70ml" False; "Le Labo Santal 33 100 ML" vs "Le Labo Another 13 EDP 100ml" False; "Creed Aventus 100 ML 2024" vs "Creed Aventus EDP 100ml" False | PIN | 2.4 |
| A25 | numbers_match flag OFF (PIN, full config) | flag OFF with every other production flag set: the three A23 titles -> False (today) | PIN | 2.1 |
| A26 | every caller follows | flag ON: noon_service's matcher (the function holding noon_service.py:233), woocommerce_service.py:213's matcher, rating_service `extract_rating_from_shopping` (rating_service.py:127) and SCS `_numbers_match` accept a "Sauvage EDP 100ml" title for "Dior Sauvage 100 ML Edp" where flag OFF rejects | RED | 2.4 |
| A27 | marketplace predicate | `is_auction_marketplace_seller`: ("Whatnot", None), (None, "https://www.whatnot.com/x"), ("eBay - seller", None), (None, "https://www.ebay.co.uk/itm/1"), ("Back Market", None) True; ("Wishlist Perfumes", None), ("Jomashop.com", "https://www.jomashop.com/x"), (None, None) False | RED | 2.2 |
| A28 | Tier-1 pick skips Whatnot (T3-08) | flag ON, items [WHATNOT, a Jomashop row]: the pick is the Jomashop row; [WHATNOT] alone -> None; both `ENABLE_DATA_GUARDS_V2` values | RED | 2.4 |
| A29 | Tier-1 pick flag OFF (PIN) | flag OFF, [WHATNOT]: today's converted pick (retailer "Whatnot") | PIN | 2.1 |
| A30 | re-selection skips marketplaces | flag ON, the only target-size candidate is a Whatnot converted row: no swap (the found price stays) | RED | 2.3 step 3 |
| A31 | PRICE_OUTCOME, flag OFF | flag OFF, a built pair: exactly one INFO record per product starting "PRICE_OUTCOME product=" with method / amount / currency / size_ml / cache / reconcile / reason / host / name fields; a size-pended side says `reason=size_mismatch reconcile=pend` | RED | 2.7 (1) |
| A32 | PRICE_OUTCOME carries no path, query or key | a price URL `https://store-a.example.com/p/x?ref=y`: the line holds `host=store-a.example.com` and neither `/p/x` nor `ref=`; no field longer than its type | RED | 2.7 (1) |
| A33 | cache gate truth table (PIN + RED) | PIN: `should_cache_price` on the 12 measured branches of PS:9343-9423 returns today's values; RED: `price_cache_refusal_reason` exists and names `no_title`, `no_url`, `listing_url`, `out_of_stock`, `identity` on the matching inputs and None on a pass | RED / PIN | 2.2 |
| A34 | flag-OFF identity, pure | flag OFF, full configuration of 2.11, the A04 / A09 / A11 pairs through the reconcile and `build_comparison_response`: the body equals the base literal the RED agent records at base (`json.dumps(sort_keys=True)` sha256 built at run time), call recorders show no extra cache write; the only new log records are `PRICE_OUTCOME` | PIN | 2.10 |

### 5.2 `tests/test_inc_p2_seam.py` (the REAL orchestrator with stubbed fetches, the `tests/test_inc_r1_seam.py` harness style: `_fetch_product_data` / `_get_price` / the verdict stubbed at their seams, the real reconcile, scoring and builder; the route rows through the FastAPI app with the auth dependency overridden)

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| B01 | phone route, Ted / Dior | GET `/api/v1/text/compare?product_a=Ted Baker M 30ml&product_b=Dior Sauvage 100 ML Edp`, flag ON, resolver OFF then ON, fix flag both: 200; `overview.products[1].price.amount == 58.110`, no `unavailable`; legacy `products[1].price` the same; no `_p2_` key anywhere in the body (recursive key walk) | RED | 2.3, 2.5 |
| B02 | POST and stream | the B01 pair through POST `/compare` and the stream `complete` event: the same prices; the SSE `prices` event carries the restored Dior price with `size_ml` 100 | RED | 2.5 |
| B03 | partial builds (X1-R1, X1-R2) | flag ON: the sync verdict-window partial and the moderation-window partial built after the reconcile carry exactly the full build's `overview.products[*].price` and `metadata.pair_price_sizes`; the moderation partial built AFTER a full build on the same dicts still shows the price-dim `limited_data` (the restore never mutated the dicts); the two stream tail partials (ENABLE_FULL_STREAM_DEADLINE on, ENABLE_EARLY_SPECS_STASH unset) and the gather-time partial carry the size stamp on every shown fragrance price and no restore (no stash there) | RED | 2.5 |
| B04 | cache what is shown, resolver OFF (T3-03) | run 1 SAUV / BLEU: the reconcile re-selects BLEU to 91.780; the `_cache_set_async` recorder holds `(key, price with amount 91.780, ttl == price_cache_ttl(price))` where key == `build_size_aware_price_cache_key` computed exactly as `_get_price` computes it for BLEU's Step-1 dict; run 2 with the recorded entry served from a fake L1: the body shows 91.780 again and the log holds `PRICE_CACHE_HIT layer=l1` | RED | 2.6 |
| B05 | cache what is shown, resolver ON | B04 with the resolver-shaped Step-1 dicts: the key differs from B04's and run 2 reads it | RED | 2.6 |
| B06 | never cache a pending / estimate / kb / refused price | a re-selected price that `should_cache_price` refuses -> no set, `PRICE_CACHE_SKIP reason=... site=persist`; a projected side whose stash is an estimate -> no set; a KB-served side (ENABLE_KB_FIRST_SERVE on) re-selected from its KB offers -> no set | RED | 2.6 |
| B07 | flag OFF cache identity (PIN, full config) | flag OFF B04 run 1: the recorder holds exactly base's writes (none for the re-selection) | PIN | 2.10 |
| B08 | PRICE_CACHE_HIT L2 | an L2 hit with `_l2_age_seconds` 120: `PRICE_CACHE_HIT layer=l2 age_s=120` | RED | 2.7 (2) |
| B09 | reseller parked (T3-06) | flag ON: a converted Tier-1 park exists, the Shopify consume returns a reseller hit: `_parked_price[full_name]` is the reseller copy with `source_method == "shopify_json"` and the candidates hold it; a race timeout then serves it (`_price_fallback_on_miss`), with ENABLE_GENUINE_PRICE_PRIORITY off and on | RED | 2.6 |
| B10 | genuine park kept | flag ON, a genuine park already present: the reseller does not replace it (still seeded) | RED (no seed at base) | 2.6 |
| B11 | reseller flag OFF (PIN) | flag OFF: `_parked_price` keeps the converted park; candidates unchanged | PIN | 2.10 |
| B12 | adapter converted park skips marketplaces | flag ON, observed converted rows [Whatnot-host row, a store-b row]: the park is the store-b row | RED | 2.6 |
| B13 | Ted / Dior 23:04 shape | flag ON, Dior's only price the parked Whatnot converted (race miss) and no other: Dior shows no Whatnot price (pending_genuine through the chokepoint, or a non-marketplace park when one exists) | RED | 2.4, 2.6 |
| B14 | flag mixes | the matrix ENABLE_PRICE_NOT_LOST x ENABLE_PRODUCT_RESOLVER x ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX (8 cells) on the Ted / Dior and YSL / Lancome pairs, plus ENABLE_EXACT_PRICE_GATE off with the flag ON (the restore copies; `public_price_view` identity does not leak `_p2_`), plus a cache-hit cell and a KB-served cell: every ON cell shows both prices, every OFF cell equals base | RED (ON cells) / PIN (OFF cells) | 2.3-2.6 |
| B15 | consumers recorded | flag ON B01: the `generate_comparison` recorder's Dior argument has `price.amount is None` with reason size_mismatch (the projection), the `compute_scores` recorder's list equals flag OFF's list | RED | 2.3 step 6 |
| B16 | PRICE_OUTCOME both routes | flag OFF and ON, sync and stream: two PRICE_OUTCOME lines per build; flag ON B01 says `reconcile=both_shown` for the projected side and `size_ml=100` | RED | 2.7 |
| B17 | flag-OFF body identity (PIN, full config + recorders) | flag OFF, B01 / B02 / B04 bodies, events and cache writes equal the base literals recorded by the RED agent; the log differs only by the three P2-11 line kinds | PIN | 2.10 |
| B18 | no new failure path | flag ON, `_p2_wire_prices` forced to raise (monkeypatch `p2_wire_price`): 200 with the flag-OFF body and one WARNING by type | RED | 2.9 |

Counts: 34 + 18 = 52 rows; RED 42 (A01-A10, A12, A13, A15, A17-A23, A26-A28, A30-A33 (A33 holds a PIN half), B01-B06, B08-B10, B12-B16 (B14 holds PIN cells), B18), PIN 10 (A11, A14, A16, A24, A25, A29, A34, B07, B11, B17). Every PIN runs with the full configuration of 2.11 and the call recorders (B1 rule). A04, A05, A09, B01 and B14 are the rows the PROOF ON THE PHONE mirrors (8b).

## 6. Mutation table (on the GREEN bytes; each mutant on a byte copy, one exact-string edit that matches once, the killing rows via gate.py `-k` with `--bound 600`, restored and sha256-compared; KILLED = an assertion failure)

| M | mutant | killed by |
|---|---|---|
| M01 | `price_not_lost_enabled` returns True (not gated) | A25, A29, A34, B07, B11, B17 |
| M02 | the reader drops `.strip()` / `.lower()` | A01 |
| M03 | `typed_size_ml` reads `user_query` (the combined text) | A04, A05 |
| M04 | `typed_size_ml` reads the price title first | A02, A08 |
| M05 | V2 typed branch calls `_mark_size_pending` when no candidate | A08, A04 |
| M06 | V2 no-common branch pends both | A09, A10 |
| M07 | common target = `max(common)` always | A13 |
| M08 | common target = `min(common)` | A12, A13 |
| M09 | the untyped side ignores the typed side's size | A07 |
| M10 | projection skipped (step 6 removed) | A17, A18, B15 |
| M11 | projection always picks index 0 | A17 |
| M12 | projection uses a new pending dict instead of the dry run's | A17 (byte equality) |
| M13 | both-projected fallback removed (P = today_pend only) | A19 |
| M14 | overview restore removed (RB:1951 keeps the base expression) | A04, B01 |
| M15 | alias copies removed (`result["products"] = product_data` under the flag) | B01 (`_p2_` key walk, alias price) |
| M16 | the restore mutates `pd["price"]` in place | B03 (moderation partial), A18 |
| M17 | the restore skips `is_price_showable` | A22 |
| M18 | `per_ml` rounded to 2 places | A21 |
| M19 | `listing_size_ml` uses `_SIZE_ML_RE` (7.5ml -> 5) / allows two tokens | A03, A21 |
| M20 | `numbers_match` strips every number | A24 |
| M21 | `numbers_match` strip not gated | A25 |
| M22 | the size token regex without the oz arm | A23 (FL OZ row) |
| M23 | marketplace predicate on the retailer only (no host) | A27, A28 |
| M24 | marketplace predicate by substring ("Wishlist" True) | A27 |
| M25 | Tier-1 skip not gated | A29 |
| M26 | V2 candidates not filtered for marketplaces | A30 |
| M27 | reseller replaces a genuine park | B10 |
| M28 | reseller not seeded | B09 (priority ON cell), B10 |
| M29 | cache write under `get_price_cache_key(...)` (the legacy key) | B04 run 2, B05 |
| M30 | cache write without the identity gate (`_cache_set_async` direct) | B06 |
| M31 | cache write for a KB re-selection | B06 |
| M32 | `PRICE_OUTCOME` behind the flag | A31, B16 |
| M33 | `PRICE_OUTCOME` logs the full URL | A32 |
| M34 | `PRICE_CACHE_HIT` missing on L1 | B04 |
| M35 | `price_cache_refusal_reason` reorders `no_url` before `no_title` | A33 |
| M36 | the SSE prices restore removed | B02 |
| M37 | the partial builds skip the step (`_p2_wire_prices` returns None for `metadata.partial`) | B03 |
| M38 | `_p2_wire_prices` exception not caught | B18 |
| M39 | `pair_price_sizes` "different_sizes" when one side null and the other 100 | A20 |

Equivalent-survivor candidates for a ruling: none foreseen; any survivor is reported with its diff.

## 7. Comm set and gates for GREEN (cheapest first; one pytest at a time; every run through gate.py)

Comm set (the union rule): the module / symbol reference grep for the edited modules (PS is imported by about 49 app modules: `git grep -l price_service -- app`, and SCS by the routes and app/main.py, so the importer closure to a fixpoint reaches every test that imports `app.` or builds the app) UNION the source-scanning pins of 1.9 (all present) UNION the module-path / glob / path-segment / `.github` readers UNION the CLAUDE.md readers (tests/test_ci_gates.py, tests/test_behavior_dimension_translation.py; the RED agent confirms by `git grep -n "CLAUDE.md"` which of the 40 mentions OPEN the file) = every test file under tests/ that names `app.`, `app/`, `CLAUDE.md`, `.github` or `SmartCompareApp`: 753 files (`<SP>/INC-P2/spec/comm_set_full.txt`, sha256 b6545390e3f84fad0ad3831d49830ca5d9258c6ba4cb463bd4721d5dcd98f067), minus the three pre-commit hook files (no .githooks change) = 750, plus the two new RED files. No edited test-support helper. The fourteen backend-scanning client jest fences run once (B-5), because app/ moves (the feedback rule); no literal they read is expected to move.

| order | gate | command |
|---|---|---|
| G1 | syntax + lint | `<venv python> -m py_compile app/services/price_service.py app/services/response_builder.py app/services/structured_comparison_service.py tests/test_inc_p2_price_not_lost.py tests/test_inc_p2_seam.py`; `<venv python> -m ruff check --select E9,F63,F7,F82 --no-cache <same files>` |
| G2 | ASCII / CRLF | bytes > 127 in the two new tests = 0; `git diff --stat` hunks only |
| G3 | the RED files | `... gate.py --bound 600 --tag inc-p2-green-red --log <SP>/INC-P2/green/red.log --cwd <W> -- tests/test_inc_p2_price_not_lost.py tests/test_inc_p2_seam.py -q` (all 52 green) |
| G4 | B-1, B-2, B-4 at head | the same commands with `green` tags; equal to the base records (B-4 decides any E1) |
| G5 | CI-order set | `... gate.py --bound 1200 --tag inc-p2-green-ci --cwd <W> -- tests/test_inc_p2_price_not_lost.py tests/test_inc_p2_seam.py tests/test_s75_fanout_identity.py tests/test_streaming.py tests/test_inc_r1_seam.py tests/test_response_builder_price_pending.py tests/test_pair_size_reselection.py -p no:randomly -q` (one alphabetical process, the chunked-record leak rule) |
| G6 | the comm set | 30 chunks of 25, `--bound 1200`, tags `inc-p2-green-cNN`; the failed node set equals the base record of B-3 |
| G7 | mutation table | 39 mutants, section 6 |
| G8 | client fences | B-5 at head |

## 8. CLAUDE.md block, anchor and owner steps

Anchor: after the INC-R1 block (CLAUDE.md:699-703 at base), before `## Tests` (CLAUDE.md:705). Readers: tests/test_ci_gates.py, tests/test_behavior_dimension_translation.py (in the comm set). Text (one block, ASCII):

**INCIDENT LANE unit (INC-P2 PRICE-NOT-LOST, built 2026-11-16, the S96-FIX incident lane; ONE new flag, default OFF, read PER CALL; absorbs INC-P1 and INC-X1; merged, NOT yet proven):**
- `ENABLE_PRICE_NOT_LOST` (`app/services/price_service.py::price_not_lost_enabled`, the house idiom). ON: the fragrance pair check keeps each perfume's own typed size, never pends a found price for size (no common size -> both prices shown, each with its own size), projects the flag-OFF pending inputs to every price-comparing consumer so nothing says "cheaper" across sizes, and RB restores the shown price only on the wire with additive `price.size_ml` / `price.per_ml` and `metadata.pair_price_sizes`; a re-selected shown price is cached under the request key (through `should_cache_price`); `numbers_match` ignores ml / oz size numbers on the product side (every caller); a genuine Shopify reseller hit is parked ahead of a converted one and seeded; auction / marketplace sellers (`_P2_MARKETPLACE_SELLERS`, Whatnot included) never become the Tier-1 pick, a converted park or a re-selection. OFF: byte-identical except the three unflagged INFO lines `PRICE_OUTCOME` (one per product per build, RB), `PRICE_CACHE_HIT` (every L1 / L2 price hit) and `PRICE_CACHE_SKIP` (the refusal reason at the persist and direct-hit cache writes).
- Production: OFF on web. Neither live bundle reads the new keys; the size label and the per-ml line ride INC-C1 / the X4 price card.
- **Owner steps (names only; a dated ledger line per step):** none to merge beyond the relay's window. The relay flips `ENABLE_PRICE_NOT_LOST` on web in its own window and runs the PROOF ON THE PHONE of the unit's PR; rollback = unset it. Old bare-name price entries expire (7 days genuine, 24 h converted); the owner may flush a pair's keys earlier with the existing admin flush route (`flush_product_cache`, text_routes.py:2085).

## 8b. PROOF ON THE PHONE (H6; from the brief's section and FINDINGS section 4)

Precondition: the unit is merged ("merged, NOT yet proven"), the relay flips `ENABLE_PRICE_NOT_LOST` on web in its own window (no other flip in it), the owner's phone on the store app or the current update (both read `price.amount` / `price.unavailable` only, Q2). Repeat, a few minutes apart where marked:

| pair (typed exactly) | what must be visible | backing check (Railway lines, no brackets in the filter; the saved comparison row) |
|---|---|---|
| "YSL Libre EDP" vs "Lancome La Vie Est Belle EDP" | a price for EACH perfume, no "No confirmed price yet" where a price was found; no price or value bar claims one is cheaper | two `PRICE_OUTCOME` lines, both with an amount, `size_ml` 90 / 100 where the listing names it, `reconcile=both_shown` or `none`; saved row `metadata.pair_price_sizes.mode` |
| a Baccarat Rouge 540 pair | a price for Baccarat Rouge 540 (the 70 ml bottle) | its `PRICE_OUTCOME` line `size_ml=70`, an amount, not `reason=size_mismatch` |
| "Sauvage EDP" vs "Bleu de Chanel EDP", run twice a few minutes apart | the SAME two prices on both runs | run 1 `PRICE_OUTCOME` (`reconcile=reselect` when the 100 ml listing was chosen); run 2 `PRICE_CACHE_HIT layer=l1` (or l2) for the re-selected perfume and the same amounts |
| "Ted Baker M 30ml" vs "Dior Sauvage 100 ML Edp" | both prices, each at its own size; no "cheaper" line, no price bar; no Whatnot seller named anywhere | two `PRICE_OUTCOME` lines `size_ml=30` and `size_ml=100`, `reconcile=both_shown` on the projected side; no `PRICE_OUTCOME` with `reason=size_mismatch`; no `host=www.whatnot.com` |

Across all runs: zero `PRICE_OUTCOME ... reason=size_mismatch` lines while the flag is ON. NOT provable in production: what a race miss shows when a genuine reseller hit exists (rare; B09 only); whether a given shop is reachable (the access walls, P2-16); every stated limit of section 9; the per-ml line and the size label on the screen (they need INC-C1). A suite or a gate in this spec is never presented as this proof.

## 9. Stated limits

- SL1 Nothing changes on a phone until the flip; after it, neither bundle draws `size_ml` / `per_ml` (INC-C1 / X4 does): the user sees two amounts without their sizes until that OTA. The verdict text may say the sizes differ (the prompt's LIKE-FOR-LIKE rule, ES:1092) but this unit adds no per-ml wording (P2-4).
- SL2 The projection gives the consumers today's one-side-pended inputs (P2-4), so `scoring_v2.winner_evidence` may keep today's sentence "has a confirmed Bahrain price while the other relies on an indicative figure" when the projected side lost; neither bundle renders `winner_evidence` (git grep) but the saved row carries it (Q-O1).
- SL3 `numbers_match` no longer rejects a title for a different size number when the user typed a size ("Dior Sauvage 50 ML Edp" vs a "100 ml" title now passes this gate): the later size axis decides; if such a listing survives, the reconcile keeps it labelled with its own size. It applies to every category with an ml / oz token in the product name (a "330 ml" drink too), as P2-8 rules.
- SL4 `size_ml` comes from the listing's own title (then `price.size`) with the strict ml parser: an oz-only title ("3.4 oz"), a title naming two sizes, or no size gives no `size_ml` and the marker says `unknown` for that side.
- SL5 Cache: old entries keyed on bare names are not purged; they expire (7 days genuine, 24 h converted); the owner may flush earlier. A re-selection is cached only when `should_cache_price` passes; the write is awaited inline after the reconcile (one Redis SET + one DB save, only on a swap; `ENABLE_ASYNC_REDIS_OFFLOAD` is absent on web).
- SL6 A projected side that the chokepoint's own checks refuse (out of stock, listing URL, region currency) keeps today's pending line: the safe side.
- SL7 With both prices shown the bundles show the price confidence pill (a confidence statement, never a cheaper claim).
- SL8 `PRICE_OUTCOME` prints per build: a compare with a moderation-window partial prints four lines; a body built outside the request context (the sync timeout partial) logs `reconcile=unknown`.
- SL9 A flag flip in the middle of a request may build one body with today's pending line; no crash.
- SL10 The marketplace list is name-based: a new auction site needs a code change; a first-party "Amazon" / "Walmart" listing is not blocked (the existing `is_marketplace_reseller` scoring still applies).
- SL11 `PRICE_CACHE_SKIP` covers the two genuine write sites named by T3-07 (persist, adapter direct hit), not the supplement / iHerb / pharmacy / Zyte writers.

## 10. Out of scope (P2-16)

The 15 s price race timing and the Phase-2 skip (INC-L1); the Bahrain shop access walls and any access route (owner; INC-P3); every client change (the size label, the per-ml line, the "converted" double label: INC-C1 / X4); per-ml comparison wording; pictures and SCS Phase 1 (INC-I2); the Claude JSON parse (INC-S1); INC-X1's `price.offsize_listing` (not built: showing both prices replaces it); the D05 `other_size` state of X1-R14 (no size pend reaches D05 under this flag: the projected dict D05 reads is today's, an accepted limit for the KB lane).

## 11. Open questions and the answers to the brief

### 11.1 Open questions for the orchestrator (rule before RED)

- O1 (P2-4 premise vs measurement) The ruling's "exactly the inputs ... in the one-side-pended case" is kept: the projection replays flag OFF's own decision (the dry run) and pends for the consumers the side(s) flag OFF pends; when flag OFF pends nothing but V2 ends at different sizes (A19), BOTH sides are projected (flag OFF's outcome-3 shape), because a one-side choice there has no flag-OFF precedent. Measured consequences: (a) `winner_evidence` may keep its price-provenance sentence for the projected runner-up (saved row only; SL2); (b) scoring treats the projected side as price-missing, as today. Alternative: always project both sides (symmetric, no evidence sentence; the inputs then equal flag OFF's both-pended case). The spec builds the ruling's version; a one-line change of step 6 switches it.
- O2 (P2-5 vs X1-R9) X1-R9 limited `size_ml` to genuine, non-converted listings; P2-5 says "every shown fragrance price". The spec follows P2-5 (converted Shopping prices get `size_ml` too, from their own title). Confirm.
- O3 (P2-9 wording) A genuine LISTING-URL Tier-1 park (SCS:8101, under `_park_listing_url_tier1_enabled`) is non-showable at the chokepoint; the literal ruling forbids replacing a genuine park, so a showable reseller hit cannot replace it. Recommend: also replace a park that `_is_listing_url` marks. The spec keeps the literal rule.
- O4 (P2-11 scope) `PRICE_CACHE_SKIP` at the persist and direct-hit sites only (SL11); widen to the four supplement writers?
- O5 (P2-7 latency) The cache write is awaited inline (SL5). A fire-and-forget keeps the response time unchanged but loses the B04 ordering guarantee; the spec keeps the await.
- O6 (naming) The pair marker is `metadata.pair_price_sizes` because `price_basis` is already a price-level key of shopify_pdp_service (1.8).
- O7 (SSE) The stream `prices` event is restored too (2.5), although no live client streams (T7-07), so a streaming client never sees "pending" then a price for the same side. Confirm.
- O8 (B-4) If a log-count test counts the new unflagged lines, it becomes E1 (4.1) for a ruling.

### 11.2 Answers to the brief's questions (measured at b0ad2603)

- Q1 Sync and stream build the explicit-pair Step-1 dicts at SCS:4478-4493 / 5193-5206 (brand "", name = the typed half, variant None, search_query = the half); with `ENABLE_PRODUCT_RESOLVER` ON, `apply_resolution` (PR:1303-1328) sets brand, name = line, variant = "<CONC> <n>ml" (size from `extract_size_ml_any` of the typed name, PR:672). `full_name` is built in `_fetch_product_data` (SCS:6043-6048) as `dedup_brand_name(brand, name + " " + variant)` (SCS:1377-1393), so `full_name` carries the typed size in BOTH modes ("Dior Sauvage 100 ML Edp" OFF, "Dior Sauvage EDP 100ml" ON) and `effective_pair_size_ml` (which reads `full_name` first) sees 100 in both. The brief's premise (iii) is right that `variant` is not read directly, but it reaches the check through `full_name`. Smallest equal reader: `typed_size_ml(p) = extract_size_ml_any(p["full_name"] or p["name"])` (A02: 30 / 100 in both modes; an oz typed size snaps the same way the resolver does).
- Q2 Section 1.5: no client code in either bundle draws a cheaper / savings / best-value / smart-pick claim from the two amounts; `getPriceDiff` (ResultsScreen 683f56c0:678-686, HEAD:716-724) is dead (its result `priceDiff`, :697 / :735, is never read); the bars and the value caption are server keys and both bundles drop `limited_data` dims (DimensionBars.tsx:82-88); no bundle reads a size key. No STOP.
- Q3 `ENABLE_DATA_GUARDS_V2`'s list (deny_hosts.py:54-80 `DENY_HOSTS`, :87-89 `DENY_LABELS`) holds only Fragrantica (21 domains), Parfumo (2), Basenotes (2) and fimgs.net: banned DATA sources, not sellers; no Whatnot, no eBay. Smallest seam: `_P2_MARKETPLACE_SELLERS` + `is_auction_marketplace_seller` in PS, read at the Tier-1 loop (after PS:10568), the adapter converted park (SCS:7889-7893) and the V2 candidate filter.
- Q4 The read key is `build_size_aware_price_cache_key(brand, name, variant, region, search_query, category=canonicalize_category(category))` with the Step-1 values (SCS:6033-6041 -> 6138 -> 7176). Resolver OFF: brand "", name = the typed half, identity text = the half; ON: brand, line, "<CONC> <n>ml", search_query without the size: two different keys, each read by the next request of the same mode. The write mirrors it from `products[i]` (2.6; B04 / B05). `should_cache_price("Bleu de Chanel EDP", noon dict, "fragrances")` passes when the dict carries a title, a PDP url, no `in_stock: false` and passes `_selection_match` / `_brand_evidence_ok` (the matcher noon's reader already ran); NOT executed in this read-only round: DEFERRED TO RED as B04 with the T3 noon dict shape.
- Q5 Section 1.6 (ten consumers with file:line); smallest seam: one projection at the end of the flag-ON reconcile in PS plus a non-mutating restore in RB's wire copies; no SS / ES edit.
- Q6 SCS edits: 4394-4395 (bind), 4667-4669 (cache call), 5128-5129 (bind), 5434-5436 (cache call), 5495-5518 (SSE), 7104-7127 (trace notes), 7188-7190 (L1 line), 7258-7262 (L2 line), 7889-7893 (park filter), 7950-7953 (skip line), 8268-8272 (reseller park), 9428-9429 (skip line), a new method after 9431, and the import block 1435-1520. None inside 6018-6906 (INC-I2's `_fetch_product_data`, Phase 1 about 6030-6450).
- Q7 Section 1.7 (26 call sites incl. rating_service.py:167 and SCS:3499-3500); the change is in the function, so every caller follows; non-ml / oz numbers unchanged (A24).
- Q8 A KB price is served in Phase 1 (SCS:6133-6139) and lands in `result["price"]` (`_cached` True, `_cache_source` "kb", title and size with "<n>ml"); its offers are seeded as candidates. It passes the reconcile and the chokepoint like any price: P2-3 applies, P2-5 stamps `size_ml` from its title; a KB-side re-selection is NOT cached (B06); `PRICE_OUTCOME` says `cache=kb`.
- Q9 4.2 lists the 27 reconcile / size_mismatch files and the 11 numbers_match files; all run flag OFF and stay unedited; no flag-ON behaviour is pinned at base (the flag does not exist), so no E-row (4.1).
- Q10 No CLAUDE.md row for this flag (or for `ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX`) at base; anchor after the INC-R1 block (CLAUDE.md:699-703), before `## Tests` (:705); readers tests/test_ci_gates.py and tests/test_behavior_dimension_translation.py.

## Not done in this spec

No pytest, jest, tsc or eslint run (read-only round, H5 c): sections 1.10 B-1..B-5, every RED row and every mutant are DEFERRED TO RED / GREEN with their commands. Not measured by execution: `should_cache_price` on the logged noon dict (Q4), the B-4 log-count tests, the comm-set base record at b0ad2603, which CLAUDE.md mentions in tests open the file. No scratch worktree was created; no file in the worktree other than this spec; no production value was read.
