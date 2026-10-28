# S81-08b LEGACY-FINGERPRINT-READER: a dark second device-match key at register and the W3-3 social apply

Flag `ENABLE_LEGACY_FINGERPRINT_READER` (new name, default OFF, read per call as the FIRST statement of the gated predicate). Lane B backend, additive. Branch `feature/s81-s08b-legacy-fingerprint-reader`, GREEN commit `63f159efec41b08e875749c3b3f2b2f7035caa2e` on base `86d5a24d` (origin/main at launch). Authorities: `specs/GATE_S81_08B.md` (GC-1..GC-11) over `specs/RULINGS_S81_08B.md` (R-S08B-1..11) over the review corrections over the spec (`.qa-s80/S81-08b_UNIT_SPEC.md`).

## What the flag does

After the S81-08 OTA the client's `X-Device-Fingerprint` carries the NEW SecureStore-id hash while every stored `users.device_fingerprint_hash` row written before the OTA holds the build-3 composition. Until the client runtime cutoff 2027-03-31T21:00Z the client also sends that composition as `X-Device-Fingerprint-Legacy` at register and both social sign-ins (never at share, compares or usage status: RULINGS_S81_08 R-S08-4 as amended by R-S08B-5).

- **ON**, at POST `/api/v1/auth/register` and in the W3-3 social apply (`_apply_social_device_fingerprint`, reachable only with `ENABLE_SOCIAL_DEVICE_FINGERPRINT` ON), a request carrying a valid primary value AND a valid legacy value (64 lower-case hex, FULL match, different from the primary) reads the device counter through ONE select (GC-2 literals): `.select("lifetime_comparisons_used, device_fingerprint_hash").in_("device_fingerprint_hash", [fp, legacy]).order("lifetime_comparisons_used", desc=True).limit(1)`. The update is the base write: the caller's own row, storing the PRIMARY value only (no upgrade-on-match, R-S08B-4), counter `max(floor, matched)`.
- One INFO `[LEGACY-FP] site=register|social top=legacy|new|none` per dual read (constants only); a failure is one WARNING `[LEGACY-FP] site=<site> inherit failed: <TypeName>` and never propagates (the register except arm, which logs `str(exc)`, never sees it).
- An invalid, empty, absent or primary-equal legacy header is dropped SILENTLY (no log, never a 400, R-S08B-6); a legacy header without a valid primary value matches nothing (as today).
- **OFF**, or **ON without the legacy header (build 3)**: byte-identical (same DB calls, bodies and log lines; literal call-list pins P1/P2/P5/P7 under the full configuration). No response key, status, header or OpenAPI change. The share route, SAME_DEVICE and the referral device lifetime cap are untouched and pinned (P8, P11, P12).

New symbols (all in `app/api/auth_routes.py`): `legacy_fingerprint_reader_enabled() -> bool`; `_read_valid_legacy_fingerprint(request, fp)` (positional, reads only through `request.headers.get`, reuses the already-imported `_DEVICE_FINGERPRINT_RE` with `fullmatch`, never logs, returns None when the mapping raises or legacy == fp; GC-3); `_inherit_device_counter_with_legacy(admin_client, fp, legacy, user_id, *, floor=0, site)`. `_read_valid_device_fingerprint` and `_inherit_device_counter` are byte-identical (P13 shas).

## Defect ids -> RED nodes -> flag -> precondition

| Defect id | What | RED nodes (tests/test_s81_s08b_legacy_fingerprint.py) | Flag | Precondition |
|---|---|---|---|---|
| S81-08b (DEFECT_LEDGER; the OTA precondition of RULINGS_S81_08 R-S08-4) | a post-OTA re-signup on an existing device inherits nothing (stored rows hold the legacy composition, the primary header carries the new hash) | R1 test_r1_flag_reader_idiom; R2 test_r2_legacy_helper_truth_table; R3 test_r3_register_dual_read_legacy_max; R4 test_r4_register_stores_new_when_new_holds_max; R5 test_r5_social_dual_read_with_floor[own1-device4], [own6-floor]; R6 test_r6_register_info_line_constants_only; R7 test_r7_social_info_line; R8 test_r8_top_new_and_top_none[new-max], [no-rows]; R9 test_r9_dual_failure_is_silent_and_typed[register], [social]; R10 test_r10_one_legacy_reader_in_app; R11 test_r11_claude_md_row (14 nodes, every base failure an AssertionError) | ENABLE_LEGACY_FINGERPRINT_READER | deployed + the owner's DATED ledger line `ENABLE_LEGACY_FINGERPRINT_READER=true on web (deployment <sha>)` before the first OTA (never "merged") |
| S81-08d (opened by R-S08B-1, not this unit) | SAME_DEVICE is dead at base (`_load_invitee` selects no device hash) | pinned untouched: P11 test_p11_same_device_untouched (M19) | (its own flag, later) | after S81-09 |
| auth_service B4-BE-DIAG (GC-4 note, not this unit) | the two tests/test_auth_interceptor.py nodes stay the pre_impl baseline | none (identical base and head) | none | not scheduled |

