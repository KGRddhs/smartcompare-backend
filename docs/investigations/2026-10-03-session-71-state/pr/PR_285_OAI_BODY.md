## Summary
This PR makes four backend changes from the session-70 OAI_OBS spec, with its review corrections C1-C11 and the session-71 rulings OQ1-OQ7 and OR1-OR15. Every change ships unflagged. Only the deployed `app/` is touched.

1. **#265: the URL-extraction client now has a retry ceiling.**
   - `url_extraction_service.get_client` passes `max_retries=openai_max_retries()`.
   - The import is function-local, inside the `if _client is None:` branch. The other kwargs are unchanged.
   - The client is built once and cached, like `extraction_service.get_client`. All five `AsyncOpenAI` constructions now honour `OPENAI_MAX_RETRIES`.
2. **#268: the silent `DAILY_4O_CAP` downgrade is now visible.**
   - `ModelRouterService.daily_4o_cap()` reads env `DAILY_4O_CAP` on every call. Unset, blank, unparsable, `inf`/`nan` or a value below 1 falls back to the class constant 1,000,000. Anything else becomes `int(float(raw))`. The class constants are unchanged.
   - `get_model(priority="high")` logs exactly ONE INFO line per downgrade decision: `[MODEL_ROUTER] 4o cap reached: routing verdict to %s (used=%d cap=%d threshold=%.2f)`. It logs nothing otherwise.
   - On the success path only, `generate_comparison` sets `usage["model_downgraded"] = True` when the verdict ran on the standard model and the standard model differs from the configured verdict model. That covers both the cap downgrade and the 429/rate/quota fallback (OQ1). The failure path and the comparison dict are unchanged.
   - `StructuredComparisonService` carries that marker into the additive key `metadata.model_downgraded: true`, which is present only when true. It appears on the sync body and on the SSE `settle_complete` / `complete` events. The marker is reset at the start of every run. If a self-critique regeneration is served, the regenerated verdict's own value is used.
   - `GET /api/v1/admin/costs/gauges` now reads `ModelRouterService().daily_4o_cap()`, so the dashboard shows the cap the router uses.
3. **Empty-message Sentry issues.**
   - New leaf module `app/services/log_scrub.py`. Its only imports are `re` and `sentry_service._scrub_string`.
   - `safe_exc` is the R-W18 scrubber, moved verbatim from `structured_comparison_service`, which re-exports it as `_safe_exc`. Its output is unchanged.
   - `exc_summary(exc)` returns the exception type plus scrubbed text, never raises, and needs no `exc_info`. The order of steps:
     1. Strip URL userinfo, query and fragment.
     2. Redact the Sentry key shapes.
     3. Collapse line breaks to one line.
     4. Drop leading whitespace.
     5. Cut to 200 characters, always last.
   - The eight ERROR sites now log a constant %-template with `exc_summary(e)`: five in `serper_service`, plus `extract_specs`, `extract_price` and `extract_price_from_training_data`. The old message prefixes are kept, and every return value is byte-identical.
4. **`_GatheringFuture exception was never retrieved`.**
   - `_cancel_prefetched_direct` attaches the new module helper `_retrieve_prefetch_outcome` as a done-callback to every prefetch gather before `clear()`.
   - Nothing is awaited. Which futures are cancelled, and when, is unchanged.
5. **Docs** (`docs/runbooks/2026-09-02-openai-tpm-launch-sizing.md`):
   - The section 3 table row now says "all five" and includes `url_extraction_service.get_client`.
   - A section 3 sentence is corrected: every OpenAI client reads `OPENAI_MAX_RETRIES` when it is built. A change therefore needs a restart or redeploy; only the fallback ceiling is re-read per call.
   - New section 6, the daily gpt-4o cap. Every number in it is MODELLED. The complimentary allowance is tier-dependent (250K/day on Tier 1-2, 1M/day on Tier 3-5), and this org's tier and data-sharing enrolment are UNMEASURED.

## What changes at deploy with no new env set
- `/api/v1/url/*` page extraction now honours `OPENAI_MAX_RETRIES`. Because `OPENAI_MAX_RETRIES=1` is already live on `web` (since 2026-09-30), these calls go from 3 attempts to 2. This is intended.
- The new INFO line appears when the 80 % cap threshold is crossed.
- The additive key `metadata.model_downgraded` appears only when true. With the cap unset and no 429 fallback, responses are byte-identical to before.
- The eight error log lines now read `<prefix><TypeName>[: scrubbed text]`, for example `Search error: ReadTimeout` instead of `Search error: `. `record.msg` is the constant template, so Sentry groups one issue per template. For the shopping site, `gl` moves into a parameter.
- Prefetch cancellation no longer produces "never retrieved" reports.
- Routing, return values, timing bounds and cancellations are unchanged.

