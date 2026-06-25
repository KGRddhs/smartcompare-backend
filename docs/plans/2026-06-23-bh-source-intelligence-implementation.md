All finder claims verified against real code. The drift-guard `_genuine_bh_capable` (line 73) confirms the strengthening effect: flipping bolo/nasser off `is_render_only` makes them newly count as genuine-capable. The boutiqaat finding is interesting — Finder 1/2 mark it CONDITIONAL, but Finder 3 live-verified it cracks via plain-curl JSON-LD. I have enough verified grounding to author the wave plan.

Let me note the one discrepancy I must flag: Finder 3 claims boutiqaat resolves to GO via curl JSON-LD, contradicting Finders 1/2's CONDITIONAL. The design doc and synthesis instruction both treat boutiqaat as crack-in-implementation. This is a dispatcher-gate flag.

---

# WAVE-STRUCTURED IMPLEMENTATION PLAN — BH Source-Intelligence + Regional-Storefront Adapters

**Base:** main `fb8696c`; working branch `feature/bh-source-intelligence` @ `28a215e` (design doc only). Backend-only bundle. Design: `docs/plans/2026-06-23-bh-source-intelligence-regional-adapters-design.md`.

**Anchors re-verified live this session** (do NOT re-derive): `Source` dataclass `source_router.py:19-54`; bolo row `:94-97`; nasser row `:116-122`; sephora.bh row `:138-141`; boutiqaat row `:142-146`; `get_shopify_sources_for_category` `:383`; `get_algolia_sources_for_category` `:401`; `_GENUINE_BH_SOURCE_METHODS` `price_service.py:4267-4275`; eval set `eval_runner.py:400-410`; parity test `test_eval_genuine_methods_parity.py`; prefetch hook `scs.py:4139-4176` (with `not is_supplement` gate at `:4140/:4143`); drift-guard `_genuine_bh_capable` `test_bahrain_source_matrix_coverage.py:61-78`; render-only pin `test_is_render_only_flag.py:28-34`; curl-vs-render cascade tests `test_curl_before_render_budget.py:53-178`; G2 super-routing `test_fragrance_content_quality.py:830-1048`.

**INVARIANTS (every wave):** no fabricated data (verify-or-omit — each adapter ships only after a live BHD-price probe confirms it); genuine = membership in `_GENUINE_BH_SOURCE_METHODS`; do NOT regress `fb8696c` honesty/missing-data set; no warmer/paid-Serper pivot; adapters use OWN sitemaps/APIs (NO Serper).

**EXECUTION MODEL:** ultracode Workflow, ONE per wave — sequential implement agents (exactly one writer on the shared tree; per-task path-restricted commit) → parallel-but-throttled (≤2-3 concurrent) adversarial reviewers. Dispatcher GATES every wave. The full test/jest suite runs ONLY in the single REGRESSION reviewer (never inside an implement task). Zero-regression gate = a temp-`main`-worktree `comm` of sorted FAILED-test sets, `branch-only-NEW == []`.

---

## WAVE 1 — Source schema extension + registry corrections (FOUNDATION)

**Why first:** every adapter wave reads the new `Source` descriptor fields and the corrected flags. This wave is the schema + registry + helper-selector foundation; it ships NO live network code. It DOES flip flags, so it must update the pinned drift tests in lockstep (the highest-risk part).

### Fixes
1. **Extend the `Source` frozen dataclass** (`source_router.py:54`, after `requires_super`) with the PART-1 descriptor fields, ALL defaulting empty so every existing positional/kwarg row is byte-unchanged:
   - `locale_paths: Tuple[str, ...] = ()`, `subdomain_patterns: Tuple[str, ...] = ()`, `currency: str = ""`, `discovery_query_templates: Tuple[str, ...] = ()`, `mechanism: str = ""`, `pdp_url_pattern: str = ""`, `sample_url: str = ""`, `status: str = ""`.
   - **HARD RULE:** tuple defaults MUST be bare `= ()` (frozen-dataclass-safe immutable), NEVER `field(default_factory=list)`. `mechanism` enum: `"" | curl | json_api | sitemap | algolia | shopify | render | provider`.
