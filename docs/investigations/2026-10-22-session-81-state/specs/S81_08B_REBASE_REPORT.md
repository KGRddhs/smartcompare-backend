# S81-08b LEGACY-FINGERPRINT-READER: REBASE-AND-GATES report

- Unit: S81-08b (lane B backend, FLAGGED `ENABLE_LEGACY_FINGERPRINT_READER`, default OFF, read per call).
- Agent: REBASE-AND-GATES, model Opus 5.5 (claude-opus-5-5). Window 2026-10-29 02:30 - ~04:00 AST (first tool call 02:30:07).
- Authorities read in full at the start and again before this report: s81-common.txt, RULINGS_REBASE_S81_08B (RB8-1..RB8-12, binding), GATE_S81_08B (GC-1..GC-11), RULINGS_S81_08B, the GREEN report, both adversary reports (the mutant definitions from their scratch JSON / scripts), the GREEN PR body, the RED file (all 1,200 lines).
- Written THROUGH THE SHELL (python): this report and PR_BODY.md (assembled from .txt parts written with the Write tool, as the engineering adversary did). Scripts (Write tool): resolve_claude.py, rebase_comm.py, rb8_mutate.py, rb_run_chunks.py. Notes: <notes>/notes.md. <notes> = <scratchpad>/S81-08b_rebase.

## Result

- verdict: READY_FOR_PR
- head_before: 63f159efec41b08e875749c3b3f2b2f7035caa2e (feature/s81-s08b-legacy-fingerprint-reader, base 86d5a24d; verified with `git status --short` EMPTY before anything)
- base_main: a8f01379b05c0079c72a74418bdbce2f4acfbe7d (origin/main re-fetched 02:31; FETCH_HEAD = origin/main = a8f01379, unchanged since the rulings)
- after the rebase: b8d611e42ca29d82cef4af0387174dc195fb8604 (63f159ef replayed; the only replayed commit)
- head_after: 9088563f9ecf1e4b61ac01dd0d6101def59d372e (the ONE pin commit, through the hook, trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; not pushed)
- footprint `git diff --stat origin/main...HEAD`: CLAUDE.md (11 +-), app/api/auth_routes.py (127 ++-), tests/test_s81_s08b_gate_rows.py (422 +), tests/test_s81_s08b_legacy_fingerprint.py (1200 +); 4 files, 1751 insertions, 9 deletions; nothing else differs from main; no whole-file diff.
- `git diff 63f159ef HEAD -- app/api/auth_routes.py` = EMPTY (0 bytes); the same for the RED file.
- RED file BLOB (`git show HEAD:tests/test_s81_s08b_legacy_fingerprint.py | sha256sum`) = 2f4f8237904ce960e7f8de67db4fbda38e765477d78a13b21753b508da2f6a92 before the rebase, after the rebase and after the pin commit (never edited). The working copy is CRLF after the rebase checkout (9436574d...), exactly as eng m7 predicted; never used for the check.
- `git status --short` of the worktree at the end: EMPTY. No .qa-mutation.lock. The base scratch worktree removed (absent from `git worktree list`, directory gone). No orphan pytest (process scan by tag / path: none).

## Files (sha256 over the bytes on disk)

| file | state | sha256 |
|---|---|---|
| tests/test_s81_s08b_gate_rows.py | NEW, LF, pure ASCII, 15,938 B, 29 nodes (blob = working copy) | 65f0 4597 9762 50ef 0ba4 0a17 2438 f980 db9e b490 a4aa 4c54 1c9c 4454 753a bfe1 |
| CLAUDE.md | union resolution + RB8-8 (a)-(e) in place; CRLF working copy (978 CRLF, 0 bare), non-ASCII 3,937 = main | working copy 6006692dc8c99452cc47bd43492d9f9dc8afd22d549721d78f05aa84fc4f03a6; blob 9c2a 04d0 5216 9a52 e117 042d 8634 2a39 a563 7152 227c 7371 3224 e531 2ffc ada3 (grouped: the hex holds long digit runs) |
| app/api/auth_routes.py | unchanged since 63f159ef | working copy f49c4b950b67408a7474f40909db67d67910d42c03c9ca727cd4b3ad72e1c082; blob 0b06 0385 9682 d074 2425 ff... (see `git show`) |
| tests/test_s81_s08b_legacy_fingerprint.py | frozen RED file | BLOB 2f4f8237904ce960e7f8de67db4fbda38e765477d78a13b21753b508da2f6a92 |
| <notes>/PR_BODY.md | the finalised PR body, pure ASCII (no robot line: the orchestrator appends the trailer) | 0207cc91dc6fe8ede7b3bdf2233459b836b4ea2fbc1571fbd2ba522db64762e6 |

