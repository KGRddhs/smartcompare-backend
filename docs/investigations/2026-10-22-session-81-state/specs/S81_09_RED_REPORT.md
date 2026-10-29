# S81-09 DEVICE-QUOTA-RIYADH -- RED report

- Agent: RED agent, Opus 5.5 (claude-opus-5-5). Written THROUGH THE SHELL (report_gen.py run by the venv python; the harness refuses a subagent Write of a report .md).
- Base: e7c81956f11749b1378aa449c4ac616c82bfe6a9 (worktree sc-s81-s09 detached; HEAD verified before and after). Notes folder: C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red
- Inputs read in full: s81-common.txt (twice; the 15:05 LEANER CHAIN section LC-1..LC-9 and MOVING MAIN 6c14ac95 read before reporting), RULINGS_S81_09 (R-S09-1..15 + Measurement rulings), the spec (sha 33fd9b53, 493 lines), the review (sha de7ae5af, 111 lines), S81_09_BRIEF, PLAN_S81 (context, standing constraints, the VERIFY quota bullets, M3, flip order, owner decisions), the S81-08 readers at sc-s81-s08 HEAD bcf75f84 (git show, read-only).
- Timing: first tool call about 13:12 AST, report about 16:15 AST (about 3 h against the 90 min budget). The overrun is load: the box slowed mid-run (a mutant run grew from 5 s to 123 s, comm chunk 04 took 585 s, a plain ls 6 s); every gate still ran to completion.

## 1. Files written in the real worktree (only these two; untracked)

| file | bytes | sha256 |
|---|---|---|
| tests/test_s81_s09_device_quota.py | 87170 | 843a6bab0215ca5289482a13f52646d9f9bbb0d334e4e5f78a2e9b1bd6c1ddae |
| tests/fixtures/s81_s09_flag_off_golden.json | 16589 | 02b29cc6d3a649324f71b27472ae135cc015ba39e9659b49c0306d1e249e6176 |

Both pure ASCII (0 bytes > 127), LF only (0 CRLF); py_compile + ruff E9,F63,F7,F82 clean. The golden was RECORDED AT BASE by the file's own _record_golden() (a scratch-only recorder test in the scratch worktree at e7c81956, never hand-written): top-level keys sorted, result dicts as insertion-order dumps, route / status / handler bodies as RAW response text (request id normalised to <rid>), Supabase op timestamps normalised to <ts> (R-S09-9). Cross-check with the spec probe base_sequences.json: 13 of 13 shared scenarios agree (calls, results, logs, key table).

## 2. Every [pyt] line

- golden record (scratch worktree, base bytes): `[pyt] tag=s09red-record start=2026-10-29 13:58:12 end=2026-10-29 13:58:54 elapsed=43s bound=600s status=OK rc=0` -- 1 passed; [hermeticity] sentinel checked 1; [netguard] blocked 0
- unit file at base, run 1 (superseded: 26 rows raised TypeError on the device_fp keyword; fixed with the _consume signature check): `[pyt] tag=s09red-base-unit start=2026-10-29 13:59:54 end=2026-10-29 14:01:10 elapsed=76s bound=600s status=FAIL rc=1` -- 87 failed / 106 passed (58 AssertionError + 26 TypeError + 3 unparsed)
- unit file at base, run 2: `[pyt] tag=s09red-base-unit2 start=2026-10-29 14:02:58 end=2026-10-29 14:03:38 elapsed=40s bound=600s status=FAIL rc=1` -- 87 failed (all AssertionError, junit-classified) / 106 passed; [hermeticity] 193; [netguard] 0
- prototype, ambient flags OFF (run 1): `[pyt] tag=s09red-proto-off start=2026-10-29 14:09:15 end=2026-10-29 14:09:49 elapsed=34s bound=600s status=OK rc=0` -- 193 passed; [hermeticity] 193; [netguard] 0
- prototype, ambient flags ON (run 1): `[pyt] tag=s09red-proto-on start=2026-10-29 14:10:01 end=2026-10-29 14:10:32 elapsed=31s bound=600s status=OK rc=0` -- 193 passed; [hermeticity] 193; [netguard] 0
- unit file at base, FINAL bytes (after the r35b _pos fix): `[pyt] tag=s09red-base-final start=2026-10-29 15:02:27 end=2026-10-29 15:03:32 elapsed=65s bound=600s status=FAIL rc=1` -- 87 failed (all AssertionError) / 106 passed; [hermeticity] sentinel checked 193; [netguard] blocked 0
- prototype, ambient OFF, FINAL bytes: `[pyt] tag=s09red-proto-off-final start=2026-10-29 15:04:05 end=2026-10-29 15:05:07 elapsed=62s bound=600s status=OK rc=0` -- 193 passed; [hermeticity] 193; [netguard] 0
- prototype, ambient ON (ENABLE_DEVICE_DAILY_QUOTA=true ENABLE_RIYADH_RESET=true exported to the runner), FINAL bytes: `[pyt] tag=s09red-proto-on-final start=2026-10-29 15:05:11 end=2026-10-29 15:05:45 elapsed=33s bound=600s status=OK rc=0` -- 193 passed; [hermeticity] 193; [netguard] 0
- prototype E-row probe (ST1 r25 + the 043 census): `[pyt] tag=s09red-proto-erows start=2026-10-29 16:04:41 end=2026-10-29 16:06:25 elapsed=104s bound=600s status=FAIL rc=1` -- 7 failed / 24 passed: exactly E2 (r25a, 'R-ST1-1: no new to_thread', count 5) + E1 (the six r25b digests); the 043 census row green

