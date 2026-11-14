# INC-I1 unit spec: PICTURE-MUST-MATCH (accept a product picture only when its text names the product; https only; the noon adapter keeps the PDP's JSON-LD image), dark behind ENABLE_IMAGE_RELEVANCE_GUARD

- Unit: INC-I1 PICTURE-MUST-MATCH. Lane: the S95-FIX incident lane (orchestrator S95-FIX, Claude Opus 5.5, session fce5ef8e-...; this spec by an Opus 5.5 spec agent, READ-ONLY round, 2026-11-14). Defects this unit addresses (the brief's list; nothing is called fixed before the phone proof, H6): S95-FIX diagnosis 2026-11-14 D2 RC1 (no relevance check, bare-name query, num=1) and RC2 (the noon adapter drops the PDP's JSON-LD image), the http part of ADV R-1 (b), and D1 F4 (merged here per ADV C-1). Trigger: the owner's comparison of 2026-11-13 21:19 UTC (the Blake poem picture for "Tyger"). DEFECT_LEDGER_INCIDENT.md has no INC-I1 row yet (the orchestrator files it).
- Flag: `ENABLE_IMAGE_RELEVANCE_GUARD` (NEW, default OFF, read PER CALL with the house idiom). Knob: `IMAGE_RELEVANCE_CANDIDATES` (default 5, clamped 1..10, the S81-10 clamp idiom). Neither name is a credential (CREDENTIALS_UNSET unchanged).
- Worktree: `C:/Users/SynAckITPC/Documents/AI/sc-inc-i1` (detached, read-only for this round). Branch GREEN creates: `fix/inc-i1-picture-must-match` (H3; the template's `feature/s81-<slug>` maps to this lane's name). RED files: `tests/test_inc_i1_picture_must_match.py` (file A) and `tests/test_inc_i1_noon_and_wiring.py` (file B).
- Base sha (full): `731bcddf531a7e123963246168ca19f262859337` (worktree HEAD == base, measured at the start and again at the end with `git rev-parse HEAD`). `git status --short`: EMPTY at the start and at the end (this file sits under `.qa-s80/`, ignored by `.gitignore:72 .qa-*/`, measured with `git check-ignore -v`).
- Measurement location: `<SP>/INC-I1/spec/` with `<SP>` = `C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad`: `comm.py` (the comm-set computation, git reads only), `comm_set.txt` (710 files), `comm_parts.json`, `probe_noon_ld.py` + `probe_noon_ld.out` (the noon JSON-LD image shape, parsed with the stdlib from `git show` exports of two committed fixtures, the exports deleted after the probe; their sha256 in `exported_copies.sha256`). Every file:line below was read at the base through `git show 731bcddf:<path>` / `git grep` in this run.
- Abbreviations: img = app/services/image_service.py (344 lines), scs = app/services/structured_comparison_service.py (9,979), noon = app/services/noon_service.py (541), jw = app/services/jsonld_widen.py (530), ps = app/services/price_service.py (17,332), cg = app/services/category_gate.py (740), ab = app/services/api_budget_service.py (1,421), ss = app/services/serper_service.py (1,463), rb = app/services/response_builder.py (2,387), leaf = the NEW app/services/image_relevance.py.
- THIS ROUND WAS READ-ONLY (H5 c, R0-9): no pytest, jest, tsc or eslint ran. Every run is written with its exact gate.py command and marked DEFERRED TO RED. A claim derived by reading code, not by running it, is marked BY READING; a claim nothing in this round could settle is marked NOT MEASURED.
- Evidence pointers: the brief = the orchestrator's rulings `<SP>/INC-I1/brief_rulings.txt` (I1-1..I1-11 bind; Q1-Q5 answered in 1.5-1.7 and 1.11); `<SP>/s95/reports/D2_image_specs_reviews_chips.md` (a: the picture chain; f: RC1, RC2, F1, F2), `D1_resolution_search_price.md` (F4, RC2), `R2_sources_images_claude.md` (b: the layered picture check), `ADV_review.md` (R-1, R-2, C-1); `<SP>/record/inc/RULINGS_INC_R0.md` (R0-1 proof standard, R0-6 merge windows, R0-8 names); `<SP>/record/s81/PLAN_S81.md` (Standing constraints; the VERIFY-stage "Images" correction; Fable ruling F1 DENY_HOSTS); `<SP>/record/s80/PLAN_S80.md` section 0 and `contract_freeze.json` (RULE 7: `overview.products[i].image_url` an absolute https raster URL or null; open question 2: ATS); `<SP>/record/s80/eval_regression.json` (tester scenario T01: the violin knowledge graph and the watch Serper image, reused as text-path fixtures); the house template `<SP>/record/s79/S78_F8_UNIT_SPEC.md` / `B3B_APPLE_REVOKE_UNIT_SPEC.md` and the G-INC-1 spec `<SP>/record/inc/G-INC-1_UNIT_SPEC.md` (unit INC-X2a, the last edit of img).
- Sister units and contracts: INC-R1 (product resolution at the explicit-pair Step 1, specified in parallel in sc-inc-r1, NOT assumed merged): INC-I1 consumes the product dict Step 1 leaves (`brand`, `name`, `category`) whatever INC-R1 writes; with INC-R1 OFF every app compare has brand "" (scs:4449-4452), with it ON the resolved house; the scs hunks are disjoint (INC-R1: the explicit-pair builders scs:4438-4453 / :5140-5153; INC-I1: one import and one keyword line in the image task scs:6260-6273): a known rebase by string anchor; CLAUDE.md union in merge order. INC-H1 NO-CONFIDENT-EMPTY (specs, reviews, chips; sc-inc-h1): no shared hunk. INC-X2 PHOTO-BUDGET (the 5 s race): untouched (I1-1). G-INC-1 INC-X2a (merged, #400): its `[IMG_TIER]` lines, tier names, outcome words and the CancelledError arm (img:338-344) stay byte-identical. D08 (ENABLE_IMAGE_PIPELINE_V2): its override policy and `IMAGE_CDN_HOSTS` unchanged. S81-07c: the `image_tier3` router site and the Tier-3 prompt unchanged. The S95 main lane (logo removal, consent re-ask, client only): no shared file.
- Personal-data rule: the repo is public. Synthetic values only in every test and fixture; the product names used are public product names (the brief's pairs, the T01 tester shapes); test hosts are `*.example.test` / `example.com` / `example.org` or the measured public host names `f.nooncdn.com`, `www.noon.com`, `www.dior.com`, `www.tomford.com` as literal test data (no network: the netguard). The new log line carries constants, a closed-set slot word, closed-set tier / outcome / reason words and one int: never a product name, URL, query text or title. No credential-shaped literal anywhere; no digit run of eight or more in a test literal (the added-line sweep); Arabic text is built at run time with `chr()` (the cg `_cps` idiom, cg:140-141), so every file stays pure ASCII.

---------------------------------------------------------------------------------------------------

## 0. What the unit does

Under `ENABLE_IMAGE_RELEVANCE_GUARD` (new, default OFF, read per call), for TEXT compares only (never a camera product), the picture cascade `image_service.get_product_image_url` accepts a candidate image only when (1) its URL is https and (2) the text that came with it names the product: a brand token of the product (from the title or the source, or the link's host, alias-folded) AND at least one significant token of the product line; when the brand is empty, a line token AND a fragrance word (perfume, parfum, eau, edt, edp, cologne, fragrance, or the Arabic word for perfume) instead. Tier 1 asks Serper Images for `"<full name> perfume"` (the word only for a fragrance-category product) with `IMAGE_RELEVANCE_CANDIDATES` results, walks them in order and takes the first that passes; Tier 1.5b tests every knowledge-graph / organic / images item before taking it; Tier 3 (the LLM pick) runs only when an organic result passes and its pick must sit on such a result's host; the piggyback tier is https-only. One INFO line per call: `[IMG_RELEVANCE] product=<slot> tier=<tier> outcome=<accepted|rejected|none> candidates=<n> reason=<none|scheme|brand|name|fragrance_word>`. Under the same flag the noon adapter copies the PDP's Product JSON-LD image (the first https raster URL) into its price dict as `image_url`, so the EXISTING post-Phase-1 price-page override (scs:6396-6429) can show the priced product's own picture. Failure policy: no candidate passes = the tier misses = the next tier, or `None` (the client's placeholder tile); never an error, never a refusal, never a new code. Flag OFF: byte-identical on every entry (no new keyword in the call, no new key in the noon dict, no new log line, no knob read), pinned.

---------------------------------------------------------------------------------------------------

## 1. Base state (measured at 731bcddf)

### 1.1 The picture cascade (img)

| Where | Measured fact |
|---|---|
| img:33-48 | imports: `from __future__ import annotations`; asyncio, json, logging, time, typing; `try_consume_serper_image_credit` (ab), `api_budget_service as _llm_breaker`, `llm_router as _llm_router`, model_config helpers, `openai_service.get_client`, `serper_service.search_images`, `deny_hosts.data_guards_v2_enabled / is_denied_url`. No import of price_service, category_gate or jsonld_widen. |
| img:57-67 `_is_valid_image_url` | the ONLY gate on every tier: a str whose stripped value starts with `http://` or `https://` (case-sensitive), and, after a base-True verdict, the deny list under `ENABLE_DATA_GUARDS_V2` (deny_hosts). http is accepted (ADV R-1 b). Also used by kb_serve.py:323 (the KB card image, which adds its own `startswith("https://")`) and by the override at scs:6424. |
| img:82 | `_ORGANIC_IMAGE_KEYS = ("imageUrl", "thumbnailUrl", "thumbnail", "image")`. |
| img:85-129 `extract_image_from_search` | Tier 1.5b, pure: (1) `knowledgeGraph` / `knowledge_graph`, keys `imageUrl`, `image`, `imageURL`, `thumbnailUrl`: the first valid; (2) the first organic item carrying a valid image key; (3) the top-level `images` block, same keys. It reads NO title, source or link. |
| img:136-153 `_TIER3_PROMPT` | no category, no brand rule beyond "Prefer official brand / authorized retailer domains". |
| img:156-217 `extract_image_via_gpt(product_name, organic_results)` | Tier 3: `organic_results[:10]` rendered as `- {link}: {snippet}`; the router site `image_tier3` through `guarded_llm_create` (S81-07c option b); JSON parse; `_is_valid_image_url(candidate)`; any failure -> None (WARNING). |
| img:220-225 `_log_img_tier` | INC-X2a: `[IMG_TIER] tier=%s outcome=%s ms=%d` (INFO). |
| img:232-239 signature | `get_product_image_url(product_name, *, region="bahrain", page_scrape_image=None, organic_results=None, search_payload=None) -> Optional[str]`. No identity, no category, no brand. |
| img:255-257 | empty name -> `return None` before any bookkeeping (no log line). |
| img:259-262 | `_t_call`, `_inflight = ["piggyback", _t_call]`, `try:`. |
| img:264-268 | Tier 1.5 piggyback: truthy and valid -> `[IMG_TIER] piggyback hit` + INFO hit line + return; else `miss` / `skipped`. Production always passes `page_scrape_image=None` (scs:6263). |
| img:274-281 | Tier 1.5b: `extract_image_from_search(search_payload)`; hit -> return; else `skipped` (payload None) / `miss`. |
| img:286-289 | the budget gate: ONE synchronous `try_consume_serper_image_credit(1)` per call; `[IMG_TIER] serper_budget` with outcome hit or miss. |
| img:290-314 | Tier 1: `await search_images(name, num_results=1)` (img:295, the BARE product name); `images[0].imageUrl` only (img:306-311); `_is_valid_image_url`; hit -> `[IMG_TIER] serper_images hit` + `[image] Tier 1 Serper hit for %r` + return. Exceptions -> `error:<Type>` + WARNING. |
| img:317-333 | Tier 3: only when `organic_results` is truthy; `_is_valid_image_url(gpt_url)` -> hit; else `miss` / `error:<Type>`; no organic -> `skipped`. |
| img:336-337 | `[image] All tiers exhausted for %r -- returning None`. |
| img:338-344 | `except asyncio.CancelledError:` one INFO `[IMG_TIER] cancelled tier=%s tier_ms=%d total_ms=%d`, no await, bare `raise` (pinned by tests/test_inc_x2a_image_tier_timing.py R2-7). No `finally`. |
| `git grep get_product_image_url` (app/, scripts/) | ONE caller: scs:6261 (import scs:1591). `extract_image_via_gpt` is also called by scripts/meas_claude_gate.py:1685-1687 (the S81-07 harness). `search_images` is called only at img:295. |

### 1.2 The caller and the price-page override (scs)

| Where | Measured fact |
|---|---|
| scs:86, :1432 | `from app.services import category_gate as _category_gate` and `from app.services.price_service import (...)` at MODULE TOP: both modules are loaded at app start (the app imports scs), so a function-local import of either at request time is a sys.modules lookup. |
| scs:1591, :1596, :1601 | `from app.services.image_service import get_product_image_url`; `from app.services import image_service` (module attribute, D03 F1-6); `from app.services import jsonld_widen` (D08, module attribute). |
| scs:1374-1390 `_product_display_identity` | text path: `full = dedup_brand_name(brand, f"{name} {variant or ''}".strip())`, i.e. `<brand> <name> <variant>` deduplicated; vision: `dedup_brand_name(brand, name) or search_query`. |
| scs:4422-4437 | camera products: `brand` (default "Unknown"), `name`, `variant` = size_or_count, `"_vision": True` (the camera path reaches the SAME cascade through `compare_from_text(..., vision_products=...)`, image_routes.py:614-616). |
| scs:4438-4453 (sync), :5140-5153 (stream), :1959-1971 (`_explicit_pair_products`) | the explicit pair: `{"brand": "", "name": <sanitized typed text>, "variant": None, "category": classify_category_from_text(...), "search_query": <typed>, "_explicit": True}`; the pair category is resolved and written back afterwards. Both live bundles send a text compare as ONE GET to /api/v1/text/compare (INC-R1 brief MF-1), i.e. the sync path. |
| scs:4565-4566, :5269-5270 | the only `_fetch_product_data` calls: `partial_slot=0` / `partial_slot=1`. |
| scs:5953-5980 `_fetch_product_data` | `brand`, `name`, `variant` from product_info; `category = canonicalize_category(product_info.get("category"))` (extraction_service.py:1236-1264; "fragrance" / "perfume" -> `"fragrances"`, :1185-1186); `is_vision = product_info.get("_vision", False)`; `full_name, display_name = _product_display_identity(...)`. |
| scs:6017-6034 | `_PHASE1_TIMEOUTS["image_url"] = 5.0`. |
| scs:6128-6160 | `unified_search` = `search_web(f"{search_query} specifications reviews price", num_results=10)` (the raw Serper /search JSON, ss:776-836) only when specs or reviews need it; else None. |
| scs:6260-6273 | the image task: `kb_serve.served(_kb["image_url"]) if (_kb and _kb["image_url"]) else get_product_image_url(full_name, region=region, page_scrape_image=None, organic_results=(unified_search.get("organic", []) if unified_search else None), search_payload=unified_search)` under `asyncio.wait_for(..., timeout=5.0)`. The KB branch runs only with ENABLE_KB_FIRST_SERVE (OFF). |
| scs:6301-6319 | a race timeout or exception -> `_price_fallback_on_miss(key, ...)`; else `result[key] = value`. |
| scs:6396-6429 the price-page override | only `if result.get("price")`: `page_img = result["price"].get("image_url")`; (a) `jsonld_widen.image_pipeline_v2_enabled()` -> `allowed_image_url(page_img, result["price"].get("url"), OFFICIAL_BRAND_DOMAINS)`; (b) elif `data_guards_v2_enabled()` -> `image_service._is_valid_image_url(page_img)`; (c) else any `http://` / `https://` string. A truthy result REPLACES the cascade image. http passes (b) and (c). |
| scs:4610, :5364 | `reconcile_pair_fairness(...)` runs at the pair level AFTER both `_fetch_product_data` calls (it may re-select the displayed price after the override ran; BY READING). |
| scs:7474-7499, :7862-7883 | the BH adapters (noon at :7486) and the direct-hit consume: `should_cache_price(...)` -> `_cache_price_and_clear_sentinel(cache_key, best)` (L1, the whole dict, scs:9357-9382 with `price_cache_ttl`: 7 days for a genuine method) + `_save_price_to_db(...)` (L2: product_data_service.save_price keeps a FIXED column set amount / currency / retailer / url / source_method / estimated / title / in_stock, product_data_service.py:342-359, NO image_url); INFO `[PRICE] BH adapter direct hit for %s: %.3f %s via %s` (scs:7879-7883). |
| rb:1951, :1972, :2232-2236 | `overview.products[i].price = public_price_view(pd.get("price"))` (ps:9426-9442: the whole price dict; with the exact gate ON the `_`-keys and `guard_rejected` are dropped) and `overview.products[i].image_url = pd.get("image_url")`. |

### 1.3 The noon adapter and its PDP JSON-LD image (RC2)

| Where | Measured fact |
|---|---|
| noon:73-93 | imports from ps (`ENABLE_PAGE_SCRAPE`, the gate chain helpers, `normalize_words`, ...) and ab (the breaker). |
| noon:105 | `_PDP_URL = "https://www.noon.com/bahrain-en/{slug}/{sku}/p/"`. |
| noon:288 / :327 | `_extract_product_jsonld(html)` returns the Product node; `_jsonld_brand(product)`. |
| noon:397-467 `_confirm_pdp` | :417 the Product JSON-LD; :425 the identity gates re-run on the PDP's own name + brand; :430 `_select_offer`; :443-454 the price dict {amount, currency "BHD", retailer "noon.com", url (the PDP), estimated False, source_method "page_scrape_jsonld", title, confidence 0.9}; :455-466 `in_stock`, `seller`, `brand` (under `exact_gate_enabled()`, ps:4370-4374, default ON); :467 `return price`. The Product node's `image` is NEVER read (D2 RC2, ADV #12 / R-2 confirmed). |
| noon:474-541 `fetch_noon_price` | `ENABLE_PAGE_SCRAPE` (ps:51, import time, default true), domain noon.com, breaker, the search ladder, up to `_MAX_PDP_CONFIRMS = 2` confirms, `is_price_showable`, content safety; NEVER raises. Called only through the scs adapter consume (scs:1655, :7486). |
| the committed fixtures (probe `<SP>/INC-I1/spec/probe_noon_ld.out`) | tests/fixtures/bh_gcc/noon_pdp_iphone_bhd.html and noon_pdp_meta_quest_3s.html: the Product JSON-LD `image` is a LIST of 10 strings, each `https://f.nooncdn.com/p/pzsku/<sku>/45/_/<n>/<uuid>.jpg?width=1200`. So the noon image host is `f.nooncdn.com` (not a noon.com subdomain) and the raster extension sits on the PATH (the query `?width=1200` follows it). Other committed shapes: an ImageObject dict and a list of ImageObjects (eval_regression.json: the tuzzut / nishane fixtures), handled by `ps._jsonld_image_urls` (ps:10995-11027: a string, a list, or an ImageObject `url` / `contentUrl` / `@id`, deduplicated, never raises). |
| tests/test_noon_adapter.py (804 lines) | synthetic Product dicts WITHOUT an `image`; assertions on single keys (`out["currency"]`, `out["seller"]`, ...); no exact-dict or key-set pin of the price dict (measured by grep for `== {`, `keys()`). |

### 1.4 The D08 image policy and the noon host (Q4)

| Where | Measured fact |
|---|---|
| jw:59-61 | `image_pipeline_v2_enabled()` = `ENABLE_IMAGE_PIPELINE_V2`, house idiom, per call. |
| jw:74, :79, :88 | `RASTER_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif")` judged on the PATH; `IMAGE_CDN_HOSTS = ("cdn.shopify.com", "cdn.salla.sa", "cdn.salla.network", "media.zid.store")`; `_NON_PUBLIC_SUFFIXES` includes `.test` and `.local`. |
| jw:156-164 `_image_host_allowlisted(host, page_url, brand_domains)` | first-party: the www-stripped host equals the page's www-stripped host or is its subdomain; else a suffix of an `IMAGE_CDN_HOSTS` entry; else the host is in `brand_domains`. |
| jw:170-193 `allowed_image_url(url, page_url, brand_domains=())` | str, no unsafe chars, https, a netloc without `@`, a public host, a raster path, not `deny_hosts.is_denied_url`, `_image_host_allowlisted`. Pure, never raises. |
| ps:594-601 | `OFFICIAL_BRAND_DOMAINS` is a set of 26 hosts (hermes.com, ..., dior.com, tomford.com, apple.com, samsung.com, sephora.com, ...); no noon or nooncdn host. |
| THE TWO BRANCHES for a noon page image (BY READING jw:156-193 and scs:6417-6429; the RED file B pins them, B-P04) | V2 ON: `allowed_image_url("https://f.nooncdn.com/p/.../x.jpg?width=1200", "https://www.noon.com/bahrain-en/.../p/", OFFICIAL_BRAND_DOMAINS)` -> None: https, public, raster (`.jpg` on the path), not denied, but `f.nooncdn.com` is neither `noon.com` nor its subdomain, matches no `IMAGE_CDN_HOSTS` entry and is not a brand domain -> REFUSED by the host allowlist only; the eager cascade image stands. V2 OFF + ENABLE_DATA_GUARDS_V2 ON: `_is_valid_image_url` -> True (nooncdn is not denied) -> the noon image replaces the cascade image. Both OFF (production today, 1.8): the inline http(s) prefix test -> the noon image replaces the cascade image. R2 caution 7 (the V2 refusal "could explain the grey card") is moot today, as ADV R-2 says: no noon image ever reaches the override at the base. |

### 1.5 The Serper fields this code reads (Q1)

| Source | Fields the code reads at the base | Fields present in repo fixtures | Fields the guard reads (contract 2.2) |
|---|---|---|---|
| Serper Images item (Tier 1, `search_images` returns `response.json()` unchanged, ss:1284-1296) | `imageUrl` only (img:306-307) | `imageUrl`, `title` (tests/test_image_service.py:73; docs/plans/2026-05-30-bundle-e-s3.md:434; eval_regression T01 fixture c `{title: 'Sefiki men watch', imageUrl}`). NOT MEASURED: `source`, `link`, `domain` appear in NO repo fixture (the provider's documented item shape; no network in this round) | `title`, `source` (text), the host of `link`, else the host of `domain` (brand test only); absent or non-string fields = empty |
| Knowledge graph (`knowledgeGraph` / `knowledge_graph` of the unified /search payload) | the image keys only (img:97-103) | `title` + `imageUrl` (tests/test_image_knowledge_graph_tier.py:42 "Tom Ford Tobacco Vanille"; :58 `{"title": "x"}`); eval_regression T01 fixture b `{title: 'Violin', type: 'Musical instrument', imageUrl}` | `title` only (I1-3) |
| Organic result (unified /search payload; also the Tier-3 input) | `title`, `snippet`, `link` (scs:9277-9281, :9306-9312; img:172 link + snippet); image keys `_ORGANIC_IMAGE_KEYS` (img:111-114); the Bright Data fallback maps to `{title, link, snippet}` (brightdata_service.py:225-246) | `{link, snippet}`, `{link, imageUrl}`, `{title, link, snippet}` (tests/test_image_service.py:153, test_image_knowledge_graph_tier.py:61, test_inc_x2a_image_tier_timing.py:104) | `title` (text) and the host of `link` (brand test only) |
| `images` block of the unified payload | image keys only (img:119-127) | none with a title | `title`, `source` (text), host of `link` / `domain` (brand test only) |

### 1.6 Brand alias folding and tokenization available (Q2)

| Where | Measured fact |
|---|---|
| ps:5171-5199 `_BRAND_ALIAS_GROUPS` | 13 frozensets of token forms: {ysl, yves, saint, laurent}, {dg, d&g, dolce, gabbana}, {jpg, jean, paul, gaultier}, {ck, calvin, klein}, {ch, carolina, herrera}, {mj, marc, jacobs}, {tf, tom, ford}, {vr, v&r, viktor, rolf}, {dior, christian}, {versace, gianni}, {armani, giorgio, emporio}, {lancome, paris}, {montblanc, mont, blanc}. NO Bvlgari / Bulgari group: `git grep -i bulgari -- app/ data/` = 0 hits (data/fragrance_lexicon.json lists the house `bvlgari` only). |
| ps:6909-6959 `_brand_evidence_ok` (the RS2 wrong-brand fence) | the repository's alias-folding idiom: the brand tokens, expanded by every group they touch (`q_brand_exp` united with every group it touches, ps:6943-6946), intersected with the candidate's alias-expanded tokens (ps:6947-6955; a candidate token counts when `len(w) > 2 and not w.isdigit()`). |
| spec_spine_service.py:190-207 `_brand_axis` | the precedent for REUSE without a module-top import: `from app.services.price_service import _BRAND_ALIAS_GROUPS, _fold_identity, normalize_words` INSIDE the function. |
| ps:3856-3868 `normalize_words` | NOT reused: flag-dependent (`exact_gate_enabled`, `ENABLE_NORMALIZE_WORDS_EMPTY_FIX`), whitespace split only (a host `www.dior.com` stays one token; `Eau-de-Parfum` becomes `eaudeparfum`; a vertical bar stays a token). |
| cg:40-44, :172-199 `normalize(text) -> List[str]` | REUSED as the tokenizer: module level stdlib only ("every app import is function-local"); NFKC, Latin combining marks stripped (an accented house matches its plain spelling), casefold, Arabic harakat / tatweel dropped, alef / ta marbuta / alef maqsura folded, Arabic-Indic digits to ASCII, any non-letter non-digit a separator (so `www.dior.com` -> `www`, `dior`, `com`; `D&G` -> `d`, `g`), one leading Arabic article stripped per token (U+0627 U+0644 + `ayn ta ra` -> the bare perfume word). Pure, total (non-str -> []), flag-free; already imported at app start (scs:86, the five route modules). |
| data/fragrance_lexicon.json (read by cg at call time) | `fragrance.concentrations` 14 terms (eau de parfum, eau de toilette, eau de cologne, extrait de parfum, parfum, edp, edt, edc, extrait, elixir, eau fraiche + 3 Arabic), `forms` 22 (perfume, perfumes, fragrance, fragrances, cologne, colognes, scent(s), body mist, ..., Arabic U+0639 U+0637 U+0631 and U+0639 U+0637 U+0648 U+0631, ...), `houses` 75. The leaf does NOT load the lexicon (a file read per call is avoidable); it carries its own closed word sets (2.2), normalized with `cg.normalize` at import. |

Answer to Q2: the tokenizer is `category_gate.normalize`; the alias data is `price_service._BRAND_ALIAS_GROUPS`, expanded with the RS2 idiom, read through a function-local import exactly as `spec_spine_service._brand_axis` does; price_service is already in `sys.modules` at request time (scs:1432), so nothing heavy is imported at request time; the missing {bvlgari, bulgari} group is added LOCALLY in the leaf (`EXTRA_ALIAS_GROUPS`), never in price_service (whose groups drive the price fences).

### 1.7 The image budget counter and Serper accounting (Q3)

| Where | Measured fact |
|---|---|
| ab:34-40 | `SERPER_IMAGE_DAILY_BUDGET` read per call (default constant `_DEFAULT_SERPER_IMAGE_DAILY_BUDGET`; CLAUDE.md:313 says 500). |
| ab:1236-1239, :1248-1295 `try_consume_serper_image_credit(n=1)` | ONE synchronous Redis INCRBY n on `budget:serper_images:<UTC date>` per call (EXPIRE 36 h on the first write; DECRBY and WARNING when over the limit -> False; fail-OPEN on any Redis error). img:288 calls it with 1 once per cascade call, BEFORE the Serper call, independent of `num`. |
| ss:1267-1309 `search_images(query, num_results=5)` | ONE POST `/images` with `{"q": query, "num": num_results}` through `_serper_post` (key failover inside, unchanged); `await _record_usage_async("serper")` ONCE per 200 (ss:1295, the lifetime usage counter); `_serper_budget_ok()` gates it. The default `num_results` is already 5; img:295 passes 1. |
| docs/CONTEXT_ARCHITECTURE.md:380 | the repo's cost table prices "Serper search (per call)". |
| NOT MEASURED | the provider's own billing rule for `num` 5 vs 1 (no network in this round). The knob's ceiling 10 keeps the request at one results page. |

Answer to Q3: in this code both counters are PER CALL: the unit keeps exactly one `try_consume_serper_image_credit(1)` and one `search_images(...)` per cascade call, so the daily image counter and the lifetime usage counter move exactly as at the base; only `q` and `num` change under the flag. Whether the provider bills a 5-result images query as one credit is OQ-6 (the relay reads the dashboard counter delta of one compare in the canary window).

### 1.8 Production flag state (the dated lines) and the frozen contract

- Source of record: the common brief H12 (c) (the relay's dated lines of 2026-11-14) and the record-copy ledger `<SP>/record/s81/ledger.md` line 316 (2026-11-07 06:24, the flag-value read: ENABLE_PAGE_SCRAPE ON; "every S81 flag ... UNSET") and line 336 (2026-11-07 09:05: ENABLE_IMAGE_PIPELINE_V2, ENABLE_KB_FIRST_SERVE, ENABLE_FRAGRANCE_ONLY_GATE NOT FLIPPED); the record-copy ledger's newest line is 2026-11-11 (line 443); nothing newer names an image flag.
- Therefore on web today: ENABLE_IMAGE_PIPELINE_V2 OFF, ENABLE_DATA_GUARDS_V2 OFF (an S81 flag, unset 2026-11-07, absent from the H12 (c) ON list), ENABLE_KB_FIRST_SERVE OFF, ENABLE_PAGE_SCRAPE ON (the noon adapter runs), ENABLE_PRICE_CACHE_WARMER false on price-warmer (line 316), ENABLE_FRAGRANCE_ONLY_GATE believed OFF (non-fragrance text compares still run), ENABLE_ANTHROPIC_TEXT ON and ENABLE_OPENAI_EGRESS_STOP ON (Tier 3 runs on Claude for a consent-3 request and fails locally below consent 3), ENABLE_EXACT_PRICE_GATE default ON in code (ps:4370-4374; CLAUDE.md:341 "IN PROD"). `ENABLE_IMAGE_RELEVANCE_GUARD` is a new name: unset by construction.
- The frozen contract (PLAN_S80 section 0 point 4; contract_freeze.json RULE 7 and finding 9): `overview.products[i].image_url` is an absolute https raster URL or null; ProductImage renders any non-empty string, falls back to the placeholder on `onError` (SmartCompareApp/src/components/primitives/ProductImage.tsx:13-16, :60, :101-103); no ATS override in SmartCompareApp/app.json (`git grep -i NSAppTransportSecurity` = 0 hits), so an http URL shows the grey tile (ADV R-1 b). Both live bundles (683f56c0 store, f1e20c39 OTA) read `image_url` only on products (ResultsContent.tsx:339 `product.image_url`, imagePrefetch.ts:36, HistoryScreen.tsx:487-491, types.ts:103); `git grep` for a read of `price.image_url` in SmartCompareApp/src at both shas = 0 hits.

### 1.9 Guards the new code must not trip; the flag-reader idiom; libraries; line endings

- Flag-reader idiom (cited): `os.getenv("ENABLE_IMAGE_PIPELINE_V2", "false").strip().lower() in _TRUTHY` with `_TRUTHY = ("true", "1", "yes", "on")` (jw:56-61); the clamped knob idiom: cg:111-124 `refusal_daily_budget` (float of the stripped value; not finite or < 1 -> the default; else `min(int(value), MAX)`).
- Libraries (the pinned venv `C:/Users/SynAckITPC/Documents/AI/.venv-qaren`, pyvenv.cfg: CPython 3.12.9): the unit uses the stdlib only (re, os, urllib.parse via its own imports; unicodedata via cg) plus in-repo leaves; no new dependency, no requirements change. On the venv: black 26.5.1, ruff 0.16.5, pytest 9.1.1, pytest-asyncio 1.4.0 (strict mode: pyproject.toml:38-46 sets no asyncio_mode); the RED rows drive coroutines with `asyncio.run` like the X2a file.
- T7b (tests/test_legal_docs_u8.py:826-864, an `rglob` over app/services/*.py): every NON-docstring string literal holding an http(s) URL with a valid external host must map to a processors.json row. The leaf and the edits add NO such literal (the scheme test uses the bare prefix `"https://"`, which holds no host).
- D03 r1i (tests/test_s81_d03_deny_and_guards.py:587-610, an `rglob` over app/): no assignment may carry a banned host literal (fragrantica, parfumo, basenotes, fimgs.net): the leaf assigns none.
- R8 / U8d (tests/test_sentry_channels_u8d_unit.py) and the key-log hygiene scan (tests/test_openai_key_log_hygiene_s69.py): the only new log line is INFO with %-args of constants; no ERROR, no exception text.
- The LLM create-site census (tests/test_model_config_enforced.py), the store=False pin (tests/test_u3c_store_false_pin.py), the router route census (tests/test_s81_s06_anthropic_router.py:47, `extract_image_via_gpt` -> ["image_tier3"]) and the Tier-3 prompt digest (tests/test_prompt_fence.py:806-818, tests/w4_11_prompt_digest_recorder.py:91, tests/fixtures/w4_11_prompt_render_digests.json image_tier3_* keys): the unit adds no create site, no route call, no prompt text.
- The INC-X2a grammar (tests/test_inc_x2a_image_tier_timing.py:32-36, R2-6, R2-7): `[IMG_TIER]` lines keep the closed tier set and outcome set; the new line starts with `[IMG_RELEVANCE]` (the X2a filter `startswith("[IMG_TIER]")` excludes it); the CancelledError handler keeps no await and its bare `raise`.
- The black ratchet (.github/black-clean-paths.txt:15-18: "Added a new .py file? It should be black-clean, so add it here"; tests/test_ci_gates.py `test_black_allowlist_entries_are_actually_clean`; CI pins black 26.5.1 and ruff 0.16.5, .github/workflows/ci.yml:155-185): the MON1 precedent added its new modules and test files; this spec does the same for the leaf and the two RED files (OQ-9).
- `tests/_env_safety.CREDENTIALS_UNSET`: no new credential name. The netguard (tests/conftest.py:31-41): the RED rows make no network attempt (every tier callable and the noon HTTP function are patched).
- Line endings (`git ls-files --eol`): img, noon, scs, jw, cg, CLAUDE.md, tests/test_inc_x2a_image_tier_timing.py, tests/test_noon_adapter.py are all `i/lf w/crlf` (`core.autocrlf=true`): the Edit tool keeps CRLF in the edited files; a whole-file diff in `git diff --stat` is a defect. New files are written LF, pure ASCII (bytes > 127 counted after every write).

### 1.10 Base pass state of the files the unit touches or pins (DEFERRED TO RED)

No whole-tree base record exists for 731bcddf (H12 b). The RED agent runs these three ONCE each at the base through the wrapper (one process at a time; paste every `[gate]` and `[pyt]` line, the `[netguard]` and `[hermeticity]` lines and the per-file counts) and stores the FAILED / ERROR id set:

```
PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/harness/gate.py --bound 600 --tag inc-i1-base-img --log C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-I1/red/base_img.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-i1 -- tests/test_image_service.py tests/test_image_service_edges.py tests/test_image_service_longtail.py tests/test_image_knowledge_graph_tier.py tests/test_inc_x2a_image_tier_timing.py tests/test_inc_g1_gate_rows.py tests/test_comparison_response_image_url.py

PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/harness/gate.py --bound 1200 --tag inc-i1-base-pins --log C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-I1/red/base_pins.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-i1 -- tests/test_noon_adapter.py tests/test_s81_d08_jsonld_widen.py tests/test_s81_d03_deny_and_guards.py tests/test_s81_s07c_role_fix.py tests/test_s81_s06_anthropic_router.py tests/test_model_config_enforced.py tests/test_prompt_fence.py tests/test_s81_s18_kb_first_serve.py

PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/harness/gate.py --bound 1200 --tag inc-i1-base-scan --log C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-I1/red/base_scan.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-i1 -- tests/test_legal_docs_u8.py tests/test_ci_gates.py tests/test_s81_s22b_self_critique_retire.py tests/test_s81_s12d_openai_egress_stop.py tests/test_sentry_channels_u8d_unit.py tests/test_openai_key_log_hygiene_s69.py tests/test_serper_budget_gate.py
```
NOT MEASURED in this round. Expected (BY READING): all green except recorded environment noise; a `status=BUSY rc=126` line means the run did not start (retry once, else NOT MEASURED, H5 a); a TIMEOUT is re-run once alone. The comm-set base record (section 7) is a separate, larger computation.

### 1.11 Every existing test that pins this region (Q5)

| Test file (nodes) | What it pins | Sees the unit? |
|---|---|---|
| tests/test_image_service.py (whole file), test_image_service_edges.py (:52-:329), test_image_service_longtail.py (:29 "uses only first image", :256 `assert_called_once_with(<arabic name>, num_results=1)`), test_image_knowledge_graph_tier.py (:40-:143) | the base tier order, `images[0]`, `num_results=1`, the KG / organic / images precedence of `extract_image_from_search`, the budget gate, Tier 3 parsing | NO: they run with the flag unset (a new name) and without `relevance=`; `extract_image_from_search` and `_is_valid_image_url` stay byte-identical |
| tests/test_inc_x2a_image_tier_timing.py (R2-1..R2-7, P2-1..P2-7) and tests/test_inc_g1_gate_rows.py (:80-:130) | the INC-X2a timing lines, their closed grammar, the CancelledError arm (no await, bare raise), the call order with recorders, `rec.search == [((NAME,), {"num_results": 1})]` (P2-2) | NO at flag OFF (the OFF path is the base path); the unit keeps the grammar under the flag too (A-R14) |
| tests/test_comparison_response_image_url.py (:89-:325) | the scs wiring: one call, `call_args.kwargs.get("organic_results")` / `.get("region")` (:321-324, `.get` only, so an extra key would not break it), the result `image_url` | NO at flag OFF (no new kwarg) |
| scs-level drivers patching `scs.get_product_image_url` with `AsyncMock` or `*a, **k` fakes: test_s81_s18_kb_first_serve.py (:404-437 records the positional args; golden counts `"get_product_image_url": 2`), test_inc_x9_cohort_line_retire.py:164, test_s78_all_timeout_cap_as_timeout.py:259, test_s75_fanout_identity.py:155-174 (the FY25 digests), test_s75_fanout_starve.py, test_phase1_per_race_timeouts.py:48 (`fast_image(*_args, **_kwargs)`), test_latency_stack_i56.py, test_price_timeout_returns_parked.py, test_lever1_orphan_cancel_i56.py, test_inc_x8_phase2_cached_rating.py, test_partial_specs_stash_on_price_timeout.py, test_s78_tier_fill_residual_guard.py, test_w4_7_*.py, test_s81_s17_kb_ingest.py, test_s81_d14_live_robots.py, test_flush_live_price_key.py, test_genuine_price_priority.py, test_s81_g1_gate_rows.py:220 | the compare flow around the image leg | NO: every fake accepts any keyword (measured); at flag OFF no keyword is added anyway |
| tests/test_s81_d08_jsonld_widen.py (:347-367 `_scs_fetch`, :629-641 R9 piggyback ON) and tests/test_s81_d03_deny_and_guards.py (:1364-1383, :1550-1551, :2082, :2129-2139 F1-6) | the override's V2 branch, the D03 deny inside `_is_valid_image_url`, scs reaching `image_service._is_valid_image_url` by module attribute | NO: the override and `_is_valid_image_url` are untouched |
| tests/test_noon_adapter.py (:224-:762) | the noon contract (headers, buy-box, ladder, gates, breaker, politeness) | NO at flag OFF; its Product fixtures carry no `image` anyway |
| the S81-07c image_tier3 router pins: tests/test_s81_s07c_role_fix.py (T01-T06, :240), test_s81_s06_anthropic_router.py (R01 / R02c, :525, :545, :602-604, :753), test_s81_s22b_self_critique_retire.py (:79 SITES_BASE, :91-93 OPENAI_MODULES_AFTER), test_s81_s07_meas_harness.py (:1365, :1383-1415), test_s81_s12d_openai_egress_stop.py (:99 WATCHED, :944-983), test_model_config_enforced.py (:154-177) | `SITES["image_tier3"]`, the Tier-3 request shape, the breaker chokepoint, the processor module list | NO: `extract_image_via_gpt`, the router and the prompt are untouched; under the flag Tier 3 is called LESS often (never when no organic result passes) |
| tests/test_serper_budget_gate.py (:391, :471), test_serper_record_usage.py (:117-122), test_s78_serper_key_memo.py (:208) | `search_images` budget gate and usage record | NO: `search_images` is untouched |
| tests/fixtures/legal_s78.json:284, app/legal/processors.json:241 (noon in the retailer row's modules) | the processor module lists | NO: no new host, no new module with a host |

---------------------------------------------------------------------------------------------------

## 2. Contract

Contract freeze re-read before this section (PLAN_S80 section 0 and contract_freeze.json, 1.8): the unit adds NO refusal, NO envelope, NO error code and NO status; `overview.products[i].image_url` stays a string or null (under the flag an https URL from the cascade); the one new response-visible key value is `overview.products[i].price.image_url` (and the legacy alias `products[i].price.image_url`) for a noon-won price under the flag: an EXISTING optional member of price objects (the cached Zyte seeds write it, zyte_service.py:499, :661; D08 writes it under V2, jw:319), additive, read by neither live bundle (1.8). The orchestrator classifies (I1-10, OQ-11).

### 2.1 Flag and knob

- `image_relevance.guard_enabled() -> bool`: `os.getenv("ENABLE_IMAGE_RELEVANCE_GUARD", "false").strip().lower() in ("true", "1", "yes", "on")`, read PER CALL, never cached.
- `image_relevance.candidates_knob() -> int`: `IMAGE_RELEVANCE_CANDIDATES`, read per call, the cg:111-124 idiom: unset -> 5; `float(raw.strip())` raising (blank, garbage) -> 5; not finite (inf, nan) or below 1 (0, negatives) -> 5; else `min(int(value), 10)` ("7.9" -> 7, "15" -> 10, " 7 " -> 7). The brief's "clamped 1..10; garbage falls back to the default" read through the house precedent (below 1 = garbage, L-I1-17).
- Names only in logs and docs; neither is a credential.

### 2.2 The leaf `app/services/image_relevance.py` (NEW)

Module level: `from __future__ import annotations`; stdlib only (`os`, `re`, `math`, `typing`, `urllib.parse.urlsplit`) plus `from app.services import category_gate as _cg` and `from app.services import jsonld_widen as _jw` (both light at module level: cg:45-55 imports the stdlib only, cg:40-44; jw:44-54 imports the stdlib plus the in-repo leaves deny_hosts and robots_eval, jw:39-42; both are already loaded at app start through scs:86 and scs:1601). `price_service` is imported ONLY inside `alias_groups()` and `first_https_raster()` (the spec_spine `_brand_axis` precedent). No logger, no log line, no I/O, no string literal holding a host. Every public function is pure and total (never raises). Arabic words are built with `chr()` from the code points below.

Constants (each word set is folded with `_cg.normalize` at import, so both sides of every comparison use the same fold):
- `FLAG_ENV = "ENABLE_IMAGE_RELEVANCE_GUARD"`, `KNOB_ENV = "IMAGE_RELEVANCE_CANDIDATES"`, `KNOB_DEFAULT = 5`, `KNOB_MAX = 10`.
- `FRAGRANCE_CATEGORY = "fragrances"` (the canonical key, extraction_service.py:1185-1186).
- `FRAGRANCE_WORDS` = fold of: perfume, parfum, eau, edt, edp, cologne, fragrance, and the Arabic word for perfume U+0639 U+0637 U+0631 (I1-3 verbatim; plurals: OQ-2).
- `CONCENTRATION_WORDS` = fold of the lexicon's concentration terms: eau, de, parfum, parfums, toilette, cologne, extrait, elixir, fraiche, edp, edt, edc, and the Arabic tokens U+0627 U+0648 (the folded U+0623 U+0648), U+062F U+0648, U+0628 U+0627 U+0631 U+0641 U+0627 U+0646, U+062A U+0648 U+0627 U+0644 U+064A U+062A.
- `STOP_WORDS` = fold of: the, a, an, and, of, for, by, with, in, on, at, to, de, du, des, la, le, les, el, al, di, da, del, pour, et.
- `BRAND_NOISE` = fold of: maison, parfums, perfumes, house.
- `PLACEHOLDER_BRANDS = frozenset({"unknown", "generic", "brand", "na", "none", "null", "unbranded", "nobrand", "other"})` (compared with the brand's folded tokens joined without spaces).
- `BRAND_EXCLUDE = STOP_WORDS | FRAGRANCE_WORDS | CONCENTRATION_WORDS | BRAND_NOISE`.
- `NAME_EXCLUDE = STOP_WORDS | CONCENTRATION_WORDS | FRAGRANCE_WORDS | fold(ml, oz, fl, spray)`.
- `SIZE_TOKEN = re.compile(r"[0-9]+(?:\.[0-9]+)?(?:ml|oz|g|gm)")` (fullmatch on a folded token).
- `EXTRA_ALIAS_GROUPS = (frozenset({"bvlgari", "bulgari"}),)`.
- `TEXT_MAX_CHARS = 512` (each text part and each name is cut before folding: the ps:5204 `_MATCH_INPUT_CAP` precedent), `SEARCH_ITEMS_MAX = 20` (items walked per organic / images list and per Tier-3 organic list), `JSONLD_IMAGES_MAX = 10`.
- Closed vocabularies: `TIERS = ("none", "piggyback", "search_payload", "serper_images", "llm_pick")`, `OUTCOMES = ("accepted", "rejected", "none")`, `REASONS = ("none", "scheme", "brand", "name", "fragrance_word")`.

Functions:
1. `guard_enabled()`, `candidates_knob()`: 2.1.
2. `alias_groups() -> Tuple[FrozenSet[str], ...]`: `tuple(price_service._BRAND_ALIAS_GROUPS) + EXTRA_ALIAS_GROUPS` through a function-local import; on any exception, `EXTRA_ALIAS_GROUPS` alone.
3. `relevance_kwargs(brand, line, category, slot, is_vision) -> Dict[str, Any]` (the scs seam): FIRST statement `if not guard_enabled(): return {}`; then `if is_vision: return {}` (the camera path stays the base path, I1-1); else `{"relevance": {"brand": <brand if str else "">, "line": <line if str else "">, "category": <category if str else "">, "slot": <slot if it is an int (not a bool) in (0, 1) else None>}}`.
4. `identity(product_name, relevance) -> Identity` (a frozen dataclass: `brand_empty: bool`, `brand_forms: frozenset`, `brand_joined: str`, `name_tokens: frozenset`, `fragrance: bool`):
   - `rel` = relevance if a dict else {}; `brand` = rel["brand"] if a str else ""; `line` = rel["line"] if a non-blank str else `product_name` (if a str, else ""); `fragrance` = rel["category"] is a str whose `.strip().lower() == "fragrances"`.
   - `folded = _cg.normalize(brand[:512])`; `placeholder = "".join(folded) in PLACEHOLDER_BRANDS`; `kept = [t for t in folded if t not in BRAND_EXCLUDE]`; `brand_tokens = frozenset()` if placeholder else `{t for t in kept if len(t) >= 2}`.
   - `brand_forms = brand_tokens` united with every group of `alias_groups()` that intersects `brand_tokens` (the RS2 expansion, ps:6943-6946); `brand_joined = "".join(kept)` when `brand_tokens` is non-empty and not placeholder, else "" (so `tomford` matches the host `www.tomford.com`).
   - `brand_empty = not brand_tokens`.
   - `name_tokens = {t for t in _cg.normalize(line[:512]) if len(t) >= 2 and t not in NAME_EXCLUDE and not SIZE_TOKEN.fullmatch(t) and t not in brand_forms}` (stop words, concentration words, fragrance words, size tokens and the brand's own forms never count as a line token).
5. `check(ident, texts, hosts) -> Optional[str]` (None = pass, else the FIRST failing reason; I1-3):
   - `t` = the union of `set(_cg.normalize(s[:512]))` over the `texts` that are str; `h` = the union of `set(_cg.normalize(host))` over the hosts of the `hosts` values (`_host(v)`: a str, stripped; `"//"` prefixed when it has no `"://"`; `urlsplit(...).hostname` or ""; a ValueError -> ""; trailing dot and a leading `www.` removed).
   - brand non-empty: `if not (ident.brand_forms & (t | h)) and not (ident.brand_joined and ident.brand_joined in h): return "brand"`; `if not (ident.name_tokens & t): return "name"`; `return None`.
   - brand empty: `if not (ident.name_tokens & t): return "name"`; `if not (FRAGRANCE_WORDS & t): return "fragrance_word"`; `return None`.
   - Host tokens serve the BRAND test only (I1-3 "(a) ... from the title or as the source / host"); the line and fragrance tests read the text only (precision first; a host such as `sauvage.example` never proves the line).
   - The fragrance-word arm applies to EVERY category when the brand is empty (I1-3 verbatim; OQ-1 proposes limiting it to fragrances and other).
6. `image_query(product_name, ident) -> str`: `product_name + " perfume"` when `ident.fragrance`, else `product_name` unchanged (I1-4: `product_name` is scs's `full_name` = `<brand> <name> <variant>` deduplicated, scs:1389, so the concentration rides it when Step 1 knows it; "perfume" only for the fragrance category).
7. `first_https_raster(value) -> Optional[str]` (the noon seam, I1-7): `urls = price_service._jsonld_image_urls(value)` (function-local import; any exception -> None); for `u` in `urls[:10]`: `ok = _jw.allowed_image_url(u, u)`; the first truthy `ok` is returned; else None. Passing the image URL as its own page URL satisfies ONLY the host allowlist (jw:156-160 first-party rule), so the one D08 policy still demands https, a netloc without `@`, a public host (no IP literal, no `.test` / `.local`), a raster PATH extension, no unsafe character and no DENY_HOSTS host.
8. `class RelevanceCall` (one per cascade call; plain attributes, no shared state):
   - `__init__(product_name, relevance)`: `self.product_name`; `self.ident = identity(product_name, relevance)`; `self.slot` = `"0"` / `"1"` when `relevance["slot"]` is the int 0 / 1 (not a bool), else `"-"`; `self.n = 0`; `self.accepted_tier = None`; `self.last_tier = "none"`; `self.last_reason = "none"`; `self._num = None`.
   - `query()` -> `image_query(self.product_name, self.ident)`.
   - `num()` -> the knob, read ONCE per call through the module attribute `candidates_knob()` (memoized in `self._num`).
   - `accept(tier, url, texts=(), hosts=()) -> bool`: `self.n += 1`; `reason = "scheme"` when `url` (already stripped and base-valid) does not start with `"https://"`, else `check(self.ident, texts, hosts)`; None -> `self.accepted_tier = tier`, True; else `self.last_tier, self.last_reason = tier, reason`, False.
   - `accept_scheme(tier, url) -> bool`: the same with the scheme test only (the piggyback tier: the page image of the priced product itself, no text to test).
   - `organic_passes(organic) -> bool`: True when some dict item of `organic[:20]` has `check(self.ident, (item.get("title"),), (item.get("link"),)) is None`; counts nothing.
   - `accept_pick(url, organic) -> bool` (Tier 3): `self.n += 1`; scheme first; then the dict items of `organic[:20]` whose `link` host is related to the pick's host (`_related(a, b)`: both non-empty after the www strip and equal, or one ends with `"." +` the other); the pick passes when ONE related item passes `check(ident, (title,), (link,))`; with no related item the candidate's text is empty: `check(ident, (), ())` gives "brand" (brand known) or "name" (brand empty); with related items that all fail, the first related item's reason; record as in `accept`.
   - `summary() -> Tuple[str, str, str, int, str]`: accepted -> `(slot, accepted_tier, "accepted", n, "none")`; else n > 0 -> `(slot, last_tier, "rejected", n, last_reason)`; else `(slot, "none", "none", 0, "none")`.

Truth table of `check` (the RED row A-R03; identity = (brand, line, category); texts / hosts as given; BY READING the rules above):

| # | brand / line / category | texts ; hosts | result |
|---|---|---|---|
| T1 | "" / "Tyger" / fragrances | "The Tyger by William Blake", "Poetry Foundation" ; a poem page link | fragrance_word |
| T2 | "" / "Tyger" / fragrances | "The Tyger" (a KG title) ; - | fragrance_word |
| T3 | "Bvlgari" / "Tygar" / fragrances | "Bulgari Le Gemme Tygar Eau de Parfum 125ml" ; - | None (the local alias group) |
| T4 | "Bvlgari" / "Tygar" / fragrances | "BVLGARI TYGAR" ; - | None (casefold) |
| T5 | "Dior" / "Sauvage EDP" / fragrances | "Sauvage Eau de Parfum" ; `https://www.dior.com/en_us/p/x` | None (the brand from the host) |
| T6 | "Dior" / "Sauvage" / fragrances | "Sauvage Eau de Toilette", "Dior" (source) ; - | None (the brand from the source) |
| T7 | "Dior" / "Sauvage" / fragrances | "Zara Sauvage Spray" ; - | brand |
| T8 | "Chanel" / "Bleu de Chanel EDP" / fragrances | "Chanel No 5 Eau de Parfum" ; - | name (line tokens = {bleu}) |
| T9 | "" / "Aventus" / fragrances | "Creed Viking Eau de Parfum" ; - | name |
| T10 | "Lanc"+chr(0xF4)+"me" / "Id"+chr(0xF4)+"le" / fragrances | "Lancome Idole Eau de Parfum" ; - (and the reverse: plain identity, accented title) | None (accent fold) |
| T11 | "" / "Tyger" / fragrances | "Tyger " + the Arabic perfume word (chr) ; - | None |
| T12 | "Sefiki" / "Limited Edition" / fragrances | "Sefiki men watch" (T01 fixture c) ; - | name |
| T13 | "" / "Shahrazad L'Intense" / fragrances | "Violin" (T01 fixture b, the KG title) ; - | name |
| T14 | "" / "Sauvage EDP" / fragrances | "Bleu de Chanel EDP" ; - | name (edp is no line token) |
| T15 | "Chanel" / "Bleu de Chanel" / fragrances | "Chanel Coco Mademoiselle parfum" ; - | name (the brand token in the line never counts) |
| T16 | "Parfums de Marly" / "Layton" / fragrances | "Layton parfums review" ; - | brand (a fragrance / noise word is never a brand token) |
| T17 | "Unknown" / "Tyger" / fragrances | "The Tyger" ; - | fragrance_word (a placeholder brand = empty) |
| T18 | "Dior" / "Sauvage" / fragrances | "Dior official site" ; `https://sauvage.dior.com/` | name (host tokens never prove the line) |
| T19 | "Tom Ford" / "Ombre Leather" / fragrances | "Ombre Leather Eau de Parfum" ; `https://www.tomford.com/x` | None (the joined brand on the host) |
| T20 | "" / "iPhone 15" / electronics | "Apple iPhone 15 128GB" ; - | fragrance_word (literal I1-3; None if OQ-1 is ruled yes) |

### 2.3 image_service changes (img)

- Import (after img:48): `from app.services import image_relevance as _relevance` (module attribute: a patch of a leaf function takes effect at call time).
- `get_product_image_url(..., search_payload=None, relevance: Optional[Dict[str, Any]] = None)`: one NEW keyword-only parameter, LAST, default None; one docstring Args line ("INC-I1: the identity for the picture-must-match guard (scs passes it for text compares only under ENABLE_IMAGE_RELEVANCE_GUARD); None = the base cascade").
- After the empty-name return (img:255-257, unchanged, logs nothing) and before `_t_call`:
```
    # INC-I1 (ENABLE_IMAGE_RELEVANCE_GUARD, read per call): the guard runs for this call
    # only when the caller handed the identity AND the flag reads ON; otherwise every
    # tier below is the base path, byte for byte.
    _rel = None
    if relevance is not None and _relevance.guard_enabled():
        _rel = _relevance.RelevanceCall(name, relevance)
```
  (The OFF production path, where scs passes no keyword, reads nothing new here; with the flag OFF and a keyword given the only new work is one env read.)
- Tier 1.5 (img:264): the condition gains `and (_rel is None or _rel.accept_scheme("piggyback", page_scrape_image.strip()))`; the `[IMG_TIER]` / `[image]` lines and the return are unchanged.
- Tier 1.5b (img:276): `search_img = extract_image_from_search(search_payload) if _rel is None else _extract_relevant_image_from_search(search_payload, _rel)`; the rest unchanged.
- Tier 1 (img:295): `response = await search_images(name, num_results=1)` when `_rel is None`, else `await search_images(_rel.query(), num_results=_rel.num())`; the pick (img:301-311) is the base block when `_rel is None`, else `candidate = _relevant_serper_image(images, _rel)`; a non-None candidate takes the base hit lines and `return candidate`; otherwise the base `_log_img_tier("serper_images", _outcome, ...)`. The budget gate (img:286-289) is unchanged: one credit per call.
- Tier 3 (img:319 and :327): `if organic_results and (_rel is None or _rel.organic_passes(organic_results)):` (no passing organic result = no LLM call; the base `else` logs `llm_pick skipped`); the hit condition becomes `if _is_valid_image_url(gpt_url) and (_rel is None or _rel.accept_pick(gpt_url.strip(), organic_results)):`. The call `extract_image_via_gpt(name, organic_results)` is unchanged (same name, same full organic list, same prompt).
- After the CancelledError arm (img:338-344, byte-identical):
```
    finally:
        if _rel is not None:
            _log_img_relevance(_rel)
```
- New module helpers (between `_log_img_tier`, img:220-225, and the Orchestrator banner, img:228):
  - `_first_image(item, keys) -> Optional[str]`: the stripped first value among `keys` that passes `_is_valid_image_url` AND starts with `https://`; else the stripped first value that passes `_is_valid_image_url` (an http one, so `accept` rejects it with reason scheme and counts it); else None.
  - `_extract_relevant_image_from_search(search_payload, rel) -> Optional[str]`: non-dict -> None; for each present KG dict (`knowledgeGraph`, then `knowledge_graph`): `url = _first_image(kg, ("imageUrl", "image", "imageURL", "thumbnailUrl"))`, accepted when `rel.accept("search_payload", url, texts=(kg.get("title"),))`; then each dict item of `organic[:20]`: `_first_image(item, _ORGANIC_IMAGE_KEYS)` with `texts=(title,)`, `hosts=(link,)`; then each dict item of `images[:20]`: `texts=(title, source)`, `hosts=(link, domain)`; the first accepted URL is returned; else None. The base precedence (KG, organic, images) is kept.
  - `_relevant_serper_image(images, rel) -> Optional[str]`: non-list -> None; for each dict item of `images[:rel.num()]`: `candidate = item.get("imageUrl")`; skipped unless `_is_valid_image_url(candidate)` (not a candidate then); `url = candidate.strip()`; accepted when `rel.accept("serper_images", url, texts=(item.get("title"), item.get("source")), hosts=(item.get("link"), item.get("domain")))`; the first accepted is returned; else None.
  - `_log_img_relevance(rel) -> None`: `slot, tier, outcome, n, reason = rel.summary()`; `logger.info("[IMG_RELEVANCE] product=%s tier=%s outcome=%s candidates=%d reason=%s", slot, tier, outcome, n, reason)`.
- `extract_image_from_search` (img:85-129), `_is_valid_image_url` (img:57-67), `extract_image_via_gpt` and `_TIER3_PROMPT` are NOT edited.
- `[IMG_TIER]` under the flag (no new tier name, no new outcome word): a rejected KG / organic / images item = `search_payload miss`; every Serper item rejected = `serper_images miss`; no passing organic result = `llm_pick skipped`; a rejected pick = `llm_pick miss`; an http piggyback = `piggyback miss`.

### 2.4 scs change (the one call site)

- Import after scs:1596: `from app.services import image_relevance as _image_relevance` (module attribute).
- In the image task (scs:6261-6270), after `search_payload=unified_search,`:
```
                    # INC-I1 (ENABLE_IMAGE_RELEVANCE_GUARD, read per call): the identity
                    # for the picture-must-match guard; flag OFF or a camera product ->
                    # {} and the call is the base call.
                    **_image_relevance.relevance_kwargs(brand, name, category, partial_slot, is_vision),
```
  `brand`, `name`, `category` (canonical), `is_vision` are the `_fetch_product_data` locals (scs:5966-5974); `partial_slot` its parameter (0 / 1 on both orchestrator paths, None for every other caller). The KB branch of the conditional is untouched (the keyword is evaluated only when the cascade runs). No other scs line changes: the override (scs:6396-6429) stays as it is (I1-1).

### 2.5 noon change (I1-7)

- Import with the app imports (after noon:93): `from app.services import image_relevance as _image_relevance`.
- In `_confirm_pdp`, after the brand stamp (noon:465-466) and before `return price` (noon:467):
```
    # INC-I1 (ENABLE_IMAGE_RELEVANCE_GUARD, read per call; OFF: no key, the base dict):
    # the PDP's own Product JSON-LD image (its first https raster URL) rides the price
    # dict, so the post-Phase-1 page-image override can show the priced product's picture.
    if _image_relevance.guard_enabled():
        _image = _image_relevance.first_https_raster(product.get("image"))
        if _image:
            price["image_url"] = _image
```
- No new log line; the flag OFF never reads `product["image"]`. The image is the confirmed PDP's own (its identity gates ran at noon:425; showable and content safety run after, noon:528-539), so no relevance test applies (the same-page rule, R2 layer 1).

### 2.6 The log line (I1-8)

- Exactly ONE INFO record per `get_product_image_url` call that passes the empty-name check while the guard runs (normal return, an uncaught exception, or the 5 s cancellation: the `finally`), logger `app.services.image_service`:
  `[IMG_RELEVANCE] product=<0|1|-> tier=<none|piggyback|search_payload|serper_images|llm_pick> outcome=<accepted|rejected|none> candidates=<int> reason=<none|scheme|brand|name|fragrance_word>`
- `candidates` = every image URL the guard tested (a base-valid URL on any tier, the Tier-3 pick included; organic results read only for the Tier-3 precondition are not candidates). `reason` = the reason of the LAST rejection when the outcome is rejected; `none` when accepted or nothing was tested (the brief's reason set has no value for these two cases: OQ-7).
- Grammar regex (RED A-R14): `^\[IMG_RELEVANCE\] product=(0|1|-) tier=(none|piggyback|search_payload|serper_images|llm_pick) outcome=(accepted|rejected|none) candidates=\d+ reason=(none|scheme|brand|name|fragrance_word)$`.
- Never a product name, URL, query, title or source text. The INC-X2a lines are unchanged and still match tests/test_inc_x2a_image_tier_timing.py:32-36 under the flag. Volume: at most 2 lines per compare (one per product), 0 with the flag OFF or for a KB-served image.

### 2.7 Test seams [production values]

`image_service.try_consume_serper_image_credit` [ab's daily Redis counter], `image_service.search_images` [ss.search_images], `image_service.extract_image_via_gpt` [the real Tier 3 through the router], `image_service._is_valid_image_url` [img:57-67], `image_relevance.guard_enabled` / `candidates_knob` [the env readers], `image_relevance.alias_groups` [ps._BRAND_ALIAS_GROUPS + EXTRA_ALIAS_GROUPS], `noon._http_get` [the curl_cffi GET in a thread], `noon._polite_sleep` [0.8-1.2 s], `noon.is_circuit_closed` / `record_failure` / `record_success` [the ab breaker], `noon.ENABLE_PAGE_SCRAPE` [True], `scs.get_product_image_url` [img's], `scs._image_relevance` [the leaf], `jsonld_widen.image_pipeline_v2_enabled` / `deny_hosts.data_guards_v2_enabled` [OFF / OFF on web, 1.8], `ENABLE_EXACT_PRICE_GATE` [ON].

### 2.8 Flag-OFF identity (the main invariant)

Proof obligations, each pinned (section 5):
- F1 scs: flag OFF (unset or any falsy spelling), with the FULL unit configuration present (the knob set to "7", ENABLE_EXACT_PRICE_GATE true): the `get_product_image_url` call receives exactly `(full_name,)` and the keyword set {region, page_scrape_image, organic_results, search_payload} with the base values (B-P02); camera products never get the keyword even with the flag ON (B-P03).
- F2 img: flag OFF with `relevance=` GIVEN behaves exactly as the base call without it: the same budget calls `[(1,)]`, the same Serper call `((name,), {"num_results": 1})`, `images[0]` taken, the same Tier-3 call, the same return value, the same `[IMG_TIER]` pairs, no `[IMG_RELEVANCE]` record, the knob reader never called (A-R16).
- F3 img: flag ON WITHOUT `relevance` (the camera path, a legacy caller) = the base call (A-P02).
- F4 img: `extract_image_from_search` and `_is_valid_image_url` are byte-identical functions (A-P03, A-P04); the CancelledError arm is byte-identical (the X2a R2-7 AST row).
- F5 noon: flag OFF with an https image in the Product JSON-LD: the price dict has no `image_url` and its key set equals the base set (B-P01); the noon search / PDP request sequence is unchanged (the existing noon rows).
- F6 the reader table: ON for "true", " TRUE ", "1", "yes", "On"; OFF for unset, "", "false", "0", "no", "off", "garbage", "tru e" (A-R01).
- F7 no new log line at flag OFF; no new Redis, HTTP or LLM call at flag OFF; the knob is not read at flag OFF.
- F8 the leaf adds no module-level import beyond the stdlib, cg and jw (A-R06), so the import at app start loads nothing new (cg and jw are already loaded by scs).
- F9 every existing pin of 1.11 stays green unedited (section 4.2), and the comm set shows no new failure (section 7).
Mid-flip: scs and img each read the flag once per product; a disagreement degrades to the base path (scs OFF -> no keyword; img OFF -> keyword ignored). noon reads it once per PDP confirm.

### 2.9 Failure table (flag ON)

| Failure | User-visible result | Log |
|---|---|---|
| Every candidate of every tier rejected (the Tyger poem) | the placeholder tile (`image_url` null) | `[IMG_TIER]` miss / skipped lines; `[IMG_RELEVANCE] ... outcome=rejected ... reason=<last>` |
| No candidate at all (no payload, budget denied, no images, no passing organic) | placeholder | `[IMG_RELEVANCE] ... tier=none outcome=none candidates=0 reason=none` |
| Serper Images raises | next tier (unchanged) | base WARNING + `error:<Type>` |
| A malformed Serper body (images not a list, items not dicts, no imageUrl) | next tier | `serper_images miss` |
| A malformed `relevance` (non-str fields, missing keys) | coerced to "" (line falls back to the product name): the brand-empty rule applies | normal lines |
| The price_service import fails inside the leaf | `alias_groups()` -> EXTRA only; `first_https_raster` -> None (no noon picture) | none (total functions) |
| The 5 s race cancels the call | placeholder (base) | the X2a cancelled line + one `[IMG_RELEVANCE]` line (the `finally`) |
| A noon JSON-LD `image` that is http, svg, on an IP / private host, denied or malformed | no `image_url` key: the cascade picture stands | none |
| ENABLE_IMAGE_PIPELINE_V2 ON with a noon price | D08 refuses `f.nooncdn.com`: the cascade picture stands | none |

### 2.10 Response contract and class

- Every new key and its type: (1) the keyword `relevance` of `image_service.get_product_image_url`: `Optional[Dict[str, Any]]`, default None, shape `{"brand": str, "line": str, "category": str, "slot": int 0 / 1 or None}` (built only by `image_relevance.relevance_kwargs`); (2) `price["image_url"]` in the noon price dict: `str` (an https raster URL on a public host, the first such member of the PDP's Product `image`), present only under the flag and only when one passes; (3) no response key is added: `price.image_url` already exists as an optional member of price objects; (4) one log prefix `[IMG_RELEVANCE]` (2.6). No new env name beyond the flag and the knob; no new Redis key, table, host or dependency.
- Keys: no key removed, renamed or retyped. `overview.products[i].image_url` / `products[i].image_url` keep their type (str or null; under the flag an https cascade URL or the override's page image). `price.image_url` gains a value for a noon-won price under the flag (an existing optional member, 2 intro). The SSE `specs` payload and `/home/smart-pick` read the same product field. No envelope, no refusal, no code, no status change; never a bare 503 (the unit raises nothing).
- Class (I1-10): SAFE by the footprint (no auth, quota, legal, consent, security middleware, migration, Redis / Lua, client or secret surface); the one response-visible key value above is reported for the orchestrator's classification (OQ-11).

### 2.11 Flag-mix walk (every mix the rollout can produce)

| Mix | Effect (BY READING) |
|---|---|
| I1 ON, INC-R1 OFF (the first window) | every app compare has brand "": a picture needs a line token plus a fragrance word; the query is `<typed name> perfume` for fragrances; "Tyger" pictures need "tyger" + a fragrance word (the poem fails); "stronger with you" pictures titled "... Stronger With You ... EDT" pass |
| I1 ON, INC-R1 ON | the resolved brand / line: the brand test plus the line test; the query `<Brand> <Line> <Conc> perfume`; "Bvlgari" + "Tygar" with a "Bulgari" title passes through the local alias group |
| I1 ON, V2 ON | the noon image is refused by D08's allowlist (1.4); every other page image follows D08 as today |
| I1 ON, ENABLE_DATA_GUARDS_V2 ON | the deny list stays inside `_is_valid_image_url` for every candidate; https on top |
| I1 ON, ENABLE_KB_FIRST_SERVE ON | a KB image is served instead of the cascade (no guard on it; kb_serve.py:323 already demands https) |
| I1 ON, ENABLE_FRAGRANCE_ONLY_GATE OFF | a non-fragrance compare with an empty brand gets the placeholder (literal I1-3; OQ-1) |
| I1 ON, consent 3 (Claude text) / below 3 (OpenAI egress stop) | Tier 3 runs on Claude only when an organic result passes; below consent 3 it fails locally as today (no AI text is needed anywhere in this unit) |
| I1 ON then OFF (rollback) | the OFF path is the base path; noon prices cached in L1 while ON keep `image_url` up to their TTL (L-I1-10) |

---------------------------------------------------------------------------------------------------

## 3. Change list (in the order GREEN applies it)

1. Byte-copy (shutil.copyfile) every existing file below into `<SP>/INC-I1/green_before/` and record its sha256: app/services/image_service.py, app/services/noon_service.py, app/services/structured_comparison_service.py, CLAUDE.md, .github/black-clean-paths.txt.
2. NEW app/services/image_relevance.py exactly as 2.2 (pure ASCII, LF, black 26.5.1 clean, ruff E9/F63/F7/F82 clean; Arabic words from `chr()` code points).
3. img: the import (2.3) after img:48.
4. img: the four helpers `_first_image`, `_extract_relevant_image_from_search`, `_relevant_serper_image`, `_log_img_relevance` between img:225 and the banner at img:228.
5. img: `get_product_image_url`: the `relevance` keyword (last) + its docstring line; the `_rel` setup after img:257; the guarded conditions at img:264, :276, :295, :301-311, :319, :327; the `finally` after img:344. No other line of img changes; the X2a bookkeeping and the CancelledError arm stay byte-identical.
6. scs: the import after scs:1596 and the one keyword expression in the image task after scs:6269 (2.4). No other scs line.
7. noon: the import after noon:93 and the block before noon:467 (2.5). No other noon line.
8. CLAUDE.md: the block of section 8 after the S81-07c block (after :682, before `## Tests` at :684, one blank line before its heading); the :341 Feature Flags clause appended after the S81-07c sentence; the one sentence appended to the :313 image paragraph. Pure ASCII.
9. .github/black-clean-paths.txt: append `app/services/image_relevance.py`, `tests/test_inc_i1_picture_must_match.py`, `tests/test_inc_i1_noon_and_wiring.py` at the end (the ratchet rule, :15-18; the MON1 precedent) (OQ-9).
No other file: no requirements*, no package files, no SmartCompareApp/ file, no .githooks, no tests/.pre_impl_failures.txt, no processors.json row (no new host), no migration, no fixture, no edit of price_service, jsonld_widen, category_gate, kb_serve or the router. The RED files are the RED agent's (frozen at the gate). Estimated diff: the leaf about 230 lines; img about 95 added / 6 changed lines (no re-indent); scs 5 lines; noon 9 lines; CLAUDE.md 4 lines changed or added; the black list 3 lines.

---------------------------------------------------------------------------------------------------

## 4. Existing pins

### 4.1 Pins that change deliberately (E-rows)

NONE (measured, 1.11): no test asserts the signature or the exact keyword set of `get_product_image_url`, the key set of the noon price dict, the absence of an image_service INFO record (the two `caplog.records == []` pins, tests/test_s78_serper_key_memo.py:615 and tests/test_w4_7_confidence_single_computation.py:700, do not reach img with the flag ON), or the text of CLAUDE.md:313 / :341. If the RED agent finds one, it is an E-row for the gate (never weakened).

### 4.2 Pins that must stay green unedited

Every file of 1.11, by name: tests/test_image_service.py, test_image_service_edges.py, test_image_service_longtail.py, test_image_knowledge_graph_tier.py, test_inc_x2a_image_tier_timing.py, test_inc_g1_gate_rows.py, test_comparison_response_image_url.py, test_noon_adapter.py, test_s81_d08_jsonld_widen.py, test_s81_d03_deny_and_guards.py, test_s81_s07c_role_fix.py, test_s81_s06_anthropic_router.py, test_s81_s22b_self_critique_retire.py, test_s81_s07_meas_harness.py, test_s81_s12d_openai_egress_stop.py, test_model_config_enforced.py, test_prompt_fence.py (+ tests/w4_11_prompt_digest_recorder.py and its digest fixture), test_s81_s18_kb_first_serve.py (+ tests/fixtures/s81_s18_flag_off_golden.json), test_s75_fanout_identity.py (the FY25 digests), test_serper_budget_gate.py, test_serper_record_usage.py, test_s78_serper_key_memo.py; test_legal_docs_u8.py (T7b), test_ci_gates.py (the black allowlist check, the CLAUDE.md readers), test_sentry_channels_u8d_unit.py, test_openai_key_log_hygiene_s69.py, test_hermeticity_pins.py; and the whole comm set (section 7).

---------------------------------------------------------------------------------------------------

## 5. RED tests

### 5.1 Harness rules for both files

- New files only: `tests/test_inc_i1_picture_must_match.py` (A) and `tests/test_inc_i1_noon_and_wiring.py` (B); pure ASCII, LF; black 26.5.1 clean (they join the black list, OQ-9).
- Nothing the unit creates is imported at module top. File A imports `app.services.image_service as img` at top (it exists); the leaf only through `_leaf()`: `spec = importlib.util.find_spec("app.services.image_relevance")`, `assert spec is not None, "INC-I1 not built: app/services/image_relevance.py is missing"`, then `importlib.import_module(...)` (an AssertionError at base, never ModuleNotFoundError). Every row that passes `relevance=` first runs `_assert_kw()`: `assert "relevance" in inspect.signature(img.get_product_image_url).parameters` (never a TypeError at base).
- An autouse fixture `monkeypatch.delenv`s `ENABLE_IMAGE_RELEVANCE_GUARD`, `IMAGE_RELEVANCE_CANDIDATES`, `ENABLE_DATA_GUARDS_V2`, `ENABLE_IMAGE_PIPELINE_V2` (raising=False); each row sets what it needs with `monkeypatch.setenv` (conftest loads the developer .env with override, so every flag is set per row).
- File A recorders: the X2a `_install` pattern (tests/test_inc_x2a_image_tier_timing.py:66-96) on the module attributes `img.try_consume_serper_image_credit` (records `(n,)`), `img.search_images` (records `((query,), kwargs)`, returns `{"images": [...]}`, optional hang), `img.extract_image_via_gpt` (records `(name, organic)`, returns a URL or raises); `caplog.set_level(logging.INFO, logger="app.services.image_service")`; `asyncio.run` drives the coroutine; sentinels built at run time (`POEM = "https://" + "poem.example.test" + "/tyger.jpg"`, `NAME = "Ty" + "ger"`, ...).
- File B noon harness: re-implemented locally (not imported from tests/test_noon_adapter.py): `FakeResp`, `_pdp_html(product)`, `_install_http(monkeypatch, search_results, pdp_pages)` patching `noon._http_get`, the quiet breaker (`noon.is_circuit_closed` -> True, `record_failure` / `record_success` MagicMocks, `noon._polite_sleep` no-op), `monkeypatch.setattr(noon, "ENABLE_PAGE_SCRAPE", True)`, `monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")` [prod ON]; the iPhone hit and PDP shapes of tests/test_noon_adapter.py:68-102 plus an `image` member. Noon image literals carry SHORT paths with no digit run of eight or more (e.g. `"https://" + "f.nooncdn.com" + "/p/pzsku/ZT1/45/_/x1/a1.jpg?width=1200"`), the measured host kept so the D08 public-host and allowlist checks see the real shape.
- File B scs harness: the pattern of tests/test_comparison_response_image_url.py:89-135 (`get_comparison_service()`; `patch.object` on `_get_specs`, `_get_price`, `_get_reviews`, `_get_verified_rating`; `scs.search_web`, `scs.tier2_fill_non_negotiables`, `scs.tier3_synthesize_non_negotiables` patched; `scs.get_product_image_url` an `AsyncMock` recorder), driving `service._fetch_product_data(product_info, region="bahrain", include_specs=True, include_reviews=True, nocache=True, partial_slot=<0|1|None>)`; the RED agent adds any leg a fragrance-category product needs (no network: the netguard fails the row otherwise).
- Assertions on fields and recorded calls, never on a substring of a body carrying a random id. Every RED row fails at base on an AssertionError ONLY; every PIN row is green at base and runs with the FULL configuration (the knob set to "7", ENABLE_EXACT_PRICE_GATE true, the flag in the stated state) plus the call recorders, so a gated mutant is killable (ruling B1).
- After writing, the RED agent runs the readers that see new test files: tests/test_ci_gates.py (it walks `tests/test_*.py` for the live_prod ratchet, :760, :779, and checks the black allowlist) and tests/test_hermeticity_pins.py (the netguard baseline tests/.network_attempt_baseline.txt, :975: the two files must add no network attempt), and `black --check` (the venv's black 26.5.1) on both files.

### 5.2 File A: tests/test_inc_i1_picture_must_match.py (the leaf and the cascade)

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| A-R01 | `test_r01_flag_reader_table` | `guard_enabled()` True for "true", " TRUE ", "1", "yes", "On"; False for unset, "", "false", "0", "no", "off", "garbage", "tru e" | RED (leaf missing) | 2.1 |
| A-R02 | `test_r02_knob_table` | `candidates_knob()`: unset 5, "" 5, "abc" 5, "inf" 5, "nan" 5, "0" 5, "-3" 5, "1" 1, " 7 " 7, "7.9" 7, "10" 10, "15" 10 | RED (leaf missing) | 2.1 |
| A-R03 | `test_r03_relevance_truth_table` (parametrized T1-T20 of 2.2) | `check(identity(NAME, rel), texts, hosts)` equals the table's result | RED (leaf missing) | 2.2 (4, 5) |
| A-R04 | `test_r04_image_query` | ("Tyger", fragrances) -> "Tyger perfume"; ("Dior Sauvage EDP", fragrances) -> "Dior Sauvage EDP perfume"; ("iPhone 15", electronics) -> "iPhone 15"; ("X", other) -> "X" | RED | 2.2 (6) |
| A-R05 | `test_r05_first_https_raster` | the noon list (three https f.nooncdn.com jpg?width=1200) -> the first; ["http://h.example.com/a.jpg", "https://h.example.com/b.png"] -> b; [ImageObject url c.webp] -> c; {"contentUrl": d.jpg} -> d; ["https://h.example.com/e.svg"] -> None; ["https://10.0.0.1/f.jpg"] -> None; a fimgs.net jpg -> None; None / 42 / {} -> None | RED | 2.2 (7) |
| A-R06 | `test_r06_leaf_import_shape` | AST of the leaf source: module-level imports only `__future__`, stdlib roots (`sys.stdlib_module_names`), `app.services.category_gate`, `app.services.jsonld_widen`; `price_service` imported only inside function bodies; no module-level `logging.getLogger`; no string constant matching `https?://[A-Za-z0-9.-]+\.[A-Za-z]{2,}` | RED | 2.2 module level |
| A-R07 | `test_r07_alias_reuse` | `alias_groups() == tuple(price_service._BRAND_ALIAS_GROUPS) + EXTRA_ALIAS_GROUPS` and `EXTRA_ALIAS_GROUPS == (frozenset({"bvlgari", "bulgari"}),)` | RED | 2.2 (2) |
| A-R08 | `test_r08_tyger_poem_rejected_at_tier1` | flag "true"; rel {brand "", line "Tyger", category "fragrances", slot 0}; payload None; organic = [one poem result titled "The Tyger by William Blake"]; Serper returns [{title "The Tyger by William Blake", source "Poetry", link poem page, imageUrl POEM}] -> returns None; `rec.search == [(("Tyger perfume",), {"num_results": 5})]`; `rec.budget == [(1,)]`; `rec.gpt == []`; `[IMG_TIER]` pairs include ("serper_images", "miss"), ("llm_pick", "skipped"); ONE line `[IMG_RELEVANCE] product=0 tier=serper_images outcome=rejected candidates=1 reason=fragrance_word` | RED (no keyword) | 2.3, 2.6 |
| A-R09 | `test_r09_kg_poem_rejected_tier1_bottle_accepted` | rel {brand "Bvlgari", line "Tygar", fragrances, slot 1}; payload {knowledgeGraph: {title "The Tyger", imageUrl POEM}}; Serper [{title "Bulgari Tygar Eau de Parfum", imageUrl BOTTLE}] -> BOTTLE; pairs ("search_payload", "miss"), ("serper_images", "hit"); line `product=1 tier=serper_images outcome=accepted candidates=2 reason=none` | RED | 2.3 |
| A-R10 | `test_r10_walk_order_and_knob` | rel {Bvlgari, Tygar}; Serper returns [poem, http bottle (title passes), bottle A https (passes), bottle B https (passes)]; knob "3": `rec.search[0][1] == {"num_results": 3}` and the result is A, candidates=3; knob "2": the walk stops after two items -> None (organic None), line `outcome=rejected candidates=2 reason=scheme` | RED | 2.3 `_relevant_serper_image` |
| A-R11 | `test_r11_https_on_every_tier` | (a) piggyback `http://...` + a passing https KG image -> the KG image; pairs ("piggyback", "miss"), ("search_payload", "hit"); (b) a passing KG with an http image and Serper [] -> None, line `tier=search_payload outcome=rejected candidates=1 reason=scheme`; (c) budget denied, a passing organic result on `shop.example.com`, the pick `http://shop.example.com/t.jpg` -> None, pair ("llm_pick", "miss") | RED | 2.2 (8), 2.3 |
| A-R12 | `test_r12_search_payload_each_item_tested` | rel {brand "Creed", line "Aventus"}; payload: KG {title "Viking", imageUrl K} (brand), organic [{title "Creed Viking", link L1, imageUrl O1} (name), {title "Creed Aventus 100ml EDP", link L2, imageUrl O2}] -> O2; `rec.budget == []`, `rec.search == []`; line `tier=search_payload outcome=accepted candidates=3 reason=none` | RED | 2.3 `_extract_relevant_image_from_search` |
| A-R13 | `test_r13_tier3_precondition_and_pick` | budget denied; rel {Creed, Aventus}; (a) organic [{title "Creed Viking", link ...}] -> `rec.gpt == []`, pair ("llm_pick", "skipped"), None; (b) organic [{title "Creed Aventus Eau de Parfum", link `https://shop.example.com/aventus`}], the pick `https://img.shop.example.com/aventus.jpg` -> that URL, pair ("llm_pick", "hit"), `rec.gpt[0] == (NAME, organic)` (the call unchanged); (c) the pick `https://cdn.other.example.org/x.jpg` -> None, line `tier=llm_pick outcome=rejected candidates=1 reason=brand` | RED | 2.2 (8), 2.3 |
| A-R14 | `test_r14_one_line_closed_grammar` | over the paths of A-R08..A-R13: exactly one `[IMG_RELEVANCE]` record per call, each matching the 2.6 regex; none contains NAME, "http", the query text or a title; every `[IMG_TIER]` record still matches the X2a TIER regex (tests/test_inc_x2a_image_tier_timing.py:32-35) | RED | 2.6 |
| A-R15 | `test_r15_cancel_under_the_flag` | flag on, rel given, payload None, Serper hangs; `asyncio.wait_for(call, 0.05)` raises TimeoutError; exactly one `[IMG_TIER] cancelled tier=serper_images ...` and exactly one `[IMG_RELEVANCE] product=0 tier=none outcome=none candidates=0 reason=none`; `rec.cancelled == ["search"]`; `rec.gpt == []` | RED | 2.3 `finally`, 2.6 |
| A-R16 | `test_r16_flag_off_with_relevance_is_the_base_call` | for the flag unset, "false", "0", "garbage", with the knob "7" and `relevance` GIVEN: `image_relevance.candidates_knob` patched to raise; result == POEM (images[0]); `rec.budget == [(1,)]`; `rec.search == [((NAME,), {"num_results": 1})]`; `rec.order == ["budget", "search"]`; no `[IMG_RELEVANCE]` record; the `[IMG_TIER]` pairs equal those of A-P01 | RED (keyword assert) | 2.3 setup, F2 |
| A-P01 | `test_p01_base_call_full_config` | flag unset, knob "7", no `relevance`: POEM from images[0]; `rec.search == [((NAME,), {"num_results": 1})]`; the X2a grammar holds; no `[IMG_RELEVANCE]` record | PIN (green at base) | F2 |
| A-P02 | `test_p02_flag_on_without_identity_is_the_base_call` | flag "true", knob "7", NO `relevance` (the camera / legacy caller): identical to A-P01 | PIN | F3 |
| A-P03 | `test_p03_base_search_payload_function_untouched` | flag "true": `img.extract_image_from_search({"knowledgeGraph": {"title": "The Tyger", "imageUrl": POEM}}) == POEM` | PIN | F4 |
| A-P04 | `test_p04_shared_validator_untouched` | flag "true": `img._is_valid_image_url("http://x.example.com/a.jpg") is True` (kb_serve.py:323 and the override scs:6424 depend on it) | PIN | F4 |

### 5.3 File B: tests/test_inc_i1_noon_and_wiring.py (the noon image, the scs wiring, the override branches)

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| B-R01 | `test_r01_noon_copies_the_first_https_raster` | the iPhone hit + a PDP whose Product carries `image` = [N1, N2, N3] (https f.nooncdn.com jpg?width=1200): one run flag OFF, one run flag "true" in the same test; `on.get("image_url") == N1`; `{k: v for k, v in on.items() if k != "image_url"} == off` | RED | 2.5 |
| B-R02 | `test_r02_noon_image_shapes` (parametrized) | flag "true": `image` = ["http://f.nooncdn.com/p/a.jpg", "https://f.nooncdn.com/p/b.png"] -> b; [{"@type": "ImageObject", "url": c.jpg}] -> c; {"@type": "ImageObject", "contentUrl": d.webp} -> d; the string "https://f.nooncdn.com/p/f.jpg?width=1200" -> f | RED | 2.2 (7), 2.5 |
| B-R03 | `test_r03_scs_passes_the_identity_under_the_flag` | flag "true"; product {"brand": "", "name": "Tyger", "variant": None, "category": "fragrances", "search_query": "Tyger", "_explicit": True}, `partial_slot=1`: the recorder's kwargs == the base keyword set plus `relevance == {"brand": "", "line": "Tyger", "category": "fragrances", "slot": 1}`; positional args `("Tyger",)`; with `partial_slot=None` the slot is None | RED | 2.4 |
| B-P01 | `test_p01_noon_flag_off_full_config` | flag unset and "false", knob "7", an https image in the JSON-LD: `"image_url" not in out`; `set(out) == {"amount", "currency", "retailer", "url", "estimated", "source_method", "title", "confidence", "in_stock", "seller", "brand"}` | PIN | F5 |
| B-P02 | `test_p02_scs_flag_off_exact_call` | flag unset and "false", knob "7": the recorder saw ONE call, args `("Tyger",)`, kwargs keys exactly {"region", "page_scrape_image", "organic_results", "search_payload"}, `page_scrape_image is None` | PIN | F1 |
| B-P03 | `test_p03_scs_camera_product_never_gets_the_identity` | flag "true", knob "7", a camera product (`"_vision": True`, brand "Synthbrand", name "Alpha"): kwargs keys exactly the base set | PIN | F1 (I1-1) |
| B-P04 | `test_p04_override_branches_for_a_noon_image` (Q4) | `_get_price` returns a noon-shaped dict (retailer "noon.com", url `https://www.noon.com/bahrain-en/s/ZT1/p/`, image_url N1), the cascade recorder returns CASCADE (https example.com jpg): V2 OFF + DG OFF -> `result["image_url"] == N1`; DG "true" -> N1; V2 "true" -> CASCADE; and `jsonld_widen.allowed_image_url(N1, <pdp url>, price_service.OFFICIAL_BRAND_DOMAINS) is None` while `jsonld_widen.allowed_image_url(N1, N1) == N1` (refused by the host allowlist only) | PIN (documents 1.4) | 1.4 |
| B-P05 | `test_p05_noon_image_rejects` (parametrized) | flag "true": `image` = ["https://f.nooncdn.com/p/e.svg"], ["https://10.0.0.1/g.jpg"], None, missing -> `"image_url" not in out` | PIN (vacuous at base; kills M24 / M25 at head) | 2.2 (7) |

Counts: RED 19 (A-R01..A-R16, B-R01..B-R03), PIN 9 (A-P01..A-P04, B-P01..B-P05). The RED gate run (DEFERRED TO RED):
```
PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/harness/gate.py --bound 600 --tag inc-i1-red-base --log C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-I1/red/red_base.log --cwd C:/Users/SynAckITPC/Documents/AI/sc-inc-i1 -- tests/test_inc_i1_picture_must_match.py tests/test_inc_i1_noon_and_wiring.py
```
Expected at base: every RED node fails with AssertionError only (no ImportError, TypeError, KeyError or setup error); every PIN node passes.

---------------------------------------------------------------------------------------------------

## 6. Mutation table

Each mutant is applied to a byte copy of the GREEN file (an exact-string edit that matches once), the killing rows run through `gate.py --bound 600 --tag inc-i1-mut-<id> ... -- <file> -k <rows>`, then the file is restored from the copy and sha256-compared (stop on a mismatch); the mutation lock `<worktree>/.qa-mutation.lock` holds the agent label and time for the whole run. KILLED = an assertion failure.

| Id | File | Mutant | Killed by |
|---|---|---|---|
| M01 | leaf | `guard_enabled` returns True always | A-R01, B-P01, B-P02 |
| M02 | img | the `_rel` setup without `_relevance.guard_enabled()` | A-R16 |
| M03 | leaf | `relevance_kwargs` without its flag check | B-P02 |
| M04 | leaf | `relevance_kwargs` without the `is_vision` exclusion | B-P03 |
| M05 | img | the `_rel` setup without `relevance is not None` (guard on with the flag alone) | A-P02 |
| M06 | leaf | `check`: the brand test removed | A-R03 (T7, T16) |
| M07 | leaf | `check`: the line test removed | A-R03 (T8, T9, T12-T15, T18) |
| M08 | leaf | `check`: the fragrance-word test removed | A-R03 (T1, T2, T17), A-R08 |
| M09 | leaf | the alias expansion removed | A-R03 (T3), A-R09 |
| M10 | leaf | `_cg.normalize` replaced by `str.lower().split()` | A-R03 (T5, T10) |
| M11 | leaf | host tokens joined into the line test | A-R03 (T18) |
| M12 | leaf | `brand_joined` dropped | A-R03 (T19) |
| M13 | leaf | the placeholder-brand fold removed | A-R03 (T17) |
| M14 | img | Tier 1 query = `name` under the guard | A-R08 |
| M15 | img | Tier 1 `num_results=1` under the guard | A-R08, A-R10 |
| M16 | img | the walk ignores the knob cap | A-R10 (knob "2") |
| M17 | img | Tier 1 takes `images[0]` without the test | A-R08 |
| M18 | leaf | the scheme test removed from `accept` / `accept_pick` | A-R10, A-R11 |
| M19 | img | Tier 1.5b calls the base `extract_image_from_search` under the guard | A-R09, A-R12 |
| M20 | img | the Tier-3 precondition removed | A-R08 (`rec.gpt == []`), A-R13 (a) |
| M21 | leaf | `accept_pick` accepts without the related-host check | A-R13 (c) |
| M22 | img | the summary logs `name` as the product field | A-R14 |
| M23 | img | the summary logged in each tier as well (two lines) | A-R14 |
| M24 | noon | the block without its flag check | B-P01 |
| M25 | leaf | `first_https_raster` returns the first URL unfiltered | A-R05, B-R02 (http first), B-P05 (svg) |
| M26 | leaf | `first_https_raster` uses a bare `startswith("https://")` instead of `allowed_image_url(u, u)` | A-R05 (IP host, svg, fimgs), B-P05 |
| M27 | leaf | the knob without the clamp | A-R02 ("15") |

Expected: 27 KILLED, no equivalent mutant (BY READING); a survivor is reported for a ruling.

---------------------------------------------------------------------------------------------------

## 7. Comm set and gates for GREEN (cheapest first; every pytest through gate.py, one process at a time)

1. Syntax and lint: `<venv python> -m py_compile` on the four app files; `<venv python> -m ruff check --select E9,F63,F7,F82 --no-cache` on the four app files and the two RED files; `<venv python> -m black --check` (26.5.1) on the leaf and the two RED files; pure ASCII (bytes > 127 = 0) and LF in the new files; CRLF kept in the edited files; `git diff --stat` shows content lines only (no whole-file diff).
2. The two RED files at head: every row green (bound 600, tag `inc-i1-red-head`).
3. The base-pass-state sets of 1.10 at head (tags `inc-i1-head-img`, `inc-i1-head-pins`, `inc-i1-head-scan`): the same FAILED / ERROR id set as at base (no E-rows).
4. The CI-order set (one process, sorted = CI's alphabetical order, bound 1200, tag `inc-i1-ciorder`): tests/test_comparison_response_image_url.py tests/test_image_knowledge_graph_tier.py tests/test_image_service.py tests/test_image_service_edges.py tests/test_image_service_longtail.py tests/test_inc_g1_gate_rows.py tests/test_inc_i1_noon_and_wiring.py tests/test_inc_i1_picture_must_match.py tests/test_inc_x2a_image_tier_timing.py tests/test_noon_adapter.py tests/test_s81_d03_deny_and_guards.py tests/test_s81_d08_jsonld_widen.py tests/test_s81_s07c_role_fix.py tests/test_s81_s18_kb_first_serve.py. The unit touches neither /health nor the app lifespan (no P73 lifespan-first rule).
5. The comm set (the union rule; computed at base by `<SP>/INC-I1/spec/comm.py` with git reads only): (1) the app import closure to a fixpoint of img, noon and scs over every app/*.py (a module joins when its text names a member by dotted path, by `from <pkg> import <leaf>` or by file path): 84 modules, app.main included (so every app.main / TestClient user joins); (2) every tests/test_*.py naming a closure member or using app.main / TestClient: 695; (3) UNION the source-scanning readers of app/ not already in: 7 (test_legal_docs_u8_d3c, test_legal_docs_u8_polish, test_legal_s78, test_precommit_hook_phase_b, test_retro_w1_2b, test_s81_s08b_gate_rows, test_secret_scan_static); (4) UNION the named source-scanning pins and the CLAUDE.md readers (44 text readers + the import graph): 6 more (test_channel_freshness, test_cohort_personalization_load, test_eval_cache_read_mode, test_eval_kpi_baseline, test_migration_index_predicate_immutability, test_retro_w1_2d); (5) UNION the SmartCompareApp-scanning backend tests: 4 more (test_feature_bucket_parity, test_migration_037_security_definer_grants, test_precommit_hook_phase_b_round2, test_s81_12_gate_rows); (6) MINUS the pre-commit hook files (2 removed: test_precommit_hook_phase_b.py, test_precommit_hook_phase_b_round2.py; the unit edits no .githooks file). Result at base: 710 files, `<SP>/INC-I1/spec/comm_set.txt`, sha256 `5e2f0266d1a562fcdc79629d26cbfbc7b5a52e6fabd501bdecbf7a24296410ba`. At head add the two RED files (712; 713 if the gate adds a gate-rows file). No edited test-support helper (the unit edits no non-test_*.py under tests/), so no helper importer joins. The new leaf is read at head by the app/ walkers already in the set (T7b, D03 r1i, the U8d R8 AST, the key-log hygiene scan, the create-site census).
   Base record: none stored for 731bcddf with this set: compute it ONCE at the base and store it under `<SP>/harness/base_records/731bcddf531a7e123963246168ca19f262859337/5e2f0266d1a562fcdc79629d26cbfbc7b5a52e6fabd501bdecbf7a24296410ba.txt` with the `[pyt]` lines (LC-6). Chunks of at most 25 files (29 chunks), bound 1200, tags `inc-i1-comm-base-NN` / `inc-i1-comm-head-NN`; each chunk driver launched ONCE (a DUPLICATE line means it is running); `comm -13` of the sorted FAILED node-id sets EMPTY; a branch-only failure is re-run against the base to tell a flake from a regression. Example chunk command:
```
PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/harness/gate.py --bound 1200 --tag inc-i1-comm-base-01 --log C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/fce5ef8e-45c1-47d7-9da1-42b27fb2581e/scratchpad/INC-I1/green/comm_base_01.log --cwd <a detached scratch worktree at 731bcddf under <SP>/INC-I1/> -- <the first 25 lines of comm_set.txt>
```
6. The fourteen backend-scanning client jest fences (brand/inAppMark.u4c, clientTruth/{medicalNote,privacyManifest,shareTruth}.s74, clipboardFallbackService, config/nativeBundle.w37, DimensionBars.perCategory, honestCounts.s69, landing.domain.s76, navigation/linking.w315, onboarding/step05Trust.s69, playInstallReferrerService(+.edges), ResultsScreen.timeout): measured by `git grep` that none names image_service, noon_service, structured_comparison_service, image_relevance, category_gate, jsonld_widen, the black list or CLAUDE.md; the rule still runs them BY PATH at GREEN and at the rebase (the footprint touches app/ and .github/): `gate.py --wait-only`, then the H5 jest probe until it prints nothing, then the project jest by path through the junction the orchestrator creates. DEFERRED.
7. The mutation run (section 6).
8. The added-line sweep (no personal value, no 8-digit run, no key shape, no `@gmail`, no `+973`) and the secret-shape sweep over the diff.
9. CI is the arbiter after the PR (green with the 11 known deselected nodes of tests/.pre_impl_failures.txt).

---------------------------------------------------------------------------------------------------

## 8. CLAUDE.md block, clauses and owner steps (wording may be tightened, content may not; pure ASCII)

Anchor: a new block after the S81-07c block (its owner-steps bullet is CLAUDE.md:682 at the base) and before `## Tests` (:684), with one blank line before its heading. If another unit of this lane merges first (INC-R1, INC-H1), the block unions AFTER the newest block in merge order.

Heading:
**INCIDENT LANE unit (INC-I1 PICTURE-MUST-MATCH, built 2026-11-1x, the S95-FIX incident lane; ONE new flag + one knob, default OFF, read PER CALL; SAFE (I1-10), one adversary; branch `fix/inc-i1-picture-must-match`; spec `.qa-s80/INC-I1_UNIT_SPEC.md`; frozen RED files tests/test_inc_i1_picture_must_match.py, tests/test_inc_i1_noon_and_wiring.py):**

Rows:
- `ENABLE_IMAGE_RELEVANCE_GUARD` + the knob `IMAGE_RELEVANCE_CANDIDATES` (5; a finite number >= 1 is truncated and clamped to 10; unset, blank, garbage, inf, nan and anything below 1 fall back to 5) (`app/services/image_relevance.py::guard_enabled` / `::candidates_knob`, the house idiom; a leaf: the stdlib, `category_gate.normalize` and `jsonld_widen.allowed_image_url` at module level, `price_service._BRAND_ALIAS_GROUPS` / `_jsonld_image_urls` only inside functions). **Effect ON**, text compares only (`_fetch_product_data` passes `relevance={brand, line, category, slot}` to `image_service.get_product_image_url` through `image_relevance.relevance_kwargs`, never for a camera product): every cascade tier accepts a picture only when its URL is https AND the text that came with it names the product: a brand token (the title or source, or the link's host; alias-folded through `price_service._BRAND_ALIAS_GROUPS` plus the local {bvlgari, bulgari}) and a significant line token (stop, concentration and fragrance words and the brand's own tokens never count), or, with an empty brand, a line token and a fragrance word (perfume, parfum, eau, edt, edp, cologne, fragrance, the Arabic word for perfume); Tier 1 asks Serper Images for `<full name> perfume` (the fragrance category; else the full name) with `IMAGE_RELEVANCE_CANDIDATES` results and takes the first that passes (one budget credit and one usage count per call, as before); Tier 1.5b tests each knowledge-graph (title) / organic (title + link host) / images item; Tier 3 runs only when an organic result passes, and its pick must sit on such a result's host; one INFO `[IMG_RELEVANCE] product=<0|1|-> tier=<none|piggyback|search_payload|serper_images|llm_pick> outcome=<accepted|rejected|none> candidates=<n> reason=<none|scheme|brand|name|fragrance_word>` per call (the INC-X2a `[IMG_TIER]` lines unchanged); the noon adapter (`noon_service._confirm_pdp`) copies the PDP's Product JSON-LD image (its first https raster URL on a public host) into its price dict as `image_url`, so the Tier 1.5 override shows the priced product's own picture while `ENABLE_IMAGE_PIPELINE_V2` is OFF (ON: D08's allowlist refuses `f.nooncdn.com` and the cascade picture stays). **OFF:** byte-identical (no keyword, no key, no line, no knob read).
- Stated limits L-I1-1..L-I1-18 (spec section 9): a correct picture whose text lacks the brand or the line is rejected (the placeholder shows); with an empty brand (every app compare until INC-R1 is ON) one line token plus a fragrance word is enough; a non-fragrance compare with an empty brand gets the placeholder; more paid Tier-1 calls; no vision, hash, raster or HEAD check on cascade pictures; noon prices cached in L1 while ON keep their picture up to 7 days after a rollback; with V2 OFF the override still accepts an http page image from another producer.
- **Owner steps (names only; a dated ledger line per step; flips are the owner's, one window each on an explicit yes):** none to merge. (1) The relay sets `ENABLE_IMAGE_RELEVANCE_GUARD` ON on web on the owner's yes, in its own window; `IMAGE_RELEVANCE_CANDIDATES` stays unset (5); price-warmer needs nothing while `ENABLE_PRICE_CACHE_WARMER` is false. (2) The PROOF ON THE PHONE of the PR body. (3) Rollback: unset the flag. Merged is NOT proven: the unit is "merged, NOT yet proven" until the owner's phone proof.

:341 Feature Flags clause (appended after the S81-07c sentence): "`ENABLE_IMAGE_RELEVANCE_GUARD` and the knob `IMAGE_RELEVANCE_CANDIDATES` (INC-I1 PICTURE-MUST-MATCH, default OFF / 5, read per call): the row of the **INCIDENT LANE unit (INC-I1 PICTURE-MUST-MATCH, ...)** block."

:313 image paragraph (one sentence appended at its end): "Since INC-I1 (`ENABLE_IMAGE_RELEVANCE_GUARD`, default OFF) the cascade accepts a picture only when its text names the product, and the noon adapter writes `price['image_url']` under that flag: the **INCIDENT LANE unit (INC-I1 PICTURE-MUST-MATCH, ...)** block."

CLAUDE.md readers (in the comm set): tests/test_ci_gates.py, test_behavior_dimension_translation.py, test_s81_s04_spend_breaker.py, test_s81_s08b_legacy_fingerprint.py, test_s81_s08b_gate_rows.py, test_s81_s23_bypass_retire.py, test_s81_s07_meas_harness.py and the other text readers found by `git grep CLAUDE` over tests/ (44 in all, `<SP>/INC-I1/spec/comm_parts.json`). None pins the :313 or :341 text (measured by grep).

## 8b. PROOF ON THE PHONE (H6, R0-1, I1-9; after the merge, the deploy and the relay's flip; nothing here needs AI text)

Preconditions: the relay confirms (read-only) that the running web deployment's commit contains the INC-I1 merge; the dated flip line for `ENABLE_IMAGE_RELEVANCE_GUARD` ON on web; the dated state of `ENABLE_IMAGE_PIPELINE_V2` (OFF expected; ON refuses the noon picture by design, L-I1-9) and of `ENABLE_PRODUCT_RESOLVER` (INC-R1) OFF for check 1.

1. Pair "stronger with you" vs "Tyger" (typed in the two fields, exactly as on 2026-11-13; INC-R1 still OFF). Must be visible: the Tyger card shows the plain placeholder tile, never the Blake poem page (the hermetic guarantee is "never a picture whose text lacks the line token or a fragrance word": a perfume picture titled with "Tyger" and a perfume word could still show, OQ-8); the stronger-with-you card shows the noon bottle photo when the noon price wins on a FRESH fetch (a noon price cached in L1 before the flip carries no picture for up to 7 days; the L2 row never does, L-I1-10). Backing: the two `[IMG_RELEVANCE]` lines of that compare (product=0 and product=1: Tyger `outcome=rejected` or `none`, never `accepted` with the poem); the `[PRICE] BH adapter direct hit for ... via noon.com` line in the same compare (a fresh noon fetch); the saved row's `products[i].image_url`: null for Tyger, an https URL on `f.nooncdn.com` for stronger-with-you when noon won (otherwise an https cascade URL or null).
2. Two golden pairs that had photos before: "Aventus" vs "Layton" and "Sauvage EDP" vs "Bleu de Chanel EDP". Must be visible: both photos on both pairs. Backing: `image_url` non-null and https in both saved rows (all four products); each product's `[IMG_RELEVANCE] ... outcome=accepted`. A placeholder on a golden product is a FINDING for the relay (L-I1-1: its picture text lacked the line or a fragrance word), not a pass.
3. On every saved row of these three compares no `image_url` starts with `http://` from the cascade (the http part of ADV R-1).
Merged is "merged, NOT yet proven" until the relay files the dated phone result. The hermetic rows (section 5) are necessary and are never presented as this proof.

---------------------------------------------------------------------------------------------------

## 9. Stated limits

- L-I1-1 (I1-11, precision first) A correct picture whose text lacks the brand (when known) or the line, or, with an empty brand, the line or a fragrance word, is rejected and the placeholder shows. A knowledge-graph card titled only with the line ("Sauvage") fails the brand test when the brand is known (I1-3 reads the KG title only, OQ-3) and the product falls to the paid Tier 1. Measured against the golden pairs: NOT possible hermetically (the repo holds no recorded Serper Images or knowledge-graph payload for them; only the T01 synthetic shapes); the phone proof (8b check 2) measures it.
- L-I1-2 With an empty brand (every app compare while INC-R1 is OFF: scs:4449-4452) the test is weaker: one line token plus a fragrance word; for a typed "Dior Sauvage" a "Dior Homme Eau de Toilette" picture passes (token "dior" + "eau"). INC-R1 ON restores the brand test.
- L-I1-3 Literal I1-3: a NON-fragrance product with an empty brand also needs a fragrance word, so under the flag every such picture is rejected (OQ-1).
- L-I1-4 More Serper Images spend: a rejected free knowledge-graph or organic image now falls to the paid Tier 1 (one daily-budget credit and one lifetime usage count per call, not per result); Tier 3 runs less (no LLM call when no organic result passes). The 5 s race (INC-X2) is unchanged; a Tier-1 call that would not have happened before can now be cut by it.
- L-I1-5 No vision check, no perceptual hash, no aspect or size check, no raster-extension check on cascade URLs (an SVG URL shows the placeholder through ProductImage onError; PLAN_S80 0.4 says "https raster"), no HEAD recheck (a dead link still shows the tile).
- L-I1-6 No cross-script matching: an Arabic-titled picture of a Latin-typed line fails the line test, and the reverse.
- L-I1-7 No stemming: the plural forms ("perfumes", "fragrances", "colognes", the Arabic plural) are not fragrance words (OQ-2).
- L-I1-8 The knowledge-graph test reads the title only (I1-3); its type, description and website are ignored (OQ-3).
- L-I1-9 With `ENABLE_IMAGE_PIPELINE_V2` ON the noon picture (`f.nooncdn.com`) is refused by D08's host allowlist (not first-party to www.noon.com, not in `IMAGE_CDN_HOSTS`) and the cascade picture stays (OQ-4).
- L-I1-10 Cache residue: a noon price cached in L1 while the flag is ON carries `image_url` for its TTL (7 days for the genuine `page_scrape_jsonld`); after a flip back OFF the override still shows that picture until the entry expires. A noon price cached BEFORE the flip carries none until it expires or is refreshed; the L2 row never stores it (product_data_service.py:342-359).
- L-I1-11 With V2 OFF the price-page override (scs:6423-6429) still accepts an http page image from another producer (e.g. a cached Zyte seed): that path can still show the grey tile (OQ-5).
- L-I1-12 Pair fairness may re-select the displayed price after the override ran (scs:4610, :5364, BY READING): the noon picture can sit beside another store's price for the same identity.
- L-I1-13 The Tier-3 pick check is host-based: a correct image on a CDN host unrelated to the organic page's host is rejected.
- L-I1-14 The camera path is unchanged (I1-1): camera products never get the guard, so https-only does not apply there.
- L-I1-15 The `[IMG_RELEVANCE]` reason names only the LAST rejection; per-reason counts are not logged.
- L-I1-16 The provider's billing for an images query with `num` 5 is not measured here (no network in this round); the code counts one call (OQ-6).
- L-I1-17 The knob follows the S81-10 clamp idiom: 0 and negatives fall back to 5 (they are not clamped to 1); above 10 clamps to 10.
- L-I1-18 The stop-word, noise-word, concentration-word and placeholder-brand sets are closed lists in the leaf; a brand made only of excluded words (a pure "Parfums" or "Maison") counts as an empty brand.

## 10. Out of scope

The camera path; the KB card image (kb_serve); D08's override policy and `IMAGE_CDN_HOSTS`; INC-X2's time budget and the 5 s race; every client file (ProductImage, the ATS setting); vision, perceptual hashing, HEAD checks; the Tier-3 prompt and the `image_tier3` router site; Step-1 resolution (INC-R1); specs, reviews, chips and bars (INC-H1); `price_service._BRAND_ALIAS_GROUPS` (unchanged: the extra group is local to the leaf); `history_routes._safe_image_url` (accepts http for old rows); the price-cache warmer; Fragrantica, Parfumo and Basenotes data in any form (never).

## 11. Open questions for the orchestrator (each with the recommended option)

- OQ-1 (proposed correction, measured) Non-fragrance products with an empty brand. Measured: the explicit pair sets brand "" for every app compare (scs:4449-4452) and ENABLE_FRAGRANCE_ONLY_GATE is believed OFF (H12 c), so non-fragrance compares run; literal I1-3 then rejects every picture of such a product (T20). Recommended: require the fragrance word only when the canonical category is `fragrances` or `other`, and the line token alone for any other category; impact: one row (A-R03 T20 flips to None) and one clause of `check`. Default in this spec: the literal I1-3.
- OQ-2 Plurals in the fragrance-word set (perfumes, parfums, fragrances, colognes, the Arabic plural U+0639 U+0637 U+0648 U+0631). Recommended YES (the lexicon lists them as forms; `normalize` does no stemming); impact: one constant and one A-R03 case.
- OQ-3 The knowledge-graph text: the title only (I1-3) or the title plus `type` / `website`. Recommended: keep the title only now and read the `[IMG_RELEVANCE] tier=search_payload reason=brand` count on the phone lines; widen in a follow-up if the KG is rejected for most branded products.
- OQ-4 The noon CDN under V2: add `nooncdn.com` to `IMAGE_CDN_HOSTS` in a D08 follow-up before any V2 flip (outside this unit's footprint, I1-1). Recommended: a separate small unit, after the noon picture is seen on the phone.
- OQ-5 The override http gap under this flag: one condition (`page_img.strip().startswith("https://")`) in the two V2-OFF branches under `ENABLE_IMAGE_RELEVANCE_GUARD` would close it. Recommended only if the orchestrator widens I1-1 (the override is listed as unchanged); otherwise the V2 flip closes it (D08 refuses http).
- OQ-6 Serper billing for `num` 5: the relay reads the Serper dashboard counter delta of one compare in the canary window. The code's own counters are per call (1.7).
- OQ-7 The `reason` value for accepted and empty lines: the brief's set (brand | name | fragrance_word | scheme) has no value for them; the spec uses `none`. Confirm.
- OQ-8 Proof check 1 expects "the plain placeholder" for Tyger; the unit guarantees "never the poem" (another perfume titled "Tyger ... perfume" would pass). Confirm the proof wording.
- OQ-9 The black ratchet: the leaf and the two RED files join `.github/black-clean-paths.txt` (the MON1 precedent; a .github edit in the footprint). Recommended YES (the ratchet rule says so); otherwise drop step 9 of the change list.
- OQ-10 PLAN_S81's VERIFY "Images" correction says the live path serves only the KB image or the retailer JSON-LD image (or the placeholder). INC-I1 keeps the Serper tiers live, narrowed. Confirm this is the intended incident step (the end state stays the plan's).
- OQ-11 Classification (I1-10): the footprint touches no FOCUS surface; one response-visible key value is new under the flag (`overview.products[i].price.image_url` for a noon-won price: an existing optional member of price objects, unread by both live bundles); no envelope, refusal, code or status change. Recommended SAFE (one adversary).
- OQ-12 (measured deviation) The brief's own example (a "Bvlgari" product accepted on a "Bulgari" title) needs an alias the repository does not have: `price_service._BRAND_ALIAS_GROUPS` holds no Bvlgari / Bulgari group (`git grep -i bulgari -- app/ data/` = 0 hits). The spec adds `EXTRA_ALIAS_GROUPS = (frozenset({"bvlgari", "bulgari"}),)` LOCALLY in the leaf (A-R07 pins reuse + extra). Recommended: keep it local (the price_service groups drive the price fences; adding a group there is a price-path change for its own ruling).
- OQ-13 I1-5 says an http candidate is "skipped, logged once". The spec reads that as the one `[IMG_RELEVANCE]` line per call, whose reason is `scheme` when an http candidate was the last rejection; an http candidate skipped BEFORE an accepted one is not visible. Alternative: append ` http_skipped=<n>` to the same single line (it extends the I1-8 grammar). Recommended: keep the I1-8 grammar exactly; the guard already never returns http.

---------------------------------------------------------------------------------------------------

## Not done in this spec

- No pytest, jest, tsc or eslint ran (READ-ONLY round, H5 c): the base pass state (1.10), the RED gate, the comm-set base record (710 files), the CI-order set, the fourteen client fences and the mutation run are DEFERRED with the commands above.
- NOT MEASURED: the Serper Images item fields `source`, `link` and `domain` (no repo fixture carries them; no network); the provider's billing for `num` 5; the knowledge-graph titles of the golden pairs; the golden-pair effect of the guard (only the phone can show it); the CPython 3.12 `asyncio.wait_for` cancellation timing on the pinned venv (BY READING, as in the G-INC-1 spec).
- Every verdict of the 2.2 truth table and of the 1.4 override branches is BY READING; the RED rows A-R03 and B-P04 confirm them (a PIN that is not green at base, or a RED row that fails with anything but an AssertionError, stops the RED agent for a ruling).
