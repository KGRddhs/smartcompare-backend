# S81-05 REQUEST-CONTEXT: three request headers into ContextVars + the HMAC device key (dark flag `ENABLE_REQUEST_CONTEXT_HEADERS`)

PLAN_S81 M1, lane B. Spec `.qa-s80/S81-05_UNIT_SPEC.md` (sha 7df306bc...), adversarial review (APPROVE_WITH_CHANGES), rulings `specs/RULINGS_S81_05.md` (R-S05-1..R-S05-11, C1-C14) and the RED gate `specs/GATE_S81_05.md` (GC-1..GC-10) in `docs/investigations/2026-10-22-session-81-state/`. Base `84c861f6`.

## What the flag does

`ENABLE_REQUEST_CONTEXT_HEADERS` (default OFF, read per HTTP request with the house idiom as the FIRST statement of the middleware; a new name, so unset in production by construction).

- New stdlib-only leaf `app/utils/request_context.py`: three ContextVars and accessors `consent_version()` (`X-AI-Consent-Version`, int 0..999 written as 1-3 ASCII digits), `device_fingerprint()` (`X-Device-Fingerprint`, `^[a-f0-9]{64}$` matched in full) and `compare_request_id()` (`X-Compare-Request-Id`, canonical uuid4, upper / mixed case normalised to lower case, R-S05-2); `header_state(name)` -> the constants `"absent"` / `"malformed"` / `"ok"` (never a value; bytes constants or str names, case-insensitive, GC-1; an EMPTY value is `"malformed"`, GC-2); `bind_from_headers` (TOTAL and ATOMIC: parse all three into locals, set the ContextVars only after every parse finished, any exception -> every value None and every state `"malformed"`, R-S05-4) and a total `reset_request_context`; `device_key(fp)` = HMAC-SHA256(`DEVICE_KEY_PEPPER` stripped, fp), fail closed (invalid fp: None without reading the pepper; unset / blank pepper: None + ONE constant WARNING per process). `legacy_hash` / `device_lookup_keys` are NOT shipped (R-S05-1).
- New pure-ASGI `app/middleware/request_context.py::RequestContextMiddleware`: flag first; OFF = one `os.getenv`, no scope read, nothing bound; ON = bind for `http` scopes only, reset in `finally`; the SAME `scope` / `receive` / `send` objects go downstream in both states; it never logs.
- `app/main.py`: registered UNCONDITIONALLY as the innermost user middleware, immediately before the CORS add (R-S05-5); the `:97` comment rewritten (C8). Stack (outermost first): RequestID, SecurityHeaders, ErrorHandler, [SlowAPIASGI under `ENABLE_DEFAULT_RATE_LIMITS`], CORS, RequestContext.
- `app/api/auth_routes.py:35`: `_DEVICE_FINGERPRINT_RE` is the leaf's `DEVICE_FINGERPRINT_RE` re-imported under its old name (one compiled object, same pattern); nothing else in the file.
- `tests/_env_safety.py`: `DEVICE_KEY_PEPPER` joins `CREDENTIALS_UNSET` (R-S05-6).
- `.github/black-clean-paths.txt`: the three new .py files join the ratchet (R-S05-8).
- `CLAUDE.md`: the SESSION 81 S81-05 flag row (after the D03 block, before `## Tests`), `DEVICE_KEY_PEPPER` in the Optional env list, the `:112` middleware-stack sentence completed in place (C7), the `:184` middleware list gains `request_context`.

No consumer reads the ContextVars yet (pinned by p01); the flag is inert until S81-06 / S81-09 / S81-22 flip. No route parameter, schema, response key, OpenAPI, DB or Redis change. Flag OFF and ON are byte-identical on every response (P4 against base literals in four states).

## Defect / ruling ids -> RED node ids

