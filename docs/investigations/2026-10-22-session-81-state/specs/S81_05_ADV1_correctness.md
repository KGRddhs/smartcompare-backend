# S81-05 REQUEST-CONTEXT: correctness adversary report (Opus 5.5)

- Unit S81-05, flag ENABLE_REQUEST_CONTEXT_HEADERS, lane B. Lens: correctness. Agent model: Opus 5.5 (claude-opus-5-5).
- Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s05, branch feature/s81-s05-request-context, HEAD verified e9fd714868c4036f904e1f840e77cb217bf3c96e at start and end; `git status --short` empty at start and end (never edited).
- Scratch: detached worktree <scratchpad>/S81-05_adv_correctness at e9fd7148 (no node_modules), the 3 LF files rewritten from their blobs so the 9 changed files were sha256-equal to the GREEN worktree; removed with `git worktree remove --force`, absent from `git worktree list` afterwards.
- Notes: <scratchpad>/S81-05_adv/ (notes.md, logs, mutate_adv.py, mutation_results.json, mut_logs/, probe file copy test_zz_s05adv_probe.py, probe_out.json, claude_md.diff).

## RED file

- tests/test_s81_s05_request_context.py: full file sha256 b7a21c742174ab682968ce7dba1e5d6f3f7696b8c37afed116d0884d79fd6c83 (55,252 B, LF, 0 bytes > 127), start and end. It is NOT the brief's ecdb5792... because GREEN appended p19 / p20 (GC-1 / GC-2, allowed by GC-10); the first 52,230 bytes hash to ecdb579286f0cc1f19798b0349e5b001e982a8bff325282d5769584d4fb3a26d (the frozen RED bytes are a strict prefix), start and end. No frozen row edited.

## Runs (every [pyt] line)

