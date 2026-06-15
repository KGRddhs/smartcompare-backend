# Genuine-BH Latency + Warmer Bundle — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.
> **Team model:** 4–5 parallel Opus agents (NOT Sonnet/Haiku) via TeamCreate, `mode: "bypassPermissions"`. Lane ownership marked with `<!-- OWNED BY: name -->`.

**Goal:** Stop luxury comparisons (esp. fragrances) from timing out, and deliver genuine BH (BHD) prices for the common catalog — by warming the price cache, failing fast to honest prices when a cold request can't finish, and trimming the live price-path latency. Make Firecrawl/Scrape.do usable off-clock for render-walled BH retailers.

**Architecture:** The genuine BH price path already *works and is correct* — proven: a cold Tom Ford pair resolves to Al Hajis 80 BHD + Ounass BH 118 BHD via curl JSON-LD for $0.017. The sole failure is **latency**: the full path is ~37.5s, over the 30s `STREAM_HARD_CAP`. Fix = (1) pre-warm genuine prices into the shared cache so live reads are instant; (2) make the hard cap return a best-available honest result instead of a 400 crash; (3) shave the ~20s price stage; (4) make the render-wave budget env-configurable so the off-clock warmer can render the walled retailers. No new sourcing engine, no matcher rewrite, no Serper overhaul (all proven already-working).

**Tech Stack:** FastAPI / Python 3.12 (backend on Railway), React Native / Expo (frontend via EAS), Upstash Redis (price cache), Serper (Google Search/Shopping), Firecrawl + Scrape.do (render scrapers), curl_cffi (curl JSON-LD), pytest, Jest.

---

## 0. Context & Proven Diagnosis (read first — do NOT re-investigate)

The bug: comparing **Tom Ford Ombré Leather vs Tom Ford Tobacco Vanille** (category=Fragrances) showed a frontend "couldn't load" error.

**Reproduced (prod, cold):** `GET /api/v1/text/compare?q=Tom+Ford+Ombr%C3%A9+Leather+vs+Tom+Ford+Tobacco+Vanille&region=bahrain&nocache=true` → **HTTP 400** after **30.9s**, body:
```json
{"success":false,"error":"We couldn't finish this comparison in time. Try again.","code":"BAD_REQUEST",...}
```

**What the evidence proved (harness scripts live in `.qa-bias-rerun/`):**
1. **It's a timeout, mis-surfaced.** The service returns `code:"TIMEOUT"` (`structured_comparison_service.py:1518`) but the route collapses every non-success into `HTTPException(400)` → `BAD_REQUEST` (`text_routes.py:311`). The copy ("couldn't…/Try again") also violates the no-scary-copy contract.
2. **Genuine prices are reachable and correct.** Full pipeline trace, cache-disabled, high cap (`_frag_pipeline_trace.py`): `success:True`, **Ombré Leather → 80.0 BHD `page_scrape_jsonld` alhajisbahrain.com**, **Tobacco Vanille → 118.0 BHD `page_scrape_jsonld` bahrain.ounass.com**, `total_cost=$0.0167`, `serper_calls=6`. Curl JSON-LD — the render wave wasn't even needed.
3. **NOT a matching bug** — `strict_title_match` passes "Tomford"↔"Tom Ford" (substring; `match_score=0.5≥0.4`). **NOT a currency-gate bug** (BHD stamped). **NOT "Serper poorly instructed"** — discovery found Al Hajis + Ounass BH itself.
4. **It IS latency.** Stage timings (`stage_timings_ms`): **total 37522ms** (> 30000 cap). Dominant: **`price_ms` ~17–20s/product** (the genuine winner confirms at 3.5s, but the stage burns ~20s on `gl=bh`-empty → `gl=us` fallback → discovery → multi-candidate scraping). Also `reviews_ms`~9s, `specs_ms`~4–8s, `verdict_ms`6.5s, `image_url_ms`~3–4s.
5. **Serper Shopping `gl=bh` is structurally empty** for BH fragrances (8/8 probe queries → 0 items; `gl=us` → 40 noisy USD). Documented stopgap in `serper_service.py:103-119`. (Not changing — discovery via `/search` organic + Shopify already reaches genuine.)
6. **Render budget is hard-capped.** `_FAN_OUT_BUDGET = 12.0` (`structured_comparison_service.py:3582`) caps the curl+render wave; the render wave gets only the leftover, so Firecrawl (`FIRECRAWL_TIMEOUT=30`, `firecrawl_service.py:14`) can't finish a luxury SPA even off-clock. This is why render-walled retailers (Sephora BH, bolo.bh, boutiqaat) never land.

