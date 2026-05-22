# Bundle C — Production State

**Last verified:** 2026-05-22 (via `railway variables --kv | findstr BUNDLE_C`)

## TL;DR

**`ENABLE_BUNDLE_C_SCORING=false` in Railway.** Code default at `app/services/scoring_service.py:303` is also `false`. The flag gates **one specific behavior**: how missing raw signals are represented (`None` when on, `MISSING_SCORE=50` when off). In current production, missing signals get `MISSING_SCORE=50`, so the **silent dim omission filter never fires** and the calibration cascade operates on numeric defaults. All other Bundle C behaviors (A.3.x, A.4.5, A.4.7, A.5.x, A.6.x, A.7.x, A.9.x, A.10.x, frontend Section B) are unconditional and **are live in production**.

The "Bundle C is OFF in prod" framing is wrong. The accurate framing is: **Bundle C's missing-signal representation runs on the legacy path; the other ~95% of Bundle C is live.**

## What is and isn't gated

| Bundle C item | Flag-gated? | Live in prod (flag=false)? |
|---|---|---|
| Missing-signal value (None vs 50) | **YES** | No — `MISSING_SCORE=50` is injected (legacy path) |
| Silent dim omission (A.4.9) when both products lack data | **YES (indirect)** | No — filter checks `is None`, never matches |
| `calibrate_score(has_signal=False)` short-circuit | **YES (indirect)** | No — `has_signal` kwarg not passed at any call site anyway |
| A.3.1 pros/cons via `response_format=json_object` | No | Yes |
| A.3.2 factual_verdict builder | No | Yes |
| A.3.3 Serper GCC→US fallback | No | Yes |
| A.4.5 `detect_comparison_quality` (weird-comparison detector) | No | Yes |
| A.4.7 Tier 2 spec fallback (4s `asyncio.wait_for` + gather) | No | Yes |
| A.5.x 5-tier `top_tier` budget + Migration 024 | No (DB-level) | Yes |
| A.6.1 priority-driven `VALUE_FORMULA_BY_PRIORITY` | No | Yes |
| A.7.1 loosened confidence thresholds | No | Yes |
| A.9.1 `applied_shifts` qualitative-only contract | No | Yes |
| A.10.x diagnostic flag-gating | No | Yes |
| Frontend Section B (BudgetPicker, DimensionBars overhaul, ConfidencePills, etc.) | No | Yes |

*Verification: `grep -n "_bundle_c_scoring_enabled\|ENABLE_BUNDLE_C_SCORING" app/services/scoring_service.py` returns exactly one usage site, at line 944.*

## Why the flag is off

Set to `false` on Railway by Ahmed during the Session 52 post-merge debugging window. Specific trigger not recorded. **Treat as "paused for re-validation," not "kill switch by design."** No code-side reason to keep it off; the gate just was never opened.

## Before flipping the flag to `true`

This is a real behavioral change. Expect:

- Some products that previously displayed scores around 70 (calibrated `MISSING_SCORE=50`) will now have missing-data dims **silently omitted** from `DimensionBars`
- More confidence pills will read "low/insufficient"
- `applied_shifts` semantics already qualitative-only — no behavior change there
- Combined with the H1 fix (deterministic `winner_index`), watch the `WINNER_INDEX_MISMATCH` log added in `response_builder.py` — it counts how often GPT and the calibrated scoring disagree on the winner

**Pre-flip checklist:**

1. Pick a low-traffic window (off-peak GCC hours)
2. Have Sentry dashboard open, filter on `app/services/scoring_service.py` and `app/services/response_builder.py` for new exception patterns
3. Have the rollback ready: `railway variables set ENABLE_BUNDLE_C_SCORING=false` (one command, immediate)
4. Flip on: `railway variables set ENABLE_BUNDLE_C_SCORING=true`
5. Watch for 30 minutes minimum, then 24 hours
6. If Sentry stays clean and `WINNER_INDEX_MISMATCH` log volume stays low (<5% of comparisons), keep on; otherwise rollback and capture an incident note here

## Related drift caught in the same audit

`ENABLE_HYBRID_MODEL_ROUTING=true` in Railway, but `grep -r "ENABLE_HYBRID_MODEL_ROUTING" app/` returns **zero matches**. The env var is **phantom** — setting it has no effect. `model_router_service.py` runs unconditionally; `gpt-4o` routing always happens below the daily cap. Either wire the flag in `model_router_service.get_model()` or remove the entry from `CLAUDE.md`'s env-vars list. Currently the value is cosmetic.

## Sources

- Flag definition: `app/services/scoring_service.py:298-306`
- Flag usage (only site): `app/services/scoring_service.py:944`
- Operational context (with retraction): [CLAUDE.md](../CLAUDE.md) Session 52 paragraph
- Historical bundle log (with retraction): [docs/SESSION_BUNDLES.md](SESSION_BUNDLES.md) Bundle C entry
- Audit memory: `memory/feedback_docs_vs_railway_env_drift.md`
- Re-validation kill switch command: `railway variables set ENABLE_BUNDLE_C_SCORING=false`

## When to update this doc

- Whenever `ENABLE_BUNDLE_C_SCORING` value changes in Railway
- Whenever a new code site reads `_bundle_c_scoring_enabled()` (currently 1; expand the table if it grows)
- Whenever `ENABLE_HYBRID_MODEL_ROUTING` is wired or removed
- At the next quarterly architecture review (re-run `railway variables --kv` and verify the table)
