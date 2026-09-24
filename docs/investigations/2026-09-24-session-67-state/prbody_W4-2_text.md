## W4-2: the shopping rung must not put a search link in `price["url"]` (PO-RECORDED-MEASURED-03), behind `ENABLE_SHOPPING_DISCOVERY_URL_SPLIT` (default OFF)

### Defect
`extract_price_from_shopping` sets `url = item["link"] or build_retailer_url(retailer, name)` on every Serper-shopping candidate. The stash mirror `_seed_shortcircuit_candidates` does the same. That value is either Serper's google.com/search link or a retailer SEARCH url we made up ourselves. Two consequences:
1. The display backstop in `is_price_showable` (`non_pdp_url`) pends the rung's own output.
2. 9 of the 46 `RETAILER_SEARCH_URLS` templates slip past `_is_listing_url`: amazon, amazon.ae, amazon.sa, target, newegg, adorama, apple, ebay and aliexpress. Those rows ship as showable and cacheable on a url we fabricated and never fetched.

### Design
- **The flag reader is coupled to W4-1 (ruling R1).** `shopping_discovery_url_split_enabled()` is true ONLY when `ENABLE_SHOPPING_DISCOVERY_URL_SPLIT` AND `ENABLE_SHOPPING_CURRENCY_TRUTH` are both truthy. Both are read on every call (`os.getenv`, `.strip().lower()`), so rolling back W4-1 also turns the split off.
- **The splitter `_shopping_split_discovery_url` has three rungs:**
  - rung 1: a `link` that `_is_listing_url` flags gives `(None, link)`;
  - rung 2: no link gives `(None, build_retailer_url(...))`, which is None for an unknown retailer, so nothing is invented;
  - rung 3: a real PDP link gives `(link, None)`, unchanged.
- **The front door and the stash mirror apply the same splitter.** A split search link goes in the PRIVATE key `_discovery_url` (ruling R4), and `url` is None.
- **The tier-7 `converted_fallback` backfill guard is the edit that does the work (ruling R2).** A parked row carrying `_discovery_url` never has a url re-minted with `build_retailer_url`. `_discovery_url_of` reads the key without checking the flag (R3), so a rollback in the middle of a request cannot re-mint one either. A url-less row without the key still gets today's backfill (pinned).
- **The Tier-1 park edit is dropped (R2).** With W4-1 on, its elif is unreachable for shopping output, and `ENABLE_PARK_LISTING_URL_TIER1` is left unchanged (R6g).
- **Wire surfaces.**
  - `public_price_view` strips `_discovery_url` while the exact gate is on. That covers the compare surfaces and `/text/price-kpi`.
  - Fixer addition: `GET /api/v1/text/prices/{product}` returns the raw `get_regional_prices` dicts and never calls `public_price_view`. With both flags ON it would have shipped the key; at base the same row was pended. `get_regional_prices` now drops `_discovery_url` from a COPY of a showable row while the exact gate is on.
  - The strip removes ONLY `_discovery_url`. Every other `_`-prefixed key (`_cached`, `_seed`) ships exactly as at base (test_19c).
  - With the gate off the row ships as-is, which is the stated rollback shape. A row without the key (every flag-OFF row) comes back as the same object.
  - This route's existing `_cached` leak is left alone and recorded as a follow-up.
- **Canary.** One line, logged for `best` only (R6e): `[SHOPPING_DISCOVERY_URL] split url->_discovery_url host=<www-stripped host of the split url> reason=<listing_url|synthesized> for <name>`. Read it alongside W4-1's `[SHOPPING_CURRENCY_TRUTH] relabel ...` line.

### Flag row
- **`ENABLE_SHOPPING_DISCOVERY_URL_SPLIT`**: default OFF, read PER CALL, and only takes effect when `ENABLE_SHOPPING_CURRENCY_TRUTH` is also ON.
- **Effect ON:** a shopping row whose only link is a search link DISPLAYS as `converted_usd`. It is showable but never genuine: 24 h TTL, and under the exact gate both `should_cache_price` and `select_best(require_url=True)` refuse it. `url` is null and the search link is kept in the private key.
- **Composition:** because of the R1 coupling, every row this flag un-pends is `converted_usd`.
- **Activation order:** W4-1's `ENABLE_SHOPPING_CURRENCY_TRUTH` first, then this flag.
- **THE FLIP WAITS ON AHMED'S PRODUCT CALL (R5).** The phones' 97b5f15 bundle and HEAD render these rows as "BHD x (converted from USD)" / "(محول من الدولار)" with the 'Local listing' pill. That is at `ResultsScreen.tsx:392-400` in 97b5f15, and `ResultsContent.tsx:147` and `ResultsScreen.tsx:446` at HEAD. W4-2 is what makes W4-1's ruling-5 misnomer visible. The flag stays off until Ahmed has seen that rendering and chosen option a, b or c as recorded in W4-1.