## Tests
- **Four RED-first files** (116 nodes): `tests/test_s70_url_client_retries.py`, `tests/test_s70_exc_summary_logs.py`, `tests/test_s70_prefetch_gather_retrieved.py`, `tests/test_s70_model_router_downgrade.py`. At base: 60 failed, 56 passed. At this head: 116 passed.
- **`tests/test_s70_fix_followups.py`** (9 nodes, from the fix round). It pins:
  - URL userinfo scrubbed when the URL is glued to a key shape (`Bearer https://u:p@h`, a JWT, or a 32+ hex run before `://`);
  - a one-line type name;
  - leading whitespace not using up the 200-character budget;
  - the per-run reset of the marker on both orchestrator paths.
  Reverting each fix makes its pin fail (5 mutants, all killed).

## Gates (bounded runner; one pytest at a time)
- The 4 RED files: 116 passed, with zero network attempts.
- The fix-pin file: 9 passed.
- The nine existing pin files: 191 passed. Two egress nodes, both in the netguard baseline.
- `tests/test_security_regression.py`: 104 passed.
- `tests/test_model_config.py`: 37 passed.
- `ruff --select E9,F63,F7,F82` and `py_compile` are clean.
- **Comm gate.** BASE is a detached worktree at `4bd5a09f`, running the 254-file module-reference set; HEAD runs 259 files.
  - BASE: 8751 passed, 2 failed.
  - HEAD: 8879 passed, 2 failed.
  - The same two `test_page_scraping` nodes fail on both sides, and both are listed in `tests/.pre_impl_failures.txt`.
  - `comm -13` (failures only on the branch) is EMPTY.
  - Netguard egress node sets are identical (173/173), and none belongs to a `test_s70_` file.
- **CI-order neighbourhood** (39 files in one process): 1284 passed, 1 xfailed.
- `git diff --stat` shows no whole-file rewrite.

## Orchestrator review (session 71)
- Process: RED by an Opus agent, gated PASS by the orchestrator; GREEN by an Opus agent; two Opus adversaries (correctness, regression), both SOUND with minors; a fix round; then the orchestrator read the diff.
- Ratified in the spec addendum (OR16-OR21): `exc_summary` runs the URL scrub BEFORE the key shapes. The spec had the opposite order, and the correctness adversary measured that a key-shape replacement glued to a URL then left the URL userinfo in the log line.
- Measured by name only on Railway `web`: `DAILY_4O_CAP` is absent, `OPENAI_MAX_RETRIES` is present. No value was read.
- The branch is fast-forwarded to main `eb86075e`. On that tree the five unit test files, the nine pin files, `test_ci_gates`, `test_model_config` and the security regression suite ran in one process: 500 passed.
- `app/services/log_scrub.py` and the five test files are committed with the unit. Three modules import `log_scrub` at module top.
- The CLAUDE.md lines (five constructions, the router line, the Sentry note) land in the session-71 docs PR.

## After deploy
- In Sentry, confirm ONE accumulating issue per template whose title reads `<prefix><TypeName>`, for example `Search error: ReadTimeout` or `Search error: ConnectError`.
- Then resolve the old per-text issues of the eight sites with a root-cause comment. That includes PYTHON-FASTAPI-N and -14, the Serper-403 "Search error" issues and the per-text "Specs extraction error" issues. Alert rules bound to the old issue ids stop firing.

## Stated limits
- `metadata.model_downgraded` is not carried on partial responses or on `/api/v1/url/compare`.
- The marker covers both the cap downgrade and the 429 fallback. The two are told apart only in the logs: the INFO line above versus the existing WARNING `[model_router] ... rate-limited mid-call`.
- The fallback trigger is a substring test on `'429'` / `'rate'` / `'quota'`, and `'rate'` also matches words such as "generate". The marker can therefore mark a fallback that followed a non-429 failure. This is pre-existing.
- The INFO line also fires for the Tier-3 synthesis `get_model("high")` call, so line counts overstate downgraded verdicts. Count the metadata key instead.
- `DAILY_4O_CAP` parsing: values below 1, commas, hex, `inf` and `nan` silently fall back to 1,000,000. `2e6` and `2_000_000` are accepted.
- The cap is TPM-blind. When Redis is down the counter reads 0, so cap protection is lost.
- `exc_summary` uses the existing Sentry patterns plus the R-W18 URL scrub. It does not redact these shapes (measured: never worse than base, which logged them raw):
  - legacy non-`proj` `sk-` keys;
  - JWTs whose header is under 20 characters;
  - lowercase `bearer`;
  - a scheme-less `//u:p@h`;
  - an unencoded space in a password.

## Follow-ups (not in this PR)
- The JWT pattern in `sentry_service._SENSITIVE_PATTERNS` is quadratic on repeated `eyJ` (pre-existing). Anchor it with a lookbehind. In the prod configuration this PR halves the synchronous scrub work on such input (measured).
- `cache_service._redis_get` logs an empty-text ERROR and does blocking I/O inside the async `get_model`.
- Discovery prefetch Tasks report "never retrieved" under a raising mock (OR4).

🤖 Generated with [Claude Code](https://claude.com/claude-code)