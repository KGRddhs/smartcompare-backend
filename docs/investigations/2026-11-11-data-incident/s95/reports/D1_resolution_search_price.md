# D1 - Product resolution, the searches sent, price selection (S95-FIX, read-only)

Code cited at 731bcddf (export under scratchpad/src/731bcddf). SCS = app/services/structured_comparison_service.py, PS = app/services/price_service.py. E = ESTABLISHED (read in code or a quoted log line), L = LIKELY (inference). Nothing here says a production problem is fixed.

## Summary

The typed text goes into every search exactly as typed. Nothing turns it into a known product first. On the explicit-pair path the backend sets `brand=""` and `search_query=<typed text>`. No later step adds a brand or corrects the spelling. The category resolver, the fragrance gate and the KB all work on the category, or on an exact id, never on the product's identity. So "Tyger" was searched on US Google Shopping and Google Images as a bare word, which returned truck parts and the Blake poem. "stronger with you" went to the price gates without a brand. Several gates only fire when the query names a house: the decant floor, the luxury flagship basis and the wrong-brand fence. Those gates stayed silent, so a 15 ml decant was picked (it was parked, not shown) and a noon.com listing of unknown size and concentration won. The price dict carries no size field, and the client shows no size, so 29.320 BHD appeared without a size.

## (a) The request and the client

| Item | Finding | Cl. |
|---|---|---|
| Screen and service | HomeScreen `runTextCompare` calls `streamComparison({product_a, product_b}, {selected_category?})` (SmartCompareApp/src/screens/HomeScreen.tsx:424-461). That becomes GET `/api/v1/text/compare/stream?product_a=&product_b=[&selected_category=]` (src/services/api.ts:880-899). REST twins exist at api.ts:742 (GET) and api.ts:1047 (POST). | E |
| selected_category | Sent only when the user tapped the Fragrances chip AND the cached categories_live has fragrances (HomeScreen.tsx:130-138, 455-457). Whether it was sent this time is not known. | E / L |
| Autocomplete, suggestions, "did you mean" | None. The inputs are plain TextInputs with `autoCorrect={false}` (src/components/TwoInputShell.tsx:696-713), so even the OS spelling correction is off. Recent searches are saved but not shown (`const [, setRecentSearches]`, HomeScreen.tsx:126). | E |
| Backend suggest or catalog endpoint | None. The text routes are /compare (POST, GET), /compare/stream, /quick (admin), /prices/{product} (admin), /price-kpi and /parse (admin key, debug) (app/api/text_routes.py:673, 891, 1097, 1564, 1665, 1741, 2163). Home has /savings, /smart-pick, /trending (app/api/home_routes.py:200, 702, 935). No route resolves a name. | E |
| Route to orchestrator | The stream route builds `explicit_pair=(product_a.strip(), product_b.strip())` (text_routes.py:1136-1138) and passes it on (text_routes.py:1263). | E |

## (b) Resolution on the explicit-pair branch

Step 1 (sync SCS:4438-4453; stream twin SCS:5140-5153; shared builder `_explicit_pair_products` SCS:1959-1971) builds `{"brand": "", "name": safe, "variant": None, "category": classify_category_from_text(safe), "search_query": safe, "_explicit": True}`. The comment says it skips `parse_product_query()` on purpose: the user typed both halves, and skipping saves an LLM call and a parse failure (SCS:4439-4441). (E)

Later steps, checked one by one:

