# S81-24 RED REPORT (AUTH-THROTTLE-V2 phase 1 + MS4 HOP-PROBE), RED agent Opus 5.5, 2026-11-07

Base daf86d32d222a885c42dc537e83c25483527a83b. Spec e545cd4a... as amended by the review (B1-B3, C1-C9, RC1-RC5) and RULINGS_S81_24 (R-S24-19..32). Reports written through the shell (python / quoted heredoc), never the Write tool.

## Files
- NEW (the only file in the real worktree): tests/test_s81_s24_auth_throttle.py, sha256 7fdf71db5b2cc43e34b24674b62d3eb57e117b1c8fa683719471b10c4c562228, 84,820 bytes, pure ASCII (0 bytes > 127), LF (0 CRLF); py_compile + ruff E9,F63,F7,F82 clean.
- Real worktree after: `git status --short` = `?? tests/test_s81_s24_auth_throttle.py` only; `git diff --stat` empty; HEAD daf86d32; no .qa-mutation.lock.
- Scratch worktree <scratchpad>/s24p (detached daf86d32, no junction): created, used for the prototype + mutants, removed (`git worktree remove --force`), absent from `git worktree list`, directory gone.

## Nodes (59 test functions; 199 nodes)
- RED: 50 functions = 90 nodes (R01-R07, R10-R16, R20-R22, R30-R34, R40-R42, R50-R51, R60-R68, R82-R83, R90-R93, R100-R105, R107, R108).
- PIN: 9 functions = 109 nodes (P70 x18 = 3 cases x 6 OFF spellings; P71 x72 = 12 cases x 6; P72; P73 x12; P74 x2; P80; P81; P83; P106).
- At base: 90 failed / 109 passed; every failure ends `tests/test_s81_s24_auth_throttle.py:<n>: AssertionError` (90 / 90 counted in the log); 0 RED node passes at base; 0 PIN node fails at base.
- Prototype, flags unset: 199 passed. Prototype with ENABLE_AUTH_THROTTLE_V2=true + AUTH_THROTTLE_PEPPER (synthetic) + all eight knobs + ENABLE_HOP_PROBE_LOG=true exported in the runner call only: 199 passed (the autouse fixture resets every flag, knob and the pepper per row, so the ambient state cannot leak).

