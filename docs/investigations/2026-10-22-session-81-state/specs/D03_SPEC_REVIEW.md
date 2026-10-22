# D03 SPEC REVIEW (adversarial): DENY-AND-GUARDS (ENABLE_DATA_GUARDS_V2)

- Unit: D03 DENY-AND-GUARDS (PLAN_S81 M1, lane B). Flag `ENABLE_DATA_GUARDS_V2` (new, default OFF).
- Spec reviewed: `.qa-s80/D03_UNIT_SPEC.md`, sha256 `3460ffabdedb35985ba6e8a12043590a923c617ea7481c3f0145e30aeefcad42` (re-hashed at start: match).
- Base for every measurement: `95cf6f864b4e70980ca191daa064c0118e223c13` (the unit worktree HEAD, `git status --short` EMPTY before and after). B4 code read at `83daa8cb` through `git show` (shared object store; sc-s80-b4 not touched).
- Probes: one detached scratch worktree of 95cf6f86 under the reviewer notes folder (`<scratchpad>/D03_review/wt`), removed with `git worktree remove --force` and verified absent from `git worktree list`. Probe source and output kept as `<scratchpad>/D03_review/test_zz_d03_review_probe.py.txt` and `probe_out.json`. The "ON" readings of source_router consumers use the spec's own oracle (section 2.4 C2: ON over R == OFF over R minus the denied rows), applied by monkeypatching `source_router.SOURCE_REGISTRY`.
- No personal values; no secret read; no flag set outside one runner call.

## VERDICT: APPROVE_WITH_CHANGES

The spec is measured with care (1.1, 1.4, 1.5, 1.11 re-measured and confirmed below), but five defects must be ruled and folded into the spec BEFORE the RED phase: a banned-source display surface the unit claims to close but does not touch (B1), a fail-closed to fail-open inversion created by the "as if absent" semantics (B2, measured), two not-gated C6 mutants no PIN can kill plus an unsatisfiable RED row (B3), an unsound memo key (B4, measured 2000/2000 id reuse), and an incomplete comm set (B5).

## 1. Refuted claims (measured truth, file:line at 95cf6f86 unless marked B4)

