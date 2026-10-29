# S81-G1 PRICE-PIPELINE group spec (measured): D08 JSONLD-WIDEN + S81-23 BYPASS-RETIRE

- Group: S81-G1 PRICE-PIPELINE, the first SAFE group under LC-9 (s81-common.txt OWNER RULING 2026-10-29). ONE branch `feature/s81-g1-price-pipeline`, ONE spec (this file), the orchestrator's spec review (LC-8), ONE RED round writing both RED files, ONE GREEN, ONE adversary (correctness lens with the engineering checks of section 12.6 folded in), ONE rebase, ONE PR.
- Units: D08 JSONLD-WIDEN (lane B; flags `ENABLE_IMAGE_PIPELINE_V2` + `ENABLE_JSONLD_RATING`; PLAN_S81 :155) and S81-23 BYPASS-RETIRE (lane B + ops; flag `ENABLE_SCRAPEDO_SUPER`; PLAN_S81 :140; owner decision 12; closes #93 as won't-do).
- Worktree `C:/Users/SynAckITPC/Documents/AI/sc-s81-g1`, detached at base `e7c81956f11749b1378aa449c4ac616c82bfe6a9` (`git rev-parse HEAD`), `git status --short` empty at the start and after every probe. Note: origin/main moved to `6c14ac95` at 15:46 (#377 S81-08, SmartCompareApp + CLAUDE.md + docs/privacy-data-inventory.md only, no app/ change): RED and GREEN run on the launch base, the rebase (one round) lands on 6c14ac95 or newer with a CLAUDE.md union.
- Evidence: PLAN_S81.md (:140, :155, the VERIFY "Images" and "Reviews" bullets :106-107/:118, owner decision 12 :210), PLAN_S80 section 0 + R-A1/R-A8/R-A13/R-A15, RULINGS_R0.md R0-3 (:16-21: the reduced dict, the wide-candidate pin, `_try_pharmacy_urls`), S81_G1_BRIEF.md (Q1-Q7), S81_15_GREEN_REPORT.md (the registry / robots record contract), the S81-15 CLAUDE.md block (CLAUDE.md:517-520 at base).
- Personal-data rule: no real names, emails, phone numbers, device ids or account ids in this file or in anything the group writes; synthetic hosts only (`store-a.example.com`, `cdn-a.example.com`; never a real merchant's account data), built at run time where a shape matters. No secret value; variable NAMES only. Production flag state: the newest dated ledger line (session-81 ledger.md) names none of the group's names; `SCRAPEDO_SUPER` is UNKNOWN in production (OWNER_ACTIONS_S81 item 5 asks "SCRAPEDO_SUPER (set or unset)", unanswered): every design below holds in both states (R-A15).
- Measurement location: `<scratchpad>/s81_g1_spec/` (`base_pins.log`). Nothing in the worktree was written except this file. Every file:line below was read at e7c81956 in this run.
- Base run (bounded runner, flags unset): `tests/test_wide_candidate_dict.py tests/test_m6_c5_judgeme_html_reviews.py tests/test_scrapedo_service.py tests/test_seed_zyte_guard.py tests/test_zyte_seed_variant.py tests/test_fragrance_content_quality.py` -> 183 passed, 1 warning. `[pyt] tag=g1spec-base-pins start=2026-10-29 18:37:53 end=2026-10-29 18:40:14 elapsed=140s bound=600s status=OK rc=0`; `[hermeticity] sentinel checked 183 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- NOT MEASURED in this run (box loaded; a plain two-file grep took over 120 s at 18:17): (a) the corpus gate OVERALL SHA256 at the base (`scripts/verify_flag_byte_identity.py` over `_proof`: the corpus is not in this worktree, `ls _proof` = absent; it lives in the `sc-scraper-proof` checkout); GREEN computes base and head in one sitting with the exact command of section 7.4; (b) the full comm set node record (section 7 gives the derivation and the seed counts; LC-6 base records are cached per (main sha, set hash)).

## 0. The group

### 0.1 Branch, units, flags

| unit | flags (new names, default OFF, read PER CALL, never cached at import) | reader | lane |
|---|---|---|---|
| D08 | `ENABLE_IMAGE_PIPELINE_V2` (image + identifiers), `ENABLE_JSONLD_RATING` (rating channel 1 + the LLM rating removal) | NEW `app/services/jsonld_widen.py::image_pipeline_v2_enabled` / `::jsonld_rating_enabled` | B |
| S81-23 | `ENABLE_SCRAPEDO_SUPER` (tri-state during the transition, Q6) | `app/services/scrapedo_service.py::scrapedo_super_enabled` | B + ops |

Branch `feature/s81-g1-price-pipeline` from the launch base. The flags stay per unit: the flip order is unchanged (PLAN_S81 "Flip order after approval"; none of the three is in the first windows).

### 0.2 Change list per unit (detail in each unit's section 3)

D08: NEW `app/services/jsonld_widen.py` (stdlib leaf + `deny_hosts`, `robots_eval`); `app/services/price_service.py` (the JSON-LD reduced result :14087-14143, `_try_pharmacy_urls` :16961-16974, `_widen_jsonld_candidate` :11088-11129, `_jsonld_product_rating` :10993-11063); `app/services/structured_comparison_service.py` (the piggyback :6185-6206, the rating block :6466-6485); `app/services/response_builder.py` (the derive loop :1593-1599, the reviews projection :1995-2010); `app/services/extraction_service.py` (the reviews prompt :976-1005 / :1856, `_normalize_review_response` :1883-1916); DELETE `app/services/judgeme_service.py`, `tests/test_m6_c5_judgeme_html_reviews.py`, `tests/fixtures/judgeme_c5/` (7 files); `scripts/seed_spec_spine.py` (one docstring line :129-131); CLAUDE.md (:348 the M6 judge.me clause, :377 runbook step (2), the new row); NEW `tests/test_s81_d08_jsonld_widen.py` + `tests/fixtures/s81_d08_rating_flag_off_golden.json`.

S81-23: `app/services/scrapedo_service.py` (:38-82); `scripts/seed_zyte_luxury.py` (docstring :1-18, `LUXURY_PAIRS` :58-69, `TRUTH_CRITICAL_SEEDS` :81-100); `tests/test_zyte_seed_variant.py` (E-rows), `tests/test_seed_zyte_guard.py` (one E-row); CLAUDE.md (:141, :142, :338, :805-808, :813, :818-820, the new row); NEW `tests/test_s81_s23_bypass_retire.py`.

### 0.3 Shared files and the order GREEN applies them

The ONLY file both units edit is `CLAUDE.md`. No app/ file is shared: S81-23 edits `scrapedo_service.py` only (its reader `source_router._super_routing_enabled` :807-820 calls `_super_enabled()` unchanged, so `source_router.py` is NOT edited); D08 never touches scrapedo / source_router / seed_zyte. GREEN order: (1) S81-23 code + its E-rows (smallest, independent); (2) D08 leaf, then price_service, scs, response_builder, extraction_service, the deletions, seed_spec_spine docstring; (3) CLAUDE.md last in one pass: the S81-23 in-place rewrites (:141, :142, :338, :805-808, :813, :818-820), the D08 in-place rewrites (:348, :377), then ONE new column-0 block "SESSION 81 flags (S81-G1 PRICE-PIPELINE: D08 JSONLD-WIDEN + S81-23 BYPASS-RETIRE, ...)" inserted after :520 (the S81-15 owner-steps bullet) holding both units' rows (section 8 of each unit).

### 0.4 Known rebases and dependencies

- CLAUDE.md: S81-08 (#377, merged 15:42), S81-12 (rebase round running), S81-09 (GREEN running) each add a block; the union is mechanical (the S81-G1 block goes after whatever is the last SESSION 81 block at rebase time).
- `structured_comparison_service.py` / `extraction_service.py`: S81-10 FRAGRANCE-ONLY-GATE (lane A, spec running) is expected to touch the compare entry and the parse path; D08's hunks are at :6185-6206, :6466-6485 (scs) and :976-1005, :1856, :1883-1916 (extraction): a known rebase, never the same lines measured today.
- `scripts/seed_spec_spine.py`: G2 KB-SEED (S81-16) ports this script to Haiku; D08's one docstring hunk (:129-131) is a known rebase for G2.
- D08 CONSUMES the S81-15 contract (the persisted `kb_merchants.robots` record, `robots_registry.robots_record` :472-503, `next_row_update` :620-716, `robots_eval.rules_for_agent` / `_match_len`) and PROVIDES a seam D14 LIVE-ROBOTS wires (Q1). S81-17 KB-INGEST later consumes `price["_jsonld_facts"]` (identity facts).

## Unit D08 JSONLD-WIDEN

### 1. Base state (measured at e7c81956)

#### 1.1 The JSON-LD capture (what already exists)

| site | file:line | measured fact |
|---|---|---|
| wide flag | price_service.py:4661-4687 | `wide_candidate_enabled()`: `ENABLE_WIDE_CANDIDATE`, DEFAULT ON (`not in ("false","0","no","off","")`), read per call |
| convention | price_service.py:10768-10811 | absent / empty / unparseable fields are OMITTED from the candidate, never None/""/[]; `_WIDE_CANDIDATE_GTIN_FIELDS = ("gtin13","gtin12","gtin8","gtin")` :10795 (no gtin14, no check digit); default bestRating 5.0 :10811 |
| image urls | price_service.py:10958-10990 `_jsonld_image_urls` | string / list / ImageObject (`url`, `contentUrl`, `@id`) -> de-duplicated list of stripped strings; no scheme / host / type check |
| rating | price_service.py:10993-11063 `_jsonld_product_rating` | Product node only (store-type deny list :10802-10805); `rating_value` finite, > 0, <= declared `bestRating` (else 5); `review_count` from `reviewCount` then `ratingCount`, carried only when > 0; returns `{"rating_value", ["review_count"]}`: the declared `bestRating` is NOT carried |
| widen | price_service.py:11088-11129 `_widen_jsonld_candidate` | sets `description`, `image` (:11098-11100), `sku` :11102-11104, `gtin` :11106-11110, `mpn`, `category`, `aggregate_rating` :11120-11122, `reviews`; no `size` key |
| call site | price_service.py:11980-11993 | `if wide_candidate_enabled(): _widen_jsonld_candidate(cand, product)`; the selection path reads none of the wide keys (pinned) |
| reduced result | price_service.py:14087-14143 (`extract_price_from_html`, JSON-LD branch) | `result = {amount, original_currency, currency, retailer, url, in_stock, confidence, estimated, source_method}` :14088-14098; `_stamp_listing_size` :14121 (fragrance `size` from the JSON-LD NAME / og:title / title, never the node's `size` property); `exact_gate_enabled()` name/brand stamp :14133-14142; `return _finish(result)` :14143. Nothing of `price_data["image"/"gtin"/"sku"/"aggregate_rating"]` reaches `result` |
| second producer | price_service.py:16920-16980 `_try_pharmacy_urls` | the return dict :16961-16974 (`amount, original_currency, currency, retailer, url, title, in_stock, confidence, estimated, source_method: "local_bhd"`) |
| other price-dict `image_url` writers | zyte_service.py:499, :661 | the off-clock Zyte seeds write `image_url` (possibly None) into cached price dicts; nothing on the live path writes `price["image_url"]` today |
| public projection | price_service.py:9389-9405 `public_price_view` | exact gate ON: drops `guard_rejected` and every `_`-prefixed key; exact gate OFF: identity |

#### 1.2 The image consumers

| site | file:line | fact |
|---|---|---|
| eager image race | structured_comparison_service.py:6041-6062 | `get_product_image_url(full_name, page_scrape_image=None, organic_results, search_payload)` under `_PHASE1_TIMEOUTS["image_url"]` (5.0 s, :5857) |
| piggyback override | structured_comparison_service.py:6185-6206 | `page_img = result["price"].get("image_url")` :6195; `if data_guards_v2_enabled(): if image_service._is_valid_image_url(page_img): result["image_url"] = page_img.strip()` :6200-6202; `elif page_img and isinstance(page_img, str) and (page_img.startswith("http://") or page_img.startswith("https://")): result["image_url"] = page_img.strip()` :6203-6206 (http accepted OFF) |
| validator | image_service.py:55-65 `_is_valid_image_url` | http or https prefix; under `ENABLE_DATA_GUARDS_V2` a `deny_hosts.is_denied_url` host is invalid; no raster check |
| response | response_builder.py:1950 | `overview.products[i].image_url = pd.get("image_url")`; SSE specs event scs:5197 |
| contract | PLAN_S80 section 0 item 4 | `overview.products[i].image_url` must be an absolute https raster URL or null |

#### 1.3 The rating pipeline and the LLM rating asks

| site | file:line | fact |
|---|---|---|
| provider tiers | rating_service.py:127-266 `extract_rating_from_shopping`, :269-333 `get_verified_rating` | Serper Shopping Tier 1 / 2 / 3 (> 1000 reviews) + the 3-seller consensus; returns `{rating, review_count, rating_verified, rating_source{name,url,retrieved_at,extract_method,confidence}}` |
| assignment | structured_comparison_service.py:6466-6480 | `rating_data` default all-None :6466; `result["rating"/"review_count"/"rating_verified"/"rating_source"]` :6477-6480 |
| GPT fallback | structured_comparison_service.py:532-560 `_apply_gpt_review_aggregate_fallback`, called :6485 | rating None + `reviews["average_rating"]` in 1.0..5.0 -> `rating` = avg, `rating_derived=True`, `review_count=None`, `rating_verified=False`, `rating_source={"name":"Aggregated from reviews","url":None,"extract_method":"gpt_review_aggregate","confidence":"low"}` |
| verified_rating | structured_comparison_service.py:6487-6494 | injected into `reviews` only when `rating_data["rating"]` (a provider rating) |
| derive | response_builder.py:468-471 `derive_rating_from_scores`; loop :1593-1599 | every product with `rating is None` gets `2.5 + overall/100*2.3` (cap 4.8) and `rating_derived=True`; the scs wrapper scs:3506-3507 |
| projections | response_builder.py:1933 (overview), :2004-2006 (reviews: rating, review_count, `rating_source`), scs:5263-5266 (SSE reviews event) | a `rating_derived=True` rating renders None; `rating_source` is projected AS IS (so the GPT stub `Aggregated from reviews` reaches `reviews.products[i].rating_source` today) |
| prompt asks | extraction_service.py:976 `REVIEWS_EXTRACTION_SYSTEM`, the asks :983 `"average_rating": 0.0-5.0 or null,` and :984 `"total_reviews": estimated_count or null,`; used :1856 (`{"role": "system", "content": REVIEWS_EXTRACTION_SYSTEM}`) and aliased :1141 `REVIEWS_EXTRACTION_PROMPT` | the estimated rating and count are model output |
| normaliser | extraction_service.py:1883-1916 `_normalize_review_response` | clears model `source_ratings` unconditionally :1904; coerces a string `average_rating` :1910-1915 |
| other reader | fact_check_service.py:360 | `gpt_rating = reviews.get("average_rating")` (review sentiment check) |
| rule | PLAN_S80 R-A8 | GPT-estimated ratings (`rating_derived`) never drive a category dimension |

#### 1.4 Robots and registry (the S81-15 contract, consumed not changed)

| site | file:line | fact |
|---|---|---|
| verdict | robots_registry.py:430-469 `decide_robots` | 2xx: the named agent AND `*` must both allow every probe URL, else `disallow`; 404/410 allow-all; challenge / other status -> `unreadable` with `challenge_vendor` |
| record | robots_registry.py:472-503 `robots_record` | the persisted `kb_merchants.robots`: `{state, status, body_sha, fetched_at, next_reread, crawl_delay, origin, source, rules:{qarenbot:[[allow|disallow, pattern]...], star:[...]}, probed, [rules_truncated]}`; "consumers answer per URL by evaluating `rules`"; frozen by `tests/fixtures/s81_s15_robots_record.json` |
| transitions | robots_registry.py:620-716 `next_row_update` | a live row failing robots -> `status="blocked"` + `blocked_reason`; a challenge -> `challenge={vendor, parked_until}` (`ROBOTS_CHALLENGE_PARK_DAYS`, default 7); a candidate is never blocked; a residential record younger than 30 days stands (`TRUSTED_RECORD_DAYS` :125) |
| matcher | robots_eval.py:173 `_match_len`, :187-216 `_rules_for_agent` (public alias `rules_for_agent` :214), :217-243 `can_fetch` | longest match wins, allow wins a tie, no rules -> allow; fails OPEN on error |
| live memo | merchant_registry.py:75 `READ_COLUMNS = "host,status,deny,blocked_reason,registry,partner"` | the live process does NOT read `robots` or `challenge`: there is NO live reader of the persisted verdict at base (D14 LIVE-ROBOTS builds it, flag `ENABLE_LIVE_ROBOTS_REGISTRY`, after the cron covers 100 % of live hosts) |
| deny | deny_hosts.py:54 `DENY_HOSTS`, :119 `normalize_host`, :150 `is_denied_host`, :168 `is_denied_url` | fragrantica (+ 20 editions), parfumo, basenotes, fimgs.net: 26 registrable domains, suffix match |
| brand domains | price_service.py:587-600 `OFFICIAL_BRAND_DOMAINS` (re-exported scs:3271) | a set literal of 25+ brand / authorized hosts |

#### 1.5 judge.me (Q2)

`app/services/judgeme_service.py` (403 lines, flag `ENABLE_JUDGEME_HTML_REVIEWS` :64). Importers measured with `git grep judgeme_service -- app scripts tests`: ONE, `tests/test_m6_c5_judgeme_html_reviews.py:35` (`import app.services.judgeme_service as judgeme`, 235 lines) + its fixtures `tests/fixtures/judgeme_c5/` (`SOURCES.json` and six `.html`). `scripts/seed_spec_spine.py:129-131` is a DOCSTRING mention only ("Mirrors ``judgeme_service._iter_jsonld_nodes``; kept local so a batch script never imports the review stack"): the script imports nothing from it (its imports :42-71, :216, :319, :377-378). The brief's "one importer, seed_spec_spine" is corrected: zero production or script importers. `app/legal/processors.json` and every other tracked file under app/ name no judgeme symbol. The other M6 pins (`test_m6_c1_normalize_and_sitemap_match.py`, `test_m6_c2_sitemap_pdp_markers.py`, `test_m6_c3_fragrance_glass_exemption.py`) do not touch judge.me and stay.

#### 1.6 Flag-reader idiom and line endings

House idiom: `os.getenv("ENABLE_X", "false").strip().lower() in ("true", "1", "yes", "on")`, e.g. `deny_hosts.data_guards_v2_enabled` (:114-117), `zyte_service._enabled` (:242-246). Every existing file D08 edits is `i/lf w/crlf` (`git ls-files --eol`: price_service, structured_comparison_service, response_builder, extraction_service, image_service, judgeme_service, seed_spec_spine, CLAUDE.md, tests/test_wide_candidate_dict.py, tests/test_m6_c5_judgeme_html_reviews.py): Edit tool on existing files; new files LF like the S81-15 new files.

#### 1.7 Libraries

No new dependency: the leaf uses `os`, `re`, `math`, `ipaddress`, `urllib.parse`, `datetime` and the in-repo `deny_hosts` + `robots_eval` (both stdlib leaves). No network, no fetch, no content-type sniff.

#### 1.8 Guards the new code must not trip

- `tests/test_sentry_channels_u8d_unit.py` R8 AST scan over app/: D08 adds NO log line (no `logger.*` call in the leaf or the hunks).
- `tests/test_prompt_fence.py`: every consuming system prompt carries `SEARCH_RESULTS_GUARD`; the D08 prompt variant is DERIVED from `REVIEWS_EXTRACTION_SYSTEM` by two count-checked `replace` calls, so it keeps the guard; the fence test must include the variant (GREEN adds the constant name to whatever list the fence iterates, if it iterates names: read `tests/test_prompt_fence.py` first; a fence that reads app/ source by AST sees a new module-level string, re-run it).
- `tests/fixtures/w4_11_prompt_render_digests.json` (the W4-11 digests): flag-OFF renders unchanged by construction (the constant is untouched; the variant is a NEW name).
- `tests/test_wide_candidate_dict.py::test_the_wide_keys_do_not_leak_into_the_page_scrape_result` (:460-475; Q3): asserts the eight wide keys (`description, image, sku, gtin, mpn, category, aggregate_rating, reviews`) are NOT in the `extract_price_from_html` result with `ENABLE_WIDE_CANDIDATE=true`. D08 ships the image as `image_url` (R0-3 ruling) and the identifiers + rating under ONE internal key `_jsonld_facts`, so the pin stays green in BOTH D08 flag states.
- The fail-OPEN `robots_eval.can_fetch` must NOT be the D08 evaluator (it returns True on error): D08's `rules_allow` is fail-CLOSED (section 2.3).

#### 1.10 Base pass state

See the header: the six touched pin files, 183 passed at base (`[pyt] tag=g1spec-base-pins ... status=OK rc=0`). The comm set base record is GREEN's (LC-6 cache, section 7).

### 2. Contract

#### 2.1 Flags (readers in the new leaf `app/services/jsonld_widen.py`)

```python
_TRUTHY = ("true", "1", "yes", "on")
def image_pipeline_v2_enabled() -> bool:   # ENABLE_IMAGE_PIPELINE_V2, default OFF, per call
    return os.getenv("ENABLE_IMAGE_PIPELINE_V2", "false").strip().lower() in _TRUTHY
def jsonld_rating_enabled() -> bool:       # ENABLE_JSONLD_RATING, default OFF, per call
    return os.getenv("ENABLE_JSONLD_RATING", "false").strip().lower() in _TRUTHY
```
Each is the FIRST statement of every gated branch, so OFF reads no other state. The two flags are independent (either may be ON alone). Contract freeze (PLAN_S80 section 0, `runs/research/contract_freeze.json`): every new key is ADDITIVE and appears only ON; no build-3 key is removed, renamed or retyped; no new error code, never a bare 503 (D08 adds no error path at all).

#### 2.2 The image and identifier policy (Q5)

`allowed_image_url(url, page_url) -> Optional[str]` (pure, never raises): returns the stripped URL or None. Accept iff ALL:
1. a `str`; stripped; scheme exactly `https` (`urlsplit(...).scheme.lower() == "https"`); a netloc; no userinfo (`@` in netloc -> None);
2. host is a PUBLIC name: not an IP literal (`ipaddress.ip_address(host)` parses -> None), not `localhost`, has at least one dot, and does not end in `.local`, `.internal`, `.localhost`, `.test` or `.invalid` (so an accepted-host test row uses a public-shaped synthetic host such as `store-a.example.com`, never the `.test` hosts the D03 file uses);
3. RASTER by the PATH extension (query and fragment ignored), case-insensitive, in `RASTER_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif")`; `.svg`, no extension, `.php` -> None (no fetch, no sniff; Q5);
4. NOT denied: `deny_hosts.is_denied_url(url)` False, evaluated UNCONDITIONALLY (not behind `ENABLE_DATA_GUARDS_V2`: the D08 policy is its own; fimgs.net / fragrantica / parfumo / basenotes are always refused);
5. ALLOWLISTED host, any of: (a) first-party: the image host and the `page_url` host share the registrable suffix (the image host equals the page host, or ends with "." + the page host with a leading `www.` stripped from both); (b) a suffix match on `IMAGE_CDN_HOSTS` (a frozen tuple in the leaf: `"cdn.shopify.com", "cdn.salla.sa", "cdn.salla.network", "media.zid.store"`: the platform CDNs of the registry's $0-adapter platforms; GREEN measures the JSON-LD image-host distribution over the 92 Gulf PDPs as INFORMATION and lists it in the PR body, the tuple is not widened in this unit); (c) the host (minus `www.`) is in `price_service.OFFICIAL_BRAND_DOMAINS` (passed in as an argument `brand_domains` so the leaf never imports price_service). The live registry is NOT consulted for images (the page host already IS the merchant that served the JSON-LD; a registry lookup adds I/O for no gain).

`valid_gtin(text) -> Optional[str]`: remove spaces and hyphens; digits only; length in (8, 12, 13, 14); GS1 mod-10 check digit (weights 3,1 from the right excluding the check digit) must match; returns the digit string or None. `size_text(value) -> str`: `price_service._jsonld_scalar_text(value)` for a Text, or `"<value> <unitText or unitCode>"` for a QuantitativeValue node, capped at 64 chars, "" when unusable (the convention).

#### 2.3 The rating channel-1 rule (Q1) and the reader seam

The rule is pure: `rating_host_allowed(entry, page_url, now) -> bool` where `entry` is a host's registry row view `{"status", "deny", "robots", "challenge"}` (exactly the `kb_merchants` columns of those names). True iff ALL:
1. `entry` is a dict; `deny` falsy; `status == "live"`; the page host is not `deny_hosts.is_denied_host`;
2. `robots` is a dict with `state == "allow"`;
3. NOT expired: `fetched_at` parses (ISO-8601, `Z` accepted) and `now < next_reread + ROBOTS_GRACE` (`ROBOTS_GRACE = timedelta(hours=24)`; a missing or unparseable `next_reread` -> expired);
4. the page URL's path (+ query) is allowed by BOTH `robots["rules"]["qarenbot"]` AND `robots["rules"]["star"]` under `rules_allow(rules, url)` (most restrictive of QarenBot and `*`); `rules_allow` mirrors `robots_eval.can_fetch`'s loop (longest `robots_eval._match_len`, allow wins a tie, an empty list -> allow) but FAIL-CLOSED: any exception or a malformed rule -> False;
5. `robots.get("rules_truncated")` falsy (a capped list cannot prove an allow: the record's own docstring);
6. no challenge: `challenge` absent or `{}`, or its `parked_until` parses and is <= now (a vendor without a parsable `parked_until` = parked = False).

Reader seam (the D14 hand-off): `ROBOTS_ENTRY_LOOKUP: Callable[[str], Optional[Mapping]]` module attribute, default `_no_entry` returning None. A missing entry = no channel-1 rating (stated). D08 does NOT read `kb_merchants` (no live reader exists at base, section 1.4; building one is D14's scope with its own precondition). Consequence, stated in the CLAUDE.md row: with only D08 merged, `ENABLE_JSONLD_RATING` ON removes the fabricated ratings (2.5) and adds NO channel-1 rating until D14 assigns the seam.

#### 2.4 Where the facts land

Under `ENABLE_IMAGE_PIPELINE_V2`, `stamp_jsonld_facts(result, price_data, page_url, brand_domains)` is called in the JSON-LD branch AFTER the whole exact-gate name/brand block (:14133-14142) and BEFORE `return _finish(result)` (:14143), at the indentation of the `if _label_ok:` body (inside it, so a currency-declined hit is never stamped), and in `_try_pharmacy_urls` on the dict it returns (:16961-16974):
- `result["image_url"]` = the FIRST entry of `price_data.get("image")` (a list) that `allowed_image_url` accepts; key OMITTED when none (R0-3);
- `result["_jsonld_facts"]` = a dict with only the present members: `gtin` (`valid_gtin(price_data.get("gtin"))`), `sku` (`price_data.get("sku")`, str, capped 64), `size` (`price_data.get("size")`, see 2.5); key OMITTED when empty.
Under `ENABLE_JSONLD_RATING` (independently): `result["_jsonld_facts"]["rating"] = {"value": v5, "count": n|None}` from `price_data["aggregate_rating"]`: `v5 = round(rating_value * 5.0 / best, 1)` with `best = aggregate_rating.get("best_rating") or 5.0`, kept only if 1.0 <= v5 <= 5.0; `count` = `review_count` or None.
The `_` prefix keeps the facts out of the public price (exact gate ON, production) through the existing `public_price_view`; the image goes out only through the existing piggyback.

#### 2.5 The candidate (two flag-gated additions in `_widen_jsonld_candidate` / `_jsonld_product_rating`)

- `ENABLE_IMAGE_PIPELINE_V2`: `cand["size"] = size_text(product.get("size"))` when non-empty (the node's schema.org `size`; NEVER written into `result["size"]`, so `_stamp_listing_size` and the pair fairness are untouched).
- `ENABLE_JSONLD_RATING`: `_jsonld_product_rating` adds `"best_rating": <declared bestRating>` when the node declares a finite one > 0 and != 5.0.
Flag OFF: the candidate dict is byte-identical (the wide pins and `tests/test_hostile_jsonld.py` stay green).

#### 2.6 The piggyback (scs:6185-6206)

`if image_pipeline_v2_enabled():` (first) -> `ok = jsonld_widen.allowed_image_url(page_img, result["price"].get("url"), OFFICIAL_BRAND_DOMAINS)`; when ok: `result["image_url"] = ok`; else the eager cascade result stands. This applies to EVERY producer of `price["image_url"]` (the JSON-LD stamp and the cached Zyte seeds), so an http or off-allowlist image never replaces the cascade under ON. `else:` the base D03 branch and the base inline branch, byte-for-byte.

#### 2.7 The rating changes under `ENABLE_JSONLD_RATING` (Q4)

At scs:6480 (after `result["rating_source"] = ...`), when the flag is ON:
1. `ch1 = jsonld_widen.channel1_rating(result.get("price"), now)`: the price's `_jsonld_facts.rating`, the page host and URL from `price["url"]`, `entry = ROBOTS_ENTRY_LOOKUP(host)`, `rating_host_allowed(entry, url, now)`; returns `{"value", "count", "source": <host>, "url": <price url>, "extract_method": "jsonld_aggregate_rating"}` or None. `now` comes from the seam `jsonld_widen._now` (production `datetime.now(timezone.utc)`).
2. When `ch1`: `result["jsonld_rating"] = ch1` (ADDITIVE, always, beside `rating_source`), and ONLY when `result["rating"] is None` (no provider rating: Serper tiers / consensus win, channel 1 fills the slot the GPT estimate used to fill): `rating = ch1["value"]`, `review_count = ch1["count"]`, `rating_verified = False`, `rating_source = {"name": "<host> (product page)", "url": <price url>, "retrieved_at": <now ISO Z>, "extract_method": "jsonld_aggregate_rating", "confidence": "medium"}`; `rating_derived` is never set.
3. `_apply_gpt_review_aggregate_fallback(result)` (:6485) is NOT called.
4. response_builder: the derive loop (:1593-1599) is skipped (`if not jsonld_rating_enabled():` around it, read once per build); the reviews projection (:1995-2010) gains `"jsonld_rating": pd["jsonld_rating"]` on a product entry ONLY when the flag is ON and the key is truthy (a post-pass over the built list, so OFF builds the identical list).
5. extraction: a NEW constant `REVIEWS_EXTRACTION_SYSTEM_NO_RATING` = `REVIEWS_EXTRACTION_SYSTEM` with the two lines `    "average_rating": 0.0-5.0 or null,\n` and `    "total_reviews": estimated_count or null,\n` removed (each `replace` asserted to match exactly once at import, the W4-11 count-checked-swap pattern); the call at :1856 picks `..._NO_RATING` when the flag is ON; `_normalize_review_response` sets `data["average_rating"] = None` and `data["total_reviews"] = None` when the flag is ON (a belt: a disobedient model's numbers never survive).
Consequence ON (stated): `reviews.products[i].rating_source` is None (not the GPT stub) for a product with no provider and no channel-1 rating; `fact_check.review_sentiment_consistent` becomes None for fresh reviews (its `gpt_rating` is None), cached reviews keep their old `average_rating` until the reviews TTL (7 d / 14 d) but it is no longer promoted.

#### 2.8 Test seams

`jsonld_widen.ROBOTS_ENTRY_LOOKUP` [the None lookup], `jsonld_widen._now` [UTC now], `jsonld_widen.IMAGE_CDN_HOSTS`, `RASTER_EXTENSIONS`, `ROBOTS_GRACE` [24 h]. Tests patch the seam with a recording callable (B1 rule: the flag-OFF PIN rows assert it is NEVER called).

#### 2.9 Flag-OFF identity (the unit's main invariant)

With `ENABLE_IMAGE_PIPELINE_V2` and `ENABLE_JSONLD_RATING` unset / `false` / `0` / `off` / `""` / ` OFF `: the `extract_price_from_html` and `_try_pharmacy_urls` results, the candidate dict, the piggyback outcome, the rating block outputs, the response projections, the reviews prompt bytes and the normaliser are byte-identical to base, the seam is never called, `jsonld_widen` performs no work beyond the two env reads. Proven by the PIN rows (section 5) with the FULL configuration present (both flags OFF in each falsy spelling, `ENABLE_WIDE_CANDIDATE=true`, both exact-gate modes, `ENABLE_DATA_GUARDS_V2` both ways, the seam patched to a recorder that would allow), by the golden-sequence fixture for the rating path, and by the corpus gate (section 7.4).

#### 2.10 Failure table (flags ON)

| input | result |
|---|---|
| JSON-LD image http / data: / protocol-relative / IP literal / localhost / non-raster / denied / third-party host | that entry skipped; the next entry tried; none -> no `image_url` key; the cascade image stands |
| gtin wrong check digit / 9-11 digits / letters | no `gtin` member |
| aggregate rating with bestRating 10, value 8 | `value` 4.0 |
| value outside 1..5 after scaling | no `rating` member |
| no registry entry (the D08 default) / status blocked or candidate / deny / state disallow or unreadable / expired / either agent disallows the path / rules truncated / challenge parked in the future / malformed rules | no channel-1 rating; nothing else changes |
| price None / not a dict / no `url` | no channel-1 rating |
| a raise inside `stamp_jsonld_facts` or `channel1_rating` | must not happen (pure, total); a raise is a test failure, never caught silently |

### 3. Change list (GREEN, in order; byte-copy every existing file first into `<scratchpad>/S81-G1_green_before/` with sha256)

1. NEW `app/services/jsonld_widen.py`: 2.1-2.4, 2.8; imports `os, re, math, ipaddress, datetime, urllib.parse`, `app.services.deny_hosts`, `app.services.robots_eval`; never imports price_service, scs or any I/O module; no logger.
2. `app/services/price_service.py`: (a) `_jsonld_product_rating` the `best_rating` member under `jsonld_rating_enabled()` (2.5); (b) `_widen_jsonld_candidate` the `size` member under `image_pipeline_v2_enabled()` (2.5); (c) the JSON-LD branch: one gated call `if image_pipeline_v2_enabled() or jsonld_rating_enabled(): jsonld_widen.stamp_jsonld_facts(result, price_data, url, OFFICIAL_BRAND_DOMAINS)` between :14142 and :14143 (the stamp itself re-reads each flag for its own members); (d) the same call on the `_try_pharmacy_urls` dict (build the dict into a local, stamp, return).
3. `app/services/structured_comparison_service.py`: the piggyback branch (2.6) and the rating block (2.7 steps 1-3); `from app.services import jsonld_widen` beside the D03 imports (:1549-1553).
4. `app/services/response_builder.py`: 2.7 step 4 (derive loop guard, reviews post-pass).
5. `app/services/extraction_service.py`: 2.7 step 5 (the derived constant next to `REVIEWS_EXTRACTION_SYSTEM`, the per-call pick at :1856, the normaliser belt).
6. DELETE `app/services/judgeme_service.py`, `tests/test_m6_c5_judgeme_html_reviews.py`, `tests/fixtures/judgeme_c5/` (`git rm`, 9 paths) (Q2).
7. `scripts/seed_spec_spine.py:129-131`: the docstring becomes "Every dict node in every JSON-LD block, in document order; kept local so a batch script never imports the review stack." (no code change).
8. CLAUDE.md (section 8).
9. NEW tests (written by RED, frozen): `tests/test_s81_d08_jsonld_widen.py`, `tests/fixtures/s81_d08_rating_flag_off_golden.json`.
No other file. No requirements, no client file, no migration, no `.githooks`, no processors.json (no new external host: D08 fetches nothing), no edit to `tests/.pre_impl_failures.txt`.

### 4. Existing pins

#### 4.1 Deliberate changes

| # | pin | today | change | reason |
|---|---|---|---|---|
| E1 | `tests/test_m6_c5_judgeme_html_reviews.py` (every node, 235 lines) + `tests/fixtures/judgeme_c5/` | pin the dead judge.me module | DELETED with the module | Q2: the module has no importer, judge.me is forbidden by the licensing ruling (CLAUDE.md:377 CAVEAT "judge.me is forbidden by the licensing ruling and is on the delete list"); the absence is pinned by R-D08-18 |
| E2 | `tests/test_prompt_fence.py` (only if it enumerates prompt constants by name) | the consuming system prompts | the variant joins the enumeration | the variant is a consuming system prompt under ON; GREEN reads the file first and records whether E2 applies |
No other existing pin changes; in particular `tests/test_wide_candidate_dict.py` is UNCHANGED (Q3).

#### 4.2 Must stay green and unedited

`tests/test_wide_candidate_dict.py` (all 40-odd nodes; :460-475 is the plan's `test_wide_candidate_dict` pin, Q3), `test_hostile_jsonld.py`, `test_jsonld_shape_ladder.py`, `test_correctness_coverage_review_findings.py` (block H), `test_s81_d03_deny_and_guards.py`, `test_s81_s15_registry_robots.py` + `test_s81_s15_gate_rows.py`, `test_image_service*.py`, `test_fact_checking.py`, `test_prompt_fence.py`, the W4-11 digest test, `test_sentry_channels_u8d_unit.py` (R8), every rating / review / response_builder test, the W4-13 flag-OFF ledger, the T23 OpenAPI fixture tests (no route or param change), and the rest of the comm set.

### 5. RED tests: `tests/test_s81_d08_jsonld_widen.py` (new; pure ASCII; hermetic)

Harness: nothing D08 creates is imported at module top; a helper `_leaf()` returns `importlib.util.find_spec("app.services.jsonld_widen")` and each RED row asserts it is not None before importing inside the body (AssertionError at base, never ImportError). An autouse fixture `delenv`s `ENABLE_IMAGE_PIPELINE_V2`, `ENABLE_JSONLD_RATING`, sets `ENABLE_WIDE_CANDIDATE=true`, restores `ROBOTS_ENTRY_LOOKUP` / `_now` after each test (via `monkeypatch.setattr` only when the leaf exists). Synthetic hosts only; HTML built from dicts with `json.dumps`; httpx mocked by patching `app.services.price_service.httpx.AsyncClient` for `_try_pharmacy_urls` (the house pattern); the piggyback AND the rating block are driven through the REAL `StructuredComparisonService._fetch_product_data` with the harness D03 already uses for exactly this site (`tests/test_s81_d03_deny_and_guards.py` `_scs_fetch(page_img, cascade_img)` and its `_scs_product_info()` / patch set around :1470-1507: COPIED into the D08 file, never imported from another test file), extended with a patched `_get_verified_rating` (the provider `rating_data`) and a patched reviews result (the `average_rating` the GPT fallback reads); so every scs PIN row is green at base against the real inline code, and every scs RED row fails at base on its assertion (ON behaves as base). GREEN may extract helpers; the rows never depend on them.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_d08_r1_flag_readers_per_call` (param: unset, "", "false", "0", "no", " OFF ", "true", "1", "yes", "on", " TRUE ") | each reader True exactly for the truthy spellings; flipping the env after import flips the result | RED (`find_spec` None -> AssertionError) | 2.1 |
| R2 | `test_d08_r2_image_policy_accepts` (param: first-party https .jpg with query, www/apex pair, `cdn.shopify.com` .webp, a brand domain .png) | `allowed_image_url` returns the stripped url | RED | 2.2 |
| R3 | `test_d08_r3_image_policy_refuses` (param: http, `//host/x.jpg`, `data:image/png;base64,...` built at run time, IP literal, localhost, userinfo, `.svg`, no extension, a fimgs.net / fragrantica / parfumo url, an unrelated third-party host) | None | RED | 2.2 |
| R4 | `test_d08_r4_valid_gtin` (param: valid 8/12/13/14 with spaces/hyphens; wrong check digit; 9/10/11 digits; letters; "") | the digits or None | RED | 2.2 |
| R5 | `test_d08_r5_reduced_result_image_url_on` | image flag ON: `extract_price_from_html` result carries `image_url` = the first ALLOWED entry of a node listing [http, fimgs, first-party https]; omitted when none allowed; the eight wide keys still absent | RED | 2.4 |
| R6 | `test_d08_r6_reduced_result_facts_on` | image flag ON: `_jsonld_facts` == {gtin (valid only), sku, size}; a wrong-check-digit gtin absent | RED | 2.4, 2.5 |
| R7 | `test_d08_r7_rating_fact_on_scaled` (param: bestRating absent 4.4 -> 4.4; bestRating 10 value 8 -> 4.0; bestRating 100 value 92 -> 4.6) | rating flag ON only: `_jsonld_facts == {"rating": {...}}`, no `image_url` | RED | 2.4, 2.5 |
| R8 | `test_d08_r8_pharmacy_producer_on` | `_try_pharmacy_urls` ON: the same stamp on its dict | RED | 3.2(d) |
| R9 | `test_d08_r9_piggyback_on` (param: https allowed / http / off-allowlist / denied) | ON, through the real `_fetch_product_data`: only the allowed one replaces the cascade image | RED (base promotes http and off-allowlist) | 2.6 |
| R10 | `test_d08_r10_rules_allow` (param table: empty -> True; `disallow /p/` vs `/p/x` -> False; `allow /p/x` + `disallow /p/` -> True; `$` and `*` patterns; a malformed rule -> False) | fail-closed longest-match | RED | 2.3 |
| R11 | `test_d08_r11_host_rule_allows` | a live, fresh, both-agents-allow, unparked entry -> True | RED | 2.3 |
| R12 | `test_d08_r12_host_rule_refuses` (param, one failing condition each: None, deny, blocked, candidate, disallow, unreadable, expired, missing next_reread, star disallows the path, qarenbot disallows, truncated, parked_until in the future, vendor without parked_until, denied host) | False | RED | 2.3 |
| R13 | `test_d08_r13_default_seam_no_rating` | rating ON, default `ROBOTS_ENTRY_LOOKUP`: no `jsonld_rating`, `rating` stays None, the GPT fallback NOT applied (no `rating_derived`) | RED | 2.3, 2.7 |
| R14 | `test_d08_r14_channel1_fills_empty_slot` | rating ON + an allowing seam: `jsonld_rating` == the literal dict; `rating`/`review_count`/`rating_source` filled as 2.7 step 2 (`retrieved_at` from the `_now` seam) | RED | 2.7 |
| R15 | `test_d08_r15_provider_rating_wins` | rating ON + allowing seam + a provider rating already set: provider fields unchanged, `jsonld_rating` added | RED | 2.7 |
| R16 | `test_d08_r16_no_derive_on` | `build_comparison_response` with rating ON and a product with no rating: `pd["rating"]` stays None, no `rating_derived` key, overview/reviews rating None, reviews `rating_source` None | RED | 2.7 step 4 |
| R17 | `test_d08_r17_reviews_projection_jsonld_rating` | ON: `reviews.products[i].jsonld_rating` present iff the product carries it; overview keys unchanged | RED | 2.7 step 4 |
| R18 | `test_d08_r18_prompt_variant` | `REVIEWS_EXTRACTION_SYSTEM_NO_RATING` exists, equals the base constant with exactly the two lines removed, contains `SEARCH_RESULTS_GUARD`; the reviews call sends it when ON (client recorder) | RED | 2.7 step 5 |
| R19 | `test_d08_r19_normaliser_belt` | ON: a model payload with `average_rating` 4.2 and `total_reviews` 900 normalises to None / None | RED | 2.7 step 5 |
| R20 | `test_d08_r20_judgeme_deleted` | `find_spec("app.services.judgeme_service") is None`; no file under app/ or scripts/ contains `judgeme_service`; `tests/fixtures/judgeme_c5` absent | RED | 3.6 |
| R21 | `test_d08_r21_candidate_additions_on` | image ON: cand carries `size` for a node with `size`; rating ON: `aggregate_rating["best_rating"]` for bestRating 10 | RED | 2.5 |

PIN rows (green at base; B1 rule: FULL configuration, both flags OFF in every falsy spelling, the seam patched to an ALLOWING recorder, `ENABLE_WIDE_CANDIDATE=true`, both exact-gate modes, `ENABLE_DATA_GUARDS_V2` both ways):

| # | test | assertion |
|---|---|---|
| P1 | `test_d08_p1_reduced_result_off_literal` | the `extract_price_from_html` result for a node carrying image/gtin/sku/size/aggregateRating equals the base LITERAL dict (recorded in the file) in both gate modes |
| P2 | `test_d08_p2_pharmacy_off_literal` | `_try_pharmacy_urls` returns the base literal dict |
| P3 | `test_d08_p3_candidate_off_literal` | the `extract_jsonld_price` candidate equals the base literal (no `size`, no `best_rating`) |
| P4 | `test_d08_p4_piggyback_off` | through the real `_fetch_product_data` (the copied D03 harness): an http, an https first-party, an off-allowlist and a padded page image each give the base outcome (recorded literals), with `ENABLE_DATA_GUARDS_V2` unset and true |
| P5 | `test_d08_p5_rating_golden_sequence` | over `tests/fixtures/s81_d08_rating_flag_off_golden.json` (12 synthetic product results: provider rating present/absent x reviews average present/absent/out-of-range/string x a price carrying/lacking `_jsonld_facts`), the ordered tuples `(rating, review_count, rating_verified, rating_source, rating_derived, jsonld_rating-present)` after the rating block AND the overview/reviews projections equal the golden, under unset / "false" / "0" / "off" / "" |
| P6 | `test_d08_p6_seam_never_called_off` | across P1-P5 the allowing recorder seam has zero calls |
| P7 | `test_d08_p7_prompt_off_sha` | `sha256(REVIEWS_EXTRACTION_SYSTEM)` equals the base literal digest; the reviews call sends that exact string with the flag OFF |
| P8 | `test_d08_p8_normaliser_off` | `average_rating` 4.2 survives, `total_reviews` untouched |
| P9 | `test_d08_p9_wide_pin_both_states` | `test_the_wide_keys_do_not_leak...`'s eight-key absence holds with BOTH D08 flags ON as well (`image_url` and `_jsonld_facts` are not wide keys) |

### 6. Mutation table (byte copies, the killing rows via `pyt.py -k`, bound 600, restore + sha256)

| id | mutant | killed by |
|---|---|---|
| D-M1 | image flag default "true" | P1, P6 |
| D-M2 | rating flag reader cached at import | R1 |
| D-M3 | `allowed_image_url` accepts http | R3, R9 |
| D-M4 | raster check dropped | R3 |
| D-M5 | deny check behind `data_guards_v2_enabled()` | R3 |
| D-M6 | first-party match drops the `www.` normalisation | R2 |
| D-M7 | gtin check digit not verified | R4, R6 |
| D-M8 | `rules_allow` evaluates only `star` | R12 (qarenbot row) |
| D-M9 | expiry ignores `next_reread` | R12 (expired) |
| D-M10 | `rules_allow` fails OPEN on a malformed rule | R10 |
| D-M11 | channel 1 overwrites a provider rating | R15 |
| D-M12 | GPT fallback still applied ON | R13 |
| D-M13 | derive loop not guarded | R16 |
| D-M14 | stamp not gated (call outside the flag check) | P1, P6 |
| D-M15 | piggyback ON falls through to the base http branch | R9 |
| D-M16 | prompt variant keeps `total_reviews` | R18 |
| D-M17 | rating not rescaled by best_rating | R7 |
| D-M18 | `_jsonld_facts` written without the `_` prefix (as `jsonld_facts`) | P9 / R5 |

### 7. Comm set (the union rule; zero-regression gate)

Classes (each re-derived by GREEN at HEAD with the S80 `comm_set` recipe; the RED agent records the base set):
1. Module and symbol reference grep over `tests/*.py` for every edited or deleted module: `price_service` (201 files measured with `git grep -l`), `structured_comparison_service` (192), `extraction_service` (121), `response_builder` (68), `image_service` (10), `judgeme_service` (1, deleted with it), `seed_spec_spine` (3), plus `deny_hosts`, `robots_eval`, `robots_registry`, `merchant_registry` (the leaf's imports), `rating_service`, `review_service`, `fact_check_service` (the rating consumers) and the symbols `_widen_jsonld_candidate`, `_jsonld_product_rating`, `_try_pharmacy_urls`, `extract_price_from_html`, `extract_jsonld_price`, `public_price_view`, `_apply_gpt_review_aggregate_fallback`, `derive_rating_from_scores`, `REVIEWS_EXTRACTION_SYSTEM`, `REVIEWS_EXTRACTION_PROMPT`, `_normalize_review_response`.
2. UNION the source-scanning pins: `test_model_config.py`, `test_model_config_enforced.py`, `test_prompt_fence.py`, `test_u3c_store_false_pin.py`, `test_start_command*.py`, `test_migration_index_predicate_immutability.py`, `test_openai_key_log_hygiene_s69.py`, `test_sentry_channels_u8d_unit.py`, and every test reading app/ or scripts/ as SOURCE (string paths, `Path(<module>.__file__)`, `inspect.getsource`, `ast.parse(read_text())`, `glob`/`rglob`/`os.walk`/`listdir`/`scandir` walkers, "app" path-segment joins, `.github` readers, conftest source readers).
3. UNION every importer of an edited module, `app/main.py` included (price_service, scs, response_builder and extraction_service are imported by app.main transitively: every test importing `app.main` or `TestClient(app)` joins).
4. UNION the CLAUDE.md readers (CLAUDE.md changes): `test_ci_gates.py` (:934, :1392), `test_behavior_dimension_translation.py` (:226), `test_s81_s04_spend_breaker.py` (:1657), `test_s81_s08b_gate_rows.py` (:282), `test_s81_s08b_legacy_fingerprint.py` (:801).
5. UNION the prompt-digest recorder importers (`tests/w4_11_prompt_digest_recorder.py` users) and `tests/fixtures/w4_11_prompt_render_digests.json` readers (the reviews prompt module changes).
6. MINUS the four `test_precommit_hook*.py` (no `.githooks` change).
Measured seed: the single union grep (`price_service|structured_comparison_service|response_builder|extraction_service|scrapedo_service|image_service|judgeme_service|seed_zyte_luxury|seed_spec_spine|source_router|robots_eval|robots_registry|merchant_registry|deny_hosts|rating_service|review_service|fact_check_service|app\.main|from app import main|Path(.*app|rglob|os.walk|scandir|listdir|inspect.getsource|ast.parse`) over `tests/*.py` minus precommit = 539 files at e7c81956 (this already holds S81-23's seeds): the group's comm set is about 540 files, about 22 chunks of 25 per side. LC-6: GREEN reuses a cached base record under `<scratchpad>/harness/base_records/<main sha>/<set sha256>.txt` when the set hash matches, else computes it once (a detached scratch worktree at the base, no junction).
7. The fourteen backend-scanning CLIENT jest fences run BY PATH from SmartCompareApp through the orchestrator's junction at GREEN and at the rebase (the footprint touches app/, scripts/ and CLAUDE.md). Measured reader of a D08-edited file: `clientTruth/medicalNote.s74.test.tsx:230` reads `app/services/extraction_service.py` (the `_PHARMACY_TABLET_TOKENS` set; D08 does not move it). No fence reads price_service, scs, response_builder, scrapedo_service, seed_zyte_luxury, seed_spec_spine or judgeme_service (`git grep` over `SmartCompareApp/__tests__`; `ResultsScreen.timeout.test.tsx:258` is a comment).

#### 7.4 Gates for GREEN (cheapest first)

1. `py_compile` + `ruff check --select E9,F63,F7,F82 --no-cache` on every changed .py; JSON load of the golden; ASCII/LF check of new files; `git diff --stat` content lines only (CRLF kept).
2. Unit: `tests/test_s81_d08_jsonld_widen.py` with the flags unset, then with both ON exported, then each alone (bound 600 each).
3. The corpus gate, base and head in one sitting, the same command both sides: `python scripts/verify_flag_byte_identity.py --proof-root C:/Users/SynAckITPC/Documents/AI/sc-scraper-proof/_proof --flags ENABLE_IMAGE_PIPELINE_V2,ENABLE_JSONLD_RATING --out <notes>/gate_<side>.json` (base = a detached scratch worktree at the base): the two OVERALL SHA256 lines must be equal (records n=414, calls=1656 expected). Information run: `--flags-on ENABLE_IMAGE_PIPELINE_V2,ENABLE_JSONLD_RATING --compare gate_head.json` and report the differing-record count (every difference must be an added `image_url` / `_jsonld_facts` key, never an amount, currency or source_method change).
4. The pins of 4.2 by file (bound 600), then the CI-order set (section 12.2, bound 1200).
5. The comm set base vs head, `comm -13` of the sorted FAILED ids EMPTY; the fourteen client fences by path.
6. Personal-data and secret sweep of the added lines (Python, counts only).

### 8. CLAUDE.md row (GREEN writes it in the S81-G1 block; wording may tighten, content may not) and owner steps

- `ENABLE_IMAGE_PIPELINE_V2` + `ENABLE_JSONLD_RATING` (D08, `app/services/jsonld_widen.py::image_pipeline_v2_enabled` / `::jsonld_rating_enabled`, read PER CALL, default OFF, new names so unset in production by construction). **Effect ON (image):** the JSON-LD price capture (`extract_price_from_html` JSON-LD branch and `_try_pharmacy_urls`) carries the first Product image that is https, on a public host, raster by extension, not on DENY_HOSTS, and first-party / a named platform CDN (`IMAGE_CDN_HOSTS`) / an `OFFICIAL_BRAND_DOMAINS` host, as `price["image_url"]`, plus `price["_jsonld_facts"]` {gtin (8/12/13/14 digits with a valid check digit), sku, the node's size text} for the KB writers; the Tier 1.5 piggyback promotes a page image only under the same policy (http refused). **Effect ON (rating):** the reviews prompt no longer asks for `average_rating` / `total_reviews` and the normaliser drops them; the GPT review-aggregate fallback and `derive_rating_from_scores` no longer run (an unknown rating stays unknown); a channel-1 rating (the Product node's own aggregateRating, rescaled to 5) fills an EMPTY rating slot and is always reported additively as `reviews.products[i].jsonld_rating`, only from a host whose persisted robots record is live, fresh (before `next_reread` + 24 h), allows the PDP path for BOTH QarenBot and `*`, and has no parked challenge; the record reader is the seam `ROBOTS_ENTRY_LOOKUP`, which returns nothing until D14 LIVE-ROBOTS wires it, so before D14 the rating flag only REMOVES fabricated ratings. **Flag OFF:** byte-identical (P1-P9, the rating golden `tests/fixtures/s81_d08_rating_flag_off_golden.json`, the corpus gate OVERALL SHA256 equal base/head). **Also (unflagged, R-A1 c):** `judgeme_service.py` and its pin file deleted (zero importers; judge.me is forbidden by the licensing ruling). **Preconditions:** `ENABLE_WIDE_CANDIDATE` ON (default ON; with it OFF the candidate carries no image / identifiers / rating and both flags are inert). **Stated limits:** section 9. **Canary (after approval, its own window each):** image: the share of compares whose `overview.products[i].image_url` is a page image (stage timings unchanged; image failures from the client's `image_load_failed` event once SF1 lands); rating: the count of products with a non-null `rating` falls (fabricated ones gone) and no `rating_source.extract_method == "gpt_review_aggregate"` appears. **Rollback:** unset the variable (cached prices keep the internal keys for their TTL, inert OFF).
- Owner steps: none to merge; flip only after approval with the owner's yes, image first, rating after D14 if a channel-1 rating is wanted.
- In-place rewrites: CLAUDE.md:348 the clause "`ENABLE_JUDGEME_HTML_REVIEWS` (judge.me server-HTML reviews, ~39 pages / 27-of-34 Gulf, `ddead8d`)" -> "`ENABLE_JUDGEME_HTML_REVIEWS` (judge.me server-HTML reviews; the module was DELETED by D08 (S81-G1): zero importers, judge.me forbidden by the licensing ruling)"; CLAUDE.md:377 runbook step (2) "`ENABLE_YOTPO_REVIEWS` + `ENABLE_JUDGEME_HTML_REVIEWS`" -> "`ENABLE_YOTPO_REVIEWS` (judge.me deleted by D08)", the CAVEAT sentence keeps Yotpo and says judgeme_service.py was deleted.

### 9. Stated limits

- L1 No channel-1 rating before D14: the seam returns nothing (2.3); the rule is complete and pinned with synthetic records.
- L2 The image allowlist is first-party + four platform CDNs + brand domains; a retailer whose JSON-LD image sits on another CDN (Cloudinary, imgix, Akamai image hosts) loses the page image and the eager cascade result stands (a measured follow-up widens the tuple).
- L3 The raster check reads the path extension only: an extension-less CDN URL that serves a JPEG is refused; a `.jpg` path that serves HTML is accepted (no fetch by design; the client renders the placeholder on error).
- L4 Cached prices written while ON carry `image_url` / `_jsonld_facts` for their TTL (24 h converted / 7 d genuine) after a rollback; the facts are stripped from the public price with the exact gate ON (production) and the piggyback OFF promotes such an `image_url` exactly as it promotes a Zyte-seeded one today.
- L5 Cached reviews keep a model `average_rating` until their TTL; ON it is never promoted, but `fact_check` still reads it for a cache hit.
- L6 A rescaled rating keeps one decimal; `worstRating` is ignored.
- L7 `rating_verified` is False for a channel-1 rating (a single retailer's aggregate, not the cross-seller consensus).
- L8 `_jsonld_facts.size` is captured, not used: the pair fairness still reads `price["size"]` from the name / title stamp.
- L9 The corpus gate exercises only `extract_price_from_html` (not the piggyback, the rating block or `_try_pharmacy_urls`): those rest on P2-P6.

### 10. Out of scope

D14's live robots lookup and attempt hooks; widening the S81-15 memo columns; the KB writes of the facts (S81-17); Serper Images timeouts, the early image stash, the Knowledge-Graph identity check and the Bright Data mapper (the rest of the PLAN_S80 B7 list, re-scoped by the pivot); Yotpo; `zyte_service.ZYTE_STORES`; any client change (build 3 already renders `image_url` / a null rating).

### 11. Open questions (for RULINGS_S81_G1)

- Q-D08-1 (Q1): the seam with no reader (recommended: SAFE, small, D14 wires it) versus widening `merchant_registry.READ_COLUMNS` with `robots,challenge` now (touches the merged S81-15 module and its frozen rows; the memo would carry up to 3 MB of rules lists per process).
- Q-D08-2 (Q4): channel 1 fills only an EMPTY slot (recommended) versus "channel 1 before Tier 1" (a single retailer would override the cross-seller consensus).
- Q-D08-3 (Q5): the `IMAGE_CDN_HOSTS` constant as written (recommended; GREEN measures the distribution as information) versus a data file.
- Q-D08-4 (Q2): delete (recommended, measured zero importers) versus a stub.
- Q-D08-5: E2 applies only if `test_prompt_fence.py` enumerates prompt names; GREEN reports which.

## Unit S81-23 BYPASS-RETIRE

### 1. Base state (measured at e7c81956)

| site | file:line | fact |
|---|---|---|
| module docstring | scrapedo_service.py:1-5 | "Scrape.do renders JavaScript pages with residential proxies and anti-bot bypass." |
| super cache | scrapedo_service.py:38-47 (comment), :47 `_SUPER_FLAGS = None` | "Cached at process init ... tests reset via reset_super_flags_cache()" |
| params | scrapedo_service.py:50-63 `_super_params` | first call reads `os.environ.get("SCRAPEDO_SUPER", "false").lower() == "true"` (exact "true" after lower, no strip: "TRUE" is ON, "1"/"yes"/" true" are OFF) and `SCRAPEDO_GEOCODE` (default "bh"); caches `{"super": "true", "geoCode": <code>}` or `{}` |
| gate | scrapedo_service.py:66-75 `_super_enabled` | `bool(_super_params())` |
| test hook | scrapedo_service.py:78-82 `reset_super_flags_cache` | sets `_SUPER_FLAGS = None` |
| requests | scrapedo_service.py:129 (`render_page`), :185 (`render_page_with_status`) | `params={"token", "url", "render": "true", **_super_params()}` |
| routing | source_router.py:807-820 `_super_routing_enabled` (lazy import of `_super_enabled`, fail-closed); :823-858 `get_sources_for_category` drops a `requires_super` row unless enabled (:850) | the lone `requires_super` row is `sephora.me` (:211-221, Akamai-walled, `status="provider-test-candidate"`) |
| other readers | scripts/ab_render_providers.py:18-33, :85; `.qa-bias-rerun/_sephora_provider_test.py` (tracked); tests: `test_fragrance_content_quality.py:866-1119` (11 rows set `SCRAPEDO_SUPER`), `test_s81_s15_registry_robots.py:71, :241, :251`, `test_sephora_provider_test_classify.py`, `test_fan_out_budget_env.py` (reloads the module), `test_bahrain_source_matrix_coverage.py`, `test_source_descriptor_fields.py`, `test_source_usage_field.py`, `test_cascade_order_regression_qa.py` | |
| render wave | structured_comparison_service.py:2289-2360 `_scrapedo_scraper` | records a `cf_block` outcome on a challenge body and does NOT stop the render wave: "challenge = stop" is not enforced live (D14) |
| Zyte seed | scripts/seed_zyte_luxury.py:1-18 docstring "the sephora-only PROOF"; `LUXURY_PAIRS` :58-69 (10 pairs, all routed by the cascade's Zyte tier, whose `zyte_service.ZYTE_STORES` :234-239 holds ONLY `sephora.me`); `TRUTH_CRITICAL_SEEDS` :81-100 (one entry, `domain: "sephora.me"`, the pinned Luna Rossa Carbon PDP) | every seed target is sephora.me |
| seed pins | `tests/test_zyte_seed_variant.py` (497 lines; 7 rows read the Carbon entry: :117, :131, :144, :169, :447, :470, :486) and `tests/test_seed_zyte_guard.py:171-198` (`--only luna rossa carbon`) | |
| #93 | docs/investigations/2026-08-25-scraper-bakeoff.md:23-33; S72 ISSUE_TRIAGE:85 | "Re-test whether curl_cffi reads sephora.me /bh-en" (20+ samples over 24 h from Railway egress) |
| CLAUDE.md | :141 "- **Firecrawl** (Tier 1.5a, ..." (its sentence "**Scrape.do** (Tier 1.5d, residential proxies, only when curl fetched HTML w/ no price)."); :142 "- **`curl_cffi` `impersonate="chrome"` defeats most Cloudflare/TLS-fingerprint walls** ..." ending "(Proven 2026-06-25 BH/GCC discovery: cracked noon/extra/al-dawaa/nahdi/panda/sharafdg + the genuine-BHD supplement giants sporter/drnutrition.)"; :338 "**Price Scraping:** ..." with "`ZYTE_API_KEY` (Zyte API render - cracks Akamai+BH-geo for luxury; ...)"; :805-808 "- **`curl_cffi` READ sephora.me** ..." (#93 specifies 20+ samples ...); :813 "controls curl cracks free"; :818-820 "- **Scrape.do - narrow keeper**, behind a "curl returned a WAF block" trigger only. Its single real win was eros.ae (Link11 491, blocks curl+Playwright+crawl4ai)." | |
| idiom / EOL | house idiom as D08 1.6; `scrapedo_service.py`, `seed_zyte_luxury.py`, `CLAUDE.md`, both seed test files `i/lf w/crlf` | |
| base pass | the header run (all six files green) | |

### 2. Contract

#### 2.1 Q6: the transition semantics (argued)

```python
def scrapedo_super_enabled() -> bool:
    raw = os.getenv("ENABLE_SCRAPEDO_SUPER")          # first statement, per call
    if raw is None:                                   # unset: today's rule, now read per call
        return os.environ.get("SCRAPEDO_SUPER", "false").lower() == "true"
    return raw.strip().lower() in ("true", "1", "yes", "on")
```
- Unset `ENABLE_SCRAPEDO_SUPER` = TODAY'S behaviour for every value of `SCRAPEDO_SUPER` (the exact base expression, including "TRUE" ON and "1" OFF); set = the new flag wins in both directions (`false` is an immediate kill switch even while `SCRAPEDO_SUPER=true`).
- Why not the clean cut (new flag alone, default OFF): production's `SCRAPEDO_SUPER` is UNKNOWN (owner item 5). If it is `true`, a clean cut changes production at deploy (sephora.me routing and the super params stop) with no flag flipped: not byte-identical, against the App Review rule. The transition form is byte-identical in BOTH states, and the owner's names-only unset of `SCRAPEDO_SUPER` on web (immediate, OWNER_ACTIONS item) is the actual retirement lever, exactly as PLAN_S81 :140 states ("the new flag defaults to today's super-mode behaviour until the owner's env change").
- The stated post-approval default flip (S81-23b, one hunk): after the dated ledger line "SCRAPEDO_SUPER unset on web", the legacy branch is deleted so unset = OFF regardless of the legacy name.
- `_super_params()` per call: `{}` when `scrapedo_super_enabled()` is False, else `{"super": "true", "geoCode": os.environ.get("SCRAPEDO_GEOCODE", "bh")}` (a fresh dict per call). `_super_enabled()` returns `scrapedo_super_enabled()` (the source_router reader is unchanged). `_SUPER_FLAGS` stays declared and `reset_super_flags_cache()` stays callable (a no-op apart from `_SUPER_FLAGS = None`) because 20+ test call sites, `scripts/ab_render_providers.py` and the tracked `.qa-bias-rerun` script call it.
- Observable difference vs base (stated, nil in production): base reads once per process; a change of `SCRAPEDO_SUPER` / `SCRAPEDO_GEOCODE` inside one process now takes effect on the next call (Railway restarts on a variable change, so production cannot observe it).
- The docstring (:1-5) and the comment block (:38-46) are rewritten neutrally: "Scrape.do renders JavaScript pages (Tier 1.5d) for render-only SPA pages when curl fetched HTML with no price. Its super / residential-proxy mode is retired under the robots policy (challenge = stop; owner decision 12): it runs only when `ENABLE_SCRAPEDO_SUPER` is true, or, while that name is unset, when the legacy `SCRAPEDO_SUPER=true` is still set (S81-23 transition)."

#### 2.2 Q7: what `seed_zyte_luxury.py` keeps (argued)

Every seed target is sephora.me (1.x), so removing the sephora.me seed EMPTIES both lists: `LUXURY_PAIRS: List[str] = []`, `TRUTH_CRITICAL_SEEDS: List[Dict[str, Any]] = []`, each with a comment "retired 2026-10-29 by S81-23 (owner decision 12): sephora.me is Akamai-walled; robots policy, challenge = stop". KEEP the scaffold (recommended) rather than delete: (a) the plan's unit text edits "the list"; (b) the startup-key guard and its pins (`tests/test_seed_zyte_guard.py`, the paid-call leak class) stay meaningful for any future, robots-allowed, non-challenged target added with a ToS verdict; (c) deletion would add stale-reference hunks in app/ comments (price_service.py:8834, scs:1137, scs:6988, zyte_service.py:12) and CLAUDE.md (:341) for no runtime gain; (d) with empty lists `main()` makes zero Zyte calls. The docstring states the script seeds nothing. `zyte_service.ZYTE_STORES` keeps its sephora.me row (out of scope; the live Zyte tier stays behind `ENABLE_ZYTE_RENDER`, default OFF, never set on web per CLAUDE.md:341).

#### 2.3 Flag-OFF identity

`ENABLE_SCRAPEDO_SUPER` unset: for `SCRAPEDO_SUPER` in {unset, "false", "true", "TRUE", "1", " true"} and `SCRAPEDO_GEOCODE` in {unset, "ae"}, the request params of both render functions and `get_sources_for_category` for makeup / skincare / fragrances / haircare equal base (P rows below, the full configuration present: `SCRAPEDO_API_TOKEN` synthetic, an httpx recorder). The seed-list change is off-clock only (no app/ reader of the lists).

#### 2.4 Failure table

| state | params | sephora.me routed |
|---|---|---|
| new unset, legacy unset/false | base `{token,url,render}` | no |
| new unset, legacy "true"/"TRUE" | base + super + geoCode | yes |
| new "false"/"0"/"off"/"" | base | no |
| new "true"/"1"/"yes"/" ON " | base + super + geoCode | yes |
| the source_router lazy import fails | base | no (fail-closed, unchanged) |

### 3. Change list (GREEN, byte copies first)

1. `app/services/scrapedo_service.py`: docstring :1-5 and comment :38-46 rewritten (2.1); `scrapedo_super_enabled()` added before `_super_params`; `_super_params` body per call; `_super_enabled` returns `scrapedo_super_enabled()`; `reset_super_flags_cache` kept (docstring: "kept for compatibility; the flags are read per call since S81-23").
2. `scripts/seed_zyte_luxury.py`: the docstring :1-18 (the script is retired, seeds nothing, kept as the guarded scaffold), both lists emptied (2.2).
3. `tests/test_zyte_seed_variant.py` E-rows (4.1).
4. `tests/test_seed_zyte_guard.py` E-row (4.1).
5. CLAUDE.md (section 8).
6. NEW `tests/test_s81_s23_bypass_retire.py` (RED, frozen).
No other file (source_router, zyte_service, price_service, scs untouched).

### 4. Existing pins

#### 4.1 Deliberate changes

| # | pin | today | change | reason |
|---|---|---|---|---|
| E3 | `tests/test_zyte_seed_variant.py::test_carbon_truth_entry_shape`, `::test_carbon_cache_key_parity`, `::test_carbon_parser_axis_presence_gap_documented`, `::test_seed_truth_entry_writes_cache_at_parity_key`, `::test_seed_truth_entry_write_gate_refusal_no_write`, `::test_seed_truth_entry_fetch_miss_pends` | read the Carbon entry from `TRUTH_CRITICAL_SEEDS` | a module-level SYNTHETIC entry `_SEED_ENTRY` (the same dict literal the script held, `domain` and `pdp_url` kept as test data, the script no longer carries it) passed to `_seed_truth_entry` / `_truth_label` / the key builder; `test_carbon_truth_entry_shape` becomes `test_truth_seed_lists_are_retired` asserting both lists are empty | Q7 |
| E4 | `tests/test_zyte_seed_variant.py::test_select_targets_only_scoping` | default lists | the same assertions over explicit `pairs=` / `truth=` synthetic lists (the function already takes them, :105-109) | Q7 |
| E5 | `tests/test_seed_zyte_guard.py::TestKeyPresentStillSeeds::test_a_key_present_at_startup_still_runs_the_seed` | `--only luna rossa carbon` reaches the Zyte fetch | `monkeypatch.setattr(seeder, "TRUTH_CRITICAL_SEEDS", [<synthetic entry>])` first, so the guard row still proves a startup key reaches the fetch (one trapped attempt, `{"genuine": 0, "pending": 1}`) | Q7 |

#### 4.2 Must stay green and unedited

`tests/test_scrapedo_service.py` (all 25+), `tests/test_fragrance_content_quality.py` (the 11 super rows :866-1119 run with `ENABLE_SCRAPEDO_SUPER` unset, so they ARE the transition pins), `test_s81_s15_registry_robots.py`, `test_sephora_provider_test_classify.py`, `test_fan_out_budget_env.py`, `test_bahrain_source_matrix_coverage.py`, `test_source_descriptor_fields.py`, `test_source_usage_field.py`, `test_cascade_order_regression_qa.py`, `test_api_budget_service.py`, the other scrapedo readers (section 7) and the CLAUDE.md readers.

### 5. RED tests: `tests/test_s81_s23_bypass_retire.py` (new; pure ASCII; hermetic)

Autouse fixture: `delenv` `ENABLE_SCRAPEDO_SUPER`, `SCRAPEDO_SUPER`, `SCRAPEDO_GEOCODE`; set `SCRAPEDO_API_TOKEN` to a synthetic word built at run time; call `reset_super_flags_cache()` before and after; httpx patched at `app.services.scrapedo_service.httpx.AsyncClient` with a recorder (the `test_scrapedo_service.py:18-21` pattern). `scrapedo_super_enabled` is read with `getattr(module, "scrapedo_super_enabled", None)` and asserted callable.

| # | test | assertion | at base | satisfied by |
|---|---|---|---|---|
| R1 | `test_s23_r1_reader_exists_and_wins` (param: new in {"true","1","yes"," ON "} x legacy {unset,"false"}) | True | RED (reader absent -> AssertionError) | 2.1 |
| R2 | `test_s23_r2_new_false_kills_legacy` (param: new in {"false","0","off",""} with legacy "true") | `_super_params() == {}` and `_super_enabled() is False` | RED (base returns the super params) | 2.1 |
| R3 | `test_s23_r3_per_call_no_reset` | legacy "true" -> params carry super; set new "false" WITHOUT calling the reset hook -> `{}` on the next call | RED (base cache) | 2.1 |
| R4 | `test_s23_r4_render_params_new_off` | both render functions with new "false" + legacy "true": params exactly `{token, url, render}` | RED | 2.1 |
| R5 | `test_s23_r5_routing_new_off` | new "false" + legacy "true": sephora.me absent for makeup/skincare/fragrances; new "true" + legacy unset: present | RED | 2.1 |
| R6 | `test_s23_r6_seed_lists_retired` | `LUXURY_PAIRS == []`, `TRUTH_CRITICAL_SEEDS == []`, and no seed string mentions "sephora" | RED | 2.2 |
| R7 | `test_s23_r7_main_makes_no_zyte_call` | startup key present, no args: `main()` returns `{"genuine": 0, "pending": 0}` and the socket recorder saw zero attempts | RED (base attempts the Carbon fetch) | 2.2 |
| R8 | `test_s23_r8_claude_md_neutral` | CLAUDE.md contains none of: "defeats most Cloudflare", "cracks Akamai", "residential proxies, only when", "#93 specifies 20+ samples", "controls curl cracks"; contains the column-0 heading "**SESSION 81 flags (S81-G1 PRICE-PIPELINE" and the name `ENABLE_SCRAPEDO_SUPER` inside it and the policy file name `2026-08-31-robots-unreadable-ruling.md` inside it | RED | 3.5 |
| R9 | `test_s23_r9_docstring_neutral` | `scrapedo_service.__doc__` does not contain "anti-bot bypass" | RED | 2.1 |

PIN rows (green at base, full configuration: token, geoCode "ae" where stated, recorder):

| # | test | assertion |
|---|---|---|
| P1 | `test_s23_p1_unset_matches_base_params` (param legacy: unset, "false", "true", "TRUE", "1", " true") | params of both functions equal the base literal per value (super + geoCode exactly for "true"/"TRUE") |
| P2 | `test_s23_p2_unset_matches_base_routing` (same params) | the bahrain-tier routed domains for the four categories equal the base literal lists (recorded in the file) |
| P3 | `test_s23_p3_reset_hook_callable` | `reset_super_flags_cache()` returns None and changes no outcome |
| P4 | `test_s23_p4_geocode_default` | legacy "true", geoCode unset -> "bh" |

### 6. Mutation table

| id | mutant | killed by |
|---|---|---|
| S-M1 | unset new name treated as OFF (the clean cut) | P1 ("true"), P2 |
| S-M2 | legacy read gains `.strip()` | P1 (" true") |
| S-M3 | legacy read accepts "1" | P1 ("1") |
| S-M4 | new flag read once and cached | R3 |
| S-M5 | new "false" ignored when legacy "true" | R2, R4, R5 |
| S-M6 | `_super_enabled` still reads the cache | R5 |
| S-M7 | a seed entry left in `TRUTH_CRITICAL_SEEDS` | R6, R7 |
| S-M8 | geoCode default changed | P4 |

### 7. Comm set

Module/symbol grep for `scrapedo_service` (16 test files), `seed_zyte_luxury` (3), the symbols `_super_params`, `_super_enabled`, `reset_super_flags_cache`, `SCRAPEDO_SUPER`, `requires_super`, `_super_routing_enabled`, `get_sources_for_category`, `LUXURY_PAIRS`, `TRUTH_CRITICAL_SEEDS`; UNION every importer of `scrapedo_service` (price_service and scs import it at module top: price_service.py:39, scs:77, so every importer of those and of `app.main` joins: already inside the D08 set); UNION the source-scanning pins; UNION the CLAUDE.md readers (D08 7.4). The group set of section 12 contains all of it. The fourteen client fences: none reads scrapedo_service, seed_zyte_luxury or the CLAUDE.md lines touched (measured grep, D08 section 7 item 7); they run by path under the group rule anyway.

### 8. CLAUDE.md row and owner steps

- `ENABLE_SCRAPEDO_SUPER` (S81-23, `app/services/scrapedo_service.py::scrapedo_super_enabled`, read PER CALL, a new name so unset in production by construction). Scrape.do's super / residential-proxy mode (and with it the routing of the lone `requires_super` row, sephora.me) is retired under the robots policy (`docs/policies/2026-08-31-robots-unreadable-ruling.md`: a challenge is a stop; owner decision 12). **Transition semantics:** with this name UNSET the legacy `SCRAPEDO_SUPER=true` still turns super mode on (byte-identical to the pre-S81-23 code for every legacy value, now read per call instead of once per process); with it SET, it wins in both directions (`false` is an immediate kill switch). **Owner step (names only, immediate):** unset `SCRAPEDO_SUPER` on `web` (and any other service that has it) and record a dated ledger line; never set `ENABLE_SCRAPEDO_SUPER=true`. **Stated post-approval change (S81-23b):** after that ledger line, the legacy branch is deleted so an unset name means OFF. The plain render wave (Firecrawl / Scrape.do without super) stays for render-only SPA rows that are not challenge walls (megamart, alosra, noon); it does not yet stop on a detected challenge (live enforcement is D14). `scripts/seed_zyte_luxury.py` seeds nothing since S81-23 (its sephora.me targets were removed); #93 (re-test curl on sephora.me) is closed as won't-do.
- In-place rewrites (first words; GREEN keeps the surrounding text):
  - :141 the clause "**Scrape.do** (Tier 1.5d, residential proxies, only when curl fetched HTML w/ no price)." -> "**Scrape.do** (Tier 1.5d, a JavaScript render service, only when curl fetched HTML with no price; its super / residential mode is OFF behind `ENABLE_SCRAPEDO_SUPER` since S81-23)."
  - :142 -> "- **`curl_cffi` fetches with a browser TLS fingerprint (`impersonate="chrome"`)**; a page that looks `render_required` is often readable as plain HTML, and the platform JSON API (`/products.json`, `/wp-json/wc/store/products`, Algolia, Unbxd, Hybris OCC `/occ/v2`, Adobe-Commerce GraphQL) often answers where the HTML PDP renders client-side: probe the API endpoint before declaring a render-tier gap. **Robots policy:** a host whose robots.txt disallows the path or is unreadable, or that serves a challenge (Cloudflare / Akamai interstitial), is a stop, never a target (`docs/policies/2026-08-31-robots-unreadable-ruling.md`; the S81-15 cron records it, live enforcement is D14); blocked hosts go to the registry's blocked list and the operator path. The live adapter user agent is an open owner ruling after the M6 named-UA dry run. (2026-06-25 BH/GCC discovery: price reads on noon / extra / al-dawaa / nahdi / panda / sharafdg and the BHD supplement sellers sporter / drnutrition.)"
  - :338 the clause "`ZYTE_API_KEY` (Zyte API render - cracks Akamai+BH-geo for luxury; used ONLY by the off-clock seed, NOT the live path)" -> "`ZYTE_API_KEY` (Zyte API render with BH geolocation; used only by the off-clock `scripts/seed_zyte_luxury.py`, which seeds nothing since S81-23; never the live path)".
  - :805-808 the bullet "- **`curl_cffi` READ sephora.me** ..." -> "- **sephora.me (2026-08-25, one sample):** a plain curl read returned the JSON-LD price once while three headless browsers got 403. The host is Akamai-protected, so under the robots policy it is not a target: #93 (the 20-sample re-test) was closed as won't-do by S81-23 and the Zyte sephora.me seeds were retired."
  - :813 "controls curl cracks free" -> "controls curl reads free".
  - :818-820 the bullet "- **Scrape.do - narrow keeper**, ..." -> "- **Scrape.do - narrow keeper** for render-only pages. Its one unique capture on 2026-08-25 was a host whose WAF blocked curl, Playwright and crawl4ai (Link11 491); under the robots policy a WAF block is a stop, so that capture class is retired. The other 3 duplicated free curl results at 9-50x latency, two of them EXCEEDING the 15s live clock."
- #93 closing text (in the PR body; the orchestrator posts it): "Closed as won't-do (S81-23, owner decision 12, 2026-10-22). sephora.me /bh-en is Akamai-protected; under the robots policy (docs/policies/2026-08-31-robots-unreadable-ruling.md) a challenge is a stop, not a target, so a 20-sample re-test of whether curl gets through would only measure how to pass a wall we no longer try to pass. The Zyte sephora.me seeds were removed from scripts/seed_zyte_luxury.py and Scrape.do's super / residential mode now runs only behind ENABLE_SCRAPEDO_SUPER (default: the legacy SCRAPEDO_SUPER, which the owner unsets). sephora.me products reach the knowledge base only through the operator path or a partner feed."

### 9. Stated limits

- L1 Until the owner's unset lands as a dated ledger line, production super mode equals whatever `SCRAPEDO_SUPER` holds today (unknown); the code alone retires nothing (by design: byte identity).
- L2 The plain render wave still renders a page whose curl fetch was a challenge (it records `cf_block`); D14 stops it.
- L3 `zyte_service.ZYTE_STORES` keeps sephora.me; `ENABLE_ZYTE_RENDER` on web would still reach it (default OFF).
- L4 `scripts/ab_render_providers.py` and the tracked `.qa-bias-rerun/_sephora_provider_test.py` set `SCRAPEDO_SUPER=true` in their own process; with `ENABLE_SCRAPEDO_SUPER` unset they behave as before (manual, off-clock, not CI).
- L5 A per-call read means a mid-process change of the legacy variable now applies on the next call (no production effect).

### 10. Out of scope

Deleting the super code path or the `requires_super` field (S81-23b after the ledger line); `zyte_service` changes; any render-wave challenge stop (D14); Firecrawl; `SCRAPEDO_TIMEOUT`; the live adapter UA.

### 11. Open questions

- Q-S23-1 (Q6): the transition semantics (recommended, byte-identical in both unknown production states) versus the clean cut (simpler, but a behaviour change at deploy if `SCRAPEDO_SUPER` is set).
- Q-S23-2 (Q7): keep the emptied scaffold (recommended) versus delete the script + its 2 test files' seed rows + the stale references.
- Q-S23-3: whether S81-23b (delete the legacy branch) is scheduled with the owner's ledger line or after approval only.

## 12. The group

### 12.1 Combined comm set

The union of D08 section 7 and S81-23 section 7: the 539-file seed measured at e7c81956 (D08 7 item 6), re-derived at HEAD by GREEN (adds the two RED files, drops `test_m6_c5_judgeme_html_reviews.py`), minus the four precommit files, chunks of at most 25 (bound 1200), base vs head, `comm -13` EMPTY; a branch-only-new failure is re-run against base before it counts. The fourteen client fences by path at GREEN and at the rebase. LC-6 base record reuse when the set hash matches.

### 12.2 CI-order set (one process, alphabetical, bound 1200)

`tests/test_fragrance_content_quality.py tests/test_hostile_jsonld.py tests/test_jsonld_shape_ladder.py tests/test_s81_d03_deny_and_guards.py tests/test_s81_d08_jsonld_widen.py tests/test_s81_s15_gate_rows.py tests/test_s81_s15_registry_robots.py tests/test_s81_s23_bypass_retire.py tests/test_scrapedo_service.py tests/test_seed_zyte_guard.py tests/test_wide_candidate_dict.py tests/test_zyte_seed_variant.py` plus every test file that names `_apply_gpt_review_aggregate_fallback`, `derive_rating_from_scores`, `_normalize_review_response` or `REVIEWS_EXTRACTION_SYSTEM` (GREEN lists them from the grep).

### 12.3 Combined footprint

Edited: `app/services/price_service.py`, `app/services/structured_comparison_service.py`, `app/services/response_builder.py`, `app/services/extraction_service.py`, `app/services/scrapedo_service.py`, `scripts/seed_zyte_luxury.py`, `scripts/seed_spec_spine.py` (docstring), `tests/test_zyte_seed_variant.py`, `tests/test_seed_zyte_guard.py`, `CLAUDE.md`. New: `app/services/jsonld_widen.py`, `tests/test_s81_d08_jsonld_widen.py`, `tests/fixtures/s81_d08_rating_flag_off_golden.json`, `tests/test_s81_s23_bypass_retire.py`. Deleted: `app/services/judgeme_service.py`, `tests/test_m6_c5_judgeme_html_reviews.py`, `tests/fixtures/judgeme_c5/` (7 files). No migration, no client file, no requirements, no `.githooks`, no processors.json, no `tests/.pre_impl_failures.txt`.

### 12.4 Shared-file plan

CLAUDE.md is the only shared file: one GREEN pass (section 0.3), the new block after the last SESSION 81 block at rebase time. The rebase onto 6c14ac95+ is a CLAUDE.md union plus the scs / extraction hunks if S81-10 has merged (known rebase, section 0.4).

### 12.5 PR plan

One PR, title "S81-G1 PRICE-PIPELINE: D08 JSONLD-WIDEN + S81-23 BYPASS-RETIRE (dark)", body at most 25,600 bytes measured with Python (LC-3): a summary, one short section per unit (flags, effect ON, flag-OFF proof: the PIN ids, the rating golden, the corpus gate OVERALL SHA256 base = head, the E-rows E1-E5, the counts RED / PIN / mutants killed), the stated limits, the owner steps (names only: unset `SCRAPEDO_SUPER` on web with a dated ledger line), the #93 closing text, no [NATIVE READ] items (no client copy). Mutation tables and gate logs go to `specs/S81_G1_*` files filed by the orchestrator.

### 12.6 The adversary's folded engineering checks (LC-1)

The single adversary also checks: every new flag is the FIRST statement of its branch and read per call; no import-time read; the leaf imports no I/O module; no new log line (R8); CRLF preserved and no whole-file diff; the corpus gate run with the identical `--flags` list both sides; the comm set derived by the union rule (module-path readers and `app.main` importers included); the E-rows only where section 4.1 says; the CLAUDE.md row content matches sections 8.

### 12.7 SAFE check (the FOCUS surfaces, each measured)

| surface | D08 | S81-23 |
|---|---|---|
| auth / tokens / sessions | not touched | not touched |
| quota / billing / refunds | not touched (no consume/refund path; the rating block runs after metering decisions, unchanged) | not touched |
| legal or privacy text / processors.json | not touched (no new external host: D08 fetches nothing; judge.me deletion touches no legal file) | not touched |
| consent path | not touched | not touched |
| security middleware | not touched | not touched |
| migrations | none | none |
| Redis / Lua | none (cached price dicts gain internal keys under ON only; no new key, no new command) | none |
| App-Review-visible client surface | no client file; build 3's rendered payload changes only with a flag ON (image source, null ratings) | none |
| secrets or key handling | none (no credential read added; `SCRAPEDO_API_TOKEN` handling unchanged) | none (the token stays in the params exactly as base) |

Both units are SAFE: no FOCUS surface found; the group stays together.

## Not done in this spec

The corpus gate OVERALL SHA256 at the base (NOT MEASURED: box loaded, corpus outside this worktree; GREEN runs base and head with the section 7.4 command); the full comm set node record (derivation and seed count given); the measured JSON-LD image-host distribution (a GREEN information step); whether `tests/test_prompt_fence.py` enumerates prompt constants (E2 conditional); the rating golden values (RED records them at base).
