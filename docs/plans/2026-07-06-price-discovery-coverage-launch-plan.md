# Price-Discovery / Coverage — Launch-Readiness Plan (2026-07-06)

Consolidated from a 4-lens triage workflow, every load-bearing claim re-verified against
`smartcompare-fragfix` (main) source before writing. Goal: a SOON launch where search
**never dead-ends** for arbitrary/local products.

Repro symptoms:
- `Tom Ford Oud Wood vs Black Orchid` → 200 @29.5s, Black Orchid genuine (55 BHD woo_store_api), **Oud Wood PENDING**.
- `Ajmal Aristocrat vs Rasasi Hawas`, `Asghar Ali Shughf vs Ajmal Wisal` → **503 TIMEOUT @~30.6s, ZERO products** ("This one's not loading") — specs thrown away.

---

## (A) VERDICT — "are we over-relying on Serper / using the APIs wrong?"

**NO on the literal claim, YES on the underlying instinct.** The engine is architecturally
correct: direct store adapters (shopify/woo/salla/algolia/unbxd/noon/magento/occ/rest_json +
curl page-scrape) run FIRST via a Serper-free speculative prefetch + escalation, short-circuit
before any Serper call, and cancel pending Serper on a genuine BHD hit. That path is real and
works — it is exactly why Black Orchid resolves in ~2-4s via theperfumesclub woo. **Serper is
the FALLBACK-of-last-resort for discovery, not the primary.**

The correct half of the owner's concern **is the launch blocker**: the Serper `site:` discovery
fallback is doing far too much work because **local/long-tail adapter coverage is thin**, and
that slow fallback (~8s discovery + ~12s fan_out) blows the 15s price race and, for two-local-brand
pairs, the whole 30s hard cap. So the accurate framing is a **COVERAGE gap, not an API-misuse bug** —
PLUS a **graceful-degradation gap** that turns a slow price into a total dead-end.

Verified in code:
- `_get_price` price-resolution order confirmed: L1/L2/neg cache → Zyte(off) → Tier-1 Serper /shopping (converted hit PARKED, not returned) → Serper-FREE adapter escalation (short-circuits + cancels Serper on genuine BHD) → **only if no adapter carried it** → Serper `site:` discovery (4 concurrent `/search`) → curl fan_out → GPT estimate.
- The prefetch (`structured_comparison_service.py:4961-5008`) fires shopify/algolia/sitemap/jsonapi + woo/salla/occ/magento_gql/unbxd/rest_json/noon — it does **NOT** fire the curl-pagescrape selector.

---

## (B) LAUNCH BLOCKERS — must-fix so search never dead-ends (do THIS session, all safe)

### BLOCKER 1 — Streaming path throws away completed specs on hard-cap (THE dead-end)
**This is the actual cause of "503 / zero products / This one's not loading."** The SSE path is
what the FE uses, and it has NO partial-salvage — unlike the sync path.