| Step | What it does with a typed name | Cl. |
|---|---|---|
| `classify_category_from_text` (extraction_service.py:1326-1357) | Matches category WORDS only, never brands or lines (its docstring says so). "Tyger" and "stronger with you" both give "other". | E |
| `_resolve_pair_category` (SCS:477-541) | With no category word: a real chip wins, else `classify_category_llm(names)` runs (SCS:538). That classifier returns ONE word (prompt at extraction_service.py:1365-1373, call at :1387-1410; it goes through router site "classify", Claude Haiku under consent v3, llm_router.py:11, 210). It returns a category only, never a brand or a corrected name. The page's fragrance spec rows show the pair resolved to fragrances, by the chip or by the classifier. | E (code) / L (which one) |
| Fragrance-only gate (believed OFF) | `post_resolve_refusal` (app/services/category_gate.py:650-699) decides category only. Its KB arm `kb_evidence` always returns False (category_gate.py:376-379). Even with the flag ON, "Tyger" proceeds as "other". | E |
| KB (ENABLE_KB_FIRST_SERVE OFF) | `fetch_cards` looks up an exact id built from (brand, name, variant) (app/services/kb_serve.py:162-164). There is no alias or fuzzy match. With brand "" and a misspelling it cannot hit, even with the flag ON. `kb_brands` (300 rows) is only read by kb_service's writer paths (kb_service.py:58, 98, 828), with no live lookup. | E |
| Brand lists in code | `FRAGRANCE_BRAND_KEYWORDS` (PS:574-583) holds house names, used as substring tests. There is no line-to-house map ("stronger with you" to Emporio Armani, "tygar" to Bvlgari). data/variant_hint_reference.json:23 maps "stronger with you" to a gender only. Neither product is in warmer_catalog, trending_curated, usable_exact_genuine_truth or validation_gold_truth (grep). | E |
| Spelling correction | None anywhere on this path. | E |

Result: "Tyger" stays brand "", name "Tyger". The image and the reviews ran on "Tyger" alone (the log line "Fetching reviews for:  Tyger" has the double space that the empty brand leaves, review_service.py:765). "stronger with you" stays brand "", name "stronger with you". (E)

**The q= parser path, for comparison.** `_parse_with_budget` (SCS:4057-4110) calls `parse_product_query` (extraction_service.py:1531-1568). Router site "parse" is role text, so it runs on Claude (`claude-haiku-5-5` by default) when ENABLE_ANTHROPIC_TEXT is on and consent is >= 3. Below consent 3 it takes the OpenAI call while ENABLE_OPENAI_PRE_V3 is on (llm_router.py:9-19, 55, 211). The prompt (extraction_service.py:105-142) returns `brand, name, variant, category, search_query` per product and "normalize brand names". It has no separate concentration or size field (both go in `variant`), no spelling-correction rule, and no confidence, "unknown" or candidates output. Fewer than two products gives `PRODUCT_PARSE_FAILURE_MESSAGE` (SCS:1809-1811, 4467-4474). It might have produced "Emporio Armani / Stronger With You", but nothing in it can say "I am not sure which product this is". (E for code; L for what Haiku would have emitted.)

## (c) The search strings actually sent (per product, explicit pair)

`_fetch_product_data` reads `brand`, `name`, `variant` and `search_query` from the product dict, and `full_name` comes from `_product_display_identity` (SCS:5966-5980). Every search below comes from those fields:

| Search | String | Where | Cl. |
|---|---|---|---|
| Unified organic (Serper web) | `"<typed> specifications reviews price"`, num 10. Specs and reviews reuse this payload. | SCS:6139, 6155/6164, 6205, 6242-6246 | E |
| Serper Shopping | `_clean_shopping_query(<typed>)`, `gl=us`, `num` 10. The gl=bh primary is bought only for countries on SERPER_SHOPPING_PRIMARY_COUNTRIES (default empty, so the primary is skipped). The result says `shopping_region="us_fallback"` whenever the bh leg is skipped or empty. That is why us_fallback fired: by construction, not by a failed bh call. "items=40" is the length of the list Serper returned. The code asks for num 10, so Serper ignores num on /shopping (L). The trace line is SCS:7943-7947. | serper_service.py:1031, 1048-1093, 891-900, 951; SCS:7910/7923 | E (L for the num behaviour) |
| Serper Images | `full_name` = `"Tyger"`, num 1. It takes the first valid URL with no relevance check (Tier 1.5b, the unified-payload image, is tried first). | image_service.py:255, 276, 295-311; SCS:6261-6269 | E |
| Reviews | Uses the unified payload. Only if that is None does it search `"<typed> <CATEGORY_REVIEW_TERMS>"`. | review_service.py:764-769 | E |
| Specs | Unified payload, else `"<typed> specifications features"`. The TIER2 refill uses `"<brand name variant> <field> specifications"`, num 3. | SCS:6861-6862, 811-822 | E |
| BH store adapters (woo, salla, occ, magento, unbxd, rest_json, noon, shopify_gcc) | `full_name`, passed to each store's search (e.g. woo `?search=<term>`, noon via `build_adapter_search_terms`). | SCS:7474-7499, 7751; woocommerce_service.py:340; noon_service.py:500-501 | E |

