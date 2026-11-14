# ADV - adversarial review of D1-D4, R1-R2 (S95-FIX, read-only)

All code was re-read in the plain export of 731bcddf. Every path:line below is at 731bcddf. SCS = app/services/structured_comparison_service.py, PS = app/services/price_service.py. E = ESTABLISHED (re-read in the code, or fetched), L = LIKELY. This report does not say that any production problem is fixed.

## Verdict in one paragraph

The main story holds. The app sends `product_a`/`product_b`, the stream route builds `explicit_pair`, and Step 1 sets `brand ""` and `search_query = typed text`. Nothing between Step 1 and the searches resolves the product. The Blake picture was accepted by `_is_valid_image_url`. "Specs High" comes from 11 N/A fields counted as citations. The 11 dash rows come from the client's structural fallback over the server's N/A stamps. The 731bcddf client does re-ask any record that is not version 3. I refute or correct seven claims, two of which change a fix. I found three gaps that no report explains:
1. The Bleu de Chanel price regression.
2. Synchronous Redis reads on the Serper key path while Redis was timing out.
3. The spend breaker failing open.

## (1) Code claims re-read

| # | Report / claim | Cited | Result |
|---|---|---|---|
| 1 | The client sends the pair, not q= | HomeScreen.tsx:457-460; api.ts:880-899 | CONFIRMED (E). `streamComparison({product_a, product_b})`; `region=bahrain` is set at api.ts:878 |
| 2 | The stream route builds explicit_pair | text_routes.py:1136-1138, 1263 | CONFIRMED |
| 3 | Step 1 explicit branch: brand "", search_query = typed text (sync + stream) | SCS:4438-4453, 5140-5153 | CONFIRMED. The q= path is used only when the pair is absent |
| 4 | Shared builder `_explicit_pair_products` | SCS:1959-1971 | CONFIRMED |
| 5 | No later step adds a brand. `_fetch_product_data` copies brand/name/search_query | SCS:5966-5985 | CONFIRMED. A grep for infer/detect/guess-brand in SCS finds 0 hits. app/ has no difflib, rapidfuzz or levenshtein |
| 6 | The fragrance gate's KB arm is inert | category_gate.py:376-379 | CONFIRMED (`return False`) |
| 7 | kb_brands has no runtime reader | kb_service.py:58, 98, 828 | CONFIRMED (column list and builder only) |
| 8 | An empty brand gives no KB id, so serve and ingest skip | kb_service.py:246-260; kb_serve.py:166-168; kb_ingest.py:416-419 | CONFIRMED (`not parts[1]` gives None; the placeholder-brand guard comes first) |
| 9 | Shopping is gl=us "us_fallback by construction" | serper_service.py:1048-1093 | CONFIRMED |
| 10 | Image Tier 1: bare name, num 1, images[0], no relevance check | image_service.py:295-311, 57-67 | CONFIRMED. The only gates are the scheme check and the deny list |
| 11 | The price-page image override needs result["price"].image_url | SCS:6406-6429 | CONFIRMED |
| 12 | The noon price dict has no image, size or concentration | noon_service.py:443-467 | CONFIRMED |
| 13 | The decant floor needs a house keyword in the name | PS:1626-1632 (list PS:574-583) | CONFIRMED. "stronger with you" contains no listed house |
| 14 | The flanker set has five words; selection mode admits extra tokens | PS:7164-7166, 8341-8378 | CONFIRMED. Selection is query ⊆ candidate, so "Intensely" passes. The identity of the noon listing stays L |
| 15 | A genuine adapter hit is cached under the bare-name key | SCS:7874-7877 | CONFIRMED (gated by `should_cache_price(full_name, ...)`) |
| 16 | The pair-size reconcile skips a one-sided pair | PS:2301-2309 | CONFIRMED (the guard is at PS:2305-2309) |
| 17 | The 11-field fragrance schema; N/A stamped when ENABLE_SPECS_NO_FABRICATION is off | extraction_service.py:213-227, 1679-1707 | CONFIRMED |
| 18 | `_clean_specs` stamps N/A again | SCS:3551-3552 | CONFIRMED |
| 19 | Client structural fallback; both-dash rows kept; "N dimensions" header | ResultsAccordion.tsx:206-222, 293-296, 596-599 | CONFIRMED |
| 20 | Specs High = 11 "unverified" rows counted as citations (wiring off) | fact_check_service.py:213-220, 562-568; scoring_service.py:1110-1115, 1207 | CONFIRMED. The flag-ON branch returns verified+likely = 0, so High also implies ENABLE_CONFIDENCE_FACTCHECK_WIRING is off (L) |
| 21 | strong maps to High | ConfidencePills.tsx:54-58 | CONFIRMED |
| 22 | The versatility dim is the reliability proxy | scoring_service.py:2177; reliability at 1832-1839 | CONFIRMED |
| 23 | Caption "N/A vs X projection"; "8h vs 8h" is max-then-min | scoring_service.py:3660-3676 | CONFIRMED |
| 24 | A no-data consensus becomes the praise | review_service.py:631-645; log at 765 | CONFIRMED |
| 25 | Verdict lines | response_builder.py:1097, 1131 | CONFIRMED |
| 26 | RevealBurst badge stays at scale 1 in an absolute slot, never unmounted | ResultsContent.tsx:536-549, 872-880; RevealBurst.tsx:71, 194-245 | CONFIRMED |
| 27 | Consent re-asks any version != 3 | aiConsent.ts:58, 93-97, 181-187 | CONFIRMED. The account switch unmounts Main (App.tsx:399-405), so grantedRef cannot carry over |
| 28 | The router: consent >= 3 gives anthropic, else openai under PRE_V3 | llm_router.py:343-355 | CONFIRMED. With ENABLE_ANTHROPIC_VERDICT OFF, `decide("verdict")` returns "openai" and the egress stop drops it, which explains "write-up unavailable" (E) |
| 29 | Price pill hidden when either price pends; degraded note | ResultsContent.tsx:593, 439-446; resultHonesty.ts:17-20 | CONFIRMED |
| 30 | Coded refusal copy exists | errorCopy.ts:83-111; en.json:703, 111 | CONFIRMED |
| 31 | Phase-1 image cap is 5.0 s | SCS:6033, 6271 | CONFIRMED (line) |
| 32 | Tier 2 wall is 4.0 s | SCS:660, 858-863 | CONFIRMED |
| 33 | Permission strings name OpenAI | app.json:220, 228 | CONFIRMED. These are plugin Info.plist strings, so they need an App Store build |

