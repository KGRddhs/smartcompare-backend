# S81-08b LEGACY-FINGERPRINT-READER: a dark second device-match key at register and the W3-3 social apply

Flag `ENABLE_LEGACY_FINGERPRINT_READER` (new name, default OFF, read per call as the FIRST statement of the gated predicate). Lane B backend, additive. Branch `feature/s81-s08b-legacy-fingerprint-reader`.

- **Base:** origin/main `a8f01379b05c0079c72a74418bdbce2f4acfbe7d` (#374 S81-06 ANTHROPIC-ROUTER), fetched 2026-10-29 02:31 AST.
- **HEAD:** `9088563f9ecf1e4b61ac01dd0d6101def59d372e` (the pin commit) on top of `b8d611e42ca29d82cef4af0387174dc195fb8604` (the GREEN commit `63f159ef` replayed onto a8f01379).
- **Authorities, in precedence order:** `specs/RULINGS_REBASE_S81_08B.md` (RB8-1..RB8-12) over `specs/GATE_S81_08B.md` (GC-1..GC-11) over `specs/RULINGS_S81_08B.md` (R-S08B-1..11) over the review corrections over the spec (`.qa-s80/S81-08b_UNIT_SPEC.md`).
- **Reviews:** GREEN report `specs/S81_08B_GREEN_REPORT.md`; correctness adversary `specs/S81_08B_ADV1_correctness.md` = **SOUND (0 blocking, 0 major, 7 minor)**; engineering adversary `specs/S81_08B_ADV1_engineering.md` = **SOUND (0 blocking, 0 major, 7 minor)**. No fix round: every minor lands in this rebase round (table below).

## What the flag does

After the S81-08 OTA the client's `X-Device-Fingerprint` carries the NEW SecureStore-id hash while every stored `users.device_fingerprint_hash` row written before the OTA holds the build-3 composition. Until the client runtime cutoff 2027-03-31T21:00Z the client also sends that composition as `X-Device-Fingerprint-Legacy` at register and both social sign-ins (never at share, compares or usage status: RULINGS_S81_08 R-S08-4 as amended by R-S08B-5).

- **ON**, at POST `/api/v1/auth/register` and in the W3-3 social apply (`_apply_social_device_fingerprint`, reachable only with `ENABLE_SOCIAL_DEVICE_FINGERPRINT` ON), a request carrying a valid primary value AND a valid legacy value (64 lower-case hex, FULL match, different from the primary) reads the device counter through ONE select (GC-2 literals): `.select("lifetime_comparisons_used, device_fingerprint_hash").in_("device_fingerprint_hash", [fp, legacy]).order("lifetime_comparisons_used", desc=True).limit(1)`. The update is the base write: the caller's own row, storing the PRIMARY value only (no upgrade-on-match, R-S08B-4), counter `max(floor, matched)`.
- One INFO `[LEGACY-FP] site=register|social top=legacy|new|none` per dual read (constants only); a failure is one WARNING `[LEGACY-FP] site=<site> inherit failed: <TypeName>` and never propagates (the register except arm, which logs `str(exc)`, never sees it); the failure table is pinned by RB8-3 for RuntimeError, postgrest APIError and httpx.ConnectError on the dual read and on the dual update at both sites.
- An invalid, empty, absent or primary-equal legacy header is dropped SILENTLY (no log, never a 400, R-S08B-6); a legacy header without a valid primary value matches nothing (as today).
- **OFF**, **ON without the legacy header (build 3)**, or **ON with an invalid or primary-equal legacy header**: byte-identical. The DB calls and response bodies are pinned by the literal call lists of P1-P7 under the full configuration; the app.* log-record lists on those drop paths are pinned by RB8-2 against literals recorded at a8f01379 (no app.* record at all at either site, with a capture-liveness control), and no record of any logger carries the primary or the legacy value (RB8-2 (b)). No response key, status, header or OpenAPI change. The share route, SAME_DEVICE and the referral device lifetime cap are untouched (P8, P11, P12).

New symbols (all in `app/api/auth_routes.py`): `legacy_fingerprint_reader_enabled() -> bool`; `_read_valid_legacy_fingerprint(request, fp)` (positional, reads only through `request.headers.get`, now pinned with the flag ON by RB8-7; reuses the already-imported `_DEVICE_FINGERPRINT_RE` with `fullmatch`; never logs; None when the mapping raises or legacy == fp; GC-3); `_inherit_device_counter_with_legacy(admin_client, fp, legacy, user_id, *, floor=0, site)`. `_read_valid_device_fingerprint` and `_inherit_device_counter` are byte-identical (P13 shas).

## Defect ids -> RED nodes -> flag -> precondition

| Defect id | What | RED nodes (tests/test_s81_s08b_legacy_fingerprint.py) | Flag | Precondition |
|---|---|---|---|---|
| S81-08b (DEFECT_LEDGER; the OTA precondition of RULINGS_S81_08 R-S08-4) | a post-OTA re-signup on an existing device inherits nothing (stored rows hold the legacy composition, the primary header carries the new hash) | R1 test_r1_flag_reader_idiom; R2 test_r2_legacy_helper_truth_table; R3 test_r3_register_dual_read_legacy_max; R4 test_r4_register_stores_new_when_new_holds_max; R5 test_r5_social_dual_read_with_floor[own1-device4], [own6-floor]; R6 test_r6_register_info_line_constants_only; R7 test_r7_social_info_line; R8 test_r8_top_new_and_top_none[new-max], [no-rows]; R9 test_r9_dual_failure_is_silent_and_typed[register], [social]; R10 test_r10_one_legacy_reader_in_app; R11 test_r11_claude_md_row (14 nodes; re-measured at a8f01379 with the file copied into the base scratch worktree: 14 failed, every one an AssertionError, 71 passed) | ENABLE_LEGACY_FINGERPRINT_READER | deployed + the owner's DATED ledger line `ENABLE_LEGACY_FINGERPRINT_READER=true on web (deployment <sha>)` before the first OTA (never the merge) |
| S81-08d (opened by R-S08B-1, not this unit) | SAME_DEVICE is dead at base (`_load_invitee` selects no device hash) | pinned untouched: P11 test_p11_same_device_untouched (M19) | (its own flag, later) | after S81-09 |
| auth_service B4-BE-DIAG (GC-4 DEFECT_LEDGER note row, OUT OF SCOPE here) | the two tests/test_auth_interceptor.py nodes stay the tests/.pre_impl_failures.txt baseline (the unconditional B4-BE-DIAG branch at auth_service.py:310-318) | none (identical base and head) | none | not scheduled |

PIN rows of the RED file (71 nodes, green at a8f01379 and at HEAD): P1 x7, P2 x6, P3 x6, P4 x16, P5 x4, P6 x2, P7 x6 + 3, P8 x6, P9 x4, P10 x2, P11 x2, P12 x2, P13 x2, P14 x2, plus test_r6pre_base_paths_log_no_user_id. PR note (correctness adversary, prove-nothing list): P9, P11 and P12 are SCOPE pins: they guard sibling files (`sentry_service` redaction, `referral_service._load_invitee`, the device lifetime cap function), not auth_routes, so no auth_routes mutant can be expected to turn them red.

## Where each adversary minor landed (RB8-2..RB8-9)

| Minor | Finding | Landing place |
|---|---|---|
| corr m1 | P1-P7 pin call lists and no tagged record, not the full app.* record list on the drop paths (N3, N3b, N3c survived) | RB8-2 rows (+ the CLAUDE.md identity sentence, RB8-8b) |
| corr m2 | the failure table pinned only for RuntimeError on the dual read (N1, N2 survived) | RB8-3 rows (+ RB8-8b) |
| corr m3 | the canary text read as delete-then-re-register is a false negative (043 NULLs the hash) | RB8-8c, the row and the owner steps below |
| corr m4 | the stakes sentence missed the `/usage/status` remaining figures | RB8-8d |
| corr m5 | NULL sorts first under DESC (GREEN Q2) | RB8-8e, stated limit (11): a note for S81-09, not a code change |
| corr m6 | the GREEN's 6,558-char slice figure was a CRLF count (R11 saw 6,551) | RB8-8f: stated here in universal newlines (see below) |
| corr m7 | the "RED file, flag ON exported" run proves nothing (the autouse `_unit_flag_unset`) | RB8-10(1): reported as a convenience run, not a gate |
| eng m1 | three from-package importers of text_routes missed by the comm builder | RB8-9: added, and the re-derivation made import-aware |
| eng m2 | R11 passes with the OTA precondition inverted (E12 survived) | RB8-4 row |
| eng m3 | the row placement (E15) and the Auth bullet (E14) unpinned | RB8-5 rows |
| eng m4 | a second primary read spelled lower case passes the exact-literal count (E3b survived) | RB8-6 row |
| eng m5 | the accessor (GC-3) unpinned with the flag ON (E9 survived) | RB8-7 row |
| eng m6 | stated limit (10) goes stale at the rebase | RB8-8a |
| eng m7 | autocrlf rewrites the frozen RED file CRLF on checkout | the RED file is verified by its BLOB (`git show HEAD:tests/test_s81_s08b_legacy_fingerprint.py \| sha256sum` = 2f4f8237...), never by the CRLF working copy (9436574d... after the rebase checkout, as the adversary predicted) |

## Change list (`git diff --stat origin/main...HEAD`: exactly these four files, no whole-file diff)

| File | Change | sha256 |
|---|---|---|
| app/api/auth_routes.py | the GREEN change (spec 1a-1e): `legacy_fingerprint_reader_enabled`, `_read_valid_legacy_fingerprint`, `_inherit_device_counter_with_legacy`, the social apply and register branches; +120 / -7, CRLF kept, added lines ASCII. Untouched by main since 86d5a24d: `git diff 63f159ef HEAD -- app/api/auth_routes.py` is EMPTY, so the GREEN's 20/20 mutation table and both adversary tables stand on these bytes | working copy f49c4b95...082 (CRLF), blob 0b060385...7e3 |
| CLAUDE.md | the GREEN row `**SESSION 81 flag (S81-08b LEGACY-FINGERPRINT-READER, ...)**` (now after the S81-06 row, before `## Tests`), the Feature Flags pointer sentence and the Auth + security hardening bullet, plus the RB8-8 in-place sentences (a)-(e); 11 lines changed vs main (+9 / -2), CRLF kept, non-ASCII byte count 3,937 = main's | working copy 6006692d...4f03a6 (CRLF), blob 9c2a04d0...cada3 |
| tests/test_s81_s08b_legacy_fingerprint.py | the RED file, frozen (85 nodes) | BLOB 2f4f8237904ce960e7f8de67db4fbda38e765477d78a13b21753b508da2f6a92, unchanged |
| tests/test_s81_s08b_gate_rows.py | NEW, test-only, LF, pure ASCII (15,938 B, 29 nodes): the RB8-2..RB8-7 rows, reaching the RED file's harness by import exactly as tests/test_s81_s06_router_gate_rows.py reaches its RED file | 65f0 4597 9762 50ef 0ba4 0a17 2438 f980 db9e b490 a4aa 4c54 1c9c 4454 753a bfe1 (grouped by four so no digit run is long; blob = working copy) |

No other file: no migration, no client file, no requirements / package / `.env` / `tests/.pre_impl_failures.txt` edit.

## Rebase (RB8-1)

`git rebase origin/main` replayed ONE commit (63f159ef -> b8d611e4) with ONE conflicted file, CLAUDE.md, at the two sites `git merge-tree` predicted, both the "both sides added at the same anchor" class, resolved by UNION in session order (S81-06 on main first, then this unit), nothing dropped or reworded:
- the `**Feature Flags:**` pointer paragraph (:341): main's line kept as it reads at a8f01379 (S81-06's seven flag names and knobs) with this unit's `ENABLE_LEGACY_FINGERPRINT_READER` sentence inserted right after S81-06's sentence (both sides were pure insertions at the same base offset; verified by script);
- the row anchor after the S81-14 block: the S81-06 row (head :507) first, a blank line, then this unit's row (head :510), then `## Tests`.
The :231 Auth bullet had no counterpart on main (auto-merged). After the continue: `git diff --check` clean, no conflict marker in CLAUDE.md, app/ or tests/.