## Conflicts and resolutions (RB8-1)

`git merge-tree --write-tree --name-only origin/main HEAD` before the rebase: one conflicted file, CLAUDE.md. `GIT_EDITOR=true git rebase origin/main`: ONE commit replayed, ONE conflict stop (CLAUDE.md), two sites, both "both sides added at the same anchor", resolved by UNION in session order (S81-06 on main first, then S81-08b) with resolve_claude.py (binary, CRLF-preserving, every assumption asserted):
1. The `**Feature Flags:**` pointer paragraph (one physical line, :341): both sides were pure insertions at the same base offset (1,420): main inserted S81-06's sentence (547 B: the seven ENABLE_ANTHROPIC_* / SONNET / OPENAI_PRE_V3 names and the ANTHROPIC_* knobs), the branch inserted this unit's sentence (168 B). Union = base[:1420] + S81-06 sentence + S81-08b sentence + base[1420:] (asserted equal to main's line with the branch sentence inserted after S81-06's, and to the branch line with S81-06's inserted before). Nothing dropped or reworded.
2. The row anchor after the S81-14 block: main's S81-06 row (2 lines) kept first, one blank line, then this unit's row (6 lines), then the existing blank line and `## Tests`.
The :231 Auth bullet merged automatically (no counterpart on main). Checks: line-level diff of the union vs main = exactly the branch's three hunks vs its base (replace :231, replace :341, insert 7 lines); `git diff --cached --check` clean; `GIT_EDITOR=true git rebase --continue` -> b8d611e4; `git diff --check a8f01379 HEAD` clean; grep of `^<<<<<<<` / `^>>>>>>>` over CLAUDE.md, app/ and tests/ empty. No test file and no app file conflicted (gate (2) of the workflow prompt, "each conflicted test file alone", therefore had nothing to run).

Row heads at HEAD (column 0): S81-14 :497, S81-06 :507, S81-08b :510; at a8f01379: S81-14 :497, S81-06 :507 (the rulings' cites hold).

## RB8-8 CLAUDE.md row edits (the Edit tool, CRLF kept, ASCII only)

(a) limit (10) -> "the comm-set base record was re-measured at the rebase main `a8f01379` (247 files; the RED's 241 at `86d5a24d` was the GREEN's base)" (the count confirmed by the base record, which completed before the commit); (b) the identity sentence gained "; the app-logger record lists on the drop paths and the no-value rule are pinned by `tests/test_s81_s08b_gate_rows.py` (RB8-2), the failure table by RB8-3"; (c) the canary sentence replaced verbatim by the ruling's text; (d) the stakes sentence now names the `/usage/status` figures (verified: `_usage_status_body` reports `remaining.daily` / `remaining.monthly` as the full allowance when `on_lifetime_free`, usage_service.py:801-837); (e) the new stated limit (11) verbatim. Nothing else changed (4 lines changed by RB8-8). R11-bounded slice: 7,739 characters with universal newlines (7,745 CRLF), under the 8,000 cap; every R11 token present, "after s81-08 merges" absent; R11 / RB8-4 / RB8-5 green.

## Pin rows (tests/test_s81_s08b_gate_rows.py; RB8-2..RB8-7) and the ten mutants

The file reaches the RED harness by `from tests.test_s81_s08b_legacy_fingerprint import ...` (FakeDB, _Query, the `full` fixture, the autouse `_no_limiter` / `_unit_flag_unset`, the drivers, the literals), as tests/test_s81_s06_router_gate_rows.py does. 29 nodes: RB8-2 drop-path identity x10 + capture liveness x2; RB8-3 failure table x12; RB8-4 x1; RB8-5a x1; RB8-5b x1; RB8-6 x1; RB8-7 x1. Green at HEAD flag unset and flag exported (29 / 29 each).

RB8-2 literals: recorded at a8f01379 in the detached base scratch worktree with this file and the RED file copied in untracked (`S08B_GATE_ROWS_RECORD=<notes>/rb82_record_base.jsonl ... -k rb8_2`, 12 passed at base), then the rows file removed from it: register = [] and social = [] in all five scenarios (no app.* record at all on the drop paths), liveness = [[app.api.auth_routes, 20, "device-fp header rejected: invalid format (expected 64-char hex), len=64"]] at both sites; the HEAD record (rb82_record_head.jsonl) equals the base record for all 12 observations. (b) is asserted before (a) so a value leak reports as (b).

Mutants (rb8_mutate.py; byte copy + sha, one exact edit matching once (E15 a scripted CRLF move), the whole rows file through pyt.py bound 600, restore, sha compare; .qa-mutation.lock held for the run and removed). Round 2 = the final rows bytes (65f0 4597 ... bfe1); round 1 (before (b) was moved ahead of (a)) gave the same 10 / 10 (logs under <notes>/mut_round1/):

| mutant | definition (source) | failed nodes (all AssertionError) | named row | round-2 [pyt] |
|---|---|---|---|---|
| N1 | dual `except Exception` -> `except RuntimeError` (correctness adv_mutants.json) | 8 = RB8-3 APIError + ConnectError cases | RB8-3 KILLED | `[pyt] tag=s08b-rb-mut-N1 start=2026-10-29 02:50:48 end=2026-10-29 02:51:04 elapsed=15s bound=600s status=FAIL rc=1` |
| N2 | the dual update built in the try, executed after it | 6 = every RB8-3 op=update case | RB8-3 KILLED | `[pyt] tag=s08b-rb-mut-N2 start=2026-10-29 02:51:04 end=2026-10-29 02:51:17 elapsed=13s bound=600s status=FAIL rc=1` |
| N3 | untagged register INFO whenever legacy is None | 5 = RB8-2 register x5, by (a) | RB8-2 KILLED | `[pyt] tag=s08b-rb-mut-N3 start=2026-10-29 02:51:17 end=2026-10-29 02:51:24 elapsed=7s bound=600s status=FAIL rc=1` |
| N3b | register logs the raw legacy header on the drop path (adv_mutants_n3bc.json) | 6 = RB8-2 register x5 ((b) in unset-valid-legacy / on-legacy-63 / on-legacy-equal; (a) in the two no-legacy scenarios) + RB8-6 | RB8-2 KILLED | `[pyt] tag=s08b-rb-mut-N3b start=2026-10-29 02:51:25 end=2026-10-29 02:51:31 elapsed=6s bound=600s status=FAIL rc=1` |
| N3c | the social apply logs the raw legacy header on the drop path | 6 = RB8-2 social x5 (as N3b) + RB8-6 | RB8-2 KILLED | `[pyt] tag=s08b-rb-mut-N3c start=2026-10-29 02:51:31 end=2026-10-29 02:51:46 elapsed=15s bound=600s status=FAIL rc=1` |
| E3b | a second primary read spelled lower case (engineering eng_mutate.py) | 2 = RB8-6 + RB8-7 | RB8-6 KILLED | `[pyt] tag=s08b-rb-mut-E3b start=2026-10-29 02:51:48 end=2026-10-29 02:52:10 elapsed=21s bound=600s status=FAIL rc=1` |
| E9 | the legacy read through `__contains__` + `__getitem__` | 2 = RB8-7 + RB8-6 | RB8-7 KILLED | `[pyt] tag=s08b-rb-mut-E9 start=2026-10-29 02:52:11 end=2026-10-29 02:52:48 elapsed=37s bound=600s status=FAIL rc=1` |
| E12 | the OTA precondition sentence -> "The OTA precondition is the merge of this unit." | 1 = RB8-4 | RB8-4 KILLED | `[pyt] tag=s08b-rb-mut-E12 start=2026-10-29 02:52:49 end=2026-10-29 02:53:17 elapsed=28s bound=600s status=FAIL rc=1` |
| E14 | the Auth bullet sentence removed | 1 = RB8-5b | RB8-5b KILLED | `[pyt] tag=s08b-rb-mut-E14 start=2026-10-29 02:53:18 end=2026-10-29 02:53:43 elapsed=25s bound=600s status=FAIL rc=1` |
| E15 | the row block moved before the S81-14 block | 1 = RB8-5a | RB8-5a KILLED | `[pyt] tag=s08b-rb-mut-E15 start=2026-10-29 02:53:44 end=2026-10-29 02:54:02 elapsed=18s bound=600s status=FAIL rc=1` |

Every restore sha256-matched the pre-mutation copy (rb8_mutants_result.json: restore_ok true x10, both rounds); afterwards `sha256sum -c` of auth_routes.py, CLAUDE.md and the rows file against pre_mutation_shas_round2.txt: OK x3. Equivalent survivors: none.

## Gates at HEAD 9088563f (RB8-10; every pytest through pyt.py, the shared .venv-qaren, one at a time)

| # | gate | result | [hermeticity] / [netguard] |
|---|---|---|---|
| 8 | ruff 0.16.5 --select E9,F63,F7,F82 --no-cache (auth_routes.py, RED file, rows file) | All checks passed! | - |
| 8 | py_compile (same three) | rc 0 | - |
| 8 | pre-commit hook on the pin commit (core.hooksPath .githooks) | ruff tier "All checks passed!", commit rc 0, no --no-verify | - |
| 8 | byte hygiene | test files 0 bytes > 127; auth_routes.py 175 = main 175; CLAUDE.md 3,937 = main 3,937 | - |
| 8 | added-line sweep over `git diff origin/main...HEAD` (mail-domain, country-code phone, 8+ digit runs, sk- / AKIA / xox / JWT / credentialed URL / PEM) | 0 hits (1,751 added lines) | - |
| 1 | RED file, flag unset (the gate) | 85 passed | 85 / 0 from 0 |
| 1 | RED file, flag exported (convenience run, NOT a gate: the autouse `_unit_flag_unset` deletes it per row) | 85 passed | 85 / 0 from 0 |
| 1 | rows file, flag unset | 29 passed | 29 / 0 from 0 |
| 1 | rows file, flag exported | 29 passed | 29 / 0 from 0 |
| 7 | tests/test_ci_gates.py + tests/test_behavior_dimension_translation.py | 79 passed | 79 / 0 from 0 |
| 6 | SR8 pair alone (u8d_unit + u8d) | 273 passed (test_u8d_pin_integration_list_unchanged green) | 273 / 0 from 0 |
| 6 | tests/test_paid_route_metering.py flag unset / exported | 21 passed / 21 passed | 21 / 2 from 2 (both) |
| 3 | pin sets A (8) + B (13) + test_s81_kb_schema.py at a8f01379 (scratch worktree), flag unset / exported | 1789 passed, 1 skipped / 1789 passed, 1 skipped | 1789 / 48 from 14 (both) |
| 3 | the same 22 files at HEAD, flag unset / exported (G5 sweep) | 1789 passed, 1 skipped / 1789 passed, 1 skipped (= base) | 1789 / 48 from 14 (both) |
| 4 | CI-order set: the GREEN's 22 + the rows file = 23, flag unset | 1374 passed, 1 skipped | 1374 / 48 from 14 |
| 5 | comm set (below) | branch-only-new EMPTY | per chunk below |
| 9 | the four tests/test_precommit_hook*.py files | NOT re-run by ruling RB8-10(9) (no .githooks input or hook-read file touched; the engineering adversary's lines at 63f159ef: `[pyt] tag=s08b-adve-hook-notdash` 875 s OK, `[pyt] tag=s08b-adve-hook-dash` 1215 s OK) | - |

## Comm set (RB8-9), measured

Re-derivation at HEAD (rebase_comm.py; 716 test files scanned; the RED's build_comm.py classes + import-aware `import M` / `from <pkg> import ... <leaf>` (incl. parenthesised lists) / `from M import` for app.api.auth_routes and its app importers {feedback, history, home, image, profile, referral, share, text, url, usage}_routes + app.main, + `.__doc__` readers; minus the four hook files; the RED file and the rows file handled as HEAD members): 246 re-derived = the RED's 241 (all present at HEAD, none dropped) + the three from-package importers (each by `import-aware:app.api.text_routes`) + 2 ADDED: tests/test_s81_s06_anthropic_router.py (module-ref:auth_routes; import-aware app.api.auth_routes / image / text / url routes / app.main; ast.parse; app/ path; request_context) and tests/test_s81_s06_router_gate_rows.py (import-aware app.main / image / url routes; rglob; app-path join; ast.parse; app/ path). Both are on main via #374 and were run on both sides. Lists: <notes>/comm_base_files.txt (247), comm_head_files.txt (248), rebase_comm_reasons.tsv, rebase_comm_rederive.txt, chunk_00..10.txt (00-09 = the RED's chunk files byte-for-byte; 10 = the three + the two), chunk_RED.txt, chunk_HEADONLY.txt, chunk_SUPP.txt.

Base record: a8f01379 in the DETACHED scratch worktree <notes>/b (`git worktree add --detach`; no SmartCompareApp/node_modules, no junction; the RED file copied in untracked from the HEAD blob, sha 2f4f8237... verified, for its own run; removed with `git worktree remove --force`, absent from `git worktree list`, directory gone). Runner rb_run_chunks.py: one chunk at a time, bound 1200, NETWORK_FLAKY_EXCLUDE deselected exactly as the RED's run_chunk.py, ENABLE_LEGACY_FINGERPRINT_READER removed from the child env.

| chunk | files | base a8f01379 | HEAD 9088563f | [hermeticity] / [netguard] base -> head |
|---|---|---|---|---|
| 00 | 25 | 2 failed, 793 passed | 2 failed, 793 passed | 795 / 18 from 7 -> same |
| 01 | 25 | 1231 passed, 1 skipped, 8 deselected | same | 1232 / 26 from 11 -> same |
| 02 | 25 | 1366 passed, 10 deselected | same | 1366 / 29 from 11 -> 1366 / 26 from 10 |
| 03 | 25 | 1230 passed | same | 1230 / 35 from 30 -> 1230 / 32 from 29 |
| 04 | 25 | 550 passed, 8 deselected | same | 550 / 3 from 3 -> same |
| 05 | 25 | 493 passed, 24 skipped, 3 deselected, 1 xfailed, 2 errors | same | 496 / 119 from 23 -> same |
| 06 | 25 | 1096 passed | same | 1096 / 0 -> same |
| 07 | 25 | 3855 passed (SR8 node green) | same | 3855 / 42 from 12 -> same |
| 08 | 25 | 539 passed, 1 skipped, 11 deselected | same | 540 / 131 from 59 -> same |
| 09 | 16 | 932 passed, 9 skipped, 35 xfailed | same | 976 / 8 from 8 -> same |
| 10 | 5 | 452 passed | same | 452 / 121 from 6 -> same |
| RED / HEADONLY | 1 / 2 | 14 failed (the 14 RED rows, 14 x AssertionError), 71 passed | 114 passed (RED 85 + rows 29) | 85 / 0 -> 114 / 0 |
| SUPP (HEAD only) | 20 | - | 303 passed, 5 deselected | 303 / 20 from 1 |

The netguard differences in 02 / 03 are base-only blocked egress attempts (one `api.openai.com` getaddrinfo each in tests/test_flush_live_price_key.py::test_flag_off_body_is_the_legacy_shape_exactly and tests/test_genuine_price_priority.py::TestFlagOffByteIdentity::test_flag_off_timeout_returns_parked_converted) plus hermeticity-pin lines that differ only by ephemeral port; results identical; neither file touches auth_routes.

Totals: base 12,608 passed, 16 failed, 2 errors, 35 skipped, 40 deselected, 36 xfailed (the 246 tracked files: 12,537 passed, 2 failed, 2 errors; the RED file: 71 passed, 14 failed); HEAD 12,651 passed (= 12,537 + 85 + 29), 2 failed, 2 errors, 35 skipped, 40 deselected, 36 xfailed.
Base FAILED/ERROR (tracked files) = the expected four: tests/test_auth_interceptor.py::test_sign_in_with_social_exception, ::test_social_login_user_insert_fails_gracefully (pre_impl), tests/test_prompt_truth.py::test_render_digests_match_base_except_the_fence, ::test_truth_on_prefix_static_and_cacheable (the two chunk-05 ERRORs = the cold-tiktoken pair). SR8 node green both sides.
`comm -13` (branch-only-new) = EMPTY; `comm -23` = the 14 RED rows (fixed at HEAD); `comm -12` = the four. Files: comm_base_failed_sorted.txt (18), comm_base_failed_sorted_noRED.txt (4), comm_head_failed_sorted.txt (4).

## Every [pyt] line (63, in run order; taken from harness/pyt_ledger.jsonl, elapsed in the ledger's decimal form; the stdout lines carry the same tag / start / end / status / rc)

```
[pyt] tag=s08b-rb-rows-head-pre start=2026-10-29 02:43:03 end=2026-10-29 02:43:07 elapsed=3.7s bound=600s status=OK rc=0
[pyt] tag=s08b-rb-rb82-record start=2026-10-29 02:44:40 end=2026-10-29 02:44:44 elapsed=3.8s bound=600s status=OK rc=0
[pyt] tag=s08b-rb-rows-head-off start=2026-10-29 02:46:28 end=2026-10-29 02:46:44 elapsed=16.5s bound=600s status=OK rc=0
[pyt] tag=s08b-rb-rows-head-on start=2026-10-29 02:46:45 end=2026-10-29 02:47:04 elapsed=19.3s bound=600s status=OK rc=0
[pyt] tag=s08b-rb-mut-N1 start=2026-10-29 02:48:25 end=2026-10-29 02:48:33 elapsed=7.4s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-N2 start=2026-10-29 02:48:33 end=2026-10-29 02:48:38 elapsed=5.4s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-N3 start=2026-10-29 02:48:39 end=2026-10-29 02:48:47 elapsed=8.5s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-N3b start=2026-10-29 02:48:47 end=2026-10-29 02:48:53 elapsed=5.3s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-N3c start=2026-10-29 02:48:53 end=2026-10-29 02:48:59 elapsed=5.7s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-E3b start=2026-10-29 02:48:59 end=2026-10-29 02:49:05 elapsed=5.8s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-E9 start=2026-10-29 02:49:06 end=2026-10-29 02:49:11 elapsed=5.3s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-E12 start=2026-10-29 02:49:11 end=2026-10-29 02:49:17 elapsed=5.6s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-E14 start=2026-10-29 02:49:17 end=2026-10-29 02:49:24 elapsed=6.6s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-E15 start=2026-10-29 02:49:24 end=2026-10-29 02:49:30 elapsed=5.3s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-N1 start=2026-10-29 02:50:48 end=2026-10-29 02:51:04 elapsed=15.0s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-N2 start=2026-10-29 02:51:04 end=2026-10-29 02:51:17 elapsed=12.8s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-N3 start=2026-10-29 02:51:17 end=2026-10-29 02:51:24 elapsed=6.8s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-N3b start=2026-10-29 02:51:25 end=2026-10-29 02:51:31 elapsed=6.2s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-N3c start=2026-10-29 02:51:31 end=2026-10-29 02:51:46 elapsed=15.0s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-E3b start=2026-10-29 02:51:48 end=2026-10-29 02:52:10 elapsed=21.3s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-E9 start=2026-10-29 02:52:11 end=2026-10-29 02:52:48 elapsed=37.4s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-E12 start=2026-10-29 02:52:49 end=2026-10-29 02:53:17 elapsed=27.6s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-E14 start=2026-10-29 02:53:18 end=2026-10-29 02:53:43 elapsed=25.3s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-mut-E15 start=2026-10-29 02:53:44 end=2026-10-29 02:54:02 elapsed=18.3s bound=600s status=FAIL rc=1
[pyt] tag=s08b-rb-red-precommit start=2026-10-29 02:54:42 end=2026-10-29 02:55:01 elapsed=18.8s bound=600s status=OK rc=0
[pyt] tag=s08b-rb-comm-base-00 start=2026-10-29 02:56:23 end=2026-10-29 02:57:05 elapsed=41.8s bound=1200s status=FAIL rc=1
[pyt] tag=s08b-rb-comm-base-01 start=2026-10-29 02:57:05 end=2026-10-29 02:58:00 elapsed=55.0s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-base-02 start=2026-10-29 02:58:00 end=2026-10-29 02:58:33 elapsed=32.5s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-base-03 start=2026-10-29 02:58:33 end=2026-10-29 03:01:16 elapsed=162.5s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-base-04 start=2026-10-29 03:01:28 end=2026-10-29 03:01:54 elapsed=26.1s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-base-05 start=2026-10-29 03:01:55 end=2026-10-29 03:02:27 elapsed=31.8s bound=1200s status=FAIL rc=1
[pyt] tag=s08b-rb-comm-base-06 start=2026-10-29 03:02:27 end=2026-10-29 03:05:13 elapsed=165.4s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-base-07 start=2026-10-29 03:05:21 end=2026-10-29 03:07:47 elapsed=146.5s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-base-08 start=2026-10-29 03:07:47 end=2026-10-29 03:08:52 elapsed=64.5s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-base-09 start=2026-10-29 03:09:01 end=2026-10-29 03:09:27 elapsed=26.1s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-base-10 start=2026-10-29 03:09:28 end=2026-10-29 03:10:28 elapsed=59.8s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-base-RED start=2026-10-29 03:10:28 end=2026-10-29 03:10:41 elapsed=12.4s bound=1200s status=FAIL rc=1
[pyt] tag=s08b-rb-pins-base-off start=2026-10-29 03:11:06 end=2026-10-29 03:12:08 elapsed=61.6s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-pins-base-on start=2026-10-29 03:12:09 end=2026-10-29 03:13:10 elapsed=60.6s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-g1-red-off start=2026-10-29 03:15:20 end=2026-10-29 03:15:38 elapsed=17.8s bound=600s status=OK rc=0
[pyt] tag=s08b-rb-g1-red-on start=2026-10-29 03:15:39 end=2026-10-29 03:15:55 elapsed=15.9s bound=600s status=OK rc=0
[pyt] tag=s08b-rb-g1-rows-off start=2026-10-29 03:15:56 end=2026-10-29 03:16:11 elapsed=15.4s bound=600s status=OK rc=0
[pyt] tag=s08b-rb-g1-rows-on start=2026-10-29 03:16:13 end=2026-10-29 03:16:29 elapsed=16.5s bound=600s status=OK rc=0
[pyt] tag=s08b-rb-g7-claude-readers start=2026-10-29 03:16:30 end=2026-10-29 03:16:46 elapsed=15.8s bound=600s status=OK rc=0
[pyt] tag=s08b-rb-g6-sr8-pair start=2026-10-29 03:16:59 end=2026-10-29 03:17:20 elapsed=21.4s bound=600s status=OK rc=0
[pyt] tag=s08b-rb-g6-metering-off start=2026-10-29 03:17:21 end=2026-10-29 03:17:26 elapsed=4.6s bound=600s status=OK rc=0
[pyt] tag=s08b-rb-g6-metering-on start=2026-10-29 03:17:26 end=2026-10-29 03:17:31 elapsed=4.3s bound=600s status=OK rc=0
[pyt] tag=s08b-rb-g3-pins-head-off start=2026-10-29 03:17:46 end=2026-10-29 03:18:56 elapsed=70.0s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-g3-pins-head-on start=2026-10-29 03:18:57 end=2026-10-29 03:20:40 elapsed=103.6s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-g4-ci-order start=2026-10-29 03:20:42 end=2026-10-29 03:21:41 elapsed=59.7s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-head-00 start=2026-10-29 03:21:53 end=2026-10-29 03:22:28 elapsed=35.1s bound=1200s status=FAIL rc=1
[pyt] tag=s08b-rb-comm-head-01 start=2026-10-29 03:22:29 end=2026-10-29 03:24:21 elapsed=112.9s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-head-02 start=2026-10-29 03:24:24 end=2026-10-29 03:25:15 elapsed=51.6s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-head-03 start=2026-10-29 03:25:16 end=2026-10-29 03:28:43 elapsed=207.4s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-head-04 start=2026-10-29 03:28:53 end=2026-10-29 03:29:13 elapsed=20.4s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-head-05 start=2026-10-29 03:29:14 end=2026-10-29 03:29:45 elapsed=31.0s bound=1200s status=FAIL rc=1
[pyt] tag=s08b-rb-comm-head-06 start=2026-10-29 03:29:45 end=2026-10-29 03:32:50 elapsed=184.3s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-head-07 start=2026-10-29 03:33:01 end=2026-10-29 03:36:39 elapsed=217.8s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-head-08 start=2026-10-29 03:36:40 end=2026-10-29 03:38:07 elapsed=86.9s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-head-09 start=2026-10-29 03:38:18 end=2026-10-29 03:38:48 elapsed=30.3s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-head-10 start=2026-10-29 03:38:49 end=2026-10-29 03:39:15 elapsed=26.3s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-head-HEADONLY start=2026-10-29 03:39:16 end=2026-10-29 03:39:22 elapsed=6.5s bound=1200s status=OK rc=0
[pyt] tag=s08b-rb-comm-head-SUPP start=2026-10-29 03:40:06 end=2026-10-29 03:40:46 elapsed=39.6s bound=1200s status=OK rc=0
```

## NOT MEASURED

- The four tests/test_precommit_hook*.py files: not run, by ruling RB8-10(9) (the unit touches no .githooks input; the rebase adds test rows and CLAUDE.md sentences only; the adversary's 63f159ef lines are cited in the PR body). No gate timed out; nothing else is unmeasured among the gates the rulings name. Outside scope by rule: the full suite; any database (the index claim stays reasoned); production.

## Deviations (each with the reason it beats the alternative)

1. Comm membership 247 at base / 248 at HEAD instead of the rulings' 245 / 246: the RB8-9 import-aware re-derivation at HEAD added tests/test_s81_s06_anthropic_router.py and tests/test_s81_s06_router_gate_rows.py (both merged with #374); RB8-9 says any added file is run on both sides and listed, which was done (chunk 10: 452 passed on both sides). The CLAUDE.md limit (10) states 247.
2. The RED file is not on main, so "245 at base" could only include it by copying it into the base scratch worktree untracked (from the HEAD blob, sha-verified) for its own run: 14 failed (the 14 RED rows, AssertionError only), 71 passed. The all-files base failure set therefore has 18 nodes (the expected four + the 14 RED rows, all in `comm -23`); the tracked-file base set is exactly the expected four. Running it gave a fresh RED-at-base check at the new main instead of silently dropping a member.
3. The rulings list "the cold-tiktoken pair + the two chunk-05 errors" as if distinct; measured, they are the same two nodes (4 expected base failures in all, not 6).
4. RB8-2 carries two extra nodes, test_rb8_2_capture_liveness[register|social] (recorded at a8f01379 with the other RB8-2 rows): with an empty literal, (a) would pass vacuously if the capture saw nothing; the control proves the capture is live. And (b) is asserted before (a), so the kill attribution matches the ruling (N3 by (a); N3b / N3c by (b) in the legacy-valued scenarios). The rows file therefore has 29 nodes, not 27.
5. The first scratch worktree attempt (<notes>/base_a8f01379) failed inside `git worktree add` ("fatal: Could not reset index file to revision 'HEAD'": the longest tracked path, 107 chars, under that 155-char root exceeds MAX_PATH; core.longpaths unset); git rolled it back itself (no registration in `git worktree list` or the admin dir, directory absent). The record used <notes>/b. No other side effect.
6. Workflow-prompt gate (2) "each conflicted test file alone": no test file conflicted (CLAUDE.md only), so there was nothing to run; the CLAUDE.md readers ran as gate (7). Gate (9): the rulings (RB8-10(9)) override the prompt; not run.
7. The PR body ends without the robot line: RB8-11 / the prompt say the orchestrator appends the generation trailer, and the body must be pure ASCII.
8. The rows file sha appears grouped by four in the PR body and here (the full hex has an 11-digit run that the added-line sweep would flag; the RED file's P13 shas use the same grouping).

## Questions for the gate

- None blocking. Q1: keep the two S81-06 test files in the S81-08b comm set for future rebases (they import app.main and auth_routes importers)? Measured green on both sides here.

## Worktree state at the end

`git -C sc-s81-s08b status --short`: EMPTY. HEAD 9088563f9ecf1e4b61ac01dd0d6101def59d372e on feature/s81-s08b-legacy-fingerprint-reader, not pushed. No .qa-mutation.lock. The scratch worktree <notes>/b removed (not in `git worktree list`). No orphan pytest process (scan by tag s08b-rb / path S81-08b_rebase: none).