PIN rows (71 nodes, green at base and head): P1 x7, P2 x6, P3 x6, P4 x16, P5 x4, P6 x2, P7 x6 + 3, P8 x6, P9 x4, P10 x2, P11 x2, P12 x2, P13 x2, P14 x2, plus test_r6pre_base_paths_log_no_user_id.

## Change list (spec section 3 as amended)

| File | Change | sha256 before -> after |
|---|---|---|
| app/api/auth_routes.py | 1a `legacy_fingerprint_reader_enabled` after `social_device_fingerprint_enabled`; 1b `_read_valid_legacy_fingerprint` after `_read_valid_device_fingerprint`; 1c `_inherit_device_counter_with_legacy` after `_inherit_device_counter`; 1d the social apply: the legacy read after the `if not fp or not user_id` guard, the base call verbatim under `if legacy is None:`, else the dual call (same floor, site="social"); 1e register: the legacy read inside `if fp and new_user_id:` before `try:`, the base call verbatim under `if legacy is None:`, else the dual call (site="register"); the except arm unchanged. +120 / -7 (the 7 are the two base calls re-indented under the branch), CRLF kept (1,763 CRLF, 0 LF-only), added lines ASCII | 0ee900c9... -> f49c4b95... |
| CLAUDE.md | 2a the `**SESSION 81 flag (S81-08b LEGACY-FINGERPRINT-READER, ...)**` row after the newest session-81 row on main (S81-14), before `## Tests` (6,558 chars, every R11 token, no "after S81-08 merges"); 2b the Feature Flags pointer sentence after the S81-04 one (:341); 2c the Auth + security hardening bullet (:231) in place. +9 / -2, CRLF kept, added text ASCII | 1b2375cb... -> 6a52dd06... |
| tests/test_s81_s08b_legacy_fingerprint.py | the RED file (frozen, written at RED, unedited) | new, 2f4f8237... (45,921 B) |

No other file: no migration, no client file, no sentry_service / middleware / leaf change, no `tests/test_s75_fanout_identity.py` or `.github/black-clean-paths.txt` change, no requirements / package / `.env` / `tests/.pre_impl_failures.txt` edit.

## Deliberate pin changes (spec 4.1)

NONE (E-none). Every pin the spec names in 4.2 stays green and unedited at HEAD:

| Pin file | Why it does not move |
|---|---|
| tests/test_social_login_device_fingerprint.py | runs with the new flag unset -> the base path, call for call (`device.eq.assert_called_once_with("device_fingerprint_hash", FP)` stays true) |
| tests/test_auth_routes_invite_fingerprint.py, tests/test_usage_device_inheritance.py | send no legacy header |
| tests/test_s81_s05_request_context.py (r08, p01, p02, p05, p06, p07, p08) | route-level read: no leaf import added, `_DEVICE_FINGERPRINT_RE` never reassigned, exactly one `request.headers.get("X-Device-Fingerprint")` literal, no p01 needle, no `legacy` + `_hash` / `device` + `_lookup_keys` name in app/ or scripts/ |
| tests/test_abuse_detection*.py, tests/test_referral_*.py, tests/test_u3c_referral_push_name.py | cover code this unit does not touch |
| tests/test_s71_u13_compare_auth_required.py (T23), test_s05_p02 | the legacy header is read from `request.headers`, never declared as a `Header(...)` parameter (P10 mirrors it) |
| tests/test_s75_fanout_identity.py (FY25) + tests/test_s81_kb_schema.py IDENTITY_NODES | FY25 file unedited (the flag is never read on a compare path) |
| tests/test_ci_gates.py, tests/test_behavior_dimension_translation.py, tests/test_s81_s04_spend_breaker.py (r38) | the new row is its own column-0 `**SESSION 81 flag (...)**` paragraph after the S81-14 block, so the S81-04 slice still ends at the next `
**SESSION` |
| tests/test_sentry_channels_u8d_unit.py (R10), tests/test_consent_capture_w3_16.py, tests/test_s79_b3b_apple_revoke.py, tests/test_security_regression.py | no sentry / consent / Apple / security code touched |

