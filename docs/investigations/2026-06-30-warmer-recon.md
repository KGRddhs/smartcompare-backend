# Wave 1 recon — price-cache warmer + cache-key parity + usable_exact_genuine KPI

**Date:** 2026-07-01 · **Branch:** `feature/genuine-price-warmer` (off `origin/main` cdaf5c5)
**Method:** 5-agent parallel recon workflow (`wf_4de01065-497`) + dispatcher first-hand reads of the crux functions.

This note is the deliverable of Wave-1 Task 1. It reshapes the plan: several legs are **already built**, and the "cache-key parity silent killer" is **not** where the design doc assumed.

---

## 0. Executive reframing (read this first)

| Design-doc assumption | Recon reality |
|---|---|
| "Warmed key ≠ live key" is a builder bug | **False at the builder.** Warmer calls `compare_from_text(query, nocache=True)` → the SAME `_get_price` → `build_size_aware_price_cache_key(...)` a live user hits. The builder already alias-normalizes EDT≡"eau de toilette", oz≡ml, TB≡GB. |
| Parity is the silent killer for the gate | For the **gate**, warmer + KPI read the SAME truth-set query strings → parity is **trivially guaranteed**. The free-form divergence (verbose warmed title vs terse live query) is real but **on-device only**, and unmeasured by the gate. |
| Titleless display/cache inconsistency is the folded item | The bigger bug is **the DB (L2 `product_prices`) never persists `title`** → a warmed price rehydrated from Postgres is titleless → fails the KPI + `should_cache_price`. |
| KPI + per-category gate need building (Task 3) | **Already built.** `run_usable_exact_genuine_kpi` returns `per_category`, and `main()` enforces `≥0.85`/category (eval_runner.py:1433-1441). |
| 30-50/category truth set exists to extend | Only **18 products / 3 categories** (electronics/fashion/fragrances × 6) exist today. |

**Net:** Wave 1's real work = (a) baseline-uuid validation; (b) **persist+rehydrate the DB title** (durability); (c) a warmer Serper-budget guard; (d) truth-set expansion; (e) a cache-key parity TEST that pins what's already safe + documents the parser residual; (f) surface the per-category gate verdict. The prod-warm + flag-flip remain the gated terminal actions.

---

## 1. Warmer cron — `scripts/cron_warm_price_cache.py`

- **Query source (3 files, no DB):** `WARMER_SUBSET` (default `smoke20`, `full`→whole set) → `load_gold_truth()` reads `data/validation_gold_truth.json` + `select_queries()` filters via `data/eval_smoke_subset.json`; then `_merge_catalog()` folds in `data/warmer_catalog.json` (`warm-*` ids, every run); then `_rotation_window()` slices `MAX_QUERIES_PER_RUN` (default 25) from a Redis cursor `warmer:cursor`. (cron:203-221)
- **Write path:** `_warm_one` → `svc.compare_from_text(record["query"], region=…, nocache=True)` (cron:172-174). **`nocache=True` bypasses the READ, not the WRITE.** Inside `_get_price`, writes fire when `should_cache_price(...)` passes: `set_cached(cache_key, best, price_cache_ttl(best))` (Redis) + `self._save_price_to_db(...)` → `product_prices` insert. (scs:4764-4766, 5934-5937)
- **Off-clock budget overrides (import-time, warmer-only):** `PRICE_RACE_TIMEOUT`=`WARMER_PRICE_RACE_TIMEOUT`(60); `STREAM_HARD_CAP_SECONDS`=`WARMER_STREAM_HARD_CAP`(150); `FAN_OUT_BUDGET_SECONDS`=`WARMER_FAN_OUT_BUDGET`(35); Firecrawl/Scrape.do timeouts raised. (cron:49-58) → the slow genuine curl/render actually finishes off-clock.
- **GAPS:** (1) **No Serper-budget guard** — only the `MAX_QUERIES_PER_RUN` count cap; relies on the generic per-request `api_budget_service`. (2) **No fresh-purge / clean-cache assertion** — `main()` goes flag→load→merge→window→warm loop, overwriting whatever is there.
- **Gate:** fail-closed `ENABLE_PRICE_CACHE_WARMER` only.

