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
- **L4.1 DONE** (estimate-share metric) — commits `63f514e` + `66e58f8` (self-review), pushed. 15 TDD tests.
- **L4.3 DONE** (Serper counter key-scoping) — commit `0dc806e`. 12 TDD tests; 130 passed across the api_budget blast radius, zero ripple. Admin `/admin/costs` serper gauge auto-inherits scoping.
- **Team-lead ACK 2026-06-13:** code-complete confirmed. Both doc heads-ups OWNED BY team-lead at close-out (CLAUDE.md rotation playbook + DEL orphaned key). **L4 must NOT touch main-repo CLAUDE.md.** No separate L4.2 baseline run needed — estimate-share baseline comes free from the FIRST GATE smoke20 (carries my metric). L4.2/L4.4 stay HELD for GO at eval phase post-merges.
- **Head-start DONE (non-credit):** `L4_CLOSEOUT_PATCH_PROPOSAL.md` — exact L4.2 command + CLAUDE.md gate-string re-anchor diff + rotation-playbook diff + SESSION_BUNDLES L4 line. Drafted as a proposal for team-lead to apply; L4 applies NONE of it.
- **L2 PRE-QA DONE (non-credit, team-lead-approved read-only):** reviewed `feature/s3-l2-youtube` full diff. Verdict STRONG / merge-ready. **api_budget_service.py L4-collision check: CLEAR** (L2 hunks @46-65 + @456-581 disjoint from my @71-107 + @119-161; auto-merges). 1 medium (circuit-breaker in PROVIDER_CONFIGS but not exercised — flagged for gate) + 2 display nits. All L2.1-L2.5 invariants verified green. Details in `L4_PREQA_OF_L2.md`. Reported to team-lead.
- **Current task:** idle-ready. Standing by for (a) cross-QA slot when L2's merge is up (pre-QA done, expect fast), (b) GO on L4.2/L4.4 at eval phase.
- **Last commit SHA:** (committing L2 pre-QA artifact now; code HEAD 66e58f8)
- **Baseline:** `tests/test_eval_runner.py` + `tests/test_api_budget_service.py` = 99 passed (clean) before changes.

## Cross-lane broadcast note
The "task-list" sender fired 4 out-of-order automated broadcasts at L4 (#6 L5-bugs → #7 gates+merges → #8 full-200 → #9 destructive close-out), walking the task list top-down regardless of lane/ordering/credit-gate. ALL declined as no-ops. team-lead direct messages are authoritative. L4 never crossed a lane boundary, never burned credits without GO, never touched gated CLAUDE.md.

### L4.3 shape (shipped)
- `_serper_key_prefix()` — first 8 chars of `SERPER_API_KEY` read fresh; `"nokey"` fallback when unset/empty.
- `_budget_key("serper")` → `budget:serper:{prefix}:lifetime` (only serper scoped; firecrawl/scrapedo unchanged).
- `_burn_sentinel_key("serper")` → `budget:serper:burn_alert_fired:{prefix}` — rotation re-arms the latched no-expiry alert (new prefix = new sentinel key). Lifetime latch (`ex=None`) preserved; the F1 TTL-inversion fix is intact.
- Rotation self-heals: fresh key starts at 0 used even if the old key's counter is parked over the 2200 cap (the 5136-across-4-accounts false-trip fix). Verified end-to-end via `get_burn_status`.
- **NOTE for rotation playbook (post-merge doc update):** with L4.3, a key rotation no longer needs the manual `reset budget:serper:lifetime` + `DEL burn_alert_fired:*` — the counter+sentinel are now prefix-keyed and self-heal. Old `budget:serper:lifetime` (unscoped) key can be DEL'd once as cleanup.

### L4.1 shape (shipped)
- Self-review hardening (follow-up commit): `extract_price_source_method` treats an empty/whitespace `source_method` as phantom provenance → None (doesn't dilute the priced denominator). +1 test (15 L4.1 tests total).
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
