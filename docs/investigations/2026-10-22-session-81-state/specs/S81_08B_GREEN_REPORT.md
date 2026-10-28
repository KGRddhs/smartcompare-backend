# S81-08b LEGACY-FINGERPRINT-READER: GREEN report

- Unit: S81-08b (lane B backend, additive, FLAGGED `ENABLE_LEGACY_FINGERPRINT_READER`, new name, default OFF, read per call as the first statement of the gated predicate).
- Agent: GREEN, model Opus 5.5 (claude-opus-5-5). The task text labels the role 'GREEN agent (Fable)' and its commit template names Fable 5.1; the commit trailer names this agent's OWN model, `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (the task rule 'the trailer naming YOUR OWN model' and the common brief).
- Window: 2026-10-28 23:55 - 2026-10-29 00:40 AST (about 45 min of the 2 h budget).
- Base: 86d5a24d17f5782e733dee82d52f38dcbf3606ff = origin/main at launch = the RED's base. origin/main moved to a8f01379 (#374 S81-06, 2026-10-28 23:57, recorded in the common brief re-read at 00:00) AFTER this workflow launched (23:56); GREEN stayed at 86d5a24d as the task fixes; the rebase step re-targets (see Rebase items).
- HEAD: 63f159efec41b08e875749c3b3f2b2f7035caa2e on `feature/s81-s08b-legacy-fingerprint-reader` (created with `git checkout -b` before the first edit; one commit through the hook; not pushed, not rebased, no PR).
- Authorities read in full (and the rulings / gate again before this report): s81-common.txt (re-read after it changed on disk), PLAN_S81 (standing constraints, VERIFY quota/auth lines, client lane, flip order), RULINGS_S81_08B, GATE_S81_08B, RULINGS_S81_08 + amendments, the spec, the review, the RED report + notes, the RED file, pyt.py.
- Written THROUGH THE SHELL (python heredocs; the harness refuses a subagent Write of a report .md): this report, PR_BODY.md and notes.md under <scratchpad>/S81-08b_green/. Byte copies of the edited files (before) under <scratchpad>/S81-08b_green_before/ (SHA256SUMS_before.txt). Scripts: green_comm.py, green_run_chunks.py, green_comm_totals.py (shell), green_mutate.py (Write tool: a Bash command over about 7 KB is rejected on this box), green_mutate_m8b.py (shell).

## Files changed (sha256 over the bytes on disk)

| file | before | after | +/- | bytes | CRLF / LF-only | bytes > 127 |
|---|---|---|---|---|---|---|
| app/api/auth_routes.py | 0ee900c98a6268279006d08b746da9f365ebdcafcf51cc5c8c6ae681b7e5460a | f49c4b950b67408a7474f40909db67d67910d42c03c9ca727cd4b3ad72e1c082 | +120 / -7 | 67,765 -> 73,488 | 1,650 -> 1,763 / 0 | 175 -> 175 (added lines 0) |
| CLAUDE.md | 1b2375cbdcd1cdf6c47cda858b2b2aa81f80be327dca07f4f3244c9c7ec4c6b6 | 6a52dd06ffe37517eb022e5b39cb9bca4dd339507ad2ecf5728e34b07a1d321a | +9 / -2 | 525,719 -> 532,726 | 968 -> 975 / 0 | 3,937 -> 3,937 (added text 0) |
| tests/test_s81_s08b_legacy_fingerprint.py (RED, frozen, committed unedited) | 2f4f8237904ce960e7f8de67db4fbda38e765477d78a13b21753b508da2f6a92 | 2f4f8237904ce960e7f8de67db4fbda38e765477d78a13b21753b508da2f6a92 | +1200 / -0 | 45,921 | LF (index LF) | 0 |

RED re-hash: at start 2f4f8237... (worktree == the RED notes copy), at the end 2f4f8237..., committed blob 2f4f8237...: OK. Only ONE RED file exists (the task text says 'two RED files'; the RED report and GATE_S81_08B name one); the commit holds it plus the two edited files. Untouched base files used by mutants M18-M20 end byte-identical: referral_routes.py 00f624f2..., referral_service.py 3e93b86e...

## Implementation (spec change list 1a-1e + 2a-2c, own code; the RED prototype diff read as a reference only)

