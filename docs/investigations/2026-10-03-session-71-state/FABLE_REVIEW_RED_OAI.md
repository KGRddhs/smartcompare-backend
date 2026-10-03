# Fable review gate — OAI/observability RED (synack-build-orchestrator Step 5.2), 2026-10-03

Reviewed in full (1,718 lines): `sc-s70-oai/tests/test_s70_url_client_retries.py` (`107b7b79…`, 116 lines), `test_s70_exc_summary_logs.py` (`b714ba46…`, 412), `test_s70_prefetch_gather_retrieved.py` (`2c9e279b…`, 507), `test_s70_model_router_downgrade.py` (`f905b305…`, 683), against `OAI_OBS_SPEC.md` as corrected (C1–C11) and ruled (OQ1–OQ7, OR1–OR15). Written by one Opus RED agent (`wf_15d14c45-c54`, 23 min) from four unverified files left by stopped agents.

**Verdict: PASS — GREEN may start (Opus).** No blocking issue; no GitHub issue filed.

Evidence the agent reported and I checked against the files:
- 116 nodes = 60 RED + 56 PIN. At BASE (detached scratch worktree at `4bd5a09f`) and at HEAD: `60 failed, 56 passed`, no collection errors, identical node/status/proving-line tables; `[netguard] blocked 0 attempt(s)`; the nine existing pin files 191 passed at HEAD; ruff tier + `py_compile` clean; ASCII-only, LF, every async test marked (pytest-asyncio strict mode).
- On-disk sha256 equals the report for all four files; no scratch worktree left.

What I verified by reading:
- **Item 1** (#265): default 2 (PIN), env 1/0 honoured (RED), explicit `max_retries` kwarg with the other three kwargs byte-identical (RED), cache-once semantics (PIN). Dummy key is not `sk-`-shaped.
- **Item 2** (#268): exact INFO text and one record per decision; nothing logged below the threshold or for non-high priority; per-call env read with the 0.80 boundary on both sides; the resolver accepts finite ≥ 1 values and rejects garbage, blanks, < 1, inf, nan; class constants pinned; the carrier on the SUCCESS usage dict for both causes (OQ1) and absent on the verdict model, on failure and when verdict == standard; `metadata.model_downgraded` on the sync body and on BOTH SSE terminal events with the stream deadline off and on; absent-not-false otherwise; the self-critique matrix (served regen wins, rejected regen and timeout keep the original); the admin gauge. SDK legs are mocked at `guarded_llm_create` / `chat.completions.create` (OR6). No forbidden contextvar rationale remains (OR8).
- **Item 3**: `exc_summary` shapes incl. `APITimeoutError`, Unicode separators, broken `__str__`, scrub-before-truncate; the leaf's imports; `scs._safe_exc is log_scrub.safe_exc`; a verbatim R-W18 reference pin; all EIGHT sites: constant `%`-template in `record.msg`, the summary last in `record.args`, exactly one ERROR record, no `exc_info`/stack (OR9), return values byte-identical (split PIN that runs at base, C3).
- **Item 4**: the C11-safe capture helper (strings only, settle + gc inside the handler scope), assertions on `context["message"]` only (OR7), three scenario REDs with 3 captures each at base, the helper contract, the cancellation-unchanged PIN, every LLM leg stubbed and asserted unreached (C4).

Deviations accepted:
- The `app.api.text_routes.log_search` stub in the pipeline harness (removes six sentinel-class `[netguard]` lines naming `test_s70_` nodes — required by C4's gate).
- The R4.2 requirement is pinned by an AST source-shape test because "every entry" and "every pending entry" are behaviourally indistinguishable (mutant M10 survived every behavioural test). It is brittle by design: GREEN implements exactly `for t in _prefetched_direct.values(): if not t.done(): t.cancel()` + a loop-level `t.add_done_callback(_retrieve_prefetch_outcome)` + `_prefetched_direct.clear()`.
- Module-top `os.environ.setdefault` lines removed (process-wide env mutation).
- The spec's garbage-cap test split into a RED resolver half and a PIN routing half; the no-marker test covers `sync | sse_off | sse_on`.
- The RED agent also ran a satisfiability prototype and five mutants in the scratch worktree only (restored by sha, worktree removed): beyond the RED role, harmless, and it proves the reds are satisfiable and non-vacuous.

Notes for GREEN (not blocking):
- Return values at the eight sites still carry raw `str(e)` (the spec forbids changing them in this unit; #226 tracks it). Do not "fix" that here.
- The site tests pin `record.args` exactly and patch `_serper_post`, `_active_serper_key`, `_serper_budget_ok`, `brightdata_service._brightdata_enabled`, `_llm_breaker.guarded_llm_create`, `extraction_service.get_client`: keep those names.
- `tests/test_model_config.py::TestNoStrayModelLiterals`: no quoted `gpt-…` literal in any `app/services/*.py`, including the router log line and `log_scrub.py`.
- The tests are frozen: GREEN edits a test only for a defect it can prove, reported as a deviation.