## The rebase-round pin rows (tests/test_s81_s08b_gate_rows.py) and their mutants

| Row | What it pins | Nodes |
|---|---|---|
| RB8-2 test_rb8_2_drop_path_log_identity | at register and at the social apply, through the RED FakeDB and the `full` configuration, five scenarios (flag unset + no legacy / + a valid distinct legacy; flag ON + no legacy / + a 63-char legacy / + a legacy equal to the primary): (b) no record of any logger carries the primary or the legacy value in getMessage(), msg, repr(args) or exc_text; (a) the ordered (logger, levelno, getMessage()) list of every app.* record equals ONE literal per site, RECORDED at a8f01379 in the detached base scratch worktree (this file and the RED file copied in untracked for that run, then removed) and confirmed equal at HEAD: the empty list at both sites (uuid / duration normalisation regexes stated in the docstring) | 10 |
| RB8-2 test_rb8_2_capture_liveness | the vacuity guard for the empty literal: an upper-case primary logs exactly the base rejection INFO line at both sites (recorded at a8f01379 with the rows above) | 2 |
| RB8-3 test_rb8_3_failure_table | site {register, social} x op {in_, update} x {RuntimeError, postgrest APIError, httpx.ConnectError}: 200 with the no-failure body; the app.* list is exactly one WARNING `[LEGACY-FP] site=<site> inherit failed: <Type>` from app.api.auth_routes; a read failure writes nothing; an update failure is not followed by a second write; the exception text (which carries both values) reaches no record. A FakeDB subclass adds `update` and typed exceptions to the raise vocabulary | 12 |
| RB8-4 test_rb8_4_ota_precondition_wording | the R11-bounded row slice holds `The OTA precondition is the DATED ledger line of this flip ON` and `never the merge`, and none of the merge-as-precondition wordings | 1 |
| RB8-5 test_rb8_5a_row_placement | the S81-14 head < the S81-06 head < the S81-08b head (each once, column 0), and the first `## ` after the S81-08b head is `## Tests` | 1 |
| RB8-5 test_rb8_5b_auth_bullet | exactly one line starts ``- **`X-Device-Fingerprint`** must match`` and it names `X-Device-Fingerprint-Legacy`, S81-08b and "silently dropped when invalid or equal" | 1 |
| RB8-6 test_rb8_6_widened_header_names | case-insensitive: one `request.headers.get(` of the quoted primary name, one of the legacy name, no `headers[...]` subscript of either (the frozen P14 / S81-05 p07 exact counts unchanged) | 1 |
| RB8-7 test_rb8_7_legacy_accessor_get_only | `_read_valid_legacy_fingerprint` with the flag ON over a recording `collections.abc.Mapping` whose `get` returns without `__getitem__`: the only recorded access is `get("X-Device-Fingerprint-Legacy")`, once, and the legacy string is returned | 1 |