- 1a `legacy_fingerprint_reader_enabled()` after `social_device_fingerprint_enabled`: `os.getenv("ENABLE_LEGACY_FINGERPRINT_READER", "false").strip().lower() in ("true", "1", "yes", "on")`, per call; docstring names S81-08 R-S08-4 / R-S08-7, the cutoff 2027-03-31T21:00Z, S81-08c, default OFF.
- 1b `_read_valid_legacy_fingerprint(request: Request, fp: Optional[str]) -> Optional[str]`: FIRST statement `if not legacy_fingerprint_reader_enabled(): return None` (request untouched OFF); `raw = request.headers.get("X-Device-Fingerprint-Legacy")` inside `try / except Exception -> None`; `not isinstance(raw, str) or _DEVICE_FINGERPRINT_RE.fullmatch(raw) is None -> None`; `raw == fp -> None`; else raw. Never logs, never raises, never 400.
- 1c `_inherit_device_counter_with_legacy(admin_client, fp, legacy, user_id, *, floor=0, site)`: one `try`: `.table("users").select("lifetime_comparisons_used, device_fingerprint_hash").in_("device_fingerprint_hash", [fp, legacy]).order("lifetime_comparisons_used", desc=True).limit(1).execute()`; inherited = max(floor, top lcu or 0); top = legacy | new | none from the returned row's stored hash; the base update `{device_fingerprint_hash: fp, lifetime_comparisons_used: inherited}` `.eq("id", user_id)`; then INFO `[LEGACY-FP] site=%s top=%s`; `except Exception` -> WARNING `[LEGACY-FP] site=%s inherit failed: %s` with `type(exc).__name__`. `_inherit_device_counter` and `_read_valid_device_fingerprint` byte-identical (P13).
- 1d social apply: `legacy = _read_valid_legacy_fingerprint(request, fp)` right after `if not fp or not user_id: return` (outside the try); the own read and the first-device early return unchanged; `if legacy is None:` the base call verbatim, `else:` the dual call with the same floor expression and site="social". `social_login` itself unchanged (P6).
- 1e register: inside `if fp and new_user_id:`, before `try:`, the legacy read; inside the try `if legacy is None:` the base call verbatim, `else:` the dual call with site="register"; the except arm unchanged.
- 2a CLAUDE.md row `**SESSION 81 flag (S81-08b LEGACY-FINGERPRINT-READER, 2026-10-29; ...)**` + 5 bullets (flag/effect/why/stakes; flag-OFF identity; activation; stated limits (10); owner steps) after the S81-14 block (the newest session-81 row on main), before `## Tests`; slice 6,558 chars bounded at `
## ` (R11 cap 8000); every R11 exact token and word present, the forbidden phrase absent. 2b the Feature Flags pointer sentence after the S81-04 one on :341. 2c the Auth + security hardening bullet :231 in place.

## Gate conditions (GC-1..GC-11): conformance

| GC | status | evidence |
|---|---|---|
| GC-1 | met | R11 green at HEAD (tokens OTA, ledger, independent, reasoned, ENABLE_REQUEST_CONTEXT_HEADERS present; 'after S81-08 merges' absent) |
| GC-2 | met | the select / in_ [fp, legacy] / order desc=True keyword / limit(1) literals and the three message texts + the app.api.auth_routes logger: R3 R4 R5 R6 R7 R8 R9 green |
| GC-3 | met | helper named and called positionally, reads only `request.headers.get`, never logs, None on a raising mapping or legacy == fp: R2 + R10 green |
| GC-4 | met | the two test_auth_interceptor nodes identical at base and head (pre_impl); nothing changed there |
| GC-5 | met | the RED deviations taken as measured; RED file unedited |
| GC-6 | met | first gate before any edit: 14 failed (AssertionError only) / 71 passed; sets A 599 and B 661+1 green; comm base = the RED's 241-file record |
| GC-7 | met (docs part orchestrator) | row after the newest session-81 row; flip ON on web right after deploy as its OWN step before the first OTA, independent of and earlier than ENABLE_REQUEST_CONTEXT_HEADERS; OTA precondition = the DATED ledger line, never the merge; rollback = unset. OWNER_ACTIONS item: orchestrator |
| GC-8 | met | one `request.headers.get("X-Device-Fingerprint")` literal (count 1); no `legacy` + `_hash` / `device` + `_lookup_keys` in app/ or scripts/; leaf import set unchanged; `_DEVICE_FINGERPRINT_RE` never assigned (P14 green); two sites only; NEW stored only; share / SAME_DEVICE untouched (P8 P11 P12); silent drop; flag first; the primary INFO length line unchanged |
| GC-9 | met | the ten stated limits in the CLAUDE.md row and the PR body |
| GC-10 | met | report, PR body and notes written through the shell |
| GC-11 | met | branch before the first edit; one commit through the hook (no --no-verify); trailer = own model; no push / rebase / PR |

