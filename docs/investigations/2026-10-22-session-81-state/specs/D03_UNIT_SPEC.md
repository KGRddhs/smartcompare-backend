# D03 UNIT SPEC: DENY-AND-GUARDS (one per-call DENY_HOSTS module, unbiased counterfeit and luxury guards)

- Unit: D03 DENY-AND-GUARDS (PLAN_S81 milestone M1, lane B, build-order slot 3).
- Flag: `ENABLE_DATA_GUARDS_V2` (new name, default OFF, read PER CALL with the house idiom; flag OFF byte-identical and pinned). No knobs.
- Worktree: `C:/Users/SynAckITPC/Documents/AI/sc-s81-d03`, detached at base `95cf6f864b4e70980ca191daa064c0118e223c13` (origin/main = PR #365 merge, B1 + B3 in).
- Branch (to be cut by the orchestrator): `feature/s80-d03-deny-and-guards` (the template's `feature/s80-<slug>`; see OQ-9 for an `s81` prefix).
- `git status --short`: EMPTY at 15:55 AST before the first probe and EMPTY after every probe (re-checked 16:07, 16:12, 16:18; probes ran with `PYTHONDONTWRITEBYTECODE=1` or through `pyt.py` with `-p no:cacheprovider`). The only file this spec writes in the worktree is this one, under the gitignored `.qa-s80/` (`.gitignore:72: .qa-*/`).
- Measurement location: `C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fd8b3d1b-a491-48e3-953f-ca3a804fd9ca/scratchpad/D03/` (notes.md, guard_probe.py + guard_probe.json, base_guards.log, base_image_url.log, comm_set.txt and its component lists, b4_url_extraction_service.py = `git show feature/s80-b4-url-mode-v2:app/services/url_extraction_service.py`).
- Evidence pointers: PLAN_S81.md (unit text "D03 DENY-AND-GUARDS" under M1; VERIFY corrections; F1 ruling in "Design panel result"); PLAN_S80.md sections 0 and 1 (R-A1, R-A3, R-A7, R-A13, R-A15); RULINGS_R0.md (R0-3 images, R0-6 clear-lists); `runs/verify/refute_C2_Legal_ToS.json` (C2.1), `refute_C2_Correctness.json` (C2.3), `refute_C6_correctness.json` + `refute_C6_legal_ToS.json` (C6.6), `runs/research/R15.json` (guard defects, lines 124-134, 184), `runs/research/A3.json:131,172`, `runs/panel/judge.json:39,91` and `plan_Data-ownership-first_no_compa.json` unit D03; the session-80 `runs/research/contract_freeze.json` and `eval_regression.json`; the B4 branch `feature/s80-b4-url-mode-v2` at `83daa8cb` (fix round 3 pending, RULINGS_FIX3_B4).
- Sister units and contracts:
  - S81-01 B4 URL-MODE-V2 (`ENABLE_URL_MODE_V2`, NOT merged at base): owns `url_routes._url_pre_gate`, `_raise_url_refusal`, the `NOT_PRODUCT_PAGE` envelope with additive `field` / `reason`, `url_extraction_service._fetch_page_v2` / `normalize_image_url` / `_extract_from_url_v2`, the error-handler passthrough `_URL_V2_PASSTHROUGH_CODES`. D03 consumer C6 is written against those names at `83daa8cb` and is implemented only on a base that contains the B4 merge (section 3, step 0; OQ-1).
  - B7 IMAGE-PIPELINE-V2 (`ENABLE_IMAGE_PIPELINE_V2`, not built): R0-3 restricts `image_service._is_valid_image_url` to https under its own flag; D03 adds a deny check to the same function. The two predicates compose by AND, each behind its own flag (section 2.4 C5).
  - S81-14 KB-SCHEMA / S81-15 REGISTRY-ROBOTS-DENY / KB ingest / S81-21 WEB-SEARCH (`blocked_domains`): consume `deny_hosts.DENY_HOSTS` and the KB-writer guard this unit exports (no table here).
  - The later R-A1 pure-defect PR (after approval, F1 ruling): deletes the fragrantica literal row (`source_router.py:347`) and the `fragrantica` entries of `RATING_TIER_2` / `LUXURY_FASHION_RETAILERS` unflagged and re-pins `tests/test_rating_tiers.py:71-72`. Not this unit.
- Personal-data rule: the repo is public. No real name, email, phone, Apple id, device id, address or account id in any file, test, fixture or log line; synthetic values only. Host names in this unit are public site names (fragrantica.com, parfumo.de, fimgs.net, retailer apexes) or synthetic `.test` hosts. No secret, key or credential-shaped literal anywhere; this unit reads no credential.

## 0. What the unit does

Under `ENABLE_DATA_GUARDS_V2` (default OFF):

1. Adds `app/services/deny_hosts.py`, a stdlib-only leaf holding the ONE banned-host list (`DENY_HOSTS`: Fragrantica and its language editions, Parfumo .com/.de, Basenotes .com/.net, the Fragrantica image CDN fimgs.net), the flag reader, `is_denied_host` / `is_denied_url` / `is_denied_source` with suffix matching on registrable domains and their subdomains, the descriptor's legacy two-host tuple (moved, value unchanged), and a flag-free KB-writer guard (`kb_source_allowed`, `assert_kb_source_allowed`, `DeniedSourceError`) for later units.
2. Routes the consumers through it, per call, ON only:
   - `source_router`: every registry consumer skips a denied row AT USE (lookups, selectors, discovery queries, tier, apex, usage, weight, render-only, descriptor lookups return exactly what they would return if the row were absent) while `SOURCE_REGISTRY` and `_LITERAL_ROWS` are built and kept byte-identically (the `:347` row is never deleted).
   - `rating_service`: a denied rating source is never selected (tier lookup, the tiered fallback, the consensus rule, the per-retailer rating list); `RATING_TIER_2` and `LUXURY_FASHION_RETAILERS` stay byte-identical constants.
   - `search_descriptor_service`: its private two-host list moves into `deny_hosts` (same value, same object identity re-exported as `DENY_HOSTS`); `_deny` uses the full list ON.
   - `image_service`: an image URL on a denied host is not a valid image URL (every tier skips it).
   - URL mode (only when `ENABLE_URL_MODE_V2` is also ON, else untouched): a pasted link on a denied host is refused by the B4 pre-gate with the existing `NOT_PRODUCT_PAGE` envelope and the new `reason` value `denied_source` before any credit is reserved and before any fetch; a redirect hop onto a denied host is never followed (same refusal); a denied-host image is never taken by `normalize_image_url`.
3. Fixes two biased guards in `price_service`, ON only:
   - `is_counterfeit_listing`: whole-token matching (a keyword plus an optional plural `s`/`es`), the Maison Margiela Replica brand-line allowlist, so "infused", "focused", "unused", "copyright", "copycat" no longer match and the gold query frag-018 listing survives, while every whole-word hit base catches (including the plural forms base caught by substring) still drops.
   - `is_luxury_brand`: the token `lv` matches only as a whole token (`LV`, `L.V.`, `L.V`, `LV.`), never inside silver, velvet, calvin, elvive, salvatore, volvo; every other luxury keyword keeps today's substring rule.

It does NOT add a registry table, a KB table, a migration, a processor row, a client change or a route parameter; it does NOT delete the fragrantica literal row or edit the rating constants (that is the later R-A1 PR); it does NOT filter Serper organic results before the specs / reviews / image prompts (measured gap, OQ-3).

## 1. Base state (MEASURED at 95cf6f86 in this run)

### 1.1 The ban is enforced in one module only

| Site | What it is at base |
|---|---|
| `app/services/search_descriptor_service.py:111` | `DENY_HOSTS = ("fragrantica.com", "parfumo.com")`, the only deny list in `app/`. |
| `app/services/search_descriptor_service.py:401-405` | `_deny(host)`: lower, strip, one leading `www.` dropped, `h == d or h.endswith("." + d)`; flag-free. |
| `app/services/search_descriptor_service.py:471` | `probe_search_descriptor` raises `ValueError` ("house rule 7") before any fetch when `_deny(host)`. |
| `scripts/resolve_search_descriptors.py:65,154` | imports `DENY_HOSTS` from the descriptor module and skips matching catalog rows (off-clock). |
| `app/services/source_router.py:347` | `Source("fragrantica.com", "global", ("fragrances",), 1.0)`, a literal row (usage `price`, no mechanism). Registry index 38 in BOTH catalog states. |
| `app/services/rating_service.py:33-39` (fragrantica at :37) | `RATING_TIER_2` includes `"fragrantica"`. |
| `app/services/rating_service.py:45-48` (fragrantica at :46) | `LUXURY_FASHION_RETAILERS` includes `"fragrantica"`; ZERO readers in `app/` (grep: definition only). |
| `app/services/review_service.py:158-172` | `clean_review_citations` rewrites `[snippet_N]` to `Per <domain>:`; the committed fixture `tests/fixtures/comparison_baseline_d2_post_bucket_a__fragrances.json` ships `Per fragrantica.com: ...` highlights. Out of scope (OQ-3). |

Measured with the real module (`python -c`, `PYTHONDONTWRITEBYTECODE=1`, no `app.main` import; the chain source_router -> search_descriptor_service -> robots_eval is stdlib-only):

| Reading | catalog OFF (44 rows) | catalog ON (`ENABLE_BH_GCC_CATALOG_SOURCES=true`, 319 rows) |
|---|---|---|
| rows whose domain contains fragrantica / parfumo / basenotes / fimgs | `fragrantica.com` only | `fragrantica.com` only |
| `build_site_discovery_query("Dior Sauvage", "fragrances", tier="global", limit=8)` | `Dior Sauvage site:amazon.com OR site:sephora.com OR site:walmart.com OR site:fragrantica.com` | identical |
| `score_source("https://www.fragrantica.com/perfume/x-1.html", "fragrances")` | 1.0 | 1.0 |
| `registry_tier("www.fragrantica.com")` / `match_registry_apex("fr.fragrantica.com")` / `source_usage(...)` | `global` / `fragrantica.com` / `price` | identical |

So today every fragrance compare that reaches the Tier 1.5 "authorized" (global) discovery spends part of its Serper result window on `site:fragrantica.com` (`structured_comparison_service.py:7054` prefetch and `:7988` inline fallback, `limit=8`).

### 1.2 Corpus spellings of the banned hosts (deny list sizing)

`grep -rhoiE` over the held corpora `sc-scraper-proof/_proof` (one read-only pass, 16:05): `fimgs.net` 87,850 (+ `rwebsocket.fimgs.net` 38), `www.parfumo.com` 38,717, `media.parfumo.com` 1,980, `parfumo.com` 70, `www.parfumo.de` 141, `www.fragrantica.com` 8,303, `fragrantica.com` 351, and 20 Fragrantica language editions: `fragrantica.asia`, `.co.il`, `.com.br`, `.cz`, `.de`, `.es`, `.fr`, `.gr`, `.hu`, `.it`, `.jp`, `.kr`, `.mn`, `.nl`, `.pl`, `.ro`, `.ru`, `.se`, `.tr`, `.ua`. No Basenotes host in the corpora; the repo carries `basenotes.net` x3 (`tests/test_retailer_quotes_from_reviews.py:74`) and the docs checkout `basenotes.com` x3. No banned host in `data/bh_gcc_sources.json`.

### 1.3 Every SOURCE_REGISTRY consumer (the C2 surface)

In `app/services/source_router.py` (each iterates the module global `SOURCE_REGISTRY` at call time):
`_registry_row_for_host` :562-596 (reg at :578; behind it `match_registry_apex` :599, `registry_tier` :616, `search_descriptor_service.descriptor_for_host` :195-228, `price_service.py:10180`, `shopify_pdp_service.py:751`), `get_sources_for_category` :675 (loop :698; behind it `build_site_discovery_query` :1180-1199, `structured_comparison_service._bahrain_discovery_only_sources` ~:1623, `review_service.py:906,984` usage="review"), `get_shopify_sources_for_category` :711 (:722), `get_algolia_sources_for_category` :729 (:740), `get_jsonapi_sources_for_category` :747 (:755), `get_curl_pagescrape_sources_for_category` :762 (:783), `get_sitemap_sources_for_category` :792 (:800), `_direct_fetch_sources` :829 (:836; behind it woo / salla / occ / magento_gql / unbxd / rest_json / noon selectors :847-881), `get_gcc_shopify_pagescrape_sources_for_category` :884 (:917), `source_usage` :929 (:946), `score_source` :954 (:969), `is_render_only_domain` :1155 (:1171).

Outside source_router, direct `SOURCE_REGISTRY` readers (left untouched; each measured inert for a denied row): `cache_service._registry_domains` :521-534 (admin by_source probe list; one extra zero-count key), `magento_graphql_service.py:294-301` (exact-apex currency; the fragrantica row's currency is ""), `price_service._curl_timeout_for_url` :14740-14755 (bahrain tier only), `structured_comparison_service._bh_locale_known_retail_domains` :2845 (memoised once; used only behind `registry_tier` in `_organic_host_bh_gcc_retail` :2880-2910, where a fragrantica host is not eligible in either state: global tier at base, off-registry with no `.bh` / BH-locale path ON). Scripts `build_source_registry_data.py:347`, `verify_source_registry.py:38` are off-clock.

Hazard measured and accepted: "as if absent" turns `registry_tier(denied)` from `global` into `None`. The two genuine-label refusals keyed on `global` (`structured_comparison_service.py:2163` `_curl_scraper`, `price_service.py:10158,16950`) therefore no longer fire for a denied host; measured unreachable because every price / harvest admission gate requires `score_source >= 1.5`, a legacy whitelist entry or a BH marker, none of which a denied host has (score 0.5 ON). Stated limit L4.

### 1.4 Rating selection (the C3 surface)

`rating_service.py:51-64` `get_rating_tier(source)`: substring of RATING_TIER_1 -> 1, of RATING_TIER_2 -> 2, else `".com"` or `".ae"` in the name -> 2, else 3; so removing a name from RATING_TIER_2 alone still leaves `fragrantica.com` at tier 2. `:67-102` `collect_retailer_ratings` (per-retailer list from the shopping cache, dedup by source); `:105-244` `extract_rating_from_shopping` (gates, then tier buckets; tier 3 needs `review_count > 1000`; the Google consensus rule runs over all candidates when no tier 1/2 exists; tiered fallback sorts by review_count then match_score); `:247-307` `get_verified_rating` (reuses the cache, else one US shopping POST). Callers: `structured_comparison_service.py:1490-1495` (imports + `RATING_TIER_1/2` class attrs :3264-3265), `:3422-3423`, `:3559-3563`, `:6167-6210`, `:8839-8842`.

### 1.5 The guards (the C4 surface)

`price_service.py:528-534` `COUNTERFEIT_KEYWORDS` (23 entries: replica, fake, dupe, inspired by, inspired, knockoff, knock-off, imitation, copy, look alike, lookalike, designer inspired, unbranded, generic, homage, alternative, pre-owned, used, vintage, secondhand, second hand), `:537-543` `LUXURY_BRAND_KEYWORDS` (30 entries incl. `"lv"`), `:1014-1022` `is_counterfeit_listing` (`any(kw in _jsonld_str(title).lower())`), `:1228-1234` `_contains_token` (the lookaround word-boundary idiom to reuse), `:1290-1293` `is_luxury_brand` (`any(brand in name.lower())`).

Callers bind the FUNCTION by name at import, so the change must live in the function bodies: `is_counterfeit_listing` from `price_service.py:3865, 9735 (shopping_listing_matches), 10352 (extract_price_from_shopping), 15436 (_match_shopify_product)`, `algolia_service.py:633,712`, `magento_graphql_service.py:933`, `noon_service.py:226`, `occ_service.py:144`, `salla_service.py:138`, `shopify_pdp_service.py:1012`, `unbxd_service.py:133`, `woocommerce_service.py:170`, `zyte_service.py:372,572`, `structured_comparison_service.py:3354-3355` (`_is_counterfeit_listing`); `is_luxury_brand` from `price_service.py:1556 (is_implausible_low_fragrance_price), 2034 (_is_designer_fragrance_name), 10281 (extract_price_from_shopping: sort order :10506 and the flagship bonus :10423), 15420`, `shopify_pdp_service.py:1047`, `structured_comparison_service.py:3366-3367`. `get_official_domain` :9701-9711 also scans `LUXURY_BRAND_KEYWORDS` by substring, but `lv` maps to no `OFFICIAL_BRAND_DOMAINS` entry (no domain base contains `lv` and `lv` contains none), so it is inert there and untouched. `_adapter_brand_token_vocab` :6898-6915 folds `lv` as a whole token (correct; untouched).

Measured with `guard_probe.py` (AST-parsed keyword sets, no `app` import; base = the literal substring rule, V2 = the section 2.4 C4 rule) over the 400 product names of the 200-case gold set `data/validation_gold_truth.json`, the 1,176 `title` / `name` strings in `tests/fixtures/**/*.json`, the 28 + 19 literal rows of `tests/test_counterfeit_filter.py` and `tests/test_luxury_brands.py`, and an edge list:

- Gold set, counterfeit: 1 false positive at base, removed by V2: frag-018 "Maison Margiela Replica Jazz Club" (keyword `replica`).
- Gold set, luxury `lv`: 5 false positives at base, removed by V2: hair-005 "L'Oreal Elvive shampoo", hair-010, hair-012 (Elvive), supp-021 "Centrum Silver", fash-015 "Calvin Klein boxer briefs".
- Fixtures: 0 counterfeit deltas; 11 luxury deltas, all `lv` inside Silver (iPhone 17 Pro Silver x3, MacBook image names x5, "Silver"), Calvin ("Calvin Klein Eternity Eau de Parfum 100ml Spray") and "displayedElvisLabel".
- The two pin files: 0 rows change under V2 (every expected verdict holds ON), 0 rows differ from base.
- Edge list (base -> V2): "Lattafa Oud Infused Eau de Parfum 100ml" T -> F, "Rose Infused Body Oil" T -> F, "Focused Serum 30ml" T -> F, "Unused tester 100ml" T -> F, "Copyright free" T -> F, "Copycat scent" T -> F, "MAISON MARGIELA 'REPLICA' By the Fireplace EDT 100 ml" T -> F; kept T: "Used tester 100ml", "Creed Aventus replicas set", "Aventus dupes 3 pack", "Replica of Maison Margiela Jazz Club dupe", "Inspired by Maison Margiela Replica Jazz Club", "REPLICA Jazz Club EDT 100ml" (no brand word: limit L7), "Amouage Homage Attar 12ml" (limit L8). Luxury: "Creed Silver Mountain Water 100ml", "Velvet Matte Lipstick", "Salvatore Ferragamo Uomo", "Volvo key fob", "Kelvin thermometer", "LVMH annual report" T -> F; "L.V. Neverfull", "l.v monogram" F -> T; kept T: "LV Neverfull MM", "LV-Monogram scarf", "Louis Vuitton Ombre Nomade", "Tom Ford Velvet Orchid" (tom ford).
- Behaviour behind the luxury bit: `is_implausible_low_fragrance_price` (:1532-1571) treats a fragrance as designer when a FRAGRANCE_BRAND_KEYWORDS house OR `is_luxury_brand` matches; "calvin klein" is not a fragrance house, so at base "Calvin Klein Eternity Eau de Parfum 100ml" is designer only through `lv`, takes the 25 BHD / 100 ml floor and a genuine 18.0 BHD price is rejected as implausible (base True; V2 False). In `extract_price_from_shopping` the luxury bit changes the candidate sort (authority-first, :10506) and the flagship bonus; its `min_price = 50` (:10285) is applied only to high-value queries (:10357), so it does not drop cheap rows by itself.
- Out of scope, recorded: `omega` matches "Omega-3" and `tiffany` matches "Tiffany biscuits" (gold supp-006, groc-018) under both rules (OQ-6).

### 1.6 Images (the C5 surface)

`image_service.py:52-57` `_is_valid_image_url(value)`: a str whose stripped form starts with `http://` or `https://`. Called at :92, :103, :116 (`extract_image_from_search`: Knowledge Graph, organic, inline images; first valid wins), :205 (`extract_image_via_gpt` Tier 3 result), :242 (Tier 1.5 piggyback), :270 (Tier 1 Serper Images), :281 (Tier 3 in the cascade). Only importer: `structured_comparison_service.py:1543` (`get_product_image_url`). The Tier 3 prompt (`_TIER3_PROMPT` + `_wrap_search_context`) is digest-pinned (`tests/fixtures/w4_11_prompt_render_digests.json` key `image_tier3_user`); D03 does not touch it.

### 1.7 URL mode (the C6 surface; B4 code, not at base)

At base `NOT_PRODUCT_PAGE`, `ENABLE_URL_MODE_V2`, `_url_pre_gate` and `_fetch_page_v2` do not exist (`grep -rn` over `app/ tests/`: no hit). On `feature/s80-b4-url-mode-v2` at `83daa8cb`: `url_routes._url_pre_gate(url1, url2)` (flag-free, called only when the route read the flag ON, after the SSRF 400 and BEFORE `_reserve_comparison_credit`), `_raise_url_refusal(code, error, field, reason)` (400 + structured detail + ONE `[URL-V2] refused code= field= reason=` INFO), `url_extraction_service.url_mode_v2_enabled` (:112), `NOT_PRODUCT_PAGE_MESSAGE` (:96), `_host_only` (:119), `classify_url_path` (:196), `normalize_image_url` (:345: the first https candidate of `price_service._jsonld_image_urls`, joined against the final url), `_fetch_page_v2` (:443: SSRF check on the initial url and on every redirect hop, 5-hop bound, `follow_redirects=False`, transport seam `_TRANSPORT`), `_extract_from_url_v2` (:948: outcome != ok -> STORE_UNREADABLE; final-url page class -> NOT_PRODUCT_PAGE), `error_handler._URL_V2_PASSTHROUGH_CODES` (the passthrough of str `field` / `reason`). Build 3 renders the generic copy for `NOT_PRODUCT_PAGE` (contract_freeze: an unmapped code renders the generic "try with brand or model" copy); the client maps it in C3 later.

### 1.8 Flag-reader idiom and libraries

House idiom (B4 `url_mode_v2_enabled`, B3 `vision_identity_v2_enabled`): `os.getenv("ENABLE_X", "false").strip().lower() in ("true", "1", "yes", "on")`, read per call. Pinned venv `C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe`; the unit needs only the stdlib (`os`, `re`, `urllib.parse`, `typing`). No dependency is added.

### 1.9 Guards the new code must not trip

- `tests/test_legal_docs_u8.py` T7b (:755-830): every non-docstring string literal in `app/services/**/*.py` holding an `http(s)://<external host>` must map to a `processors.json` row. `deny_hosts.py` must therefore hold BARE host names only (no scheme in any non-docstring literal); host names without a scheme are not scanned (the descriptor's tuple passes today for that reason).
- `tests/test_model_config.py` (stray model literal scan over `app/`), `test_model_config_enforced.py`, `test_prompt_fence.py`, `w4_11_prompt_digest_recorder.py`: no prompt, model literal or dispatch site changes, so the new flag needs NO clear-list entry (unlike B3 / B4, which changed prompts and route parameters; R0-6). The U13 `CLEAN_ENV` needs none either: the URL consumer fires only with `ENABLE_URL_MODE_V2` ON, which that list already clears after B4.
- `tests/test_s71_u13_compare_auth_required.py` T23 OpenAPI fixture: no route parameter or body field is added (R0-6).
- Pre-commit hook + secret scanner: no credential-shaped literal.
- Line endings: backend files are CRLF in the working copy, LF in the index (`core.autocrlf=true`); edit with the Edit tool; a whole-file diff in `git diff --stat` is a defect. The new files are written LF, pure ASCII (bytes > 127 = 0).

### 1.10 Base pass state of the files the unit touches (bounded runner)

```
d03-base-guards: tests/test_counterfeit_filter.py tests/test_luxury_brands.py tests/test_rating_tiers.py tests/test_search_descriptor_d3.py tests/test_bh_gcc_registry_loader.py tests/test_registry_liveness_gate.py tests/test_source_router_discovery.py tests/test_source_router_bahrain_first.py tests/test_global_tier_never_genuine.py tests/test_m13_registry_longest_host.py tests/test_source_usage_field.py tests/test_decomposed_services.py
================ 302 passed, 2 deselected, 1 warning in 6.01s =================
[hermeticity] sentinel checked 302 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=d03-base-guards start=2026-10-22 16:11:42 end=2026-10-22 16:11:49 elapsed=7s bound=600s status=OK rc=0

d03-base-image-url: tests/test_image_service.py tests/test_image_service_edges.py tests/test_image_service_longtail.py tests/test_image_knowledge_graph_tier.py tests/test_comparison_response_image_url.py tests/test_url_extraction.py tests/test_url_quality.py tests/test_url_compare_category.py tests/test_paid_route_metering.py tests/test_legal_docs_u8.py tests/test_model_config.py
====================== 238 passed, 12 warnings in 11.77s ======================
[hermeticity] sentinel checked 238 test(s)
[netguard] blocked 5 attempt(s) from 3 node(s)
[netguard]   tests/test_comparison_response_image_url.py::TestOrchestratorWiring::test_organic_results_passed_to_image_service [egress] socket.getaddrinfo api.openai.com:443
[netguard]   tests/test_paid_route_metering.py::test_camera_success_consumes_once_and_never_refunds [sentinel] socket.create_connection neutralized.supabase.invalid:443
[netguard]   tests/test_paid_route_metering.py::test_url_compare_saves_history_with_input_type_url [sentinel] socket.create_connection neutralized.supabase.invalid:443
[pyt] tag=d03-base-image-url start=2026-10-22 16:11:58 end=2026-10-22 16:12:11 elapsed=13s bound=600s status=OK rc=0
```

The 2 deselected nodes are the runner's free-tier marker filter (`collected 304 items / 2 deselected`). The three netguard nodes are pre-existing baseline nodes (blocked, test passes). The full comm set (section 7) is NOT run by this spec; GREEN runs it at base and head.

### 1.11 Base values of the RED inputs and a satisfiability probe (measured)

A probe file `tests/test_zz_d03_probe.py` ran in a DETACHED scratch worktree of 95cf6f86 under the notes folder (created with `git worktree add --detach`, removed with `git worktree remove --force` afterwards; the unit worktree was never written), through the runner:

```
======================= 7 passed, 11 warnings in 3.42s ========================
[hermeticity] sentinel checked 7 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=d03-probe start=2026-10-22 16:27:25 end=2026-10-22 16:27:29 elapsed=4s bound=600s status=OK rc=0
```

Results (`probe.json` in the notes folder): `is_counterfeit_listing` True at base for the frag-018 listing, the infused title, "Used tester 100ml", "Creed Aventus replicas set"; `is_luxury_brand` True for "Centrum Silver", "Calvin Klein boxer briefs", "LV Neverfull MM", "Tom Ford Velvet Orchid", False for "L.V. Neverfull"; the Calvin Klein 18.0 BHD floor True and `_is_designer_fragrance_name` True at base. Satisfiability: with `price_service.is_counterfeit_listing` monkeypatched to the 2.4 C4 rule, `extract_price_from_shopping("Maison Margiela Replica Jazz Club", [the R5c listing], "BHD", category="fragrances")` returns amount 45.0, `local_bhd`, EDT, 100ml (base None), and `shopping_listing_matches` is True; with `is_luxury_brand` patched to the C4 rule the Calvin Klein floor and the designer bit are False. Rating at base: `get_rating_tier` 2 for Fragrantica / fragrantica.com / Fragrantica.ru, 3 for Parfumo / Parfumo.de; R4b returns 4.3 from "Fragrantica via Google Shopping"; R4c picks Fragrantica over Boots (17104 vs 20 reviews); R4d picks the `somestore.com` row whose link is on fimgs.net; R4e fires the Google consensus (4.0 / 5000); R4f lists both sources. Images at base: `_is_valid_image_url(<fimgs>)` True, `extract_image_from_search` returns the fimgs KG image, the cascade returns the fimgs piggyback, Tier 3 returns the fimgs pick. Descriptor at base: `_deny` False for basenotes.com and www.parfumo.de; `probe_search_descriptor("basenotes.com", rec)` made 3 fetches and returned without raising. URL route at base (recorders patched, flags unset): POST `/api/v1/url/compare` with a fragrantica url1 -> 200, reserve 1 call, compare 1 call (so R8a fails at base on its status assertion, and P10 is green at base).

## 2. Contract

### 2.1 Flag

`ENABLE_DATA_GUARDS_V2`, default OFF, ONE reader `deny_hosts.data_guards_v2_enabled()`:

```python
def data_guards_v2_enabled() -> bool:
    return os.getenv("ENABLE_DATA_GUARDS_V2", "false").strip().lower() in (
        "true", "1", "yes", "on",
    )
```

Read PER CALL at every consumer site, as the FIRST statement of the new branch, so the OFF path reads no other state (no deny lookup, no memo, no extra regex). Every module imports the reader from `deny_hosts` (one definition; the W2-1 / B4 precedent); `error_handler` is not touched (the B4 passthrough already carries any str `reason`). No knob. Production state: a new name, so unset in production by construction (Railway not read; R-A15; no ledger line names it).

### 2.2 New module `app/services/deny_hosts.py` (stdlib-only leaf)

Imports: `from __future__ import annotations`, `os`, `re`, `typing`, `urllib.parse.urlsplit`. No `app.*` import (so every service can import it at module top without a cycle). No `http(s)://` in any non-docstring literal (T7b). Public names (`__all__`):

| Name | Type / signature | Contract |
|---|---|---|
| `DENY_HOSTS` | `Tuple[str, ...]` | The 26 registrable domains, lower case, no scheme, no `www.`, no port: `fragrantica.com`, `fragrantica.asia`, `fragrantica.co.il`, `fragrantica.com.br`, `fragrantica.cz`, `fragrantica.de`, `fragrantica.es`, `fragrantica.fr`, `fragrantica.gr`, `fragrantica.hu`, `fragrantica.it`, `fragrantica.jp`, `fragrantica.kr`, `fragrantica.mn`, `fragrantica.nl`, `fragrantica.pl`, `fragrantica.ro`, `fragrantica.ru`, `fragrantica.se`, `fragrantica.tr`, `fragrantica.ua`, `parfumo.com`, `parfumo.de`, `basenotes.com`, `basenotes.net`, `fimgs.net` (section 1.2; the brief's four plus the measured editions, OQ-2). |
| `DENY_LABELS` | `FrozenSet[str]` | `{"fragrantica", "parfumo", "basenotes", "fimgs"}`: the first label of every entry, for source NAMES ("Fragrantica", "Parfumo.de"). |
| `LEGACY_DESCRIPTOR_DENY_HOSTS` | `Tuple[str, ...]` | `("fragrantica.com", "parfumo.com")`, the descriptor's base value moved here verbatim (flag-OFF identity of `search_descriptor_service.DENY_HOSTS`). |
| `data_guards_v2_enabled()` | `() -> bool` | 2.1. |
| `normalize_host(value)` | `(Any) -> str` | `""` for a non-str; else strip whitespace, lower, drop a trailing `.`, drop a `:port` suffix, drop ONE leading `www.`. Never raises. |
| `is_denied_host(host)` | `(Any) -> bool` | `h = normalize_host(host)`; `bool(h) and any(h == d or h.endswith("." + d) for d in DENY_HOSTS)`. Flag-FREE, pure, never raises. `notfragrantica.com` False; `fragrantica.com.evil.test` False; `fr.fragrantica.com` True. |
| `is_denied_url(url)` | `(Any) -> bool` | `urlsplit(url).hostname` (a protocol-relative `//host/x` included; a schemeless `host/x` read as `//host/x`; userinfo ignored by `hostname`), then `is_denied_host`; a non-str or a `ValueError` from `urlsplit` -> False. Flag-free, never raises. |
| `is_denied_source(value)` | `(Any) -> bool` | True when `is_denied_url(value)` or `is_denied_host(value)`, or the casefolded text carries a `DENY_LABELS` label as a whole token (`(?<![a-z0-9])label(?![a-z0-9])`: "Fragrantica" True, "fragrantica.ru" True, "Notfragrantica" False). Flag-free. |
| `DeniedSourceError` | `class DeniedSourceError(ValueError)` | Raised by the KB guard; message `"denied source"` (a constant: never the value). |
| `kb_source_allowed(value)` | `(Any) -> bool` | `not is_denied_source(value)`; flag-FREE: a KB writer (new code behind its own flag) calls it unconditionally; `None` / `""` -> True (presence of provenance is the writer's rule). |
| `assert_kb_source_allowed(value)` | `(Any) -> None` | Raises `DeniedSourceError` when `not kb_source_allowed(value)`. |

The module docstring states the house rule (Fragrantica, Parfumo, Basenotes banned; fimgs.net denied for images; robots fail-closed; never fetched by any path) and that `DENY_HOSTS` is the ONLY deny literal list in `app/` (pinned, R1i).

### 2.3 What "read per call by the consumers" means

The deny functions are pure and flag-free; the flag is read at each consumer site. The module needs no memo (26 suffix checks). `source_router` alone keeps a filtered-registry memo (2.4 C2), because a fan-out calls `score_source` once per candidate link and the filter costs about `len(SOURCE_REGISTRY) x 26` string checks per call (319 rows with the catalog ON).

### 2.4 Consumer contracts (ON; OFF = base bytes)

- **C1 `search_descriptor_service`.** `DENY_HOSTS = deny_hosts.LEGACY_DESCRIPTOR_DENY_HOSTS` (the same tuple OBJECT; value `("fragrantica.com", "parfumo.com")`; still importable by `scripts/resolve_search_descriptors.py`). `_deny(host)`: first statement `if data_guards_v2_enabled(): return deny_hosts.is_denied_host(host)`, then the base body unchanged. `probe_search_descriptor` unchanged (it calls `_deny`), so ON it refuses basenotes / fimgs / parfumo.de / every Fragrantica edition before any fetch with the same `ValueError`.
- **C2 `source_router`.** New private helper:

  ```python
  _ROUTABLE_MEMO = None  # (id(registry), len(registry), filtered list); test seam [None at import]

  def _routable_registry():
      if not data_guards_v2_enabled():
          return SOURCE_REGISTRY            # the same object, nothing else read
      reg = SOURCE_REGISTRY
      memo = _ROUTABLE_MEMO
      if memo is not None and memo[0] == id(reg) and memo[1] == len(reg):
          return memo[2]
      filtered = [s for s in reg if not is_denied_host(getattr(s, "domain", ""))]
      _ROUTABLE_MEMO = (id(reg), len(reg), filtered)   # via `global`
      return filtered
  ```

  Every `for ... in SOURCE_REGISTRY` / `enumerate(SOURCE_REGISTRY)` in the module (the fourteen sites of 1.3: :578 when `registry is None`, :698, :722, :740, :755, :783, :800, :836, :917, :946, :969, :1171) reads `_routable_registry()` ONCE per call instead. `_registry_row_for_host(..., registry=<list>)` keeps an explicit `registry` argument unfiltered (test-only path; no app caller passes it, measured). `SOURCE_REGISTRY`, `_LITERAL_ROWS`, `_load_catalog_rows`, `Source` and every row are unchanged; the filtered list is a NEW list (never an in-place edit). The "as if absent" oracle: for every consumer `f` and arguments `a`, `f(a)` with the flag ON over registry `R` equals `f(a)` with the flag OFF over `[s for s in R if not is_denied_host(s.domain)]`. Measured ON effect on the real registry: the global fragrance query loses `site:fragrantica.com` (3 domains remain, both catalog states), `score_source(<fragrantica url>)` 1.0 -> 0.5, `registry_tier` `global` -> `None`, `match_registry_apex("fr.fragrantica.com")` -> `fr.fragrantica.com`.
- **C3 `rating_service`.** New private `_rating_source_denied(source, link) -> bool` = `data_guards_v2_enabled() and (is_denied_source(source) or is_denied_url(link))` with the flag read FIRST. `get_rating_tier(source)`: ON and `is_denied_source(source)` -> 3, before the base loops (so neither `RATING_TIER_2` nor the `.com` / `.ae` rule can lift it). `extract_rating_from_shopping`: a candidate whose `source` or `link` is denied is skipped before any tiering (`continue` right after the rating parse), so it reaches neither a tier bucket nor the consensus rule. `collect_retailer_ratings`: a denied `source` (or `link`) item is skipped before the dedup. `get_verified_rating` inherits both (it calls `extract_rating_from_shopping`). `RATING_TIER_1`, `RATING_TIER_2`, `RATING_TIER_3`, `LUXURY_FASHION_RETAILERS` are byte-identical sets (never mutated; the scs class attributes keep pointing at them).
- **C4 `price_service` guards.**
  - `is_counterfeit_listing(title)`: `title_lower` exactly as base; then `if data_guards_v2_enabled(): return _counterfeit_v2(title_lower)`; else the base `any(...)`. `_counterfeit_v2`: verdict = `_CF_V2_RE.search(tl)` or (`_CF_V2_REPLICA_RE.search(tl)` and not `_contains_token(tl, "margiela")`), where `_CF_V2_RE` = `(?<![a-z0-9])(?:<every COUNTERFEIT_KEYWORDS entry except "replica", re.escape'd, longest first>)(?:s|es)?(?![a-z0-9])` and `_CF_V2_REPLICA_RE` = the same shape for `replica`; both compiled ONCE at import from the `COUNTERFEIT_KEYWORDS` literal (no env read at import). The brand-line allowlist is a module constant `COUNTERFEIT_BRAND_LINE_ALLOWLIST = {"replica": ("margiela",)}` (keyword -> tokens that neutralise it when present in the same title); `COUNTERFEIT_KEYWORDS` is unchanged.
  - `is_luxury_brand(product_name)`: `name_lower` as base; `if data_guards_v2_enabled(): return any(b in name_lower for b in LUXURY_BRAND_KEYWORDS if b not in _LUXURY_WHOLE_TOKEN_KEYWORDS) or bool(_LV_TOKEN_RE.search(name_lower))`; else base. `_LUXURY_WHOLE_TOKEN_KEYWORDS = frozenset({"lv"})`; `_LV_TOKEN_RE = re.compile(r"(?<![a-z0-9.])l\.?v\.?(?![a-z0-9.])")` (matches `lv`, `l.v.`, `l.v`, `lv.`, `lv-monogram`; not `lvmh`, `silver`, `x.lv`, `l.v.c`). `LUXURY_BRAND_KEYWORDS` is unchanged.
  - Every importer of the two functions inherits the change (the body changes, the binding does not); `get_official_domain`, `_adapter_brand_token_vocab`, `is_fragrance_query` and the keyword sets are untouched.
- **C5 `image_service`.** `_is_valid_image_url(value)`: base checks first (non-str False; the stripped http(s) prefix test); when that base verdict is True: `if data_guards_v2_enabled() and is_denied_url(stripped): return False`. The flag is read only after a base-True verdict and before the deny lookup (OFF reads nothing else). Every tier then skips a denied image (the 1.5b loops continue to the next candidate; Tier 1 and Tier 3 fall through). The Tier 3 prompt and its organic block are unchanged (no digest moves). Composition with B7: B7's https predicate (its own flag) and this deny predicate are independent ANDs on a base-True verdict.
- **C6 URL mode (only when `ENABLE_URL_MODE_V2` is also ON; on the B4 merge base).**
  - `url_routes._url_pre_gate(url1, url2)`: first statement `if data_guards_v2_enabled():` compute `d1 = is_denied_url(url1)`, `d2 = is_denied_url(url2)`; when either is True return `{"field": "both" if d1 and d2 else ("url1" if d1 else "url2"), "reason": "denied_source"}` BEFORE the path classes and the same_url rule; a denied url beside a homepage url -> `field` `both`, reason `denied_source` (B4's url1-reason-wins convention, denied first). The route then raises the existing `_raise_url_refusal("NOT_PRODUCT_PAGE", DENIED_SOURCE_MESSAGE, field, "denied_source")`: after the SSRF 400, before `_reserve_comparison_credit` (R-A7: $0, no row, no refund), status 400, body `{success: false, error: <copy>, code: "NOT_PRODUCT_PAGE", request_id, field, reason: "denied_source"}` through B4's error-handler passthrough. `DENIED_SOURCE_MESSAGE` (new constant in `url_extraction_service`, calm copy policy): "We do not read that site. Paste the product page from a store that sells it." (OQ-4: reuse `NOT_PRODUCT_PAGE_MESSAGE` instead).
  - `url_extraction_service._fetch_page_v2`: inside the hop loop, after the SSRF re-validation of `nxt` and before the next GET: `if data_guards_v2_enabled() and is_denied_url(nxt):` set `outcome="denied"`, `final_url=current`, return (no request to the denied host). `_extract_from_url_v2`: `if outcome == "denied": return _v2_refusal(url, "NOT_PRODUCT_PAGE", "denied_source", "denied", status)` before the generic `outcome != "ok"` branch. The per-url refusal then ships through B4's `_URL_V2_REFUSAL_CODES` path as the 400 with `field` / `reason` and B4's non-delivery exit (refund once, no lifetime bump, no history row; R-A3).
  - `url_extraction_service.normalize_image_url`: a candidate whose host `is_denied_host` is skipped (`continue`) when `data_guards_v2_enabled()`, so the next https candidate or the og fallback is taken.
  - With `ENABLE_URL_MODE_V2` OFF none of these functions runs (B4's route reads its flag once and only then calls them), so D03 ON + V2 OFF leaves the URL path byte-identical to base.
- **C7 KB-writer guard.** `kb_source_allowed` / `assert_kb_source_allowed` exported, no caller in this unit.

### 2.5 New keys and values

| Where | Key | Type | ON only |
|---|---|---|---|
| URL 400 body (B4 envelope) | `reason` value `"denied_source"` | str (additive enum value) | yes, and only with `ENABLE_URL_MODE_V2` ON |
| URL 400 body | `error` = `DENIED_SOURCE_MESSAGE` | str | same |
| logs | none new: B4's `[URL-V2] refused code=NOT_PRODUCT_PAGE field=<f> reason=denied_source` and `[URL-V2] outcome=denied reason=denied_source status=<int or None>` carry it (constants and ints only, never a url) | | |

No response key is added, renamed or retyped anywhere else (contract freeze, PLAN_S80 section 0 item 4). No stored row changes shape. Values that change ON stay inside contracts build 3 already renders (re-read `runs/research/contract_freeze.json` findings 3, 5b, 5f, 11): an image refused by the deny becomes `null` (finding 5f: `overview.products[i].image_url` is an absolute https raster url or null; the placeholder renders); a rating whose only source was denied becomes the existing null rating; the URL refusal is a 400 whose code build 3 does not map, so it renders the generic copy (finding 3), before any credit is reserved; a success payload still crowns as today (finding 5b; D03 adds no abstain).

### 2.6 Failure table

| Input / condition | Behaviour |
|---|---|
| Flag unset / `""` / `false` / `0` / `off` / `no` / garbage | base bytes on every path |
| Flag `TRUE`, ` on `, `1`, `Yes` | ON (strip + lower) |
| `is_denied_*` given None, int, bytes, a dict, `"http://[bad"` | False, never raises |
| A host with port / trailing dot / upper case / `www.` | normalised before matching |
| A `SOURCE_REGISTRY` row without `domain` | kept (getattr default `""`, not denied) |
| `SOURCE_REGISTRY` monkeypatched to a new list | memo key (id, len) misses, recomputed |
| A Shopping item with no `source` / no `link` | not denied on the missing field |
| A counterfeit title that is not a str (BLOCKER 5 shapes) | `_jsonld_str` as base, then V2 |
| A denied pasted url that the SSRF guard also blocks | the base SSRF 400 (it runs first) |
| URL deny with `ENABLE_URL_MODE_V2` OFF | untouched (base route) |
| Any exception inside a deny check | impossible by contract (pure functions, never raise); no try/except added |

Never a bare 503; no new error code; the refusal travels only through an envelope B4 adds and build 3 renders as its generic copy.

### 2.7 Flag-OFF identity: the main invariant

With the flag OFF (every falsy spelling, the FULL unit configuration present: `ENABLE_URL_MODE_V2=true`, `ENABLE_LONGEST_HOST_MATCH` both states, the synthetic registry carrying one denied row of every selector shape), every consumer returns exactly what base returns: the denied rows flow through every selector and lookup, the fragrantica rating is tier 2 and selected, the descriptor list is the two-host tuple, every counterfeit and luxury verdict equals base (the infused title is still counterfeit, Centrum Silver still luxury), a fimgs.net image is still valid, a fragrantica link still reaches `_reserve_comparison_credit`. The behavioural OFF outputs are themselves the call recorders: a "not gated" mutant (a consumer that filters without reading the flag) changes one of them and is killed (ruling B1).

### 2.8 Test seams (production value in brackets)

`source_router.SOURCE_REGISTRY` [the import-built list] and `source_router._ROUTABLE_MEMO` [None at import], monkeypatched per test; `deny_hosts.DENY_HOSTS` [the 26-host tuple] (read at call time by `is_denied_host`, so a test may patch it); `url_extraction_service._TRANSPORT` [None] (B4 seam, an `httpx.MockTransport` in tests); `image_service.try_consume_serper_image_credit` [the budget gate] patched False; `image_service.get_client` / `image_service._llm_breaker.guarded_llm_create` [the OpenAI chokepoint] patched with a fake; `url_routes._reserve_comparison_credit` / `url_routes.compare_from_urls` / `url_routes._validate_url_offloop_or_sync` [real] patched with recorders.

## 3. Change list (in the order GREEN applies it)

0. Preconditions: the worktree is rebased onto the B4 merge commit (OQ-1); if B4 has not merged, steps 1-6 and 8 apply on 95cf6f86 and step 7 waits (the URL RED rows R9* stay red and the unit does not open a PR until step 7 lands). Byte copies (Python `shutil.copyfile`) of every edited file into the notes folder with sha256 recorded before the first edit.
1. NEW `app/services/deny_hosts.py` (2.2). LF, pure ASCII.
2. `app/services/search_descriptor_service.py`: import `deny_hosts`; replace the `:111` literal by `DENY_HOSTS = deny_hosts.LEGACY_DESCRIPTOR_DENY_HOSTS` (the comment "House rule 7, in code" kept); `_deny` per C1. Nothing else.
3. `app/services/source_router.py`: import `data_guards_v2_enabled`, `is_denied_host` from `deny_hosts`; add `_ROUTABLE_MEMO` + `_routable_registry()` after `SOURCE_REGISTRY` (:532); switch the fourteen sites of 1.3 to one `_routable_registry()` read per call. The `:347` row and every other row byte-unchanged.
4. `app/services/rating_service.py`: import from `deny_hosts`; `_rating_source_denied`; the three edits of C3. The four sets byte-unchanged.
5. `app/services/price_service.py`: import `data_guards_v2_enabled` from `deny_hosts`; after `LUXURY_BRAND_KEYWORDS` add `COUNTERFEIT_BRAND_LINE_ALLOWLIST`, `_LUXURY_WHOLE_TOKEN_KEYWORDS`, `_LV_TOKEN_RE`; after `_contains_token` (it must be defined first) build `_CF_V2_RE` / `_CF_V2_REPLICA_RE` and `_counterfeit_v2`; the two body edits of C4. The keyword sets byte-unchanged.
6. `app/services/image_service.py`: import from `deny_hosts`; the `_is_valid_image_url` edit of C5.
7. (B4 merge base) `app/api/url_routes.py` (`_url_pre_gate` deny branch; the route passes `DENIED_SOURCE_MESSAGE` when the reason is `denied_source`) and `app/services/url_extraction_service.py` (`DENIED_SOURCE_MESSAGE`, the `_fetch_page_v2` hop deny, the `_extract_from_url_v2` `denied` branch, the `normalize_image_url` skip). If fix round 3 renamed any B4 symbol, GREEN maps by role and reports the mapping.
8. `tests/test_s81_d03_deny_and_guards.py` is the frozen RED file (GREEN does not edit it except a gate ruling).
9. `CLAUDE.md`: the section 8 row, inserted after the SESSION 80 B3 row (`CLAUDE.md:476-477` at base), edited with the Edit tool (CRLF preserved).

No other file. Explicitly untouched: `error_handler.py`, `structured_comparison_service.py`, `review_service.py`, `cache_service.py`, `magento_graphql_service.py`, every adapter, `data/*.json`, `app/legal/processors.json`, the clear-list tests, `tests/.pre_impl_failures.txt`, `requirements*`.

## 4. Existing pins

### 4.1 Pins that change deliberately

None in the CI state (flag OFF). Measured (guard_probe): the 28 counterfeit and 19 luxury literal rows of `tests/test_counterfeit_filter.py` / `tests/test_luxury_brands.py` keep their expected verdicts under the V2 rule, so the plan's "ON-only pins test_counterfeit_filter, test_luxury_brands" do not redden with this design. Known ON-only reds (CI runs OFF; never set the flag in a local `.env`): `tests/test_rating_tiers.py::TestExpandedTiers::test_fragrantica_is_tier_2` (asserts the OFF rule; ON tier 3). GREEN runs the comm set once more at head with `ENABLE_DATA_GUARDS_V2=true` exported for that runner call only (a measurement, not a gate) and lists every node that turns red; the list goes into the CLAUDE.md row and the PR body. The later R-A1 PR re-pins `test_rating_tiers.py:71-72` when it deletes the fragrantica entries.

### 4.2 Pins that must stay green and unedited

`tests/test_counterfeit_filter.py`, `tests/test_luxury_brands.py`, `tests/test_rating_tiers.py`, `tests/test_decomposed_services.py`, `tests/test_search_descriptor_d3.py` (incl. `test_the_two_forbidden_hosts_are_refused_without_a_fetch` :462-467, both states), `tests/test_bh_gcc_registry_loader.py` and `tests/test_registry_liveness_gate.py` (SOURCE_REGISTRY construction), `tests/test_source_router_*.py`, `tests/test_global_tier_never_genuine.py`, `tests/test_m13_registry_longest_host.py`, `tests/test_source_usage_field.py`, `tests/test_organic_pdp_harvest.py`, `tests/test_image_service*.py`, `tests/test_image_knowledge_graph_tier.py`, `tests/test_comparison_response_image_url.py`, `tests/test_url_*.py`, `tests/test_paid_route_metering.py`, `tests/test_legal_docs_u8.py` (T7b), `tests/test_model_config.py`, `tests/test_model_config_enforced.py`, `tests/test_prompt_fence.py`, the W4-11 digest fixture, the FY25 nine-digest node `tests/test_s75_fanout_identity.py::test_FY25_flag_off_compare_identity_matches_main`, `tests/test_s80_url_mode_v2.py` (after the B4 merge), and every file of the comm set (section 7).

## 5. RED tests: `tests/test_s81_d03_deny_and_guards.py`

Hermetic (no network: netguard on; no Supabase, OpenAI or Serper; route rows import `app.main` first and patch the recorders). Every RED row fails at base on an AssertionError only: missing symbols are read through helpers (`_mod(name)` = `importlib.util.find_spec` then import or None; `_attr(obj, name)` = getattr or None) and asserted. Every PIN row is green at base, runs with the full configuration of 2.7 and records its base value as a literal. Flag state is set per test with `monkeypatch.setenv` / `delenv` only. Fixtures: the gold rows frag-018, supp-021, fash-015, hair-005 (`data/validation_gold_truth.json`), the Serper organic shape of `tests/fixtures/serper_oudwood_organic.json` (fragrantica result at position 4 with rating 4.3 / 17104), and the tester scenario map of `eval_regression.json` (T07 never a wrong image; T02/T03 URL refusals before the reserve). The synthetic registry `_REG` (built with `source_router.Source`): denied rows D1 `fragrantica.com` global fragrances 1.0 (the literal shape), D2 `www.parfumo.de` gcc fragrances 1.5 mechanism `woo_store_json` status live `is_render_only=True`, D3 `media.parfumo.com` bahrain fragrances 3.0 `is_shopify=True` with a `SearchDescriptor` (`platform_api`, a `{q}` template on that host), D4 `fimgs.net` bahrain fragrances `is_algolia=True`, D5 `basenotes.com` bahrain fragrances mechanism `json_api`, D6 `forum.basenotes.net` bahrain fragrances mechanism `sitemap`, D7 `fragrantica.ru` bahrain fragrances (mechanism ""), D8 `fragrantica.asia` gcc fragrances with `sample_url` ending `/products.json`; allowed rows A1 `amazon.com` global all, A2 `sephora.com` global fragrances, A3 `bh.perfume-shop.test` bahrain fragrances `is_shopify=True`, A4 `notfragrantica.com` gcc fragrances 1.5.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1a | `test_r1a_module_exists` | `find_spec("app.services.deny_hosts")` is not None and exposes the 2.2 names | AssertionError (None) | C0 |
| R1b | `test_r1b_module_is_stdlib_only` | every top-level import of `deny_hosts.py` (AST) is in `sys.stdlib_module_names` or `__future__` | AssertionError (no file) | C0 |
| R1c | `test_r1c_no_http_literal_t7b_safe` | no non-docstring str constant in `deny_hosts.py` contains `http://` or `https://` | AssertionError | C0 |
| R1d | `test_r1d_deny_hosts_content` | `sorted(DENY_HOSTS)` == the 26 hosts; each lower case, no scheme / `www.` / port; `LEGACY_DESCRIPTOR_DENY_HOSTS == ("fragrantica.com", "parfumo.com")`; `DENY_LABELS` == the 4 labels | AssertionError | C0 |
| R1e | `test_r1e_is_denied_host[...]` (24 cases) | True: `fragrantica.com`, `www.fragrantica.com`, `FRAGRANTICA.COM.`, ` fr.fragrantica.com `, `fragrantica.com:443`, `fragrantica.ru`, `www.fragrantica.com.br`, `www.parfumo.de`, `media.parfumo.com`, `basenotes.com`, `basenotes.net`, `fimgs.net`, `rwebsocket.fimgs.net`; False: `notfragrantica.com`, `fragrantica.com.evil.test`, `fragranticacom.net`, `parfumo.co`, `fimgs.network`, `bahrain.ounass.com`, `""`, None, 123, `b"fimgs.net"`, `{}` | AssertionError | C0 |
| R1f | `test_r1f_is_denied_url[...]` | True: `https://fimgs.net/mdimg/perfume/375x500.1826.jpg`, `http://www.fragrantica.com/perfume/Tom-Ford/Oud-Wood-1826.html`, `//media.parfumo.com/x.jpg`, `fimgs.net/x.jpg`, `https://u@www.parfumo.de/x`, `https://fimgs.net:8443/x`; False: `https://bahrain.ounass.com/x`, `https://notfragrantica.com/x`, `http://[bad`, None | AssertionError | C0 |
| R1g | `test_r1g_is_denied_source[...]` | True: `Fragrantica`, `fragrantica.ru`, `Parfumo`, `Basenotes`, `https://fimgs.net/a.jpg`; False: `Notfragrantica`, `Boots`, `Sally Beauty`, `""`, None | AssertionError | C0 |
| R1h | `test_r1h_reader_truthy[TRUE| on |1|Yes]` | `data_guards_v2_enabled()` True | AssertionError (no module) | C0 |
| R1i | `test_r1i_single_deny_literal_list` | AST scan of `app/**/*.py`: no module other than `deny_hosts.py` assigns a tuple / list / set / frozenset literal containing `parfumo.com`, `basenotes.com` or `fimgs.net`; `search_descriptor_service.DENY_HOSTS is deny_hosts.LEGACY_DESCRIPTOR_DENY_HOSTS` (documented exemptions: the `source_router.py:347` Source row and the rating name sets) | AssertionError (`search_descriptor_service.py:111`) | C0 + C1 |
| R2a | `test_r2a_descriptor_deny_on[...]` | ON `_deny(h)` True for `basenotes.com`, `www.parfumo.de`, `fimgs.net`, `fragrantica.ru`, `www.fragrantica.com.br`; False for `notfragrantica.com`, `fragrancebh.com` | AssertionError (basenotes False) | C1 |
| R2b | `test_r2b_probe_refuses_new_hosts_without_fetch[basenotes.com|fimgs.net|www.parfumo.de]` | ON: `probe_search_descriptor(h, rec)` raises `ValueError` and the recorder (returns `(404, "")`) saw 0 calls (try/except, then one assert) | AssertionError (base probes, 3 calls) | C1 |
| R3a | `test_r3a_as_if_absent[<consumer>]` (22 params) | ON over `_REG` == OFF over `_REG` minus the denied rows, for: `get_sources_for_category` (fragrances; usage None / price / review), `build_site_discovery_query("Q", "fragrances", tier=t, limit=8)` for bahrain / gcc / global, `get_shopify_sources_for_category`, `get_algolia_sources_for_category`, `get_jsonapi_sources_for_category`, `get_curl_pagescrape_sources_for_category`, `get_sitemap_sources_for_category`, `get_woo_sources_for_category`, `get_gcc_shopify_pagescrape_sources_for_category`, `score_source(<D1 url>)`, `source_usage(<D2 url>)`, `registry_tier("www.fragrantica.com")`, `match_registry_apex("fr.fragrantica.com")`, `is_render_only_domain("www.parfumo.de")`, `_registry_row_for_host("media.parfumo.com")`, `search_descriptor_service.descriptor_for_host("media.parfumo.com")`, each with `ENABLE_LONGEST_HOST_MATCH` OFF and ON | AssertionError (the denied row is returned / scored) | C2 |
| R3b | `test_r3b_real_registry_global_query` | ON, real registry: `build_site_discovery_query("Dior Sauvage", "fragrances", tier="global", limit=8) == "Dior Sauvage site:amazon.com OR site:sephora.com OR site:walmart.com"`; `score_source("https://www.fragrantica.com/perfume/x-1.html", "fragrances") == 0.5`; `registry_tier("www.fragrantica.com") is None` | AssertionError (fragrantica included, 1.0, global) | C2 |
| R3c | `test_r3c_per_call_flip` | in one test: ON -> fragrantica absent from the global query; delenv -> present; ON again -> absent (the memo never serves an OFF read) | AssertionError on the first ON half | C2 |
| R4a | `test_r4a_rating_tier_denied_on` | ON `get_rating_tier` == 3 for `Fragrantica`, `fragrantica.com`, `Fragrantica.ru`, `Parfumo`; == 2 for `Sally Beauty`, `boots`; == 1 for `Sephora` | AssertionError (2) | C3 |
| R4b | `test_r4b_only_denied_candidate_no_rating` | ON `extract_rating_from_shopping("Tom Ford Oud Wood", [fragrantica item: source "Fragrantica", rating 4.3, ratingCount 17104, title "Tom Ford Oud Wood", link on www.fragrantica.com])["rating"] is None` | AssertionError (4.3 tier 2) | C3 |
| R4c | `test_r4c_denied_loses_to_allowed` | ON with the item of R4b plus a Boots item (rating 4.6, ratingCount 20, same title): the result's `rating_source.name` starts with `Boots` | AssertionError (Fragrantica wins on count) | C3 |
| R4d | `test_r4d_denied_link_with_neutral_source` | ON an item with source `somestore.com` (tier 2 by the .com rule) and a link on fimgs.net / fragrantica.com is never selected | AssertionError | C3 |
| R4e | `test_r4e_consensus_ignores_denied` | ON three tier-3 items from `Parfumo`, `Basenotes`, `Parfumo.de` with identical rating 4.0 and ratingCount 5000: rating None (base: the Google consensus fires) | AssertionError | C3 |
| R4f | `test_r4f_collect_retailer_ratings_drops_denied` | ON `collect_retailer_ratings(name, {name: [Fragrantica item, Boots item]})` lists only Boots | AssertionError | C3 |
| R5a | `test_r5a_frag018_replica_survives_on` | ON `is_counterfeit_listing` False for `Maison Margiela Replica Jazz Club Eau de Toilette 100ml` and `MAISON MARGIELA 'REPLICA' By the Fireplace EDT 100 ml` | AssertionError (True) | C4 |
| R5b | `test_r5b_substring_false_positives_gone_on[...]` | ON False for `Lattafa Oud Infused Eau de Parfum 100ml`, `Rose Infused Body Oil`, `Focused Serum 30ml`, `Unused tester 100ml`, `Copyright free`, `Copycat scent` | AssertionError | C4 |
| R5c | `test_r5c_frag018_shopping_price_on` | ON `extract_price_from_shopping("Maison Margiela Replica Jazz Club", [{"title": "Maison Margiela Replica Jazz Club Eau de Toilette 100ml", "price": "BHD 45.000", "source": "Ounass", "link": "https://bahrain.ounass.com/shop-maison-margiela-replica-jazz-club-edt-100ml-0001.html"}], "BHD", category="fragrances")` is not None and its `amount == 45.0` (satisfiable: measured in 1.11 with the C4 rule monkeypatched, amount 45.0 `local_bhd`) | AssertionError (None) | C4 |
| R5d | `test_r5d_reader_per_call` | in one test: ON infused title False; delenv -> True | AssertionError on the ON half | C4 |
| R6a | `test_r6a_lv_false_positives_gone_on[...]` | ON `is_luxury_brand` False for `Centrum Silver` (supp-021), `Calvin Klein boxer briefs` (fash-015), `L'Oreal Elvive shampoo` (hair-005), `Creed Silver Mountain Water 100ml`, `Velvet Matte Lipstick`, `Salvatore Ferragamo Uomo`, `Volvo key fob`, `LVMH annual report` | AssertionError (True) | C4 |
| R6b | `test_r6b_lv_whole_token_aliases_on` | ON True for `L.V. Neverfull`, `l.v monogram` | AssertionError (False) | C4 |
| R6c | `test_r6c_calvin_klein_floor_on` | ON `is_implausible_low_fragrance_price("Calvin Klein Eternity Eau de Parfum 100ml", 18.0) is False` and `_is_designer_fragrance_name(same) is False` | AssertionError (True) | C4 |
| R7a | `test_r7a_image_validator_denies_on[...]` | ON `_is_valid_image_url` False for `https://fimgs.net/mdimg/perfume/375x500.1826.jpg`, `https://rwebsocket.fimgs.net/a.png`, `https://www.fragrantica.com/x.jpg`, `http://media.parfumo.com/x.jpg` | AssertionError (True) | C5 |
| R7b | `test_r7b_search_payload_skips_denied_on` | ON `extract_image_from_search({"knowledgeGraph": {"imageUrl": <fimgs>}, "organic": [{"imageUrl": "https://cdn.perfume-shop.test/a.jpg"}]}) == "https://cdn.perfume-shop.test/a.jpg"` | AssertionError (fimgs) | C5 |
| R7c | `test_r7c_cascade_never_returns_denied_on` | ON, budget patched False: `asyncio.run(get_product_image_url("Tom Ford Oud Wood", page_scrape_image=<fimgs>))` is None | AssertionError (fimgs) | C5 |
| R7d | `test_r7d_tier3_denied_pick_refused_on` | ON, fake client returning `{"image_url": <fimgs>}`: `asyncio.run(extract_image_via_gpt(name, [organic row]))` is None | AssertionError (fimgs) | C5 |
| R8a | `test_r8a_url_compare_denied_url1[post|get]` | both flags ON: 400, `code == "NOT_PRODUCT_PAGE"`, `reason == "denied_source"`, `field == "url1"`, `error == DENIED_SOURCE_MESSAGE` (via `_attr`), reserve recorder 0 calls, compare recorder 0 calls | AssertionError (base: 200, reserve 1 call) | C6 |
| R8b | `test_r8b_field_rules` | url2 denied -> `url2`; both denied -> `both`; url1 denied + url2 a storefront root -> `both` with reason `denied_source` | AssertionError | C6 |
| R8c | `test_r8c_redirect_hop_never_fetched` | both ON, `_TRANSPORT` = a MockTransport answering the pasted PDP with 301 Location on www.fragrantica.com: the transport saw exactly one request (the pasted host); the per-url result has `code == "NOT_PRODUCT_PAGE"`, `reason == "denied_source"` | AssertionError (`_fetch_page_v2` absent at base) | C6 |
| R8d | `test_r8d_normalize_image_url_skips_denied` | both ON: `normalize_image_url(["https://fimgs.net/a.jpg", "https://cdn.perfume-shop.test/b.jpg"], "https://store.perfume-shop.test/p/1")` == the cdn url | AssertionError (absent at base) | C6 |
| R9a | `test_r9a_kb_guard` | `kb_source_allowed` True for `https://bahrain.ounass.com/x`, `Boots`, None, `""`; False for `https://www.parfumo.de/x`, `Fragrantica`, `fimgs.net`; `assert_kb_source_allowed("fimgs.net")` raises `DeniedSourceError` (a `ValueError`) whose message is the constant `denied source` | AssertionError | C7 |
| R9b | `test_r9b_kb_guard_is_flag_free` | with `ENABLE_DATA_GUARDS_V2` unset the guard still denies `fimgs.net` | AssertionError | C7 |
| P1 | `test_p1_off_consumers_equal_base[flag=unset|false|0|off||garbage]` | flag OFF, `_REG`, `ENABLE_URL_MODE_V2=true`, `ENABLE_LONGEST_HOST_MATCH` both: every R3a call returns the base value WITH the denied rows (recorded literal lists of domains / weights / tiers / query strings) | green | base |
| P2 | `test_p2_registry_never_mutated` | after ON and OFF calls: `source_router._LITERAL_ROWS[38] == Source("fragrantica.com", "global", ("fragrances",), 1.0)`, `len(_LITERAL_ROWS) == 44`, `SOURCE_REGISTRY` is the same object with the same length as before the calls, and the real global query OFF is the base literal of 1.1 | green | base / C2 |
| P3 | `test_p3_rating_off_equals_base` | flag OFF: `RATING_TIER_2` == the 21-entry literal set (with `fragrantica`), `LUXURY_FASHION_RETAILERS` == its 7-entry literal set, `get_rating_tier("Fragrantica") == 2`, the R4b/R4c/R4e/R4f inputs return the base results (Fragrantica selected, consensus fires, both listed) | green | base |
| P4 | `test_p4_descriptor_off_equals_base` | `search_descriptor_service.DENY_HOSTS == ("fragrantica.com", "parfumo.com")` (both states); OFF `_deny` False for basenotes / fimgs / parfumo.de / fragrantica.ru and True for `www.fragrantica.com`, `parfumo.com`; OFF the probe of `basenotes.com` makes its robots fetch (recorder 1+ calls) | green | base |
| P5 | `test_p5_guards_off_equal_base` | flag OFF: every R5/R6 input returns its base verdict (literal table from guard_probe: infused True, Centrum Silver True, `L.V. Neverfull` False, the Calvin Klein floor True) | green | base |
| P6 | `test_p6_guards_on_keep_whole_word_hits` | ON True for `Used tester 100ml`, `Creed Aventus replicas set`, `Aventus dupes 3 pack`, `Replica of Maison Margiela Jazz Club dupe`, `Inspired by Maison Margiela Replica Jazz Club`, `REPLICA Jazz Club EDT 100ml`, `Pre-owned bag`, `Second hand watch`; luxury ON True for `LV Neverfull MM`, `LV-Monogram scarf`, `Louis Vuitton Ombre Nomade`, `Tom Ford Velvet Orchid` | green (base substring) | C4 |
| P7 | `test_p7_guards_on_parity_existing_pin_corpus` | ON: the 28 counterfeit and 19 luxury literal rows of the two pin files (copied) keep their expected verdicts | green | C4 |
| P8 | `test_p8_importers_bind_the_same_function` | `algolia_service.is_counterfeit_listing is price_service.is_counterfeit_listing` (and woocommerce, salla, occ, unbxd, noon, magento, zyte); `shopify_pdp_service.ps.is_luxury_brand is price_service.is_luxury_brand`; the keyword sets equal their literals after ON calls | green | base |
| P9 | `test_p9_image_off_equals_base` | flag OFF: `_is_valid_image_url(<fimgs>)` True; R7b returns the fimgs url; R7c returns the fimgs url (budget False) | green | base |
| P10 | `test_p10_url_off_untouched[d03=off,v2=on | d03=on,v2=off]` | a fragrantica url1: with D03 OFF + V2 ON, or D03 ON + V2 OFF, the route reaches `_reserve_comparison_credit` (recorder 1 call) and `compare_from_urls` (recorder 1 call); no `denied_source` anywhere in the body | green at base (no pre-gate at base) | base / B4 |
| P11 | `test_p11_reader_falsy[unset||false|0|off|no|garbage|FALSE ]` | the consumers behave as base (one counterfeit, one registry, one image probe per value) | green | base |

Counts: 37 RED test functions (R1a-R9b, several parametrized; about 150 RED cases), 11 PIN test functions (about 120 PIN cases), 36 mutants. The RED author builds the base literals of P1, P3, P5 at base and freezes them in the file.

## 6. Mutation table

Each mutant on a byte copy (Python `shutil.copyfile`), an exact-string edit that matches once, the killing rows run through `pyt.py -k` (bound 600), restore from the copy, sha256 compare (stop on mismatch); `.qa-mutation.lock` held by the mutation agent.

| # | mutant (file: edit) | killed by |
|---|---|---|
| M1 | deny_hosts: `data_guards_v2_enabled` returns True | P1, P3, P5, P9, P11 |
| M2 | deny_hosts: reader without `.strip().lower()` | R1h (`TRUE`, ` on `, `Yes`) |
| M3 | deny_hosts: `is_denied_host` uses `d in h` (substring) | R1e (`notfragrantica.com`, `fragrantica.com.evil.test`, `fimgs.network`) |
| M4 | deny_hosts: exact match only (no subdomain arm) | R1e (`www.parfumo.de`, `media.parfumo.com`, `rwebsocket.fimgs.net`) |
| M5 | deny_hosts: `fimgs.net` removed from `DENY_HOSTS` | R1d, R7a |
| M6 | deny_hosts: `normalize_host` keeps the port | R1e (`fragrantica.com:443`) |
| M7 | deny_hosts: `is_denied_url` without the schemeless fallback | R1f (`fimgs.net/x.jpg`) |
| M8 | deny_hosts: `is_denied_source` label match without boundaries | R1g (`Notfragrantica`) |
| M9 | deny_hosts: `kb_source_allowed` reads the flag | R9b |
| M10 | search_descriptor: `DENY_HOSTS = deny_hosts.DENY_HOSTS` | P4, R1i |
| M11 | search_descriptor: `_deny` ignores the flag (always legacy) | R2a, R2b |
| M12 | source_router: `_routable_registry` filters with the flag OFF | P1, P2 |
| M13 | source_router: `score_source` still iterates `SOURCE_REGISTRY` | R3a[score_source], R3b |
| M14 | source_router: `get_sources_for_category` not routed | R3a[get_sources...], R3b |
| M15 | source_router: `_registry_row_for_host` not routed | R3a[registry_tier / match_registry_apex / descriptor_for_host] |
| M16 | source_router: the filter removes rows from `SOURCE_REGISTRY` in place | P2 |
| M17 | source_router: memo key without `len` / without the flag gate (serves an OFF read from the memo) | R3c, P1 |
| M18 | rating: denied source mapped to tier 3 but not skipped in `extract_rating_from_shopping` | R4b (17104 > 1000 makes it a tier-3 pick), R4e |
| M19 | rating: skip in the tiered fallback only, not before the consensus | R4e |
| M20 | rating: `collect_retailer_ratings` not filtered | R4f |
| M21 | rating: link host not checked | R4d |
| M22 | rating: `RATING_TIER_2.discard("fragrantica")` at import | P3 |
| M23 | price: V2 regex without the plural `(?:s|es)?` | P6 (`replicas`, `dupes`) |
| M24 | price: Margiela allowlist applied to every keyword | P6 (`Replica of Maison Margiela Jazz Club dupe`, `Inspired by Maison Margiela Replica Jazz Club`) |
| M25 | price: `used` dropped from the V2 keyword set | P6 (`Used tester 100ml`) |
| M26 | price: `lv` removed from the luxury check instead of whole-token | P6 (`LV Neverfull MM`) |
| M27 | price: `_LV_TOKEN_RE` without the dots (`lv` only) | R6b |
| M28 | price: counterfeit V2 ungated (flag ignored) | P5, R5d |
| M29 | image: deny check not gated by the flag | P9 |
| M30 | image: deny check only in `extract_image_from_search` | R7c, R7d |
| M31 | url: deny evaluated after `_reserve_comparison_credit` | R8a (reserve 0 calls) |
| M32 | url: deny fires with `ENABLE_URL_MODE_V2` OFF | P10 |
| M33 | url: `field` always `both` | R8a, R8b |
| M34 | url: redirect hop deny after the GET | R8c (transport saw 2 requests) |
| M35 | deny_hosts: an `import requests` added | R1b |
| M36 | deny_hosts: a `"https://fragrantica.com"` literal added | R1c (and T7b in the comm set) |

Equivalent survivors, if any, are reported for a ruling.

## 7. Comm set and gates for GREEN (cheapest first)

1. `python -m py_compile` and `ruff check --select E9,F63,F7,F82 --no-cache` on the seven app files + the test file.
2. Byte checks: new files LF and pure ASCII (count bytes > 127 = 0); `git diff --stat` shows no whole-file diff on a CRLF backend file.
3. Unit file, flag states as written (bound 600).
4. The pin groups of 1.10 at head (bound 600 each), then the CI-order set = the unit file + the two groups + `tests/test_s80_url_mode_v2.py` (bound 1200).
5. Comm set (zero-regression gate) = module and symbol reference grep UNION source-scanning pins UNION CLAUDE.md readers UNION SmartCompareApp-scanning tests, MINUS the `test_precommit_hook*.py` files: 299 files at base (`comm_set.txt` in the notes folder):
   - module grep `source_router|rating_service|search_descriptor_service|image_service|price_service|url_extraction_service|url_routes|deny_hosts` over `tests/*.py`: 253 files (+ support modules `tests/conftest.py`, `_env_safety.py`, `_hermeticity.py`, `w4_11_prompt_digest_recorder.py`: none is edited, so the support-module importer rule adds nothing);
   - symbol grep (`is_counterfeit_listing`, `is_luxury_brand`, the two keyword sets, `RATING_TIER_1/2`, `LUXURY_FASHION_RETAILERS`, `get_rating_tier`, `SOURCE_REGISTRY`, `_LITERAL_ROWS`, `DENY_HOSTS`, `_is_valid_image_url`, `get_product_image_url`, `extract_image_from_search`, `build_site_discovery_query`, `score_source`, `registry_tier`, `match_registry_apex`, `_registry_row_for_host`, `get_sources_for_category`, `extract_rating_from_shopping`, `collect_retailer_ratings`, `get_verified_rating`, `probe_search_descriptor`, `is_implausible_low_fragrance_price`, `_is_designer_fragrance_name`, `shopping_listing_matches`, `/url/compare`, `/url/extract`, `compare_from_urls`, `normalize_image_url`): 97 files (275 with the module grep);
   - files naming an edited module by path (`<module>.py`): 41; the walkers over `app/` (19, incl. `test_legal_docs_u8.py`, `test_model_config_enforced.py`, `test_u3c_store_false_pin.py`, `test_sentry_channels_u8d_unit.py`, `test_security_regression.py`); the listed source-scanning pins (`test_model_config.py`, `test_model_config_enforced.py`, `test_prompt_fence.py`, `test_u3c_store_false_pin.py`, `test_start_command.py`, `test_migration_index_predicate_immutability.py`, `test_openai_key_log_hygiene_s69.py`, `test_sentry_channels_u8d_unit.py`);
   - CLAUDE.md readers `tests/test_ci_gates.py`, `tests/test_behavior_dimension_translation.py` (CLAUDE.md changes);
   - the 25 SmartCompareApp-scanning backend tests (`grep -rl SmartCompareApp tests/`; the URL `reason` value set widens on the client-visible contract);
   - plus the new unit file and, on the B4 base, `tests/test_s80_url_mode_v2.py`.
   Run in chunks of at most 25 files (12 chunks), bound 1200 each, at base and at head, `comm -13` of the sorted FAILED node-id sets EMPTY; re-run a branch-only-new failure against base once to tell a network flake from a regression. Record the two known tiktoken ERROR nodes of `tests/test_prompt_truth.py` identically on both sides if they appear.
6. ON measurement (not a gate): the same chunks at head with `ENABLE_DATA_GUARDS_V2=true` exported for each runner call only; list every node that turns red (expected: `test_rating_tiers.py::TestExpandedTiers::test_fragrantica_is_tier_2`).
7. The mutation table of section 6.
8. The pre-commit hook test files are NOT run (no `.githooks` change).

## 8. CLAUDE.md flag row and owner steps

Insert after the SESSION 80 B3 row:

**SESSION 81 flag (D03 DENY-AND-GUARDS, 2026-10-22; default OFF, read PER CALL; a new name, so unset in production by construction (Railway not read); PLAN_S81 unit D03 (M1) and Fable ruling F1; spec `.qa-s80/D03_UNIT_SPEC.md` of the unit worktree):**
- `ENABLE_DATA_GUARDS_V2` (D03, `app/services/deny_hosts.py::data_guards_v2_enabled`; the stdlib-only leaf holds the ONE banned-host list `DENY_HOSTS` (fragrantica.com and its 20 language editions measured in the held corpora, parfumo.com, parfumo.de, basenotes.com, basenotes.net, fimgs.net = the Fragrantica image CDN), `is_denied_host` / `is_denied_url` / `is_denied_source` (registrable domain or any subdomain; www, port, trailing dot and case normalised; never raises), the descriptor's two-host tuple `LEGACY_DESCRIPTOR_DENY_HOSTS`, and the flag-FREE KB-writer guard `kb_source_allowed` / `assert_kb_source_allowed` / `DeniedSourceError` for the KB units; bare host names only, so the T7b legal scan sees nothing). **Effect ON:** (1) `source_router` skips a denied row AT USE in every consumer (selectors, discovery queries, `score_source`, `source_usage`, `registry_tier`, `match_registry_apex`, `is_render_only_domain`, `_registry_row_for_host` and the descriptor lookup return exactly what they would return if the row were absent; measured: the global fragrance discovery query loses `site:fragrantica.com` in both catalog states), while `SOURCE_REGISTRY` and `_LITERAL_ROWS` are built byte-identically (the `:347` row is never deleted; a per-process memo keyed on the registry object's id and length serves the filtered list); (2) `rating_service` never selects a denied rating source (tier 3 in `get_rating_tier`, skipped before tiering and the consensus in `extract_rating_from_shopping`, dropped from `collect_retailer_ratings`), the rating sets unchanged; (3) the descriptor probe refuses every denied host before a fetch; (4) `image_service` treats an image URL on a denied host as invalid in every tier; (5) with `ENABLE_URL_MODE_V2` also ON, a pasted link on a denied host is refused by the B4 pre-gate (after the SSRF 400, before the credit reserve) as 400 `NOT_PRODUCT_PAGE` with `reason: "denied_source"` and the matching `field`, a redirect hop onto a denied host is never followed (the same refusal through B4's non-delivery exit), and `normalize_image_url` skips a denied image; (6) `price_service.is_counterfeit_listing` matches whole tokens (a keyword plus an optional `s`/`es`), so "infused", "focused", "unused", "copyright", "copycat" no longer drop a listing, and ignores `replica` when the title carries `margiela` (gold frag-018), while whole-word hits ("used tester", "replicas", "dupes", "pre-owned") still drop; (7) `price_service.is_luxury_brand` matches `lv` only as a whole token (`LV`, `L.V.`), never inside Silver, Velvet, Calvin, Elvive, Salvatore (gold supp-021, fash-015, hair-005/010/012), so e.g. a Calvin Klein fragrance no longer takes the designer low-price floor. **Flag OFF:** byte-identical (pinned by `tests/test_s81_d03_deny_and_guards.py` P1-P11 with the full configuration: the denied rows flow through every consumer, the fragrantica rating is tier 2, the descriptor list is the two-host tuple, every guard verdict equals base, a fimgs.net image is valid, a fragrantica link reaches the reserve). **Stated limits:** (1) Serper organic results from denied hosts still reach the specs / reviews / Tier-3 image prompts and the `Per fragrantica.com:` review attribution (a follow-up unit); (2) a listing titled "REPLICA Jazz Club" without the brand word is still dropped; Amouage "Homage" titles still drop (owner call); (3) whole-token matching can admit a counterfeit phrased without any keyword as a whole word (e.g. "replicaa"); (4) `registry_tier(<denied host>)` is None ON, so the global-tier genuine-label refusals no longer see it (measured unreachable: no price or harvest gate admits a host scoring 0.5 without a BH marker); (5) `/url/extract` (admin-only under U13) is not denied; (6) the admin by_source dashboard still probes `fragrantica.com`; (7) `omega` / `tiffany` substring false positives in the luxury list are untouched; (8) never set the flag in a local `.env`: `tests/test_rating_tiers.py::TestExpandedTiers::test_fragrantica_is_tier_2` (and any node GREEN's ON run lists) encodes the OFF rule (CI runs flag OFF). **Precondition:** none to merge (the URL half lands on the B4 merge base); flip after approval, the owner's explicit yes, one canary window. **Canary:** the global discovery query in the Railway log carries no `site:fragrantica.com`; zero `rating_source` naming Fragrantica / Parfumo / Basenotes in fresh fragrance compares; zero `fimgs.net` in `products[i].image_url`; the counterfeit-rejection rate per category before vs after (expect a small drop concentrated in "infused" / Margiela titles); the shopping-price coverage of Calvin Klein / Elvive / Centrum Silver pairs; with URL mode ON, the `[URL-V2] refused ... reason=denied_source` count. **Rollback:** unset the variable (per call, immediate).

Owner steps (names only): none before merge; after approval set `ENABLE_DATA_GUARDS_V2=true` on `web` (and on `price-warmer` only if its warmer path should share the guards: OQ-7) in its own canary window.

## 9. Stated limits

- L1 Organic Serper results from denied hosts still reach the specs / reviews prompts and the review highlight attribution (`review_service.clean_review_citations` writes `Per fragrantica.com:`; the committed d2 baseline fixture shows it); the image Tier 3 prompt still lists denied links (only its output is refused). A follow-up unit (lane A, prompt digests move) is needed for full provenance hygiene (OQ-3).
- L2 The KB-writer guard has no caller here; KB / registry / web-search units must call it.
- L3 Direct `SOURCE_REGISTRY` readers outside source_router (cache_service dashboard list, magento currency, curl timeout, scs BH-locale set) are untouched; each measured inert for the only denied row.
- L4 "As if absent" makes `registry_tier(denied)` None (section 1.3); measured unreachable on the price and harvest paths.
- L5 The filtered-registry memo detects a replaced or resized `SOURCE_REGISTRY`, not an in-place same-length element swap (production never mutates it; tests replace the list).
- L6 The V2 counterfeit regexes are compiled at import from `COUNTERFEIT_KEYWORDS`; a runtime mutation of that set is not seen ON.
- L7 The Margiela allowlist keys on the brand token in the TITLE only; a title without "Margiela" stays dropped; a fake that names Margiela and `replica` but no other keyword passes.
- L8 "homage", "inspired", "generic", "alternative", "vintage" still drop whole-word titles (Amouage Homage Attar is a genuine product; owner call, OQ-5).
- L9 `L.V` / `LV.` count as luxury ON; `lvmh` does not.
- L10 Under ON a fragrance compare's global discovery window holds 3 domains instead of 4 (no replacement row exists in either catalog state); the Serper call count is unchanged.
- L11 `/url/extract` and `/url/detect` are not denied (admin-only / no fetch of the page body under U13).
- L12 The redirect-hop deny and `normalize_image_url` skip depend on B4's final bytes (fix round 3 may rename; GREEN maps by role).

## 10. Out of scope

No registry table, no KB tables, no migration, no `processors.json` row (no new external host is contacted; hosts are only refused); no deletion of the fragrantica literal row or the rating entries (the later R-A1 pure-defect PR after approval, F1); no organic-result filtering before the LLM prompts; no change to `omega` / `tiffany` / other luxury keywords; no robots or ToS registry state (S81-15); no web_search `blocked_domains` wiring (S81-21); no client copy for `denied_source` (client C3); no change to `scripts/*`.

## 11. Open questions for the orchestrator

- OQ-1 B4 dependency: build D03 GREEN on the B4 merge base (recommended; build order already puts S81-01 first), or carve C6 into a D03b that follows B4 so D03 can merge first?
- OQ-2 Deny list scope: the brief names four hosts; the corpus shows 20 Fragrantica language editions, parfumo.de, and the repo shows basenotes.net. Default: include all 26 (the ban is per site; zero registry rows are affected beyond fragrantica.com). Confirm.
- OQ-3 A follow-up unit for organic-result provenance (drop DENY_HOSTS results before the specs / reviews / Tier-3 image prompts and from the highlight attribution): it moves the W4-11 digests and touches lane A. Schedule?
- OQ-4 URL refusal copy: a new `DENIED_SOURCE_MESSAGE` (default) or reuse `NOT_PRODUCT_PAGE_MESSAGE` ("That link opens a store page, ..." is untrue for Fragrantica)? Build 3 shows its generic copy either way.
- OQ-5 Extend `COUNTERFEIT_BRAND_LINE_ALLOWLIST` to `homage -> amouage` (a genuine Amouage attar line)? Default no (not in the brief).
- OQ-6 The `omega` (Omega-3) and `tiffany` (Tiffany biscuits) luxury false positives on the gold set: a separate unit or fold into D03 under the same flag? Default separate.
- OQ-7 Should `price-warmer` get the flag too (it runs the same price path off-clock)? Default: the same window as `web`.
- OQ-8 `get_rating_tier` ON returns 3 for a denied source (default) or a new sentinel (0) so callers can tell "denied" from "unknown"? 3 keeps the int contract.
- OQ-9 Branch prefix: `feature/s80-d03-deny-and-guards` (the template) or `feature/s81-...` (the session)?

Not done in this spec: no RED file; the V2 rules were measured by an AST-only replica (`guard_probe.py`, gold set + fixtures + pin rows) and by monkeypatched prototypes of the two guards in a scratch worktree (1.11), not by a full GREEN prototype of the deny consumers (source_router, rating, descriptor, image, URL were measured at base only); the comm set was enumerated (299 files), not run; the ON-state node list of the comm set was not measured.
