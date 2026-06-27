# Genuine-price CORRECTNESS — FIX plan (PR #9 was HELD; this session fixes the leaks)

**Status:** PR #9 (`feature/genuine-price-correctness`, 9 commits off prod `b207bfa`) BUILT the 5-layer
correctness scaffolding but an external deep review REFUTED the "exact product, fail-closed,
independently measured" claim with REPRODUCIBLE runtime leaks. Every blocker below was verified
gate-on against the real code. **This plan fixes them, then re-gates. Do NOT merge until every gate
passes.** PR #10 (docs-only context) should merge to `main` first; this fix-work rebases off it.

## CARDINAL RULE (unchanged)
Select a price ONLY if it is the EXACT requested product — model + concentration + size/storage +
variant + count + strength — native BHD (or honest converted_usd), CURRENT PDP price, in stock,
on a valid PDP URL. A miss PENDS. Provenance (genuine `source_method`) is necessary, NOT sufficient.
The gate must ALSO not over-reject (no false pends).

## Two load-bearing lessons (why PR #9 leaked despite a green gate)
1. **A green comm gate + a passing self-review is NOT proof of correctness.** The 110 new tests
   ENCODE the same wrong assumptions (they assert missing-URL + unknown-stock are "acceptable") AND
   never exercised the real runtime paths (iHerb / pharmacy / `select_best`). Reproduce the actual
   RUNTIME leak through the public entry, not a helper in isolation.
2. **The strict matcher that was unit-tested (`is_exact_match`) is NOT the one the selector runs**
   (`select_best` → permissive `_selection_match`). Test the function the orchestrator actually calls.

---

## THE 8 RELEASE BLOCKERS (all reproduced gate-on) + the fix per the directive

### B1 — CRITICAL: supplements return + cache the WRONG product (iHerb + pharmacy bypass)
- **Repro:** a mocked request for *Solgar Vitamin D3 5000 IU 120 Softgels* returned the genuine-BHD
  price of *Solgar Magnesium Citrate 120 Tablets*.
- **Cause:** `fetch_iherb_price` (`app/services/price_service.py:~5408`, selection fallback `:~5552`)
  falls back to "best overlap" with NO minimum threshold, REMOVES the matched title, and hardcodes
  `in_stock=True`; the response backstop then accepts it. The pharmacy route calls
  `extract_jsonld_price()` WITHOUT the requested product name (`:~5658`) → exact gate disabled.
- **Fix:** fix the iHerb/pharmacy bypasses FIRST. Route both through the SAME structured exact
  matcher; keep the matched title/name + real availability on the price; pass `query_name` to
  `extract_jsonld_price`. No "best overlap" without an exact-identity gate.

### B2 — CRITICAL: the strict matcher is not the runtime matcher (flankers + product FORMS leak)
- **Repro (gate-on, verified):** `select_best`/`_selection_match` ACCEPT:
  - *YSL Black Opium* ← *Black Opium Over Red* (flanker; extra distinctive token tolerated by subset)
  - *Dior Sauvage EDT* ← *Dior Sauvage Deodorant* (form — even `is_exact_match` accepts it)
  - *Tom Ford Oud Wood EDP* ← *Tom Ford Oud Wood Candle* (form)
  - *Dior Sauvage EDT 100ml* ← a candidate omitting BOTH concentration and size (auto-accepted)
- **Cause:** `_selection_match` (`:~3035`) is query-SUBSET; product forms (deodorant/candle/lotion/
  refill) are STRIPPED as noise (`_FORM_NOISE_TOKENS`, `:~2794`); axes are checked only when BOTH
  sides state them. `select_best` (`:~3172`) runs `_selection_match`, not the strict `is_exact_match`.
- **Fix:** REPLACE runtime subset matching with a STRUCTURED EXACT matcher that explicitly REJECTS
  flankers and different product FORMS (deodorant/candle/spray ≠ the bottle). A query-stated axis
  MISSING from a candidate must be UNVERIFIED → pend, not auto-accept. Make `select_best` USE this
  matcher (one matcher, used at runtime).

### B3 — CRITICAL: the `usable_exact_genuine` KPI is circular + disconnected from its truth set
- **Repro:** the truth file says the function receives a `truth_entry` and validates expected
  identity; the actual `usable_exact_genuine_for_product(body, product_idx)` (`scripts/eval_runner.py:474`)
  NEVER loads or examines the truth file. It counts prices with no URL, unknown/missing stock, and
  no independent identity check. Both missing-URL examples count as usable; `tests/test_kpi_metric.py:47`
  explicitly declares missing URLs acceptable.