### Refuted or corrected

- **R-1. D2 RC3 (the 5 s image race timed out because Serper took about 10 s) is contradicted by the same run.** "[image] Tier 1 Serper hit for 'Tyger'" shows a Serper Images call that returned within the 5 s cap in the same window. The 10 s figure is `serper_shopping`, not images. Three other explanations fit equally well:
  - (a) the Serper image budget gate denied the call (`try_consume_serper_image_credit`, image_service.py:290);
  - (b) the cascade returned a URL the phone could not load. ProductImage falls back to the tone tile on `onError`. `_is_valid_image_url` accepts `http://`, iOS ATS blocks plain http loads, and app.json has no ATS override (grep: 0 hits);
  - (c) Tier 1.5b returned a dead link.

  Downgrade RC3 to "unknown". The `[IMG_TIER]` lines decide it. D2's fix F2 (copy the noon JSON-LD image) stands either way.
- **R-2. R2 caution 7 is refuted (E).** R2 said the noon image may fail the V2 allowlist, which would explain the grey card. No noon image ever reaches the override: the noon dict carries no `image_url` (noon_service.py:443-467). The allowlist question only arises after D2 F2.
- **R-3. D2 says Tier 2 runs per-field search and LLM "one after the other".** The module comment ("gather lets fields share", SCS:661) and the per-field 3.5 s budget point to concurrent fields. The 4 s wall conclusion stands.
- **R-4. D2 "11 dash rows = the model found nothing" is not shown for "stronger with you".** The specs prompt allows training-data answers, so an all-null reply for a famous line is surprising. Nothing in the reports separates three cases:
  - (i) the specs race timed out (8 s) or errored on one side, while the other side's 11 N/A built the rows;
  - (ii) an all-N/A sheet served from L1/L2 cache (written within 7-30 days, SCS:6913);
  - (iii) a real all-null reply.

  The log reads must split these before F3/F6 are sized as the cure.
- **R-5. D3 F-PRICEPILL ship path.** "Derive the specs leg from spec coverage" is server code (scoring_service.py:1199-1213), not OTA. It also duplicates D2 F4. Pick one owner for the Specs chip.
- **R-6. D1 F2b ship path.** A new AMBIGUOUS_PRODUCT code needs a server deploy as well as the OTA. The JSON summary says OTA only; the body says both.
- **R-7. D1 F1 cannot work as specified today.** The "curated house-and-line alias table" does not exist. kb_products is empty, and kb_brands holds houses, not lines. So the only arm that maps "stronger with you" to Emporio Armani is the proposed Claude call. R1 cautions that an unconstrained LLM proposal must resolve to a catalog row. Two further limits:
  - The Claude site runs only for consent >= 3 (llm_router.py:350-355). Old-consent accounts would get no resolution, so the deterministic arm must stand alone.
  - It adds an LLM call to Step 1 on a path that already times out.

  F1 must ship with a seed catalog (R1 step 1 / D4-F3), or explicitly as a resolve-or-refuse gate.

