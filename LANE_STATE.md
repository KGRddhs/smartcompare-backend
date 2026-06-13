# LANE_STATE — L4 (Eval persistence + estimate-share metric + Serper counter)

**Branch:** `feature/s3-l4-eval-metric`
**Worktree:** `C:/Users/SynAckITPC/Documents/ai/smartcompare-s3-l4`
**Owner:** L4
**Plan:** `docs/plans/2026-06-13-bundle-b-s3-plan.md` §L4

## Scope (4 sub-tasks)
- **L4.1** estimate-share metric — `% of priced fields with source_method=="estimated"`. Thread `extract_price_source_method` → `GradedQuery` → `aggregate()` → `EvalReport` → `_format_report` + per-query JSONL. Mirrors the I3.6 `missing_dim_cells` pattern exactly. **CODE NOW (TDD, mocked bodies).**
- **L4.3** key-scope `budget:serper:lifetime` → `budget:serper:{key_prefix}:lifetime` (prefix = first 8 chars of `SERPER_API_KEY`); rotation-safe `burn_alert_fired:{key_prefix}` sentinel. **CODE NOW (TDD, mocked Redis).**
- **L4.2** persist S3 full-200 row + re-anchor baseline off `4aee8e88`. **HELD for team-lead GO (Serper-credit-heavy).**
- **L4.4** live burn drill (cold query increments new counter; rotation resets clean). **HELD for team-lead GO.**

## Status
- **L4.1 DONE** (estimate-share metric) — 14 new TDD tests green; full `test_eval_runner.py` = 32 passed; `test_eval_persistence.py` = 6 passed (new metadata keys flow through). py_compile OK.
- **Current task:** L4.3 — key-scope the Serper counter (TDD next).
- **Last commit SHA:** (committing L4.1 now)
- **Baseline:** `tests/test_eval_runner.py` + `tests/test_api_budget_service.py` = 99 passed (clean) before changes.

### L4.1 shape (shipped)
- `extract_price_source_method(body, idx)` + `count_price_source_cells(body) -> (estimated, priced)` in eval_runner.py.
- `GradedQuery.{estimated_price_cells, priced_cells}` (default 0); `EvalReport.{estimated_price_cells_total, priced_cells_total, estimate_share}`.
- `estimate_share = sum(estimated) / sum(priced)` (0.0 guard on empty/all-error/no-price). Denominator = PRODUCED prices (non-null source_method); a no-price product is in neither bucket (honesty-of-produced, not coverage).
- Threaded: `grade_run_result` populates → `aggregate` sums → `_format_report` "estimate-share" line → per-query JSONL (`dataclasses.asdict`) → persist `metadata` jsonb (`estimate_share` + totals).

## Key findings (grounding)
- I3.6 `missing_dim_cells` is the exact mirror pattern for L4.1: `extract_*` fn → `GradedQuery.<field>=0` default → `grade_run_result` populates → `aggregate` sums to `EvalReport.<>_total/_mean` → `_format_report` line + persist `metadata`. Estimate-share differs only in being a per-product (idx 0,1) price tally → run-level ratio.
- `extract_price_amount` @ eval_runner.py:246, `aggregate` @620, `EvalReport` @487, `_format_report` @711, per-query JSONL written @787 (`dataclasses.asdict(g)`).
- L4.3 blast radius: `_budget_key("serper")` @ api_budget_service.py:74; `_burn_sentinel_key` @118 derives from it. Burn-alert tests (test_api_budget_service.py:584-715) seed via `_budget_key("serper")` HELPER (not literal) → key-scoping is transparent to them. ONLY `test_serper_is_lifetime` @62 asserts the literal string `budget:serper:lifetime` → must update to the key-scoped format.
- `SERPER_API_KEY` may be unset in tests (no `.env` in worktree; conftest `load_dotenv` searches up-tree). `_serper_key_prefix()` MUST be deterministic with a stable fallback (`"nokey"`) when env is unset/empty so the prefix is constant within a process.

## Blockers
- none

## Handoff notes
- Ring cross-QA order: L5→**L4**→L2→L3→L1→L5 (I QA L2's merge; L5 QAs mine).
- L4.1's estimate-share baseline is FED BY L1.1's gold-200 estimate audit — coordinate the baseline number at the L1/L4 mid-eval.
- L4.2 re-anchor touches CLAUDE.md + gate commands (shared docs) — coordinate with team-lead before editing main-repo CLAUDE.md.