## 2. Cache-key parity — `price_service.py` + `structured_comparison_service.py`

- **Single derivation:** `_get_price` builds `cache_key = build_size_aware_price_cache_key(brand, name, variant, region, search_query)` (scs:4155), where `search_query = product_info.get("search_query", f"{brand} {name} {variant}")` (scs:3469) — the **parser's** output, identical function for warmer-write and live-read. Physical key = `md5("|".join(...))[:12]` → `price:<12hex>`.
- **`_identity_cache_token(text)`** (ps:5009) composes 3 axes with `.`: concentration (`extract_concentration`→lowercased, EDP/EDT/…), electronics/variant qualifiers (`_quals_in`→sorted-joined, FE/Pro/Max), size/storage/count/weight (`size_variant_token`→`256gb`/`100ml`). `_strip_identity_axes` removes these from `name`/`variant` so the same axis in `name` vs `search_query` collapses to one base.
- **Alias normalization — ALREADY SAFE:** `extract_concentration` maps `eau de toilette` and `edt` → the single label `EDT` (ps:2773-2789); `size_variant_token`/`extract_size_ml_any` snap `oz`→`ml` (3.4oz→100ml), `TB`→`GB`, `L`→`ml`.
- **The real residual (UPSTREAM, parser):** a size/qualifier axis PRESENT in the verbose warmed title but ABSENT from a short live query → different token → different key:
  - Warm `"Dior Sauvage Eau de Toilette 100ml"` → token `edt.100ml`; live `"Dior Sauvage EDT"` → token `edt` → **DIFFERENT key.** The alias collapses; the **size presence/absence does not.**
  - `"Samsung Galaxy S24 256GB"` vs `"Galaxy S24 256GB"`: token `256gb` both; base collapses IFF the parser fills `brand="Samsung"` for both (it normally does).
- **Consequence for the gate:** the warmer and the KPI both read the SAME truth-set strings → identical parser output → identical key → parity is **guaranteed for the gate measurement**. Fully fixing the free-form on-device case requires deriving the key from the RESOLVED-MATCH identity (matched PDP brand/name/concentration/size) fed back on both sides — a larger change that risks flag-OFF byte-identity. **Decision: pin the already-safe alias parity with a test; document the parser residual; do NOT re-architect keying in Wave 1.**

## 3. usable_exact_genuine KPI — `scripts/eval_runner.py`

- **`usable_exact_genuine_for_product`** (eval:484-583): (a) non-pending positive amount; (b) `source_method ∈ GENUINE_BH_SOURCE_METHODS` (eval:400-423, mirrors ps `_GENUINE_BH_SOURCE_METHODS`, parity-pinned); (c) `in_stock is True` (unknown≠usable); (d) present non-listing PDP url; (e) exact identity vs the truth entry via `_selection_match` + fail-closed structured axes (`storage_gb`/`size_ml`/`concentration`/`colorway`). **A titleless price → `title==""` → returns False** (eval:538-540).
- **`run_usable_exact_genuine_kpi`** (eval:1213-1275): loads `data/usable_exact_genuine_truth.json`, GETs `/api/v1/text/price-kpi?q=&region=&nocache=` per truth entry (`nocache=false` for `--read-cache` WARMED, else COLD), maps body[0]+truth through the checker, aggregates **per-category** `{usable, requested, share}` + overall. PROD-HTTP (post-deploy). `_KPI_HTTP_TIMEOUT=90`.
- **Per-category gate — ALREADY WIRED:** `main()` (eval:1424-1441) prints the KPI JSON, computes `failing = {c: share for share < 0.85}`, exits 1 + "warmer activation stays PAUSED" if any category is below. So Task 3's mechanism exists.
- **Baseline uuid bug:** `--baseline-run-id` → `eval_gate._regression_gate` → `fetch_eval_run` → `.eq("id", run_id)` on a `uuid PK` (eval_persistence:91-110). A truncated `54b603e8` triggers Postgres `22P02 invalid input syntax for type uuid`, but the `try/except` **swallows it → returns None → "baseline not found"** (indistinguishable from a genuinely missing row). Full uuid `54b603e8-4eab-41c9-a34d-a5e391446559` casts cleanly. **Fix: validate the id is a full uuid before the query and raise a clear error.**
- **Truth set:** `data/usable_exact_genuine_truth.json` — 18 products, 3 categories (electronics/fragrances/fashion × 6), deliberately disjoint from `warmer_catalog.json` (pinned by `tests/test_kpi_set_disjoint_from_warmer.py`).

