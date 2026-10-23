# S81-05 RED REPORT (REQUEST-CONTEXT, ENABLE_REQUEST_CONTEXT_HEADERS, lane B)

- Agent: RED, Opus 5.5. Start 2026-10-23 08:13 AST, end ~09:35 AST.
- Real worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s05, HEAD 84c861f68ba3b23606c69ce2d1f78597e2f3037b (detached), unchanged.
- Notes folder: <scratchpad>/S05_red/ (notes.md, logs, mutation logs + junit xml, comm lists, prototype copies).
- Inputs read in full: s81-common.txt, S81-05_UNIT_SPEC.md, S81-05_SPEC_REVIEW.md, RULINGS_S81_05.md, PLAN_S81 sections 0/1 + M1 S81-05 text, RULINGS_R0 headers.
- Step (2) "files the review listed as not measured": the list in the task text is EMPTY; the review's "not re-run" items (the full 1.10 pin set and the comm chunks) are covered by the comm run at base below (it contains every 1.10 pin file).

## Files written

| path | sha256 | bytes | notes |
|---|---|---|---|
| tests/test_s81_s05_request_context.py (real worktree, untracked) | ecdb579286f0cc1f19798b0349e5b001e982a8bff325282d5769584d4fb3a26d | 52230 | pure ASCII (0 bytes > 127), LF (0 CR), black 26.5.1 --check clean (pyproject config), ruff E9/F63/F7/F82 clean, py_compile OK |

Nothing else written in the real worktree. `git status --short` = `?? tests/test_s81_s05_request_context.py`.

## Row inventory (167 nodes)

RED (149 nodes, 30 functions): r01 flag reader x13, r02 consent valid x5, r03 consent invalid x19, r04 fp valid x3, r05 fp invalid x11, r06 request id valid x3 (lower/upper/mixed, R-S05-2), r07 request id invalid x15, r08 one regex object (identity + AST), r09 HMAC x2, r10 fail closed + latch x4, r11 invalid fp no pepper read x11, r12 pepper never leaks, r13 header_state x7 (R-S05-3), r14 defaults, r15 binds inside x4, r16 malformed none + no log x9, r17 reset return/raise x2 + nested, r18 first occurrence x6, r19 non-http x2, r20 bind total x8 + atomic bind x3 (R-S05-4 / C2), r21 concurrency (two barriers), r22 flag OFF reads nothing x7 (full config + getenv/bind/reset recorders + C11 ScopeSpy), r23 flag ON reads flag once, r24 AST no-log, r25 stack registration x4 (R-S05-5), r26 end-to-end via httpx.ASGITransport in one asyncio.run (C3) x2, r27 pepper in CREDENTIALS_UNSET, r28 black ratchet entries (R-S05-8).
PIN (18 nodes): p01 no consumer in app/ + scripts/, p02 OpenAPI declares no context header, p03 CORS kwargs literal, p04 response bytes literal x8 (401 + 404 x states a/b/c/d, R-S05-9), p05 no header value logged x4, p06 fp readers unchanged, p07 route header reads untouched, p08 no legacy_hash / device_lookup_keys anywhere (R-S05-1).

## Runs (every [pyt] line)

P4 literal recording at base (scratch worktree, recording hook only in that copy; removed before the frozen file):
- `[pyt] tag=s05-p4rec1 start=2026-10-23 08:25:39 end=2026-10-23 08:25:47 elapsed=8s bound=600s status=FAIL rc=1` (placeholder dict, recording run) [netguard] blocked 0, [hermeticity] 8
- `[pyt] tag=s05-p4rec2 start=2026-10-23 08:26:10 end=2026-10-23 08:26:16 elapsed=5s bound=600s status=FAIL rc=1` ; the two record files `cmp` IDENTICAL; all four states equal per path.