## Runs (every pytest through pyt.py, the shared .venv-qaren, one at a time)

| gate | result | [hermeticity] / [netguard] | [pyt] |
|---|---|---|---|
| first gate: RED file at base | 14 failed (14 x AssertionError, no other type), 71 passed | 85 / 0 from 0 | `[pyt] tag=s08b-green-gate1-unit-base start=2026-10-29 00:03:27 end=2026-10-29 00:03:33 elapsed=6s bound=600s status=FAIL rc=1` |
| first gate: set A at base | 599 passed | 599 / 14 from 8 | `[pyt] tag=s08b-green-gate1-A-base start=2026-10-29 00:03:39 end=2026-10-29 00:04:09 elapsed=29s bound=1200s status=OK rc=0` |
| first gate: set B at base | 661 passed, 1 skipped | 661 / 34 from 6 | `[pyt] tag=s08b-green-gate1-B-base start=2026-10-29 00:04:16 end=2026-10-29 00:04:37 elapsed=21s bound=1200s status=OK rc=0` |
| unit file HEAD, flag unset | 85 passed | 85 / 0 from 0 | `[pyt] tag=s08b-green-unit-off start=2026-10-29 00:10:53 end=2026-10-29 00:10:57 elapsed=4s bound=600s status=OK rc=0` |
| unit file HEAD, flag ON exported | 85 passed | 85 / 0 from 0 | `[pyt] tag=s08b-green-unit-on start=2026-10-29 00:10:58 end=2026-10-29 00:11:02 elapsed=4s bound=600s status=OK rc=0` |
| set A HEAD flag OFF | 599 passed (= base) | 599 / 14 from 8 | `[pyt] tag=s08b-green-head-A-off start=2026-10-29 00:11:15 end=2026-10-29 00:11:36 elapsed=21s bound=1200s status=OK rc=0` |
| set B HEAD flag OFF | 661 passed, 1 skipped (= base) | 661 / 34 from 6 | `[pyt] tag=s08b-green-head-B-off start=2026-10-29 00:11:43 end=2026-10-29 00:12:04 elapsed=21s bound=1200s status=OK rc=0` |
| test_s81_kb_schema.py HEAD OFF | 529 passed | 529 / 0 from 0 | `[pyt] tag=s08b-green-head-kb-off start=2026-10-29 00:12:10 end=2026-10-29 00:12:18 elapsed=8s bound=600s status=OK rc=0` |
| G5 flag ON sweep: A + B + kb_schema | 1789 passed, 1 skipped | 1789 / 48 from 14 | `[pyt] tag=s08b-green-head-AB-on start=2026-10-29 00:12:26 end=2026-10-29 00:13:10 elapsed=44s bound=1200s status=OK rc=0` |
| CI-order set (22 sorted: A + B + the RED file; the CLAUDE.md readers are in B) | 1345 passed, 1 skipped | 1345 / 48 from 14 | `[pyt] tag=s08b-green-ci-order start=2026-10-29 00:26:40 end=2026-10-29 00:27:20 elapsed=40s bound=1200s status=OK rc=0` |

Lint: `.venv-qaren python -m py_compile app/api/auth_routes.py tests/test_s81_s08b_legacy_fingerprint.py` rc 0; `python -m ruff check --select E9,F63,F7,F82 --no-cache` on both: All checks passed! (ruff 0.16.5). Hook: `.githooks/pre-commit` ran on the commit (ruff tier 'All checks passed!', no refusal; black not applicable: neither file is on .github/black-clean-paths.txt). Added-line sweep (@gmail, +973, 8+ digit runs, key / JWT / PEM / credentialed-URL shapes) over the diff, the RED file and PR_BODY.md: 0 hits.

### Mutation table on the committed bytes (spec G6; real worktree, .qa-mutation.lock held and removed, byte copies, restore sha-verified after each, git status clean after the run)

