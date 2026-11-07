# S81-24 AUTH-THROTTLE-V2 phase 1 + MS4 HOP-PROBE echo line (dark)

**STATUS: READY. The final round's one blocker (the frozen P73 row's dependence on an earlier in-process lifespan) is CLOSED by the ruled pin-fix PF-1 of RULINGS_PINFIX_S81_24 (the frozen RED file's blob sha superseded: see the Pin-fix section); re-measured green with the lifespan user first and on the comm chunk that held the twelve failures.**

Base `39ac80ba437760d1a77eaac9670faeea505f08f4` (origin/main, #394 S81-G8 FOLLOWUPS); HEAD `a920190bb991488306712fdf1aeed4a080a092ff`, three commits:
- GREEN 0775995d (replayed from f8f64d9d)
- fix round 1 0e9b0fc9 (replayed from ba4079cc)
- the final-round CLAUDE.md commit a920190b

FOCUS unit (auth routes, Redis Lua, the 429 contract build 3 renders, a privacy TTL statement). The spec `S81_24_UNIT_SPEC.md` (e545cd4a...) as amended, with RULINGS_S81_24 (R-S24-19..32), GATE_S81_24 (GC-1..GC-10), RULINGS_FIX1_S81_24 (F1-1..F1-7) and RULINGS_REBASE_S81_24 (RB-S24-1..6). Reports: specs/S81_24_RED_REPORT.md, S81_24_GREEN_REPORT.md, S81_24_ADV1_correctness.md, S81_24_ADV2_securityandprivacy.md, S81_24_FIX1_REPORT.md, S81_24_REVERIFY_REPORT.md and the final-round REBASE_REPORT.md.

## Pin-fix (the final round's blocker, ruled and measured)
The frozen RED row `tests/test_s81_s24_auth_throttle.py::test_p73_hop_probe_off_silent` (12 parametrized nodes, PIN class) asserts that `/health` carries exactly five keys, because "the TestClient runs no lifespan here". That only holds if no earlier test in the same pytest process has run the app lifespan.

`tests/test_s81_s20_result_gate.py` (on main since #390) enters `with TestClient(app_main.app)`, which runs the lifespan. When it runs earlier in the same process, `/health` also carries `adapter_executor` and `redis_offloop_pool`, and all 12 P73 nodes fail on an AssertionError.
- Minimal repro: `[pyt] tag=s24fin-p73-test_s81_s20_result_gate ... status=FAIL rc=1` (12 failed, 166 passed).
- The RED file alone is green. So was every earlier round, because their chunk order ran the RED file after the test_z* files.
- CI runs `python -m pytest tests/` in one process, with test_s81_s20 before test_s81_s24, so CI would very likely go red.

RULED (RULINGS_PINFIX_S81_24 PF-1, the S86 J09 precedent): a pin-fix of the frozen RED file: P73's /health key assertion now subtracts the three documented process-state pool keys (LIFESPAN_HEALTH_FIELDS = adapter_executor / price_parse_pool / redis_offloop_pool, present only once their pool exists in the process: app/main.py *_snapshot) before comparing with the five base keys; nothing else in the row or the file. The frozen blob sha is superseded: 7fdf71db... -> d48467fe9033bdfb... (GATE_S81_24 GC-1 amended). Re-measured after the fix: the lifespan user first then the RED file in one process = 0 failed (`[pyt] tag=s24pf-repro start=2026-11-07 14:10:10 end=2026-11-07 14:10:21 elapsed=11s bound=1200s status=OK rc=0` = 365 passed, 0 failed); the comm chunk that held the twelve failures = its environmental ids only (`[pyt] tag=s24pf-comm-c11 start=2026-11-07 14:10:59 end=2026-11-07 14:11:59 elapsed=60s bound=1200s status=FAIL rc=1` = 10 failed (all 10 in base_failed.txt), 1887 passed); comm -13 EMPTY.

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

## Change list (git diff --numstat origin/main...HEAD)
| file | + | - |
|---|---|---|
| app/services/auth_throttle.py (NEW, ASCII, LF blob) | 495 | 0 |
| app/api/auth_routes.py (1 import, 6 gates, 2 login record guards) | 17 | 0 |
| app/middleware/request_id.py (hop_probe_log_enabled, HOP_PROBE_PATHS, _log_hop_probe, 1 guarded call) | 69 | 0 |
| tests/_env_safety.py (AUTH_THROTTLE_PEPPER after DEVICE_KEY_PEPPER) | 2 | 0 |
| tests/test_s81_s24_auth_throttle.py (the frozen RED file; blob 7fdf71db... through the fix round, d48467fe... after the ruled pin-fix PF-1) | 2137 | 0 |
| tests/test_s81_s24_fix1_rows.py (fix round 1, f96a9dd8...) | 251 | 0 |
| tests/test_s81_s24_gate_rows.py (fix round 1, 5b591613...) | 144 | 0 |
| CLAUDE.md (the S81-24 block after the S81-G8 block; the :341 sentence after the S81-G8 sentence; the :92 apply record and the S81-08b row rewritten in place) | 10 | 4 |

This unit changes no legal file, migration or client file; no rate_limiter, error_handler or main.py; no requirements and no .githooks. Naming (F1-5): `DAY_KEY_TTL_SECONDS` is the one ruled name exception (a binding RED D4 name; value 86400, with no secret shape).

## The CLAUDE.md rewrites of the final round (RB-S24-3)
- :92 apply record: the 045 part-1 checks passed 2026-11-07; 047 applied 2026-11-07 09:20 (postcheck exact); 046 / 049 / 048 applied 2026-11-07 from the merged migration blobs (the 12:05 ops line). The parenthesis is unchanged.
- The S81-08b row: Activation DONE (`ENABLE_LEGACY_FINGERPRINT_READER` ON on `web` since 2026-11-07, deployment cffeb4eb, carried by e313f2e3); the OTA precondition MET; the owner step DONE.
  - Deviation: the ruled sentence "The OTA precondition, the DATED ledger line ..., is MET" turns the frozen RB8-4 row of tests/test_s81_s08b_gate_rows.py red. That row requires the fragment "The OTA precondition is the DATED ledger line of this flip ON" (measured: `s24fin-cmdreaders-exact` status=FAIL rc=1, 1 failed).
  - The committed wording keeps the fragment: "The OTA precondition is the DATED ledger line of this flip ON, and it is MET (the 2026-11-07 09:00 line: deployment cffeb4eb), never the merge:" (`s24fin-cmdreaders`: 510 passed).
- The S81-24 stated-limits row gains L-F1 and L-F2 after L-S24-19 (m-RV2).

## RED rows and mutants
- 199 nodes = 90 RED (50 functions) / 109 PIN (9 functions); at base 90 failed on AssertionError only, 109 passed (GATE GC-2).
- The RED mutation table: 60 mutants, 60 KILLED, 0 survivors (specs/S81_24_RED_REPORT.md).
- Ruling -> rows: R-S24-19 login backoff R10-R16; R-S24-20 TTLs R34; R-S24-21 memo R60 / R61 / R67; R-S24-22 slowapi reset + V2 marker in every route row; R-S24-23 R100-R108; R-S24-24 R68; R-S24-7 the 429 R50 / R51 / P74; R-S24-9 enumeration R21 / R32; R-S24-14 OFF identity P70-P73; R-S24-10 decorator pins P80 / P81; placement R82 / R83; hygiene R90-R93 / P83.
- Fix round 1 rows: F1-R1 (a cancelled durable write whose job raises later: no 'never retrieved' record, exactly one constants-only WARNING; 2 nodes, RED at f8f64d9d on an AssertionError: `[pyt] tag=s24f1-red-head-all start=2026-11-07 11:41:21 end=2026-11-07 11:41:34 elapsed=13s bound=600s status=FAIL rc=1` = 2 failed, 210 passed), F1-R2 (a cancelled gate read: fail-open, no new line; PIN), F1-R3 (the write lands after the outer cancel; PIN); gate rows G24-GR1 (HMAC key = pepper.strip(), kills M58'), G24-GR2 (an unknown endpoint allows and writes no key, kills A17), G24-GR3 (an empty hop-probe header counts as present, `is not None`, kills A15), each green at HEAD and RED on a sha-verified byte-copy mutant (s24f1-mut-GR1 / GR2 / GR3 status=FAIL rc=1, restored sha-equal). The F1-1 mutants (the callback removed; the callback re-raising; the WARNING carrying the message text) are each killed by F1-R1 (s24f1-mut-F1a / F1b / F1c status=FAIL rc=1, AssertionError only, restored sha-equal).
- At the fix HEAD: `[pyt] tag=s24f1-green-off start=2026-11-07 11:41:57 end=2026-11-07 11:42:08 elapsed=11s bound=600s status=OK rc=0` and `[pyt] tag=s24f1-green-on start=2026-11-07 11:42:08 end=2026-11-07 11:42:19 elapsed=10s bound=600s status=OK rc=0` (212 passed each = the frozen 199 + the 13 new nodes).
- At the GREEN HEAD: `[pyt] tag=s24-green-red-off start=2026-11-07 09:01:11 end=2026-11-07 09:01:28 elapsed=17s bound=600s status=OK rc=0` (199 passed) and `[pyt] tag=s24-green-red-on start=2026-11-07 09:01:35 end=2026-11-07 09:01:42 elapsed=6s bound=600s status=OK rc=0` (199 passed; both flags + a synthetic low-entropy pepper + the eight knobs exported in the runner call only).
- Final round: no new test row (RB-S24-3: CLAUDE.md only). After the replay, the frozen file and both fix-round files are byte-identical at their shas (re-hashed first and last from `git show HEAD:<path>`).
- Pin-fix (ruled, RULINGS_PINFIX_S81_24 PF-1): the frozen RED file's P73 /health key assertion tolerates the three documented lifespan pool keys; base blob 7fdf71db... -> new LF blob d48467fe9033bdfb...; the five base keys, the /app/version keys, the HDR_200 set and the no-[HOP_PROBE]-line assertion unchanged; 212 nodes both states after the edit.

## Review chain
- Two adversaries, both NOT_READY, now CLOSED:
  - security F1 (the never-retrieved durable-write exception), by F1-1 with F1-R1..F1-R3;
  - correctness MAJ-C1 (a missed importer), by the widened comm set of record;
  - the minors become stated limits by id: L1 narrowed, L8, L-S24-17, L-S24-18, L-S24-19, m3 (the presence booleans, pinned by G24-GR3), the ints-only reply parser, DAY_KEY_TTL_SECONDS (the ruled name exception) and the CRLF working-copy note.
- Re-verifier NOT_READY (0 blocking / 1 MAJOR / 4 minors):
  - MAJ-RV1 is a measurement-membership gap (the variable-name import_module form), closed by this round's fixpoint closure;
  - m-RV1: this body re-cut with the numstat at HEAD;
  - m-RV2: L-F1 and L-F2 stated in CLAUDE.md and here;
  - m-RV3: the fixpoint closure;
  - m-RV4 (process note): 15 of the 20 environmental ids are CRLF working-copy artefacts, identical on both sides.
- Follow-up S81-04b (Q-F1): `app/services/llm_spend_breaker.py` `_run_bounded_async(durable=True)` gets the same done-callback (flag OFF; classified at its brief).

## Gates (final round, at HEAD a920190b)
- Static checks: ruff --select E9,F63,F7,F82 --no-cache and py_compile are clean on the seven Python files; bytes > 127 = 0 in the four new files; `git diff --stat origin/main...HEAD` shows the eight files, hunks only; every non-CLAUDE.md hunk of both replayed commits has an equal patch-id.
- Unit files (199 frozen + 13 fix-round nodes): `s24fin-unit-off2` 212 passed; `s24fin-unit-on2` 212 passed (both flags, a synthetic low-entropy pepper and the eight knobs exported in that runner call only).
- Pins set of GC-2: `s24fin-pins-off` and `s24fin-pins-on` each 316 passed, 1 skipped. The R8 pair (`s24fin-r8pair`): 273 passed. tests/test_paid_route_metering.py: 21 passed, both unset and exported.
- CI-order set (19 files), `s24fin-ciorder`: 789 passed; the 2 failures are the two baselined test_auth_interceptor social nodes.
- Other readers:
  - the CLAUDE.md readers by the import graph (six files), `s24fin-cmdreaders`: 510 passed;
  - the migration readers (13 test_migration_* + test_s81_kb_schema), `s24fin-migreaders`: 791 passed;
  - tests/test_secret_scan_static.py, `s24fin-secretscan`: 31 passed.
- Comm set of record: 382 files at HEAD.
  - Derivation: the fix round's 370, re-derived by the AST closure to a fixpoint in both directions (including the variable-name import_module form).
  - Closure additions (8):
    - test_s81_d17b_coverage_paging: imports the member test_s81_d17_coverage through a NAME (MAJ-RV1);
    - test_m13_04_full_stream_deadline and test_m18_region_guard_prescoring: imported as support by test_prescoring_showable_guard (m-RV3);
    - test_retro_w1_3: imports test_openai_breaker;
    - test_s81_b1b_url_telemetry: imports test_s80_b1;
    - test_s81_g8_gate_rows, test_s81_s11b_result_aggregates and test_s81_s18b_store_label: import test_s81_s18_kb_first_serve (new on main).
  - Also added: tests/test_migration_041_user_events_public_select_policy.py (a migration reader, RB-S24-3). That makes 379, plus the three S81-24 files = 382.
  - Run at HEAD in 16 chunks of at most 25 files (s24fin-comm-c00..c15, bound 1200).
  - Base at 39ac80ba, built per file and STORED as base_records/39ac80ba.../99bacbe8...: 347 members reused from the G9 RED record fe55771e..., 25 from the daf86d32 records, and 7 run in a detached scratch worktree (76 passed, 0 failed; the worktree was removed).
  - Result: base FAILED = 21 ids; HEAD FAILED before the pin-fix = 33 = the same 21 + the 12 P73 nodes; after the ruled pin-fix (RULINGS_PINFIX_S81_24 PF-1) the chunk that held them (chunk 11) re-ran at HEAD with only its environmental ids and the lifespan-first repro is green: comm -13 EMPTY; comm -23 EMPTY.
- Client fences (jest 29.7.0, node v24.11.1): 14 / 15 suites pass; the only failures are the four config/nativeBundle.w37 drift nodes; b3a is green.
- FULL jest, once (LC-7), from full.json: 3,976 passed, 4 failed (the four w37 nodes), 13 skipped, 13 todo, 410 suites.
- NOT RUN: the four tests/test_precommit_hook*.py (no .githooks change; RB-S24-4). NOT REQUIRED: the corpus gate (no price-pipeline module).

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
- L-F2 (the re-verifier m-RV2) the record-failed WARNING fires once per abandoned failing write with no memo: under a sustained Redis outage one WARNING per abandoned write (log volume only, below Sentry's event level).
- The adversaries' minors not fixed above are stated limits (LC-4); the 'CRLF kept' wording of the GREEN report is a working-copy statement (the committed blobs are LF).

## Flip preconditions and owner steps (names only; a dated ledger line per step)
None to merge. Before `ENABLE_AUTH_THROTTLE_V2` flips: (1) `AUTH_THROTTLE_PEPPER` set on web (the owner generates it; never in a transcript; never a reused pepper); (2) owner item 8 (the Supabase dashboard sign-up and token limits) done; (3) the S81-12 window live (the throttle text; privacy-line mapping R-S24-28: backoff keys = the failed sign-ins line, account keys = the account-linked sign-in records line, interval keys = the short-lived security checks line, the day counter = "up to 24 hours"); (4) the S81-24e client line (ForgotPasswordScreen maps RATE_LIMITED to common.errors.rateLimited) live in a post-approval OTA (R-S24-25); (5) the owner's explicit yes, then a canary that BEGINS with one scripted pass per endpoint (synthetic email, flag ON, pepper set) reading the throttled / skipped lines (R-S24-29), then real traffic reading the `[AUTH_THROTTLE] throttled` count per endpoint, never an edge 429 count (CR2). Rollback: unset the flag (per call; keys expire within 24 h).
Probe (R-S24-23): a dated names-only read of `FORWARDED_ALLOW_IPS` on web first; `ENABLE_HOP_PROBE_LOG` ON only after the deploy settles; from one public IP one plain GET /health and one with a forged single TEST-NET X-Forwarded-For; pick the two lines by timestamp (the Railway healthcheck also hits /health); the booleans land as a dated ledger line; unset the flag.

## Follow-ups
S81-24b (phase 2 after the probe: per-IP / per-device keys, the m13_02 leftmost pin, #299, the GoTrue secret-key client + Sb-Forwarded-For, SMTP, the W1-9b retirement after a canary); S81-24c (test-only: retire the string-presence limiter tests); S81-24d (the register enumeration contract); S81-24e (the client ForgotPassword RATE_LIMITED mapping).

## [NATIVE READ]
EMPTY (no Arabic string in this unit).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