Mutants (each on a sha-verified byte copy under `.qa-mutation.lock`, the whole rows file run, restored and sha-compared; every kill an AssertionError, no other exception type; the run repeated on the final rows bytes, round 2 below):

| Mutant | Target | Named row (nodes red) | Also red | [pyt] (round 2) |
|---|---|---|---|---|
| N1 dual `except Exception` -> `except RuntimeError` | auth_routes.py | RB8-3 (8: the APIError and ConnectError cases) | - | `[pyt] tag=s08b-rb-mut-N1 start=2026-10-29 02:50:48 end=2026-10-29 02:51:04 elapsed=15s bound=600s status=FAIL rc=1` |
| N2 the dual update executed outside the try | auth_routes.py | RB8-3 (6: every op=update case) | - | `[pyt] tag=s08b-rb-mut-N2 start=2026-10-29 02:51:04 end=2026-10-29 02:51:17 elapsed=13s bound=600s status=FAIL rc=1` |
| N3 an untagged register INFO line whenever legacy is None | auth_routes.py | RB8-2 (5 register scenarios, by (a)) | - | `[pyt] tag=s08b-rb-mut-N3 start=2026-10-29 02:51:17 end=2026-10-29 02:51:24 elapsed=7s bound=600s status=FAIL rc=1` |
| N3b register logs the raw legacy value on the drop path | auth_routes.py | RB8-2 (5 register: (b) in the three legacy-valued scenarios, (a) in the two without) | RB8-6 | `[pyt] tag=s08b-rb-mut-N3b start=2026-10-29 02:51:25 end=2026-10-29 02:51:31 elapsed=6s bound=600s status=FAIL rc=1` |
| N3c the social apply logs the raw legacy value on the drop path | auth_routes.py | RB8-2 (5 social, (b) / (a) as N3b) | RB8-6 | `[pyt] tag=s08b-rb-mut-N3c start=2026-10-29 02:51:31 end=2026-10-29 02:51:46 elapsed=15s bound=600s status=FAIL rc=1` |
| E3b a second primary read spelled lower case | auth_routes.py | RB8-6 | RB8-7 | `[pyt] tag=s08b-rb-mut-E3b start=2026-10-29 02:51:48 end=2026-10-29 02:52:10 elapsed=21s bound=600s status=FAIL rc=1` |
| E9 the legacy read through `__contains__` + `__getitem__` | auth_routes.py | RB8-7 | RB8-6 | `[pyt] tag=s08b-rb-mut-E9 start=2026-10-29 02:52:11 end=2026-10-29 02:52:48 elapsed=37s bound=600s status=FAIL rc=1` |
| E12 "The OTA precondition is the merge of this unit." | CLAUDE.md | RB8-4 | - | `[pyt] tag=s08b-rb-mut-E12 start=2026-10-29 02:52:49 end=2026-10-29 02:53:17 elapsed=28s bound=600s status=FAIL rc=1` |
| E14 the Auth bullet sentence removed | CLAUDE.md | RB8-5b | - | `[pyt] tag=s08b-rb-mut-E14 start=2026-10-29 02:53:18 end=2026-10-29 02:53:43 elapsed=25s bound=600s status=FAIL rc=1` |
| E15 the row moved before the S81-14 block | CLAUDE.md | RB8-5a | - | `[pyt] tag=s08b-rb-mut-E15 start=2026-10-29 02:53:44 end=2026-10-29 02:54:02 elapsed=18s bound=600s status=FAIL rc=1` |