## 4. `/price-kpi` endpoint — `app/api/text_routes.py:636-692`

- Params `q, region, nocache(default True)`. Runs the real `parse_product_query` → resolves `category = p0.category or _infer_category_from_query(q) or "other"` (text:667) → threads it into `_get_price(brand, name, variant, region, search_query, nocache, category)` (text:671) → `set_resolved_price_category(category)` ContextVar (scs:4144). Non-showable (`is_price_showable(enforce_correctness=True)` fails) → `make_pending_price` (text:678-682); returns `overview.products[0].price` via `public_price_view`.
- **`public_price_view`** (ps:4990-5006) drops ONLY `guard_rejected` + `_`-prefixed keys; **keeps `title`, `source_method`**. A null title in the KPI response ⇒ either a PEND (`make_pending_price` has no title) or a genuinely titleless resolved listing.
- **`nocache=true` against prod STILL WRITES** to the shared Upstash + `product_prices` whenever `should_cache_price` passes → local KPI runs pollute prod cache (the documented gotcha).

## 5. Titleless + showable + cache discipline — `price_service.py`

- **`is_price_showable(…, enforce_correctness=False)`** (ps:1204): base checks (dict, positive amount, `source_method ∈ _showable_source_methods()` = genuine ∪ converted_usd, implausibility guards). Correctness backstop is opt-in + flag-gated (`if enforce_correctness and exact_gate_enabled()`, ps:1266). **Titleless-with-url is SHOWN**: pends only when identity AND url both missing (ps:1290); the axis backstop at ps:1312-1317 is `if identity and (...)` → skipped when titleless. This title-OR-url leniency is DELIBERATE (documented over-rejection avoidance for descriptive converted/page-scrape/iHerb titles).
- **`should_cache_price`** (ps:4940) hard-requires `title` (ps:4959-4961) + valid PDP url + `in_stock is not False` + `_selection_match`. → **titleless is SHOWN but NOT cached.**
- **`_backstop_identity_ok`** (ps:4776): axis-only (`_axis_mismatch(strict_extras=False)`), brand-independent. Callers: display chokepoint (ps:1312) + cache-READ revalidation (`_cache_price_identity_ok`, scs:728/741). No-op when flag OFF or title-less.
- **Flag guard** `exact_gate_enabled()` (ps:3028, default ON) present on every surface → flag-OFF byte-identical to b207bfa.

**Reconciliation decision:** do NOT tighten display to pend titleless (that re-introduces the documented over-rejection). Instead **persist + rehydrate the DB `title`** so warmed prices are durably KPI-usable and cacheable — making the warmer's cache side (which already requires title) consistent with what it serves.

---

## 6. Revised Wave-1 task list (supersedes the plan's Tasks 2-7 detail)