| # | mutant | failing rows (all AssertionError unless noted) | [pyt] (bound 600) |
|---|---|---|---|
| M1 | flag reader returns True | P1, P5, R1, R2 | s08b-green-mut-M1 00:30:46-00:30:52 6s FAIL rc=1 |
| M2 | no .strip().lower() | R1 | s08b-green-mut-M2 00:30:53-00:30:58 5s FAIL rc=1 |
| M3 | fullmatch -> match | R2 | s08b-green-mut-M3 00:30:58-00:31:03 5s FAIL rc=1 |
| M4 | raw == fp dedupe removed | P3, P7 (equal-new), R2 | s08b-green-mut-M4 00:31:04-00:31:10 6s FAIL rc=1 |
| M5 | dual update stores legacy | R3, R4, R5, R8 | s08b-green-mut-M5 00:31:10-00:31:15 5s FAIL rc=1 |
| M6 | in_ [legacy] only | R3, R4, R5, R8 | s08b-green-mut-M6 00:31:15-00:31:21 5s FAIL rc=1 |
| M7 | desc=False | R3, R4, R5, R6, R8 | s08b-green-mut-M7 00:31:21-00:31:26 5s FAIL rc=1 |
| M8 | header read (unguarded) before the flag read | R10 (AssertionError) + R2 (RuntimeError: the exploding mapping now raises out of the helper) | s08b-green-mut-M8 00:31:26-00:31:32 5s FAIL rc=1 |
| M8b | header read (guarded) before the flag read | R2 ('R2 OFF reads no header') + R10, AssertionError only | s08b-green-mut-M8b 00:33:08-00:33:18 10s FAIL rc=1 |
| M9 | INFO formats the legacy value | R3, R4, R5, R6, R7, R8 (sentinel) | s08b-green-mut-M9 00:31:32-00:31:37 6s FAIL rc=1 |
| M10 | dual except arm re-raises | R9 | s08b-green-mut-M10 00:31:38-00:31:43 6s FAIL rc=1 |
| M11 | social upgrade-on-match | P5 (on-own-legacy) | s08b-green-mut-M11 00:31:43-00:31:49 6s FAIL rc=1 |
| M12 | register consults legacy without NEW | P4 | s08b-green-mut-M12 00:31:49-00:31:54 5s FAIL rc=1 |
| M13 | register always dual (in_ [fp, None]) | P1, P2, P3 | s08b-green-mut-M13 00:31:55-00:32:00 6s FAIL rc=1 |
| M14 | legacy reads as new | R6, R7 (R8 keeps its labels by construction, as the RED found) | s08b-green-mut-M14 00:32:00-00:32:06 5s FAIL rc=1 |
| M15 | no update when no rows | R8 (no-rows) | s08b-green-mut-M15 00:32:06-00:32:12 6s FAIL rc=1 |
| M16 | social dual floor=0 | R5 (own6-floor) | s08b-green-mut-M16 00:32:12-00:32:17 5s FAIL rc=1 |
| M17 | social_login applies when the legacy flag is ON | P6 | s08b-green-mut-M17 00:32:17-00:32:23 5s FAIL rc=1 |
| M18 | share forwards the legacy header (referral_routes) | P8 (body-absent), R10 | s08b-green-mut-M18 00:32:23-00:32:28 5s FAIL rc=1 |
| M19 | _load_invitee selects the hash (referral_service) | P11 | s08b-green-mut-M19 00:32:28-00:32:34 6s FAIL rc=1 |
| M20 | cap function .in_ [fp, fp] (referral_service) | P12 | s08b-green-mut-M20 00:32:34-00:32:39 5s FAIL rc=1 |

Result: 20 / 20 KILLED by an assertion failure in a named row (M8 by R10; M8b shows R2 kills the guarded form too); 0 survivors. Detail: green_mutants.json, green_mutants_m8b.json, mut_M*.log.

## Comm set at HEAD (zero-regression gate)

Base record: the RED's 241 files at 86d5a24d (<scratchpad>/S81-08b_red/comm_files.txt, comm_reasons.tsv, s08b_comm_base_failed_sorted.txt): 12,083 passed, 3 failed, 2 errors, 35 skipped, 40 deselected, 36 xfailed. HEAD union re-derived by green_comm.py (the RED's rule classes + the new names this unit adds: legacy_fingerprint_reader_enabled, _read_valid_legacy_fingerprint, _inherit_device_counter_with_legacy, ENABLE_LEGACY_FINGERPRINT_READER, Fingerprint-Legacy, LEGACY-FP; + a deliberately wide probe on get_admin_supabase_client / register_user / sign_in_with_social): all 241 re-derived (none dropped) + the RED file = the BINDING 242-file set; the wide probe added 20 files that only reference get_admin_supabase_client in OTHER modules' namespaces (not a symbol this unit changes or newly references) = a supplementary HEAD-only chunk. Lists: head_comm_files.txt (262), head_comm_reasons.tsv, head_chunk_00..10.txt. Chunks 00-08 are byte-identical to the RED's base chunks; chunk 09 = the base chunk 09 + the RED file appended last (17 files); chunk 10 = the 20 supplementary files. Runner green_run_chunks.py: one chunk at a time, bound 1200, the flag removed from the child env, the repo NETWORK_FLAKY_EXCLUDE deselected as at base (1 node, tests/test_rate_limiting_complete.py::TestRateLimitCoverage::test_prices_endpoint_rate_limited in chunk 05, the same as the base record).

