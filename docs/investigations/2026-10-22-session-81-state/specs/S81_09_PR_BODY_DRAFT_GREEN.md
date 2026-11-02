# S81-09 DEVICE-QUOTA-RIYADH: 3 compares a day per device + the Asia/Riyadh reset (two dark flags)

Lane B backend, PLAN_S81 M3 (`PLAN_S81.md` :148; the VERIFY quota grafts :102-104; owner decisions 2 and 5). Base `e7c81956` (S81-08 #377 later moved main to `6c14ac95` with client files + CLAUDE.md + docs only; GATE_S81_09 GC-6: GREEN stays at the base, the rebase round recomputes). FOCUS unit (quota + Lua): two adversaries (LC-1, GC-12). Branch `feature/s81-s09-device-quota-riyadh` at the base `e7c81956f11749b1378aa449c4ac616c82bfe6a9`: **the GREEN commit is NOT made yet** - the pre-commit hook's gitleaks step refused the staged set on ONE finding inside the FROZEN RED file (see "Commit blocked" below); the 13 paths are staged, nothing was bypassed. Spec `.qa-s80/S81-09_UNIT_SPEC.md`, its review, `specs/RULINGS_S81_09.md` (R-S09-1..15), `specs/GATE_S81_09.md` (GC-1..GC-13) in the session-81 state folder.

## What the flags do (both default OFF, read PER CALL, new names: unset in production)

- `ENABLE_RIYADH_RESET`: ONE date helper (`usage_service._usage_window`) moves every usage date key (`usage:daily:` / `usage:monthly:`, the previous-window refund fallbacks, the anon keys, the quota path and its status) to the Asia/Riyadh calendar (fixed +03:00, no DST; zoneinfo has no tzdata on the pinned venv); the daily counters reset at 00:00 Riyadh (21:00 UTC). A drift pin ties it to `llm_spend_breaker.riyadh_day` (r30). OFF: the UTC keys byte for byte.
- `ENABLE_DEVICE_DAILY_QUOTA` (free tier, not in `DEVICE_QUOTA_EXEMPT_USER_IDS`; premium, a NULL or any other tier and the allow-list run the base path byte-identically, R-S09-4/5): ONE Upstash Lua EVAL per consume (`DEVICE_CONSUME_SCRIPT` via `llm_spend_breaker._eval`, offloaded under `ENABLE_ASYNC_REDIS_OFFLOAD`) checks and debits the device-daily key `usage:device:<S81-05 HMAC device key>:<day>` FIRST and the account-daily key `usage:daily:<uid>:<day>` (3 each, `DEVICE_DAILY_CAP = 3`, no knob, R-S09-6), EXPIREAT the next reset + 1 h; a refusal writes nothing; the monthly cap, the referral bonus and the lifetime-free bypass are retired on that path (a fresh account on a capped device gets nothing). The 429 `USAGE_LIMIT` gains `resets_at` + `scope` through the flag-gated handler allow-list and `retry_after_seconds` / `Retry-After` through the W1-9 block. A failed compare refunds both keys exactly once through `DEVICE_REFUND_SCRIPT` from a request-scoped debit stash (no refund call site changed; R-S09-3 / GC-5: the stash is read whatever the flag says). `/usage/status` reports the BINDING axis in `remaining.daily` / `used.daily` (R-S09-1), `remaining.device_daily` with a device key, `limits.device_daily` = 3 (always, appended last, GC-3), `resets_at`, `counted_scope`, the retired monthly axis as never binding and `remaining.lifetime_free` 0 (R-S09-14). A missing / malformed / unkeyable header = account-only + ONE INFO `[USAGE-DEVICE] account-only header=<state>`, never a 400; a Redis error or bad reply fails OPEN with ONE WARNING `[USAGE-DEVICE] consume fail-open type=<Name>`. The referral rewards pause under the same flag (R-S09-2, GC-1): no Loop-1 Deep Review credit, no Loop-2 redemption row / bonus bump / invitee credit / `lifetime_invites_consumed` slot, no reward push; the invite row and the redeemed mark unchanged; ONE INFO `[REFERRAL-PAUSE] ...` each.
- Both OFF: byte-identical (Redis calls, results, raw bodies, log lines, referral writes and push), pinned by the committed golden `tests/fixtures/s81_s09_flag_off_golden.json` under the five OFF spellings with the full configuration (B1).

## Files

| file | lines | sha256 (after, prefix) |
|---|---|---|
| CLAUDE.md | +9 / -2 | 7403487481d6da9b |
| app/api/image_routes.py | +4 / -1 | 717d1e5a05d455dc |
| app/api/text_routes.py | +14 / -3 | 767be4451ba9d89b |
| app/api/url_routes.py | +6 / -1 | c0ff7eb2f4e2c046 |
| app/api/usage_routes.py | +16 / -1 | 8645776ffaffc56c |
| app/middleware/error_handler.py | +29 / -0 | 56332100e766db5f |
| app/services/referral_service.py | +38 / -6 | a928a6b65b69c29b |
| app/services/usage_service.py | +478 / -12 | 570785b43ead06fa |
| tests/fixtures/s81_s09_flag_off_golden.json | +722 / -0 | 02b29cc6d3a64932 |
| tests/test_s81_s05_request_context.py | +27 / -4 | 49d0b015fdd6fe53 |
| tests/test_s81_s09_device_quota.py | +2068 / -0 | 843a6bab0215ca52 |
| tests/test_s81_s09_gate_rows.py | +252 / -0 | 992e2eab6af121dd |
| tests/test_s81_st1_usage_path_offloop.py | +15 / -7 | 6380fff98dadf148 |

No migration, no lock / requirements / package file, no client file, no `.githooks` change (the hook test files were not run: no hook change), no personal value.

## Requirement -> node map (DEFECT_LEDGER row S81-09; RED `tests/test_s81_s09_device_quota.py` 193 nodes = 87 RED + 106 PIN; GREEN gate rows `tests/test_s81_s09_gate_rows.py` 20 nodes)

| requirement (PLAN :148 / ruling) | nodes |
|---|---|
| flag readers, idiom, per call | r01, g4 |
| `DEVICE_DAILY_CAP = 3`, no knob (R-S09-6) | r02 |
| allow-list (R-S09-4), premium (Q1), NULL tier base path (R-S09-5) | r03, r24, r25, p16 |
| ONE date helper, key helpers, Riyadh drift pin | r04 (x8), r05 (x4), r30 (x7), r42, p07 (x5), p11 (x6) |
| ONE EVAL, KEYS/ARGV, EXPIREAT next reset + 1 h, both client shapes, offload, HMAC key | r06, r07 (x2), r28, r29 (x2), r32, r35, r35b |
| device before lifetime-free; both exhausted = device | r08 (x2) |
| account refusal; the consume result's binding min (GC-2) | r09, r10, gc2 (x9) |
| retry_after / resets_at / scope; handler allow-list | r11 (x4), r12, r13 (x6), r14, r36, p06 (x5) |
| refund both keys once (stash), across Riyadh midnight, after a flag flip (L6), explicit-keys latch | r15, r16 (x4), r17, r34, r39, g5 |
| previous daily key = Riyadh-yesterday | r18 |
| status binding axis, counted_scope, limits.device_daily, ST1 placement | r19, r20 (x4), r21, r31, r37 (x3), r38 (x3), gc3, g6 (x2) |
| account-only + ONE metric; no secret in logs | r22 (x4), r23 |
| fail-open + outage metric; bad reply (C19) | r26, r27 (x5) |
| retired monthly + bonus | r33 |
| referral pause (R-S09-2) + step 4 (GC-1) | r40, r41, p15 (x10), gc1a, gc1b (x5) |
| flag-OFF identity, full config | p01 (x30), p02 (x15), p03 (x15), p04 (x6), p05 (x7), p08, p09, p10, p12, p13, p14 |

## Deliberate pin changes (E-rows; measured, nothing else moved)

| E | node(s) | change | reason |
|---|---|---|---|
| E1 | `tests/test_s81_st1_usage_path_offloop.py::test_r25b_frozen_digests[app/services/usage_service.py::<fn>]` for `_daily_key`, `_monthly_key`, `_previous_daily_key`, `_previous_monthly_key`, `consume_comparison_credit`, `refund_comparison_credit` (6 nodes) | BASE_DIGESTS re-recorded: 3f76488c -> ebfcb0ba, 63ff3c9e -> 5b47fefd, b3c3dd2e -> 7b808f15, 885f6947 -> 9e40493a, cfe716e2 -> f77292f5, 65eabb27 -> 67a67f8d (one comment naming S81-09) | the one usage date helper behind the four key helpers, the flag-gated quota branch, the stash refund block; flag-OFF behaviour stays pinned by ST1 BASE_CONSUME_SEQ / BASE_REFUND_SEQ / BASE_ROUTE (green, unedited) and the S81-09 golden; the other 22 digests unchanged |
| E2 | `...::test_r25a_source_inventory` | `to_thread` count 4 -> 5 | the one `_offload_dispatch_async` (the #115 dispatch of the device EVALs, parity with `_atomic_consume_async`); r25a's other assertions unedited and green |
| E3 | `tests/test_s81_s05_request_context.py::test_s05_p01_no_consumer_in_app` | `_ALLOWED_CTX_FILES` += `app/services/usage_service.py`; its import pinned to exactly `from app.utils import request_context as _request_context` and its attribute uses to {device_fingerprint, device_key, header_state, HEADER_DEVICE_FINGERPRINT}; the `header_state` needle allowed in that file (the S81-06 E9 form, generalised to a per-consumer table) | GATE_S81_09 GC-13 (17:43); `usage_routes.py` no longer names the leaf (it passes `**device_quota_kwargs()`); see the deviation below on `header_state` |
| at the flip, not here | `tests/test_legal_disclosure_s77.py` D11, `tests/test_register_benefits_parity_s69.py` | green and unedited in this PR (TIER_LIMITS unchanged) | re-pinned in the `DEVICE_QUOTA_RESET` re-fill PR (S81-12 spec E24 / D5) |

Measured: the BASE ST1 bytes against the GREEN code fail exactly the 7 E1/E2 nodes; the BASE S05 bytes fail exactly the E3 node; the 043 census (`test_every_per_user_cache_key_is_purged_or_kept`) stays green (R-S09-7: the key helpers keep their `user_id` f-strings; the device key interpolates no user id).

## Gates (every pytest through `pyt.py`, one at a time; flags exported to one runner call only)

- RED file, ambient flags OFF: `[pyt] tag=s09green-unit-off elapsed=133s bound=600s status=OK rc=0` -- 193 passed in 120.32s (0:02:00)
- RED file, both flags ON in the runner env: `[pyt] tag=s09green-unit-on elapsed=42s bound=600s status=OK rc=0` -- 193 passed in 30.15s
- E-row probe: the BASE ST1 pin bytes (temp copy) + the 043 census vs the GREEN code: `[pyt] tag=s09green-erow-probe elapsed=149s bound=600s status=FAIL rc=1` -- 7 failed, 575 passed in 138.93s (0:02:18)
- ST1 pin file after E1/E2: `[pyt] tag=s09green-st1 elapsed=82s bound=600s status=OK rc=0` -- 531 passed in 62.19s (0:01:02)
- gate rows file: `[pyt] tag=s09green-gaterows elapsed=51s bound=600s status=OK rc=0` -- 20 passed in 37.82s
- E3 probe: the BASE S05 pin bytes (temp copy) + the edited S05 file vs the GREEN code: `[pyt] tag=s09green-e3-probe elapsed=66s bound=600s status=FAIL rc=1` -- 1 failed, 351 passed in 54.30s
- RED file + gate rows, final code, flags OFF: `[pyt] tag=s09green-unit-off2 elapsed=49s bound=600s status=OK rc=0` -- 213 passed in 40.59s
- RED file + gate rows, final code, flags ON: `[pyt] tag=s09green-unit-on2 elapsed=47s bound=600s status=OK rc=0` -- 213 passed in 32.96s
- CI-order set (25 files, flags OFF): `[pyt] tag=s09green-ci-order elapsed=302s bound=1200s status=OK rc=0` -- 1309 passed in 269.63s (0:04:29)
- tests/test_secret_scan_static.py alone minus the load-timed-out tracked-binaries node (the index holds the staged new files): `[pyt] tag=s09green-secret-rest elapsed=41s bound=600s status=OK rc=0` -- 30 passed, 1 deselected in 34.93s
- the amended RED copy (gitleaks fix, temp probe), flags OFF: `[pyt] tag=s09green-amended-off elapsed=81s bound=600s status=OK rc=0` -- 193 passed in 63.14s (0:01:03)
- the amended RED copy (gitleaks fix, temp probe), flags ON: `[pyt] tag=s09green-amended-on elapsed=52s bound=600s status=OK rc=0` -- 193 passed in 41.79s
- 3 gate-row sanity mutants (G1 the pause reads the lifetime slot, G2 no binding min, G3 no limits.device_daily): all KILLED by AssertionError, restores sha-verified (the [pyt] lines are in the GREEN report).

Comm set: the RED's 200-file list re-derived at HEAD by the union rule (+ the GREEN symbols, the importers of the two edited pin files, the gate-rows file kept out like the RED file): IDENTICAL, set sha256 `c9f7585d...`; no addition, so the CACHED base record at e7c81956 was REUSED (LC-6; 11,971 passed, failed/error set = the 2 known cold-tiktoken `test_prompt_truth` ERRORs); no base re-run. HEAD, one chunk at a time, `test_secret_scan_static.py` alone (GC-7):

- `[pyt] tag=s09green-comm-00 start=2026-10-29 17:58:34 end=2026-10-29 18:00:52 elapsed=138s bound=1200s status=OK rc=0` -- 17 files: 899 passed in 128.44s (0:02:08)
- `[pyt] tag=s09green-comm-01 start=2026-10-29 18:00:58 end=2026-10-29 18:06:51 elapsed=354s bound=1200s status=OK rc=0` -- 10 files: 1352 passed in 340.97s (0:05:40)
- `[pyt] tag=s09green-comm-02 start=2026-10-29 18:07:00 end=2026-10-29 18:11:46 elapsed=286s bound=1200s status=OK rc=0` -- 25 files: 969 passed, 6 deselected in 273.22s (0:04:33)
- `[pyt] tag=s09green-comm-03 start=2026-10-29 18:11:51 end=2026-10-29 18:15:12 elapsed=201s bound=1200s status=OK rc=0` -- 25 files: 2284 passed in 192.84s (0:03:12)
- `[pyt] tag=s09green-comm-04 start=2026-10-29 18:15:13 end=2026-10-29 18:26:24 elapsed=670s bound=1200s status=OK rc=0` -- 25 files: 727 passed in 661.34s (0:11:01)
- `[pyt] tag=s09green-comm-05 start=2026-10-29 18:26:29 end=2026-10-29 18:30:26 elapsed=237s bound=1200s status=FAIL rc=1` -- 25 files: MEASUREMENT FAILURE (pytest-timeout 120 s inside a module import in tests/test_observability.py under box load, no pytest summary); re-run once alone as 05r
- `[pyt] tag=s09green-comm-05r start=2026-10-29 18:30:32 end=2026-10-29 18:33:02 elapsed=150s bound=1200s status=FAIL rc=1` -- 25 files: 969 passed, 27 skipped, 6 deselected, 1 xfailed, 2 errors in 135.70s (0:02:15); FAILED/ERROR: ERROR tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, ERROR tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable
- `[pyt] tag=s09green-comm-06 start=2026-10-29 18:33:08 end=2026-10-29 18:39:24 elapsed=376s bound=1200s status=OK rc=0` -- 25 files: 1041 passed in 351.23s (0:05:51)
- `[pyt] tag=s09green-comm-07 start=2026-10-29 18:39:36 end=2026-10-29 18:51:08 elapsed=692s bound=1200s status=OK rc=0` -- 24 files: 2569 passed, 1 skipped, 8 deselected in 647.31s (0:10:47)
- `[pyt] tag=s09green-comm-08 start=2026-10-29 18:51:15 end=2026-10-29 18:55:04 elapsed=229s bound=1200s status=OK rc=0` -- 23 files: 1130 passed, 9 skipped, 2 deselected, 35 xfailed in 219.02s (0:03:39)
- `[pyt] tag=s09green-comm-09 start=2026-10-29 18:55:06 end=2026-10-29 18:58:27 elapsed=200s bound=600s status=FAIL rc=1` -- 1 files: MEASUREMENT FAILURE (9 passed, then pytest-timeout 120 s on test_tracked_binaries_carry_the_magic_bytes_of_their_extension under box load); re-run once alone as 09r
- `[pyt] tag=s09green-comm-09r start=2026-10-29 18:58:38 end=2026-10-29 19:03:03 elapsed=265s bound=600s status=FAIL rc=1` -- 1 files: MEASUREMENT FAILURE again on the same node: it is NOT MEASURED by name; the file's other 30 nodes passed in their own run (s09green-secret-rest)

HEAD failed/error set: ERROR tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, ERROR tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable. Branch-only-new (HEAD minus the base record): **EMPTY**.

Client fences (the 14 backend-scanning suites by path through the orchestrator junction, node v24.11.1, jest 29.7.0, one jest at a time):

- shareTruth.s74 alone (first; reads app/services/referral_service.py by path): Test Suites: 1 passed, 1 total / Tests:       10 passed, 10 total (tag s09green-fence-shareTruth)
- the other 13 fences: Test Suites: 1 failed, 12 passed, 13 total / Tests:       5 failed, 225 passed, 230 total (tag s09green-fences-13)
- nativeBundle.w37 re-run alone: Test Suites: 1 failed, 1 total / Tests:       4 failed, 54 passed, 58 total (tag s09green-fence-nativeBundle-rerun)
- `[jest] tag=s09green-fence-shareTruth start=2026-10-29 17:59:22 end=2026-10-29 18:00:25 rc=0`
- `[jest] tag=s09green-fences-13 start=2026-10-29 18:00:50 end=2026-10-29 18:03:19 rc=1` (12 suites PASS; nativeBundle.w37 d5, k2, k4, k5 drift + u12 a 5 s timeout under load)
- `[jest] tag=s09green-fence-nativeBundle-rerun start=2026-10-29 18:04:36 end=2026-10-29 18:05:22 rc=1` (alone: exactly the 4 accepted drift nodes d5, k2, k4, k5; u12 passed)

The 4 nativeBundle.w37 nodes are the accepted drift class (the junctioned clone's node_modules older than this worktree's lock: expo 54.0.34 vs 54.0.37, eslint-config-expo 55.0.1, react-native-gesture-handler installed); the unit touches no SmartCompareApp file and none of the files that suite reads. No unit-caused red fence, so the FULL jest suite runs once in the last round before the PR (LC-7). ruff (E9,F63,F7,F82) and py_compile clean on every touched python file; `black --check` clean on the black-listed S05 pin file; CRLF kept, no added non-ASCII byte.

## Stated limits

R-S09-11 and the RED's, as ruled:
1. Header-less callers (build 3; a device id not ready within S81-08's `DEVICE_ID_HEADER_TIMEOUT_MS`, 1,000 ms) get 3 a day per ACCOUNT with no monthly bound: about 90 a month, looser than base by about 9x; a forged random header evades the device axis, never the account axis (per-IP / per-device throttles are S81-24).
2. A Redis outage fails OPEN (a device can exceed 3 that day) AND skips `record_lifetime_comparison` on delivered url / camera compares (gated on `usage_consumed`), undercounting the lifetime counter.
3. The two Lua scripts never execute locally (no Lua runtime: the fake emulates them; r35 / r35b pin the literals and their shape); multi-key EVAL on Upstash is reasoned, not measured; a CROSSSLOT or reply-shape surprise fails open for every free compare until rollback (CR3: the first canary check).
4. Rollback: the monthly counter misses that month's quota-path consumes (up to 10 extra free compares); the device-rule texts stay published unless `DEVICE_QUOTA_RESET` is re-filled null through the U8 machinery.
5. Exempt users (premium, the allow-list, every non-free tier) are uncapped by the device rule and keep EXPIRE 86400 and the 32-day monthly key (the privacy s8 bullet speaks of the free tier; S81-12b wording); the exemption is account-based: a reviewer's NEW free account is device-capped (L14, R-S09-4).
6. The Riyadh flip opens one fresh window 3 h early, once (the three-hour transition); a rollback between 21:00 and 24:00 UTC can refund the wrong UTC window once; a mid-day flip of the quota flag keeps the shared account-daily count.
7. The OTA order binds: `ENABLE_REQUEST_CONTEXT_HEADERS` ON and the S81-08 header propagated before `ENABLE_DEVICE_DAILY_QUOTA`; `ENABLE_RIYADH_RESET` first in its own window; the v3 Terms live first.
8. A premium or tier-read-failed status pays one extra tier read; without a header the status names `counted_scope` daily even when the device is exhausted (the next consume answers).
9. The anon gate (`check_anon_usage_allowed`) is untouched and never carries the new 429 fields (GC-4: M38 equivalent by construction); `check_usage_allowed` (no caller) ignores the device rule.
10. S81-10's refusal refunds are covered by the stash only inside the same request context (CR6, a known rebase).
11. Device counter keys are pseudonymous HMACs expiring about 1 h after the reset; a pepper rotation restarts every device counter that day.

## Flip order and owner steps (names only; a dated ledger line per step)

1. `DEVICE_KEY_PEPPER` set on `web` (S81-05 item; no dated line yet). 2. Confirm the App Review accounts premium (session-79 ledger 06:55) or set `DEVICE_QUOTA_EXEMPT_USER_IDS`. 3. After approval: the S81-08 OTA published and propagated (two launches), then `ENABLE_REQUEST_CONTEXT_HEADERS=true` in its own window. 4. LEGAL-V3 (S81-12) merged and live (backend + landing). 5. `ENABLE_RIYADH_RESET=true` FIRST, alone, in its own window, between 00:00 and 21:00 UTC (canary: the next 21:00 UTC reset). 6. Then one window: the data-only re-fill recording `DEVICE_QUOTA_RESET` (+ D11 re-pinned, landing re-render), then `ENABLE_DEVICE_DAILY_QUOTA=true` (the referral pause moves with it). The privacy s3.5 / deletion device-counter wording is S81-12b's edit at key retirement (R-S09-13). Notes for Review: the free limit is 3 comparisons a day per device.

## Canary (R-S09-10; the Lua runs for the first time in production)

On the test device: one success, one refusal and one refund, each followed by `/usage/status` (read back `used.daily`, `remaining.device_daily`, `counted_scope`, `resets_at`: the counters must move 0 -> 1 -> refusal (unchanged) -> refund back); one over-cap 429 carrying `resets_at`, `scope`, `retry_after_seconds` + `Retry-After`; ZERO `[USAGE-DEVICE] consume fail-open` lines (any one = CR3, roll back); the `account-only` INFO count falling as the OTA spreads; ONE EVAL per compare in the Upstash command count; `[REFERRAL-PAUSE]` lines only on referral events. Rollback: unset the variable (per call; device counters expire within a day; the stash still refunds an in-flight debit).

## Commit blocked (ruling needed before the commit)

The hook (gitleaks 8.30.1 with `HEAD:.gitleaks.toml`) refused the staged set: exactly ONE finding, `generic-api-key` at `tests/test_s81_s09_device_quota.py:831` (the frozen RED file, `_RefClient.respond`: `[the synthetic share-token field: value elided for the docs hook, see the unit report]`, a synthetic value in a key named like a token). GREEN may not edit the frozen file, bypass the hook or widen `.gitleaks.toml` (read from HEAD; its own PR). Measured fix for the ruling: the one-line amendment `[the synthetic share-token field: value elided for the docs hook, see the unit report]` (the same bytes at run time; the golden is unchanged) gives sha256 `551a3167ac54d1ef842f76d1603c05c3a7e404384f6f161bb33bc1c4fad6963f`, 0 gitleaks findings on the same config (the frozen bytes: 1), and 193 / 193 with the flags OFF and ON as a temporary probe copy (`s09green-amended-off` 81 s OK, `s09green-amended-on` 52 s OK). After the re-freeze the commit is the same 13 paths with the amended RED file.

## Deviations and questions for the gate

- GC-13 vs the frozen RED r22: GC-13 limits the usage_service leaf reads to {device_fingerprint, device_key} and lists `header_state` as a forbidden needle, but r22 (frozen, 4 nodes) requires the `account-only header=<absent|malformed|ok>` metric of spec 2.5 step 1, and absent vs malformed is only visible through `header_state`. GREEN kept `header_state(HEADER_DEVICE_FINGERPRINT)` and pinned exactly that set in E3 (ruling requested). GC-13's "function-local" import: the import is module-level, the S81-06 E9 form it cites (llm_router imports at module level); one import per file holds.
- `usage_routes.py` passes `**device_quota_kwargs()` to `get_device_usage_status` instead of naming the leaf (spec 3.6 named the leaf there), so usage_service is the only new consumer of the leaf.
- The quota-path status GETs take the ST1 pool under `ENABLE_USAGE_PATH_OFFLOOP` (spec 2.7), with the ST1 inline fallback and its WARNING shape (g6 x2); r25a's pool-GET assertion is `>= 2`, so it does not move.
- An explicit `consumed_keys` carrying `device_daily` and the stash share one latch (g5); no route passes keys today.
- GC-2 site measurement: the consume result reaches a response only through the 429 detail, whose `tier` / `remaining` the handler drops; no log line formats it (gc2 wire rows x6 pin the key set).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
