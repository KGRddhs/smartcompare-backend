# Genuine-price warmer + variant metadata — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: use `superpowers:executing-plans` to implement this plan task-by-task. This is an **ultracode TEAM** plan — each wave runs `recon → TDD implement (sequential writers, path-restricted commits) → adversarial COVERAGE-DRIVEN sweep (Workflow tool) → dispatcher gates every finding → comm gate`. **Wave 1's gate must pass before Wave 2 starts.**

**Goal:** Make genuine BHD prices actually SHOW on cold/cache-served compares by safely auto-activating the price-cache warmer behind a trustworthy correctness gate (Wave 1), then close the ~9 token-indistinguishable residual leaks with a structured `VariantDescriptor` (Wave 2).

**Architecture:** Wave 1 is "build a gate trustworthy enough to hand it the prod-cache-write decision" — three legs (warmed per-category KPI, cache-key parity, fresh-purge) that, all green, AUTO-flip `ENABLE_PRICE_CACHE_WARMER`. Wave 2 replaces token-set residual checks with structured field comparison sourced from the existing axis extractors + a narrow LLM hint.

**Tech Stack:** FastAPI/Python 3.12, Upstash Redis + Supabase (`product_prices`), Railway (prod env + `railway variables`), the `Workflow` tool for sweeps. Shipped baseline: main `cdaf5c5`, `ENABLE_EXACT_PRICE_GATE` ON, flag-OFF byte-identical.

**Design:** `docs/plans/2026-06-30-genuine-price-warmer-and-variant-metadata-design.md`.