Unit file at base, REAL worktree (step 4):
- first: `[pyt] tag=s05-red-base start=2026-10-23 08:28:37 end=2026-10-23 08:28:53 elapsed=15s bound=600s status=FAIL rc=1` 149 failed, 18 passed
- final bytes: `[pyt] tag=s05-red-base2 start=2026-10-23 08:48:48 end=2026-10-23 08:49:25 elapsed=38s bound=600s status=FAIL rc=1` -> `149 failed, 18 passed, 41 warnings in 32.24s`; `[hermeticity] sentinel checked 167 test(s)`; `[netguard] blocked 0 attempt(s) from 0 node(s)`.
- every failure is an AssertionError: 149 `E   AssertionError` lines, 0 other `E ...Error/Exception` lines; 149/149 failed ids are test_s05_r* and 0 are test_s05_p*; failed id list: <scratchpad>/S05_red/red_base_failed.txt.

Prototype (scratch worktree `git worktree add --detach <notes>/S81-05_scratch 84c861f6`, leaf + middleware + 4 edits: auth_routes re-import, main.py import + innermost registration, _env_safety pepper, black-clean-paths 3 entries):
- `[pyt] tag=s05-proto-on start=2026-10-23 08:30:44 end=2026-10-23 08:30:53 elapsed=9s bound=600s status=OK rc=0` 167 passed (ENABLE_REQUEST_CONTEXT_HEADERS=true exported for that call)
- `[pyt] tag=s05-proto-off start=2026-10-23 08:31:06 end=2026-10-23 08:31:12 elapsed=6s bound=600s status=OK rc=0` 167 passed (flag unset)
- `[pyt] tag=s05-proto-pins start=2026-10-23 08:31:14 end=2026-10-23 08:31:19 elapsed=5s bound=600s status=OK rc=0` 18 passed, 149 deselected
- E1 probe: `[pyt] tag=s05-proto-e1 start=2026-10-23 08:31:34 end=2026-10-23 08:31:59 elapsed=25s bound=600s status=FAIL rc=1` over test_retro_w1_9 + test_conftest_env_safety + test_social_login_device_fingerprint + test_auth_routes_invite_fingerprint: 7 failed, 91 passed, 1 skipped = exactly the 7 E1 nodes (TestW19cFlagOffIdentity::test_imported_app_has_no_rate_limit_middleware, ::test_fresh_exec_flag_off_matches_the_imported_app, ::test_falsy_flag_values_register_nothing[ /0/false/off/no]); netguard 2 baseline nodes (test_auth_routes_invite_fingerprint x2, sentinel neutralized.supabase.invalid).
- `[pyt] tag=s05-proto-on2 start=2026-10-23 08:35:37 end=2026-10-23 08:35:43 elapsed=6s bound=600s status=OK rc=0` (after the R20 wrapping)
- `[pyt] tag=s05-proto-on3 start=2026-10-23 08:47:27 end=2026-10-23 08:48:01 elapsed=34s bound=600s status=OK rc=0` (after the R21 strengthening)
- final bytes ON: `[pyt] tag=s05-proto-final-on start=2026-10-23 08:50:02 end=2026-10-23 08:50:32 elapsed=30s bound=600s status=OK rc=0` -> 167 passed; [hermeticity] 167; [netguard] 0
- final bytes OFF: `[pyt] tag=s05-proto-final-off start=2026-10-23 08:50:35 end=2026-10-23 08:50:58 elapsed=23s bound=600s status=OK rc=0` -> 167 passed; [hermeticity] 167; [netguard] 0
- Flag-OFF byte identity on the prototype: p04 (all 8 nodes) equal the base literals in states a (unset), b (false + pepper + valid headers), c (true + pepper + valid headers), d (true + malformed headers).
- Prototype shas (copies in <scratchpad>/S05_red/proto_final/): app/utils/request_context.py 275b6213..., app/middleware/request_context.py 9b386b34..., app/main.py 5c9bbb88..., app/api/auth_routes.py 0ee900c9..., tests/_env_safety.py cba3121f..., .github/black-clean-paths.txt 0e1e7a26...; scratch `git diff --stat`: 4 files, 9 insertions, 1 deletion.

## Mutation table (47 mutants; byte copy -> exact edit matching once -> whole unit file through pyt.py bound 600 -> restore -> sha256 compare; .qa-mutation.lock created/removed; KILLED = failures that are all assertion failures per junit xml, 0 errors)

