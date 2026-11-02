# S81-09 DEVICE-QUOTA-RIYADH: 3 compares a day per device + the Asia/Riyadh reset (two dark flags)

Lane B backend, PLAN_S81 M3 (`PLAN_S81.md` :148; the VERIFY quota grafts :102-104; owner decisions 2 and 5). FOCUS unit (quota + Lua): two adversaries (LC-1, GC-12), both SOUND (0 blocking / 0 major; 10 + 5 minors ruled in `specs/RULINGS_FIX1_S81_09.md` F1-1..F1-14). Base = origin/main `6c14ac954f601902d322547de04982033aca5925` (fetched 2026-11-02; S81-08 #377 on top of the unit's first base `e7c81956`: SmartCompareApp files + CLAUDE.md + docs only). Branch `feature/s81-s09-device-quota-riyadh`: HEAD = `f563b0c2636a921c31639e3f896f587610f6ecb3`, ONE commit on that base: fix round 1's `990f06d8` (the 13 GREEN paths + EK4 + four gate rows + docs, made through the hook) replayed by the rebase round (`specs/RULINGS_REBASE_S81_09.md` RB9-1..RB9-4); the only conflict was CLAUDE.md (the RB9-2 union below); no pin row was needed. Spec `.qa-s80/S81-09_UNIT_SPEC.md`, its review, `specs/RULINGS_S81_09.md` (R-S09-1..15), `specs/GATE_S81_09.md` (GC-1..GC-14); reports `specs/S81_09_{GREEN,FIX1,REBASE}_REPORT.md`, `specs/S81_09_ADV1_{correctness,quotaandbilling}.md`, `specs/S81_09_REBASE_EVIDENCE.md` (session-81 state folder).

## What the flags do (both default OFF, read PER CALL, new names: unset in production)

- `ENABLE_RIYADH_RESET`: ONE date helper (`usage_service._usage_window`) moves every usage date key (`usage:daily:` / `usage:monthly:`, the previous-window refund fallbacks, the anon keys, the quota path and its status) to the Asia/Riyadh calendar (fixed +03:00, no DST; zoneinfo has no tzdata on the pinned venv); the daily counters reset at 00:00 Riyadh (21:00 UTC). A drift pin ties it to `llm_spend_breaker.riyadh_day` (r30). OFF: the UTC keys byte for byte. A refund across the Riyadh flip finds the old UTC key as Riyadh-yesterday only after 21:00 UTC; inside 00:00-21:00 UTC the two key strings coincide (F1-7).
- `ENABLE_DEVICE_DAILY_QUOTA` (free tier, not in `DEVICE_QUOTA_EXEMPT_USER_IDS`; premium, a NULL or any other tier and the allow-list run the base path byte-identically, R-S09-4/5): ONE Upstash Lua EVAL per consume (`DEVICE_CONSUME_SCRIPT` via `llm_spend_breaker._eval`, offloaded under `ENABLE_ASYNC_REDIS_OFFLOAD`) checks and debits the device-daily key `usage:device:<S81-05 HMAC device key>:<day>` FIRST and the account-daily key `usage:daily:<uid>:<day>` (3 each, `DEVICE_DAILY_CAP = 3`, no knob, R-S09-6), EXPIREAT the next reset + 1 h; a refusal writes nothing; the monthly cap, the referral bonus and the lifetime-free bypass are retired on that path (a fresh account on a capped device gets nothing). The 429 `USAGE_LIMIT` gains `resets_at` + `scope` through the flag-gated handler allow-list and `retry_after_seconds` / `Retry-After` through the W1-9 block. A failed compare refunds both keys exactly once through `DEVICE_REFUND_SCRIPT` from a request-scoped debit stash (no refund call site changed; R-S09-3 / GC-5: the stash is read whatever the flag says). `/usage/status` reports the BINDING axis in `remaining.daily` / `used.daily` (R-S09-1), `remaining.device_daily` with a device key, `limits.device_daily` = 3 (always, appended last, GC-3), `resets_at`, `counted_scope`, the retired monthly axis as never binding and `remaining.lifetime_free` 0 (R-S09-14). A missing / malformed / unkeyable header = account-only + ONE INFO `[USAGE-DEVICE] account-only header=<state>`, never a 400; a Redis error or bad reply fails OPEN with ONE WARNING `[USAGE-DEVICE] consume fail-open type=<Name>`. The referral rewards pause under the same flag (R-S09-2, GC-1): no Loop-1 Deep Review credit, no Loop-2 redemption row / bonus bump / invitee credit / `lifetime_invites_consumed` slot, no reward push; the invite row and the redeemed mark unchanged; ONE INFO `[REFERRAL-PAUSE] ...` each.
- Both OFF: byte-identical (Redis calls, results, raw bodies, log lines, referral writes and push), pinned by the committed golden `tests/fixtures/s81_s09_flag_off_golden.json` under the five OFF spellings with the full configuration (B1).

## Files

| file | lines (vs base) | blob sha256 at HEAD (prefix) |
|---|---|---|
| CLAUDE.md | +9 / -2 | d14e0f8b3caa892e |
| app/api/image_routes.py | +4 / -1 | abb783f1b50c80c3 |
| app/api/text_routes.py | +14 / -3 | d191e0fcf14dd1d3 |
| app/api/url_routes.py | +6 / -1 | 508fec0ad7d29ea2 |
| app/api/usage_routes.py | +16 / -1 | 47336e28dbd46f20 |
| app/middleware/error_handler.py | +29 / -0 | bf71cbd1dcd05071 |
| app/services/referral_service.py | +38 / -6 | aad54e3cc4227c8f |
| app/services/usage_service.py | +478 / -12 | b096a76733a291fb |
| tests/fixtures/s81_s09_flag_off_golden.json | +722 / -0 | 02b29cc6d3a64932 (frozen) |
| tests/test_s81_s05_request_context.py | +27 / -4 | c0394a5307c50388 |
| tests/test_s81_s09_device_quota.py | +2068 / -0 | 551a3167ac54d1ef (frozen, EK4) |
| tests/test_s81_s09_gate_rows.py | +389 / -0 | a8e01fcf6f22c5de |
| tests/test_s81_st1_usage_path_offloop.py | +15 / -7 | 6a0d65ad05c62ecf |

The 12 non-CLAUDE blobs are byte-identical to fix round 1's `990f06d8` (replayed without conflict); the app/ files and the two edited pins keep the fix round's CRLF working copies; the three new files were re-checked-out CRLF by the rebase (core.autocrlf), blobs unchanged (every working-copy sha256: the evidence file). `git diff --stat origin/main...HEAD` = exactly these 13 files, no whole-file diff; `git diff --check` clean; no conflict marker in CLAUDE.md, app/ or tests/.

No migration, no lock / requirements / package file, no client file, no `.githooks` change (the four hook test files were still run once alone at the rebased HEAD: `[pyt] tag=s09rb-hook-notdash elapsed=280s bound=1800s status=OK rc=0` -- 167 passed, 160 deselected; `[pyt] tag=s09rb-hook-dash elapsed=492s bound=1800s status=OK rc=0` -- 157 passed, 3 skipped, 167 deselected), no personal value.

## The rebase (RB9-1, RB9-2)

`git merge-tree` re-measured: CONFLICT CLAUDE.md only; the rebase stopped on CLAUDE.md alone (two regions), resolved from `git show` blobs (written CRLF) as the union in merge order: main's rows stay (... S81-06, S81-08b, S81-15, S81-08) and the S81-09 block goes immediately after the S81-08 block, before `## Tests`; the `**Feature Flags:**` pointer paragraph = main's text plus this unit's pointer where the branch put it; the Key-services `usage_service.py` bullet = the branch's rewrite with main's S81-08 sentence (appended to that bullet on main) kept verbatim after it; no row reworded. Non-ASCII bytes: main 3,937, the branch's delta -6 (an em dash and an arrow rewritten in ASCII), the result 3,931; index blob `d14e0f8b...` = the composed bytes.

## Requirement -> node map (DEFECT_LEDGER row S81-09; RED `tests/test_s81_s09_device_quota.py` 193 nodes = 87 RED + 106 PIN; gate rows `tests/test_s81_s09_gate_rows.py` 24 nodes = 20 GREEN + 4 fix round 1)

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
| refund both keys once (stash), across Riyadh midnight, after a flag flip (L6), explicit-keys latch | r15, r16 (x4), r17, r34, r39, g5, f1_12 (no stash across requests) |
| previous daily key = Riyadh-yesterday | r18 |
| status binding axis, counted_scope, limits.device_daily, ST1 placement | r19, r20 (x4), r21, r31, r37 (x3), r38 (x3), gc3, g6 (x2), f1_2 (Riyadh day after 21:00 UTC), f1_3 (NULL tier) |
| account-only + ONE metric; no secret in logs | r22 (x4), r23 |
| fail-open + outage metric; bad reply (C19) | r26, r27 (x5), f1_4 (code 2 without a device key) |
| retired monthly + bonus | r33 |
| referral pause (R-S09-2) + step 4 (GC-1) | r40, r41, p15 (x10), gc1a, gc1b (x5) |
| flag-OFF identity, full config | p01 (x30), p02 (x15), p03 (x15), p04 (x6), p05 (x7), p08, p09, p10, p12, p13, p14 |

## Deliberate pin changes (E-rows: E1 + E2 + E3 = exactly 8 nodes, as both adversaries measured; nothing else moved)

| E | node(s) | change | reason |
|---|---|---|---|
| E1 | `tests/test_s81_st1_usage_path_offloop.py::test_r25b_frozen_digests[app/services/usage_service.py::<fn>]` for `_daily_key`, `_monthly_key`, `_previous_daily_key`, `_previous_monthly_key`, `consume_comparison_credit`, `refund_comparison_credit` (6 nodes) | BASE_DIGESTS re-recorded (the six old -> new prefixes: `specs/S81_09_REBASE_EVIDENCE.md`; one comment naming S81-09) | the one usage date helper behind the four key helpers, the flag-gated quota branch, the stash refund block; flag-OFF behaviour stays pinned by ST1 BASE_CONSUME_SEQ / BASE_REFUND_SEQ / BASE_ROUTE (green, unedited) and the S81-09 golden; the other 22 digests unchanged |
| E2 | `...::test_r25a_source_inventory` | `to_thread` count 4 -> 5 | the one `_offload_dispatch_async` (the #115 dispatch of the device EVALs, parity with `_atomic_consume_async`); r25a's other assertions unedited and green |
| E3 | `tests/test_s81_s05_request_context.py::test_s05_p01_no_consumer_in_app` | `_ALLOWED_CTX_FILES` += `app/services/usage_service.py`; its import pinned to exactly `from app.utils import request_context as _request_context` and its attribute uses to {device_fingerprint, device_key, header_state, HEADER_DEVICE_FINGERPRINT}; the `header_state` needle allowed in that file (the S81-06 E9 form, generalised to a per-consumer table) | GC-13 as applied = the ruling (GC-14 (a), F1-8): the `header_state` needle is allowed for `usage_service.py` only, as the frozen r22 (4 nodes) needs the `account-only header=<absent|malformed|ok>` metric, which only the leaf's reader `header_state` produces; `usage_routes.py` no longer names the leaf (it passes `**device_quota_kwargs()`) |
| at the flip, not here | `tests/test_legal_disclosure_s77.py` D11, `tests/test_register_benefits_parity_s69.py` | green and unedited in this PR (TIER_LIMITS unchanged) | re-pinned in the `DEVICE_QUOTA_RESET` re-fill PR (S81-12 spec E24 / D5) |

Measured: the BASE ST1 bytes against the GREEN code fail exactly the 7 E1/E2 nodes; the BASE S05 bytes fail exactly the E3 node (8 in all; re-measured by the quota-and-billing adversary, s09adv-qb-erows: 8 failed, 699 passed); the 043 census (`test_every_per_user_cache_key_is_purged_or_kept`) stays green (R-S09-7: the key helpers keep their `user_id` f-strings; the device key interpolates no user id).

## Gates at the rebased HEAD (RB9-3; every pytest through `pyt.py`, one at a time; flags exported to one runner call only)

- ruff 0.16.5 `--select E9,F63,F7,F82 --no-cache` + py_compile on the 11 touched python files: clean.
- RED file, flags OFF: `[pyt] tag=s09rb-unit-off elapsed=4s bound=600s status=OK rc=0` -- 193 passed; both flags ON in the runner env: `[pyt] tag=s09rb-unit-on elapsed=4s bound=600s status=OK rc=0` -- 193 passed (the golden under the five OFF spellings with the full configuration are rows of this file).
- gate rows OFF: `[pyt] tag=s09rb-rows-off elapsed=3s bound=600s status=OK rc=0` -- 24 passed; ON: `[pyt] tag=s09rb-rows-on elapsed=3s bound=600s status=OK rc=0` -- 24 passed.
- each conflicted test file alone: none (no test file conflicted).
- R8 pair (`test_sentry_channels_u8d_unit.py` + `test_sentry_channels_u8d.py`): `[pyt] tag=s09rb-r8pair elapsed=17s bound=600s status=OK rc=0` -- 273 passed.
- `tests/test_paid_route_metering.py` flags unset: `[pyt] tag=s09rb-metering-off elapsed=4s bound=600s status=OK rc=0` -- 21 passed; both exported: `[pyt] tag=s09rb-metering-on elapsed=4s bound=600s status=OK rc=0` -- 21 passed.
- the CLAUDE.md readers (`test_ci_gates.py` + `test_behavior_dimension_translation.py`): `[pyt] tag=s09rb-readers elapsed=5s bound=600s status=OK rc=0` -- 79 passed.
- CI-order set, flags OFF (GREEN's 25 files + `test_s81_s04_spend_breaker.py`, `test_s81_s08b_legacy_fingerprint.py`, `test_s81_s08b_gate_rows.py` = 28; the two readers are members): `[pyt] tag=s09rb-ciorder elapsed=50s bound=1200s status=OK rc=0` -- 1711 passed.

Comm set (RB9-3 d): the 200-file list `specs/S81_09_COMM_SET.txt` re-derived at the rebased HEAD by the union rule (the RED's builder classes and seed, minus the four hook files and the two unit files): IDENTICAL, 200 members, no addition (main moved by SmartCompareApp files, CLAUDE.md and `docs/privacy-data-inventory.md` only; no backend test added or changed). BASE RECORD at 6c14ac95 per LC-6: 185 files reused per file from the two stored records (S81-12 rebase-fix `0ea73814...`, S81-10 RED `336233f0...`; they agree on every shared file), the 15 not yet recorded run here in one chunk in a detached scratch worktree of origin/main without a junction (`[pyt] tag=s09rb-base-u15 elapsed=18s bound=1200s status=OK rc=0` -- 102 passed), the union stored as `harness/base_records/6c14ac95.../c9f7585d75ab76da....txt` (+ `.pyt.log`, `.files`); its failed/error set = the cold-tiktoken pair (2 ERRORs in `tests/test_prompt_truth.py`, the known base noise). HEAD, 9 chunks of at most 25 + `test_secret_scan_static.py` alone:

- `s09rb-comm-00` 17 files: 28s OK rc=0 -- 899 passed
- `s09rb-comm-01` 10 files: 37s OK rc=0 -- 1352 passed
- `s09rb-comm-02` 25 files: 39s OK rc=0 -- 969 passed, 6 deselected
- `s09rb-comm-03` 25 files: 34s OK rc=0 -- 2284 passed
- `s09rb-comm-04` 25 files: 67s OK rc=0 -- 727 passed
- `s09rb-comm-05` 25 files: 25s FAIL rc=1 -- 969 passed, 27 skipped, 6 deselected, 1 xfailed, 2 errors
- `s09rb-comm-06` 25 files: 99s OK rc=0 -- 1041 passed
- `s09rb-comm-07` 24 files: 112s OK rc=0 -- 2569 passed, 1 skipped, 8 deselected
- `s09rb-comm-08` 23 files: 59s OK rc=0 -- 1130 passed, 9 skipped, 2 deselected, 35 xfailed
- `s09rb-secretscan` 1 files: 5s OK rc=0 -- 31 passed

HEAD failed/error set = the same pair; comm -13 (branch-only-new) **EMPTY**; comm -23 (base-only) empty. The S81-10 record's four deterministic failures (`test_auth_interceptor.py`, `test_page_scraping.py`) are not members of this set.

Client (RB9-3 e, f; node v24.11.1, jest 29.7.0, tsc 5.9.3; the project tools by path from `sc-s81-s09/SmartCompareApp` through the orchestrator junction, one jest at a time):

- shareTruth.s74 alone, first (it reads `app/services/referral_service.py`): `[jest] tag=s09rb-fence-shareTruth start=2026-11-02 12:09:24 end=2026-11-02 12:09:27 rc=0` -- Tests: 10 passed, 10 total
- the other 13 fences: `[jest] tag=s09rb-fences-13 start=2026-11-02 12:09:36 end=2026-11-02 12:09:42 rc=1` -- Tests: 4 failed, 226 passed, 230 total (only nativeBundle.w37 d5, k2, k4, k5 red: the accepted drift class)
- the FULL suite once (LC-7): `[jest] tag=s09rb-jest-full start=2026-11-02 12:09:51 end=2026-11-02 12:10:08 rc=1` -- Tests: 4 failed, 13 skipped, 13 todo, 3794 passed, 3824 total; Test Suites: 1 failed, 3 skipped, 385 passed, 386 of 389 total; Snapshots 42 passed; the four red nodes = nativeBundle.w37 d5, k2, k4, k5 (passed = 3,794 as on main); no -u, no .snap, `git status --short` empty
- `[tsc] tag=s09rb-tsc start=2026-11-02 12:10:39 end=2026-11-02 12:10:47 rc=0` -- 0 errors

The hook (RB9-3 g): git's sequencer commits a resolved pick with `git commit -n`, so `rebase --continue` printed no hook output; the repo hook (`.githooks/pre-commit`, main's bytes = HEAD's) was run by hand on the replayed commit's diff: a temp index holding `f563b0c2`'s tree inside the detached scratch worktree at 6c14ac95 (GIT_INDEX_FILE only; no commit, no ref moved): `[hook] tag=s09rb-hook-replayed start=2026-11-02 12:11:12 end=2026-11-02 12:11:15 rc=0`, ruff `All checks passed!`, black `1 file would be left unchanged` (+ black's py3.15 target-version warning), gitleaks no finding; plus a read-only `gitleaks git` scan of `6c14ac95..f563b0c2` with `HEAD:.gitleaks.toml`, `--redact --ignore-gitleaks-allow`: 1 commit scanned, no leaks found.

Earlier rounds (their per-run lines moved verbatim to the evidence file, LC-3): GREEN at `e7c81956` -- RED 193 / 193 OFF and ON, E-row probes 7 + 1, gate rows 20, CI-order 1309, comm 200 files branch-only-new EMPTY, fences red only on the 4 drift nodes; fix round 1 at `990f06d8` -- RED 193 / 193, gate rows 24 / 24, MF2 / MF3 / MF4 / MF12 KILLED, CI-order 1313, secret scan 31 (F1-13).

## Stated limits

R-S09-11, the RED's and fix round 1's (F1-5, F1-6, F1-11), as ruled:
1. Header-less callers (build 3; a device id not ready within S81-08's `DEVICE_ID_HEADER_TIMEOUT_MS`, 1,000 ms) get 3 a day per ACCOUNT with no monthly bound: about 90 a month, looser than base by about 9x; a forged random header evades the device axis, never the account axis (per-IP / per-device throttles are S81-24).
2. A Redis outage fails OPEN (a device can exceed 3 that day) AND skips `record_lifetime_comparison` on delivered url / camera compares (gated on `usage_consumed`), undercounting the lifetime counter.
3. The two Lua scripts never execute locally (no Lua runtime: the fake emulates them; r35 / r35b pin the literals and their shape); multi-key EVAL on Upstash is reasoned, not measured; a CROSSSLOT or reply-shape surprise fails open for every free compare until rollback (CR3: the first canary check).
4. Rollback: the monthly counter misses that month's quota-path consumes (up to 10 extra free compares); the device-rule texts stay published unless `DEVICE_QUOTA_RESET` is re-filled null through the U8 machinery.
5. Exempt users (premium, the allow-list, every non-free tier) are uncapped by the device rule and keep EXPIRE 86400 and the 32-day monthly key (the privacy s8 bullet speaks of the free tier; S81-12b wording); the exemption is account-based: a reviewer's NEW free account is device-capped (L14, R-S09-4).
6. The Riyadh flip opens one fresh window 3 h early, once (the three-hour transition); a rollback between 21:00 and 24:00 UTC can refund the wrong UTC window once; a mid-day flip of the quota flag keeps the shared account-daily count.
7. The OTA order binds: `ENABLE_REQUEST_CONTEXT_HEADERS` ON and the S81-08 header propagated before `ENABLE_DEVICE_DAILY_QUOTA`; `ENABLE_RIYADH_RESET` first in its own window; the v3 Terms live first; the referral-copy OTA propagated first (F1-10).
8. A premium or tier-read-failed status pays one extra tier read; without a header the status names `counted_scope` daily even when the device is exhausted (the next consume answers).
9. The anon gate (`check_anon_usage_allowed`) is untouched and never carries the new 429 fields (GC-4: M38 equivalent by construction); `check_usage_allowed` (no caller) ignores the device rule.
10. S81-10's refusal refunds are covered by the stash only inside the same request context (CR6, a known rebase).
11. Device counter keys are pseudonymous HMACs expiring about 1 h after the reset; a pepper rotation restarts every device counter that day.
12. A Supabase outage in the tier read puts every user, premium included, on the 3 / day quota path while `ENABLE_DEVICE_DAILY_QUOTA` is ON (the free default of `_get_user_tier_info`; base: the lifetime-free branch) (F1-6 a).
13. An EVAL whose reply is lost after it ran fails open (consumed False, no stash): a later failed compare is not refunded and both counters keep +1 until EXPIREAT (rare, bounded) (F1-6 b).
14. An exception out of `compare_from_text` on POST / GET `/api/v1/text/compare` reaches no refund arm (the base class: no try / except), so on the quota path both keys keep +1 until the window ends; the stream path's `finally` refunds (F1-11 a).
15. The Profile stat `bonus_credits_this_month` keeps summing pre-flip Loop-2 grants for the rest of the flip month while the quota path applies no bonus (bounded: 7-day expiry, the flip month); the client hides it later (CL4 / S81-11) (F1-11 b).
16. X03 is EQUIVALENT by construction: without `exc.status_code == 429` the handler's USAGE_LIMIT block behaves the same (all seven USAGE_LIMIT producers raise 429, grep-measured); no row (F1-5).

## Flip order and owner steps (names only; a dated ledger line per step)

1. `DEVICE_KEY_PEPPER` set on `web` (S81-05 item; no dated line yet). 2. Confirm the App Review accounts premium (session-79 ledger 06:55) or set `DEVICE_QUOTA_EXEMPT_USER_IDS`. 3. After approval: the S81-08 OTA published and propagated (two launches), then `ENABLE_REQUEST_CONTEXT_HEADERS=true` in its own window. 4. LEGAL-V3 (S81-12) merged and live (backend + landing). 5. `ENABLE_RIYADH_RESET=true` FIRST, alone, in its own window, between 00:00 and 21:00 UTC (canary: the next 21:00 UTC reset). 6. The referral-copy OTA (F1-10): under the quota flag the backend grants no referral reward while the build-3 / S81-08 copy still promises one (`referrals.share.reward.later`, `referrals.share.toast.confirm`, `home.bonus.*`, `referrals.status.bonusLabel`; `ENABLE_REFERRAL_SYSTEM` ON): flip only after an OTA whose copy stops promising rewards ('rewards are paused') has propagated (S81-11 + CL4 SHARE-FLOW). 7. Then one window: the data-only re-fill recording `DEVICE_QUOTA_RESET` (+ D11 re-pinned, landing re-render), then `ENABLE_DEVICE_DAILY_QUOTA=true` (the referral pause moves with it). The privacy s3.5 / deletion device-counter wording is S81-12b's edit at key retirement (R-S09-13). Notes for Review: the free limit is 3 comparisons a day per device.

## Canary (R-S09-10; the Lua runs for the first time in production)

On the test device: one success, one refusal and one refund, each followed by `/usage/status` (read back `used.daily`, `remaining.device_daily`, `counted_scope`, `resets_at`: the counters must move 0 -> 1 -> refusal (unchanged) -> refund back); one over-cap 429 carrying `resets_at`, `scope`, `retry_after_seconds` + `Retry-After`; ZERO `[USAGE-DEVICE] consume fail-open` lines (any one = CR3, roll back); the `account-only` INFO count falling as the OTA spreads; ONE EVAL per compare in the Upstash command count; `[REFERRAL-PAUSE]` lines only on referral events. Rollback: unset the variable (per call; device counters expire within a day; the stash still refunds an in-flight debit).

## EK4 and the commit (GC-14 amended; F1-1, F1-9)

The hook's gitleaks step (generic-api-key) had refused the frozen RED file at `tests/test_s81_s09_device_quota.py:831` (a synthetic share-token value). Fix round 1 applied the ONE sanctioned line: the value as two concatenated pieces (`"tok" + "-s09-synthetic"`; the runtime value, the golden and every row unchanged), nothing else. Blob sha256: frozen `843a6bab0215ca5289482a13f52646d9f9bbb0d334e4e5f78a2e9b1bd6c1ddae` (87,170 B) -> amended `551a3167ac54d1ef842f76d1603c05c3a7e404384f6f161bb33bc1c4fad6963f` (87,175 B, byte-identical to GREEN's measured copy). Commit `990f06d8` through the hook (never --no-verify): its gitleaks step passed; a read-only re-scan of `e7c81956..990f06d8` with the hook's flags and `HEAD:.gitleaks.toml`: 0 findings. The rebase round replayed it as `f563b0c2` (the 12 non-CLAUDE blobs unchanged; CLAUDE.md = the union); the hook re-run on the replayed diff passed and the read-only scan of `6c14ac95..f563b0c2` found no leaks (above).

## Deviations and questions for the gate

- GC-13 vs the frozen RED r22: GC-13 limits the usage_service leaf reads to {device_fingerprint, device_key} and lists `header_state` as a forbidden needle, but r22 (frozen, 4 nodes) requires the `account-only header=<absent|malformed|ok>` metric of spec 2.5 step 1, and absent vs malformed is only visible through `header_state`. GREEN kept `header_state(HEADER_DEVICE_FINGERPRINT)` and pinned exactly that set in E3 (ruled: GC-14 (a), F1-8). GC-13's "function-local" import: the import is module-level, the S81-06 E9 form it cites (llm_router imports at module level); one import per file holds.
- `usage_routes.py` passes `**device_quota_kwargs()` to `get_device_usage_status` instead of naming the leaf (spec 3.6 named the leaf there), so usage_service is the only new consumer of the leaf.
- The quota-path status GETs take the ST1 pool under `ENABLE_USAGE_PATH_OFFLOOP` (spec 2.7), with the ST1 inline fallback and its WARNING shape (g6 x2); r25a's pool-GET assertion is `>= 2`, so it does not move.
- An explicit `consumed_keys` carrying `device_daily` and the stash share one latch (g5); no route passes keys today.
- GC-2 site measurement: the consume result reaches a response only through the 429 detail, whose `tier` / `remaining` the handler drops; no log line formats it (gc2 wire rows x6 pin the key set).
- Rebase round, RB9-2 (c): main's S81-08 had appended one sentence to the same usage_service.py bullet; kept verbatim after the branch's rewrite (the union drops no main text). RB9-2 (a): main's Feature Flags paragraph carries no S81-08 pointer (unchanged since e7c81956), so the union equals the branch's paragraph.
- Rebase round: the hook ran by hand on the replayed diff (a temp index in the scratch worktree; git skips hooks on a replayed pick); the scratch worktree removed afterwards.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