**Setup (before Task 1):** `git fetch && git worktree add -b feature/genuine-price-warmer ../smartcompare-warmer origin/main` and copy `.env` into the worktree (worktrees don't inherit the gitignored `.env`; sibling `load_dotenv` walks UP and never reaches it).

---

# WAVE 1 — warmer + measurement (GATE-FIRST)

### Task 1: Recon (read-only; produce a findings note, no code)

**Files to read + questions to answer (write answers into `docs/investigations/2026-06-30-warmer-recon.md`):**
- `scripts/cron_warm_price_cache.py` — how does it pick queries (`WARMER_SUBSET`), how many (`MAX_QUERIES_PER_RUN`), the `PRICE_RACE_TIMEOUT`, and does it write via `_get_price`? Does it carry the resolved TITLE onto the cached price?
- `app/services/price_service.py` — `build_size_aware_price_cache_key`, `_identity_cache_token` (~5009), and the live READ path in `scs._get_price`: **what string is the cache key derived from on the WRITE (warmer) vs the READ (live compare)?** This is the parity question — answer it exactly with two concrete example queries (e.g. "Dior Sauvage Eau de Toilette 100ml" warm vs "Dior Sauvage EDT" live).
- `scripts/eval_runner.py` — `run_usable_exact_genuine_kpi` (~1205) + `usable_exact_genuine_for_product` (~510): confirm it reads `price.title`, hits `/price-kpi`, and how `--read-cache` (warmed) vs cold flows.
- `app/api/text_routes.py` — the `/price-kpi` handler: confirm it threads category + returns the title (it does NOT strip it — `public_price_view` only drops `guard_rejected` + `_`-keys; a `null` title means the resolved price had none).
- Current cache cleanliness: is there a clean-cache assertion anywhere?

**Step — Commit the recon note:** `git add docs/investigations/2026-06-30-warmer-recon.md && git commit -m "recon(warmer): cache-key parity + KPI + warmer findings"`

---

### Task 2: KPI baseline-anchor fix + a per-category truth set

**Files:** Modify `scripts/eval_runner.py` (the `--baseline-run-id` handling) + wherever the KPI truth set lives (recon Task 1 locates it). Test: `tests/test_eval_kpi_baseline.py` (create).

- **Step 1 (failing test):** assert the KPI run-mode accepts the FULL uuid `54b603e8-4eab-41c9-a34d-a5e391446559` and that a truncated `54b603e8` raises a clear error (not a silent `uuid ~~` 400). Also assert a 30–50-product/category truth set exists with the pinned axes (storage/size/concentration/etc.).
- **Step 2:** run it, expect FAIL.
- **Step 3:** implement — validate the baseline id is a full uuid; build/extend the truth set per category (electronics, fragrances, supplements, skincare, haircare, makeup, grocery, fashion). Truth entries: `{query, region, category, expected:{brand, storage_gb|size_ml|concentration|...}}`.
- **Step 4:** run, expect PASS.
- **Step 5:** commit (`-- scripts/eval_runner.py tests/test_eval_kpi_baseline.py <truth-file>`).

---

### Task 3 (GATE LEG 1): warmed per-category `usable_exact_genuine` KPI

**Files:** Modify `scripts/eval_runner.py`. Test: `tests/test_eval_kpi_per_category.py`.

- **Step 1 (failing test):** the KPI run-mode (`--kpi usable_exact_genuine --read-cache`) reports a **per-category** pass-rate dict and a gate verdict (`>=0.85` per category). A titleless or non-exact resolved product counts NOT-usable (already true via `usable_exact_genuine_for_product`). Pin: a product with a correct exact title + native BHD + in-stock + valid PDP counts usable; a sibling/converted/titleless does not.
- **Step 2-4:** run-fail → implement the per-category aggregation + the gate boolean → run-pass.
- **Step 5:** commit.

*Note:* the KPI is measured WARMED, so it can only be meaningful AFTER a warm pass (Task 6). This task builds the MEASUREMENT; Task 7 runs it on warmed data.

---

### Task 4 (GATE LEG 2): cache-key parity — derive the key from the resolved-match identity

**Files:** Modify `app/services/price_service.py` (the cache-key derivation per Task 1 findings) + `scripts/cron_warm_price_cache.py` if it builds its own key. Test: `tests/test_price_cache_key_parity.py`.

- **Step 1 (failing test):** warming SKU phrasing A and reading phrasings B/C of the SAME SKU HIT the same key. Concretely: `build_size_aware_price_cache_key`-equivalent for ("Dior Sauvage", "Eau de Toilette", "100ml") == that for ("Dior Sauvage", "EDT", "100ml") == ("Dior Sauvage", None, "100ml" after EDT-resolution). Likewise S24 "256GB" warmed vs live. Use `_identity_cache_token` (concentration/variant/size). Assert distinct VARIANTS still differ (EDT≠EDP, 256≠128).
- **Step 2:** run-fail (today they differ → MISS).
- **Step 3:** implement — make the key derive from the RESOLVED-match identity token (alias-normalized: EDT≡"eau de toilette", oz≡ml) rather than the raw query string, on BOTH the warmer write and the live read. Keep flag-OFF byte-identical (guard with `exact_gate_enabled()` if it changes any flag-OFF behavior).
- **Step 4:** run-pass.
- **Step 5:** commit.

---

### Task 5 (GATE LEG 3 + folded items): fresh-purge precondition, titleless-price consistency, Serper guard

**Files:** `scripts/cron_warm_price_cache.py`, `app/services/price_service.py` (`is_price_showable` titleless branch), a purge/clean-cache helper. Tests: `tests/test_warmer_preconditions.py`.

- **Step 1 (failing tests):** (a) the warmer refuses to run unless a clean-cache assertion passes; (b) titleless-price consistency — DECIDE per recon: either the warmer guarantees a title on every cached price, OR `is_price_showable(enforce_correctness=True)` PENDS a titleless price (fail-closed). Pin the chosen behavior (recommend: pend titleless at display, since a price we cannot SKU-verify should not show — but verify it does not over-reject a measurable share via the coverage sweep). (c) a Serper-budget circuit caps the warmer per run (`MAX_QUERIES_PER_RUN` + budget check).
- **Step 2-4:** run-fail → implement → run-pass.
- **Step 5:** commit.

---

### Task 6: warm a per-category sample (real, bounded) + run the KPI on it

- **Step 1:** confirm a fresh purge (the GOTCHA: a local `_get_price`/warm with `nocache=True` STILL WRITES the shared Upstash + `product_prices` DB — so either run against an isolated cache OR accept + re-purge after). Document the Serper estimate.
- **Step 2:** run the warmer on the per-category truth set (bounded by `MAX_QUERIES_PER_RUN`).
- **Step 3:** run the warmed KPI (Task 3) → per-category pass-rate.
- **Step 4 (NO code commit — a measurement artifact):** save the per-category KPI result to `docs/investigations/2026-06-30-warmer-kpi-result.md`.

---

### Task 7 (WAVE 1 GATE): coverage sweep + comm gate + AUTO-ACTIVATION

- **Step 1 — coverage sweep (Workflow tool):** adversarial sweep over the warmer/KPI/cache-key changes — does the cache-key change collide two distinct variants? does the titleless rule over-reject genuine prices? Reproduce every finding through the runtime; dispatcher gates each.
- **Step 2 — comm gate:** worktree of `origin/main` + `.env` + free-unit suite both sides + `comm -13` the sorted FAILED sets → branch-only-NEW must be `[]` vs `.qa-correctness/main-baseline-failed.txt`. CI `backend-tests` is RED-by-design — gate on the comm-diff, not CI.
- **Step 3 — AUTO-ACTIVATION rule:** flip `ENABLE_PRICE_CACHE_WARMER` ON (Railway `railway variables --set` + explicit redeploy) **iff** per-category KPI ≥85% (Task 6) ∧ cache-parity proven (Task 4) ∧ clean cache (Task 5) ∧ sweep + comm green. **Any red → warmer stays OFF + write the per-leg diagnosis; STOP (do not start Wave 2 until Wave 1 is green or consciously deferred).**
- **Step 4:** open a PR to main (`gh` via the cached git-credential token; the deploy-classifier blocks direct push to main). Merge on green.

---

# WAVE 2 — structured `VariantDescriptor` (ONLY after Wave 1 gate passes)

### Task 8: Recon the 9 residuals + the descriptor source

**Read + write `docs/investigations/2026-06-30-variant-descriptor-recon.md`:** for EACH residual (gender flanker, one-sided SPF, same-token concentration flanker `Sauvage→Elixir`, cross-unit g↔ml, makeup one-sided formula, ZMA/Cal-Mag acronym), document: the current token-rule + its over-rejection trap (why a token fix re-breaks correct products — see the pins in `tests/test_correctness_coverage_sweep_fixes.py`), and which axis extractor already produces the structured signal. Decide the 2-3 cases that genuinely need the NARROW LLM hint (men's-base vs femme-flanker; flagship vs flanker concentration). Commit the note.

### Task 9: the `VariantDescriptor` type + extractor (TDD)

**Files:** Create `app/services/variant_descriptor.py`. Test: `tests/test_variant_descriptor.py`.
- **Step 1 (failing test):** `build_variant_descriptor(text, category, brand)` returns a typed object: `{concentration, size:{value,unit_class}, storage_gb, gender, spf, count, strength, formula, flavour, ...}` from the existing extractors. Pin per category (Sauvage EDT → concentration=EDT; Sauvage Elixir → concentration=Elixir; CeraVe 340g → size{340,g}; CeraVe 177ml → size{177,ml}).
- **Step 2-4:** run-fail → implement (wrap the existing `extract_concentration`/`_size_ml`/`_gender_of`/`_spf`/… into the descriptor) → run-pass.
- **Step 5:** commit.

### Task 10-N: close each residual via descriptor comparison (one task per residual, TDD)

For each residual, a task: **Step 1** flip its xfail/held pin in `tests/test_correctness_coverage_sweep_fixes.py` to assert the correct reject AND add the over-rejection GUARD it must not break; **Step 2** run-fail; **Step 3** route `_selection_match`/the backstop to compare the `VariantDescriptor` field (with correct asymmetry) instead of the token set, adding the narrow LLM hint only for the 2-3 recon-flagged cases; **Step 4** run-pass; **Step 5** commit. Keep flag-OFF byte-identical.

### Task N+1 (WAVE 2 GATE): coverage sweep + comm gate

- **Coverage sweep (Workflow):** re-sweep ALL categories both directions — the descriptor fix's OWN over-rejection is the next blind spot. Dispatcher gates every finding; re-sweep after each fix until convergence.
- **Comm gate:** branch-only-NEW == `[]` vs main.
- PR to main; merge on green.

---

## Hard-won gotchas (carry into both waves)
- `nocache=True` bypasses the cache READ, not the WRITE → local warm/seed/KPI pollutes the shared prod Upstash + `product_prices` DB. Run against an isolated cache or purge after.
- COLD compares hit the 30s `STREAM_HARD_CAP` → genuine loses → pending; `_get_price` in isolation (no compare cap, 60s) ≈ the warmable ceiling. The warmer (cache-served) is the only cold genuine path — but only if the warmed key matches the live parse (Task 4).
- CI `backend-tests` is RED-by-design on EVERY commit incl shipped main (`test_value_math` TDD stubs + `test_youtube` env). Gate on the comm-diff, never CI green.
- Coverage-driven > hypothesis-driven: a sweep whose prompt LISTS cases only confirms the prompter. Make agents ENUMERATE the space + reproduce through the runtime selector. After a fix, re-sweep (not the hypothesis review).
- Windows cp1252: pin `encoding='utf-8'`; dump non-ASCII to a file + Read, never `print()`.