### KPI / canary
- **Expected signature:** the pend rate falls and `usable_exact_genuine` does NOT rise. KPI clause (d) still requires a PDP url (R8). Publish the pend-rate fall separately.
- **Any `usable_exact_genuine` drop on these rows comes from W4-1 alone.**
  - Under R1 the split reader is False whenever `ENABLE_SHOPPING_CURRENCY_TRUTH` is off, so with W4-1 off W4-2 changes nothing. This is pinned byte-identical: the R1 params of tests 7_off, 8_9_off, 13 and 15, which mutation M14 reddens.
  - The genuine label is lost before W4-2 acts. Measured at base 6ab9d7ea with TRUTH on and the split unset, the Amazon no-link row is already `converted_usd`. Test 13's base literals record the same: with W4-1 on, every shape is `converted_usd`.
- **W4-2 adds no label change of its own.** Every row it touches is `converted_usd` with the split on or off, and the rows it un-pends stay non-genuine. It has two extra effects:
  1. the display un-pend, i.e. the pend-rate fall;
  2. on the no-link rows of the 9 non-listing templates, `should_cache_price` goes from True to False. That is the 24 h converted un-cache disclosed under R6a below.

  Any second-order KPI effect of the resulting re-runs (Serper plus Tier-1.5 on each such request) is unmeasured.
- Watch the canary line's host distribution: google.com means rung 1, and retailer hosts mean rung 2.

### Honest limits and disclosures
- (R6a) **Un-cache cost.** Rows from the 9 non-listing-template retailers lose their 24 h converted cache. Each request then re-runs Serper plus the Tier-1.5 cascade, including while the key is unfunded or blocked by the spend gate. Accepted, because a fabricated url must not be cached. This is W4-2's only KPI-relevant cost; the genuine-label loss belongs to W4-1 (see KPI above).
- (R6b) `amazon.ae` AND `amazon.sa` both map to the amazon.com template, because `RETAILER_SEARCH_URLS` matches by substring in insertion order. Follow-up PO-RECORDED-MEASURED-03b, which also covers the `_is_listing_url` blind spot for those 9 shapes when the link is a REAL Serper link.
- (R6c) `_is_listing_url` does not catch real Serper links of the `google.com/shopping/product/<id>` shape. Follow-up 03c.
- (R6d) **Consumers of the split row:**
  - the Tier-1 park and tier-7 return;
  - the broader-search rung (`extract_price_from_shopping(broader_name, ...)` -> `_persist_genuine_price` -> return);
  - the race-miss `_parked_price` return (scs ~:5729);
  - the stash;
  - `GET /text/prices` via `get_regional_prices`, now stripped of `_discovery_url` only, under the gate.
- (R6e) The canary logs once for `best`, never once per candidate. Pinned: a split sibling behind a PDP `best` logs nothing.
- (R6f) Comparison-history rows carry `_discovery_url` only when the exact gate is off.
- (R6g) `ENABLE_PARK_LISTING_URL_TIER1` is unchanged.
- **Gate-off consequence, pinned as CURRENT behaviour (red-gate ruling 4).** With `ENABLE_EXACT_PRICE_GATE=false`, a discovery-only row IS cacheable and selectable, because the gate is what refuses it. On the real `_get_price`, the url-less Amazon row is written to L1 with `_discovery_url` inside, and handed to the L2 writer with url NULL (tests 12b/12c). With the gate off, `public_price_view` and the `/text/prices` strip both return the row unchanged. Prod runs with the gate ON.
- **Flag-ON pin contradictions.** These 8 existing nodes must be made flag-aware before activation. They pin today's behaviour of putting the search url in `url`, so with SPLIT+TRUTH set process-wide they go red. They are the same class as `test_price_cache_bust_probe`, and CI runs with flags unset, so nothing is red today:
  - `tests/test_shopping_currency_truth.py::test_5_google_search_link_is_never_local_bhd_flag_on`
  - `tests/test_shopping_currency_truth.py::test_10_local_bhd_requires_host_evidence_flag_on[www.google.com/search?ibp=oshop&q=acme+widget+deluxe]`
  - `tests/test_shopping_currency_truth.py::test_10_local_bhd_requires_host_evidence_flag_on[missing-link]`
  - `tests/test_shopping_currency_truth.py::test_12_showable_chokepoint_still_pends_google_row_non_pdp_url`
  - `tests/test_url_extraction.py::test_price_url_falls_back_to_retailer_search_when_no_link`
  - `tests/test_url_extraction.py::test_price_url_falls_back_when_link_is_empty_string`
  - `tests/test_url_extraction.py::test_price_url_falls_back_when_link_is_none`
  - `tests/test_url_quality.py::TestShoppingUrlExtraction::test_no_link_gets_retailer_search_url`

  With TRUTH alone, the same files are 196/196 green.