**Cost model:** cached compare ≈ $0.005 (verdict only); cold ≈ $0.015–0.025. Warmer pays off per re-compare.

---

## 1. Locked Design Decisions (defaults — change only with dispatcher sign-off)

- **D1 — Fail-fast = best-available, never a crash.** The hard cap (`STREAM_HARD_CAP_SECONDS`) must STOP raising `TimeoutError`→error for a valid query. On the soft deadline, return `success:true` with the **best-available** assembled result: whatever specs/reviews are ready + the best price found so far (genuine if landed, else honest `converted_usd`, else last-resort `estimated`), and a templated verdict if the GPT verdict didn't finish. Only return `success:false` when BOTH products have NO usable data at all (existing `INSUFFICIENT_DATA` path).
- **D2 — Error contract (BE↔FE coordination point).** When a true hard failure occurs, preserve the specific `code` end-to-end (do NOT collapse to 400). New mapping: `TIMEOUT` → HTTP **503** (transient, retryable) with body `{success:false, error:<friendly>, code:"TIMEOUT", request_id}`. Copy must obey the no-scary-copy contract: NO "couldn't", "try again", "failed". Approved EN: e.g. *"Still gathering prices — give it another tap in a moment."* Arabic mirror (no `تعذر`/`فشل`).
- **D3 — Converted price labeling.** Never the word "estimated"/"تقدير" in UI. Use "indicative"/"reference" microcopy on the price pill only (per `feedback_no_estimated_word_in_ui`). Backend `source_method` enum stays as-is.
- **D4 — Variant/concentration precision.** Prefer the candidate whose concentration (EDP/EDT/Parfum) + size (ml) best matches the query; when the query is unspecified, pick a **consistent** basis across the two compared products (don't compare a 30ml to a 100ml). Annotate the chosen size in the price object so the FE can show it. Out of scope: forcing a specific retailer.
- **D5 — Render budget.** Replace hard-coded `_FAN_OUT_BUDGET = 12.0` with `float(os.getenv("FAN_OUT_BUDGET_SECONDS", "12.0"))`. **Live stays 12s** (the 15s clock is sacred). **Warmer sets `FAN_OUT_BUDGET_SECONDS=35`** so Firecrawl/Scrape.do finish luxury SPAs off-clock.
- **D6 — Warmer is the genuine-share engine.** Extend the gold catalog with the structural pairs (luxury fragrance, haircare, gadgets — incl. this Tom Ford pair). Activation = Railway cron + flag `ENABLE_PRICE_CACHE_WARMER=true` (Ahmed). Serper budget: free key is finite (~2,500, shared with live) → the plan sizes a sustainable cadence; **continuous full-catalog warming needs PAID Serper** (flagged as an Ahmed decision, not a code blocker).
- **D7 — EAS push** of the committed usage-counter fix (`1e5a788`) is folded into the frontend lane (prep), but the interactive `eas update` is run by Ahmed.
- **D8 — Discovery BH-locale filter.** Filter the render-wave candidate URLs to BH-locale/product PDPs (drop `noon.com/egypt`, `/saudi`, category/listing pages) so the render wave (when it fires, mostly in the warmer) renders the RIGHT page.

---

## 2. Team Structure, Ownership & Operating Rules

**Lanes (assign one Opus agent each; backend may split into be-core + be-sourcing for 5 agents):**
- `be-core` — WS1 (fail-fast + surfacing), WS2 (latency trim). **Critical path.**
- `be-sourcing` — WS3 (render budget + Firecrawl/Scrape.do + discovery filter), WS4 (warmer catalog), WS5 (variant precision).
- `fe` — WS6 (graceful error/timeout UI + converted labeling), WS7 (EAS push prep).
- `test` — red-green tests to **80%** for every WS; harness upkeep.
- `qa` — cross-QA every lane's work; reproduce→verify; regression + eval gate.

**Operating rules (Ahmed's + CLAUDE.md, BOTH apply):**
1. **Opus only.** No Sonnet/Haiku.
2. **100% complete** before disassembly. No "mostly done."
3. **Cross-QA mandatory:** before the team disassembles, each member QAs ANOTHER member's work. Subpar/missed work is **sent back**, not waved through.
4. **Idle = useful:** an idle member either writes red-green tests (toward 80%) for the new feature, or waits for their QA result. Never idle-idle.
5. **Delegate** — work is split across lanes, not done solo.
6. **ACK every dispatcher ruling** before proceeding; check inbox between tasks (CLAUDE.md team discipline).
7. **Verify "complete" against the commit** (`git show`), never the report.
8. **Path-restricted commits:** `git commit -m "msg" -- <paths>` (the `--` is a path separator).
9. **Escalate stalls** after 30 min OR 3 silent nudges → dispatcher takeover.
10. **Budget discipline:** Serper finite (~2,490 on key `696e4e57…`, shared w/ live); Firecrawl **450 lifetime**. Test cache-disabled (`UPSTASH_REDIS_URL=""` after `load_dotenv`) via `.qa-bias-rerun/_firecrawl_scrapedo_test.py` — never burn broadly. Eval = `--concurrency 1`, full-200 needs dispatcher GO.

---

## 3. Workstreams

### WS1 — Fail-fast + correct surfacing (be-core) <!-- OWNED BY: be-core -->

**Problem:** hard-cap raises `TimeoutError` → `{success:false, code:TIMEOUT}` → route collapses to HTTP 400 `BAD_REQUEST` → FE "couldn't load." A valid query should NEVER hard-crash.

**Files:**
- Modify: `app/services/structured_comparison_service.py:1493-1520` (non-streaming hard-cap wrapper) + the streaming hard-cap (`~2046-2052`).
- Modify: `app/api/text_routes.py:296-314` (non-success collapse to 400) + the SSE handler (`~455-462`).
- Modify: `app/middleware/error_handler.py:23` (code map; add 503→`TIMEOUT` or preserve passed code).
- Test: `tests/test_compare_timeout_graceful.py` (new), `tests/test_text_routes_error_mapping.py` (new/extend).

**Approach:**
1. Make `_compare_from_text_impl` assemble a **best-available partial** as it goes (stash latest specs/price/reviews per product on `self`), so on cancellation the wrapper can return what's ready instead of nothing. Add a `_build_partial_response()` that mirrors `response_builder.build_comparison_response()` with whatever is present + honest labels + a templated verdict fallback.
2. In the hard-cap wrapper: on `asyncio.TimeoutError`, if at least one product has usable data → return `_build_partial_response()` with `success:true` + `metadata.partial=true`; else return the existing `INSUFFICIENT_DATA` body. STOP returning the bare `code:TIMEOUT` error for the has-data case.
3. Route (`text_routes.py:296-314`): generalize the `CONTENT_UNAVAILABLE` passthrough — preserve the structured body + map `TIMEOUT`→503 (per D2), other codes per their semantics; only genuinely-bad requests stay 400.
4. Friendly copy per D2 (EN + AR i18n keys).

**Acceptance:** the Tom Ford repro returns `success:true` with two prices (genuine if warmed, else converted) OR, if it must fail, a 503 `TIMEOUT` (not 400) with compliant copy. No forbidden vocab anywhere in the response.

**Required tests (red-green, ≥80%):**
- `test_hardcap_returns_partial_when_one_product_has_data` (mock impl to exceed cap with partial state → assert `success:true`, `metadata.partial`).
- `test_hardcap_insufficient_data_when_no_product_data` (→ `INSUFFICIENT_DATA`).
- `test_route_preserves_timeout_code_as_503` (service returns `code:TIMEOUT` → route → 503, body code `TIMEOUT`).
- `test_error_copy_has_no_forbidden_vocab` (grep the response strings).

### WS2 — Live price-path latency trim (be-core) <!-- OWNED BY: be-core -->

**Problem:** `price_ms` ~17–20s/product dominates the 37.5s total. The genuine winner confirms at 3.5s, but the stage keeps spending (gl=us fallback, multi-candidate discovery+scrape) before settling.

**Files:**
- Modify: `app/services/structured_comparison_service.py` `_get_price` (the `_FAN_OUT_BUDGET` block `~3582-3656`, the discovery/escalation `~3070-3520`), `_PRICE_RACE_TIMEOUT` (`:609`, `:2512`).
- Test: `tests/test_price_latency_budget.py` (new).

**Approach (TASK 0 = trace first):** Re-run `_frag_pipeline_trace.py` with extra timing logs inside `_get_price` to attribute the ~20s (unified_search vs gl=bh+gl=us shopping vs discovery vs each candidate scrape). Then trim the proven waste, e.g.:
- Short-circuit the `gl=us` Serper-shopping fallback when a genuine BH curl candidate has already landed (don't spend on a converted fallback you won't use).
- Cap discovery candidate count + stop scraping further candidates once a rank-≥85 genuine confirms (the early-exit exists; verify it isn't being bypassed by the two-wave loop).
- Confirm the two products' Phase-1 run concurrently (not serialized).

**Acceptance:** cold Tom Ford pair `total_ms` drops below 30000 (fits the live cap) with both prices still genuine, OR the price stage yields a genuine/converted price ≤ ~12s/product. Measure via `_frag_pipeline_trace.py` (compare before/after `stage_timings_ms`).

**Required tests:** unit tests on the early-exit/short-circuit predicates (no live calls); a timing assertion is QA-measured, not unit.

### WS3 — Render budget env-config + Firecrawl/Scrape.do + discovery filter (be-sourcing) <!-- OWNED BY: be-sourcing -->

**Problem (Ahmed: "don't forget Firecrawl/Scrape.do"):** the render wave is hard-capped at 12s so Firecrawl/Scrape.do never finish luxury SPAs, even off-clock; discovery sometimes feeds wrong-region pages.

**Files:**
- Modify: `app/services/structured_comparison_service.py:3582` (`_FAN_OUT_BUDGET` → env per D5).
- Modify: discovery candidate filtering in `_get_price` / `app/services/source_router.py` (BH-locale filter per D8; the `_BH_LOCALE_MARKERS` at `source_router.py:425` + `bahrain_locale_rewrite` already exist — extend the drop-list for wrong-region/category URLs).
- Review: `app/services/firecrawl_service.py` (`FIRECRAWL_TIMEOUT=30`) + `app/services/scrapedo_service.py` — confirm they honor the larger budget; no change unless the trace shows a bug.
- Test: `tests/test_fan_out_budget_env.py` (new), `tests/test_discovery_bh_locale_filter.py` (new).

**Approach:**
1. `_FAN_OUT_BUDGET = float(os.getenv("FAN_OUT_BUDGET_SECONDS", "12.0"))`. Live unchanged (12s); warmer passes 35s.
2. BH-locale discovery filter: drop `noon.com/egypt|/saudi|/ksa`, `/cairo`, category/search/listing URLs (no `/product`/PDP signal); KEEP `/en-bh/`, `.bh`, `bahrain.*`, Shopify product URLs.
3. **Firecrawl/Scrape.do capability test (the explicit ask):** with `FAN_OUT_BUDGET_SECONDS=35`, run `.qa-bias-rerun/_firecrawl_scrapedo_test.py` (cache-disabled) on the render-walled BH retailers (Sephora BH, bolo.bh, boutiqaat) for a luxury fragrance + a haircare item; record whether they render+extract a genuine BHD price. If they DO → those sources become warmer-only genuine. If a scraper has a real defect (timeout/selector), fix it here. Budget: Firecrawl 450 lifetime — a handful of targeted URLs only.

**Acceptance:** `FAN_OUT_BUDGET_SECONDS` honored (test); discovery filter drops wrong-region/category URLs (test); a written finding on Firecrawl/Scrape.do for the 3 render-walled retailers (genuine-extract: yes/no + evidence).

### WS4 — Warmer catalog + activation (be-sourcing) <!-- OWNED BY: be-sourcing -->

**Problem:** the warmer (`scripts/cron_warm_price_cache.py`) is built + deployed dormant; it must cover the structural categories and run on a cadence.

**Files:**
- Modify: the warmer gold catalog (the `WARMER_SUBSET` source — confirm where the catalog lives; extend with luxury fragrance/haircare/gadget pairs incl. Tom Ford Ombré Leather + Tobacco Vanille).
- Modify: warmer to export `FAN_OUT_BUDGET_SECONDS=35` (+ existing `PRICE_RACE_TIMEOUT=60`) for its run.
- Test: extend `tests/test_cron_warm_price_cache.py` (catalog coverage + budget env).
- Ops doc: `docs/runbooks/qaren-warmer-activation.md` (cron registration + Serper sizing).

**Approach:** add the structural pairs; verify warm → `set_cached` → a cache-read probe (`.qa-bias-rerun/_genuine_share_probe.py`) shows genuine for the warmed pair; document the Railway cron registration (`python -m scripts.cron_warm_price_cache`, e.g. `0 */12 * * *`) + `MAX_QUERIES_PER_RUN` sizing against the free Serper budget; flag the paid-Serper decision for continuous full warming.

**Acceptance:** after a warm run, the Tom Ford pair serves genuine BHD from cache on a normal (15s-clock) request, fast, no timeout. Warmer unit tests green (≥80%).

### WS5 — Variant/concentration precision (be-sourcing) <!-- OWNED BY: be-sourcing -->

**Problem:** the trace chose Ounass 118 BHD for Tobacco Vanille vs the Sephora 72 BHD (30ml) the user saw — likely a size mismatch; the two compared products should use a consistent basis.

**Files:**
- Modify: `app/services/price_service.py` — `variant_mismatch` (`:579`) + the candidate scoring in `_match_shopify_product` (`:1530`) / `extract_price_from_shopping`; add concentration/size extraction + a consistency preference (D4).
- Test: `tests/test_variant_precision.py` (new).

**Approach (TASK 0 = trace):** confirm the chosen sizes for the trace pair, then add: parse EDP/EDT/Parfum + `\d+ml`; prefer the candidate matching the query's stated size/concentration; when unspecified, prefer a basis consistent across both products (e.g. both 100ml). Annotate `price.size`/`price.concentration`.

**Acceptance:** for a query that specifies a size, the matched price is that size; for an unspecified pair, both products report the same size basis where available. Unit tests on the parse + preference (no live calls).

### WS6 — Graceful error/timeout UI + converted labeling (fe) <!-- OWNED BY: fe -->

**Files:**
- Modify: `SmartCompareApp/src/screens/ResultsScreen.tsx`, `src/components/ResultsLoadingView.tsx`, `src/services/api.ts` (`parseApiError`, `streamComparison` fallback), price-pill component, `src/i18n/` (EN+AR keys).
- Test: `SmartCompareApp/__tests__/ResultsScreen.timeout.test.tsx` (new).

**Approach:** handle the new `TIMEOUT`/503 + `metadata.partial=true` gracefully (render the partial result; if truly empty, a soft non-scary state with a tap-to-retry — no "couldn't load"). Converted price pill shows "indicative/reference" microcopy (D3), never "estimated". Verify against the copy-policy (`src/i18n/.copy-policy.json`).

**Acceptance:** Jest renders the partial + timeout states; no forbidden vocab (EN/AR); `npx tsc --noEmit` clean.

### WS7 — EAS push of usage-counter fix (fe) <!-- OWNED BY: fe -->

**Files:** none (mechanical). `SmartCompareApp/` — `npm install` (box node_modules incomplete) → `npx tsc --noEmit` → `eas update --branch preview` (Ahmed runs the interactive `eas update`).

**Acceptance:** `1e5a788` reaches the preview channel; two-launch propagation noted. (Verified by Ahmed on device.)

### WS-TEST / WS-QA (test + qa lanes) <!-- OWNED BY: test --> <!-- OWNED BY: qa -->

- **test:** drive red-green to **≥80%** per WS; keep `.qa-bias-rerun/` harness current; add the timeout/partial integration tests; do NOT run network "free" tests in unit batches.
- **qa:** reproduce the Tom Ford crash → verify fixed (warmed = genuine fast; cold = graceful, never 400); cross-QA each lane vs its `git show`; run the free unit suite + the eval `smoke20 --concurrency 1 --baseline-run-id 4aee8e88…` (regression, no drop); confirm no forbidden vocab; sign off the Firecrawl/Scrape.do finding.

---

## 4. Sequencing & Dependencies

1. **First, together:** lock the **D2 error contract** (be-core publishes the exact `code`/`metadata.partial`/HTTP shape) so `fe` builds against it in parallel.
2. **Parallel:** WS1+WS2 (be-core) ‖ WS3+WS4+WS5 (be-sourcing) ‖ WS6 (fe, against the contract) ‖ test scaffolding.
3. **Converge:** WS4 warm → QA cache-read genuine; WS1 partial → QA repro graceful.
4. **Gate:** cross-QA all lanes → free unit suite green → eval smoke20 no-regression → dispatcher verifies each "complete" via `git show`.
5. **Ship:** backend merge `--no-ff` → Railway auto-deploy (~90s) → prod smoke (the Tom Ford curl: expect `success:true` genuine, or graceful 503) → Ahmed registers warmer cron + flips `ENABLE_PRICE_CACHE_WARMER` → Ahmed runs `eas update` (WS7).

## 5. Definition of Done

- Tom Ford pair: warmed → genuine BHD, fast, no timeout; cold → graceful best-available (never a 400/scary copy).
- `FAN_OUT_BUDGET_SECONDS` env wired; warmer uses 35s; Firecrawl/Scrape.do finding documented for the 3 render-walled retailers.
- Warmer catalog covers the structural pairs; activation runbook written.
- All new code ≥80% red-green; full free unit suite green (no regressions); eval smoke20 no drop vs baseline.
- Cross-QA done; every "complete" verified against the commit. No forbidden vocab (EN/AR). `npx tsc --noEmit` clean.

## 6. Budget & Ops Guardrails

- Serper finite (~2,490, shared with live) — measurement runs `--concurrency 1`; full-200 needs dispatcher GO. Firecrawl 450 lifetime — targeted URLs only.
- Prod-cache/Redis writes are classifier-blocked for the dispatcher — warmer runs on Railway; local warms via Ahmed `!` or a Bash rule.
- Railway: CLI works (`kinghaleem999@`, project `empowering-enthusiasm`/`web`/`production`); deploy commit at `environments.edges[].node.serviceInstances.edges[].node.latestDeployment.meta.commitHash`.

## 7. Repro / Verify Harness (in `.qa-bias-rerun/`, cache-disabled, no prod write)

- `_frag_pipeline_trace.py` — full pipeline + `stage_timings_ms` (the latency oracle).
- `_firecrawl_scrapedo_test.py` — render-scraper capability (set `FAN_OUT_BUDGET_SECONDS=35`).
- `_serper_shopping_probe.py` / `_serper_search_probe.py` — Serper surface probes.
- `_bh_source_probe.py` — registry Shopify `/products.json` (curl_cffi).
- `_genuine_share_probe.py` — prod cache-read genuine-share + cost.