| chunk | HEAD | [hermeticity] / [netguard] (base) | [pyt] |
|---|---|---|---|
| 00 | 2 failed, 793 passed | 795 / 18 from 7 (same) | `[pyt] tag=s08b-comm-head-00 start=2026-10-29 00:15:14 end=2026-10-29 00:15:45 elapsed=30s bound=1200s status=FAIL rc=1` |
| 01 | 1231 passed, 1 skipped, 8 deselected | 1232 / 26 from 11 (same) | `[pyt] tag=s08b-comm-head-01 start=2026-10-29 00:15:45 end=2026-10-29 00:16:28 elapsed=43s bound=1200s status=OK rc=0` |
| 02 | 1366 passed, 10 deselected | 1366 / 29 from 11 (same) | `[pyt] tag=s08b-comm-head-02 start=2026-10-29 00:16:28 end=2026-10-29 00:16:58 elapsed=30s bound=1200s status=OK rc=0` |
| 03 | 1230 passed | 1230 / 35 from 30 (same) | `[pyt] tag=s08b-comm-head-03 start=2026-10-29 00:16:58 end=2026-10-29 00:18:11 elapsed=73s bound=1200s status=OK rc=0` |
| 04 | 550 passed, 8 deselected | 550 / 3 from 3 (same) | `[pyt] tag=s08b-comm-head-04 start=2026-10-29 00:18:17 end=2026-10-29 00:18:36 elapsed=19s bound=1200s status=OK rc=0` |
| 05 | 493 passed, 24 skipped, 3 deselected, 1 xfailed, 2 errors | 496 / 119 from 23 (same) | `[pyt] tag=s08b-comm-head-05 start=2026-10-29 00:18:36 end=2026-10-29 00:19:04 elapsed=28s bound=1200s status=FAIL rc=1` |
| 06 | 1096 passed | 1096 / 0 from 0 (same) | `[pyt] tag=s08b-comm-head-06 start=2026-10-29 00:19:05 end=2026-10-29 00:21:44 elapsed=159s bound=1200s status=OK rc=0` |
| 07 | 1 failed, 3853 passed | 3854 / 42 from 12 (same) | `[pyt] tag=s08b-comm-head-07 start=2026-10-29 00:21:49 end=2026-10-29 00:23:57 elapsed=129s bound=1200s status=FAIL rc=1` |
| 08 | 539 passed, 1 skipped, 11 deselected | 540 / 131 from 59 (same) | `[pyt] tag=s08b-comm-head-08 start=2026-10-29 00:23:58 end=2026-10-29 00:25:01 elapsed=63s bound=1200s status=OK rc=0` |
| 09 (+ RED file) | 1017 passed, 9 skipped, 35 xfailed | 1061 (= 976 + 85) / 8 from 8 | `[pyt] tag=s08b-comm-head-09 start=2026-10-29 00:25:01 end=2026-10-29 00:25:32 elapsed=31s bound=1200s status=OK rc=0` |
| 10 (supplementary, HEAD only) | 303 passed, 5 deselected | 303 / 20 from 1 | `[pyt] tag=s08b-comm-head-10 start=2026-10-29 00:25:38 end=2026-10-29 00:26:04 elapsed=26s bound=1200s status=OK rc=0` |

HEAD totals over the binding 242: 12,168 passed (= 12,083 + 85), 3 failed, 2 errors, 35 skipped, 40 deselected, 36 xfailed. HEAD FAILED/ERROR set (s08b_comm_head_failed_sorted.txt) == the base set, 5 nodes: tests/test_auth_interceptor.py::test_sign_in_with_social_exception; tests/test_auth_interceptor.py::test_social_login_user_insert_fails_gracefully; tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence (ERROR); tests/test_prompt_truth.py::test_truth_on_prefix_static_and_cacheable (ERROR); tests/test_sentry_channels_u8d.py::TestU8dPins::test_u8d_pin_integration_list_unchanged. `comm -13` (branch-only-new) = EMPTY; `comm -23` = EMPTY; `comm -12` = 5.

