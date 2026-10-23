# S81-05 ADVERSARY REPORT - lens: engineering

- Unit S81-05 REQUEST-CONTEXT (ENABLE_REQUEST_CONTEXT_HEADERS, lane B). Agent: Opus 5.5 adversary (engineering lens). Start 14:23 AST, end ~15:40 AST (2026-10-23).
- Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s05, branch feature/s81-s05-request-context, HEAD e9fd714868c4036f904e1f840e77cb217bf3c96e verified at start and end; `git status --short` empty at start and end (never edited).
- Scratch worktree <scratchpad>/S81-05_adv_engineering (detached at e9fd7148), git status empty after every probe and after the mutants, removed with `git worktree remove --force`; `git worktree list` no longer lists it.
- RED file tests/test_s81_s05_request_context.py: on-disk and committed sha256 b7a21c742174ab682968ce7dba1e5d6f3f7696b8c37afed116d0884d79fd6c83 (55,252 B, LF, ASCII); its first 52,230 bytes hash to the frozen ecdb579286f0cc1f19798b0349e5b001e982a8bff325282d5769584d4fb3a26d at start and at end, so GREEN's additions are a strict suffix (the p19 / p20 block + two helper tuples, GC-1 / GC-2, GC-10). No row edited.
- Box load: `node -e 0` 3.4-8.7 s during this review (the slow-spawn pathology); every timing below is load-inflated (the unit file took 69-77 s vs GREEN's 6-10 s).

## Verdict: SOUND (no blocking, no major; 7 minors, all documentation or measurement rulings)

## Diff hygiene (measured on the GREEN bytes)

- 9 files, +2025 / -5 (matches the PR body). The 5 deleted lines are all rewrites: auth_routes.py:35 (the regex becomes the leaf import), main.py:97 (comment, allowed by R-S05-5 / C8), CLAUDE.md :112 / :184 / the Optional env line (GC-8, spec 3.8). No unjustified deletion.
- Line endings: committed blobs are LF everywhere (no CR in `git diff`); working copy: existing files keep CRLF (main.py 631/631, auth_routes 1650/1650, _env_safety 291/291, test_retro_w1_9 534/534, black-clean-paths 60/60, CLAUDE.md 949/949), the three new files LF (D2, harmless: the index is LF either way). No whole-file diff.
- ASCII: the three new files 0 bytes > 127. Of the 2,025 added lines exactly one carries bytes > 127: the rewritten CLAUDE.md Optional-env line, whose 4 non-ASCII characters are the pre-existing em-dashes (new-only non-ASCII set empty). CLAUDE.md 3961 -> 3946 high bytes (the five :112 arrows became `->`), as GREEN reports.
- Added-line sweep: no @gmail / +973 / sk- / eyJ / PEM / credentialed-URL shape; the only 8-digit runs are the HSTS `max-age=31536000` literals in the frozen P4 records. gitleaks 8.30.1 over 84c861f6..e9fd7148 with .gitleaks.toml: "no leaks found" (1 commit, ~79.5 KB). The test file builds its pepper by concatenation and its fingerprints as "ab"*32 / "cd"*32 (low entropy).
- Imports: the leaf imports only stdlib (hashlib, hmac, logging, os, re, threading, uuid, contextvars, typing + `from __future__ import annotations`) = the spec 2.2 list; the middleware imports only the leaf; main.py gains one import (after the ErrorHandler import, spec 3.4); auth_routes gains only the leaf import (spec 3.2 text byte for byte). No requirements / client / migration / .githooks / processors.json / legal / .pre_impl_failures change.
- File shas on disk equal the GREEN report table for all 9 files (leaf ae5bc868..., middleware d6f06adf..., main 5b55a9cd..., auth_routes 0ee900c9..., _env_safety cba3121f..., test_retro_w1_9 0f058258..., black-clean-paths b9b2ad87..., CLAUDE.md c0db5378..., RED b7a21c74...).
- black-clean-paths: the three entries are in sorted position; black 26.5.1 `--check --config pyproject.toml` on the three new files: "3 files would be left unchanged".
- ruff `--select E9,F63,F7,F82 --no-cache` on the 7 Python files: All checks passed. py_compile on the 7 files: OK.
- GREEN's mutation record (mutation_results_partial.json): 53 entries, 52 KILLED, 1 SURVIVED = X16, restore sha ok on all 53; consistent with the report and the PR body. No .qa-mutation.lock left in the GREEN worktree.

## Comm set re-derivation (union rule) vs GREEN's 210-file list

Re-derived independently over tests/test_*.py at HEAD with the classes GREEN's regexes do not cover, then subtracted GREEN's list:
- `Path(...).glob(` walkers: 15 files, 4 outside the list (test_migration_042, test_migration_044, test_platform_router, test_skill_frontmatter): they glob migrations/, fixtures, _proof and skills, never app/.
- `ast.parse` readers: 34 files, 10 outside the list; each parses one named unedited app/services module (structured_comparison_service, usage_service, log_scrub, price_service via `__file__`, push_service, prompt_personalities / extraction_service, the two genuine-price files over app/services specific modules).
- path-segment readers (`/ "app" / ...`): 10 outside the list, each reads one unedited services file or app/config.py.
- os.listdir / scandir: 0; `.github` readers outside the list: 0; `user_middleware` / `middleware_stack` / `add_middleware` / `allow_headers` / openapi / X-Request-ID readers outside the list: 0; pkgutil walkers: 0.
- tests/conftest.py defines no client fixture importing app.main; the helper modules (_route_introspection, _hermeticity, _netguard, _tokenizer, _bundle_c_helpers, _retro_r_mig_sql, w4_11 recorder) import no edited module (only _env_safety and _netguard -> _env_safety.live_mode_enabled, unchanged; conftest runs for every test anyway). tests/_env_safety.py importers / CREDENTIALS_UNSET readers are in the list.
- Migration / manifest readers are not owed by the union rule (no migration, processors.json or legal text change); I ran the legal and migration-predicate readers anyway (srcpins below).
- Result: NO missing file. GREEN's list is complete; its regex set (minor m5) is narrower than the rule text but the gap holds no relevant reader.

## Runs (every [pyt] line; one pytest at a time, scratch worktree)

- unit ON: `[pyt] tag=s05e-unit-on start=2026-10-23 14:43:05 end=2026-10-23 14:44:24 elapsed=79s bound=600s status=OK rc=0` 173 passed; [hermeticity] sentinel checked 173 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- unit OFF: `[pyt] tag=s05e-unit-off start=2026-10-23 14:44:30 end=2026-10-23 14:46:22 elapsed=111s bound=600s status=OK rc=0` 173 passed; [hermeticity] 173; [netguard] blocked 0
- CI-order set (GREEN's 16 files, alphabetical, one call): `[pyt] tag=s05e-ciorder start=2026-10-23 14:49:56 end=2026-10-23 15:00:45 elapsed=649s bound=1200s status=FAIL rc=1` - a MEASUREMENT failure: pytest-timeout (thread method, 120 s per test) killed the process inside tests/test_conftest_env_safety.py::test_app_main_still_imports_under_the_sentinels (a subprocess import of app.main) after one F in that file's subprocess-driven nodes; no summary, no [hermeticity] / [netguard] line (process killed). Re-run once, split in two calls (deviation: the whole set again would hit the same per-test timeout under this load):
  - `[pyt] tag=s05e-ciorder2-noenv start=2026-10-23 15:02:47 end=2026-10-23 15:08:58 elapsed=370s bound=1200s status=OK rc=0` (the 15 other files) 876 passed; [hermeticity] sentinel checked 876 test(s); [netguard] blocked 16 attempt(s) from 10 node(s) (= GREEN's 16 / 10)
  - `[pyt] tag=s05e-envsafety start=2026-10-23 15:17:28 end=2026-10-23 15:18:15 elapsed=47s bound=1200s status=OK rc=0` tests/test_conftest_env_safety.py 24 passed, 1 skipped, 2 deselected; [hermeticity] 25; [netguard] blocked 0
  - Together 900 passed + 1 skipped = GREEN's CI-order totals (900 passed, 1 skipped, 2 deselected). The E1 EXPECTED_STACK nodes (test_retro_w1_9), T23 (fixture not re-recorded), FY25, W4-13, test_m13_01, test_ci_gates and test_behavior_dimension_translation (the two CLAUDE.md readers) all green.
- source-scanning pins + manifest readers: `[pyt] tag=s05e-srcpins start=2026-10-23 15:09:08 end=2026-10-23 15:10:27 elapsed=79s bound=1200s status=OK rc=0` 386 passed; [hermeticity] 386; [netguard] blocked 0 (test_legal_disclosure_s77, test_legal_docs_u8, test_legal_docs_u8_polish, test_legal_s78, test_migration_index_predicate_immutability, test_model_config, test_model_config_enforced, test_openai_key_log_hygiene_s69, test_prompt_fence, test_start_command, test_u3c_store_false_pin; test_sentry_channels_u8d_unit ran in the CI-order set).
- comm chunk c00 (GREEN chunk_00, 14 files): `[pyt] tag=s05e-comm-c00 start=2026-10-23 15:10:38 end=2026-10-23 15:12:01 elapsed=82s bound=1200s status=OK rc=0` 447 passed; [hermeticity] 447; [netguard] blocked 0 (= GREEN 447)
- comm chunk c12 (14 files: security_middleware, security_regression, sentry u8d x2, share_routes, social_login fingerprint + smoke, start_command, ...): `[pyt] tag=s05e-comm-c12 start=2026-10-23 15:12:06 end=2026-10-23 15:14:35 elapsed=149s bound=1200s status=OK rc=0` 612 passed, 1 skipped, 8 deselected; [hermeticity] 613; [netguard] blocked 14 attempt(s) from 8 node(s) (= GREEN)
- comm chunk c06 (14 files: legal_routes, legal_s78, limiter_endpoint_key, m13_01/02/03/05/21/25/26/28/29, ...): `[pyt] tag=s05e-comm-c06 start=2026-10-23 15:19:18 end=2026-10-23 15:22:37 elapsed=198s bound=1200s status=OK rc=0` 132 passed; [hermeticity] 132; [netguard] blocked 3 attempt(s) from 3 node(s) (= GREEN)
- Three comm chunks: branch failures vs GREEN's head record: identical (0 failed in each); no base re-run needed.
- collect: `[pyt] tag=s05e-collect start=2026-10-23 15:18:18 end=2026-10-23 15:19:01 elapsed=43s bound=600s status=OK rc=0` 173 nodes; per-row counts equal every count in the PR body table (r01 13, r02 5, r03 19, r04 3, r05 11, r06 3, r07 15, r09 2, r10 4, r11 11, r13 7, r15 4, r16 9, r17 2 + nested = 3, r18 6, r19 2, r20_atomic 3, r20_bind_is_total 8, r22 7, r25 4, r26 2, p04 8, p05 4, p19 3, p20 3; singles 1); R = 149, P = 18 + 6.
- hook black nodes (own calls, test_precommit_hook.py -k black, 4 nodes): run 1 `[pyt] tag=s05e-hook-black start=2026-10-23 15:22:55 end=2026-10-23 15:25:12 elapsed=137s bound=1200s status=FAIL rc=1` (pytest-timeout 120 s kill in the first node, inside the hook subprocess; no summary); re-run once alone `[pyt] tag=s05e-hook-black start=2026-10-23 15:27:08 end=2026-10-23 15:34:10 elapsed=421s bound=1200s status=FAIL rc=1` 4 failed, all `subprocess.TimeoutExpired: ... .githooks/pre-commit timed out after 90 seconds` (sh and dash), no AssertionError; [hermeticity] 4; [netguard] blocked 0. NOT MEASURED (two timeout-class failures under box load); GREEN's `[pyt] tag=s05g-hook-black ... status=OK rc=0` (4 passed, 12:57) and the commit made through the hook remain the only measurements.

## Mutants applied by hand (scratch worktree, byte copy -> exact edit matching once (EOL-normalised) -> killing rows via pyt.py -k -> restore -> sha256 compare; .qa-mutation.lock held in the scratch worktree and removed; every restore sha-equal)

| id | mutant | result | killed by |
|---|---|---|---|
| ME1 | RequestContext added AFTER the CORS add (not innermost) | KILLED (11 failed) | r25 stack_registration, TestW19cFlagOffIdentity (E1) |
| ME2 | registration gated on the flag at import | KILLED (11) | r25, r26, TestW19cFlagOffIdentity |
| ME3 | auth_routes compiles its own regex again | KILLED (1) | r08 one_regex_object |
| ME4 | DEVICE_KEY_PEPPER removed from CREDENTIALS_UNSET | KILLED (1) | r27 |
| ME5 | the leaf dropped from black-clean-paths | KILLED (1) | r28 |
| ME6 | dict(scope) passed downstream on the ON path | KILLED (1) | r23 flag_on_reads_flag_once |
| ME7 | scope type read before the flag | KILLED (7) | r22 flag_off_reads_nothing (all 7 states) |
| ME8 | HMAC keyed with the unstripped pepper | KILLED (1) | r09[padded] |
| ME9 | reset outside finally | KILLED (1) | r17[raises] |
| ME10 | flag cached at middleware import | KILLED (1) | r26[true] |

All failures are assertion failures (0 ERROR lines, 0 non-assertion E lines). Per-mutant [pyt] lines are in <scratchpad>/S81-05_adv/mutants_eng.json and mut_logs/ (e.g. `[pyt] tag=s05e-ME1-not-innermost start=2026-10-23 15:14:46 end=2026-10-23 15:15:20 elapsed=34s bound=600s status=FAIL rc=1`, ..., `[pyt] tag=s05e-ME10-import-time-flag start=2026-10-23 15:17:12 end=2026-10-23 15:17:22 elapsed=10s bound=600s status=FAIL rc=1`). Note: ME6, ME8, ME9 and ME10 are each killed by exactly one node (thin, but real assertion kills; not prove-nothing).

## Claims probed against the code (CLAUDE.md row, :112, PR body)

- Stack order (outermost first) RequestID -> SecurityHeaders -> ErrorHandler -> [SlowAPIASGI under ENABLE_DEFAULT_RATE_LIMITS] -> CORS -> RequestContext: matches the add order in app/main.py (RequestContext added first, RequestID last). TRUE.
- "the @limiter.limit decorators, the exception handlers, the dependencies and the routes run inside it": main.py registers handlers only for HTTPException, RequestValidationError and RateLimitExceeded (Starlette ExceptionMiddleware, inside the user middleware); no Exception/500 handler (which would sit on ServerErrorMiddleware, outside). TRUE.
- ContextVar rule: redis_offloop.py:104 and price_service.py:4503 use contextvars.copy_context(); anyio 4.14.2 run_sync_in_worker_thread copies the context (_asyncio.py:2633 / :1033), so Starlette's threadpool and sync streaming generators see the values; app/utils/executor.py installs a plain ThreadPoolExecutor via loop.set_default_executor (run_in_executor does not copy). TRUE.
- Share path `/api/v1/referrals/share` carries `device_fingerprint_hash` in the JSON body (referral_routes.py:75 / :117 / :176). TRUE. CORS allow_headers = Authorization, Content-Type, X-Admin-Key, X-Request-ID (unchanged). TRUE.
- Flag OFF = one os.getenv and no scope read: `if not request_context_headers_enabled() or scope.get("type") != "http"` short-circuits before the scope read. TRUE (ME7 pins it).
- The two auth_interceptor base failures named in the comm records are rows 88-89 of tests/.pre_impl_failures.txt (CI deselects them). TRUE.
- Comm totals in the PR body (9,318 passed, 2 failed, 33 skipped, 35 xfailed, 79 deselected over 15 chunks of 14 = 210 files) re-add from the 15 chunk lines. TRUE.

## Minors (documentation / measurement rulings for the orchestrator)

- m1 CLAUDE.md S81-05 row, **Canary**: "watch for the single WARNING line (it means the pepper is missing)" cannot fire in this unit's window: the WARNING is emitted only inside device_key(), which nothing calls until S81-09 (p01 pins no consumer). A missing DEVICE_KEY_PEPPER is therefore silent at the S81-05 flip; reword to "the WARNING can appear only once a consumer (S81-09) calls device_key; confirm DEVICE_KEY_PEPPER by name before that consumer flips".
- m2 PR body "Flag OFF and ON are byte-identical on every response (P4 against base literals in four states)": P4 measures two envelopes (401, 404) in four states; "every response" holds by construction (the identical scope / receive / send objects, pinned by r22 / r23), not by P4. Reword to say which part is measured.
- m3 app/main.py S81-05 comment (spec 3.4 verbatim): "SlowAPI / ErrorHandler / SecurityHeaders / CORS run outside the ContextVar scope" - "SlowAPI" is the conditional SlowAPIASGIMiddleware; the slowapi @limiter.limit decorators run INSIDE the scope (CLAUDE.md :112 states this correctly). Optional wording fix ("SlowAPIASGI (when enabled)").
- m4 precision: the row and the leaf docstring say the flag is read "once per HTTP request"; it is read once per ASGI call of every scope type (lifespan and websocket included, by design: flag first). Harmless.
- m5 harness: GREEN's build_comm_head.py regexes do not cover `Path.glob(` walkers, `/ "app" / ...` path-segment readers or bare `ast.parse(read_text)` readers named in the union rule; re-derived here with those classes: no missing file (every such reader targets an unedited single module). Record for the derivation script, no unit change.
- m6 measurement: the CI-order set as one call FAILED under box load (per-test 120 s timeout in test_conftest_env_safety's subprocess import of app.main); the split re-run (876 + 25 nodes) is green and equals GREEN's totals. Not a product defect.
- m7 NOT MEASURED: tests/test_precommit_hook.py -k black (4 nodes) timed out twice under load (pytest-timeout, then the hook subprocess's own 90 s TimeoutExpired); re-run on an idle box before the PR if the orchestrator wants a second measurement.

## Prove-nothing rows

None found from this lens (every engineering mutant is killed by an assertion; the four single-node kills are listed above).

## Not done / NOT MEASURED

- Hook black nodes (m7). The other 11 GREEN comm chunks were not re-run (three chosen: c00, c06, c12). G6 flag-ON identity set not re-run (the unit file was run ON and OFF). The rebase onto the moved origin/main (S81-03 #369 merged) is not this agent's step: expect the CLAUDE.md flag-row anchor union and the FY25 base re-take (GC-10, GREEN Q1).
- Files written (notes folder only): engineering_REPORT.md, notes.md, mutate_eng.py, seq.sh, count_nodes.py (written, NOT run: it would import app.main outside conftest), claude_diff.txt, mutants_eng.json, mut_backup/, mut_logs/, *.log, seq*.out.