Comm set and the 27 pin files: section 6. Mutants: section 5 (one [pyt] line each).

## 3. The RED file (rulings first, then review corrections, then the spec)

193 nodes: 42 RED test functions = 87 nodes (every one fails at base on an AssertionError ONLY, junit-classified: 87 AssertionError, 0 other); 16 PIN test functions = 106 nodes (all green at base, under the full B1 configuration: both flags OFF in the five spellings, mixed per flag; ENABLE_REQUEST_CONTEXT_HEADERS=true with a valid X-Device-Fingerprint bound; DEVICE_KEY_PEPPER (built by concatenation); the decoy DEVICE_DAILY_QUOTA_CAP=7; DEVICE_QUOTA_EXEMPT_USER_IDS naming another synthetic uid; ENABLE_PAID_ROUTE_METERING=true; call recorders on Redis, Supabase reads, consume, status and the referral client). Missing symbols are read through _need() (getattr + assert); the device_fp keyword through _consume() (inspect.signature + assert). Every flag a row depends on is set or deleted explicitly (an autouse fixture clears 18 env names).

| RED row | what it pins | source |
|---|---|---|
| r01 | flag readers truth table (usage_service x2 + error_handler local one-liner, 13 spellings, per call) | spec R01 |
| r02 | DEVICE_DAILY_CAP == 3 constant; DEVICE_DAILY_QUOTA_CAP=1 moves nothing | R-S09-6 (replaces spec R02 knob) |
| r03 | DEVICE_QUOTA_EXEMPT_USER_IDS parse (case, garbage, blank, 50 cap) | spec R03, R-S09-4 |
| r04 x8 | _usage_window at T1/T2/T4/T5 ON and OFF (+ default now via FakeDatetime) | spec R04 |
| r05 x4 | key helpers Riyadh / UTC | spec R05 |
| r06 | ONE eval, KEYS [acct, dev], ARGV ['3','3',expireat]; zero [USAGE-DEVICE] records | spec R06 + R-S09-8 |
| r07 x2 | EXPIREAT = next reset + 3600 ON / OFF | spec R07 |
| r08 x2 | device before lifetime-free; M33 case acct 3 + dev 3 -> device_daily | spec R08 + R-S09-8 (C2c) |
| r09 | account refusal scope daily | spec R09 |
| r10 | code-0 result FULL dict incl. key order; zero [USAGE-DEVICE] records | spec R10 + R-S09-8 (C2d) |
| r11 x4 | retry_after ceil int + resets_at (T0 on/off, T2, T6) | spec R11 |
| r12 | POST compare 429 on the wire (+ Retry-After 1800) | spec R12 |
| r13 x6 | every consume site passes device_fp; 429 extras | spec R13 |
| r14 | handler allow-list (bad scope / non-str dropped; other codes base) | spec R14 |
| r15 | stash refund: one eval, other uid base-only, second refund no call | spec R15, R-S09-3 |
| r16 x4 | route failure refunds both keys once after the drain (text POST, stream error, url, camera) | spec R16 |
| r17 | refund after Riyadh midnight is exact | spec R17 |
| r18 | previous daily key = Riyadh-yesterday + the transition | spec R18 |
| r19 | status RAW body (binding axis, limits.device_daily) | R-S09-1 / R-S09-6 (re-derived) |
| r20 x4 | counted_scope: device binds / account binds / tie / no header | R-S09-1 (re-derived) |
| r21 | status reads: one tier read, GET acct + dev, no bonus, no monthly | spec R21 |
| r22 x4 | account-only + ONE INFO header=<absent|malformed|ok|absent>; 200 | spec R22 |
| r23 | no secret in any log (guarded: an EVAL ran) | spec R23 |
| r24 | allow-list = golden base path (guarded by _quota_live) | spec R24, R-S09-4 |
| r25 | premium = golden; refund after it = golden refund_nokeys (device refund block not gated) | spec R25, R-S09-3 |
| r26 | fail-open + ONE WARNING type=ConnectionError; later refund no EVAL / no write | spec R26 (amended, see deviations) |
| r27 x5 | bad replies 'OK' / [0,1] / None / [5,1,1] / [True,1,1] -> BadReply | spec R27 + C19 |
| r28 | upstash-shaped client gets eval(script, keys=, args=) | spec R28 |
| r29 x2 | offload ON -> worker thread, OFF -> loop thread | spec R29 |
| r30 x7 | drift pin vs llm_spend_breaker.riyadh_day at T0..T6 | spec R30 |
| r31 | status route passes device_fp | spec R31 |
| r32 | device key = HMAC; raw fp in no key / arg | spec R32 |
| r33 | retired monthly + bonus (consume + status) | spec R33 |
| r34 | camera consume device_fp + one refund (zero-product exit) | spec R34 |
| r35 | script literals byte for byte (LF-joined, no trailing LF) | spec R35, R-S09-10 |
| r35b | static script shape (KEYS/ARGV use, device first, EXPIREAT ARGV[3], refund floor) | R-S09-10 (new) |
| r36 | usage_limit_extras: {} on every golden base result, the 3 keys on a refusal | spec R36 |
| r37 x3 | status quota path at lifetime 0 and 2 (lifetime_free 0, binding daily) | R-S09-1 / R-S09-14 (new; kills M24) |
| r38 x3 | the S81-08 reader port (bcf75f84 == merged 6c14ac95) fed three capped shapes: canCompare False, sheet daily with 0 left, pill 3/3 | R-S09-1 probe row (new) |
| r39 | L6: consume ON, flag OFF, refund still refunds from the stash | R-S09-3 (new) |
| r40 | referral Loop-1 deep_review credit paused + ONE INFO, invite and response unchanged | R-S09-2 (new) |
| r41 | referral Loop-2 grants + push paused + ONE INFO each (step 4 and the redeemed mark not asserted) | R-S09-2 (new) |
| r42 | RIYADH alone at T2 moves only the date (the T2 half of spec P11) | spec P11 (split) |