## Gates (bounded runner pyt.py, shared .venv-qaren, one pytest at a time)

First gate at base 86d5a24d, before any edit (GC-6):
- RED file: 14 failed (14 x AssertionError, no other type), 71 passed, 11 warnings in 5.05s; [hermeticity] sentinel checked 85 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
  `[pyt] tag=s08b-green-gate1-unit-base start=2026-10-29 00:03:27 end=2026-10-29 00:03:33 elapsed=6s bound=600s status=FAIL rc=1`
- set A (8 files): 599 passed; [hermeticity] sentinel checked 599 test(s); [netguard] blocked 14 attempt(s) from 8 node(s)
  `[pyt] tag=s08b-green-gate1-A-base start=2026-10-29 00:03:39 end=2026-10-29 00:04:09 elapsed=29s bound=1200s status=OK rc=0`
- set B (13 files): 661 passed, 1 skipped; [hermeticity] sentinel checked 661 test(s); [netguard] blocked 34 attempt(s) from 6 node(s)
  `[pyt] tag=s08b-green-gate1-B-base start=2026-10-29 00:04:16 end=2026-10-29 00:04:37 elapsed=21s bound=1200s status=OK rc=0`

At HEAD:
- lint: `python -m py_compile` rc 0 (auth_routes.py, the RED file); `python -m ruff check --select E9,F63,F7,F82 --no-cache` (ruff 0.16.5): All checks passed!; the pre-commit hook passed on the commit (no --no-verify).
- unit file, flag unset: 85 passed; sentinel 85; netguard 0 / 0 -- `[pyt] tag=s08b-green-unit-off start=2026-10-29 00:10:53 end=2026-10-29 00:10:57 elapsed=4s bound=600s status=OK rc=0`
- unit file, `ENABLE_LEGACY_FINGERPRINT_READER=true` exported for the call: 85 passed; sentinel 85; netguard 0 / 0 -- `[pyt] tag=s08b-green-unit-on start=2026-10-29 00:10:58 end=2026-10-29 00:11:02 elapsed=4s bound=600s status=OK rc=0`
- set A flag OFF: 599 passed (= base); sentinel 599; netguard 14 from 8 -- `[pyt] tag=s08b-green-head-A-off start=2026-10-29 00:11:15 end=2026-10-29 00:11:36 elapsed=21s bound=1200s status=OK rc=0`
- set B flag OFF: 661 passed, 1 skipped (= base); sentinel 661; netguard 34 from 6 -- `[pyt] tag=s08b-green-head-B-off start=2026-10-29 00:11:43 end=2026-10-29 00:12:04 elapsed=21s bound=1200s status=OK rc=0`
- tests/test_s81_kb_schema.py flag OFF: 529 passed; sentinel 529; netguard 0 / 0 -- `[pyt] tag=s08b-green-head-kb-off start=2026-10-29 00:12:10 end=2026-10-29 00:12:18 elapsed=8s bound=600s status=OK rc=0`
- flag ON sweep (A + B + kb_schema, one call, the flag exported for that call only): 1789 passed, 1 skipped; sentinel 1789; netguard 48 from 14 -- `[pyt] tag=s08b-green-head-AB-on start=2026-10-29 00:12:26 end=2026-10-29 00:13:10 elapsed=44s bound=1200s status=OK rc=0`
- CI-order set (22 files sorted: sets A + B, which hold the CLAUDE.md readers, + the RED file), flag unset: 1345 passed, 1 skipped; sentinel 1345; netguard 48 from 14 -- `[pyt] tag=s08b-green-ci-order start=2026-10-29 00:26:40 end=2026-10-29 00:27:20 elapsed=40s bound=1200s status=OK rc=0`
- mutation table on the COMMITTED bytes (real worktree, MUTATION LOCK, byte copies, restore sha-verified after each, worktree clean vs HEAD after the run): 20 / 20 KILLED on an AssertionError by the named row or its stated alternate (M1 P1; M2 R1; M3 R2; M4 P3; M5 R3/R4; M6 R4; M7 R3; M8 R10 (unguarded peek: R2 fails too, with the exploding mapping's RuntimeError; the guarded variant M8b is killed by R2 + R10, AssertionError only); M9 R6; M10 R9; M11 P5; M12 P4; M13 P2; M14 R6 + R7 (R8 keeps its labels by construction, as the RED found); M15 R8; M16 R5; M17 P6; M18 P8 + R10; M19 P11; M20 P12). Each `[pyt] ... bound=600s status=FAIL rc=1`, 5-9 s; full lines in green_mutants.json.

### Comm set (zero-regression gate)

Base record = the RED's 241-file record at 86d5a24d (GC-6; `specs/S81_08B_COMM_SET.txt`): 12,083 passed, 3 failed, 2 errors, 35 skipped, 40 deselected, 36 xfailed. At HEAD the union was re-derived (`green_comm.py`): all 241 re-derived (none dropped) + the RED file = the binding 242-file set, run in the RED's own chunk composition (chunks 00-08 byte-identical to the base chunks, chunk 09 = the base chunk 09 + the RED file last), one chunk at a time, bound 1200, the repo's NETWORK_FLAKY_EXCLUDE deselected as at base, the flag unset:

| chunk | HEAD result | [pyt] |
|---|---|---|
| 00 | 2 failed, 793 passed | `[pyt] tag=s08b-comm-head-00 start=2026-10-29 00:15:14 end=2026-10-29 00:15:45 elapsed=30s bound=1200s status=FAIL rc=1` |
| 01 | 1231 passed, 1 skipped, 8 deselected | `[pyt] tag=s08b-comm-head-01 start=2026-10-29 00:15:45 end=2026-10-29 00:16:28 elapsed=43s bound=1200s status=OK rc=0` |
| 02 | 1366 passed, 10 deselected | `[pyt] tag=s08b-comm-head-02 start=2026-10-29 00:16:28 end=2026-10-29 00:16:58 elapsed=30s bound=1200s status=OK rc=0` |
| 03 | 1230 passed | `[pyt] tag=s08b-comm-head-03 start=2026-10-29 00:16:58 end=2026-10-29 00:18:11 elapsed=73s bound=1200s status=OK rc=0` |
| 04 | 550 passed, 8 deselected | `[pyt] tag=s08b-comm-head-04 start=2026-10-29 00:18:17 end=2026-10-29 00:18:36 elapsed=19s bound=1200s status=OK rc=0` |
| 05 | 493 passed, 24 skipped, 3 deselected, 1 xfailed, 2 errors | `[pyt] tag=s08b-comm-head-05 start=2026-10-29 00:18:36 end=2026-10-29 00:19:04 elapsed=28s bound=1200s status=FAIL rc=1` |
| 06 | 1096 passed | `[pyt] tag=s08b-comm-head-06 start=2026-10-29 00:19:05 end=2026-10-29 00:21:44 elapsed=159s bound=1200s status=OK rc=0` |
| 07 | 1 failed, 3853 passed | `[pyt] tag=s08b-comm-head-07 start=2026-10-29 00:21:49 end=2026-10-29 00:23:57 elapsed=129s bound=1200s status=FAIL rc=1` |
| 08 | 539 passed, 1 skipped, 11 deselected | `[pyt] tag=s08b-comm-head-08 start=2026-10-29 00:23:58 end=2026-10-29 00:25:01 elapsed=63s bound=1200s status=OK rc=0` |
| 09 (+ RED file) | 1017 passed, 9 skipped, 35 xfailed | `[pyt] tag=s08b-comm-head-09 start=2026-10-29 00:25:01 end=2026-10-29 00:25:32 elapsed=31s bound=1200s status=OK rc=0` |

HEAD totals over the 242 files: 12,168 passed (= 12,083 + the RED file's 85), 3 failed, 2 errors, 35 skipped, 40 deselected, 36 xfailed; every [hermeticity] / [netguard] figure per chunk equal to base (09 adds the RED file's 85 checked, 0 blocked). HEAD FAILED/ERROR set = the five known base nodes, identical both sides:
- tests/test_auth_interceptor.py::test_sign_in_with_social_exception and ::test_social_login_user_insert_fails_gracefully (tests/.pre_impl_failures.txt; the unconditional B4-BE-DIAG branch, GC-4)
- tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence and ::test_truth_on_prefix_static_and_cacheable (ERROR, cold tiktoken cache)
- tests/test_sentry_channels_u8d.py::TestU8dPins::test_u8d_pin_integration_list_unchanged (SR8: red in the shared venv while the anthropic SDK is installed there; fixed by the S81-06 merge #374)

**branch-only-new (`comm -13` of the sorted FAILED sets) = EMPTY**; `comm -23` (fixed at head) = EMPTY.

Supplementary (HEAD only, no base record needed): the re-derivation also caught 20 files that reference only `get_admin_supabase_client` in OTHER modules' namespaces (not a symbol this unit changes or newly references); chunk 10: 303 passed, 5 deselected, 0 failed -- `[pyt] tag=s08b-comm-head-10 start=2026-10-29 00:25:38 end=2026-10-29 00:26:04 elapsed=26s bound=1200s status=OK rc=0`. A passing file cannot hold a branch-only-new failure.

## Stated limits (GC-9, R-S08B-10)

1. Two request-time sites only: register and the W3-3 social apply; with `ENABLE_SOCIAL_DEVICE_FINGERPRINT` OFF (production state UNKNOWN: no dated ledger line names it) the social half is inert.
2. SAME_DEVICE is dead at base (`referral_service._load_invitee` selects no device hash, so `abuse_detection_service.evaluate_invite` always sees None) and stays untouched; it compares stored values with stored values, so no header can reach it (its revival is S81-08d).
3. The referral device lifetime cap (stored-vs-stored) splits across the transition: legacy-hash and new-hash accounts on one device are two buckets, at most one extra cap of 3 lifetime invites per device (accepted, R-S08B-1; S81-09 revisits device identity).
4. After the cutoff a device that never registered inside the window loses its link to its legacy-hash rows.
5. The legacy value is today's composition with the CURRENT osBuildId: a row stored under an earlier OS build, app id or nonce matches neither header, as at base (the reader restores today's match rate, no more).
6. The header is a client claim: the reader can only raise the inherited counter and never changes what is stored; a client can still escape inheritance with a random primary value, as today.
7. The register except arm keeps its pre-existing `str(exc)` WARNING (flag-independent); the dual function never raises into it.
8. The anon gate keys (`anon:<fp>`) are untouched (build 3 sends no device header on the anonymous routes; anonymous compares are 401 under `ENABLE_COMPARE_AUTH_REQUIRED`); CORS `allow_headers` does not list the legacy header (native clients do not preflight; an Expo web build would, like S81-05 limit 5).
9. The claim that the 023 partial index `idx_users_device_fingerprint_active` serves the `IN` read is reasoned from its predicate, not measured on a database.
10. The comm-set base was measured by the RED (241 files at 86d5a24d); GREEN measured HEAD only. The stakes are bounded: the per-user daily and monthly free counters are unaffected; the inherited lifetime counter gates only the lifetime-free branch and the `/usage/status` lifetime figure. The `top=` label is not deterministic on a counter tie (a log label only).

## Owner steps (names only)

- Right after this unit deploys, as its OWN step in the PLAN_S81 flip order BEFORE the first OTA: set `ENABLE_LEGACY_FINGERPRINT_READER=true` on `web` and record the dated ledger line `ENABLE_LEGACY_FINGERPRINT_READER=true on web (deployment <sha>)`; that line (never "merged") is the S81-08 OTA precondition. It may precede Apple approval (ON without the header is byte-identical for build 3) and is independent of, and earlier than, `ENABLE_REQUEST_CONTEXT_HEADERS` (which flips after the OTA in its own window).
- Canary after the OTA: a re-signup on a pre-OTA test device with no OS update since its first registration logs `[LEGACY-FP] site=register top=legacy` and inherits the old counter.
- Rollback: unset the variable (read per call, immediate). Nothing else: no migration, no credential, no pepper.
- Orchestrator (not this PR): OWNER_ACTIONS gains the flip item (GC-7); the DEFECT_LEDGER S81-08b row gains the RED file / branch / HEAD.

## Rebase note

origin/main moved to `a8f01379` (#374 S81-06 ANTHROPIC-ROUTER, 2026-10-28 23:57) after this GREEN launched on `86d5a24d`. At the rebase (R-S08B-11, C13): CLAUDE.md :341 is one physical Feature Flags line that S81-06 also edits (re-apply the one S81-08b pointer sentence by hand on top of S81-06's line) and the row anchor after the newest session-81 row is a union with S81-06's row; `app/api/auth_routes.py` is not touched by S81-06; re-derive the comm set at the rebased HEAD (S81-06 adds files that import app.main) and expect the SR8 node to turn green there.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