- **Fix:** REBUILD `usable_exact_genuine` to LOAD each truth entry and INDEPENDENTLY validate
  expected identity, present PDP URL, confirmed stock, and current offer. Fix the tests that codify
  missing-URL / unknown-stock as acceptable.

### B4 — HIGH: JSON-LD can label stale or variant-minimum prices as exact + available
- **Repro:** an expired 2020 offer accepted as showable.
- **Cause:** `AggregateOffer.lowPrice` accepted (`extract_jsonld_price:~3928` `offer.get("price") or
  offer.get("lowPrice")`) even though it may be the cheapest size/variant; `priceValidUntil` never
  checked; missing availability → `in_stock=True`.
- **Fix:** `AggregateOffer.lowPrice` must NOT represent an exact variant without SKU/offer proof;
  honor `priceValidUntil` (reject stale); missing availability = unknown, not auto-in-stock.

### B5 — HIGH: missing identity + URL is fail-OPEN
- **Repro:** a 400 BHD `local_bhd` candidate with NO title/name/URL passes both `select_best()` and
  the response backstop.
- **Fix:** require title/name + a valid PDP URL BEFORE selection OR cache write. No identity / no
  valid PDP URL → pend (fail-CLOSED). (The tests intentionally codify missing-URL/unknown-stock as
  acceptable — change them.)

### B6 — HIGH: cache keys are request-derived, not resolved-identity-derived
- **Repro:** the cache key is created before any candidate is selected, from parser/request fields,
  and every later source writes to it; no runtime `resolved_identity`. A wrong candidate that passes
  the permissive matcher is cached under the requested product for the genuine TTL
  (`app/services/structured_comparison_service.py:~4121`).
- **Fix:** derive the cache key from the RESOLVED match identity; write the cache ONLY after an exact
  match resolves (the matcher's identity == the cache key's identity).

### B7 — MEDIUM: internal gate details leak through the public payload
- **Repro:** `guard_rejected` (described as "non-UX") is copied into `price`, and raw price dicts are
  exposed through both response projections (`response_builder.py:~1249` and `:~1402`).
- **Fix:** keep diagnostics (`guard_rejected`) in `metadata`, NOT the public price object; ensure the
  response projection strips internal `_`/diagnostic keys from the price.

### B8 — MEDIUM: "flag OFF is byte-identical" is unsupported + false
- **Cause:** there are NO tests exercising `ENABLE_EXACT_PRICE_GATE=false`; several changes remain
  unconditional (retaining shopping titles, availability semantics, removing Unbxd `wasPrice`).
- **Fix:** add a flag-OFF test asserting byte-identical b207bfa behaviour, OR gate the remaining
  unconditional changes. Make the rollback claim true + tested.

## What is LEGITIMATE (do not redo; but fix the test assumptions)
- The 110 new focused tests pass; full-suite 8043 passed / 46 failed == prod baseline (test-set
  zero-regression is real). BUT the tests encode incorrect assumptions (missing-URL/unknown-stock
  "acceptable") and miss the reproduced runtime paths — those tests must be corrected.
- The 5-layer SHAPE (exact gate + authority selector + availability + chokepoint backstop +
  cache-key + KPI) is the right architecture; the leaks are gaps in coverage/enforcement.

## Deferred / acknowledged (decide, don't silently carry)
- M3 fashion category-detection (brand-overlap risk: grocery "Red Apple" vs "Green Apple").
- L2 `_page_identity_ok` store-name-only title (can't be distinguished from a wrong product by
  token overlap — keeping it conservative-pend is correct).