- unit OFF: `[pyt] tag=s05adv-c-unit-off start=2026-10-23 13:58:48 end=2026-10-23 13:58:54 elapsed=7s bound=600s status=OK rc=0` 173 passed; [hermeticity] sentinel checked 173 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- unit ON (flag exported): `[pyt] tag=s05adv-c-unit-on start=2026-10-23 13:59:04 end=2026-10-23 13:59:11 elapsed=7s bound=600s status=OK rc=0` 173 passed; [hermeticity] 173; [netguard] blocked 0
- probes 1 (probe bugs of mine: annotations under `from __future__`, a wrong 500-code guess): `[pyt] tag=s05adv-c-probe1 start=2026-10-23 14:03:56 end=2026-10-23 14:04:02 elapsed=6s bound=600s status=FAIL rc=1`; the identity assertions themselves passed
- probes 2: `[pyt] tag=s05adv-c-probe2 start=2026-10-23 14:05:54 end=2026-10-23 14:05:59 elapsed=5s bound=600s status=OK rc=0` 4 passed; [hermeticity] 4; [netguard] blocked 0
- probes 3 (probe bug, Request import): `[pyt] tag=s05adv-c-probe3 start=2026-10-23 14:14:23 end=2026-10-23 14:14:29 elapsed=6s bound=600s status=FAIL rc=1`
- probes 4: `[pyt] tag=s05adv-c-probe4 start=2026-10-23 14:14:43 end=2026-10-23 14:14:52 elapsed=8s bound=600s status=OK rc=0` 5 passed; [hermeticity] 5; [netguard] blocked 0
- billing / identity pins with the flag ON exported (test_image_identify_llm_unavailable_s69, test_m18_usage_symmetry, test_paid_route_metering, test_retro_w1_9, test_retro_w2_1, test_s71_u13_compare_auth_required (T23), test_s75_fanout_identity (FY25), test_s80_url_mode_v2, test_w4_13_flag_off_ledger): `[pyt] tag=s05adv-c-billing-on start=2026-10-23 14:13:39 end=2026-10-23 14:14:03 elapsed=24s bound=1200s status=OK rc=0` 779 passed; [hermeticity] 779; [netguard] blocked 2 attempt(s) from 2 node(s) (test_paid_route_metering camera-success / url-history sentinel nodes, the neutralized supabase host: baseline class)
- fingerprint / middleware pins with the flag ON exported (test_auth_routes_invite_fingerprint, test_conftest_env_safety, test_m13_01_slowapi_middleware, test_observability, test_security_middleware, test_security_regression, test_social_login_device_fingerprint): `[pyt] tag=s05adv-c-fp-on start=2026-10-23 14:18:25 end=2026-10-23 14:18:56 elapsed=31s bound=1200s status=OK rc=0` 215 passed, 1 skipped, 2 deselected; [hermeticity] 216; [netguard] blocked 16 attempt(s) from 10 node(s) (the same count GREEN's CI-order set recorded for the baseline sentinel nodes)
- mutation table: 27 [pyt] lines, s05adv-c-<id>, 14:08:13-14:11:59, all bound=600s, status=FAIL rc=1 except RESETFWD and STATELEAK status=OK rc=0 (full lines in mutation_results.json `pyt` field). No TIMEOUT anywhere.
- lint (not pytest): black 26.5.1 `--check --config pyproject.toml` on the 3 new files "3 files would be left unchanged"; ruff E9,F63,F7,F82 on the 7 py files "All checks passed!"; py_compile OK.

## Mutation table (by hand, byte copy -> exact edit matching once (dry-checked 27/27, 0 bad anchors) -> whole unit file -> restore -> sha256 compare; .qa-mutation.lock in the scratch worktree, removed)

| id | edit | result (failed nodes, all AssertionError) |
|---|---|---|
| X3 | middleware: type check before the flag read | KILLED 7 |
| X5 | reset removed from finally | KILLED 13 |
| X6 | reset after the try, not in finally | KILLED 1 |
| X8 | downstream gets a wrapped send | KILLED 4 |
| X9 | consent regex `\d{1,3}` | KILLED 2 |
| X12 | fingerprint fullmatch -> match | KILLED 2 |
| X14 | uuid.UUID without version=4 | KILLED 4 |
| X17 | last occurrence wins | KILLED 7 |
| X22 | `if not pepper:` (no strip) | KILLED 2 |
| X23 | warning latch removed | KILLED 4 |
| X28 | registration gated on the flag at import | KILLED 4 |
| X29 | registration moved outermost | KILLED 4 |
| X32 | DEVICE_KEY_PEPPER removed from CREDENTIALS_UNSET | KILLED 1 |
| X33 | auth_routes local re.compile again | KILLED 1 |
| X34 | `scope = dict(scope)` before downstream | KILLED 5 |
| X36 | flag read once at import | KILLED 48 |
| X38 | set-as-you-parse (consent set before the other parses) | KILLED 6 |
| NOLOWER (new) | no lower-case normalisation (R-S05-2) | KILLED 3 |
| NOROUNDTRIP (new) | uuid canonical round-trip check removed | KILLED 4 |
| KEYNOSTRIP (new) | HMAC key not stripped | KILLED 1 |
| AFTERCORS (new) | registered after the CORS add (CORS innermost) | KILLED 4 |
| EMPTYABSENT (new, GC-2) | empty value -> "absent" | KILLED 3 |
| STRCASE (new, GC-1) | str names case-sensitive | KILLED 3 |
| EXCEPTABSENT (new, R-S05-4) | except arm states "absent" | KILLED 3 |
| BADISOK (new, R-S05-3) | a present invalid header reports "ok" | KILLED 9 |
| RESETFWD (new) | reset in forward order | SURVIVED: EQUIVALENT (four distinct ContextVars, each reset to its own token; order cannot matter) |
| STATELEAK (new) | header_state's non-constant-state filter removed | SURVIVED: EQUIVALENT (only the three constants are ever bound: `_parse_one` returns constants, the except arm binds `_MALFORMED_STATES`; the filter is unreachable defensive code, GREEN D6 / Q2) |

25 KILLED, 2 equivalent survivors, 0 errors, every restore sha-verified (pre_mutation_SHA256SUMS.txt OK after the run). GREEN's own table cross-checked: mutation_results_partial.json holds 53 rows, 52 KILLED, 1 SURVIVED = X16 (as reported).

## Runtime truth of the claims (probes in the scratch worktree, tests/test_zz_s05adv_probe.py, copy in the notes folder)

1. Flag-OFF / flag-ON identity: a fresh exec of HEAD app/main.py with the RequestContextMiddleware entry stripped from user_middleware (the runtime equivalent of base: the only other app diff is the auth_routes re-import of an identical pattern) was compared with HEAD flag OFF, HEAD flag ON (valid headers) and HEAD flag ON (malformed headers) on 12 request shapes: GET /, /api/v1/app/version, /api/v1/legal/privacy, /api/v1/legal/terms?lang=ar, /api/v1/usage/status (401), an unknown route (404), POST /api/v1/auth/login {} (422), a raising route (500), HTTPException 418, a 422 query validation, a 200 query route, an OPTIONS CORS preflight asking for x-device-fingerprint (400). Status, body bytes and every header except `date` were EQUAL in all four states (limiter reset before each request). TRUE.
2. Error-handler mapping: the 500 is the ErrorHandlerMiddleware envelope (`success:false`, code SERVER_ERROR, request_id echoed, security headers) identically in all states; the 418 / 422 handler envelopes identical; an app exception handler (add_exception_handler, i.e. ExceptionMiddleware, inside the scope) sees the bound values with the flag ON and None with it OFF. The row's "the exception handlers ... run inside RequestContext" is TRUE for the registered handlers (HTTPException, RequestValidationError, RateLimitExceeded); the generic 500 is built outside by ErrorHandler, as the row also says.
3. BackgroundTasks see the values; the next request on the same app without headers reads None / all "absent" (no leak); an empty X-Device-Fingerprint value reads state "malformed" end to end (GC-2). TRUE.
4. ContextVar rule: redis_offloop (`app/utils/redis_offloop.py:104` copy_context) and the price-parse pool (`price_service.py:4503` copy_context) copy the context; `app/utils/executor.py` installs a plain ThreadPoolExecutor, so `run_in_executor` does not copy. TRUE (read; r26 exercises CPython's default executor, see minor m3).
5. Billing R-A3: no billing / metering / refund file is in the diff; with the flag ON exported the metering and refund pins (test_paid_route_metering, test_m18_usage_symmetry, test_retro_w2_1, test_image_identify_llm_unavailable_s69, test_s80_url_mode_v2) and the W4-13 ledger stay green (779 passed). TRUE.
6. Contract freeze (PLAN_S80 section 0): no response key, code, refusal or OpenAPI change; T23 and FY25 green with the flag ON; identity probe above. TRUE.
7. GREEN report byte claims: bytes > 127 main.py 36, auth_routes.py 175, _env_safety.py 63, test_retro_w1_9.py 0, black-clean-paths 15 (all equal to base), CLAUDE.md 3961 -> 3946, the three new files 0; CR counts: existing files CRLF on every line (CLAUDE.md 949/949), new files LF. TRUE. The 9 file sha256 values in the report table equal the bytes on disk.
8. CLAUDE.md row facts checked against code: header shapes, the None rule, the state constants, the WARNING text, the stack order (r25 + main.py:119-178), E1 = 7 nodes (test_retro_w1_9.py:273-292), build-3 header senders (authService.ts:154 / :998 / :1160), share body path (referral_routes.py:75 prefix + :176 /share, ShareRequest.device_fingerprint_hash), httptools==0.8.0 pinned. TRUE except the two wording minors below.

## Findings

Blocking: none. Major: none.

Minors (documentation / rulings for the orchestrator):
- m1 (CLAUDE.md row stated limit (4), PR body limit 5): "a future device-keyed limiter must be a decorator or a consumer inside the route, never a slowapi key_func reading these values" contradicts the runtime: a `@limiter.limit(..., key_func=kf)` decorator key_func runs inside RequestContext and reads the bound fingerprint (probe test_adv_decorator_key_func_sees_values: status 200, kf saw FP_A). Only the SlowAPIASGIMiddleware default-limit key_func runs outside. Suggested wording: "never the key_func of the default-limit (SlowAPIASGIMiddleware) path; a decorator key_func does see the values".
- m2 (leaf `device_key`, robustness for S81-09): with a pepper str that is not UTF-8 encodable (a lone surrogate, the POSIX surrogateescape form of a non-UTF-8 env byte) `pepper.strip().encode("utf-8")` raises UnicodeEncodeError out of device_key instead of failing closed (probe: raised UnicodeEncodeError). Unreachable when the owner follows the "64+ hex characters" step; no consumer exists yet. Ruling: either the leaf catches UnicodeError -> None (+ the same WARNING), or S81-09's spec treats a raising device_key as account-only.
- m3 (CLAUDE.md row, ContextVar rule): "(`app/utils/executor.py`) does NOT copy the context ... (pinned by r26)": r26 drives the app without lifespan, so it pins CPython's default executor, not the installed qaren-worker pool; the claim holds because that pool is a plain ThreadPoolExecutor (read), but "pinned by r26" overstates what the node exercises.
- m4 (PR body): "Flag OFF and ON are byte-identical on every response (P4 against base literals in four states)": P4 measures two routes; "every response" holds by construction (no consumer, same objects downstream) and this adversary measured 12 request shapes equal; say "by construction; measured on the 401 / 404 (P4)".
- m5 (GREEN Q2 / D6): the header_state non-constant filter is unpinnable (STATELEAK equivalent) and bytes-name case folding is unobservable through any test; both harmless; a ruling keeps or drops them as dead defensive code.

## Prove-nothing rows (no mutant of this unit can redden them, or a leg is vacuous)

- test_s05_r14_accessors_default_none: true for any ContextVar(default=None) and for the module-global mutant when nothing is bound; adds nothing beyond the r17 / r22 "before" reads.
- test_s05_r12_pepper_never_leaks: the `PEPPER not in out` legs over HMAC hex and `PEPPER not in repr(states)` are vacuous by construction (hex digests and the three constants cannot contain the pepper text); only the caplog leg has teeth.
- test_s05_p02_openapi_declares_no_context_header: no route is added by the unit; a guard for a future change, killed by no mutant here.
- test_s05_p04 states c / d and test_s05_p05[true]: identity by construction while p01 holds (no consumer); they become load-bearing when a consumer lands.
- test_s05_p05[unset]: nothing is bound with the flag off; it pins pre-existing logging of the 401 / 404 paths only.

## Deviations

- The task names the frozen sha ecdb5792...; the committed file is b7a21c74... because of the GC-allowed p19 / p20 append; the frozen bytes were verified as a strict prefix (not a defect).
- Several cheap pin re-runs used the flag ON exported (the unit ON / OFF runs are near-identical because the autouse fixture deletes the flag; the rows set it themselves).
- Another session's pytest (st1pr2 tags) was running on the box during my runs; mine ran one at a time and I never touched another process.

## NOT MEASURED

- The comm-set chunks and the CI-order set were not re-run in full (engineering lens); the pin subsets above were run with the flag ON instead.
- No live uvicorn / httptools run (claim 7 of the row is true by HTTP/1.1 grammar; not measured on a socket).

## git status --short of the unit worktree at the end

(empty)