2. **Add two registry-filter selectors** beside `get_shopify_sources_for_category` (`:383`) / `get_algolia_sources_for_category` (`:401`):
   - `get_jsonapi_sources_for_category(category)` → `mechanism == "json_api"`, bahrain-tier, category-matched.
   - `get_sitemap_sources_for_category(category)` → `mechanism in {"sitemap","curl"}` (or a new `is_sitemap` flag — implementer's call; prefer `mechanism` to avoid a 7th bool). Both mirror the Shopify-selector shape exactly (returns `[]`, never raises).
3. **Registry flag corrections** (the STALE flips):
   - **bolo.bh** `:94-97` → remove `is_render_only=True`; set `mechanism="sitemap"`, `currency="BHD"`, `subdomain_patterns=("www.",)`, `pdp_url_pattern="/products/{internal_id}-{slug}"`, `sample_url` (a live-verified PDP), `status="live"`. Update the inline comment from "Vue SPA" to "Nuxt SSR plain-curl JSON-LD (recon 2026-06-23)".
   - **nasserpharmacy.com** `:116-122` → remove `is_render_only=True`; set `mechanism="json_api"`, `currency="BHD"`, `locale_paths=("/bh-en",)`, `pdp_url_pattern="/bh-en/{product_alias}"`, `sample_url`, `status="live"`.
   - **boutiqaat.com** `:142-146` → **CONDITIONAL — DISPATCHER-GATE (see flags).** Wave-1 default per design + Finders 1/2: KEEP `is_render_only=True, requires_super=True`, set descriptor metadata only (`mechanism=""` or `"render"`, `status="provider-test-candidate"`). Finder 3's curl-JSON-LD GO claim is re-verified in Wave 4's prep, NOT taken on faith here.
   - **sephora.bh → sephora.me** `:138-141` → REPLACE the domain literal with `sephora.me`; KEEP `is_render_only=True, requires_super=True`; set `locale_paths=("/bh-en",)`, `currency="BHD"`, `mechanism="provider"`, `pdp_url_pattern="/bh-en/p/{slug}/{product_id}"`, `sample_url="https://www.sephora.me/bh-en/p/size-up-immediate-supersized-volume-mascara/713779"`, `status="provider-test-candidate"`.
4. **Optional `build_site_discovery_query` enhancement** (`:667-674`): prefer `discovery_query_templates`/`locale_paths` over bare `site:{domain}` ONLY when non-empty; empty rows keep today's exact branch. Gate behind a non-empty check. (Low priority — can defer; flag if it touches the default branch.)

### Exact files + anchors
- `app/services/source_router.py:54` (dataclass), `:383`/`:401` (new selectors), `:94-97`/`:116-122`/`:138-141`/`:142-146` (rows), `:667-674` (optional discovery).
- `docs/contracts/bahrain-source-matrix.md` (matrix rows: bolo/nasser move (d)/(e)→(a)/(b); sephora.bh literal→sephora.me).

### Test contracts (TDD — NO live network)
- **NEW** `tests/test_source_descriptor_fields.py`: defaults empty on a bare `Source(...)`; tuple defaults are `()`; `mechanism` value-set pin; every `mechanism in {curl,json_api,sitemap,shopify,algolia}` bahrain row is NOT render-only AND NOT requires_super; every `mechanism in {provider,render}` row IS render-only/requires_super.
- **NEW** selector pins: `get_jsonapi_sources_for_category("supplements")` contains `nasserpharmacy.com`; `get_sitemap_sources_for_category("makeup")` contains `bolo.bh`; both return `[]` for an unknown category; never raise.
- **MODIFY (the breaking-by-design pins) — update in lockstep:**
  - `test_is_render_only_flag.py:28-34` — MOVE `bolo.bh` + `nasserpharmacy.com` from `RENDER_ONLY_DOMAINS` to `CURL_DIRECT_DOMAINS` (`:37-42`). (nasser is json_api not curl-JSON-LD, but it IS curl-tier / non-render — the set name is "not-render-only"; add a comment.)
  - `test_curl_before_render_budget.py:53-178` — every `nasserpharmacy.com` case (curl=0/render=2) INVERTS to curl-capable (curl=1/render=0). Rewrite using the new mechanism routing. (Most-affected file.)
  - `test_cascade_order_regression_qa.py:287,337,357-408` — `:337 assert is_render_only_domain("nasserpharmacy.com") is True` flips to False; the two cascade cases rewrite to curl-wave.
  - `test_render_wave_domain_cap.py:41-75` — swap `bolo.bh`/`nasserpharmacy.com` for still-render-only domains (`bn.boots.com`, `megamart.bh`, `alosraonline.com`).
  - `test_fragrance_content_quality.py:830-1048` — `_G2_SUPER_DOMAINS` and all `sephora.bh` literals → `sephora.me` (G2 gating logic preserved by keeping `requires_super=True`; only the literal changes).
  - `test_source_usage_field.py:60` (comment), `test_bahrain_source_matrix_coverage.py:206` (comment) — `sephora.bh`/`bolo.bh` literal updates.
- **Drift-guard:** `_genuine_bh_capable` (`:73`) now returns True for supplements/skincare/makeup/haircare via the newly-non-render bolo/nasser rows. Verify the LENIENT gate still passes and update `STRICT_KNOWN_SOURCE_GAPS` (`:51`) if a strict gap closes.

### Regression guards
- `test_eval_genuine_methods_parity.py` — UNCHANGED this wave (no new method strings yet). Must stay green.
- `test_f8_registry_pharmacy_domain_parity` (`:200`) — `PHARMACY_DOMAINS` (`price_service.py:520`) unchanged; bolo already in both, nasser registry-only (parity allows). Confirm green.
- `test_source_router_bahrain_first.py` / `test_source_router_shopify_l13.py:43` — nasser still routed + bahrain-tier + `is_shopify is False`. Confirm green (non-breaking).

### Dependencies
None. This is the foundation.

### DISPATCHER-GATE flags
- **F1a (boutiqaat verdict conflict):** Finder 3 live-claims boutiqaat cracks $0 via plain-curl JSON-LD (3 PDPs, incl. a 100ml fragrance at 50.43 BHD), flatly contradicting Finders 1/2 + the design's CONDITIONAL. **Wave-1 ruling: keep boutiqaat render-only/requires_super (conservative). The crack-or-defer decision is RE-VERIFIED at the start of Wave 4, not taken on a single finder's word.** If re-verify confirms curl-JSON-LD, boutiqaat promotes to a Wave-4 $0 adapter; if not, it defers to provider-test alongside sephora.me.
- **F1b (sephora.me apex vs www):** registry key = `sephora.me` (apex); canonical host `www.sephora.me/bh-en`. Confirm `match_registry_apex`/`is_render_only_domain` www-suffix-strip handles it (Finder 1 says `_normalize_domain` does).

---

## WAVE 2 — Sitemap/search DISCOVERY channel (the new NON-Serper resolver)

**Why second:** the bolo + boutiqaat adapters need name→PDP-URL resolution from a Redis-cached slug index BEFORE they can fetch+parse. nasser's discovery is its own search API (built inside its adapter, Wave 3). This wave builds the shared off-clock index + the per-query matcher. Depends on Wave 1's `mechanism`/selectors.

### Fixes
1. **A `RegionalSitemapIndex` builder** (new module, e.g. `app/services/sitemap_discovery_service.py`): fetch a source's sitemap-index → child sitemaps → extract `<loc>` PDP URLs → store a compact `{normalized_slug_token → pdp_url}` map in Redis under `discovery:sitemap:{domain}`, TTL ~24h (sitemaps `<changefreq>daily</changefreq>`; Shopify-catalog precedent is 6h).
   - **CRITICAL — off-clock only.** bolo = 16 children × ~21k = ~336k URLs / ~20MB; boutiqaat = 27MB+20MB. The index MUST be built by an OFF-CLOCK job, NEVER on the 15s request clock. Host: a NEW `scripts/cron_index_sitemaps.py` ($0, Serper-independent — do NOT couple to the paid-Serper warmer flag), flag-gated `ENABLE_SITEMAP_INDEX` (default OFF, fail-closed).
2. **A per-query matcher** `_match_sitemap_slug(slug_index, query)` reusing the Shopify-matcher helpers: `normalize_words` (`price_service.py:3824`/`:2296`), `numbers_match` (`:2301`), `variant_mismatch` (`:2352`) — query tokens ⊆ slug tokens + numbers-match + variant-guard. Returns the best PDP URL or None.
3. **Request-time lookup**: `resolve_pdp_via_sitemap(domain, query)` → Redis index read (NO live fetch on clock) → matcher → PDP URL or None. On a cold/missing index → graceful None (honest MISS → cascade continues → pending). Do NOT crawl on miss.
4. **Caching layers (3):** sitemap index (24h) + per-product price cache (`price_cache_ttl` genuine 7d) + negative cache — but an adapter no-match must be treated like `converted_usd` (negative-cache EXEMPT per SF-1, `price_service.py:204`) so a later index refresh can upgrade it, NOT a 30d structural dead-end.

### Exact files + anchors
- **NEW** `app/services/sitemap_discovery_service.py` (builder + matcher + resolver).
- **NEW** `scripts/cron_index_sitemaps.py` (off-clock index job, flag-gated).
- Reuse: `price_service.normalize_words/numbers_match/variant_mismatch` (`:2296/:2301/:2352`), `cache_service._redis_get/_set`, `should_negative_cache` (`:175`).

### Test contracts (TDD — mocked sitemap XML, NO live network)
- **NEW** `tests/test_sitemap_discovery.py`:
  - Fixture `tests/fixtures/bolo_sitemap_index.xml` + `bolo_sitemap_products1.xml` (small slice) → builder produces `{slug_token → pdp_url}`; asserts a known slug maps to its `/products/{id}-{slug}` URL.
  - Matcher: `_match_sitemap_slug(index, "CeraVe Vitamin C Serum")` → the cerave PDP URL; a no-match query → None; a variant-mismatch (50ml query vs 100ml slug) → None or the variant-guard fires.
  - **Index-cache contract:** index fetched once, Redis-cached — assert a second resolve does ZERO HTTP (monkeypatch the fetcher with a call-counter).
  - Empty/missing index → resolver returns None gracefully (no raise, no crawl).
  - Negative-cache: an adapter no-match is NOT 30d-negcached (exempt-like `converted_usd`).

### Regression guards
- No change to `_GENUINE_BH_SOURCE_METHODS` or the cascade yet (this wave is discovery-only, consumed by Wave 3). `comm` branch-only-NEW == [].

### Dependencies
Wave 1 (mechanism field + selectors).

### DISPATCHER-GATE flags
- **F2a (no clean public search API for bolo/boutiqaat):** Finders 2+3 both probed and found NO usable JSON search endpoint in read-only budget (bolo `/api/v1/*` → 500; boutiqaat `searchplus/rest` → 404). The sitemap-index IS the resolver. A headless XHR capture COULD replace it later but is out of scope. Confirm the dispatcher accepts the sitemap-index (not a search API) as the bolo/boutiqaat discovery mechanism.
- **F2b (index host decoupling):** Finder 2 OU-6 recommends a NEW `cron_index_sitemaps.py` over folding into the paid-Serper warmer cron — sitemap indexing is $0 and Serper-independent. Ratify the separate cron.
- **F2c (cold-request behavior):** with no index yet built (flag OFF or first deploy), bolo/boutiqaat resolve to None → pending. This is honest but means the genuine-share win only lands AFTER the index cron runs (an Ahmed activation, like the warmer). Flag this as a known activation dependency.

---

## WAVE 3 — The 3 storefront ADAPTERS (bolo, nasser, boutiqaat-conditional)

**Why third:** adapters consume Wave 1's flags/selectors + Wave 2's discovery. Each adapter is discover→fetch→parse→stamp-genuine, hooked into the FREE direct-prefetch slot. Each ships ONLY after a live BHD-price probe (verify-or-omit). This is the largest wave — consider splitting into 3a/3b/3c sequential sub-tasks (one adapter per implement agent, path-restricted commits).

### Fixes

**3a — bolo.bh adapter** (`mechanism="sitemap"`, $0 plain curl):
- `fetch_bolo_price(name, currency)` → `resolve_pdp_via_sitemap("bolo.bh", name)` (Wave 2) → `curl_fetch_html(pdp_url)` (`price_service.py:3617`) → parse.
- **PARSE — DISPATCHER-GATE (see flags):** Finder 3 says `extract_jsonld_price` (`:3135`, handles `@graph`) reads bolo's PDP JSON-LD as-is → `page_scrape_jsonld` (already genuine, NO new method). Finder 2 says the price is in the Nuxt `"price":N` payload + `<sup class="currency">BHD</sup>`, NOT schema.org JSON-LD → needs a bolo-specific Nuxt regex + a SKU/variant-bind guard (the 793KB HTML carries multiple `"price"` values: 66.32/129/130). **Resolution: try `extract_jsonld_price` FIRST (Finder 3's live claim); fall back to a bolo-Nuxt-`"price"` parse ONLY if the JSON-LD path returns None on the live fixture.** The implement agent MUST drive both against a REAL saved PDP fixture and pick whichever extracts the correct main-product BHD price (binding to the PDP's primary product, not a carousel item).
- Stamp `page_scrape_jsonld` (JSON-LD path) OR a new `sitemap_curl` (Nuxt path) — see method-string flag below.

**3b — nasserpharmacy.com adapter** (`mechanism="json_api"`, $0 single authenticated GET):
- `fetch_nasser_price(name, currency)` → `GET https://newapi.nasserpharmacy.com/v1/filterSearchs?search_term={name}&page=1&limit=20&...&lang=1&currency_code=BHD` with headers `Nasser:<token>`, `MOBILEOS:REACT`, `APPVERSION:1`.
  - **`page=1` REQUIRED** (422 without it). **`currency_code=BHD` drives server FX.**
  - **The price is in the SEARCH response — NO second `/newproduct` call** (Finder 3 live-verified; the recon's STEP-2 POST is unnecessary and 404'd).
  - Match query to `products[].name` via `strict_title_match`/`numbers_match`; prefer the lower of `price`/`special` (special != "0" = active offer); `decimal_places=3` (BHD fils — round to 3); `stock_text`-aware. Stamp `source_method="local_bhd"` (genuine, native BHD).
- **Static guest token** read from the `NASSER_GUEST_TOKEN` env (empty default → fail-closed; the recon value from Finder 3's bundle extraction is BURNED + redacted from this doc — re-scrape fresh + set on Railway before activation). Token-missing/401 path → None (verify-or-omit).

**3c — boutiqaat.com adapter** (CONDITIONAL — crack-in-implementation):
- **RE-VERIFY FIRST** (out-of-band probe, NO commit): does a live boutiqaat `/en-bh/{cat}/{slug}-{id}/p/` PDP curl-fetch yield a JSON-LD BHD price via `extract_jsonld_price`?
  - **If YES** (Finder 3's claim holds): ship as a `mechanism="sitemap"` + curl-JSON-LD adapter identical in shape to bolo (`fetch_boutiqaat_price`), flip the Wave-1 row off `is_render_only`/`requires_super`, stamp `page_scrape_jsonld`. Categories makeup/skincare/haircare/fragrances.
  - **If NO** (Finders 1/2 CONDITIONAL holds): DEFER — boutiqaat stays render-only/requires_super (Wave 1 default), no adapter ships, it joins sephora.me as a provider-test candidate (Wave 4 measures it too).

**3d — hook all shipped adapters into the FREE prefetch slot** (`scs.py:4139-4176`):
- Add `_jsonapi_sources_pf = get_jsonapi_sources_for_category(category)` + `_sitemap_sources_pf = get_sitemap_sources_for_category(category)` beside `_shopify_sources_pf`/`_algolia_sources_pf`.
- **DO NOT inherit the `not is_supplement` gate** (`:4140/:4143`) — bolo/nasser COVER supplements. Either un-gate the new selectors OR add an explicit Stage-1.5 in the supplement branch (`scs.py:4870+`, between iHerb `:4841` and pharmacy `:4876`). Implementer's call; pin whichever in a test.
- Fire as `asyncio.ensure_future(asyncio.gather(*(fetch_X(s.domain, full_name, currency/category) ...), return_exceptions=True))`; consume via `_prefetched_direct`; cancel via `_cancel_prefetched_direct` (`:4169`). Resolved price → `self._price_candidates` so `_select_best`/`reconcile_pair_fairness` see it.

**3e — new genuine source_method(s) → join BOTH sets in lockstep** (only if a new string is introduced):
- IF bolo lands as `sitemap_curl` (Nuxt path) → add `"sitemap_curl"` to `_GENUINE_BH_SOURCE_METHODS` (`price_service.py:4267`) AND `GENUINE_BH_SOURCE_METHODS` (`eval_runner.py:400`).
- IF nasser is decided to stamp `json_api` instead of `local_bhd` → add `"json_api"` to BOTH.
- **PREFERRED (minimizes risk):** bolo → `page_scrape_jsonld` (existing), nasser → `local_bhd` (existing) → **NO new method string, NO set edit, parity test untouched.** Add new strings ONLY if the parse path genuinely can't reuse an existing genuine method. DISPATCHER-GATE: confirm the final method-string decision.

### Exact files + anchors
- `app/services/price_service.py` — `fetch_bolo_price`, `fetch_nasser_price`, (cond.) `fetch_boutiqaat_price` (clone `fetch_shopify_price`/`fetch_algolia_price` shape, `:3906`/`algolia_service.py:326`); reuse `extract_jsonld_price` `:3135`, `curl_fetch_html` `:3617`, match helpers `:2296-2352`; (cond.) `_GENUINE_BH_SOURCE_METHODS` `:4267`.
- `app/services/structured_comparison_service.py:4139-4176` (prefetch hook) + `:4870+` (supplement Stage-1.5, if chosen).
- (cond.) `scripts/eval_runner.py:400` (parity lockstep).

### Test contracts (TDD — recorded fixtures, monkeypatched fetchers, NO live network)
- **bolo:** `tests/fixtures/bolo_pdp_cerave.html` → `fetch_bolo_price`/`extract_jsonld_price(...,"BHD",query_name="CeraVe Vitamin C Serum")` asserts `amount≈11.62, currency=="BHD"`, genuine method; multi-`"price"` HTML → binds the MAIN product, not a carousel item; miss → `None` (NOT a pending dict — the WS-2 `_price_fallback_on_miss` revert lesson).
- **nasser:** `tests/fixtures/nasser_filterSearchs_cerave.json` → `_match_nasser_product(resp, "CeraVe Foaming Cleanser")` → `amount==13.341, currency=="BHD", source_method=="local_bhd"`; wrapper test asserts headers `Nasser/MOBILEOS/APPVERSION` + `page=1`+`currency_code=BHD` sent; token-missing/401 → None; `special != "0"` → picks the lower price; `decimal_places=3` rounding.
- **boutiqaat (cond.):** `tests/fixtures/boutiqaat_pdp_frag.html` → `extract_jsonld_price(...,query_name="Ghuyoum Alqassar Eau de Parfum 100ml")` → `amount≈50.43, "BHD"` (only if the GO path ships).
- **Genuine-set membership pin** (if a new string added): `assert {"sitemap_curl"/"json_api"} <= _GENUINE_BH_SOURCE_METHODS`; `is_price_showable("x",{"amount":5,"currency":"BHD","source_method":<new>}) is True`; `price_cache_ttl(...)==GENUINE_PRICE_CACHE_TTL`; `should_negative_cache(...) is False`.
- **Showable-guard composition:** a bolo sample/decant under the fragrance/haircare floor, or a low-fragrance price → `is_price_showable() is False` (the implausible-low/high/sample guards `:991-1011` still bite — no new bypass).
- **Selector + supplement-wiring pin:** `get_jsonapi_sources_for_category("supplements")` contains nasser; the prefetch/Stage-1.5 fires for supplements (assert the supplement branch reaches the new adapter).
- **Fairness:** an adapter price lands in `self._price_candidates` → `reconcile_pair_fairness` (`:2115`) re-selects a size-matched genuine price with zero new calls (adapter carries `title`+`size` for `effective_pair_size_ml` `:1057`).

### Live verify step (SEPARATE, per adapter — the verify-or-omit gate)
A standalone read-only probe (`.qa-bh-sourcing/_verify_<adapter>.py`, out-of-band, NOT a unit test): a real bolo PDP → genuine `page_scrape_jsonld`/`sitemap_curl` BHD; a real nasser `filterSearchs` → `local_bhd` BHD (re-confirm the static token live); (cond.) a real boutiqaat PDP → JSON-LD BHD. **An adapter ships ONLY if its live probe returns a real BHD amount.** Re-run on deploy (token may rotate; `scripts/verify_source_registry.py` is the existing manual hook — HEAD/curl each `sample_url`).

### Regression guards
- `test_eval_genuine_methods_parity.py` — green (no new string in the preferred path; OR both sets edited in lockstep).
- The Wave-1 curl-vs-render cascade tests (already rewritten in Wave 1) — green with the new curl-tier routing.
- fb8696c honesty set: `is_price_showable`/`make_pending_price`/`should_negative_cache` behavior unchanged for non-adapter paths; `comm` branch-only-NEW == [].

### Dependencies
Wave 1 (flags/selectors), Wave 2 (sitemap discovery — bolo/boutiqaat only; nasser is self-contained).

### DISPATCHER-GATE flags
- **F3a (bolo parse-path conflict — already covered):** JSON-LD (Finder 3) vs Nuxt-`"price"` regex (Finder 2). Resolution = drive BOTH against the real fixture, pick the one that extracts the correct main-product price. Don't ship blind.
- **F3b (nasser static token rotation):** the token is a const baked into `main.<hash>.js`; rotates on a FE redeploy (filename hash changes). Finder 3's live 401-on-wrong-token proves the gate is strict (fails cleanly, not silently). Store as a const + a deploy-time liveness probe; re-scrape `main.*.js` on a liveness failure. Flag: this is the ONE live-credential risk in the bundle.
- **F3c (boutiqaat crack verdict):** the Wave-1-deferred decision is made HERE via the re-verify probe. GO → $0 curl adapter; NO-GO → defer to provider-test. Dispatcher gates the probe result before the boutiqaat adapter commits.
- **F3d (method-string decision):** prefer reusing `page_scrape_jsonld`/`local_bhd` (no set edit, no parity churn) over inventing `sitemap_curl`/`json_api`. Confirm before any `_GENUINE_BH_SOURCE_METHODS` edit (and if edited, BOTH sets in lockstep or the parity test reds).
- **F3e (supplement-branch wiring):** the prefetch slot is gated `not is_supplement` (`:4140`). bolo/nasser cover supplements → un-gate the new selectors OR add an explicit Stage-1.5. Pin whichever in a test (a supplement compare must reach the new adapters).

---

## WAVE 4 — sephora.me regional-alias finalization

**Why fourth:** the Wave-1 sephora.bh→sephora.me row swap is done; this wave finalizes the alias as a `provider-test-candidate` (NO prod price-path wiring — sephora.me is Akamai-walled, $0 discovery is structurally impossible per Finder 4 OU-2: empty BH sitemap). This is a SMALL wave — mostly confirming the alias is correctly gated OFF and routes identically to the old sephora.bh under `SCRAPEDO_SUPER` OFF.

### Fixes
1. Confirm the `sephora.me` row (Wave 1) is filtered out of `get_sources_for_category` when `SCRAPEDO_SUPER` OFF (default) via `_super_routing_enabled` (`:331`) — byte-identical OFF-state routing to old sephora.bh.
2. Confirm `status="provider-test-candidate"` + `sample_url` set; NO price adapter (sephora.me discovery needs render, deferred to the provider test).
3. (Optional, if Wave-1 deferred it) the `_G2_SUPER_DOMAINS` literal + G2 tests already swapped to `sephora.me` in Wave 1 — verify.

### Exact files + anchors
- `app/services/source_router.py` (sephora.me row, already in Wave 1), `:331` (`_super_routing_enabled`).
- `tests/test_fragrance_content_quality.py:830-1048` (G2 super-routing, swapped in Wave 1).

### Test contracts
- `SCRAPEDO_SUPER` OFF → `sephora.me` absent from routing (byte-identical to today). ON → routed render-only (the G2 ON-path). No haircare/electronics category leak (per `:896-905`).

### Regression guards
- G2 byte-identity tests green; the OFF-state registry is unchanged from today's behavior (only the domain literal differs).

### Dependencies
Wave 1.

### DISPATCHER-GATE flags
- **F4a:** sephora.me ships NO price adapter (correct — Akamai-walled + empty BH sitemap = no $0 path). This wave is alias-hygiene only; the actual render-capability test is Wave 5.

---

## WAVE 5 — Provider-test HARNESS (sephora.me Scrape.do-Super + Zyte) — DESIGN-BUILT, NOT PROD-WIRED

**Why last + separate:** this is an out-of-band measurement experiment, run ONCE AFTER the 3 adapters ship, to decide if a residential-BH render cracks Akamai where a datacenter render gets 403. It does NOT touch the cascade, does NOT flip the prod flag, does NOT wire a price path. `SCRAPEDO_SUPER` stays OFF in Railway.

### Fixes (build the harness)
- **NEW** `.qa-bias-rerun/_sephora_provider_test.py` (out-of-band, `.qa-*` convention — sibling of `_render_capability_bh_retailers.py`).
- **Reuse, don't re-implement:** `scrapedo_service.render_page_with_status(url)` (`:160`, returns `(html,status,cost)` — the budget anchor); `_super_params()` (`:49`); `reset_super_flags_cache()` (`:76`); classify via `_detect_cf_interstitial` (`scs.py:93`) PLUS an added Akamai check (`Server:AkamaiGHost`/`"Reference #"`/`"AkamaiGHost"`/`"Access Denied"`/status 403 — the existing `_CF_INTERSTITIAL_MARKERS` `:78` lacks an Akamai token, OU-3); price via `extract_price_from_html` (`price_service.py:3324`).
- **Env guard (no-prod-write):** `load_dotenv()` → THEN blank `UPSTASH_REDIS_URL/_TOKEN=""` → set `SCRAPEDO_SUPER="true"`, `SCRAPEDO_GEOCODE="bh"`, `SCRAPEDO_TIMEOUT="35"` → `reset_super_flags_cache()` (MUST reset — flag is process-cached at first read; the footgun). Redis blanked → `record_usage` no-ops, breaker fail-open → never pollutes `budget:scrapedo:<month>` / never trips the shared breaker.
- **Script-local credit cap: 60 Scrape.do credits/run** (the SOLE spend gate, out-of-band); abort before a call if `credits_spent + worst_case(25) > cap`. Sum the returned `cost` (super bills ~10-25/req).
- **Zyte leg (no repo integration exists):** a single local `async def _zyte_render(url)` → `POST https://api.zyte.com/v1/extract` Basic-auth `(ZYTE_API_KEY,"")`, body `{"url":..,"browserHtml":true,"geolocation":"BH"}`; read `["browserHtml"]`; own cap (4 renders, fixed tally — no clean per-request header, OU-4). `ZYTE_API_KEY` in LOCAL `.env` only (Ahmed-provided, free trial); NO Railway env, NO service file.
- **The 4 LIVE-VERIFIED URL shapes** (no rediscovery needed): PDP `…/p/size-up…/713779` (403 Akamai), category `/bh-en/makeup` (403), search `/bh-en/search?q=mascara` (403), un-walled control `/bh-en/brands` (200, 0 harvestable links). Test the harvest path (shapes 2+3), not just the PDP — sephora.me has NO BH sitemap (OU-2), so discovery itself needs the render.
- **Output:** `.qa-bias-rerun/_sephora_provider_test_result.json` mirroring the prod `_record_provider_attempt` field set (so a future narrow-wire replays into `source_trace`); emit `verdict ∈ {GO_SCRAPEDO, GO_ZYTE, NO_GO}` + credit tally.

### Test contracts
- **NONE in the unit suite** — this is an out-of-band experiment script, not prod code. (Optionally a tiny pure-function test for the classify/harvest-regex helper against a saved-HTML fixture, NO network.)

### Run step (the actual experiment — AFTER adapters ship, ONCE)
Run `_sephora_provider_test.py` once; read the verdict:
- **GO_SCRAPEDO** (super geoCode=bh returns 200 + no Akamai marker + a BHD price OR harvestable PDPs that then price) → a SEPARATE narrow-wire decision: a PDP-only `sephora.me` provider path (avoid the category/search path — `validate_scrape_url` `:608` rejects search/category pages, OU-5), gated by `_super_routing_enabled`, ships ONLY after this confirmed evidence.
- **GO_ZYTE** (super 403s but Zyte browserHtml+geolocation:BH passes) → document Zyte as the provider; a minimal Zyte service is a follow-on decision, NOT this step.
- **NO_GO** (both block all 4 real URLs) → document the structural Akamai gap; sephora.me's categories are largely covered by boutiqaat+nasser anyway → defer; keep `SCRAPEDO_SUPER` OFF.

### Dependencies
Waves 1-3 (the adapters ship first; this measures the residual gap).

### DISPATCHER-GATE flags
- **F5a (the whole open question, OU-1):** does residential-BH egress crack Akamai *Bot Manager* (behavioral/TLS-fingerprint, not just IP-geo)? Unproven — the harness exists to answer it. A BH residential IP may STILL fail Akamai's JS/sensor challenge. Hence the Zyte A/B leg.
- **F5b (OU-6 — super has NEVER actually fired in prod):** MEMORY records `SCRAPEDO_SUPER` ON across 9 nocache pulls = super never fires (cascade short-circuits on converted_usd/curl-JSON-LD before Tier 1.5d; BH luxury SPAs have no Serper URL to render). This harness is the FIRST controlled test that FORCES super onto a known sephora.me PDP — it isolates a render capability prod has never exercised. The `SCRAPEDO_SUPER` ON state on Railway (per MEMORY) is dormant overhead; consider reverting OFF post-experiment if NO_GO.
- **F5c (Akamai marker gap, OU-3):** if GO ships a narrow wire, ADD the Akamai markers to the prod `_CF_INTERSTITIAL_MARKERS` (`:78`) so `detected_cf` flags Akamai blocks in `source_trace` (today a 403 Akamai page records `cf_block` only via the status branch).

---

## SHIP-GATE (backend-only, the whole-bundle merge gate)

1. **Free-unit `comm` zero-regression:** temp-`main`-worktree, run the free-unit suite (`-m "not (live_unit or live_db or integration)" --ignore=tests/test_integration.py`) on BOTH branch and main, `comm -13` of sorted FAILED-test sets → **`branch-only-NEW == []`**. (The known order-flaky `test_rate_limiting_complete` + `test_value_math.py` TDD-RED stubs are pre-existing excludes — verify byte-identical to main, not branch-introduced.)
2. **Parity pin GREEN:** `test_eval_genuine_methods_parity.py` (if any method string added, both sets in lockstep).
3. **Drift-guard GREEN:** `test_bahrain_source_matrix_coverage.py` LENIENT gate passes; `STRICT_KNOWN_SOURCE_GAPS` updated for any closed strict gap; the rewritten `test_is_render_only_flag`/`test_curl_before_render_budget`/`test_cascade_order_regression_qa`/`test_render_wave_domain_cap`/`test_fragrance_content_quality` G2 all green.
4. **smoke20 vs baseline `54b603e8`:** `python -m scripts.eval_runner --subset smoke20 --mode regression --baseline-run-id 54b603e8` — winner ≥ 0.50, factual 1.0 HELD, specs ~0.95 (cold-run noise tolerated). **GOTCHA:** the stale OS `SUPABASE_*` env false-fails the baseline-fetch tooling → restart Claude Code OR `source .env` before the eval; read the metrics axis manually, don't trust the automated "GATE FAIL" if it's the short-ID baseline-fetch tooling fault.
5. **Fresh-nocache prod genuine-share confirm (the verify-or-omit live gate):** AFTER deploy, a fresh `?nocache=true` prod pull on a real bolo product (e.g. a CeraVe supplement) → genuine `page_scrape_jsonld`/`sitemap_curl` `source_method`, NOT `converted_usd`; a nasser product → `local_bhd`. The NEW genuine source_methods must be VISIBLE in the response `source_method` + `/admin/costs` registry bucket. (Note: eval uses `nocache=true` = COLD scraping; the bolo/boutiqaat sitemap-index path needs the `cron_index_sitemaps.py` ACTIVATED for the cached genuine-share — an Ahmed activation, like the warmer. Cold bolo with no index → pending = honest, not a regression.)
6. **eval-is-POST-deploy:** the eval_runner is a prod-HTTP harness — run smoke20 + the genuine-share confirm AFTER the backend deploys, never on un-deployed branch code.
7. **Backend-only:** NO EAS update (no FE changes). Confirm `git status -- SmartCompareApp/` clean.

**Activation dependencies handed to Ahmed (zero Claude tokens):** register the `cron_index_sitemaps.py` Railway cron + flip `ENABLE_SITEMAP_INDEX` (the bolo/boutiqaat cached-genuine-share lever); run the Wave-5 provider-test ONCE + decide GO/NO-GO; (if NO_GO) revert `SCRAPEDO_SUPER` OFF on Railway.

---

## CROSS-CUTTING DISPATCHER-GATE SUMMARY (the over-stated / drift / risk flags)

| # | Flag | Severity | Resolution |
|---|---|---|---|
| **F1a** | **boutiqaat verdict CONFLICT** — Finder 3 live-claims $0 curl-JSON-LD GO (3 PDPs, 50.43 BHD fragrance); Finders 1/2 + design say CONDITIONAL/uncracked. | HIGH | Wave-1 keeps it render-only (conservative); Wave-3c re-verifies live before any adapter commits. Don't ship boutiqaat on one finder's word. |
| F3a | bolo parse-path: JSON-LD (F3) vs Nuxt-`"price"` regex (F2); 793KB HTML has multiple `"price"` values. | MED | Drive BOTH against a real fixture; bind to main product, not carousel. |
| F3b | nasser static token rotation (const in `main.<hash>.js`, rotates on FE redeploy). | MED | Const + deploy-liveness probe + re-scrape on 401. The one live-credential risk. |
| F3d/F3e | method-string churn + supplement-branch `not is_supplement` gate. | MED | Prefer reusing `page_scrape_jsonld`/`local_bhd` (no parity churn); un-gate selectors for supplements + pin. |
| F2c/F5b | activation deps: sitemap-index cron (genuine-share lever) + `SCRAPEDO_SUPER` super has NEVER fired in prod. | LOW | Both are Ahmed activations; cold path is honest-pending, not a regression. |
| F5a | sephora provider-test feasibility — Akamai Bot Manager may resist residential-BH egress (TLS/JS fingerprint, not just IP-geo). | OPEN | The harness IS the answer; Zyte is the A/B control; NO_GO defers (boutiqaat+nasser cover the categories). |

**Anchor-drift confirmed CLEAN this session:** all finder-cited line numbers re-verified against live `fb8696c` code (`Source` `:19-54`, rows `:94/:116/:138/:142`, selectors `:383/:401`, genuine set `:4267`, eval set `:400`, prefetch `:4139`, drift-guard `:61-78`, render-only pin `:28-34`, curl-vs-render `:53-178`, G2 `:830-1048`). No drift found; the only conflict is the boutiqaat verdict (F1a), which is a finder-vs-finder disagreement, not an anchor error.