Verified:
- **Sync path** `compare_from_text` (`structured_comparison_service.py:2634-2674`) already builds a `success:true` PARTIAL on hard-cap via `_partial_has_usable_data()` (2470) + `_build_partial_response()` (2487). **Good — keep.**
- **Stream path** (`:3336-3367`) wraps BOTH products' `_fetch_product_data` in ONE atomic `asyncio.wait_for(STREAM_HARD_CAP_SECONDS)`; on `TimeoutError` it yields `success:false / code:STREAM_TIMEOUT` with **ZERO product data** (`:3356-3367`). No stash, no partial. Specs that landed inside the 8s specs cap are discarded.
- Even the sync stash `self._partial_product_data = product_data` (`:2880`) is set **AFTER** the pair `asyncio.gather` (`:2870`) returns — so a cancellation mid-price-wait (the local-brand case where neither product's price settles) leaves `_partial_product_data = None` and the sync path also falls through to `INSUFFICIENT_DATA`/`TIMEOUT`.

**Exact change (`structured_comparison_service.py`):**
1. **Stash identity+specs EARLY, before the price wait, on BOTH paths.** In `_fetch_product_data`, right after `result = {brand, name, full_name, variant, category, query}` is built (~`:3919`), register that dict into a per-request ordered buffer pre-sized to 2 (reset alongside the other `_partial_*` resets). The buffer is non-empty with identity from t=0.
2. **Attach an `add_done_callback` to the specs task** (`:~4037`) that writes `result["specs"] = <specs>` into that SAME buffer entry the instant specs land (guarded try/except; on failure writes nothing → specs stays None).
3. **Stream path:** add the sync path's partial machinery. Seed `self._partial_product_data` before `:3336`; on `TimeoutError` at `:3343`, if `_partial_has_usable_data()` build via `_build_partial_response(...)` and yield it as `settle_complete`/`complete` with `partial:true` + 2 products, **never** the zero-product `STREAM_TIMEOUT`.
4. **Lower-risk alternative** (if per-task callbacks are too invasive): replace the pair-level `asyncio.gather` at `:2870`/`:3336` with a wrapper that stashes each product's `result` into the buffer slot the moment that product's fetch returns (`as_completed`-style). Combined with the specs-done-callback this covers the both-uncovered case where neither product finishes before 30s.

Gate: no new flag needed (it only ADDS a partial where a 503 was returned — strictly a degradation improvement). Optional `ENABLE_EARLY_SPECS_STASH` default-ON if a rollback lever is wanted.

**Regression test** `tests/test_partial_specs_stash_on_price_timeout.py`:
- patch `_get_specs` → real dict after ~0.2s; patch `_get_price` → `await asyncio.sleep(40)`; monkeypatch `STREAM_HARD_CAP_SECONDS` → 1.0; call `compare_from_text("Asghar Ali Shughf vs Ajmal Wisal", region="bahrain")`. Assert `success is True`, `metadata.partial is True`, `len(products)==2`, each carries the patched specs, NO `code in {TIMEOUT, STREAM_TIMEOUT}`.
- streaming variant iterating `compare_from_text_streaming(...)` — final `settle_complete`/`complete` carries `partial:true` + 2 products.
- both-hang variant (specs AND price time out) → falls through to `INSUFFICIENT_DATA` (proves the fix doesn't mask a genuine no-data case).
- happy-path pin: a fast-price pair still returns success with prices (no regression to the covered case).

### BLOCKER 2 — Orphaned GCC page-scrape rows have NO fast direct-fetch consumer (the coverage wiring bug)
**This is the "only relying on Serper for discovery" concern, verified in code.** ~64 GCC-tier
fragrance/perfume-house rows carry `mechanism=""` (plain curl / `page_scrape_jsonld`). The selector
that would give them a fast $0 direct-fetch, `get_curl_pagescrape_sources_for_category`
(`source_router.py:693-720`), is **hard-restricted to `tier=="bahrain"`** AND its ONLY caller is
the **supplements** Stage-3 (`structured_comparison_service.py:6241`, hardcoded `"supplements"`).
For fragrances these rows get NO prefetch consumer → they fall to the slow Serper `site:` discovery
(`build_site_discovery_query(tier="gcc")`) + curl fan_out → blows the 15s race → PEND / 503.

Contrast (verified): the woo/salla/occ/magento/unbxd/rest_json selectors use `_direct_fetch_sources`
(`source_router.py:760-775`) which DOES span `("bahrain","gcc")` and IS K-capped (`BH_GCC_FANOUT_K=6`).
The curl-pagescrape mechanism is the one left bahrain-only — and the blank-mechanism GCC rows match
NONE of the mechanism-keyed selectors, so `_direct_fetch_sources` doesn't reach them either. They are
genuinely orphaned for fragrances.

**Exact change (`source_router.py` + `structured_comparison_service.py`):**
1. Add a selector `get_curl_pagescrape_sources_for_category_all_tiers(category)` (or add a `tiers` param to the existing one) that mirrors `_direct_fetch_sources`: `s.tier in ("bahrain","gcc")`, `mechanism`-empty / `is_shopify`/`is_algolia`-excluded, ordered (bahrain before gcc, then `priority_rank`, then registry order), **K-capped via `_fanout_k()`** to bound the fan-out.
2. Wire it into the **speculative prefetch** at `structured_comparison_service.py:4961-5008` (a new `_curl_pagescrape_sources_pf`) and into `_consume_adapter_prefetch` escalation, so those ~64 rows become $0 direct curl+JSON-LD fetches that beat the 15s race — **no Serper call needed**.
3. Gate behind `ENABLE_BH_GCC_CATALOG_SOURCES` (already the flag guarding these rows). Safety: the adapter stamps genuine-BHD vs converted_usd by the **actual response currency**, so a GCC row can't mis-claim a BH price (a GCC/foreign-currency store returns `converted_usd`, correctly captioned by the PR#20 FE honesty work).

**Test:** pin that `get_..._all_tiers("fragrances")` returns the GCC blank-mechanism rows (asgharali/rasasi/swissarabian/…), K-capped ≤ `_fanout_k()`, bahrain-before-gcc order; a supplements call is unchanged; latency-invariant test still green (one bounded K-capped source group).

### BLOCKER 3 (optional, same session, tiny) — sync INSUFFICIENT_DATA branch should ship specs too
At `:2659` the sync path returns `INSUFFICIENT_DATA` when `_partial_product_data` exists but
`_partial_has_usable_data()` is False. With Blocker 1's early stash, a specs-present/price-slow case
now has usable data, so this branch will correctly build a partial instead — verify the early-stash
change makes `_partial_has_usable_data()` True in that case (specs check at `:2483`).

---

## (C) COVERAGE PLAN — local GCC sources to add + adapter shape

**Biggest lever = Blocker 2's wiring fix** (turns ~64 already-cataloged, already-live GCC rows into
$0 direct fetches). That alone moves the local perfume houses OFF the Serper path. On top of that,
add the named **`.com` main storefronts** (verified ABSENT — only regional subdomains exist today),
each mapping to an EXISTING adapter shape:

| Domain (candidate)            | Adapter shape / mechanism        | Why | Status |
|-------------------------------|----------------------------------|-----|--------|
| `asgharali.com`               | `shopify` (probe `/products.json`) | `om.asgharali.com` already cataloged; main site likely Shopify | **NEEDS web-discovery/liveness probe** |
| `rasasi.com`                  | `shopify` (probe `/products.json`) | consistent with `rasasistore.com` / `store.rasasi.com.sa` | **NEEDS probe** |
| `ajmalperfume.com` / `ajmal.com` | `magento_graphql` (`fetch_magento_graphql_price`) | consistent with cataloged `en-kwt.ajmal.com=magento_graphql` | **NEEDS probe** |
| `lattafa.com`                 | likely `shopify`                  | major GCC house, absent | **NEEDS probe** |
| `swissarabianperfumes.com`    | likely `shopify`                  | `swissarabian.com` cataloged as blank-mechanism (curl) | **NEEDS probe** |

Already-live BH fast adapters that cover much of the fragrance space (no action):
theperfumesclub + bh-en.smellsoreal (woo BH), goldenscent (algolia BH), klinq + en-kwt.ajmal
(magento), bahrain.naseem / bh.mubkhar / bh.afnan (shopify BH), noon_catalog (BH marketplace).

**For Tom Ford Oud Wood specifically:** no reachable $0 BH store currently carries it. Options
(post-launch, verify first): add any live BH woo/shopify store that stocks Tom Ford designer/niche;
rely on the already-wired `noon_catalog` row; or accept `converted_usd`/price-pending (now graceful
after Blocker 1). Also probe `bolo.bh` (known BH marketplace) as a direct row.

**Discovery guardrail (load-bearing):** exact platform + liveness + BHD currency for EVERY candidate
domain (`/products.json` reachable? Magento GraphQL endpoint live? currency BHD?) **must be
liveness-probed by a separate web-discovery pass before flipping `status="live"`.** Do NOT ship
unverified rows — that reopens the dead-wired-row class (PR#13). This is the "18-wide tripped the
rate-limit → run in a FRESH session, batch ≤4" pattern from CLAUDE.md.

---

## (D) SEQUENCING for a SOON launch

### THIS session (safe, code-only, no web discovery, no rate-limit exposure)
1. **Blocker 1** — streaming (and sync) early specs-stash + partial-on-hard-cap. *The dead-end fix; highest impact × safety.* + regression test.
2. **Blocker 2** — wire the all-tiers curl-pagescrape selector into prefetch + consume (gated by existing `ENABLE_BH_GCC_CATALOG_SOURCES`). *Turns ~64 live GCC rows into $0 fetches — the "not only Serper" fix.* + selector test.
3. **Blocker 3** — verify the sync `INSUFFICIENT_DATA` branch now ships specs.
4. Comm gate (branch-only-NEW == [] vs the 46-line baseline), flag-OFF byte-identity check for the new selector wiring.

**Launch-acceptable state after 1-3:** EVERY search returns specs + scores + verdict (never "not
loading"); local-brand/uncovered prices render as "pricing settling" instead of crashing; the ~64
GCC perfume-house rows resolve genuine/converted via $0 direct fetch instead of the slow Serper path.

### FRESH session (heavy web discovery + one delicate change — POST-launch, improves SHARE not dead-ends)
5. **Add the named `.com` main storefronts** (Table C) — liveness/platform-probe each, then add as fast rows mapped to shopify/magento adapters. Batch ≤4, fresh session (rate-limit).
6. **Cache-key-parity change (delicate, needs test coverage).** Verified gap: `build_size_aware_price_cache_key` → `_identity_cache_token` (`price_service.py:7775`) folds a size token, so a **sizeless** live query ("Tom Ford Oud Wood") yields an EMPTY token → legacy size-agnostic key, while a warmed/seeded "Oud Wood 100ml" carries a size token → a DIFFERENT key. The seeded genuine price exists but the live read misses it → PENDING. Fix = derive the read key from the RESOLVED-match identity, OR apply the fragrance flagship-100ml default identically on BOTH warm/seed write and live read. Pin with a test that a sizeless live query hits a sized seeded key. *This is the documented Wave-1 cache-key-parity gap — do it carefully with coverage, not under launch pressure.*
7. **Latency tuning (riskiest, last).** Shrink Serper `site:` discovery / `_fan_out_budget_seconds`, or tune the DORMANT `ENABLE_GENUINE_PRICE_PRIORITY`. CLAUDE.md pins this as "needs live tuning, gate on cold-live variance NOT the warmed KPI" → **not a pre-launch change.**

---

## Do NOT
- Do NOT reframe this as "fix Serper" — Serper is used correctly (adapters first, fallback-of-last-resort). Widen coverage + make price failure non-fatal.
- Do NOT ship catalog rows without a liveness probe (reopens the dead-wired class).
- Do NOT touch `ENABLE_GENUINE_PRICE_PRIORITY` or fan-out budgets before launch.