| PIN row | what it pins |
|---|---|
| p01 x30 | 6 consume scenarios x 5 spellings == golden (calls, result, logs) |
| p02 x15 | 3 refund scenarios x 5 spellings |
| p03 x15 | 3 status scenarios x 5 spellings: function result AND raw route body |
| p04 x6 | the 5 consume sites' 429 raw bodies + Redis calls, no Retry-After, header present |
| p05 x7 | consume called with exactly (uid, token), no kwargs; status get_usage_status(user_id=, access_token=) |
| p06 x5 | handler flag OFF: W1-9 base body + Retry-After, no resets_at / scope |
| p07 x5 | key helper table UTC |
| p08 | flag OFF with EVAL raising and every request_context accessor + lsb._eval raising: golden |
| p09 | os.getenv recorder: DEVICE_QUOTA_EXEMPT_USER_IDS / DEVICE_DAILY_QUOTA_CAP never read flag OFF |
| p10 | quota ON + anon gate ON: anonymous camera 429 == golden |
| p11 x6 | RIYADH ON quota OFF at T0 == golden |
| p12 | TIER_LIMITS literal |
| p13 | check_usage_allowed unchanged quota ON |
| p14 | quota ON success fires record_lifetime_comparison once |
| p15 x10 | referral create_invite / loop2 flag OFF == golden ops + push, no INFO (R-S09-2) |
| p16 | NULL tier runs the base path (R-S09-5) |

## 4. Prototype (scratch worktree, thrown away)

Applied by proto_patch.py (exact-string edits, CRLF kept; no whole-file diff: 7 files, 326 insertions, 23 deletions), diff saved at %s/prototype.diff (25,864 bytes): usage_service (readers, DEVICE_DAILY_CAP, the exempt parser, _usage_window + the four key helpers through it with the f-string writers kept, the two scripts, _offload_dispatch_async, the _DEVICE_DEBIT stash read regardless of the flag, _consume_device_quota, the refund device block, get_device_usage_status + _device_status_body with the binding axis, usage_limit_extras, device_quota_kwargs), error_handler (local reader + the USAGE_LIMIT pass-through after the B4 block), text/url/image routes (the kwargs + extras at the five sites), usage_routes (the flag branch), referral_service (the three pauses with ONE constant INFO line each; the prototype skips all four Loop-2 grant steps, one possible GREEN choice). Results: 193/193 green with the flags ON and OFF (section 2). What the spec got wrong or left open is in section 7.

E-rows confirmed on the prototype (GREEN applies them; none is edited by the RED): E1 = the six r25b digests (_daily_key, _monthly_key, _previous_daily_key, _previous_monthly_key, consume_comparison_credit, refund_comparison_credit); E2 = r25a to_thread 4 -> 5. tests/test_migration_043_delete_user_cascade.py::test_every_per_user_cache_key_is_purged_or_kept stays GREEN with the f-string writers (R-S09-7; the device key f-string interpolates no user id).

## 5. Mutation table (52 mutants on byte copies of the prototype; .qa-mutation.lock held and removed; every restore sha256-verified)

51 KILLED (every kill an AssertionError, junit-classified), 1 SURVIVED (M38, equivalent by construction, for a ruling).

