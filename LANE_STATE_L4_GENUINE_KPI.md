# LANE L4 (S3 reopened) — Eval genuine-BH-price-share KPI + smoke20 loop + OpenAI cost-guard

**Worktree:** `C:/Users/SynAckITPC/Documents/ai/smartcompare-s3-l4`
**Branch:** `feature/s3-eval-genuine-kpi` (off `origin/main` @ 41365a1)
**Owner:** L4
**Task:** #18 (blocks #8 close-out). Owns `scripts/eval_runner.py` + `eval_persistence` — no conflict with L1's price pipeline.

## Mandate (Ahmed via team-lead): GENUINE BH prices — US/estimate last resort. genuine-BH-share is the PRIMARY dial.

## Tasks
- **E1 — genuine-BH-price-share KPI** — DONE (this branch). Of all PRODUCED prices, % genuine_bh vs converted_usd vs estimated, run-level + per-category. PRIMARY success dial (higher genuine = better). Extends the S3 L4.1 estimate-share thread.
- **E3 — OpenAI cost-guard** — NEXT. Full-200 capture drained the OpenAI account (insufficient_quota took prod down). Add OpenAI-budget awareness to the eval (refuse/warn if a run would exceed a safe budget), the way Serper is cost-guarded.
- **E2 — smoke20-only enforcement** — after E3. Ahmed wants full-200 avoided (token cost); make smoke20 the fast path, no full-200 without dispatcher GO.
- **E4 — Supabase DNS note** — persistence stays `--persist`-gated (getaddrinfo fails on this box); don't block on it.

## E1 shape (shipped this branch)
- `GENUINE_BH_SOURCE_METHODS = {local_bhd, page_scrape, page_scrape_rendered, firecrawl, scrapedo_rendered, shopify_json}` (shopify_json forward-compat for the Shopify adapter, tasks #14-16/#21).
- `count_price_provenance(body) -> {genuine_bh, converted_usd, estimated, priced}` (supersedes L4.1's `count_price_source_cells` in grade_run_result; the 3 buckets partition `priced`).
- `GradedQuery.{genuine_bh_price_cells, converted_usd_price_cells}` (+ existing estimated/priced).
- `EvalReport.{genuine_bh_price_cells_total, converted_usd_price_cells_total, genuine_bh_share, converted_usd_share, per_category_provenance}`.
- `aggregate`: run-level shares + per-category dict (zero-guarded, no ZeroDiv on empty/all-error).
- `_format_report`: genuine-BH-share PRIMARY line (ASCII-only separators — Windows cp1252 mojibake trap) + per-category breakdown.
- Per-query JSONL (`dataclasses.asdict`) + persist `metadata` jsonb get the new fields (no migration — schema-on-read).
- estimate_share (L4.1) PRESERVED for back-compat.

## E3 shape (shipped this branch)
- `OPENAI_CALLS_PER_QUERY=5` (parse+specs+price+reviews+verdict fan-out), `DEFAULT_OPENAI_CALL_BUDGET=150` (smoke20's 100 passes; full-200's 1000 refused), `EVAL_OPENAI_CALL_BUDGET` env override (fresh-read, malformed→default).
- `estimate_openai_calls(n)` + `check_openai_budget(n, budget, allow_overspend) -> (ok, msg)` (refuse / override-warn / near-warn / ok; ASCII-only messages).
- CLI `--openai-call-budget` + `--allow-openai-overspend`; pre-run gate in main() AFTER the Serper guard, returns 3 on refuse (pre-network). Static estimate (eval hits remote prod, can't read its live counter).

## E2 shape (shipped this branch)
- **Double-lock policy:** full-200 needs BOTH `--allow-full` (Serper) AND `--allow-openai-overspend` (OpenAI E3); smoke20 sails past both. main()-level tests assert the refusal paths (pre-network, return 3) + that smoke20/overridden-full reach run_eval (stubbed). This IS the "no full-200 without dispatcher GO" enforcement.

## E4 — DONE (no code change)
- Supabase persist stays `--persist`-gated (already optional in main(); getaddrinfo fails on this box). Noted, doesn't block. Eval runs sandbox-disabled when persistence is actually wanted.

## Status
- **E1 + E3 + E2 + E4 ALL DONE + GREEN.** 28 new TDD tests (E1 16 / E3 8 / E2 4); full test_eval_runner.py + test_eval_persistence.py + test_eval_gate.py = 82 passed. py_compile OK. CLI refusals eyeballed (Serper refuse, OpenAI refuse ~1000/150, ASCII-clean).
- **Commits:** E1 `b2be842`; E3+E2 (committing now).
- **Next:** lane complete — report to team-lead; ready for L5 smoke20 + gate.

## For L5's smoke20 (post-L1-batch)
The report now shows `genuine-BH-share -- X% GENUINE | converted_usd Y% | estimated Z%` (overall) + per-category, to quantify the rise vs the before-state (~60% estimate-share). No full-200; smoke20 is the loop.

## Blockers
- none

## Notes
- Did NOT touch the merged-in L3 `LANE_STATE.md` (shared-file artifact in main) — using this distinct file for my lane.
- E2/E3 sequencing: E1 (done, critical path) → E3 (cost-guard, the drain lesson) → E2 (smoke20-only).