## (2) Research claims checked

| Claim | Source | Result |
|---|---|---|
| Haiku 5.5 is USD 0.10/0.50 per MTok, cache read 0.01; Sonnet 5.5 is 2/10; batch is 50 % | platform.claude.com/docs/en/about-claude/pricing.md | CONFIRMED |
| Web search costs USD 10 per 1,000 searches; web fetch has no extra charge; code execution is free with _20260209 | same | CONFIRMED |
| Citations with `output_config.format` return a 400 | .../structured-outputs.md | CONFIRMED |
| Grammar cache lasts 24 h | same | CONFIRMED |
| Cache minimum is 512 tokens on Haiku 5.5 and Sonnet 5.5 | .../prompt-caching.md | CONFIRMED |
| Batch: 100k requests or 256 MB, most within 1 h, expiry at 24 h, results kept 29 days, server tools work | .../batch-processing.md | CONFIRMED |
| Web fetch: no JavaScript; robots.txt refusals; only URLs already in context | .../web-fetch-tool.md | CONFIRMED |
| allowed_domains and blocked_domains together give a 400; an unsupported country gives a 400; dynamic filtering is not ZDR | .../web-search-tool.md | CONFIRMED |
| Vision costs ceil(w/28)·ceil(h/28) tokens; 1000 px = 1,296 | .../vision.md | CONFIRMED |
| Haiku 5.5 has 1M context and 128K output | models/overview.md | CONFIRMED |
| Licences: RapidFuzz, jellyfish, symspellpy, splink, dedupe, faiss and CLIP are MIT; anyascii is ISC; sentence-transformers and big_vision are Apache-2.0; imagehash is BSD-2; robotoff, zingg and openfoodfacts-server are AGPL-3.0; open_clip, pgvector and FragDB show NOASSERTION | api.github.com/repos/... | CONFIRMED |
| FragDB is "a full crawl" of a source, CC-BY-NC-4.0 | raw README | CONFIRMED, and correctly forbidden |
| The TidyTuesday 2024-12-10 set was web-scraped from Parfumo | rfordatascience.github.io | CONFIRMED, and correctly forbidden |
| OBF: database ODbL, contents DbCL, images CC BY-SA | world.openbeautyfacts.org/terms-of-use | CONFIRMED. EAN 3605522040229 = SWY EDT 30 ml (OBF API) |
| fuzzystrmatch metaphone caveat for multibyte input | postgresql.org/docs/18 | CONFIRMED |
| Serper: B2B, "web-scraped data", not affiliated with Google, no hiding of the source | serper.dev/terms | CONFIRMED |
| Google is suing SerpApi | blog.google | CONFIRMED (page title and text) |
| WooCommerce Store API is unauthenticated with no sensitive data | developer.woocommerce.com | CONFIRMED |
| Shopify `/products/{handle}.js`, 250 variants | shopify.dev ajax | CONFIRMED |
| **Amazon Creators API needs 10 qualifying sales in 30 days** (marked E) | cited Amazon pages | **NOT on the cited pages as fetched.** Only third-party sources say it (affiliate-toolkit.com, a wordpress.org forum post). Downgrade to L |
| PA-API 5 cut-off dates (30 Apr / 15 May 2026) | Amazon deprecation page | The page as fetched gives no date (JS-rendered). Third parties disagree. L |
| Admitad (Mitgo) advertiser feeds | support.mitgo.com/.../360019922878 | curl gets **404**. The search index has the article, with the formats listed differently by language. Content L |
| GS1 Verified-by-GS1 terms | gs1.org PDF | **403** to curl (unverified) |
| Shopify "a missed match is not fatal" | shopify.engineering catalog-clustering I and II | **Phrase not found on either page**. The precision-first idea is present. Treat it as a paraphrase, not a quote |
| LELA (2601.05192), confidence entity linking (2601.08500), entropy dialogue (2509.06185) | arxiv.org | CONFIRMED (titles match their use) |
| Etsy spelling post | codeascraft.com | 403 to curl (bot block); unverified |
| Other cited URLs (Instacart, ByteByteGo, idealo, CEUR, NAACL, UvA, Salla, Zid, ArabClicks, RFC 9309, Google 6324461) | - | Resolve with HTTP 200. Content not re-read |

No report relies on a Fragrantica- or Parfumo-derived source. Both are named only as forbidden. I fetched nothing from either.

## (3) Consistency, gaps, standing rules

