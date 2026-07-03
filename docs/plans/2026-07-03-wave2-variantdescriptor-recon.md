# Wave-2 VariantDescriptor — recon results (2026-07-03, branch @ 7af40eb)

**Status: RECON COMPLETE — ready to BUILD next ultracode session.** Raw lane JSONs (census / design / parity, ~90KB, machine-consumed): `docs/investigations/2026-07-03-wave2-recon/*.json`. All findings reproduced through the REAL runtime with `ENABLE_EXACT_PRICE_GATE=true`.

## The structural picture
The 5 decision points collapse into TWO enforcement strengths:
- **(A) airtight** — brand-aware full `_selection_match` at selection / `select_best` / `should_cache_price` (price_service.py:5616/:5889/:6139)
- **(B) axis-only** — `_backstop_identity_ok` (:5800, = `_axis_mismatch(strict_extras=False)`) + bounded `_category_type_added` (:4254) at cache-read `_cache_price_identity_ok` (scs.py:720) and display `is_price_showable(enforce_correctness=True)` (:1313)

**Census: 21 classes** — 5 FULL leaks (gender flanker base→femme, one-sided SPF, makeup one-sided formula, apparel bare size-letter, Disney-Stitch construction — last two newly documented), 9 BACKSTOP-ONLY leaks (Sauvage→Elixir, GoodGirl→Suprême, AF1→Air Max 1, AirPods Pro→Pro 2, iPhone-SE year both-stated, gender both-stated ⚠️ even the EXPLICIT Homme↔Femme conflict passes the backstops, femme-query-unconfirmed, Size-M-vs-XL, candidate-omits-axis, titleless), 6 OVER-REJECTIONS (ZMA/Cal-Mag, Omega-3 hyphen↔space, SE-year-add, Switch-Light, g↔ml cross-unit, ReDoS-cap), + the ladder-exposure amplifier. Confound corrected: prior SE/AirPods "display pends" were the price-plausibility guard, NOT identity — at realistic amounts they LEAK at read/display.

## Load-bearing NEW findings
1. **The L2-DB round-trip drops `title` AND `in_stock` on this branch** (product_data_service.py:103/119-126, save :139-152 — PR#12's migration-033 title persistence is NOT here) → every DB-served price re-enters identity-less → both weak chokepoints are **VACUOUS for the whole DB leg**, and scs:4679 re-promotes such rows into Redis under only the weak check. **Warmer precondition #1** (converges with PR#12).
2. **Warmer-writable poison TODAY = exactly 2 classes** (gender flanker + one-sided SPF — the only census classes that ALSO pass the write gate). Everything else is read/display-only exposure. This is the runbook risk-quantification line.
3. The GPT-verdict scrub (extraction_service.py:1782) calls `is_price_showable` WITHOUT `enforce_correctness`/category → a display-pended not_exact/OOS amount can still reach the verdict prompt. Parity gap; fix alongside.

## The build plan (design lane, option C confirmed)
- All ~35 axis extractors already exist as pure functions; the same strings are re-parsed ~5× per candidate → **extract-once VariantDescriptor is a refactor, not new parsing**. All decision fns already no-op flag-OFF → Phase-A inherits byte-identity for free.
- The residuals split into 3 closure modes: **backstop-only** (bounded token axes at the backstops — no LLM: Elixir/Pro-2/gender-both-stated class), **deliberate-tradeoff** (gender flanker / one-sided SPF / makeup formula — token-impossible: curated base-line reference + NARROW LLM hint), **over-rejections** (deterministic alias folds: ZMA≡Cal-Mag-class acronyms, Omega-3 hyphen fold).
- **LLM hint: cache-WRITE time only, off-clock/warm contexts, NEVER the 15s live path** (live display keeps the HELD tolerances); gpt-4o-mini temp=0 JSON; Redis-cached verdicts 90d; per-run cap knob; fail-closed = refuse-the-write (price still displays).
- **Phases: A** refactor-with-pins (golden-corpus equivalence dump) → **B1** backstop new axes (the warmer precondition) + the DB title/in_stock persistence fix + the verdict-scrub parity fix → **B2** selection recoveries (over-rejection folds) → **B3** curated-reference + LLM hint. Each phase: coverage sweep BOTH directions + comm gate.

## Next ultracode session ladder
1. **Wave-2 BUILD** per the phases above (Phase A+B1 = the warmer unblock; B2/B3 can follow).
2. **PR sequencing with Ahmed**: #12 → #13 → `feature/genuine-price-kpi` (KPI 18/18 evidence in `docs/plans/2026-07-01-warmer-source-quality-blocker.md` §session-3). Note the DB-leg fix overlaps PR#12's migration 033 — reconcile when stacking.
3. **Warmer activation** per `docs/runbooks/2026-06-30-warmer-activation.md`: fresh purge → flip (needs Railway auth — CLI dead on this machine) → re-measure 3×.
4. Optional: determinism live-tuning (`ENABLE_GENUINE_PRICE_PRIORITY` dormant); FE converted-USD caption leg (mobile session, EAS).
