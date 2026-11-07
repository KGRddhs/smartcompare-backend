# S81-24 AUTH-THROTTLE-V2 phase 1 + MS4 HOP-PROBE echo line (dark)

Base `daf86d32d222a885c42dc537e83c25483527a83b`; HEAD `ba4079cce1bb0adfcab2fb6f35efa9f31278bc92` before the final round's replay (branch `feature/s81-s24-auth-throttle-v2`: the GREEN commit f8f64d9d + the fix-round-1 commit ba4079cc, each through the hook). Answers the two adversaries (correctness MAJ-C1 + m1-m8; security F1 + m1-m4) per RULINGS_FIX1_S81_24 (F1-1..F1-7). FOCUS unit (auth routes, Redis Lua, the 429 contract build 3 renders, a privacy TTL statement). Spec `S81_24_UNIT_SPEC.md` (e545cd4a...) as amended by the review, RULINGS_S81_24 (R-S24-19..32) and GATE_S81_24 (GC-1..GC-10).

## What the flags do
- `ENABLE_AUTH_THROTTLE_V2` (NEW, default OFF, read per call as the FIRST statement of the guard at each gated route). ON: one Lua EVAL per decision (six frozen scripts) on a dedicated 4-thread `auth-throttle` pool under `asyncio.wait_for(AUTH_THROTTLE_REDIS_TIMEOUT_SECONDS)`, before any GoTrue / Supabase call of the route body and before the W1-9b lockout calls:
  - login: count-only backoff per email (R-S24-19): the n-th consecutive `Invalid email or password` result arms min(2^(n-1), cap) s; the gate refuses only while that wait is live; a success clears it. The two record writes are shielded; the gate read is cancellable and unshielded (R-S24-24). Fix round 1 (F1-1, the security MAJOR): the INNER pool future of a shielded write carries a done-callback that always retrieves its exception; when the wait was abandoned (a timeout or a cancel) and the job fails later, it logs ONE constants-only WARNING `[AUTH_THROTTLE] record failed endpoint=<login_fail|login_clear> type=<Type>` (no message text, no traceback, no key) instead of the loop's ERROR `Future exception was never retrieved` with the exception repr (one Sentry event per login before the fix).
  - register: one per email per interval (after the consent check).
  - password_reset, resend_verification: one per email per interval and N per Asia/Riyadh day, each on its own keys (resend gated outside its try).
  - change_password, update_email: N per window per authenticated user id.
  - Keys `auth_throttle:<endpoint>:<kind>:<HMAC-SHA256(AUTH_THROTTLE_PEPPER, ident)[:32]>`; TTLs per R-S24-20 (backoff max(TTL knob, cap), interval = the interval, account = the window, the day counter 24 h from its first increment).
  - A refusal is the SAME 429 the slowapi limit emits (`RATE_LIMITED`, `Retry-After` = `retry_after_seconds` >= 1) plus INFO `[AUTH_THROTTLE] throttled endpoint=<e> count=<n> retry_after=<s>`.
  - Fail OPEN on every Redis error / timeout / unset client / malformed reply (the parser accepts exactly three non-bool ints with the flag in {0, 1}; a digit-str reply such as ['1','0','0'] is REFUSED and fails open, as the frozen R63 pins; GATE GC-4 Q-R2's 'digit-str' sentence is corrected by the orchestrator; upstash-redis 1.7.0 returns Lua integers as Python ints): WARNING `[AUTH_THROTTLE] skipped endpoint=<e> type=<T>` (60 s per-endpoint memo; per request: login failure [login, login_fail], login success [login, login_clear], other routes [endpoint]); an unset pepper = V2 inactive, ONE `[AUTH_THROTTLE] pepper unset` WARNING per process.
- `ENABLE_HOP_PROBE_LOG` (NEW, default OFF, read per request inside `RequestIDMiddleware.dispatch`): one INFO `[HOP_PROBE] ...` line (counts and booleans only; last field `uvicorn_forwarded_allow_ips_set`, the env NAME presence) on GET /health and GET /api/v1/app/version only.
- Knobs (default, range; out of range / garbage / inf / nan -> the default): `AUTH_THROTTLE_LOGIN_CAP_SECONDS` 60 (8..3600), `AUTH_THROTTLE_REGISTER_INTERVAL_SECONDS` 60 (10..3600), `AUTH_THROTTLE_RESET_INTERVAL_SECONDS` 60 (10..3600), `AUTH_THROTTLE_RESET_PER_DAY` 5 (1..100), `AUTH_THROTTLE_ACCOUNT_PER_WINDOW` 5 (1..100), `AUTH_THROTTLE_ACCOUNT_WINDOW_SECONDS` 600 (60..86400), `AUTH_THROTTLE_TTL_SECONDS` 21600 (60..86400), `AUTH_THROTTLE_REDIS_TIMEOUT_SECONDS` 0.5 (0.05..5.0). Credential name `AUTH_THROTTLE_PEPPER` joins `tests/_env_safety.CREDENTIALS_UNSET`.
- Flag OFF: byte-identical on every auth response, header set, log line and Redis command sequence with the FULL companion configuration (P70-P74); the 429 contract and the middleware-order pins green in both states.

## Change list (git diff --numstat daf86d32 HEAD)
| file | + | - |
|---|---|---|
| app/services/auth_throttle.py (NEW, ASCII, LF) | 464 | 0 |
| app/api/auth_routes.py (CRLF kept: 1 import, 6 gates, 2 login record guards) | 17 | 0 |
| app/middleware/request_id.py (CRLF kept: hop_probe_log_enabled, HOP_PROBE_PATHS, _log_hop_probe, 1 guarded call) | 69 | 0 |
| tests/_env_safety.py (AUTH_THROTTLE_PEPPER after DEVICE_KEY_PEPPER) | 2 | 0 |
| tests/test_s81_s24_auth_throttle.py (the frozen RED file, 7fdf71db..., unedited) | 2134 | 0 |
| CLAUDE.md (the S81-24 block after the S81-22 block + the :341 pointer clause) | 7 | 1 |

Fix round 1 (git diff --numstat f8f64d9d ba4079cc):

| file | + | - |
|---|---|---|
| app/services/auth_throttle.py (`_durable_done` + `_run(durable, endpoint)`: the F1-1 hunk only) | 38 | 7 |
| tests/test_s81_s24_fix1_rows.py (NEW: F1-R1 x2 RED at f8f64d9d, F1-R2 / F1-R3 PIN) | 251 | 0 |
| tests/test_s81_s24_gate_rows.py (NEW: G24-GR1 x3, G24-GR2 x5, G24-GR3) | 144 | 0 |
| CLAUDE.md (the S81-24 block edited in place, CRLF kept) | 2 | 2 |

No legal file, migration, client file, rate_limiter / error_handler / main.py edit, requirements or .githooks change.

Naming (F1-5, the ruled exception): `DAY_KEY_TTL_SECONDS` keeps its name (a binding RED D4 name; its value 86400 has no secret shape; gitleaks 8.30.1 clean with the repo and default configs): it is the ONE constant whose name carries a gitleaks keyword ('key'); the rule stands for every other name.

## RED rows and mutants
- 199 nodes = 90 RED (50 functions) / 109 PIN (9 functions); at base 90 failed on AssertionError only, 109 passed (GATE GC-2).
- The RED mutation table: 60 mutants, 60 KILLED, 0 survivors (specs/S81_24_RED_REPORT.md).
- Ruling -> rows: R-S24-19 login backoff R10-R16; R-S24-20 TTLs R34; R-S24-21 memo R60 / R61 / R67; R-S24-22 slowapi reset + V2 marker in every route row; R-S24-23 R100-R108; R-S24-24 R68; R-S24-7 the 429 R50 / R51 / P74; R-S24-9 enumeration R21 / R32; R-S24-14 OFF identity P70-P73; R-S24-10 decorator pins P80 / P81; placement R82 / R83; hygiene R90-R93 / P83.
- Fix round 1 rows: F1-R1 (a cancelled durable write whose job raises later: no 'never retrieved' record, exactly one constants-only WARNING; 2 nodes, RED at f8f64d9d on an AssertionError: `[pyt] tag=s24f1-red-head-all start=2026-11-07 11:41:21 end=2026-11-07 11:41:34 elapsed=13s bound=600s status=FAIL rc=1` = 2 failed, 210 passed), F1-R2 (a cancelled gate read: fail-open, no new line; PIN), F1-R3 (the write lands after the outer cancel; PIN); gate rows G24-GR1 (HMAC key = pepper.strip(), kills M58'), G24-GR2 (an unknown endpoint allows and writes no key, kills A17), G24-GR3 (an empty hop-probe header counts as present, `is not None`, kills A15), each green at HEAD and RED on a sha-verified byte-copy mutant (s24f1-mut-GR1 / GR2 / GR3 status=FAIL rc=1, restored sha-equal). The F1-1 mutants (the callback removed; the callback re-raising; the WARNING carrying the message text) are each killed by F1-R1 (s24f1-mut-F1a / F1b / F1c status=FAIL rc=1, AssertionError only, restored sha-equal).
- At the fix HEAD: `[pyt] tag=s24f1-green-off start=2026-11-07 11:41:57 end=2026-11-07 11:42:08 elapsed=11s bound=600s status=OK rc=0` and `[pyt] tag=s24f1-green-on start=2026-11-07 11:42:08 end=2026-11-07 11:42:19 elapsed=10s bound=600s status=OK rc=0` (212 passed each = the frozen 199 + the 13 new nodes).
- At the GREEN HEAD: `[pyt] tag=s24-green-red-off start=2026-11-07 09:01:11 end=2026-11-07 09:01:28 elapsed=17s bound=600s status=OK rc=0` (199 passed) and `[pyt] tag=s24-green-red-on start=2026-11-07 09:01:35 end=2026-11-07 09:01:42 elapsed=6s bound=600s status=OK rc=0` (199 passed; both flags + a synthetic low-entropy pepper + the eight knobs exported in the runner call only).

## E-rows (deliberate pin changes)
None. No existing test edited; no pin reddened.

## Gates
- ruff --select E9,F63,F7,F82 + py_compile clean on the five Python files; bytes > 127 = 0 in auth_throttle.py; no whole-file diff.
- Fix round 1: CI-order set `[pyt] tag=s24f1-ci start=2026-11-07 11:46:38 end=2026-11-07 11:47:32 elapsed=53s bound=1200s status=FAIL rc=1` (2 failed = the two baselined social nodes, 789 passed, 1 skipped); pins set 316 passed ON (`s24f1-pins-on` elapsed=30s OK) and unset (`s24f1-pins-off` elapsed=30s OK); the WIDENED comm set of record (F1-2, MAJ-C1): the AST test-support closure adds tests/test_s81_s10_gate_rows.py (it imports the member test_s81_s10_fragrance_gate) and, for completeness, the five test modules members import as support (test_compare_timeout_graceful, test_hotfix_shopping_query_clean, test_openai_breaker, test_prescoring_showable_guard, test_tradeoffs_dedup_parity): 370 files, record base_records/daf86d32.../e3b889e4....{files,header.txt,txt,pyt.log} (base REUSED from a9a3f4b3... + ea0d2f1b..., LC-6); at the fix HEAD the 370 + the three S81-24 test files in 15 chunks (s24f1-comm-chunk_00..14, bound 1200): FAILED = the same 20 environmental ids, `comm -13` EMPTY; tests/test_secret_scan_static.py `s24f1-secretscan` 31 passed; fences `[jest] tag=s24f1-fences` 14 / 15 suites, exactly the four w37 drift nodes, b3a green.
- GREEN: CI-order set (19 files): `[pyt] tag=s24-green-ci start=2026-11-07 09:01:55 end=2026-11-07 09:02:54 elapsed=59s bound=1200s status=FAIL rc=1` = 2 failed (the two baselined test_auth_interceptor social nodes), 789 passed, 1 skipped (as at base).
- Pins set (429 contract, s05, retro_w1_9, retro_w1_1, brute_force, retro_w1_9_429, conftest env safety): 316 passed ON (`s24-green-pins-on` elapsed=32s OK) and unset (`s24-green-pins-off` elapsed=31s OK).
- Comm set: the RED's 364 (a9a3f4b3...) + the RED file = 365 files at HEAD in 15 chunks (s24g-comm-c00..c14, bound 1200) vs the STORED base record base_records/daf86d32.../a9a3f4b3....txt (REUSED, LC-6): HEAD FAILED = the same 20 environmental ids; `comm -13` EMPTY. The 38 CLAUDE.md readers re-run after the CLAUDE.md edit: 876 + 844 passed, 0 failed.
- tests/test_secret_scan_static.py alone: `[pyt] tag=s24g-secretscan start=2026-11-07 09:22:13 end=2026-11-07 09:22:20 elapsed=7s bound=600s status=OK rc=0` (31 passed).
- Client fences (the fourteen + b3a/nativeStrings by path through the junction; jest 29.7.0, node v24.11.1): 14 / 15 suites pass; config/nativeBundle.w37 fails exactly the four accepted drift nodes (d5, k2, k4, k5); b3a green. The FULL jest suite NOT run here (LC-7: the final round).
- The four tests/test_precommit_hook*.py NOT RUN (no .githooks change). The corpus gate NOT required (no price-pipeline module).

## Stated limits (ids as amended; L9 and L12 withdrawn)
- L1 (narrowed) the six scripts run only as a Python model in the hermetic tests; they ran correctly on a throwaway localhost Redis 5.0.14 / Lua 5.1 in the adversary's probe, so the limit is Upstash's engine and its REST path; the fake's JSON-int reply shape matches the measured upstash-redis 1.7.0 decode of an EVAL reply; the canary's scripted pass is their first Upstash execution (R-S24-29).
- L2 `now` is the web process clock passed as ARGV; replica skew shifts windows.
- L4 during an Upstash outage only the in-memory slowapi floor remains (V2 and W1-9b both fail open).
- L5 the per-IP floor keeps keying on the edge peer; true only while `FORWARDED_ALLOW_IPS` is unset on web.
- L6 the 24 h day counter outlives the live privacy "within 6 hours" sentence until S81-12.
- L7 anyone who knows an email can hold its login at most one cap window per wrong attempt (60 s default); the W1-9b 900 s lockout already allowed a stronger hold.
- L8 the keys are pseudonymous personal data (a peppered digest of an email or a user id); a pepper rotation orphans every key and resets every throttle.
- L10 register stays enumerable as at base (400 "already exists" vs 200) in both states (S81-24d).
- L11 with `ENABLE_UPSTASH_BOUNDED_TRANSPORT` OFF a stalled REST call parks a pool thread; the wait_for bound still fails open on time.
- L14 auth_throttle.py is not in `.github/black-clean-paths.txt`.
- L15 the account routes' GoTrue token verify (Depends) runs before the gate.
- L-S24-16 N concurrent wrong-password attempts inside one Redis round trip all reach GoTrue before the first failure records.
- L-S24-17 the interval keys arm on every ALLOWED register / reset / resend call, including one GoTrue then rejects: a retry inside 60 s gets the V2 429 (phase 2 may move the arm to the success path).
- L-S24-18 RESET_SCRIPT is a two-key EVAL without a hash tag: CROSSSLOT on a clustered Redis = fail open (Upstash assumed non-clustered).
- L-S24-19 the reset / resend day caps are per email: anyone who knows an email can exhaust its 5 a day in about 5 minutes, and the victim's own reset is 429 until the Riyadh midnight (the slowapi edge bucket does not stop one client); phase 2 keys the caps per (email, device) once the header OTA lands.
- L-F1 (fix round 1) if a timeout and the job's own failure land in the same loop iteration, the callback retrieves the exception without the WARNING (the memoised skipped TimeoutError line still fires); the merged S81-04 `llm_spend_breaker._run_bounded_async(durable=True)` carries the same latent form (flag OFF): an orchestrator follow-up, not this unit's edit.
- The adversaries' minors not fixed above are stated limits (LC-4); the 'CRLF kept' wording of the GREEN report is a working-copy statement (the committed blobs are LF).

## Flip preconditions and owner steps (names only; a dated ledger line per step)
None to merge. Before `ENABLE_AUTH_THROTTLE_V2` flips: (1) `AUTH_THROTTLE_PEPPER` set on web (the owner generates it; never in a transcript; never a reused pepper); (2) owner item 8 (the Supabase dashboard sign-up and token limits) done; (3) the S81-12 window live (the throttle text; privacy-line mapping R-S24-28: backoff keys = the failed sign-ins line, account keys = the account-linked sign-in records line, interval keys = the short-lived security checks line, the day counter = "up to 24 hours"); (4) the S81-24e client line (ForgotPasswordScreen maps RATE_LIMITED to common.errors.rateLimited) live in a post-approval OTA (R-S24-25); (5) the owner's explicit yes, then a canary that BEGINS with one scripted pass per endpoint (synthetic email, flag ON, pepper set) reading the throttled / skipped lines (R-S24-29), then real traffic reading the `[AUTH_THROTTLE] throttled` count per endpoint, never an edge 429 count (CR2). Rollback: unset the flag (per call; keys expire within 24 h).
Probe (R-S24-23): a dated names-only read of `FORWARDED_ALLOW_IPS` on web first; `ENABLE_HOP_PROBE_LOG` ON only after the deploy settles; from one public IP one plain GET /health and one with a forged single TEST-NET X-Forwarded-For; pick the two lines by timestamp (the Railway healthcheck also hits /health); the booleans land as a dated ledger line; unset the flag.

## Follow-ups
S81-24b (phase 2 after the probe: per-IP / per-device keys, the m13_02 leftmost pin, #299, the GoTrue secret-key client + Sb-Forwarded-For, SMTP, the W1-9b retirement after a canary); S81-24c (test-only: retire the string-presence limiter tests); S81-24d (the register enumeration contract); S81-24e (the client ForgotPassword RATE_LIMITED mapping).

## [NATIVE READ]
EMPTY (no Arabic string in this unit).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