10 / 10 KILLED by the named row; every restore sha256-matched; the lock removed; the three files byte-identical to the pre-mutation shas afterwards. (Round 1 on the earlier rows bytes, before (b) was moved ahead of (a) in RB8-2: the same 10 / 10.)

## Gates at HEAD 9088563f (bounded runner pyt.py, the shared .venv-qaren, one pytest at a time)

- Lint: `python -m ruff check --select E9,F63,F7,F82 --no-cache` (ruff 0.16.5) on app/api/auth_routes.py, the RED file and the gate-rows file: All checks passed!; `python -m py_compile` on the same three: rc 0. The pre-commit hook ran on the pin commit (ruff tier "All checks passed!", no --no-verify). Byte hygiene: 0 bytes > 127 in either test file; auth_routes.py 175 = main's 175 (added lines ASCII); CLAUDE.md 3,937 = main's 3,937. Added-line sweep over `git diff origin/main...HEAD` (the common-brief personal-data shapes: mail-domain and country-code phone patterns, 8+ digit runs; and the key / token / JWT / PEM / credentialed-URL shapes): 0 hits.
- RED file, flag unset (the gate): 85 passed; sentinel 85; netguard 0 / 0 -- `[pyt] tag=s08b-rb-g1-red-off start=2026-10-29 03:15:20 end=2026-10-29 03:15:38 elapsed=18s bound=600s status=OK rc=0`. The same file with the flag exported is a CONVENIENCE run, not a gate (the RED's autouse `_unit_flag_unset` deletes the flag before every row; the flag-ON evidence is the rows that set the flag themselves, R3-R9 / P2 / P5-P7, and the flag-ON pin sweep below): 85 passed -- `[pyt] tag=s08b-rb-g1-red-on start=2026-10-29 03:15:39 end=2026-10-29 03:15:55 elapsed=16s bound=600s status=OK rc=0`.
- Gate-rows file, flag unset: 29 passed -- `[pyt] tag=s08b-rb-g1-rows-off start=2026-10-29 03:15:56 end=2026-10-29 03:16:11 elapsed=15s bound=600s status=OK rc=0`; with the flag exported (its rows set their own state): 29 passed -- `[pyt] tag=s08b-rb-g1-rows-on start=2026-10-29 03:16:13 end=2026-10-29 03:16:29 elapsed=16s bound=600s status=OK rc=0`.
- Pin sets A (8) + B (13) + tests/test_s81_kb_schema.py, compared with the same 22 files at a8f01379 in the base scratch worktree (S81-06 touched test_s81_kb_schema.py; equal both sides is the gate): base flag unset 1789 passed, 1 skipped -- `[pyt] tag=s08b-rb-pins-base-off start=2026-10-29 03:11:06 end=2026-10-29 03:12:08 elapsed=62s bound=1200s status=OK rc=0`; base flag exported 1789 passed, 1 skipped -- `[pyt] tag=s08b-rb-pins-base-on start=2026-10-29 03:12:09 end=2026-10-29 03:13:10 elapsed=61s bound=1200s status=OK rc=0`; HEAD flag unset 1789 passed, 1 skipped -- `[pyt] tag=s08b-rb-g3-pins-head-off start=2026-10-29 03:17:46 end=2026-10-29 03:18:56 elapsed=70s bound=1200s status=OK rc=0`; HEAD flag exported (the GREEN's G5 sweep) 1789 passed, 1 skipped -- `[pyt] tag=s08b-rb-g3-pins-head-on start=2026-10-29 03:18:57 end=2026-10-29 03:20:40 elapsed=104s bound=1200s status=OK rc=0`. Sentinel 1789 and netguard 48 from 14 on all four.
- CI-order set: the GREEN's 22 files + tests/test_s81_s08b_gate_rows.py = 23, sorted, flag unset: 1374 passed, 1 skipped (= the GREEN's 1345 + 29); sentinel 1374; netguard 48 from 14 -- `[pyt] tag=s08b-rb-g4-ci-order start=2026-10-29 03:20:42 end=2026-10-29 03:21:41 elapsed=60s bound=1200s status=OK rc=0`.
- The SR8 pair alone (tests/test_sentry_channels_u8d_unit.py + tests/test_sentry_channels_u8d.py): 273 passed, test_u8d_pin_integration_list_unchanged GREEN in the shared venv at this HEAD (the post-#374 record) -- `[pyt] tag=s08b-rb-g6-sr8-pair start=2026-10-29 03:16:59 end=2026-10-29 03:17:20 elapsed=21s bound=600s status=OK rc=0`.
- tests/test_paid_route_metering.py flag unset: 21 passed -- `[pyt] tag=s08b-rb-g6-metering-off start=2026-10-29 03:17:21 end=2026-10-29 03:17:26 elapsed=5s bound=600s status=OK rc=0`; flag exported: 21 passed -- `[pyt] tag=s08b-rb-g6-metering-on start=2026-10-29 03:17:26 end=2026-10-29 03:17:31 elapsed=4s bound=600s status=OK rc=0`.
- The two CLAUDE.md readers (tests/test_ci_gates.py + tests/test_behavior_dimension_translation.py): 79 passed -- `[pyt] tag=s08b-rb-g7-claude-readers start=2026-10-29 03:16:30 end=2026-10-29 03:16:46 elapsed=16s bound=600s status=OK rc=0`. R11 is green with the RB8-8 sentences in place: the R11-bounded row slice is 7,739 characters read with universal newlines (7,745 with CRLF), under the 8,000 cap. (The GREEN's "6,558 chars" was the CRLF count of the pre-RB8-8 row; R11 read it as 6,551.)
- The four tests/test_precommit_hook*.py files were NOT re-run at the rebase (RB8-10(9)): the unit touches no .githooks input and no file the hook tests read, and the rebase adds test rows and CLAUDE.md sentences only. The engineering adversary measured all four green at 63f159ef within the ceiling: `[pyt] tag=s08b-adve-hook-notdash` 875 s OK and `[pyt] tag=s08b-adve-hook-dash` 1215 s OK (specs/S81_08B_ADV1_engineering.md). CI is the arbiter.

## Comm set (zero-regression gate; RB8-9), measured

Membership, re-derived IMPORT-AWARE at HEAD (the RED's rule classes re-run on the rebased tree + `import M` / `from <pkg> import ... <leaf>` (incl. parenthesised lists) / `from M import` for app.api.auth_routes and every app importer of it (feedback, history, home, image, profile, referral, share, text, url, usage routes) and app.main + docstring readers; MINUS the four hook files): every one of the RED's 241 re-derived, the three from-package importers the RED's class missed re-derived (`tests/test_m13_35_sse_disconnect_finally.py`, `tests/test_m18_preverdict_disconnect_refund.py`, `tests/test_openai_breaker.py`), and TWO files added beyond them, both on main through #374 and run on both sides: `tests/test_s81_s06_anthropic_router.py` and `tests/test_s81_s06_router_gate_rows.py`. The record therefore covers **247 files at base** (the RED's 241 in its own chunks 00-09 + chunk 10 = the three + the two + the RED file, which is not on main and was copied into the base scratch worktree untracked for its own run) and **248 at HEAD** (+ tests/test_s81_s08b_gate_rows.py, run with the RED file as the HEAD-only chunk).

FRESH base record at the rebase main a8f01379 in a DETACHED scratch worktree under the notes folder (no node_modules, no junction; removed afterwards with `git worktree remove --force` and verified absent from `git worktree list`); bound 1200 per chunk, one chunk at a time, the repo's NETWORK_FLAKY_EXCLUDE deselected as in the RED's record, the flag unset:

| chunk | files | base a8f01379 | HEAD 9088563f |
|---|---|---|---|
| 00 | 25 | 2 failed, 793 passed `[pyt] tag=s08b-rb-comm-base-00 ... elapsed=42s status=FAIL rc=1` | 2 failed, 793 passed `[pyt] tag=s08b-rb-comm-head-00 ... elapsed=35s status=FAIL rc=1` |
| 01 | 25 | 1231 passed, 1 skipped, 8 deselected `... base-01 elapsed=55s status=OK rc=0` | same `... head-01 elapsed=113s status=OK rc=0` |
| 02 | 25 | 1366 passed, 10 deselected `... base-02 elapsed=33s status=OK rc=0` | same `... head-02 elapsed=52s status=OK rc=0` |
| 03 | 25 | 1230 passed `... base-03 elapsed=162s status=OK rc=0` | same `... head-03 elapsed=207s status=OK rc=0` |
| 04 | 25 | 550 passed, 8 deselected `... base-04 elapsed=26s status=OK rc=0` | same `... head-04 elapsed=20s status=OK rc=0` |
| 05 | 25 | 493 passed, 24 skipped, 3 deselected, 1 xfailed, 2 errors `... base-05 elapsed=32s status=FAIL rc=1` | same `... head-05 elapsed=31s status=FAIL rc=1` |
| 06 | 25 | 1096 passed `... base-06 elapsed=165s status=OK rc=0` | same `... head-06 elapsed=184s status=OK rc=0` |
| 07 | 25 | 3855 passed (the SR8 node GREEN) `... base-07 elapsed=147s status=OK rc=0` | same `... head-07 elapsed=218s status=OK rc=0` |
| 08 | 25 | 539 passed, 1 skipped, 11 deselected `... base-08 elapsed=65s status=OK rc=0` | same `... head-08 elapsed=87s status=OK rc=0` |
| 09 | 16 | 932 passed, 9 skipped, 35 xfailed `... base-09 elapsed=26s status=OK rc=0` | same `... head-09 elapsed=30s status=OK rc=0` |
| 10 | 5 | 452 passed `... base-10 elapsed=60s status=OK rc=0` | same `... head-10 elapsed=26s status=OK rc=0` |
| RED (base, copied in) / HEADONLY (RED + rows) | 1 / 2 | 14 failed (the 14 RED rows, AssertionError only), 71 passed `... base-RED elapsed=12s status=FAIL rc=1` | 114 passed `... head-HEADONLY elapsed=7s status=OK rc=0` |

(Every elided `[pyt]` line reads `[pyt] tag=s08b-rb-comm-<side>-<chunk> start=2026-10-29 ... bound=1200s ...`; the full lines are in the rebase report.) [hermeticity] counts are equal per chunk on both sides; [netguard] blocked counts are equal except chunks 02 and 03, where base logged one more blocked `api.openai.com` resolve each (tests/test_flush_live_price_key.py, tests/test_genuine_price_priority.py; timing-dependent egress attempts, blocked, results identical) and the hermeticity-pin lines differ only by ephemeral port.

Totals: base 12,608 passed, 16 failed, 2 errors, 35 skipped, 40 deselected, 36 xfailed (over the 246 tracked files: 12,537 passed, 2 failed, 2 errors; the RED file: 71 passed, 14 failed); HEAD 12,651 passed (= 12,537 + 85 + 29), 2 failed, 2 errors, 35 skipped, 40 deselected, 36 xfailed.

Base failure set (the tracked files) = exactly the expected four: the pre_impl auth pair `tests/test_auth_interceptor.py::test_sign_in_with_social_exception` and `::test_social_login_user_insert_fails_gracefully` (the GC-4 B4-BE-DIAG baseline) and the cold-tiktoken pair `tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence` and `::test_truth_on_prefix_static_and_cacheable` (the two chunk-05 ERRORs). `tests/test_sentry_channels_u8d.py::TestU8dPins::test_u8d_pin_integration_list_unchanged` is GREEN on both sides at a8f01379 (RB6-14 closed by #374).

**branch-only-new (`comm -13` of the sorted FAILED/ERROR node-id sets) = EMPTY.** `comm -23` (fixed at HEAD) = the 14 RED rows; `comm -12` = the four nodes above.

Supplementary HEAD-only chunk (the GREEN's 20 files that reference `get_admin_supabase_client` only in other modules' namespaces; disjoint from the 248; no base record needed): 303 passed, 5 deselected -- `[pyt] tag=s08b-rb-comm-head-SUPP start=2026-10-29 03:40:06 end=2026-10-29 03:40:46 elapsed=40s bound=1200s status=OK rc=0`.

## Deliberate pin changes (spec 4.1)

NONE (E-none). Every existing pin the spec names in 4.2 stays green and unedited (test_social_login_device_fingerprint.py, test_auth_routes_invite_fingerprint.py, test_usage_device_inheritance.py, test_s81_s05_request_context.py r08 / p01 / p02 / p05-p08, the abuse-detection and referral files, test_s71_u13_compare_auth_required.py T23, test_s75_fanout_identity.py FY25 + test_s81_kb_schema.py IDENTITY_NODES, test_ci_gates.py, test_behavior_dimension_translation.py, test_s81_s04_spend_breaker.py r38, test_sentry_channels_u8d_unit.py R10, test_consent_capture_w3_16.py, test_s79_b3b_apple_revoke.py, test_security_regression.py): all inside the pin sets and the comm set above. The frozen RED file is unedited (BLOB 2f4f8237...); the rebase-round rows live in the new tests/test_s81_s08b_gate_rows.py.

## Stated limits (the CLAUDE.md row, as amended in place by RB8-8)

1. Two request-time sites only: register and the W3-3 social apply; with `ENABLE_SOCIAL_DEVICE_FINGERPRINT` OFF (production state UNKNOWN: no dated ledger line names it) the social half is inert.
2. SAME_DEVICE (`abuse_detection_service.evaluate_invite`) is dead at base (`referral_service._load_invitee` selects no device hash) and stays untouched, stored-vs-stored and out of any header's reach (its revival is the flagged defect row S81-08d).
3. The referral device lifetime cap compares stored values, so legacy-hash and new-hash accounts on one device are two buckets across the transition: at most one extra cap of 3 lifetime invites per device (accepted, R-S08B-1; S81-09 revisits device identity).
4. After the cutoff a device that never registered inside the window loses its link to its legacy-hash rows.
5. The legacy value is today's composition with the CURRENT osBuildId, so a row stored under an earlier OS build, app id or nonce matches neither header, as at base: the reader restores today's match rate, no more.
6. The header is a client claim: the reader can only raise the inherited counter and never changes what is stored (a client can still escape inheritance with a random primary value, as today).
7. The register except arm keeps its pre-existing `str(exc)` WARNING (flag-independent); the dual function never raises into it (now pinned by RB8-3 for three exception types on the dual read and the dual update at both sites).
8. The anon gate keys (`anon:<fp>`) are untouched (build 3 sends no device header on the anonymous routes, and anonymous compares are 401 under `ENABLE_COMPARE_AUTH_REQUIRED`), and CORS `allow_headers` does not list the legacy header (native clients do not preflight; an Expo web build would, like S81-05 limit 5).
9. That the 023 partial index `idx_users_device_fingerprint_active` serves the `IN` read is reasoned from its predicate, not measured on a database.
10. The comm-set base record was re-measured at the rebase main `a8f01379` (247 files; the RED's 241 at `86d5a24d` was the GREEN's base).
11. `users.lifetime_comparisons_used` is nullable (011, INT DEFAULT 0) and PostgreSQL sorts NULL first under `DESC` (postgrest 2.31.0 renders no `nullslast`), so a NULL-counter row would be returned first and read as 0: the base read has the same property within the primary group and the dual read widens it across both; practically unreachable (default 0, 043 writes 0, the 011 RPC COALESCEs); the RED FakeDB sorts NULL as 0; GC-2 binds `desc=True`, so this is a note for S81-09, not a code change.

Stakes (the row's effect paragraph, corrected by RB8-8d): the per-user daily and monthly free counters are unaffected; the inherited lifetime counter gates only the lifetime-free branch and the `/usage/status` figures (the lifetime figure, and `remaining.daily` / `remaining.monthly`, which `_usage_status_body` reports as the full allowance while on the lifetime-free branch). The `top=` label is not deterministic on a counter tie (a log label only).

PR-only notes:
- GREEN Q1: a returned row whose stored hash equals neither value would be labelled `none` (its counter is still taken); the `IN` filter makes that case unreachable, so the three-label contract of spec 2.2 (legacy | new | none) stands; no fourth label.
- P9, P11 and P12 of the RED file are scope pins over sibling files (the Sentry redaction, `referral_service._load_invitee`, the device lifetime cap function), not over auth_routes (the correctness adversary's prove-nothing list).
- Measured not pinned: nothing the rulings name; the four hook test files are the RB8-10(9) carry-over stated above.

## Owner steps (names only; a dated ledger line per step)

- Right after this unit deploys, as its OWN step in the PLAN_S81 flip order BEFORE the first OTA: set `ENABLE_LEGACY_FINGERPRINT_READER=true` on `web` and record the dated ledger line `ENABLE_LEGACY_FINGERPRINT_READER=true on web (deployment <sha>)`. The OTA precondition is the DATED ledger line of this flip ON, never the merge: an OTA gated only on the merge ships the reader dark, and every post-OTA re-signup then inherits nothing with no error and no log line. The flip may precede Apple approval (ON without the legacy header is byte-identical for build 3) and is independent of, and earlier than, `ENABLE_REQUEST_CONTEXT_HEADERS` (which flips after the OTA in its own window).
- Canary after the OTA: keep the pre-OTA email-registered test account (NOT deleted: migration 043's `delete_user_cascade` NULLs `users.device_fingerprint_hash` and zeroes `lifetime_comparisons_used`, so a delete-then-re-register canary reads `top=none` and inherits nothing at base and at HEAD, a false negative) and register a SECOND account on that device with no OS update since the first registration: it logs `[LEGACY-FP] site=register top=legacy` and inherits the first account's lifetime counter.
- Rollback: unset the variable (read per call, immediate). Nothing else: no migration, no credential, no pepper.

## Out of scope / for the orchestrator

- The DEFECT_LEDGER note row "auth_service B4-BE-DIAG" (GC-4: the unconditional diagnostic branch behind the two tests/test_auth_interceptor.py baseline nodes) is OUT OF SCOPE for this unit; not scheduled.
- Orchestrator steps (RB8-12, after the merge): the dated ledger line with the merge sha; the s81-common.txt moving-main list; DEFECT_LEDGER (S81-08b MERGED; the S81-09 note: NULL-first under DESC and device identity); OWNER_ACTIONS item 32 stays open until the owner's dated flip line; PLAN_S81 gains the S81-08b ON step before the first OTA; the unit worktree removed (it holds no node_modules junction).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