- RC1. Spec 1.3 "a fragrantica host is not eligible in either state" and L4 "measured unreachable". REFUTED for a BH-locale path. `_organic_host_bh_gcc_retail` (structured_comparison_service.py:2882-2919) rejects on `registry_tier(host) == "global"` (:2906-2909), then falls to the off-registry rungs; the path rung (:2916-2918) trusts `_bh_locale_host_registry_known`, whose memo `_bh_locale_known_retail_domains` (:2845-2872) is built ONCE from the UNFILTERED `SOURCE_REGISTRY` (it contains fragrantica.com: measured True). Probe, real registry: base `(False, False)` and `_harvest_organic_pdp_candidates(...) == []`; ON-oracle `(True, False)` and the harvest returns `[("https://www.fragrantica.com/bh-en/perfume/Tom-Ford/Oud-Wood-1826.html", "fragrantica.com", "organic_harvest", 0.5)]`. The harvest is default ON (`ENABLE_ORGANIC_PDP_HARVEST`, :2749-2753) and its rows feed `_build_escalation_scrapers`, which fetches. The same downgrade reaches price_service.py:10158 (`global_tier` refusal skipped; a `/bh-en/` first segment then returns genuine True at :10170-10175). Google will not index such a Fragrantica path, but the design turns a fail-closed refusal into an off-registry trust decision, against "never fetched by any path".
- RC2. Spec 2.4 C5 "Every tier then skips a denied image". REFUTED for the live Tier 1.5 piggyback: it is not in image_service. structured_comparison_service.py:6122-6127 sets `result["image_url"] = page_img.strip()` after its own inline http(s) test; the only `get_product_image_url` caller passes `page_scrape_image=None` (:5978-5981; R0-3 already records the image_service Tier 1.5 kwarg as dead on the live path). Today the piggyback is reachable only through Zyte-seeded cached prices (`zyte_service.py:499,661` carry `image_url`; `scripts/seed_zyte_luxury.py:141-168` caches that dict at the live size-aware key; the session-80 CLAUDE.md image row says the override never fires, so its live rate is unmeasured either way); after B7 every JSON-LD price feeds it (R0-3 write site), so the gap must be closed in D03 or assigned to B7 explicitly.
- RC3. Spec section 0 / 2.4 C3 / 2.5 "a denied rating source is never selected" / "becomes the existing null rating". REFUTED at the user surface. `review_service.build_retailer_quotes_from_reviews` (review_service.py:269-330), called LIVE at structured_comparison_service.py:6462-6469, ships `{retailer, text, rating}` from cited organic results. Measured on the committed real capture `tests/fixtures/serper_oudwood_organic.json` (Fragrantica at index 3, rating 4.3 / ratingCount 17104) with a highlight citing `[snippet_4]`: `[{"retailer": "fragrantica.com", "rating": 4.3, "text": "Tom Ford Oud Wood is a sensual, unisex fragrance blending ..."}, ...]`. That lands in `reviews.products[i].retailer_quotes` (response_builder.py:2029) and counts as review evidence in `result_gate._reviews_present` (result_gate.py:430-432). It is post-LLM: filtering it moves no prompt digest, so the L1 / OQ-3 justification ("prompt digests move") does not apply to it, nor to the `Per <domain>:` attribution written by `clean_review_citations` (review_service.py:158-172).
- RC4. Spec 1.5 counts. `COUNTERFEIT_KEYWORDS` has 21 entries (not 23); `LUXURY_BRAND_KEYWORDS` has 29 (not 30). Measured `len()` at base (price_service.py:528-543).
- RC5. Spec 2.4 C2 "the fourteen sites of 1.3". The list names twelve, and source_router.py has exactly twelve registry loop sites: :578, :698, :722, :740, :755, :783, :800, :836, :917, :946, :969, :1171.
- RC6. Spec 1.5 anchor `price_service.py:10352 (extract_price_from_shopping)`: the call is at :10353.
- RC7. Spec 2.3 / L5 "the memo key (id, len) ... detects a replaced or resized SOURCE_REGISTRY". REFUTED for replacement: CPython recycles the id of a freed list. Measured: a 12-element list freed and a new 12-element list allocated got the SAME id in 2000 of 2000 trials. The memo stores the filtered list, not the registry, so a freed registry's id is reusable and a same-length replacement is served the stale filtered list. Five existing files patch `source_router.SOURCE_REGISTRY` (test_bh_gcc_registry_loader x3, test_shopify_gcc_orphan_wiring x7, test_m13_registry_longest_host, test_ourshopee_demotion, test_wave_d_cv_polish), so gate 6 (comm set with the flag ON) can report stale-memo artefacts as ON reds, and the unit's own tests must reset the seam by hand.
- RC8. RED row R5b lists "Copycat scent" as a false positive to clear. A "copycat" fragrance is a clone by definition (counterfeit class); base True is the correct verdict and V2 False is a new false negative.
- RC9. Spec 2.4 C4 / section 0 "every whole-word hit base catches still drops". REFUTED for keywords glued to digits: measured `1:1replica Creed Aventus 100ml` base True -> V2 False; `Creed Aventus Replica1` base True -> V2 False (the `(?<![a-z0-9])...(?![a-z0-9])` idiom of `_contains_token` treats digits as word characters). A letters-only boundary `(?<![a-z])...(?![a-z])` keeps both True, still returns False for infused / unused / copyright / the Margiela titles, and agrees with the spec rule on all 133 string literals of tests/test_counterfeit_filter.py (measured: 0 differences).
- RC10. Spec 2.5 and the CLAUDE.md row item (5) "the same refusal" for a redirect hop. B4's `_v2_refusal` takes `error` from `_v2_code_message(code)` (B4 url_extraction_service.py:364-371, :940-945): a hop refusal coded NOT_PRODUCT_PAGE ships `NOT_PRODUCT_PAGE_MESSAGE`, not `DENIED_SOURCE_MESSAGE` (the spec's own OQ-4 calls that copy untrue for Fragrantica). The two denied paths would carry different copy.
- RC11. Spec section 0 / L11 / P10 (`d03=on, v2=off` reaches reserve AND compare). PLAN_S81 unit D03 routes the deny through "URL mode" (not V2 only), and owner round 3 extended fail-closed to the live path. With D03 ON and V2 OFF (production until V2's own window), base `extract_from_url` (url_extraction_service.py:466-483) -> `fetch_page` (:90) fetches a pasted www.fragrantica.com link; P10 pins that fetch as intended behaviour.
- RC12. Spec 7 gate 5 "299 files" as the complete comm set. REFUTED: missing `tests/test_w4_13_flag_off_ledger.py` (it drives five `/api/v1/url/compare` scenarios through the real url_routes via `tests/fixtures/_gen_w4_13_flag_off_ledger.py:17`, which the `tests/*.py` grep cannot see; B4's own file reads that fixture at test_s80_url_mode_v2.py:1375, :1398), and 11 adapter test files that drive the edited `is_counterfeit_listing` body through its by-name bindings (the P8 row itself pins those bindings): test_algolia_catalog_stores, test_bh_gcc_adapter_gatefixes, test_kpi_session_fixes, test_magento_brand_wiring, test_magento_graphql_adapter, test_occ_adapter, test_regression_gate_diff, test_salla_api_adapter, test_unbxd_service, test_woocommerce_adapter, test_zyte_service.

Confirmed as written (re-measured): search_descriptor_service.py:111 / :401-405 / :471; the only deny literal in app/ (grep over app/ and scripts/); source_router.py:347 (literal index 38, 44 literals, 44 rows catalog OFF); the base global query `Dior Sauvage site:amazon.com OR site:sephora.com OR site:walmart.com OR site:fragrantica.com`, `score_source` 1.0, tier `global`, apex `fragrantica.com`; rating_service.py:33-48 (RATING_TIER_2 21 entries with fragrantica at :37, LUXURY_FASHION_RETAILERS 7 at :46, zero readers); get_rating_tier :51-64; the gold false positives (frag-018 `replica`; hair-005/010/012, supp-021, fash-015 `lv`); the Calvin Klein designer floor (:1532-1571); T7b scans only `https?://` literals (test_legal_docs_u8.py:761, :822-828); `_registry_row_for_host(registry=...)` has no app caller; image_service has one importer (structured_comparison_service.py:1543); the four direct registry readers outside source_router (cache_service.py:526-529, magento_graphql_service.py:294-295, price_service.py:14745-14749, structured_comparison_service.py:2851-2854); no data/*.json carries a banned host; no test scans app/ for a flag inventory; the base pins of 1.10 plus three more files pass (357 passed).

## 2. Blocking issues (resolve in the spec before RED)

- B1 (RC3, legal C2.1). Route the two post-LLM display surfaces under the flag in `review_service` (pure functions, no prompt digest moves): `build_retailer_quotes_from_reviews` skips a cited result whose `_extract_domain(link)` is denied; `clean_review_citations`' attribution `_attr` (:172) returns "" for a denied domain. Add RED rows (the Oud Wood fixture: no quote and no `Per fragrantica.com:` ON), PIN rows (OFF base literals), mutants, and add review_service.py to the change list; add the review_service importers missing from the comm set (10 files, e.g. test_retailer_quotes_from_reviews.py, test_review_paraphrase.py); list the ON-only reds (test_retailer_quotes_from_reviews.py:74, test_fragrance_content_quality.py:516-527, test_review_paraphrase.py:42-50, :259). Alternative: an explicit owner / legal ruling that keeps them as a named limit; the spec must not claim "never selected" either way.
- B2 (RC1). "As if absent" must not downgrade a refusal. Add ONE never-fetched chokepoint under the flag: `price_service.validate_scrape_url` (:990-1007, already in the change list) returns False for `is_denied_url(url)` (flag read first). Every escalation candidate passes it at `_build_escalation_scrapers` (structured_comparison_service.py:2448-2450), and so do the harvest (:2970), the BH tier (:2547) and the official tier (:2589). Add RED (ON: the `/bh-en/` harvest above returns []; `validate_scrape_url(<denied>)` False), PIN (OFF True) and a mutant; correct 1.3 and L4 (the shopping relabel at :10158 then also needs a word: denied hosts never carry a genuine label ON, or state it).
- B3 (session-79 vacuous-PIN class). P10 patches `compare_from_urls`, so no PIN ever runs `_fetch_page_v2` or `normalize_image_url`: an ungated hop deny and an ungated image skip survive every row. Add P12 (D03 OFF + V2 ON: a MockTransport 301 to www.fragrantica.com is followed, the transport sees 2 requests, outcome ok) and P13 (D03 OFF + V2 ON: `normalize_image_url([fimgs, cdn], base)` returns the fimgs url), with mutants M37 / M38. R8c is unsatisfiable as written: `_fetch_page_v2` re-validates the pasted url and every hop through `app.utils.url_validator` (B4 :465, :476), which the netguard blocks on DNS, so the outcome is `blocked` with 0 requests; R8c must use B4's own seams (`ues.httpx.AsyncClient` factory + `app.utils.url_validator.validate_external_url`, test_s80_url_mode_v2.py:338-360). Section 2.8 must list them.
- B4 (RC7). Key the memo on the registry OBJECT and keep a strong reference (`memo = (reg, filtered)`, hit when `memo[0] is reg`), so a recycled id can never hit; or reset `_ROUTABLE_MEMO` in tests/conftest.py autouse (the serper memo precedent). Add a row that frees one registry, installs a same-length different one and asserts a fresh filter, plus a mutant (id-only key).
- B5 (RC12). Add `tests/test_w4_13_flag_off_ledger.py` (pin collision on the URL route) and the 11 adapter test files to the comm set and to the ON measurement; with B1, the review_service importers too.

## 3. Corrections (fold into the spec; no re-spec needed)

1. RC9: build the counterfeit V2 regexes with letters-only lookarounds `(?<![a-z])` / `(?![a-z])`; add RED / PIN cases `1:1replica Creed Aventus 100ml` and `Creed Aventus Replica1` stay True ON; mutant "alnum boundary".
2. RC8: drop `Copycat scent` from R5b; keep it counterfeit ON through a V2-only extra token tuple (e.g. `_CF_V2_EXTRA_TOKENS = ("copycat",)`, `COUNTERFEIT_KEYWORDS` unchanged); add it to P6.
3. RC4-RC6: fix the counts (21, 29), "twelve sites", and :10353.
4. RC2: either route the piggyback at structured_comparison_service.py:6122-6127 through `image_service._is_valid_image_url` (one call, adds scs to the change list, lane A) or record it as a stated limit AND make B7's piggyback write site (price_service JSON-LD branch, R0-3 :14000-14007) apply `is_denied_url`; fix the CLAUDE.md row item (4) wording either way.
5. RC10: give the hop refusal `DENIED_SOURCE_MESSAGE` (map reason `denied_source` in `_v2_code_message` or pass the copy into `_v2_refusal`) and assert `error` in R8c; or state that the hop carries `NOT_PRODUCT_PAGE_MESSAGE` (OQ-4).
6. Hop order: run `is_denied_url(nxt)` BEFORE the hop SSRF re-validation (pure, no DNS lookup of the denied host, a deterministic `denied_source` reason even when the hop also fails SSRF).
7. RC11: with V2 OFF, deny in base `extract_from_url` BEFORE `fetch_page`, returning the existing `{"success": False, "error": "Failed to fetch URL", "url": url}` (the existing `<2 products` 400 + one refund, the W4-9 verbatim literal; build 3 renders it). Never edit `fetch_page` (B4 pin `test_fetch_page_untouched_pin`, BASE_FETCH_PAGE_SHA). Redirect hops stay uncovered on the base path (state it). If not taken: a precondition "flip only with or after ENABLE_URL_MODE_V2" and P10[d03=on,v2=off] relabelled as a pinned limit.
8. Section 1.5 / the CLAUDE.md row "Effect ON" are incomplete: the guards also move `strict_title_match` (price_service.py:3842-3865, used by 11 modules incl. rating_service), the response chokepoint `is_price_showable` (:1853, via the designer floor) and pair-size fairness `effective_pair_size_ml` / `target_pair_size_ml` / `reselect_to_target_size` (:1972-2105, via `_is_designer_fragrance_name`). State them; the canary reads the per-pair size basis on Calvin Klein / Elvive pairs.
9. Rollback / canary wording: values computed ON are cached past a rollback (L1 price 24 h, genuine 7 d; Tier-3 estimate 12 h), and a 30-day `nogenuine:` sentinel planted under OFF still suppresses Tier 1.5 on previously compared keys after the flip. "Per call, immediate" holds for new computations only; canary on never-seen pairs or `nocache=true`.
10. OQ-2: also deny by registrable LABEL (`fragrantica`, `parfumo`, `basenotes`, `fimgs` followed by any suffix), so an unlisted edition (`fragrantica.cn`, `parfumo.it`) is denied without a list edit; keep the 26-host tuple as the pinned documented list; R1e adds `fragrantica.cn` True and `notfragrantica.cn` False.
11. R1i: include `fragrantica.com` in the scanned set with the documented exemption of the `_LITERAL_ROWS` Source call (source_router.py:347), so a second fragrantica tuple is caught.
12. R4f: add an item with a neutral source and a denied link (M21 kills only the `extract_rating_from_shopping` half today).
13. Mutation table: add the luxury-ungated mutant (killed by P5), M37 / M38 (B3), the id-key memo mutant (B4), the alnum-boundary mutant (correction 1) and, with B1 / B2, their mutants.
14. RED mechanics: R1b / R1c must assert the file exists before reading it (a missing file raises FileNotFoundError, not AssertionError); R8c / R8d must assert the B4 attributes before `monkeypatch.setattr` (the default `raising=True` raises AttributeError at base).
15. Add a copy-policy fence row for `DENIED_SOURCE_MESSAGE` (scary_vocab_en of SmartCompareApp/src/i18n/.copy-policy.json; precedent tests/test_text_error_envelope_no_raw_exception.py:570-580). Measured: the proposed sentence has 0 hits.
16. Section 4.2: list tests/test_retro_w2_1.py and tests/test_w4_13_flag_off_ledger.py explicitly. Section 7: state that `scripts/verify_flag_byte_identity.py` is blind to this unit (extract_price_from_html :13791-14146 reaches none of the edited bodies), since PLAN_S81 Verification asks for it where the price path is touched.
17. State the ON log change: a Fragrantica Shopping link's W4-1 relabel reason moves from `global_tier` (:10158) to `no_bh_evidence` (:10198).
18. L9: `LVs Neverfull` is luxury at base and not ON (measured).

## 4. Contract risks

- URL: `reason: "denied_source"` is an additive value on B4's 400 (V2 ON only), code NOT_PRODUCT_PAGE, which build 3 renders as its generic copy (contract_freeze finding 3); no key added, renamed or retyped; the copy text is not displayed by build 3.
- Billing (R-A3): the pre-gate refusal is $0 before the reserve; a hop refusal is one reserve + one refund through B4's per-url exit (no lifetime bump, no history row); correction 7's base-path deny uses the existing `<2 products` exit (one refund). No abstain is added on text or camera; no 503, so no FEATURE_DISABLED mapping; the camera failure envelope is untouched.
- A rating removed ON goes through `derive_rating_from_scores` (response_builder.py:1591-1597, `rating_derived` True), nulled in the overview projections (:1931, :2002): the existing unrated-product shape, not a new one.
- `retailer_quotes` keeps its list type under B1 (fewer or no items).
- B4 dependency: R8a-R8d freeze B4 names at 83daa8cb while B4 fix round 3 is in flight (session-81 ledger ~16:10); a rename forces a gate ruling on a frozen file (spec L12). The D03b carve-out (OQ-1) removes the coupling.
- ON blast radius beyond the stated consumers: correction 8 (shopping matcher, showable chokepoint, pair-size fairness).

## 5. Pin collisions (missing from spec section 4)

- tests/test_w4_13_flag_off_ledger.py + tests/fixtures/w4_13_flag_off_ledger.json (five url scenarios through the real route; OFF must stay record-identical; not in the comm set).
- tests/test_s80_url_mode_v2.py::test_fetch_page_untouched_pin (BASE_FETCH_PAGE_SHA over `fetch_page`): any URL deny stays out of `fetch_page`.
- ON-only reds to list: tests/test_rating_tiers.py:71-72 (listed); with B1: test_retailer_quotes_from_reviews.py:74, test_fragrance_content_quality.py:516-527, test_review_paraphrase.py:42-50 and :259.
- Copy-policy fence for the new message constant (correction 15).
- Checked clean: T23 OpenAPI (no route parameter), FY25 nine digests (listed), W4-11 prompt digests (no prompt change), test_retro_w2_1 URL pins (in the comm set), T7b (bare hosts only).

## 6. Session-79 defect classes (result per class)

- Vacuous PIN rows: FOUND (B3: the hop deny and the image skip have no killing PIN). P10 is vacuous at 95cf6f86 by construction and becomes meaningful only on the B4 base.
- Mutants no RED row can kill: FOUND (M37 / M38 as above; the id-key memo).
- Comm-set files missing: FOUND (B5).
- Flag-OFF byte identity not pinned: the C6 OFF bodies of `_fetch_page_v2` / `normalize_image_url` (B3); the rest is pinned behaviourally.
- Response key removed / renamed / retyped: none.
- Refusal reaching build 3 through an unrenderable shape: none (generic copy for NOT_PRODUCT_PAGE; correction 7 uses an existing exit).
- Billing (R-A3): clean (section 4).
- Pin collisions: FOUND (section 5).
- Camera failure envelope: no interaction.
- Cache keys without a category / language axis: none added; the flip is masked by existing caches (correction 9).
- Error-handler code mapping: no codeless 503.
- A stated limit that is a defect: L1 (B1, the display halves are cheap and post-LLM), L4 (B2), L5 (B4).

## 7. Questions for the orchestrator

1. B1: route `retailer_quotes` and the `Per <domain>:` attribution under the flag now, or rule them a named limit with the owner's legal call?
2. B2: accept `price_service.validate_scrape_url` as the single never-fetched chokepoint under the flag (keeping "as if absent" for the selectors), or require explicit refusal semantics at the three `registry_tier == "global"` sites?
3. OQ-1: carve C6 into a D03b that follows B4 (recommended: fix round 3 in flight and a frozen RED file), or keep D03 waiting on the B4 merge?
4. Correction 7: deny the base (V2 OFF) URL path in `extract_from_url`, or make "flip with or after ENABLE_URL_MODE_V2" a precondition?
5. Corrections 1-2: letters-only boundaries, and "copycat" stays counterfeit?
6. Correction 4: route the scs:6122 piggyback through image_service in D03 (touches lane A), or assign the deny to B7's write site?
7. Correction 10: add the label rule beside the 26-host tuple?
8. Correction 5: the hop refusal copy, DENIED_SOURCE_MESSAGE or NOT_PRODUCT_PAGE_MESSAGE?
9. The brief binds "PLAN_S81 sections 0 and 1"; PLAN_S81 has no numbered sections. The spec read PLAN_S80 sections 0 and 1 plus PLAN_S81 "Standing constraints"; confirm that reading.

## 8. Runs

```
d03rev-probe1 (scratch worktree of 95cf6f86, tests/test_zz_d03_review_probe.py): 5 passed, 1 warning in 10.00s
[hermeticity] sentinel checked 5 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=d03rev-probe1 start=2026-10-22 16:45:56 end=2026-10-22 16:46:11 elapsed=15s bound=600s status=OK rc=0

d03rev-base-guards (scratch worktree of 95cf6f86: the 12 files of spec 1.10 + test_retailer_quotes_from_reviews.py + test_organic_pdp_harvest.py + test_w4_13_flag_off_ledger.py): 357 passed, 2 deselected, 11 warnings in 10.58s
[hermeticity] sentinel checked 357 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=d03rev-base-guards start=2026-10-22 16:56:50 end=2026-10-22 16:57:02 elapsed=12s bound=600s status=OK rc=0
```

Not done in this review: no GREEN prototype of the deny consumers; the comm set was diffed against reference greps, not run; the ON readings of source_router consumers use the spec's own "as if absent" oracle (registry monkeypatched), not a built `_routable_registry`; the B4 names were read at 83daa8cb, not at the fix-round-3 bytes.