No category word ("perfume") is added anywhere; the prompt rule forbids appending price words (extraction_service.py:117, 128). "Tyger" on US Google Shopping returned Tyger Auto truck parts (log). Some were dropped as accessories ("cover" is in ACCESSORY_KEYWORDS, PS:467-468; filter at PS:10528) (E). The rest were LIKELY dropped by the other shopping filters, which the PRICE_FILTER_TRACE line would show (PS:10652-10664).

**The seam for one canonical "Brand Line Concentration".** It is ONE seam: the product dict built in Step 1. Every downstream query takes its string from that dict's `brand`, `name`, `variant` and `search_query` (SCS:5966-5973). That covers the unified query, shopping, adapters, images (via full_name), reviews and specs. The dict is built in three places: sync SCS:4444-4452, stream SCS:5144-5153, and the shared `_explicit_pair_products` SCS:1959-1971. The q= parser output lands at SCS:4476 and its stream twin. A resolver must rewrite the dict before `_resolve_pair_category` (SCS:4488) and before `_fetch_product_data` (SCS:4564). Then no downstream call site needs to change. (E)

## (d) Price selection for "stronger with you"

How `_get_price` (SCS:7067) works, in order:

1. L1 and L2 cache, checked against the same bare name (SCS:7107-7150).
2. Tier 1 Serper Shopping, then `extract_price_from_shopping` (SCS:7959-7962). A GENUINE Tier-1 price returns at once. A `converted_usd` price (every us_fallback item, PS:10514, 10599) is PARKED as `converted_fallback` / `_parked_price` (SCS:7998-8005).
3. Official, Algolia and the other direct hits.
4. `_consume_adapter_prefetch` (SCS:8296). It short-circuits on the most AUTHORITATIVE genuine adapter hit. Converted hits are only seeded or parked (SCS:7787-7826). The winner is chosen by `select_best`: in stock, then authority, then precision, then amount (PS:8706-8722). It is never the cheapest.

The three log lines:

| Line | Tier and why | Checks it passed | Cl. |
|---|---|---|---|
| woo 2.442 BHD oudworlds.com | Woo adapter (woocommerce_service.py:160-290). oudworlds prices in OMR, so the candidate is `converted_usd` (woocommerce_service.py:208-221; the earlier note at PS:14262 says "oudworlds.com ... (OMR, converted_usd)"). A converted hit cannot short-circuit (SCS:7787-7791), so it lost to the genuine noon hit. At about 2.4 BHD it is almost certainly a clone oil or decant (L). Its gates were counterfeit words, strict-or-selection-primary, numbers, variant_mismatch and `_selection_match`. None of them can see a missing brand, because the query has none. | E (mechanism) / L (method, title) |
| `[PRICE] Selected: Aura Fragrance (tier 0.5) at BHD 6.38 ... size=15ml conc=EDT` | Tier 1 shopping (PS:10689-10694) from us_fallback, so `converted_usd`, so parked, not shown. It survived because the decant floor `is_implausible_low_fragrance_price` only applies when the NAME contains a house keyword (PS:1626-1632), and "stronger with you" has none. `is_luxury_brand` was False, so no 50 BHD floor and no 100 ml flagship bonus (PS:10454-10459, 10596). If every BH adapter had missed, this 15 ml decant was the parked fallback (L). | E |
| `BH adapter direct hit ... 29.320 BHD via noon.com (page_scrape_jsonld)` | The noon adapter: search, gates, PDP JSON-LD confirm (noon_service.py:474-534). `page_scrape_jsonld` is genuine, so it won the short-circuit (SCS:7833-7885) and was written to cache under the bare-name key when `should_cache_price(full_name, ...)` passed (SCS:7874-7877). The gates (noon_service.py:215-243) run against "stronger with you": the brand fence has no brand, the concentration axis has no query concentration, the size axis has no query size, and the flanker set is only `elixir, supreme, absolu, intense, extreme` (PS:7164-7166). So "Intensely" or "Absolutely" listings, an EDP, a 50 ml or a gift set without "set" in the title could all pass. Which listing it was is NOT known: the title is not logged. | E (gates) / L (identity) |