| id | mutant | verdict | killing rows | [pyt] |
|---|---|---|---|---|
| M01 | quota path keeps the base lifetime-free branch before the EVAL | KILLED | test_r06_one_eval_per_consume, test_r08_device_before_lifetime_free, test_r10_success_shape | `[pyt] tag=s09red-m01 start=2026-10-29 14:13:19 end=2026-10-29 14:13:41 elapsed=21s bound=600s status=FAIL rc=1` |
| M02 | two EVALs (account alone, then both) instead of one | KILLED | test_r06_one_eval_per_consume | `[pyt] tag=s09red-m02 start=2026-10-29 14:13:43 end=2026-10-29 14:14:02 elapsed=19s bound=600s status=FAIL rc=1` |
| M03 | EXPIRE 86400 instead of EXPIREAT in the consume script | KILLED | test_r35_scripts_are_pinned_literals, test_r35b_script_shape_static | `[pyt] tag=s09red-m03 start=2026-10-29 14:14:04 end=2026-10-29 14:14:24 elapsed=20s bound=600s status=FAIL rc=1` |
| M04 | _usage_window ignores ENABLE_RIYADH_RESET | KILLED | test_r04_usage_window, test_r05_key_helpers_riyadh, test_r11_retry_after_and_resets_at, test_r30_riyadh_drift_pin | `[pyt] tag=s09red-m04 start=2026-10-29 14:14:26 end=2026-10-29 14:14:45 elapsed=19s bound=600s status=FAIL rc=1` |
| M05 | the refund skips the device key | KILLED | test_r15_refund_decrements_both_keys_once, test_r16_route_failure_refunds_both, test_r34_camera_consume_and_refund | `[pyt] tag=s09red-m05 start=2026-10-29 14:14:47 end=2026-10-29 14:14:53 elapsed=6s bound=600s status=FAIL rc=1` |
| M06 | the handler drops scope | KILLED | test_r12_post_compare_429_on_the_wire, test_r13_every_consume_site_passes_device_fp, test_r14_handler_allow_list | `[pyt] tag=s09red-m06 start=2026-10-29 14:14:54 end=2026-10-29 14:14:59 elapsed=6s bound=600s status=FAIL rc=1` |
| M07 | the account-only metric carries the raw fingerprint | KILLED | test_r22_no_header_is_account_only_plus_one_metric | `[pyt] tag=s09red-m07 start=2026-10-29 14:15:00 end=2026-10-29 14:15:06 elapsed=5s bound=600s status=FAIL rc=1` |
| M08 | a malformed header raises HTTPException(400) | KILLED | test_r22_no_header_is_account_only_plus_one_metric | `[pyt] tag=s09red-m08 start=2026-10-29 14:15:07 end=2026-10-29 14:15:12 elapsed=5s bound=600s status=FAIL rc=1` |
| M09 | the consume branch not gated by the flag | KILLED | test_p01_golden_consume_flag_off, test_p08_no_eval_and_no_context_read_flag_off | `[pyt] tag=s09red-m09 start=2026-10-29 14:15:13 end=2026-10-29 14:15:20 elapsed=7s bound=600s status=FAIL rc=1` |
| M10 | the handler pass-through not gated | KILLED | test_p06_handler_flag_off | `[pyt] tag=s09red-m10 start=2026-10-29 14:15:20 end=2026-10-29 14:15:29 elapsed=9s bound=600s status=FAIL rc=1` |
| M11 | scope not checked against the value set | KILLED | test_r14_handler_allow_list | `[pyt] tag=s09red-m11 start=2026-10-29 14:15:44 end=2026-10-29 14:15:49 elapsed=5s bound=600s status=FAIL rc=1` |
| M12 | the allow-list ignored | KILLED | test_r24_allow_list_runs_the_base_path | `[pyt] tag=s09red-m12 start=2026-10-29 14:15:50 end=2026-10-29 14:15:56 elapsed=5s bound=600s status=FAIL rc=1` |
| M13 | premium device-capped | KILLED | test_r25_premium_is_not_device_capped | `[pyt] tag=s09red-m13 start=2026-10-29 14:15:56 end=2026-10-29 14:16:02 elapsed=6s bound=600s status=FAIL rc=1` |
| M14 | fail-open returns consumed True + keys | KILLED | test_r26_fail_open_with_outage_metric, test_r27_bad_reply_fails_open | `[pyt] tag=s09red-m14 start=2026-10-29 14:16:03 end=2026-10-29 14:16:08 elapsed=6s bound=600s status=FAIL rc=1` |
| M15 | the stash not checked against the user id | KILLED | test_r15_refund_decrements_both_keys_once | `[pyt] tag=s09red-m15 start=2026-10-29 14:16:09 end=2026-10-29 14:16:15 elapsed=5s bound=600s status=FAIL rc=1` |
| M16 | the stash latch removed (refund twice decrements twice) | KILLED | test_r15_refund_decrements_both_keys_once | `[pyt] tag=s09red-m16 start=2026-10-29 14:16:15 end=2026-10-29 14:16:25 elapsed=10s bound=600s status=FAIL rc=1` |
| M17 | counted_scope tie -> daily | KILLED | test_r20_counted_scope, test_r37_status_quota_path_fresh_accounts | `[pyt] tag=s09red-m17 start=2026-10-29 14:16:26 end=2026-10-29 14:16:31 elapsed=6s bound=600s status=FAIL rc=1` |
| M18 | remaining.device_daily present without a device key | KILLED | test_r20_counted_scope | `[pyt] tag=s09red-m18 start=2026-10-29 14:16:32 end=2026-10-29 14:16:53 elapsed=21s bound=600s status=FAIL rc=1` |
| M19 | retry_after by int() truncation instead of ceil | KILLED | test_r11_retry_after_and_resets_at | `[pyt] tag=s09red-m19 start=2026-10-29 14:16:57 end=2026-10-29 14:17:38 elapsed=42s bound=600s status=FAIL rc=1` |
| M20 | resets_at rendered +00:00 under RIYADH ON | KILLED | test_r11_retry_after_and_resets_at, test_r12_post_compare_429_on_the_wire, test_r19_status_body_device | `[pyt] tag=s09red-m20 start=2026-10-29 14:17:41 end=2026-10-29 14:18:09 elapsed=28s bound=600s status=FAIL rc=1` |
| M21 | device key = the raw fingerprint (no HMAC) | KILLED | test_r06_one_eval_per_consume, test_r32_device_key_is_the_hmac | `[pyt] tag=s09red-m21 start=2026-10-29 14:18:11 end=2026-10-29 14:19:01 elapsed=50s bound=600s status=FAIL rc=1` |
| M22 | the monthly cap still consulted on the quota path | KILLED | test_r06_one_eval_per_consume, test_r33_retired_monthly_and_bonus | `[pyt] tag=s09red-m22 start=2026-10-29 14:19:05 end=2026-10-29 14:20:25 elapsed=80s bound=600s status=FAIL rc=1` |
| M23 | the status reads the bonus and the monthly counter on the quota path | KILLED | test_r21_status_reads_on_quota_path | `[pyt] tag=s09red-m23 start=2026-10-29 14:20:49 end=2026-10-29 14:21:52 elapsed=63s bound=600s status=FAIL rc=1` |
| M24 | remaining.lifetime_free not zeroed on the quota path | KILLED | test_r37_status_quota_path_fresh_accounts, test_r38_s81_08_reader_port_sees_the_binding_axis | `[pyt] tag=s09red-m24 start=2026-10-29 14:21:57 end=2026-10-29 14:22:39 elapsed=42s bound=600s status=FAIL rc=1` |
| M25 | device_quota_kwargs returns the kwarg with the flag OFF | KILLED | test_p05_consume_call_shape_flag_off | `[pyt] tag=s09red-m25 start=2026-10-29 14:22:44 end=2026-10-29 14:23:31 elapsed=47s bound=600s status=FAIL rc=1` |
| M26 | a route reads x-device-fingerprint itself (text POST) | KILLED | test_r22_no_header_is_account_only_plus_one_metric | `[pyt] tag=s09red-m26 start=2026-10-29 14:23:33 end=2026-10-29 14:24:02 elapsed=29s bound=600s status=FAIL rc=1` |
| M27 | the device cap read from the env knob (R-S09-6: no knob) | KILLED | test_r02_device_daily_cap_is_a_constant, test_r06_one_eval_per_consume | `[pyt] tag=s09red-m27 start=2026-10-29 14:24:11 end=2026-10-29 14:25:07 elapsed=55s bound=600s status=FAIL rc=1` |
| M28 | Riyadh offset 4 h | KILLED | test_r04_usage_window, test_r30_riyadh_drift_pin | `[pyt] tag=s09red-m28 start=2026-10-29 14:25:10 end=2026-10-29 14:25:52 elapsed=42s bound=600s status=FAIL rc=1` |
| M29 | the camera route does not pass device_fp | KILLED | test_r13_every_consume_site_passes_device_fp, test_r34_camera_consume_and_refund | `[pyt] tag=s09red-m29 start=2026-10-29 14:25:57 end=2026-10-29 14:26:32 elapsed=34s bound=600s status=FAIL rc=1` |
| M30 | the stream route does not pass device_fp | KILLED | test_r13_every_consume_site_passes_device_fp | `[pyt] tag=s09red-m30 start=2026-10-29 14:26:34 end=2026-10-29 14:27:22 elapsed=48s bound=600s status=FAIL rc=1` |
| M31 | _eval bypassed (redis-py shape only) | KILLED | test_r28_upstash_client_shape | `[pyt] tag=s09red-m31 start=2026-10-29 14:27:27 end=2026-10-29 14:28:03 elapsed=35s bound=600s status=FAIL rc=1` |
| M32 | the device EVAL always inline (offload ignored) | KILLED | test_r29_offload_dispatch | `[pyt] tag=s09red-m32 start=2026-10-29 14:28:19 end=2026-10-29 14:29:40 elapsed=81s bound=600s status=FAIL rc=1` |
| M33 | the device checked AFTER the account inside the script | KILLED | test_r35_scripts_are_pinned_literals, test_r35b_script_shape_static | `[pyt] tag=s09red-m33 start=2026-10-29 14:29:43 end=2026-10-29 14:31:09 elapsed=85s bound=600s status=FAIL rc=1` |
| M34 | the refund script decrements without the floor | KILLED | test_r35_scripts_are_pinned_literals, test_r35b_script_shape_static | `[pyt] tag=s09red-m34 start=2026-10-29 14:55:35 end=2026-10-29 14:55:42 elapsed=6s bound=600s status=FAIL rc=1` |
| M35 | the status route not gated | KILLED | test_p03_golden_status_flag_off, test_p05_consume_call_shape_flag_off | `[pyt] tag=s09red-m35 start=2026-10-29 14:31:51 end=2026-10-29 14:32:33 elapsed=42s bound=600s status=FAIL rc=1` |
| M36 | _previous_daily_key UTC yesterday under RIYADH ON | KILLED | test_r05_key_helpers_riyadh, test_r18_previous_daily_key_is_riyadh_yesterday | `[pyt] tag=s09red-m36 start=2026-10-29 14:32:47 end=2026-10-29 14:34:05 elapsed=78s bound=600s status=FAIL rc=1` |
| M37 | the allow-list knob read with the flag OFF | KILLED | test_p09_knobs_not_read_flag_off | `[pyt] tag=s09red-m37 start=2026-10-29 14:34:10 end=2026-10-29 14:35:18 elapsed=68s bound=600s status=FAIL rc=1` |
| M38 | the anon details gain the extras (image anon gate) | SURVIVED | - | `[pyt] tag=s09red-m38 start=2026-10-29 14:35:23 end=2026-10-29 14:36:31 elapsed=68s bound=600s status=OK rc=0` |
| M39 | C2a: the status keeps the base lifetime-free full allowance below lifetime 3 | KILLED | test_r37_status_quota_path_fresh_accounts, test_r38_s81_08_reader_port_sees_the_binding_axis | `[pyt] tag=s09red-m39 start=2026-10-29 14:36:38 end=2026-10-29 14:37:46 elapsed=68s bound=600s status=FAIL rc=1` |
| M40 | C2b: an always-on account-only metric | KILLED | test_r06_one_eval_per_consume, test_r10_success_shape | `[pyt] tag=s09red-m40 start=2026-10-29 14:37:52 end=2026-10-29 14:39:02 elapsed=70s bound=600s status=FAIL rc=1` |
| M41 | C2d: a stray scope key on the code-0 result | KILLED | test_r10_success_shape | `[pyt] tag=s09red-m41 start=2026-10-29 14:40:40 end=2026-10-29 14:42:14 elapsed=93s bound=600s status=FAIL rc=1` |
| M42 | C14: the device refund block re-derives a device key without a stash | KILLED | test_p02_golden_refund_flag_off, test_p08_no_eval_and_no_context_read_flag_off, test_r25_premium_is_not_device_capped | `[pyt] tag=s09red-m42 start=2026-10-29 14:42:19 end=2026-10-29 14:44:22 elapsed=123s bound=600s status=FAIL rc=1` |
| M43 | R-S09-3 L6: the stash read only while the flag is ON | KILLED | test_r39_refund_after_flag_off_uses_the_stash | `[pyt] tag=s09red-m43 start=2026-10-29 14:44:31 end=2026-10-29 14:45:47 elapsed=76s bound=600s status=FAIL rc=1` |
| M44 | R-S09-3: the stash set on a fail-open consume | KILLED | test_r26_fail_open_with_outage_metric | `[pyt] tag=s09red-m44 start=2026-10-29 14:45:53 end=2026-10-29 14:46:48 elapsed=55s bound=600s status=FAIL rc=1` |
| M45 | R-S09-2: the Loop-1 pause not gated (always paused) | KILLED | test_p15_referral_flag_off_golden | `[pyt] tag=s09red-m45 start=2026-10-29 14:50:51 end=2026-10-29 14:51:27 elapsed=36s bound=600s status=FAIL rc=1` |
| M46 | R-S09-2: Loop-2 grants not paused | KILLED | test_r41_referral_loop2_rewards_and_push_paused | `[pyt] tag=s09red-m46 start=2026-10-29 14:51:29 end=2026-10-29 14:51:55 elapsed=26s bound=600s status=FAIL rc=1` |
| M47 | R-S09-2: the reward push not paused | KILLED | test_r41_referral_loop2_rewards_and_push_paused | `[pyt] tag=s09red-m47 start=2026-10-29 14:51:58 end=2026-10-29 14:52:37 elapsed=40s bound=600s status=FAIL rc=1` |
| M48 | R-S09-2: the pause line carries the referrer id | KILLED | test_r41_referral_loop2_rewards_and_push_paused | `[pyt] tag=s09red-m48 start=2026-10-29 14:52:39 end=2026-10-29 14:53:09 elapsed=29s bound=600s status=FAIL rc=1` |
| M49 | R-S09-1: remaining.daily = the account axis only (spec 2.7 shape) | KILLED | test_r19_status_body_device, test_r20_counted_scope, test_r37_status_quota_path_fresh_accounts, test_r38_s81_08_reader_port_sees_the_binding_axis | `[pyt] tag=s09red-m49 start=2026-10-29 14:54:20 end=2026-10-29 14:54:49 elapsed=29s bound=600s status=FAIL rc=1` |
| M50 | R-S09-1: used.daily = the account count always | KILLED | test_r19_status_body_device, test_r38_s81_08_reader_port_sees_the_binding_axis | `[pyt] tag=s09red-m50 start=2026-10-29 14:54:50 end=2026-10-29 14:55:04 elapsed=14s bound=600s status=FAIL rc=1` |
| M51 | R-S09-6: limits.device_daily missing | KILLED | test_r19_status_body_device | `[pyt] tag=s09red-m51 start=2026-10-29 14:55:05 end=2026-10-29 14:55:11 elapsed=6s bound=600s status=FAIL rc=1` |
| M52 | R-S09-5: the predicate tier != 'premium' (NULL tier capped) | KILLED | test_p16_null_tier_runs_the_base_path | `[pyt] tag=s09red-m52 start=2026-10-29 14:55:12 end=2026-10-29 14:55:19 elapsed=7s bound=600s status=FAIL rc=1` |

