# S81-08b LEGACY-FINGERPRINT-READER: RED report

- Unit: S81-08b (lane B backend, additive, FLAGGED: ENABLE_LEGACY_FINGERPRINT_READER, new name, default OFF, read per call as the first statement of the gated predicate).
- Agent: RED, Opus 5.5 (claude-opus-5-5). Window: 2026-10-28 23:10 - 23:52 AST.
- Base: 86d5a24d17f5782e733dee82d52f38dcbf3606ff = origin/main (worktree HEAD verified before and after). Real worktree: C:/Users/SynAckITPC/Documents/AI/sc-s81-s08b.
- Authorities (precedence): RULINGS_S81_08B.md (R-S08B-1..11 + Measurement rulings) > review corrections (S81-08b_SPEC_REVIEW.md sha 658ce617...) > spec (S81-08b_UNIT_SPEC.md sha 920fb599..., re-hashed: match).
- This report was written through the shell (bash quoted heredoc), not the Write tool; the comm list + reasons TSV are in <scratchpad>/S81-08b_red/ (comm_files.txt, comm_reasons.tsv).
- Notes folder: C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-08b_red/ (notes.md, every log, pyt_lines.txt, mutants.json, prototype.diff, make_prototype.py, mutate.py, build_comm.py, run_chunk.py, comm_totals.py, restore_check.py, restore_manifest_sha256.txt).

## Files written

| file | bytes | sha256 | bytes>127 | CR | backslash |
|---|---|---|---|---|---|
| tests/test_s81_s08b_legacy_fingerprint.py (the ONLY file added to the real worktree) | 45921 | 2f4f8237904ce960e7f8de67db4fbda38e765477d78a13b21753b508da2f6a92 | 0 | 0 | 0 |

py_compile OK; ruff check --select E9,F63,F7,F82 --no-cache: All checks passed. Max digit run in the file: 4 (the P13 shas are written in groups of four, joined at run time; every id is uuid.UUID(int=...) and every fingerprint sha256 of a synthetic byte string, built at run time).
File name: the spec section 3 item 3 and section 5 name tests/test_s81_s08b_legacy_fingerprint.py, which overrides the task default name test_s81_s08b_legacy_fingerprint_reader.py.

## Re-anchor at 86d5a24d

git diff ea3aef15..86d5a24d touches only .sqlfluff, CLAUDE.md, app/services/kb_service.py (new), migrations 045/047 (+ rollbacks) and tests/test_s81_kb_schema.py (new). app/api/auth_routes.py, app/api/referral_routes.py, app/services/referral_service.py, app/services/abuse_detection_service.py, app/services/sentry_service.py and app/utils/request_context.py are byte-identical, so every app cite of the spec holds at 86d5a24d (auth_routes: social_device_fingerprint_enabled :395-417, _read_valid_device_fingerprint :478-496, _inherit_device_counter :499-537, _apply_social_device_fingerprint :540-579, register def :584, fp read :624, social_login :1158-1184; referral_service _load_invitee :758-770, _referrer_device_lifetime_count :772-812). CLAUDE.md at 86d5a24d: Feature Flags paragraph :341, S81-04 row :494, S81-14 row :497, ## Tests :507.

## Gate 1: pin sets A and B at base (each in one runner call)

- Set A (8 files): 599 passed, 63 warnings in 19.69s; [hermeticity] sentinel checked 599 test(s); [netguard] blocked 14 attempt(s) from 8 node(s)
  [pyt] tag=s08b-red-base-A start=2026-10-28 23:14:33 end=2026-10-28 23:14:54 elapsed=21s bound=1200s status=OK rc=0
- Set B (13 files): 661 passed, 1 skipped, 13 warnings in 25.66s; [hermeticity] sentinel checked 661 test(s); [netguard] blocked 34 attempt(s) from 6 node(s)
  [pyt] tag=s08b-red-base-B start=2026-10-28 23:15:02 end=2026-10-28 23:15:30 elapsed=27s bound=1200s status=OK rc=0
Both equal the spec 1.10 counts (599 / 661 + 1 skipped).

## RED file at base (85 nodes)

[pyt] tag=s08b-red-unit-base start=2026-10-28 23:25:40 end=2026-10-28 23:25:49 elapsed=8s bound=600s status=FAIL rc=1
14 failed, 71 passed, 11 warnings in 7.00s; [hermeticity] sentinel checked 85 test(s); [netguard] blocked 0 attempt(s) from 0 node(s).
Every failure is an AssertionError (log: 14 lines "E AssertionError", no other exception type; red_unit_base.log).