| id | what | node ids (tests/test_s81_s05_request_context.py) |
|---|---|---|
| S81-05 | three headers into ContextVars, None rule, flag per call | test_s05_r01 (13), r02 (5), r03 (19), r04 (3), r05 (11), r06 (3), r07 (15), r14, r15 (4), r16 (9), r17 (2 + nested), r19 (2), r21, r26 (2) |
| S81-05 device key | HMAC, fail closed, never leaks | test_s05_r09 (2), r10 (4), r11 (11), r12 |
| R-S05-1 | no dual-hash map | test_s05_p08 |
| R-S05-2 | lower-case request id | test_s05_r06, r07[v1-upper], r13[upper-id] |
| R-S05-3 / GC-1 | header_state constants, str names | test_s05_r13 (7), r14, r22, test_s05_p19 (3) |
| GC-2 | empty value = malformed | test_s05_p20 (3) |
| R-S05-4 / C2 | atomic bind, total bind | test_s05_r20_atomic_bind_when_a_parser_raises (3), r20_bind_is_total (8) |
| R-S05-5 | innermost, unconditional, pure ASGI, same objects | test_s05_r25 (4), r15, r19, r22 (7), r23 |
| R-S05-6 | CORS unchanged; pepper sanitised | test_s05_p03, r27 |
| R-S05-8 | black ratchet | test_s05_r28 |
| R-S05-9 / GC-3 | P4 401 + 404 bytes | test_s05_p04 (8) |
| C3 | R26 driver (httpx.ASGITransport, one asyncio.run) | test_s05_r26 (2) |
| C9 | first occurrence decides | test_s05_r18 (6) |
| C11 | ScopeSpy reads / writes | test_s05_r22, r23 |
| R8 / D2 | one regex object (identity + AST) | test_s05_r08 |
| no-log | sources never log | test_s05_r24, p05 (4) |
| parity | existing fingerprint readers and route reads unchanged | test_s05_p06, p07 |
| no-consumer | nothing reads the vars yet | test_s05_p01, p02 |

173 nodes = 149 RED + 18 PIN (frozen RED bytes, sha ecdb5792...) + 6 additive PIN nodes p19 / p20 appended by GREEN (GC-1 / GC-2; the frozen bytes are a strict prefix of the file; new sha b7a21c74...).

## Deliberate pin changes (spec 4.1)

| # | node | before | after | why |
|---|---|---|---|---|
| E1 | `tests/test_retro_w1_9.py::TestW19cFlagOffIdentity::test_imported_app_has_no_rate_limit_middleware`, `::test_fresh_exec_flag_off_matches_the_imported_app`, `::test_falsy_flag_values_register_nothing[ , 0, false, off, no]` (7 nodes via `EXPECTED_STACK`) | the four base classes | the four + `"RequestContextMiddleware"` last | registered unconditionally and innermost; the list still proves "no rate-limit middleware" with the flag OFF |

No other existing node changes.

## Gates (every pytest through pyt.py, one at a time)