1. **Baseline-uuid validation** (eval_runner/eval_gate) — clear error on a non-full-uuid `--baseline-run-id`; correct the CLAUDE.md gate command to the full uuid. *[safe, TDD]*
2. **DB title persistence + rehydration** (`product_data_service.save_price`/`get_cached_price`, migration for a `title` column) — the durability fix; gated so flag-OFF byte-identical + safe on a missing column. *[safe, TDD, needs a migration]*
3. **Warmer Serper-budget guard** (`cron_warm_price_cache.py`) — a pre-run + per-query budget circuit using `api_budget_service`; estimate + cap the spend. *[safe, TDD]*
4. **Cache-key parity test** (`tests/test_price_cache_key_parity.py`) — pin EDT≡"eau de toilette"/oz≡ml same-size → same key; distinct variants differ; DOCUMENT the parser axis-presence residual as xfail/comment. *[safe, TDD]*
5. **Per-category gate verdict surfacing** — emit a structured `{gate_pass, failing}` in the KPI JSON (mechanism already in `main()`); optionally a `--kpi-gate` exit contract test. *[safe, TDD]*
6. **Truth-set expansion** — grow existing categories for statistical power + seed new categories with verified BH-available SKUs (research-gated; only add products with a plausible genuine BH source). *[data, research-gated]*
7. **Fresh-purge precondition helper** — a clean-cache assertion the warmer/measurement can call; for LOCAL runs, an isolated-cache path OR a documented purge-after. *[safe, TDD]*

**GATED terminal actions (need explicit user GO + a healthy paid Serper key):**
- **Task 6/warm real sample + measure KPI** — writes to the SHARED prod cache + burns paid Serper. Requires isolated-cache OR accept+purge-after.
- **Task 7/flip `ENABLE_PRICE_CACHE_WARMER`** — prod activation, iff per-category KPI ≥85% ∧ parity proven ∧ clean cache ∧ sweep+comm green.

---

## 7. Adversarial coverage sweep — findings + dispositions (`wf_b806ccdd-467`)

5 parallel adversaries, each reproducing through the runtime. Dispatcher-gated:

| Finding | Sev | Disposition |
|---|---|---|
| Budget guard used the free-tier-calibrated lifetime counter (`get_remaining`/`has_budget('serper')`, ceiling 2200) → would PERMANENTLY disable the warmer on a healthy paid key past 2200 lifetime burn | MED (confirmed) | **FIXED** — replaced with a tier-independent per-run credit cap (`WARMER_MAX_SERPER_CREDITS_PER_RUN`, 900); dropped the lifetime dependency + `_serper_exhausted` |
| `urn:uuid:`/braced baseline-id forms pass `uuid.UUID()` but 22P02 → phantom "not found" | LOW (confirmed) | **FIXED** — validate the canonical hyphenated form |
| `kpi_gate_verdict` + main() KPI refactor | — | **No findings** (correct; the only divergence vs the old inline check is empty→PAUSED, the intended fix) |
| L2 title persistence (flag-gated) | — | **No findings** (flag-OFF byte-identical; flag-ON-but-column-absent swallowed on both save + read; list-title coerced at display) |
| **`extract_weight_or_volume('5G')` → (5.0,'g')**: cellular "5G/4G/3G" mis-parsed as gram-weight → the same phone's base query and its "5G" PDP title hash to DIFFERENT cache keys (false-SPLIT → warmer cache MISS across electronics) | HIGH (confirmed) | **DEFERRED** — see below |

### Deferred: the 5G/4G/5G weight-token false-split (HIGH, pre-existing)

`extract_weight_or_volume` (ps:2928) matches bare `<digit>G` as grams, so `size_variant_token('Galaxy S24 FE 5G')` → `fe.5g` vs `fe` for the base model → different cache keys → a guaranteed warm-vs-live MISS for any electronics whose genuine PDP title carries "5G". **It is PRE-EXISTING in main `cdaf5c5` (not a Wave-1 regression)** and NOT trivially fixable, because the same extractor feeds the **correctness matcher's weight axis** (ps:1827/1839/1851 — PR #9 territory) AND the disambiguation is **category-dependent**: "5G" is cellular for a phone but "5 grams" for a supplement ("Creatine 5G"). A category-blind strip would FALSE-MERGE supplement weights ("Creatine 5G" ≡ "Creatine 10G" → wrong-SKU cache serve — strictly worse). The correct fix is **category-aware** (exclude cellular `[2-5]G` from weight ONLY for electronics/gadget context, preserving supplement gram parsing) and must be verified by the correctness COVERAGE sweep — so it belongs in a dedicated correctness session, not the warmer-gate wave. Impact until fixed: warmer coverage degradation (a miss → live pending/converted), NOT a wrong price. Tracked for the next correctness-sweep session.