## Deviations (each with the reason it beats the alternative)

1. One RED file, not two: the task text says 'the two RED files'; the RED report, GATE_S81_08B and the worktree hold exactly one (tests/test_s81_s08b_legacy_fingerprint.py). Committed that one with the two edited files.
2. Model / trailer: the task text says 'GREEN agent (Fable)' and its commit template names 'Claude Fable 5.1'; this agent is Opus 5.5, and the same task text says 'the trailer naming YOUR OWN model' (the common brief: never claim another model), so the trailer is `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
3. Base: origin/main moved to a8f01379 (#374 S81-06) at 23:57, one minute after this workflow launched at 86d5a24d; the task fixes GREEN at 86d5a24d (GC-6's re-point applies to a GREEN launched at a later main), so GREEN measured at 86d5a24d against the RED's record; the rebase is the orchestrator's next step (Rebase items).
4. Comm set: the binding set is 242 (the RED's 241 + the RED file), run in the RED's own chunk composition so base and head group the same files; a supplementary HEAD-only chunk of 20 over-inclusive files (get_admin_supabase_client references in other modules) was run too: all green, so it cannot hold a branch-only-new failure and needs no base record.
5. Mutation table re-run on the committed bytes (spec G6) although the task procedure does not list it: it proves the RED's 20-mutant table on the GREEN code (the RED proved it on its own prototype). M8 as an unguarded peek fails R2 with the exploding mapping's RuntimeError (R10 is the assertion kill); the guarded variant M8b shows R2's own assertion kills the read-before-flag order.
6. The CLAUDE.md row date is 2026-10-29 (the GREEN commit date) where the spec draft says 2026-10-24; the Auth bullet adds '(S81-08b, default OFF)' and 'when invalid or equal' to the spec's 2(c) sentence (the same rule, stated fully).
7. CI-order set = sets A + B (which contain the three CLAUDE.md readers) + the RED file = 22 files sorted (tests/test_s81_kb_schema.py ran on its own flag OFF and inside the flag-ON sweep, both green).
8. PR_BODY.md carries 4 bytes > 127: the required closing robot line only; every other written file is pure ASCII + LF (report, notes, scripts); CLAUDE.md and auth_routes.py keep CRLF with ASCII-only additions.

## Questions for the gate

- Q1: `top` for a returned row whose stored hash equals neither value reads `none` (the counter is still taken from that row). PostgREST's `in` filter makes the case unreachable; keep the three-label contract (spec 2.2) or add a fourth label?
- Q2: `users.lifetime_comparisons_used` is `INT DEFAULT 0`, nullable (migration 011); `ORDER BY ... DESC` puts NULLs first in PostgreSQL, so a NULL-counter row on a matched device would be read as 0. Identical to the base `_inherit_device_counter` read, and GC-2 binds `order(..., desc=True)` exactly; out of scope here: a follow-up note for S81-09?
- Q3 (orchestrator, docs): OWNER_ACTIONS gains the flip item (GC-7); PLAN_S81:185 gains the S81-08b ON step before 'the first OTA' (R-S08B-2); the DEFECT_LEDGER S81-08b row gains the RED file / branch / HEAD 63f159ef.

## NOT MEASURED

Nothing the gate requires. Outside scope by rule: the full suite; the four test_precommit_hook*.py files (the unit edits no .githooks file); any database (the partial-index claim stays reasoned); the comm set at the rebased HEAD (after the rebase onto a8f01379, by the rebase step).

## Rebase items (for the orchestrator's rebase onto a8f01379 or later)

- CLAUDE.md :341 (the one physical Feature Flags line) is edited by S81-06 too: re-apply the S81-08b pointer sentence by hand on top of S81-06's line; the row anchor after the newest session-81 row is a union with S81-06's row (R11's slice stays bounded by the next `
**SESSION` or `
## `). app/api/auth_routes.py: no S81-06 hunk expected (verify with the rebase diff).
- Re-derive the comm set at the rebased HEAD (S81-06 adds files that import app.main) and take a fresh base record there; the SR8 node (test_sentry_channels_u8d.py::TestU8dPins::test_u8d_pin_integration_list_unchanged) should turn green with S81-06's re-pin.

## Worktree state

`git status --short` of C:/Users/SynAckITPC/Documents/AI/sc-s81-s08b after the commit and after the mutation run: EMPTY (clean vs HEAD 63f159ef). No .qa-mutation.lock, no scratch worktree created by this agent, no orphan pytest (process scan: only the orchestrator's stall_monitor.py).