Notes: spec M27 (knob clamp) is moot under R-S09-6 and recast as 'cap read from the env knob'. M03 / M33 / M34 are Lua-text mutants: the emulating fake keys on the module constants, so they die on r35 / r35b (no Lua runtime, R-S09-10); M34 first run showed one ValueError in r35b (str.index on a dropped needle), fixed with the asserting _pos helper and re-run (killed, AssertionError only). M26 dies on r22[ctx_off] (the S81-05 p07 needle pin was not selected by the -k expression). M38 SURVIVED: check_anon_usage_allowed never returns retry_after / resets_at / scope, so usage_limit_extras is {} on the anon detail; observable only if the anon result changed shape. M39 = C2a, M40 = C2b, M41 = C2d, M42 = C14 (a device refund without a stash), M43 = R-S09-3 L6, M44 = the stash set on a fail-open, M45-M48 = R-S09-2, M49-M51 = R-S09-1 / R-S09-6, M52 = R-S09-5.

## 6. Comm set at base = the BASE RECORD (real worktree, one chunk at a time, bound 1200)

- List: C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/comm_files.txt (200 files) and C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/comm_reasons.tsv (per-file reasons). Built by build_comm.py: module / symbol reference grep for usage_service, error_handler, text_routes, url_routes, image_routes, usage_routes, referral_service, request_context, llm_spend_breaker (+ 20 symbols) UNION the named source-scanning pins UNION every app/ walker (rglob / glob / os.walk / scandir / listdir / inspect.getsource / ast.parse / app path joins / <module>.__file__ / .github) UNION the CLAUDE.md readers UNION the SmartCompareApp-scanning backend tests (23) UNION tests/test_retro_w1_9.py (C13) UNION the referral tests (R-S09-2) UNION the spec's 99-file seed MINUS the three test_precommit_hook*.py present. NETWORK_FLAKY_EXCLUDE: no member falls in the set.
- Set sha256 c9f7585d75ab76dab68c1d7e222563357c6ea34f327c728270cecbde479bb9fd; cached per LC-6 at <scratchpad>/harness/base_records/e7c81956f11749b1378aa449c4ac616c82bfe6a9/c9f7585d...txt.
- Chunk 00 = the spec Set A (17 files), chunk 01 = the spec Set B (10 files): 899 + 1352 = 2,251 passed / 0 failed, exactly the spec 1.10 record (netguard 2 and 25 sentinel-host attempts, as recorded there).
- chunk 00: `[pyt] tag=s09red-comm-00 start=2026-10-29 15:06:07 end=2026-10-29 15:07:27 elapsed=80s bound=1200s status=OK rc=0` -- 899 passed; [hermeticity] 899; [netguard] blocked 2 from 2 nodes (sentinel host)
- chunk 01: `[pyt] tag=s09red-comm-01 start=2026-10-29 15:07:48 end=2026-10-29 15:11:06 elapsed=199s bound=1200s status=OK rc=0` -- 1352 passed; [hermeticity] 1352; [netguard] blocked 25 from 3 nodes
- chunk 02: `[pyt] tag=s09red-comm-02 start=2026-10-29 15:12:16 end=2026-10-29 15:15:11 elapsed=175s bound=1200s status=OK rc=0` -- 969 passed, 6 deselected; [hermeticity] 969; [netguard] 25 from 12 nodes
- chunk 03: `[pyt] tag=s09red-comm-03 start=2026-10-29 15:15:30 end=2026-10-29 15:18:19 elapsed=169s bound=1200s status=OK rc=0` -- 2284 passed; [hermeticity] 2284; [netguard] 29 from 11 nodes
- chunk 04: `[pyt] tag=s09red-comm-04 start=2026-10-29 15:18:38 end=2026-10-29 15:28:23 elapsed=585s bound=1200s status=OK rc=0` -- 727 passed; [hermeticity] 727; [netguard] 33 from 30 nodes
- chunk 05: `[pyt] tag=s09red-comm-05 start=2026-10-29 15:28:38 end=2026-10-29 15:29:57 elapsed=78s bound=1200s status=FAIL rc=1` -- 969 passed, 27 skipped, 6 deselected, 1 xfailed, 2 ERROR = tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable and ::test_render_digests_match_base_except_the_fence (the known cold-tiktoken base noise of the common brief); [hermeticity] 972; [netguard] 127 from 7 nodes
- chunk 06: `[pyt] tag=s09red-comm-06 start=2026-10-29 15:30:08 end=2026-10-29 15:32:41 elapsed=153s bound=1200s status=OK rc=0` -- 1041 passed; [hermeticity] 1041; [netguard] 6 from 5 nodes
- chunk 07: `[pyt] tag=s09red-comm-07 start=2026-10-29 15:32:59 end=2026-10-29 15:40:26 elapsed=446s bound=1200s status=FAIL rc=1` -- MEASUREMENT FAILURE: no pytest summary; pytest-timeout (120 s per test) killed the process inside tests/test_secret_scan_static.py::test_tracked_binaries_carry_the_magic_bytes_of_their_extension (git cat-file per tracked binary under box load); re-run as 09 + 10
- chunk 09: `[pyt] tag=s09red-comm-09 start=2026-10-29 15:42:11 end=2026-10-29 15:50:33 elapsed=503s bound=1200s status=OK rc=0` -- chunk 07 minus the secret scan (24 files): 2569 passed, 1 skipped, 8 deselected; [hermeticity] 2570; [netguard] 58 from 26 nodes
- chunk 10: `[pyt] tag=s09red-comm-10 start=2026-10-29 15:52:18 end=2026-10-29 15:54:01 elapsed=103s bound=600s status=OK rc=0` -- tests/test_secret_scan_static.py alone: 31 passed in 97 s; [hermeticity] 31; [netguard] 0
- chunk 08: `[pyt] tag=s09red-comm-08 start=2026-10-29 15:58:19 end=2026-10-29 16:03:25 elapsed=306s bound=1200s status=OK rc=0` -- 1130 passed, 9 skipped, 2 deselected, 35 xfailed; [hermeticity] 1174; [netguard] 86 from 40 nodes
- Totals: 11,971 passed, 0 FAILED, 2 ERROR (the known test_prompt_truth pair), 37 skipped, 36 xfailed, 22 deselected (the runner's free-tier marker filter). Sorted failed / error node-id set = the two test_prompt_truth nodes only.
- The unit's own RED file is not in the comm set (its base state is the RED record of section 2); the seed's non-test helper tests/fixtures/_gen_w4_13_flag_off_ledger.py is not run (no tests; importing a generator).

## 7. Deviations from the spec (reported, not silently changed) and choices the RED made

- R02 / M27: the spec's DEVICE_DAILY_QUOTA_CAP knob is gone (R-S09-6): r02 pins the constant DEVICE_DAILY_CAP = 3 and proves the env name moves nothing; every quota row runs with the decoy DEVICE_DAILY_QUOTA_CAP=7 present.
- R19 / R20 re-derived for R-S09-1: remaining.daily = min(account, device remaining), used.daily = the binding axis's used, ties name the device, remaining.device_daily only with a device key, remaining.monthly 10, remaining.lifetime_free 0, limits.device_daily = 3 APPENDED LAST in limits (placement is the RED's choice; not asserted in the no-header case).
- R-S09-3 vs spec 2.6: the ruling's L6 row (r39) requires the refund to use the stash AFTER the flag goes OFF, so _device_refund_keys must NOT read the flag first (spec 2.6 said it returns None when OFF). The stash is usage_service's own ContextVar, so P08 / P09 (no request_context / knob read flag OFF) stay satisfiable (the prototype proves it).
- R26: the spec's 'a later refund makes no Redis call' conflicts with 2.6 (no stash -> the base fallback, which GETs); r26 asserts no EVAL and no write after a fail-open consume (consumed False means the routes never refund).
- R24 / R25 would pass vacuously at base (the flag is inert there); both are guarded by _quota_live() (the reader must exist and read ON) so they are RED at base; r25 also pins the 'device refund block not gated' class (a refund after a premium consume == golden refund_nokeys, no EVAL).
- Spec P11 split: the T0 half stays PIN (p11), the T2 half (RIYADH alone moves only the date) fails at base and is RED r42.
- R10 uses a scenario where the account and device remaining agree (2 / 2) and r08 asserts remaining.device_daily only, so the consume-side meaning of remaining.daily (account axis per spec 2.5, or the binding min per R-S09-1's principle) is NOT pinned (it never reaches the wire: the handler drops it).
- R-S09-2 referral rows assert the Loop-1 credit, the Loop-2 redemption row, the users bonus bump, the invitee credit and the push are skipped under the flag with ONE INFO line each (constants only); step 4 (lifetime_invites_consumed, ruling cites :881-897) and _update_invite_as_redeemed are NOT asserted (see question 1).
- Script literals: LF-joined, no trailing LF (the S81-04 RECORD_SCRIPT precedent); the spec's 'equivalent' EXPIREAT-reorder candidate is killed by the byte-for-byte r35 (no longer equivalent).
- Route rows run through the real middleware stack (TestClient, ENABLE_REQUEST_CONTEXT_HEADERS=true); refund rows drain fire_and_forget through the app shutdown drain (with TestClient(app) ...: app.main._drain_background_tasks, 8 s bound).
- P09 records os.getenv only (an os.environ.get reader of the allow-list would escape it).
- Comm set: the walker criterion '__file__' is narrowed to '<module>.__file__' readers (106 files that only locate the repo through their own __file__ and read no app/ source were dropped; 3 module-__file__ readers kept).

## 8. Questions for the gate

1. R-S09-2: under the pause, is Loop-2 step 4 (users.lifetime_invites_consumed, :881-897, listed in the ruling) skipped or kept (the dormant s9 text keeps '3 successful invites per device'), and is the invite still marked redeemed? The RED asserts neither.
2. The consume result's remaining.daily under the quota flag: the account axis (spec 2.5) or the binding min (R-S09-1)? Not on the wire; unpinned except where both agree.
3. limits.device_daily: appended last in limits (r19); present without a device key or not (unasserted)?
4. M38 (anon details gain the extras): rule equivalent by construction, or add a row that feeds an anon result carrying the keys?
5. Confirm R-S09-3's reading: the stash is consulted regardless of ENABLE_DEVICE_DAILY_QUOTA (r39), reversing spec 2.6's flag-first statement.
6. MOVING MAIN: origin/main moved to 6c14ac95 at 15:42 (S81-08: SmartCompareApp + CLAUDE.md + docs; no app/ or tests/ change; the two ported reader files are byte-identical to bcf75f84). This base record is at e7c81956 (the task base); per LC-6 the GREEN recomputes at 6c14ac95 (at least the CLAUDE.md readers and the 23 SmartCompareApp scanners can move).
7. tests/test_secret_scan_static.py: its tracked-binaries row hits the 120 s per-test timeout inside a 25-file chunk under load (it killed chunk 07); alone it passes in 97 s. GREEN should run it in its own runner call.
8. R26 wording (no Redis call vs the base fallback's GETs) as amended here.

## 9. Restore check and NOT MEASURED

- Real worktree: 3,442 tracked files sha256-identical before and after (manifest_before.json / manifest_after.json); git status --short = '?? tests/fixtures/s81_s09_flag_off_golden.json' and '?? tests/test_s81_s09_device_quota.py' only; HEAD e7c81956. No tracked file, requirements*, tests/.pre_impl_failures.txt or .env was edited or read for values; no git write in the real worktree; no package manager.
- Scratch worktree C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/s09_scratch (detached at e7c81956, no node_modules, no junction) removed with git worktree remove --force; git worktree list no longer lists it; the directory is gone; the mutation lock was removed before.
- No orphan pytest: the only python.exe left is the orchestrator's stall_monitor.py.
- NOT MEASURED: the Lua scripts on a real Redis / Upstash (no Lua runtime on the box, R-S09-10; the canary is the first execution); the client fences (shareTruth.s74 reads referral_service.py: GREEN and every rebase, by path through an orchestrator junction, R-S09-2); the full jest suite (not a RED duty, LC-7); the comm set at the moved main 6c14ac95.

## 10. Paths

- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/notes.md
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/pyt_lines.txt
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/base_final.xml
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/base_final_failed_nodes.txt
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/golden_recorded.json
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/proto_patch.py
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/prototype.diff
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/mutate.py
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/mutation_table.tsv
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/mutants.jsonl
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/mut/
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/build_comm.py
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/comm_files.txt
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/comm_reasons.tsv
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/comm_chunks/
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/comm_logs/
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/run_chunks.py
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/manifest.py
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/manifest_before.json
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/manifest_after.json
- C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_red/report_gen.py