- **Client.** A grep for price.url or discovery_url in SmartCompareApp finds nothing at HEAD or at 97b5f15. `ProductPrice.url` is already optional, so an absent url is a valid shape for the pre-OTA client. The rendering change is the R5 product call above.

### Follow-ups
- 03b: the `RETAILER_SEARCH_URLS` amazon.ae/amazon.sa collision, plus the `_is_listing_url` blind spot for real links.
- 03c: google.com/shopping/product links.
- `rating_source.url` gets the same split. It is the only link the pre-OTA client opens.
- Rewrite the 8 pins listed above to be flag-aware.
- The `_cached` leak on `/text/prices`. test_19c pins that this unit does not widen its strip into it.
- NETWORK_FLAKY: `tests/test_shopify_discovery_l13.py::TestFetchShopifyPrice::test_fetch_uses_catalog_and_matches`. It never uses its patched `_fetch_shopify_catalog` and makes live libcurl fetches.
- The comm-gate netguard does not stop libcurl, because curl_cffi resolves DNS in C. With a curl_cffi guard added, each full comm run blocked 129 live requests across 29 nodes, e.g. test_openai_breaker x60 and test_supplement_branch_genuine::test_cde2 x15. The standing comm tooling should add that guard.

### Gates
- **Unit file:** 114 passed in each of 5 env states: unset; SPLIT; TRUTH; SPLIT+TRUTH; SPLIT+TRUTH with `ENABLE_EXACT_PRICE_GATE=false`. Both the netguard and the curl_cffi guard were on, with 0 network attempts.
  - At base 6ab9d7ea the OFF-state pins pass unchanged and only the ON tests are red. That was measured on the 113-node file.
  - test_19c is ON-only. It was not re-run at base, but deleting the strip (D1a) turns it red.
- **Mutations:** 27 mutations in the fix round, plus the M0 control run: 16 M-rows (the spec table), 8 N-rows (adversary N1/N1b/N2/N3/N3b/N4/N4b/N6) and 3 D-rows (the regional strip D1a/b/c). Each one turns its named pin red.
  - The r1 adversary re-ran them with matching red counts and added 15 of its own mutations. 14 went red; X15 (strip every `_`-prefixed key) survived.
  - The polish pass added test_19c. X15 now turns it red (1 failed / 113 passed), and D1a re-run turns test_19 and test_19c red.
  - Every restore was checked by sha256 against a byte snapshot.
- **Preserve:** 164/164 at head (re-run after the polish) and 164/164 at base.
- **Lint:** ruff 0.16.5 E9,F63,F7,F82 clean; py_compile clean on all three files.
- **Comm gate:** a module-reference set of 309 files plus the unit file, run with the same run_comm.py and netguard plus a curl_cffi guard.
  - `comm -13` base->head is EMPTY, including against the originally recorded base.
  - Head fails only the 2 baseline ids and the network id the ruling accepted.
  - The polish pass changed only the test file (append-only, +22 lines). The app files are byte-identical to the gated fix round.
- **Byte identity:** base -> head -> base2, with 0 of 1656 records differing on every pairing (OVERALL 251ca82a... on all three).
  - Honest scope: the corpus harness never enters the shopping rung, so this proves only that the shared spine did not move.
  - The rung's flag-OFF identity rests on the literal pins verified at base, and on a 21-record base-vs-head `_get_price` differential probe with 0 differences.
- **Full free-tier suite (spec gate 5):** not run locally; left to CI.

🤖 Generated with [Claude Code](https://claude.com/claude-code)