| id | mutant | result | failed nodes | killing tests (rows) |
|---|---|---|---|---|
| X1 | flag reader without strip | KILLED | 1 | r01_flag_reader_per_call |
| X2 | flag default true | KILLED | 15 | r01, r22, r26 |
| X3 | scope type read before the flag | KILLED | 7 | r22 |
| X4 | flag check removed (always bind) | KILLED | 9 | r22, r23, r26 |
| X5 | reset removed from finally | KILLED | 13 | r13, r17 nested, r17 return/raise, r20 atomic, r23 |
| X6 | reset after the call, not in finally | KILLED | 1 | r17[raises] |
| X7 | http-only check removed | KILLED | 2 | r19 |
| X8 | downstream gets a wrapped send | KILLED | 4 | r15 |
| X9 | consent regex \d | KILLED | 2 | r03 |
| X10 | consent up to 4 digits | KILLED | 2 | r03, r16 |
| X11 | consent via int() not regex | KILLED | 10 | r03 |
| X12 | fp fullmatch -> match | KILLED | 2 | r05, r11 |
| X13 | fp regex re.I | KILLED | 5 | p06, r05, r08, r11, r16 |
| X14 | uuid without version=4 | KILLED | 4 | r07 |
| X15 | request id not lower-cased (R-S05-2 flip of the spec's X15) | KILLED | 3 | r06, r13 |
| X16 | len == 36 pre-check removed | SURVIVED | 0 | EQUIVALENT BY RULING R-S05-11 |
| X17 | last occurrence wins | KILLED | 7 | r13, r18 |
| X18 | bind try/except removed | KILLED | 10 | r20 atomic, r20 total |
| X19 | module globals instead of ContextVars | KILLED | 10 | r21, r22, r26 |
| X20 | pepper unset -> sha256 fallback (fail open) | KILLED | 5 | r10, r12 |
| X21 | device_key skips the fingerprint parse | KILLED | 8 | r11 |
| X22 | blank pepper not stripped | KILLED | 2 | r10 |
| X23 | warning latch removed | KILLED | 4 | r10 |
| X24 | warning carries the fingerprint | KILLED | 5 | r10, r24 |
| X25 | sha1 instead of sha256 | KILLED | 3 | r09, r26 |
| X25b | HMAC key and message swapped | KILLED | 3 | r09, r26 |
| X26s | header states not reset after the request (new; spec X26 dropped by R-S05-1) | KILLED | 12 | r13, r17 nested, r17 return/raise, r20 atomic |
| X27s | except arm states absent, not malformed (new; spec X27 dropped) | KILLED | 3 | r20 atomic |
| X28 | registration wrapped in the flag | KILLED | 4 | r25, r26 |
| X29 | registered outermost (after RequestID) | KILLED | 4 | r25 |
| XNI | NOT-INNERMOST: added after the CORS add | KILLED | 4 | r25 |
| X30 | middleware logs the headers | KILLED | 12 | p05, r16, r24 |
| X31 | planted consumer in usage_service | KILLED | 1 | p01 |
| X32 | pepper dropped from CREDENTIALS_UNSET | KILLED | 1 | r27 |
| X33 | auth_routes compiles its own regex again | KILLED | 1 | r08 (AST half; identity half cannot, see deviation D2) |
| X34 | scope copied before downstream | KILLED | 5 | r15, r23 |
| X35 | CORS allow_headers widened | KILLED | 1 | p03 |
| X36 | flag read once at import | KILLED | 42 | r01, r13, r15, r17, r18, r20, r21, r22, r23, r26 |
| X37 | middleware computes a device key per request | KILLED | 4 | p01, r20 atomic, r23, r24 |
| X38 | set each ContextVar as its header parses (C2 leak) | KILLED | 2 | r20 atomic[parse_device_fingerprint], [parse_compare_request_id] |
| XHL | HEADER-LOGGED: leaf logs each header value | KILLED | 12 | p05, r16, r24 |
| XSLV | STATE-LEAKS-VALUE: header_state returns the raw value | KILLED | 4 | r13 |
| X40 | header_state default None, not absent | KILLED | 23 | r13, r14, r17, r20, r22, r26 |
| X43 | device_fingerprint() reads the request-id var | KILLED | 14 | r13, r15, r17, r18, r21, r23, r26 |
| X44 | a new file missing from the black ratchet | KILLED | 1 | r28 |
| X45 | consent value stripped before the match | KILLED | 3 | r03 |
| X46 | request id accepts non-str via str() | KILLED | 1 | r07 |

Counts: 47 mutants, 46 KILLED (all assertion failures, 0 non-assertion kinds, 0 errors), 1 SURVIVED = X16 (equivalent by ruling R-S05-11). Every restore sha-verified (harness aborts on mismatch; none). Raw results: <scratchpad>/S05_red/mutation_results.json (+ _partial.json for the X19 re-run), per-mutant logs + junit xml <scratchpad>/S05_red/mut_logs/, harness <scratchpad>/S05_red/proto/mutate.py. Byte version: 46 mutants ran 08:38-08:46 against the RED file before the R21 strengthening (the only byte difference to the frozen file is the R21 body: one barrier -> two barriers); X19 re-ran on the final bytes (killed by r21/r22/r26). The 46 killing sets do not depend on the R21 body except where r21 is listed beside other killers (X36, X43).

## Comm set at base (REAL worktree, flag unset, one runner call per chunk, bound 1200)

List: <scratchpad>/S05_red/comm_files.txt (187 files), reasons TSV <scratchpad>/S05_red/comm_files.tsv, chunks <scratchpad>/S05_red/comm/chunk_00..07, builder <scratchpad>/S05_red/build_comm.py. Union = (a) reference grep over tests/test_*.py for app.main, app.middleware, auth_routes, _env_safety/CREDENTIALS_UNSET/neutralize_credentials, test_retro_w1_9, app.utils, request_context/RequestContextMiddleware, black-clean-paths, _DEVICE_FINGERPRINT_RE; (b) source-scanning pins (the named list + every rglob/os.walk/glob("app/iterdir/glob.glob walker + test_start_command*); (c) CLAUDE.md readers; (d) T23/FY25/W4-13; UNION the spec's 150-file list (all 150 included; +37 = the reviewer's 187). EXCLUDED: the four test_precommit_hook*.py; the new RED file (head add); NETWORK_FLAKY_EXCLUDE node `tests/test_rate_limiting_complete.py::TestRateLimitCoverage::test_prices_endpoint_rate_limited` deselected (the other three flaky nodes live in files not in the set). SmartCompareApp-scanning tests not added: the unit changes no client file and no client-visible byte (P4/p05 pin it).

- two rc=4 usage errors first (CR in the chunk files; [pyt] tag=s05-redcomm-base-c00 08:53:27 rc=4, c01 08:53:43 rc=4; fixed, re-run)
- c00 `[pyt] tag=s05-redcomm-base-c00 start=2026-10-23 08:54:26 end=2026-10-23 08:56:22 elapsed=116s bound=1200s status=FAIL rc=1` 2 failed, 986 passed; [hermeticity] 988; [netguard] blocked 19 attempt(s) from 8 node(s); FAILED tests/test_auth_interceptor.py::test_sign_in_with_social_exception, ::test_social_login_user_insert_fails_gracefully (tests/.pre_impl_failures.txt:88-89, known reds)
- c01 `[pyt] tag=s05-redcomm-base-c01 start=2026-10-23 08:56:36 end=2026-10-23 08:57:36 elapsed=60s bound=1200s status=OK rc=0` 968 passed, 1 skipped, 47 deselected; [hermeticity] 969; [netguard] blocked 11 attempt(s) from 7 node(s)
- c02 `[pyt] tag=s05-redcomm-base-c02 start=2026-10-23 08:57:51 end=2026-10-23 09:09:25 elapsed=693s bound=1200s status=OK rc=0` 1641 passed, 9 deselected; [hermeticity] 1641; [netguard] blocked 57 attempt(s) from 38 node(s) (the hermeticity_pins self-tests + baseline sentinel nodes)
- c03 `[pyt] tag=s05-redcomm-base-c03 start=2026-10-23 09:09:50 end=2026-10-23 09:11:24 elapsed=93s bound=1200s status=OK rc=0` 442 passed, 10 deselected; [hermeticity] 442; [netguard] blocked 3 attempt(s) from 3 node(s)
- c04 `[pyt] tag=s05-redcomm-base-c04 start=2026-10-23 09:12:20 end=2026-10-23 09:17:00 elapsed=280s bound=1200s status=OK rc=0` 796 passed, 1 skipped, 1 deselected; [hermeticity] 796; [netguard] blocked 115 attempt(s) from 20 node(s)
- c05 `[pyt] tag=s05-redcomm-base-c05 start=2026-10-23 09:17:32 end=2026-10-23 09:23:50 elapsed=378s bound=1200s status=OK rc=0` 2249 passed; [hermeticity] 2249; [netguard] blocked 4 attempt(s) from 2 node(s)
- c06 `[pyt] tag=s05-redcomm-base-c06 start=2026-10-23 09:24:32 end=2026-10-23 09:28:17 elapsed=225s bound=1200s status=OK rc=0` 988 passed, 10 deselected; [hermeticity] 988; [netguard] blocked 144 attempt(s) from 66 node(s)
- c07 `[pyt] tag=s05-redcomm-base-c07 start=2026-10-23 09:28:57 end=2026-10-23 09:29:45 elapsed=47s bound=1200s status=OK rc=0` 592 passed, 9 skipped, 35 xfailed; [hermeticity] 636; [netguard] blocked 8 attempt(s) from 8 node(s)
- Total: 8,662 passed, 2 failed, 11 skipped, 35 xfailed (test_value_math). Base FAILED set (<scratchpad>/S05_red/comm_base_failed.txt) = the two test_auth_interceptor nodes = exactly spec 1.10's base set. No TIMEOUT.
- Box load: `node -e 0` measured 5.6 s at 09:08 (slow-spawn pathology; c02 took 693 s for 1641 nodes). All gates still completed inside their bounds.

## Restore check

- `restore_check.py`: all 3413 tracked files of the real worktree byte-equal (sha256) to a pristine base checkout (the scratch worktree; the four prototype-edited files compared against their pre-prototype byte copies): `tracked 3413 checked 3413 mismatch 0` (run before and after the comm set).
- Real worktree HEAD 84c861f68ba3b23606c69ce2d1f78597e2f3037b; `git status --short` = `?? tests/test_s81_s05_request_context.py` only.
- Scratch worktree removed with `git worktree remove --force` (no node_modules / junction inside); `git worktree list` no longer lists it; directory gone. No .qa-mutation.lock left. No orphan pytest (no python process with my tags / cwd). No .env anywhere in the notes folder.

## Deviations from the spec (rulings applied; reported, not silently changed)

- D1 (R-S05-1) spec R13 / X26 / X27 dropped; R13 is now the header_state row; new PIN p08 (no `legacy_hash` / `device_lookup_keys` in the leaf or anywhere in app/ + scripts/). New mutants X26s / X27s replace the spec's X26 / X27.
- D2 (R8) the spec's `auth_routes._DEVICE_FINGERPRINT_RE is leaf.DEVICE_FINGERPRINT_RE` cannot kill X33: `re.compile` caches identical (pattern, flags), so a second local compile returns the SAME object. R8 adds an AST pin: auth_routes has exactly `from app.utils.request_context import DEVICE_FINGERPRINT_RE as _DEVICE_FINGERPRINT_RE` and no assignment to `_DEVICE_FINGERPRINT_RE`.
- D3 (R-S05-2) R6 accepts upper / mixed case and returns the lower-case canonical form; R7 drops the upper-case row and adds v1-upper, lead-space, bytes, trail-LF. The spec's X15 is flipped (mutant = remove the `.lower()`), killed by r06/r13.
- D4 (R-S05-4 / C2) R20 gains three atomic variants (each parser in turn raising through the leaf namespace), not only the fingerprint parser, because the parse order is GREEN's choice; each asserts None x3 + "malformed" x3 inside and None x3 + "absent" x3 after the request; an exception escaping the middleware is converted into an AssertionError so a non-total bind is KILLED by an assertion (X18). Junk-header variants (missing / None / str / int / bad items) accept a state of "absent" or "malformed" per header (the ruling fixes only the except arm).
- D5 (R21) the spec's single-event design does NOT detect module globals (measured: X19 survived R21 with one barrier because the second request finished before the first read); R21 now holds two barriers (both bound, then both read, then both exit).
- D6 (R24) the spec text "no other logging.* call" in the leaf would forbid `logging.getLogger(__name__)`; R24 allows exactly getLogger and still requires exactly one `logger.warning(<one str constant>)` with no keywords.
- D7 (C3) R26 drives a fresh exec of app/main.py with httpx.ASGITransport inside ONE asyncio.run (no lifespan, so no startup hooks run) and sleeps 0.15 s before reading the route-spawned task's record; readers: async route, sync + async dependency, asyncio.to_thread, loop.run_in_executor (pinned None = stated limit), sync def route, async and sync StreamingResponse generators, spawned task.
- D8 (R-S05-9) P4 = 401 (`GET /api/v1/usage/status`, no bearer) and 404 (`GET /api/v1/s05-no-such-route`) x states a/b/c/d = 8 nodes; literals recorded twice at base, byte-identical. MEASURED: the unknown-route 404 body is FastAPI's default `{"detail":"Not Found"}` (no success/code/request_id; starlette's router 404 is not the fastapi HTTPException the envelope handler is registered for), so P4 pins that body, not an envelope. P5 uses the same two routes (not /app/version).
- D9 (R-S05-8) new RED row r28: the three new files are listed in .github/black-clean-paths.txt (GREEN adds the entries). The RED file itself is black-clean now.
- D10 the RED file is LF (task rule "Pure ASCII and LF in every file you write"); spec 1.9 asked CRLF for new files. Both are black-clean; with core.autocrlf=true the index is LF either way.
- D11 header_state is called with the leaf's own constants HEADER_CONSENT_VERSION / HEADER_DEVICE_FINGERPRINT / HEADER_COMPARE_REQUEST_ID (the spec 2.2 bytes names); outside a bound request (and with the flag OFF) every state must be "absent" (r14, r22). Assumption: the ruling lists only the three constants as return values, so the unbound default is "absent", not None.
- D12 r25[imported] reads the already-imported app_main.app, so it depends on ENABLE_DEFAULT_RATE_LIMITS being unset at import (true in CI, as for the existing E1 pins).
- D13 mutation runs executed the WHOLE unit file per mutant (not -k), so the killing sets above are complete.

## Questions for the gate

- Q1 header_state name spelling: RED calls it with the leaf's bytes constants. Should a `str` header name ("x-device-fingerprint") also be part of the contract for S81-09 (the prototype accepts both)? Not pinned.
- Q2 a present but EMPTY header value (`X-Device-Fingerprint: `): "malformed" or "absent"? Not pinned (S81-09's forged-header metric depends on it).
- Q3 the unknown-route 404 at base is `{"detail":"Not Found"}`, not the unified envelope; P4 pins it as is (pre-existing, outside this unit). Confirm that pinning the measured body is wanted.
- Q4 r26 pins `loop.run_in_executor` -> None (spec stated limit 5 / K4). A consumer unit that installs a context-copying default executor would flip that node deliberately.
- Q5 X16 survived as predicted; equivalent by ruling R-S05-11 (no row).

## NOT MEASURED

- The mutation table on the FINAL RED bytes for 46 of 47 mutants (measured on the previous byte version, differing only in the R21 body; X19 re-measured on the final bytes). Not re-run because of box load (node -e 0 = 5.6 s) and the 90-minute budget.
- Head comm run, G6 (flag ON over FY25 / W4-13 / T23 / w1_9 / observability / security_middleware), the precommit-hook black nodes and tests/test_ci_gates.py::test_black_allowlist_entries_are_actually_clean with the three new entries: GREEN's gates.