- Bytes: the three new files pure ASCII; existing files keep CRLF; `git diff --stat` content lines only (9 files, +2025 / -5); CLAUDE.md non-ASCII bytes 3961 -> 3946 (the five arrows of the rewritten `:112` line became ASCII `->`; nothing non-ASCII added).
- Lint: ruff E9,F63,F7,F82 clean and py_compile OK on the 7 Python files; black 26.5.1 `--check` clean on the 3 new files; the pre-commit hook passed (no `--no-verify`).
- Unit file, flag ON: `[pyt] tag=s05g-unit-on start=2026-10-23 12:36:31 end=2026-10-23 12:36:42 elapsed=10s bound=600s status=OK rc=0` (173 passed; [hermeticity] 173; [netguard] blocked 0)
- Unit file, flag OFF: `[pyt] tag=s05g-unit-off start=2026-10-23 12:37:06 end=2026-10-23 12:37:13 elapsed=6s bound=600s status=OK rc=0` (173 passed; [hermeticity] 173; [netguard] blocked 0)
- GC-6 mutation table on GREEN's bytes against the final RED file (whole unit file per mutant, byte copy, restore, sha256 compare, `.qa-mutation.lock`): 53 mutants = the RED table's 47 + XSLV2 + five p19 / p20 mutants (XP19a str names ignored, XP19b str names case-sensitive, XP19c unknown name -> consent state, XP20 empty value reads absent, XP20b empty value skipped at collection): 52 KILLED (assertion failures only, 0 errors), 1 SURVIVED = X16 (`len == 36` pre-check removed), EQUIVALENT BY RULING R-S05-11 / GC-5. Every restore sha-verified.
- CI-order pin set (16 files, alphabetical: the unit file, test_retro_w1_9 incl. E1, test_m13_01, test_conftest_env_safety, the two fingerprint files, test_security_regression, test_ci_gates, test_security_middleware, test_observability, T23, FY25, W4-13, test_sentry_channels_u8d_unit, test_behavior_dimension_translation, test_s79_b3b_apple_revoke): `[pyt] tag=s05g-ciorder start=2026-10-23 12:55:00 end=2026-10-23 12:56:36 elapsed=95s bound=1200s status=OK rc=0` (900 passed, 1 skipped, 2 deselected; [hermeticity] 901; [netguard] blocked 16 attempt(s) from 10 node(s), the baseline sentinel nodes of spec 1.10)
- G6 flag ON identity (`ENABLE_REQUEST_CONTEXT_HEADERS=true` exported for that call only; FY25, W4-13, T23, w1_9, observability, security_middleware): `[pyt] tag=s05g-g6-flagon start=2026-10-23 12:57:05 end=2026-10-23 12:57:21 elapsed=16s bound=1200s status=OK rc=0` (215 passed)
- Black ratchet: `[pyt] tag=s05g-black-allow start=2026-10-23 13:00:50 end=2026-10-23 13:01:00 elapsed=10s bound=600s status=OK rc=0` (`test_ci_gates.py::test_black_allowlist_entries_are_actually_clean` 1 passed); `[pyt] tag=s05g-hook-black start=2026-10-23 12:57:36 end=2026-10-23 13:00:31 elapsed=174s bound=1200s status=OK rc=0` (`tests/test_precommit_hook.py -k black` 4 passed, 58 deselected)
- Comm set at HEAD: 210 files = the RED base list (187, all included) UNION the HEAD re-derivation (+ the unit file, + 22 tests that read app source through `inspect.getsource`), MINUS the four `test_precommit_hook*.py`; 15 chunks of 14 files, bound 1200, one at a time; the NETWORK_FLAKY node `test_rate_limiting_complete.py::TestRateLimitCoverage::test_prices_endpoint_rate_limited` deselected as at base. Total 9,318 passed, 2 failed, 33 skipped, 35 xfailed. HEAD FAILED = `tests/test_auth_interceptor.py::test_sign_in_with_social_exception`, `::test_social_login_user_insert_fails_gracefully` (`tests/.pre_impl_failures.txt`, known local reds) = the RED base FAILED set; **branch-only-NEW = empty**. The 23 head-only files had zero failures, so no base re-run was needed for them.
  - `[pyt] tag=s05g-comm-head-c00 start=2026-10-23 13:03:21 end=2026-10-23 13:03:38 elapsed=17s bound=1200s status=OK rc=0` (447 passed)
  - `[pyt] tag=s05g-comm-head-c01 start=2026-10-23 13:03:44 end=2026-10-23 13:04:06 elapsed=22s bound=1200s status=FAIL rc=1` (2 failed = the two baseline auth_interceptor nodes, 555 passed, 25 deselected)
  - `[pyt] tag=s05g-comm-head-c02 start=2026-10-23 13:04:41 end=2026-10-23 13:05:53 elapsed=72s bound=1200s status=OK rc=0` (856 passed)
  - `[pyt] tag=s05g-comm-head-c03 start=2026-10-23 13:06:07 end=2026-10-23 13:08:09 elapsed=122s bound=1200s status=OK rc=0` (154 passed, 1 skipped)
  - `[pyt] tag=s05g-comm-head-c04 start=2026-10-23 13:08:22 end=2026-10-23 13:09:32 elapsed=70s bound=1200s status=OK rc=0` (1262 passed)
  - `[pyt] tag=s05g-comm-head-c05 start=2026-10-23 13:10:06 end=2026-10-23 13:19:02 elapsed=536s bound=1200s status=OK rc=0` (430 passed)
  - `[pyt] tag=s05g-comm-head-c06 start=2026-10-23 13:19:17 end=2026-10-23 13:20:16 elapsed=59s bound=1200s status=OK rc=0` (132 passed)
  - `[pyt] tag=s05g-comm-head-c07 start=2026-10-23 13:20:31 end=2026-10-23 13:22:01 elapsed=89s bound=1200s status=OK rc=0` (339 passed)
  - `[pyt] tag=s05g-comm-head-c08 start=2026-10-23 13:22:21 end=2026-10-23 13:23:50 elapsed=89s bound=1200s status=OK rc=0` (363 passed, 21 skipped)
  - `[pyt] tag=s05g-comm-head-c09 start=2026-10-23 13:24:35 end=2026-10-23 13:28:48 elapsed=253s bound=1200s status=OK rc=0` (461 passed, 1 skipped)
  - `[pyt] tag=s05g-comm-head-c10 start=2026-10-23 13:29:30 end=2026-10-23 13:32:18 elapsed=167s bound=1200s status=OK rc=0` (598 passed)
  - `[pyt] tag=s05g-comm-head-c11 start=2026-10-23 13:32:52 end=2026-10-23 13:35:20 elapsed=148s bound=1200s status=OK rc=0` (1907 passed)
  - `[pyt] tag=s05g-comm-head-c12 start=2026-10-23 13:35:45 end=2026-10-23 13:36:15 elapsed=30s bound=1200s status=OK rc=0` (612 passed, 1 skipped)
  - `[pyt] tag=s05g-comm-head-c13 start=2026-10-23 13:36:33 end=2026-10-23 13:37:36 elapsed=63s bound=1200s status=OK rc=0` (370 passed)
  - `[pyt] tag=s05g-comm-head-c14 start=2026-10-23 13:40:03 end=2026-10-23 13:40:37 elapsed=34s bound=1200s status=OK rc=0` (832 passed, 9 skipped, 35 xfailed)