**Gaps (no report explains them):**
- **G-1. Bleu de Chanel: 91.780 BHD on the old-consent run, "No confirmed price yet" two minutes later on the new account.** No report traces it.
  - The consent path cannot add a price on the old path. With OpenAI stopped, the only LLM price tier (SCS:8888 `extract_price`, site "price") fails there, but runs on Claude for v3.
  - So 91.780 came from a non-LLM tier (an adapter or the cache). Its absence two minutes later points at adapter variance, a timeout, or a cache miss on a different key, not at consent (L).
  - Relay read: both runs' `[PRICE]` lines and the cache key for Bleu de Chanel EDP.
- **G-2. Synchronous Redis on the Serper key path.** `_is_serper_key_exhausted` calls `cache_service._redis_get` (a synchronous `redis_client.get`) on every key selection, unless ENABLE_SERPER_KEY_STATE_MEMO is on (serper_service.py:181-217, 318-335; cache_service.py:173-184).
  - /health showed Redis reads timing out (llm_spend_fail_open 5) and one of three keys marked exhausted.
  - Each Serper call may then block the event loop on a Redis read. With ENABLE_UPSTASH_BOUNDED_TRANSPORT off, that read is unbounded (cache_service.py:75-90).
  - This is a candidate cause of the roughly 10 s `serper_shopping` and of the TIER2, image and specs timeouts. Class TIMEOUT (L).
  - Relay reads: the "Redis GET error" count in the window, and the names (not values) of ENABLE_SERPER_KEY_STATE_MEMO and ENABLE_UPSTASH_BOUNDED_TRANSPORT.
- **G-3. llm_spend_fail_open 5.** The spend breaker was not enforcing its bound while Redis was sick. No report raises it. It is a cost-safety item for the owner, not a page fault.

**Contradictions:**
- **C-1. Image fixes overlap.** D2 F1 (relevance gate, None when the brand is empty) and D1 F4 (category word plus relevance) cover the same ground; merge them into one unit. R2 layer 2 adds aspect and size checks.
- **C-2. Two cures for the Specs chip.** D2 F4 (skip NA in `verify_spec_citations`; it shifts reliability for every product) and D3 F-PRICEPILL (spec coverage) are both cures. Choose one, and run the flag-mix walk before choosing.
- **C-3. Three spec fixes interlock.** D2 F3 (server drops NA) and D3 F-SPECEMPTY (client empty state) must ship as a pair. Without the client change, the header reads a bare "dimensions" (ResultsAccordion.tsx:293-296).
- **C-4. Shopify /products.json.** R2 says it is undocumented by Shopify and recommends `.js` or JSON-LD. R1 calls /products.json "the main ingest stream", and the feed walker uses it. The owner's terms verdict should cover this point explicitly.
- **C-5. Page copies.** D4-F7 / B4 proposes saving the HTML of 16,730 PDP pages. R1 says to store facts, not page copies. Storing pages is a copyright and terms question per host, beyond robots.

**Standing rules:**
- **S-1. D4 A2 "RELAY run: ENABLE_FEED_WALKER=true".** A flag flip needs the owner's explicit yes and one window, even for a DRY run. Do not run it under standing approval alone.
- **S-2. D4-F6 proposes a seeder APPLY, but the seeder has no ToS check** (`url_gate` without `require_tos`, D4 table, seed_kb_batch.py:197). That is inconsistent with D4-F1's own gate. Add `require_tos` before any APPLY.
- **S-3. Secrets.** No report prints a secret. D4 names `ANTHROPIC_API_KEY` by reference only, which is acceptable. Keep it so in briefs.
- **S-4. Scraping.** R2 recommends that Serper Shopping data never be shown as the price. The product shows converted Serper prices today (parked fallback). That is an owner or counsel ruling, not an agent change.

**Owner items covered:** every item in the owner's lists has an owner report except G-1 (the Bleu price). The Sauvage units and the "Oriental" scent family remain L (model output).

## Per-report verdict

| Report | Verdict | Main issues |
|---|---|---|
| D1 | MINOR ISSUES | F1 depends on a catalog and an alias table that do not exist, and on Claude only for consent >= 3 (R-7); F2b also needs a server deploy (R-6) |
| D2 | MINOR ISSUES | RC3 contradicted by the Tyger Tier 1 hit (R-1); Tier 2 described as sequential (R-3); the all-null SWY specs not separated from a timeout or cache (R-4) |
| D3 | MINOR ISSUES | F-PRICEPILL specs part is server code and duplicates D2 F4 (R-5); the consent cause is correctly marked L |
| D4 | MINOR ISSUES | A2 flip by the relay (S-1); seeder APPLY without a ToS check (S-2); page-copy corpus (C-5) |
| R1 | MINOR ISSUES | The Shopify "not fatal" quote is not found (paraphrase); the /products.json terms question is unstated (C-4) |
| R2 | MINOR ISSUES | The Amazon 10-sales gate is marked E but not on the cited Amazon pages; the noon-image caution refuted (R-2); Mitgo URL 404 and GS1 403 to curl |