## Row map (amendments applied)
- R01 module surface: FLAG, PEPPER_ENV, ENDPOINTS, KNOBS {name: (default, lo, hi)} incl. the timeout (0.5, 0.05, 5.0), the six scripts, gate / record_login_failure / record_login_success coroutines, digest / email_ident / account_ident / throttle_key / riyadh_day_compact / seconds_to_riyadh_midnight / knob / redis_timeout_seconds / _eval / _parse_reply / _pool / _now_ms / _monotonic / _reset_pepper_warning / _reset_skip_memo, THROTTLED_MESSAGE (== the error_handler literal), SKIP_LOG_MEMO_SECONDS 60, DAY_KEY_TTL_SECONDS 86400.
- R02 flag idiom (13 nodes); R03 knobs defensive per call (out of range -> the default, C5 deliberate); R04 the six frozen Lua texts + sha256; R05 key grammar + HMAC digest; R06 pepper unset / blank = allow, zero Redis calls, ONE `[AUTH_THROTTLE] pepper unset`; R07 Riyadh day (vs llm_spend_breaker.riyadh_day).
- R10 COUNT-ONLY backoff (R-S24-19): 8 consecutive counted failures, each followed by an immediate retry: 401 each time with [LOGIN_GATE, LOGIN_FAIL]; the retries 429 with 1, 2, 4, 8, 16, 30, 30, 30 (cap 30) AND the V2 marker (count = n). R11 success clears (CLEAR issued; next wait 1 again). R12 four non-credential results: GATE only, never FAIL, no key. R13 default cap 60 (1, 2, 4, 8, 16, 32, 60...). R14 the gate EVAL precedes the W1-9b get and login_user; a refused login calls nothing else and issues exactly one EVAL. R15 the W1-9b sequence ON = [eval GATE, get, set(nx, ex=900), incr, expire(900, nx), eval FAIL] / [eval GATE, get, delete, eval CLEAR]. R16 (amended) five concurrent FIRST gates ALL pass; after one counted failure five concurrent gates all 429 retry 1.
- R20 register interval 20 s (+ marker), register_user not called on a refusal; R21 existence-blind refusals; R22 (Q11) consent refusal arms nothing, consent-complete request one INTERVAL EVAL.
- R30 reset interval 15 s + per-day 3 (the 4th -> retry = seconds to the Riyadh midnight = 39555 at 10:00:45Z), a new day key after 21:00Z; R31 resend on its own keys, same cycle; R32 reset existence-blind; R33 reset never blocked by a 30 s login backoff; password-recovery issues no EVAL; R34 (R-S24-20) INTERVAL ARGV ttl = the interval (20), RESET interval TTL = 15 and day 86400 on the first increment only, LOGIN_FAIL TTL = the TTL knob (7200) and max(TTL, cap) when TTL 60 / cap 120, ACCOUNT TTL = the window (120).
- R40 / R41 the per-account window (2 per 120 s) on PUT /password and PUT /email, keyed on the user id digest, no login key touched, the window reopens; R42 the W1-9b calls kept after the ACCOUNT EVAL.
- R50 V2 429 == slowapi 429 (key order, types, header names, Retry-After); R51 retry 0 / -3 -> 1.
- R60 (B2) client None: the exact per-route skipped list: login failure [login, login_fail], login success [login, login_clear], every other route [its endpoint], type RedisUnconfigured, WARNING; R61 ConnectionError the same lists; R62 timeout 0.05 s vs a 0.5 s EVAL: allow within 0.4 s, TimeoutError; R63 eight malformed replies -> ValueError; R64 FAIL / CLEAR raising: 401 / 200 unchanged, login_fail / login_clear lines; R65 log hygiene (every [AUTH_THROTTLE] line full-matches a template, no email / local part / pepper / user id / key / 32-hex); R66 bad idents; R67 (R-S24-21) the per-endpoint 60 s memo with the _monotonic seam and the _reset_skip_memo seam; R68 (R-S24-24) on a 1-worker pool held busy: a CANCELLED record_login_failure and a TIMED-OUT record_login_success both land after release, the timed-out gate never runs (cancellable).
- R82 / R83 AST placement (the If on auth_throttle_v2_enabled() with one awaited gate / record call; first statement, register right after the consent If, resend outside the try; non-gated routes carry no auth_throttle name; the import line present).
- R90 AUTH_THROTTLE_PEPPER in CREDENTIALS_UNSET, no DEVICE_KEY pepper in the leaf; R91 leaf imports (stdlib + fastapi + `from app.services import cache_service as _cache_service` only) + `_eval` identical on both fake shapes; R92 hygiene (ASCII, LF, no G1 needle, no gitleaks-keyword hex constant, none of BeautifulSoup / QarenBot / kb_ / chat.completions); R93 (C8) POOL_WORKERS 4, POOL_THREAD_PREFIX auth-throttle, built lazily once with that prefix.
- R100 / R101 (C2: TestClient client=("100.64.0.1", 50000)) exact [HOP_PROBE] lines incl. the trailing `uvicorn_forwarded_allow_ips_set=false`; R102 paths only (POST /login, GET /, GET /api/v1/usage/status, HEAD /health, POST /health, GET /healthz: none); R103 no value (incl. the FORWARDED_ALLOW_IPS value) and no IPv4 shape in any line; R104 garbage headers (count = non-empty entries); R105 flag idiom per request; R107 (R-S24-23) the boolean = NAME presence (unset false, set true, "" true); HOP_PROBE_PATHS == ("/health", "/api/v1/app/version") (Q10); R108 (C3) a stub scope with client None logs one line with the peer booleans false; a request whose headers raise logs nothing and does not raise.
- P70 / P71 flag-OFF identity (six spellings x every case) with the FULL configuration (pepper + eight non-default knobs) and ONE recorder as BOTH auth_service.redis_client and cache_service.redis_client: status, body fields, header names, Retry-After, the exact W1-9b recorder sequence, the service call order, the app.* log records (only the base resend ERROR line), no EVAL, no [AUTH_THROTTLE] / [HOP_PROBE] line, the pool unbuilt. P72 a mixed OFF sequence. P73 hop flag OFF (six spellings) with V2 ON or OFF: silent, base body keys (/health without lifespan: 5 keys, no adapter_executor). P74 the 429 contract both states (redis None). P80 (Q8) the 15-route decorator table + `_EXPIRED_LOGOUT_BUDGET = parse_rate_limit('10/minute')`; P81 decorator order; P83 (C6) the RED file's own setenv hygiene, ASCII, LF, no G1 needle; P106 the probe paths identical ON vs OFF.
- Every route row resets the slowapi storage before EACH request (`_send` -> limiter.reset(), R-S24-22) and every V2 -> 429 assertion goes through `_expect_v2_429` (code, error, the `[AUTH_THROTTLE] throttled endpoint=<e> count=<n> retry_after=<s>` marker for that request, retry_after_seconds == Retry-After == the marker's retry). R50 / P74 deliberately do NOT reset between their 4 posts (they need the slowapi 429).
- Rows that drive more than four consecutive login failures (R10, R13, R33) lift the W1-9b `failed_login:*` counter from the fake after each failure (`_lift_lockout`): otherwise the untouched 5-in-15-min lockout answers the 6th with ACCOUNT_LOCKED (measured at the first prototype run); the lockout itself stays pinned by R15 / P70 / P71.

## The amended Lua (LF join, no trailing LF; sha256)
LOGIN_GATE_SCRIPT 8adceb7c822c392167dd7ae3d6b8f52e929d9d35cc634571d5be2dc70cd81315 (KEYS[1] the backoff hash; ARGV [now_ms]; read-only, count-only):
    local u = tonumber(redis.call('HGET', KEYS[1], 'u') or '0')
    local c = tonumber(redis.call('HGET', KEYS[1], 'c') or '0')
    local now = tonumber(ARGV[1])
    if now < u then return {0, math.ceil((u - now) / 1000), c} end
    return {1, 0, c}
LOGIN_FAIL_SCRIPT 941fa5bc181ff187592dcb384dfb52e358365ed0b6dc9cb39ea1abb0f4f9d578 (ARGV [now_ms, cap_ms, ttl_s]; the c-th failure arms min(2^(c-1) s, cap)):
    local c = redis.call('HINCRBY', KEYS[1], 'c', 1)
    local w = 1000
    for i = 2, math.min(c, 23) do w = w * 2 end
    if w > tonumber(ARGV[2]) then w = tonumber(ARGV[2]) end
    redis.call('HSET', KEYS[1], 'u', tonumber(ARGV[1]) + w)
    redis.call('EXPIRE', KEYS[1], ARGV[3])
    return c
LOGIN_CLEAR_SCRIPT d5c2157a7f09aca2b3faee49953d80b5905a98c0afadb442553830b3952e58a1 (text unchanged): return redis.call('DEL', KEYS[1])
INTERVAL_SCRIPT 8d04ebbf..., RESET_SCRIPT 963aab43..., ACCOUNT_SCRIPT 8e3153ec...: texts UNCHANGED from spec 2.4 (shas equal); R-S24-20 changes their ARGV only: INTERVAL ARGV[3] = the interval s; RESET ARGV[4] = the interval s, ARGV[5] = 86400; ACCOUNT ARGV[4] = the window s. LOGIN_FAIL ARGV[3] = max(AUTH_THROTTLE_TTL_SECONDS, cap). The six FROZEN_SCRIPT_SHA256 values are pinned in R04.

## Prototype (thrown away; scratch worktree <scratchpad>/s24p)
- NEW app/services/auth_throttle.py (sha256 b98fd0e72af4082e081e656974f8cff7cb01a67cb82b21d79a2770377c04511d, LF, ASCII; copy at <scratchpad>/S81-24_red/proto/auth_throttle.final.py).
- git diff --stat (hunks only, CRLF preserved): app/api/auth_routes.py +18 (the import, six gates, two record guards), app/middleware/request_id.py +60 (imports, logger, HOP_PROBE_PATHS, hop_probe_log_enabled, _ip, _b, _log_hop_probe with the uvicorn boolean, the one guarded call), tests/_env_safety.py +2; 3 files, 80 insertions. CLAUDE.md not edited. Full diff <scratchpad>/S81-24_red/proto.diff; the apply script apply_proto.py.
- Seats: login gate before `# Check brute-force lockout`; record_login_failure after `await track_failed_login(body.email)` inside the failure If; record_login_success after `await clear_failed_logins(body.email)`; register after the consent If; reset / resend first statement (resend outside the try); the account gates before `email = current_user.get("email") or ""`.
- API the RED binds for GREEN: KNOBS dict + knob(name) + redis_timeout_seconds(); _POOL global + _pool() + POOL_WORKERS + POOL_THREAD_PREFIX; _now_ms / _monotonic seams; _reset_pepper_warning / _reset_skip_memo seams; SKIP_LOG_MEMO_SECONDS; DAY_KEY_TTL_SECONDS; _run(..., durable=True) = wait_for(shield(wrap_future)) for FAIL / CLEAR only; gate order: endpoint, ident, digest (pepper), client, EVAL; request_id: hop_probe_log_enabled, _log_hop_probe, HOP_PROBE_PATHS, the line's LAST field uvicorn_forwarded_allow_ips_set.

## Mutation table (60 mutants: the spec's 36 as amended + 24 for the amended rows; each on the prototype's bytes in the scratch worktree under .qa-mutation.lock, the whole unit file via pyt.py bound 600, restored from the in-memory byte copy and sha256-compared after every mutant; all four files re-verified equal to proto_shas.txt at the end)

| id | mutant | result | killing rows (test functions) |
|---|---|---|---|
| M01 | login gate guard -> if True | KILLED | test_p70_off_identity_login, test_p72_off_no_throttle_records, test_r82_v2_placement_ast |
| M02 | reset gate guard -> if True | KILLED | test_p71_off_identity_other_routes, test_p72_off_no_throttle_records, test_r82_v2_placement_ast |
| M03 | flag truthy set drops on | KILLED | test_r02_flag_idiom_per_call |
| M04 | knob range check removed | KILLED | test_r03_knobs_defensive_per_call |
| M05 | LOGIN_GATE now < u -> now <= u (Lua text) | KILLED | test_r04_scripts_frozen, test_r10_login_backoff_sequence, test_r11_success_clears, test_r12_only_credential_failures_count, test_r13_default_cap, test_r14_login_placement_order (+6) |
| M06 | digest without the pepper | KILLED | test_r05_key_grammar_and_digest, test_r40_change_password_account_window, test_r41_update_email_account_window |
| M07 | email_ident drops lower() | KILLED | test_r05_key_grammar_and_digest |
| M08 | digest [:32] -> full 64 | KILLED | test_r05_key_grammar_and_digest, test_r40_change_password_account_window, test_r41_update_email_account_window |
| M09 | pepper unset -> refuse 429 | KILLED | test_r06_pepper_unset_fail_open_once |
| M10 | pepper warning latch removed | KILLED | test_r06_pepper_unset_fail_open_once |
| M11 | RIYADH_UTC_OFFSET_HOURS 3 -> 0 | KILLED | test_r07_riyadh_day, test_r30_reset_interval_and_day, test_r31_resend_own_keys |
| M12 | record_login_failure counts every failure | KILLED | test_r12_only_credential_failures_count |
| M13 | record_login_success line deleted | KILLED | test_r11_success_clears, test_r15_w19b_untouched_on, test_r60_no_client_fail_open, test_r61_eval_raises_fail_open, test_r64_record_failures_harmless, test_r83_login_record_placement_ast |
| M14 | login gate moved after login_user | KILLED | test_r14_login_placement_order, test_r15_w19b_untouched_on, test_r82_v2_placement_ast |
| M15 | await track_failed_login(body.email) deleted | KILLED | test_p70_off_identity_login, test_r15_w19b_untouched_on, test_r83_login_record_placement_ast |
| M16 | cap ARGV in seconds | KILLED | test_r10_login_backoff_sequence, test_r11_success_clears, test_r13_default_cap, test_r33_reset_never_blocked_by_login, test_r34_ttls |
| M17 | RESET per_day ARGV = knob + 1 | KILLED | test_r30_reset_interval_and_day, test_r31_resend_own_keys, test_r34_ttls |
| M18 | day-cap retry ARGV = the interval | KILLED | test_r30_reset_interval_and_day, test_r31_resend_own_keys |
| M19 | change_password ident -> email | KILLED | test_r40_change_password_account_window, test_r82_v2_placement_ast |
| M20 | 429 code RATE_LIMITED -> THROTTLED | KILLED | test_r10_login_backoff_sequence, test_r11_success_clears, test_r13_default_cap, test_r14_login_placement_order, test_r20_register_interval, test_r21_register_existence_blind (+8) |
| M21 | max(1, retry) removed | KILLED | test_r51_retry_after_at_least_one |
| M22 | gate fail-open except narrowed to ConnectionError | KILLED | test_p74_429_contract_both_states, test_r60_no_client_fail_open, test_r62_eval_timeout_fail_open, test_r63_malformed_reply_fail_open, test_r67_skip_memo_per_endpoint, test_r68_record_writes_shielded_gate_cancellable |
| M23 | _parse_reply accepts bool | KILLED | test_r63_malformed_reply_fail_open |
| M24 | throttled line adds key= | KILLED | test_r10_login_backoff_sequence, test_r11_success_clears, test_r13_default_cap, test_r14_login_placement_order, test_r20_register_interval, test_r21_register_existence_blind (+9) |
| M25 | day key TTL ARGV = TTL knob | KILLED | test_r34_ttls |
| M26 | resend gate moved inside the try | KILLED | test_r31_resend_own_keys, test_r82_v2_placement_ast |
| M27 | reset gate endpoint literal -> login | KILLED | test_r30_reset_interval_and_day, test_r31_resend_own_keys, test_r32_reset_existence_blind, test_r33_reset_never_blocked_by_login, test_r34_ttls, test_r50_v2_429_equals_slowapi_429 (+4) |
| M28 | echo flag check removed | KILLED | test_p73_hop_probe_off_silent, test_r104_hop_probe_garbage, test_r105_hop_probe_flag_idiom |
| M29 | / added to HOP_PROBE_PATHS | KILLED | test_r102_hop_probe_paths_only, test_r107_hop_probe_uvicorn_boolean |
| M30 | echo line adds the leftmost value | KILLED | test_r100_hop_probe_health_line, test_r101_hop_probe_version_headers, test_r103_hop_probe_no_values, test_r104_hop_probe_garbage, test_r107_hop_probe_uvicorn_boolean, test_r108_hop_probe_client_none_and_raising_request |
| M31 | leftmost / rightmost swapped | KILLED | test_r100_hop_probe_health_line |
| M32 | peer_public = not is_private | KILLED | test_r100_hop_probe_health_line, test_r101_hop_probe_version_headers |
| M33 | AUTH_THROTTLE_PEPPER entry removed | KILLED | test_r90_pepper_in_credentials_unset |
| M34 | by-name redis_client import | KILLED | test_r10_login_backoff_sequence, test_r11_success_clears, test_r12_only_credential_failures_count, test_r13_default_cap, test_r14_login_placement_order, test_r15_w19b_untouched_on (+22) |
| M35 | login limiter 5/minute -> 6/minute | KILLED | test_p80_decorator_table_ast |
| M36 | register interval_ms = interval seconds | KILLED | test_r20_register_interval, test_r21_register_existence_blind, test_r34_ttls |
| M37 | LOGIN_GATE pre-arms (the withdrawn spec form, Lua text) | KILLED | test_r04_scripts_frozen, test_r10_login_backoff_sequence, test_r11_success_clears, test_r12_only_credential_failures_count, test_r13_default_cap, test_r14_login_placement_order (+6) |
| M38 | register interval key TTL = TTL knob | KILLED | test_r34_ttls |
| M39 | account key TTL = TTL knob | KILLED | test_r34_ttls |
| M40 | reset interval key TTL = TTL knob | KILLED | test_r34_ttls |
| M41 | skip memo removed | KILLED | test_r67_skip_memo_per_endpoint |
| M42 | skip memo global, not per endpoint | KILLED | test_r60_no_client_fail_open, test_r61_eval_raises_fail_open, test_r64_record_failures_harmless, test_r67_skip_memo_per_endpoint |
| M43 | memo window 60 -> 600 | KILLED | test_r01_module_surface, test_r67_skip_memo_per_endpoint |
| M44 | the V2 throttled marker line removed | KILLED | test_r10_login_backoff_sequence, test_r11_success_clears, test_r13_default_cap, test_r14_login_placement_order, test_r20_register_interval, test_r21_register_existence_blind (+9) |
| M45 | uvicorn boolean always false | KILLED | test_r103_hop_probe_no_values, test_r107_hop_probe_uvicorn_boolean |
| M46 | uvicorn boolean reads the value | KILLED | test_r107_hop_probe_uvicorn_boolean |
| M47 | record writes not shielded | KILLED | test_r68_record_writes_shielded_gate_cancellable |
| M48 | the gate read shielded too | KILLED | test_r68_record_writes_shielded_gate_cancellable |
| M49 | LOGIN_FAIL write not durable | KILLED | test_r68_record_writes_shielded_gate_cancellable |
| M50 | POOL_WORKERS 4 -> 8 | KILLED | test_r93_pool_shape |
| M51 | pool thread prefix changed | KILLED | test_r93_pool_shape |
| M52 | echo bare except removed | KILLED | test_r108_hop_probe_client_none_and_raising_request |
| M53 | echo crashes on client None | KILLED | test_r108_hop_probe_client_none_and_raising_request |
| M54 | register gate before the consent check | KILLED | test_r22_register_gate_after_consent, test_r82_v2_placement_ast |
| M55 | update_email ident -> email | KILLED | test_r41_update_email_account_window, test_r82_v2_placement_ast |
| M56 | echo also on HEAD | KILLED | test_r102_hop_probe_paths_only |
| M57 | day key by the UTC day | KILLED | test_r30_reset_interval_and_day, test_r31_resend_own_keys |
| M58 | pepper not stripped | KILLED | test_r06_pepper_unset_fail_open_once |
| M59 | login record placed before track_failed_login | KILLED | test_r15_w19b_untouched_on, test_r83_login_record_placement_ast |
| M60 | account window reset off (per_window ARGV = window) | KILLED | test_r34_ttls, test_r40_change_password_account_window, test_r41_update_email_account_window |

60 / 60 KILLED, 0 survivors, 0 equivalent. Each kill includes at least one AssertionError row; M22 also raises (CancelledError / RedisUnconfigured / TimeoutError / ValueError escape the narrowed except, the intended failure), M27 / M34 also an IndexError in one row. M52 first died on a RuntimeError only; R108 was made assertion-only (the raising call is caught and asserted) and M52 re-run: KILLED by AssertionError. The test-file edit after batches 1-2 touched only R108's Boom block, so the other 59 results stand. Per-mutant logs <scratchpad>/S81-24_red/mut/M*.log; JSON mutants_all.json.

## Every [pyt] line (logs under <scratchpad>/S81-24_red/)
- [pyt] tag=s24-red-base1 start=2026-11-07 08:17:00 end=08:17:11 elapsed=11s bound=600s status=FAIL rc=1 (102 failed / 97 passed: 12 P73 nodes red on the /health adapter_executor key, fixed: no lifespan in the TestClient)
- [pyt] tag=s24-red-base2 start=2026-11-07 08:17:36 end=08:17:46 elapsed=10s bound=600s status=FAIL rc=1 (90 failed / 109 passed)
- [pyt] tag=s24-red-proto-off start=2026-11-07 08:21:02 end=08:21:09 elapsed=7s bound=600s status=FAIL rc=1 (6 failed: test-side fixes R07 datetime arg, the W1-9b lockout lift, the R63 None sentinel, the R104 count)
- [pyt] tag=s24-red-proto-off2 start=2026-11-07 08:21:36 end=08:21:42 elapsed=6s bound=600s status=OK rc=0 (199 passed)
- [pyt] tag=s24-red-proto-on start=2026-11-07 08:21:53 end=08:21:59 elapsed=6s bound=600s status=OK rc=0 (199 passed)
- [pyt] tag=s24-red-base3 start=2026-11-07 08:21:59 end=08:22:10 elapsed=11s bound=600s status=FAIL rc=1 (90 failed / 109 passed)
- [pyt] tag=s24-mut-M01 .. s24-mut-M60: 61 runs (M52 twice), each elapsed 7-10s bound=600s status=FAIL rc=1 (= killed); 08:23:59 .. 08:31:59
- FINAL (the frozen bytes 7fdf71db...):
  [pyt] tag=s24-red-final-base start=2026-11-07 08:32:12 end=2026-11-07 08:32:23 elapsed=11s bound=600s status=FAIL rc=1 -- 90 failed, 109 passed; [hermeticity] sentinel checked 199 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
  [pyt] tag=s24-red-final-proto-off start=2026-11-07 08:32:24 end=2026-11-07 08:32:30 elapsed=6s bound=600s status=OK rc=0 -- 199 passed; [hermeticity] 199; [netguard] blocked 0
  [pyt] tag=s24-red-final-proto-on start=2026-11-07 08:32:30 end=2026-11-07 08:32:36 elapsed=6s bound=600s status=OK rc=0 -- 199 passed; [hermeticity] 199; [netguard] blocked 0
- CI-order set (the spec's 1.10 seventeen files + tests/test_s81_s08b_legacy_fingerprint.py (C9 P13 / p14) + tests/test_retro_w1_1.py (the middleware-order pin); list ci_order_set.txt):
  [pyt] tag=s24-red-ci-base start=2026-11-07 08:32:48 end=2026-11-07 08:33:42 elapsed=55s bound=1200s status=FAIL rc=1 -- 2 failed, 789 passed, 1 skipped, 2 deselected; [hermeticity] sentinel checked 792; [netguard] blocked 18 attempt(s) from 11 node(s) (the neutralized.supabase.invalid sentinel)
  [pyt] tag=s24-red-ci-proto start=2026-11-07 08:33:43 end=2026-11-07 08:34:39 elapsed=56s bound=1200s status=FAIL rc=1 -- 2 failed, 789 passed, 1 skipped, 2 deselected; same hermeticity / netguard lines
  Both FAILED sets = {tests/test_auth_interceptor.py::test_sign_in_with_social_exception, ::test_social_login_user_insert_fails_gracefully} (baselined, tests/.pre_impl_failures.txt); comm -13 base vs prototype = EMPTY: no existing pin reddens (the 429 contract, the four middleware-order pins, the W1-9b pins, s05 p01, s08b P13 / p14, conftest env safety all green).
- [pyt] tag=s24-red-pins-proto-on start=2026-11-07 08:34:50 end=2026-11-07 08:35:22 elapsed=32s bound=600s status=OK rc=0 -- 316 passed, 1 skipped, 2 deselected (test_429_contract, test_s81_s05_request_context, test_retro_w1_9, test_retro_w1_1, test_brute_force, test_retro_w1_9_429, test_conftest_env_safety at the prototype with ENABLE_AUTH_THROTTLE_V2=true + a synthetic AUTH_THROTTLE_PEPPER + ENABLE_HOP_PROBE_LOG=true exported in the runner call only)
- [pyt] tag=s24-red-secretscan-base start=2026-11-07 08:35:22 end=2026-11-07 08:35:29 elapsed=7s bound=600s status=OK rc=0 -- tests/test_secret_scan_static.py alone at base (with the RED file present): 31 passed; [netguard] blocked 0
- [pyt] tag=s24red-comm-c00 start=2026-11-07 08:40:28 end=2026-11-07 08:40:52 elapsed=24s bound=1200s status=OK rc=0 -- 85 passed; [hermeticity] 85; [netguard] blocked 0
- No TIMEOUT, no DUPLICATE. The live-process check (Win32_Process) was made once, at 08:40 before the comm chunk: only the two stall_monitor.py processes, no foreign pytest; the earlier runs did not check first (they were short, 6-56 s).

## Comm set and its base record (R-S24-31), built LAST
- Derivation at daf86d32 (derive_comm.py over `git ls-tree HEAD tests`): names (auth_routes / auth_service / rate_limiter / error_handler / request_id / _env_safety / auth_throttle / the /api/v1/auth, /api/v1/app/version, /health strings) UNION the app.main importers UNION the walkers (Path("app, "app/, rglob, .glob, inspect.getsource, ast.parse, os.listdir, scandir, os.walk) UNION the CLAUDE.md readers (string + the import graph: test_s81_s08b_gate_rows via test_s81_s08b_legacy_fingerprint) UNION the SmartCompareApp scanners UNION the named pins (incl. test_migration_index_predicate_immutability, test_openai_key_log_hygiene_s69, test_model_config*, test_prompt_fence, test_u3c_store_false_pin, test_start_command*, test_sentry_channels_u8d_unit) MINUS the four test_precommit_hook*.py: 262 members, ALL inside the spec's 364; the spec's wider walker class adds 102. Union = the spec's 364, additions 0, removals 0; checked the tests-dir walkers and the uvicorn / FORWARDED_ALLOW_IPS readers: the two outside the set (test_price_parse_offload, test_url_validator_offloop_hops) name uvicorn in prose only.
- COMM_SET.txt = 364 files, sha256 a9a3f4b3568ce39f3a9108bae21cb38c5f669d9d6cb91ab73bbdd600fc6ea0e7 (= the spec's set sha); comm_reasons.tsv = file / union reasons / base-record source. The RED file and the GREEN gate-rows file are HEAD-only (GREEN adds them).
- Reuse / run split: 350 REUSED OUTRIGHT from the same-sha record daf86d32/ea0d2f1b... (712, G8 RED); 7 REUSED per file under GC-9 from 05ccaed2/48158306... (bytes unchanged 05ccaed2 -> daf86d32, no compare_runs / cron_compare_judge / text_routes / image_routes / url_routes / CLAUDE.md / the three S81-22 test names, no app.main / app.api / TestClient, no walker): test_delete_user_cascade, test_m13_02_proxy_aware_ratelimit, test_migration_027 / 029 / 030 / 031, test_sqlfluff_config; 7 RUN at daf86d32 in the real worktree (one chunk, s24red-comm-c00, 85 passed): test_audit_logging, test_gitleaks_config, test_price_source, test_skill_frontmatter, test_yotpo_reviews (not in the 05ccaed2 record), test_migration_042_search_logs_is_synthetic (walker), test_migration_044_apple_siwa_tokens (names + walker).
- STORED: <scratchpad>/harness/base_records/daf86d32d222a885c42dc537e83c25483527a83b/a9a3f4b3568ce39f3a9108bae21cb38c5f669d9d6cb91ab73bbdd600fc6ea0e7.{files,header.txt,txt,pyt.log}; FAILED = 20 ids, all environmental (the stored records' ids restricted to this set): auth_interceptor x2, prompt_truth cold-tiktoken x2, s81_d16 r10, s81_d17 r9, s81_d22c p1 x5, s81_s10 r06, s81_s16 r27 x5, s81_s19 r15, s81_s22 b02, s81_s22_judge j01.
- Not run here (as ruled): the corpus gate (no price-pipeline module); the fourteen client fences + b3a (GREEN, through the orchestrator's junction); the four test_precommit_hook*.py (NOT RUN: no .githooks change).

## RC2 anchors re-measured at daf86d32 (review RC2 confirmed)
register_user await :711; login: check_account_locked :808, login_user :829, track_failed_login :832, clear_failed_logins :849; update_email: check_account_locked :1223, update_user_email :1227; change_password: check_account_locked :1254, change_user_password :1258. Limiter lines as spec 1.1 (P80 pins the 15-row table by AST).

## Deviations from the spec (all ruled amendments applied; these are the RED's own choices)
- D1 R16 rewritten for R-S24-19 (five concurrent first attempts all pass; a refusal only after a recorded failure); L9 withdrawn accordingly.
- D2 R34 rewritten for R-S24-20 (interval / account keys expire at their own interval / window; the TTL knob governs the login backoff only, effective max(TTL, cap)); the spec's 2.2 sentence "effective TTL = max(TTL knob, the window)" now applies to the backoff key only.
- D3 New rows beyond the spec's 45 + 8: R67 (memo), R68 (shield + cancellable gate), R93 (C8 pool), R107 (uvicorn boolean), R108 (C3 client None + raising request), P83 (C6 setenv hygiene); R60 / R61 carry the B2 per-route record lists.
- D4 The RED names API the spec left open: `knob(name)` + `KNOBS` (name -> (default, lo, hi)), `_POOL`, `POOL_THREAD_PREFIX`, `_monotonic`, `_reset_skip_memo`, `SKIP_LOG_MEMO_SECONDS`, `DAY_KEY_TTL_SECONDS`; GREEN implements them by these names.
- D5 Route rows driving more than four login failures lift the W1-9b counter (`_lift_lockout`) so the V2 backoff is measured alone; the spec's R10 / R13 text did not account for the 5-in-15-min lockout.
- D6 P73 / P106 read /health without a lifespan (TestClient not entered): 5 body keys (no adapter_executor), not the spec probe's 6.
- D7 R104 count for "not-an-ip, , 300.1.1.1" is 2 (non-empty entries), per 2.8.
- D8 The uvicorn boolean is the LAST field of the [HOP_PROBE] line (`... peer_public=<b> uvicorn_forwarded_allow_ips_set=<b>`); a NAME set to "" counts as set.
- D9 The CI-order set = the spec's 1.10 seventeen files + test_s81_s08b_legacy_fingerprint.py (C9) + test_retro_w1_1.py (middleware order): 19 files.

## Open questions for the gate
- Q-R1 Pepper unset: the RED pins ONE `[AUTH_THROTTLE] pepper unset` per process and NO `skipped` line (spec 2.9 / R06); R-S24-21 B2 says "the exact per-route record list under an unset client / pepper". The RED applies the B2 list to the unset CLIENT (R60). Rule whether an unset pepper must also emit `skipped ... type=<PepperUnset>` lines (R06 would change).
- Q-R2 The fake models Upstash's integer replies; a real Upstash REST reply for a Lua table of ints is a JSON array of ints (assumed, not measured: no network). The R-S24-29 scripted canary pass is the first real execution.
- Q-R3 R68 pins that a timed-out GATE read never runs once dequeued (cancellable, R-S24-24); a GREEN that shields the gate is killed (M48).

## Restore check
- Real worktree sc-s81-s24: HEAD daf86d32; `git status --short` = `?? tests/test_s81_s24_auth_throttle.py` only; `git diff --stat` empty (every tracked file equal to the base); no .qa-mutation.lock; no tracked file, requirement, .pre_impl_failures, .env or CLAUDE.md touched; no flag / knob / pepper in any .env or the OS environment (exported in single runner calls only).
- Scratch worktree removed (`git worktree remove --force`), absent from `git worktree list`, directory gone; prototype files sha-verified against proto_shas.txt after the last mutant; no orphan pytest (no pytest process live at the end).
- Files: <scratchpad>/S81-24_red/{RED_REPORT.md, COMM_SET.txt, comm_reasons.tsv, notes.md, progress.txt, mutants_all.json, mutation_table.txt, proto.diff, proto/, mut/*.log, *.log} and <scratchpad>/S81-24_RED_REPORT.md (identical copy), written through the shell.