- Base comm record (RED agent, 187 files, 8 chunks at 84c861f6): 8,662 passed, 2 failed (the same two auth_interceptor nodes), 11 skipped, 35 xfailed.

## Stated limits

1. Build 3 sends `X-Device-Fingerprint` as a header only on register and the two social sign-ins; share carries the hash in the JSON body; it never sends the other two headers: every accessor reads None on compare, camera, usage and share until the S81-08 OTA.
2. The consent version is the client's claim; S81-06 treats it as a claim.
3. The fingerprint is client-generated and only format-checked; the S81-08 composition change and a pepper rotation both restart every device key.
4. ContextVar rule for consumers: read the accessors before any offload; `asyncio.to_thread`, Starlette's threadpool, `redis_offloop` and the price-parse pool copy the context, a task created in the request keeps its snapshot; `loop.run_in_executor` with the installed default executor reads None (pinned, r26).
5. Innermost position: a CORS preflight never binds; the default-limit 429 of `SlowAPIASGIMiddleware` is produced outside the scope (a device-keyed limiter must be a decorator or a consumer in the route).
6. CORS `allow_headers` unchanged (native clients do not preflight; Expo web would be refused).
7. No minimum pepper length enforced.
8. The leaf's full match rejects the trailing-newline fingerprint the `auth_routes` / `usage_service` `.match` readers accept; no HTTP/1.1 parser (httptools in production) delivers one.
9. No DB or privacy-text change (device counters move in S81-12 LEGAL-V3).
10. One `os.getenv` per HTTP request in both flag states (not timed).
11. The unknown-route 404 body is FastAPI's default `{"detail":"Not Found"}` (pre-existing; S81-05b), pinned as measured.
12. The device-fingerprint transition is dual-VALUE (R-S05-1): `X-Device-Fingerprint-Legacy` is S81-08's contract; this unit parses only `X-Device-Fingerprint`.

## Owner steps (names only)

1. Set `DEVICE_KEY_PEPPER` on `web` (a random text value of at least 64 hex characters; never in the repo, chat or a ledger) BEFORE the flag flips.
2. After approval and after the S81-08 OTA has propagated: set `ENABLE_REQUEST_CONTEXT_HEADERS=true` on `web` in the PLAN_S81 window "ledger, breaker, request context ON", its own canary window, before any consumer flag (S81-06 / S81-09 / S81-22).
3. Record both as dated ledger lines (names only). Rollback: unset the variable (per request, immediate).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