| row | node(s) | at base | base failure message |
|---|---|---|---|
| R1 | test_r1_flag_reader_idiom | FAIL | R1: auth_routes.legacy_fingerprint_reader_enabled is missing |
| R2 | test_r2_legacy_helper_truth_table | FAIL | R2: auth_routes._read_valid_legacy_fingerprint is missing |
| R3 | test_r3_register_dual_read_legacy_max | FAIL | call list carries .eq(NEW), not in_ (writes 1) |
| R4 | test_r4_register_stores_new_when_new_holds_max | FAIL | call list (base never sends in_) |
| R5 | test_r5_social_dual_read_with_floor[own1-device4], [own6-floor] | FAIL x2 | call list .eq(NEW) (own1 also writes 1) |
| R6 | test_r6_register_info_line_constants_only | FAIL | no [LEGACY-FP] record |
| R7 | test_r7_social_info_line | FAIL | no [LEGACY-FP] record |
| R8 | test_r8_top_new_and_top_none[new-max], [no-rows] | FAIL x2 | no [LEGACY-FP] record |
| R9 | test_r9_dual_failure_is_silent_and_typed[register], [social] | FAIL x2 | no typed WARNING (base never calls in_) |
| R10 | test_r10_one_legacy_reader_in_app | FAIL | 0 app files read the legacy header |
| R11 | test_r11_claude_md_row | FAIL | no column-0 SESSION 81 flag (S81-08b paragraph |

PIN rows, all GREEN at base (71 nodes): P1 x7 (unset, empty, false, 0, off, no, garbage), P2 x6 (true, TRUE, padded true, 1, yes, on), P3 x6 (upper, len63, len65, empty, non-hex, equal-new), P4 x16 (register and social x primary absent / upper / len63 / empty x flag false / true), P5 x4 (off-own-null, off-own-legacy, on-own-legacy, on-own-new), P6 x2 (W3-3 unset / false), P7 x6 (ON spellings) + 3 (social upper / len63 / equal-new legacy), P8 x6 (body-new / body-absent / body-upper x flag false / true), P9 x4, P10 x2, P11 x2, P12 x2, P13 x2, P14 x2 (leaf import shape; names rule), plus test_r6pre_base_paths_log_no_user_id x1.

Seeds and literals (R-S08B-8, review C7): REG_BASE, SOCIAL_BASE_NULL and SOCIAL_BASE_OWNED are literal lists in the file, RECORDED AT BASE 86d5a24d with the file own EVALUATING FakeDB (eq / in_ / not_.is_ / order desc / limit / single over seeded rows, every builder call recorded as [method, args(, kwargs)]) and tie-free seeds: REG seed LEG:3, NEW:1, OTHER:9 -> base writes 1; SOCIAL seed own NULL lcu 1, NEW:2, LEG:4, OTHER:9 -> base writes 2; OWNED = the 5-call own read. P1 / P2 / P3 / P5 / P7 being green at base IS the recording. The probe_out.json values (lcu 3 / 4 for any seed) were not reused.
C12 measured first: test_r6pre_ (base register + social paths, both headers, DEBUG capture) is green at base, so no base log line carries the user id and the R6 sentinel keeps NEW, LEG and UID (applied in R3-R9).
B1: every flag-OFF / no-op PIN runs under the FULL configuration of spec 2.6 (ENABLE_SOCIAL_DEVICE_FINGERPRINT=true, ENABLE_REQUEST_CONTEXT_HEADERS=true, ENABLE_REFERRAL_SYSTEM=true, DEVICE_KEY_PEPPER synthetic set after the app.main import, ENABLE_CONSENT_REQUIRED and ENABLE_APPLE_TOKEN_REVOCATION deleted, the legacy header sent) with the FakeDB call recorder and the get_admin_supabase_client factory call count; the unit flag is deleted by an autouse fixture and set explicitly by every row.

## Prototype (scratch worktree only; satisfiability in three states)

Detached scratch worktree <scratchpad>/S81-08b_scratch at 86d5a24d; make_prototype.py applied spec change list items 1a-1e to app/api/auth_routes.py (CRLF kept, 104 diff lines, added lines 0 bytes > 127, py_compile + ruff clean; prototype sha b67ef2dfd6955edb5c1addf014a5d3c27ba63978dbc826d111ce144fa6f91743) and item 2 to CLAUDE.md (Feature Flags pointer sentence on :341 + a SESSION 81 flag (S81-08b row after the S81-14 row, before ## Tests). Diff kept as prototype.diff (ASCII, non-ASCII context escaped).
- Unit file, ambient flag unset: 85 passed, 11 warnings in 3.36s; [hermeticity] sentinel checked 85 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
  [pyt] tag=s08b-proto-unit-off start=2026-10-28 23:27:53 end=2026-10-28 23:27:57 elapsed=4s bound=600s status=OK rc=0
- Unit file, ENABLE_LEGACY_FINGERPRINT_READER=true exported for the call: 85 passed, 11 warnings in 3.34s; same sentinel / netguard lines
  [pyt] tag=s08b-proto-unit-on start=2026-10-28 23:27:57 end=2026-10-28 23:28:01 elapsed=4s bound=600s status=OK rc=0
- The three states inside the file: flag OFF (P1 x7 spellings, P5 off-*), flag ON with no legacy header (P2 x6, P7 x6: byte-identical REG_BASE / SOCIAL_BASE_NULL), flag ON with a valid legacy header (R3-R9): all green on the prototype.
- Pin sets A + B + tests/test_s81_kb_schema.py on the prototype: 1789 passed, 1 skipped, 63 warnings in 41.94s (flag unset) and in 41.49s (flag ON exported)
  [pyt] tag=s08b-proto-pinsAB-off start=2026-10-28 23:28:13 end=2026-10-28 23:28:57 elapsed=43s bound=1200s status=OK rc=0
  [pyt] tag=s08b-proto-pinsAB-on start=2026-10-28 23:28:57 end=2026-10-28 23:29:40 elapsed=43s bound=1200s status=OK rc=0

## Mutation table (20 mutants; each ONE exact-string edit matching once on a byte copy of the prototype; restored from the copy, sha256 compared; MUTATION LOCK <scratch>/.qa-mutation.lock held for the run and removed)

| # | mutant | file | named killer | KILLED by (failing test functions, all AssertionError) | [pyt] |
|---|---|---|---|---|---|
| M1 | flag reader returns True | auth_routes | P1 | P1, P5, R1, R2 (10 nodes) | s08b-mut-M1 23:31:01-23:31:06 5s FAIL rc=1 |
| M2 | flag reader without .strip().lower() | auth_routes | R1 | R1 | s08b-mut-M2 23:31:06-23:31:11 5s FAIL rc=1 |
| M3 | .fullmatch -> .match in the legacy helper | auth_routes | R2 | R2 (LEG + newline) | s08b-mut-M3 23:31:12-23:31:17 5s FAIL rc=1 |
| M4 | the raw == fp dedupe removed | auth_routes | P3 | P3, P7 (equal-new), R2 | s08b-mut-M4 23:31:17-23:31:22 5s FAIL rc=1 |
| M5 | the update stores legacy instead of fp | auth_routes | R3, R4 | R3, R4, R5, R8 | s08b-mut-M5 23:31:22-23:31:27 5s FAIL rc=1 |
| M6 | in_ list [legacy] only | auth_routes | R4 | R3, R4, R5, R8 | s08b-mut-M6 23:31:27-23:31:32 5s FAIL rc=1 |
| M7 | desc=True -> desc=False in the dual read | auth_routes | R3 | R3, R4, R5, R6, R8 | s08b-mut-M7 23:31:33-23:31:38 5s FAIL rc=1 |
| M8 | the header read before the flag read | auth_routes | R2 | R2 (OFF recorder reads), R10 (first statement) | s08b-mut-M8 23:31:38-23:31:43 5s FAIL rc=1 |
| M9 | the INFO line formats the legacy value | auth_routes | R6 | R3, R4, R5, R6, R7, R8 (sentinel) | s08b-mut-M9 23:31:43-23:31:48 5s FAIL rc=1 |
| M10 | the dual except arm re-raises (propagates to the register arm) | auth_routes | R9 | R9 | s08b-mut-M10 23:31:48-23:31:53 5s FAIL rc=1 |
| M11 | social upgrade-on-match (own == legacy -> dual write) | auth_routes | P5 | P5 (on-own-legacy) | s08b-mut-M11 23:31:53-23:31:58 5s FAIL rc=1 |
| M12 | register consults legacy when NEW is absent | auth_routes | P4 | P4 (ON register params) | s08b-mut-M12 23:31:58-23:32:03 5s FAIL rc=1 |
| M13 | register always uses the dual function (in_ [fp, None]) | auth_routes | P2 | P1, P2, P3 (19 nodes) | s08b-mut-M13 23:32:03-23:32:09 5s FAIL rc=1 |
| M14 | top from the NEW comparison only (legacy reads as new) | auth_routes | R6 / R8 | R6, R7 (R8 not: it expects top=new / top=none, which M14 keeps) | s08b-mut-M14 23:32:09-23:32:14 5s FAIL rc=1 |
| M15 | dual function skips the update when no rows | auth_routes | R8 | R8 (no-rows) | s08b-mut-M15 23:32:14-23:32:19 5s FAIL rc=1 |
| M16 | social dual call passes floor=0 | auth_routes | R5 | R5 (own6-floor) | s08b-mut-M16 23:32:19-23:32:24 5s FAIL rc=1 |
| M17 | social_login calls the apply when the legacy flag is ON whatever W3-3 says | auth_routes | P6 | P6 | s08b-mut-M17 23:32:24-23:32:29 5s FAIL rc=1 |
| M18 | share forwards the legacy header as device_fingerprint_hash when the body omits it | referral_routes | P8 | P8 (body-absent), R10 | s08b-mut-M18 23:32:29-23:32:34 5s FAIL rc=1 |
| M19 | _load_invitee selects device_fingerprint_hash | referral_service | P11 | P11 | s08b-mut-M19 23:32:34-23:32:39 5s FAIL rc=1 |
| M20 | the cap function uses .in_ over a two-value list ([fp, fp]) | referral_service | P12 | P12 (call literal) | s08b-mut-M20 23:32:39-23:32:44 5s FAIL rc=1 |

Result: 20 / 20 KILLED, 0 SURVIVED, every one by its named row (M14 by R6, the first of the spec pair R6 / R8). Every [pyt] line above is bound=600s, full lines in pyt_lines.txt; per-mutant detail (failing tests, error types, restore_sha_ok true) in mutants.json. Prototype shas after the 20 restores equal proto_shas_before_mutation.txt (auth_routes b67ef2df..., referral_routes 00f624f2..., referral_service 3e93b86e...).
M20 note: [fp, fp] keeps the sum; it is killed only by the P12 call literal (P12 is a shape pin of the untouched function, as R-S08B-1 / R-S08B-7 intend).

## Comm set: re-derived at 86d5a24d and run as the BASE RECORD (real worktree)

List: <scratchpad>/S81-08b_red/comm_files.txt (241 files), reasons <scratchpad>/S81-08b_red/comm_reasons.tsv, chunks comm_chunk_00..09.txt (25 x 9 + 16), builder build_comm.py.
Union rule (common brief): module reference grep for the edited module auth_routes (79 refs) UNION every app importer of auth_routes incl. app/main.py (app.main, feedback / history / home / image / profile / referral / share / text / url / usage routes: 182 refs) UNION referral_routes (share PIN P8) UNION the changed symbols (_read_valid_device_fingerprint, _inherit_device_counter, _apply_social_device_fingerprint, social_device_fingerprint_enabled, social_login, /auth/register, /auth/social-login) UNION the 8 named source-scanning pins + test_start_command* UNION every module-path / glob / path-segment / ast.parse / inspect.getsource / __file__ / .github / app-path reader UNION the CLAUDE.md readers (every test naming CLAUDE.md) UNION the spec 7.1(c) names + tests/test_s81_kb_schema.py (rebase) UNION the SmartCompareApp scanners UNION every test mentioning a fingerprint UNION the request_context readers; MINUS the four test_precommit_hook*.py; the new RED file is excluded from the base record (not a base file; GREEN adds it at head). NETWORK_FLAKY_EXCLUDE (scripts/regression_gate_diff.py:56): the one member file in the set (tests/test_rate_limiting_complete.py, chunk 05) had its node deselected.
Versus the spec 222-file list (<old scratchpad>/s81-08b/comm_files.txt): 0 missing, 19 added (tests/test_s81_kb_schema.py + 18 from the broader reader classes; list comm_added_vs_spec.txt).

| chunk | result | [pyt] |
|---|---|---|
| 00 | 2 failed, 793 passed | [pyt] tag=s08b-comm-base-00 start=2026-10-28 23:35:53 end=2026-10-28 23:36:22 elapsed=30s bound=1200s status=FAIL rc=1 |
| 01 | 1231 passed, 1 skipped, 8 deselected | [pyt] tag=s08b-comm-base-01 start=2026-10-28 23:36:22 end=2026-10-28 23:37:04 elapsed=42s bound=1200s status=OK rc=0 |
| 02 | 1366 passed, 10 deselected | [pyt] tag=s08b-comm-base-02 start=2026-10-28 23:37:04 end=2026-10-28 23:37:34 elapsed=30s bound=1200s status=OK rc=0 |
| 03 | 1230 passed | [pyt] tag=s08b-comm-base-03 start=2026-10-28 23:38:06 end=2026-10-28 23:39:21 elapsed=75s bound=1200s status=OK rc=0 |
| 04 | 550 passed, 8 deselected | [pyt] tag=s08b-comm-base-04 start=2026-10-28 23:39:21 end=2026-10-28 23:39:40 elapsed=19s bound=1200s status=OK rc=0 |
| 05 | 493 passed, 24 skipped, 3 deselected, 1 xfailed, 2 errors | [pyt] tag=s08b-comm-base-05 start=2026-10-28 23:39:40 end=2026-10-28 23:40:09 elapsed=29s bound=1200s status=FAIL rc=1 |
| 06 | 1096 passed | [pyt] tag=s08b-comm-base-06 start=2026-10-28 23:40:16 end=2026-10-28 23:43:01 elapsed=165s bound=1200s status=OK rc=0 |
| 07 | 1 failed, 3853 passed | [pyt] tag=s08b-comm-base-07 start=2026-10-28 23:43:01 end=2026-10-28 23:45:18 elapsed=137s bound=1200s status=FAIL rc=1 |
| 08 | 539 passed, 1 skipped, 11 deselected | [pyt] tag=s08b-comm-base-08 start=2026-10-28 23:45:25 end=2026-10-28 23:46:34 elapsed=69s bound=1200s status=OK rc=0 |
| 09 | 932 passed, 9 skipped, 35 xfailed | [pyt] tag=s08b-comm-base-09 start=2026-10-28 23:46:34 end=2026-10-28 23:46:59 elapsed=25s bound=1200s status=OK rc=0 |

Hermeticity / netguard per chunk: 00 795 / 18 from 7; 01 1232 / 26 from 11; 02 1366 / 29 from 11; 03 1230 / 35 from 30; 04 550 / 3 from 3; 05 496 / 119 from 23; 06 1096 / 0 from 0; 07 3854 / 42 from 12; 08 540 / 131 from 59; 09 976 / 8 from 8 (sentinel checked N test(s) / netguard blocked attempts from nodes).
TOTALS base: 12083 passed, 3 failed, 2 errors, 35 skipped, 40 deselected (39 marker filter + 1 NETWORK_FLAKY), 36 xfailed.
BASE FAILED/ERROR set (5; sorted file s08b_comm_base_failed_sorted.txt), every one a known base failure, none a regression:
- tests/test_auth_interceptor.py::test_sign_in_with_social_exception (tests/.pre_impl_failures.txt; the unconditional B4-BE-DIAG social_login branch, auth_service.py:310-318)
- tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully (tests/.pre_impl_failures.txt; same cause)
- tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence (ERROR, cold tiktoken)
- tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable (ERROR, cold tiktoken)
- tests/test_sentry_channels_u8d.py::TestU8dPins::test_u8d_pin_integration_list_unchanged (SR8 pin red in the shared venv since the anthropic SDK install of 2026-10-28; fixed by the S81-06 PR)
GREEN: re-derive the union at head (add the RED file), same chunking and deselect, comm -13 against this sorted set must be EMPTY.

## Deviations from the spec (rulings / review applied; nothing silently changed)

1. File name: tests/test_s81_s08b_legacy_fingerprint.py (spec 3.3 / 5), not the task default ..._reader.py.
2. Base literals (C7 / R-S08B-8): REG_BASE writes lcu 1 and SOCIAL_BASE_NULL writes 2 (this file seeds, evaluated); the probe_out.json values 3 / 4 were filter-blind and are not used.
3. P4 (C8 / R-S08B-8): NEW absent / upper / 63 chars / empty + valid legacy, both flag states, zero FakeDB calls and factory call count 0; also run on the social route (an addition: 16 nodes).
4. P8 (R-S08B-7 / C6): a body-absent case added (kwargs device_fingerprint_hash None) so M18 is killable; with the spec body-NEW case alone M18 is equivalent.
5. R11 (R-S08B-9): slice bounded at the first of NL + "**SESSION" and NL + "## ", row cap 8000 chars. R-S08B-2 / R-S08B-10 added tokens: OTA, ENABLE_REQUEST_CONTEXT_HEADERS (case-sensitive), ledger, independent, reasoned (case-insensitive) and the forbidden phrase "after S81-08 merges". The spec words register / social / rollback are matched case-insensitively (the spec own row writes Rollback).
6. R6 precondition (C12) is its own PIN node test_r6pre_base_paths_log_no_user_id (green at base, so UID stays in the sentinel).
7. P3 route-level invalid values are upper, len63, len65, empty, non-hex, equal-new: a trailing newline, a leading space or a non-ASCII value cannot travel as an HTTP header through the test client, so those three are covered at the helper level in R2 (M3 is killed there by LEG + newline).
8. Additions inside rows: R2 also asserts the helper emits no record from app.api.auth_routes (R-S08B-6) and returns None on a raising header mapping; P5 adds on-own-new; P7 adds social invalid / equal legacy (3 nodes); P1-P7 also assert the admin factory call count and no [LEGACY-FP] record; P14 carries the names rule (p07 count == 1, the four p01 needles absent from auth_routes, legacy_hash / device_lookup_keys absent from app/ and scripts/, _DEVICE_FINGERPRINT_RE never Assign / AnnAssign / AugAssign / NamedExpr target, identity with the leaf object, leaf pattern).
9. M14 is killed by R6 and R7, not R8 (R8 expectations survive M14 by construction). M10 is built as "except: raise" (the arm removed in effect).
10. Comm set: 241 files, not 222 (0 missing, +19, see above); measured here as the base record (the spec left it NOT MEASURED).

## Questions for the gate

- Q1: the extra R11 tokens (OTA, ledger, independent, reasoned, ENABLE_REQUEST_CONTEXT_HEADERS, forbidden "after S81-08 merges") bind GREEN row wording to R-S08B-2 / R-S08B-10; confirm or strike.
- Q2: R3 / R4 / R5 / R8 pin the spec 2.2 literals exactly: select "lifetime_comparisons_used, device_fingerprint_hash", in_("device_fingerprint_hash", [fp, legacy]) in that order, order desc=True passed as a keyword, limit(1); R6 / R7 / R9 pin the exact messages and the auth_routes logger name. A GREEN that reorders the IN list or the select columns goes red by design (the spec contract).
- Q3: R2 drives the helper with a stand-in request whose .headers is a recording mapping and calls it positionally as (request, fp); GREEN must read only through request.headers (the spec 2.1 contract).
- Q4: tests/test_auth_interceptor.py two nodes are red at base because the B4-BE-DIAG branch in auth_service.py:310-318 is unconditional; they are in tests/.pre_impl_failures.txt (recorded, not a regression); a row for its removal is outside this unit.

## NOT MEASURED

Nothing the Measurement rulings require. Outside scope by rule: any live database (the partial-index claim of spec 1.6 stays reasoned), the CI-order / full suite, the hook test files, the comm set at head (GREEN).

## Restore check, cleanup, worktree state

- Real worktree: never mutated by this agent (the prototype and every mutant ran only in the scratch worktree). restore_check.py: 3429 tracked regular files, git hash-object of each working file (autocrlf clean filter) == the HEAD blob id: 0 mismatches; sha256 manifest of every tracked working file: restore_manifest_sha256.txt. HEAD 86d5a24d17f5782e733dee82d52f38dcbf3606ff.
- Scratch worktree <scratchpad>/S81-08b_scratch: git worktree remove --force rc=0; absent from git worktree list; directory gone. It never held a node_modules junction.
- Mutation lock created at the scratch root for the run and removed after the last restore; no lock in the real worktree.
- No orphan pytest: the process scan after the last run shows only the orchestrator stall_monitor.py.
- git status --short of the real worktree: "?? tests/test_s81_s08b_legacy_fingerprint.py" (only the new RED file).