**Why no size on screen.** The noon price dict holds amount, currency, retailer, url, source_method, title, confidence, and optionally in_stock, seller and brand. It has no size or concentration key (noon_service.py:443-465). Only shopping candidates carry `size` (PS:10642-10644). `reconcile_pair_sizes` returns at once when either side has no positive amount (PS:2301-2309), and Tyger had none. So no fairness pass looked at the size or annotated it. The client has no code that renders a price size (grep of src for price.size / size_ml found nothing). Showing it needs INC-X1, or the server folding the size into a field the card already shows. (E)

**Why Tyger got "No confirmed price yet".** All three inputs failed. The misspelt bare word matched no BH store listing (Bvlgari's is "Tygar"). The US shopping rows were truck parts and were filtered (above). Nothing genuine was found, so the side pended. The exact final tier (organic, Tier 1.5 fan-out, estimate suppressed at display) is not established from code alone (L).

## (e) Root causes

| id | cause | where | class | conf |
|---|---|---|---|---|
| RC1 | The explicit-pair path never resolves a typed name. Brand stays "", the name stays as typed, nothing corrects the spelling. The category resolver, classifier, gate and KB return a category or an exact-id miss, never an identity. | SCS:4438-4453, 5140-5153, 1959-1971; SCS:477-541; extraction_service.py:1326-1410; category_gate.py:376-379, 650-699; kb_serve.py:162-164 | RESOLUTION | E |
| RC2 | Every search sends the bare typed string with no category word: US shopping, the first image with no relevance check, the unified, review and spec queries. "Tyger" returned truck parts and the poem. | SCS:6139, 7910/7923, 6261; serper_service.py:1048-1093; image_service.py:295-311; review_service.py:767 | SEARCH | E |
| RC3 | The price identity gates are keyed on a house name in the query. With no brand: the decant floor, the luxury floor and flagship basis, and the wrong-brand fence are all off; no concentration or size axis can mismatch; the flanker list is narrow. A 15 ml decant was selected (parked), and a noon listing of unverified identity and size won. | PS:1626-1632, 10454-10459, 10596, 7164-7166, 8692-8702; noon_service.py:215-243 | DATA | E (gates) / L (wrong listing) |
| RC4 | The price is shown without its size. Genuine adapter dicts carry no size or concentration, the pair-size reconcile skips a one-sided pair, and the client renders no price size. | noon_service.py:443-465; PS:2301-2309; client grep | DISPLAY | E |
| RC5 | A weakly identified price is cached under the bare-name key. Later "stronger with you" requests are served the same unsized noon price from L1/L2, checked only against the same bare name. | SCS:7874-7877, 7107-7150 | DATA | L |
| RC6 | No path asks the user which product they meant. There is no suggest endpoint, autocorrect is off, and the parser has no confidence or candidates output. | TwoInputShell.tsx:713; app/api route list; extraction_service.py:105-142 | RESOLUTION | E |

## (f) Fix seams

| id | fix | user sees | size | ships |
|---|---|---|---|---|
| F1 | A Step-1 resolver at the one seam (SCS:1959-1971, 4444-4452, 5144-5153, plus the parser output at SCS:4476). Steps: deterministic first (kb_brands plus a curated house-and-line alias table plus edit-distance <= 2 on line names, so Tyger becomes Tygar); then one bounded Claude call on a new router site with a closed JSON schema (as `disambiguate` does, llm_router.py:223) returning `{brand, line, concentration, size_ml, confidence, candidates[]}`. It rewrites `brand / name / variant / search_query` before `_resolve_pair_category`, so every search, gate and cache key inherits the canonical identity. That alone re-arms RC3's brand-keyed gates. | "Emporio Armani Stronger With You EDT" and "Bvlgari Tygar" searched, priced and pictured correctly | L | server deploy |
| F2a | When resolution confidence is low or a side is unresolvable, refuse BEFORE any fetch with the error event `{success:false, code:"INSUFFICIENT_DATA", reason:"placeholder_identity"}`. Coded stream events pass through the route unchanged (text_routes.py:1332-1357), the client forwards `reason` (api.ts:986-993, 850-856), and `friendlyErrorKey` maps it to "We need clearer names to tell which products these are. Add the brand and the fragrance name." (errorCopy.ts:83-93; en.json:703). That copy arrived with S81-11 (5fcb9fba, an ancestor of ea47cbfb). That the store bundle carries it is L, and depends on the second OTA having shipped. An older bundle shows the default "Sharper match coming up - add the brand and the fragrance name." (en.json:111). The current app NEVER renders the backend `error` string (HomeScreen.tsx:497-508), so a PRODUCT_PARSE_FAILURE_MESSAGE-style sentence or a candidate list in `error` would not appear. Check that the failure arm refunds the compare. | An Alert asking for clearer names instead of a wrong comparison | S | server deploy |
| F2b | A real "Which one did you mean?" picker: a new code (e.g. AMBIGUOUS_PRODUCT) carrying `candidates[]`, rendered as tappable rows that re-run the compare with the canonical name. It is JS only, so it ships over the air on runtime 1.0.0. Older bundles fall to the default copy (errorCopy.ts:110-111), which stays backward-safe. Optional later: a suggest endpoint plus typeahead (L, OTA plus server). | Candidates such as "Bvlgari Aqva / Bvlgari Tygar" to tap | M | over-the-air update (+ server deploy for the code) |
| F3 | A listing-identity gate against the RESOLVED product in `_selection_match` / `select_best` (PS:8341, 8627), so every tier and adapter inherits it. Require the brand and line in the title or brand field; on concentration and size, use the resolved defaults; reject decant, sample, travel or vial titles and sub-30 ml prices for an unsized ask; reject clone markers (an oil or attar from another house, "inspired"); widen flankers per line ("intensely", "absolutely", "freeze", "parfum" ...). Stamp `size_ml` and `concentration` (from `extract_sizes_ml(title)` / `extract_concentration`) on every selected price dict. INC-X1 then renders it. | Only a matching full-bottle price, shown with its size | M | server deploy (size label: over-the-air update via INC-X1) |
| F4 | Add a category word for a fragrance pair in the shopping, image and unified queries, and an image relevance check (title or host must carry the resolved brand or line). This backs up F1. | No truck parts or poem pages | S | server deploy |
| F5 | After F1 and F3 ship, purge the cached price rows written under the bare-name keys ("stronger with you", "Tyger"), L1 and L2. | Old unsized price stops coming back | S | owner or ops step |

## Log reads for the relay (to confirm the L items)

- The noon hit's listing title, size and in_stock: the saved comparison row's price.title for product 0 (it is not in the log line).
- The full oudworlds woo line (source_method and title), and any `[NOON]` lines in 21:19:46-21:20:06.
- `[GL_FALLBACK_TRACE] ... category=` for both products, to see whether the pair resolved to fragrances, and whether the request URL carried `selected_category`.
- `[PRICE_FILTER_TRACE] zero candidates ... 'Tyger'` (first 3 titles), and the last price tier logged for Tyger.
- Which Claude calls made up the 5 (classify? specs? reviews?), to see whether `classify_category_llm` ran.