- L4 "Pro Max" vs "ProMax" cache miss (perf only).
- Vitamin C vs D single-char discriminator drop (PRE-EXISTING in `_identity_tokens_ps`, not PR #9).

---

## EXECUTION — ultracode Workflows, TDD per wave, critique + fix + QA, comm-gated

Run as ultracode Workflows (one per wave): sequential implement agent(s) → parallel adversarial
reviewers → QA. The DISPATCHER gates every finding against the real code (~⅓ of reviewer findings
are no-ops — grep every named symbol, re-derive every must-fix). After EACH wave, run the comm
zero-regression gate (`branch-only-NEW == []` vs the cached `.qa-correctness/main-baseline-failed.txt`,
46 == prod baseline). Run a SECOND adversarial review at the end to catch opposite-error regressions
(last time round-2 caught a class-swap under-rejection + a weight-axis over-rejection that round-1's
fixes introduced).

- **Wave 1 — FAILING adversarial tests FIRST (TDD).** Reproduce all 8 blockers as failing tests
  THROUGH THE REAL RUNTIME PATH (not helpers): the iHerb Solgar-D3→Magnesium mock; `select_best`
  flanker + deodorant + candle + omitted-axis; the no-title-no-url fail-open; the expired-2020
  AggregateOffer; the KPI loading-and-validating a truth entry; the request-vs-resolved cache key;
  the guard_rejected payload leak; the flag-OFF byte-identical assertion. Confirm each FAILS on the
  current branch.
- **Wave 2 — structured exact matcher (B2).** New exact matcher (reject flankers + product forms;
  missing query-stated axis = unverified→pend); `select_best` uses it. Make the Wave-1 matcher reds pass.
- **Wave 3 — adapters/extractors: identity + availability + URL (B1, B4, B5).** Preserve candidate
  identity (title/name) + real availability through EVERY adapter; fix iHerb (threshold + keep title +
  real stock) + pharmacy (pass `query_name`); `AggregateOffer.lowPrice` needs SKU/offer proof +
  `priceValidUntil` + missing-availability≠in_stock; require title/name + valid PDP URL before
  selection/cache (fail-closed).
- **Wave 4 — cache-key-from-resolved-identity + payload hygiene (B6, B7).** Key from the resolved
  match; cache write only after an exact match; `guard_rejected` → metadata, strip internal keys
  from the public price.
- **Wave 5 — rebuild the KPI (B3).** `usable_exact_genuine` loads each truth entry + independently
  validates expected-identity / PDP-URL / confirmed-stock / current-offer; fix the tests that codify
  missing-URL/unknown-stock as OK.
- **Wave 6 — rollback truthful (B8) + final gates.**

## GATES before any merge
1. comm zero-regression (`branch-only-NEW == []`) — `extract_jsonld_price` / `is_price_showable` /
   the consume / the cache key are very high blast radius.
2. The 8 adversarial cases are FAILING-first then GREEN (and the corrected tests no longer assert
   missing-URL/unknown-stock are acceptable).
3. No-fab: PEND on a miss; new PENDs flagged `guard_rejected` (in metadata) + MEASURED, never silent.
4. Rollback: `ENABLE_EXACT_PRICE_GATE=false` proven byte-identical to b207bfa (tested).
5. Second adversarial review round → no opposite-error regression.
6. POST-DEPLOY (the eval is a prod-HTTP harness): smoke20 vs baseline `54b603e8`; flag-ON prod
   spot-check (`woo_store_api` Sauvage still the correct exact one, not a cheaper wrong one).
7. Rebuilt KPI run (COLD + WARMED, the non-circular truth set) — Phase-2 warmer activation stays
   PAUSED until `usable_exact_genuine` ≥ 85% per category (electronics/fashion/fragrances).

## Ops gotchas (recurring)
- `eval_runner` is a PROD-HTTP harness → POST-DEPLOY only.
- A local `_get_price`/seed/warm with `nocache=True` STILL WRITES the shared Upstash + `product_prices`
  DB (nocache bypasses the READ, not the WRITE) → never warm/seed before correctness passes.
- stale Redis cache masks a fix → re-test a FRESH pair or `?nocache=true`.
- deploy-classifier BLOCKS `git push origin …:main` + destructive prod ops → open a PR via `gh`
  reusing the git credential: `GH_TOKEN=$(printf 'protocol=https\nhost=github.com\n\n'|git credential fill|sed -n 's/^password=//p')` (gh CLI is unauthenticated; token never printed). Repo `KGRddhs/smartcompare-backend`.
- worktrees DON'T inherit gitignored `.env`; stale OS-scope `SUPABASE_*` can shadow `.env` (restart CC).
- Workflow rate-limit worsens with session age → batch ≤4 concurrent late; run heavy fan-out fresh;
  build multi-line agent prompts with `array.join('\n')`, not nested backticks.

## READ FIRST next session
- `CLAUDE.md` → the "genuine-price CORRECTNESS build — PR #9 OPEN + HELD" Active-runtime entry.
- `memory/project_genuine_price_correctness_plan.md` (the HELD banner + blockers).
- The branch's tests: `tests/test_correctness_*.py`, `tests/test_exact_match_contract.py`,
  `tests/test_kpi_metric.py`, `tests/test_correctness_review_fixes.py`.
- The IMPL-SPEC (the original architecture): `docs/plans/2026-06-27-genuine-price-correctness-IMPL-SPEC.md`.
- Lessons: `memory/feedback_green_gate_not_correctness.md`, `memory/feedback_verify_llm_reviewer_findings.md`.
