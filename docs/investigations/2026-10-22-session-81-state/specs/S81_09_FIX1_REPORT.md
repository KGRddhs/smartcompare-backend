# S81-09 DEVICE-QUOTA-RIYADH -- fix round 1 (PIN-FIX) report

- Agent: PIN-FIX, Opus 5.5 (claude-opus-5-5). Written THROUGH THE SHELL (compose_report.py run by the venv python; the harness refuses a subagent Write of a report .md). Rulings: specs/RULINGS_FIX1_S81_09.md (FINAL 2026-11-02 11:29, F1-1..F1-14 + the Procedure), GATE_S81_09 GC-1..GC-14 as amended, RULINGS_S81_09; read in full with s81-common.txt, both adversary reports and the GREEN report before the first command.
- Window: first tool call 11:31:50 AST, report about 11:55 AST (budget 60 min). Box idle: node -e 0 = 0.088 s.
- Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s09, branch feature/s81-s09-device-quota-riyadh.
- HEAD before: e7c81956f11749b1378aa449c4ac616c82bfe6a9 (the 13 GREEN paths STAGED, uncommitted).
- HEAD after: 990f06d85a016f3d9f7f0f64f22849c99a4ba8e8 (ONE commit through the hook, never --no-verify; nothing pushed, no PR).

## E0 (verification first)

- branch / HEAD as named; `git status --short` = exactly the 13 staged paths of <scratchpad>/S81-09_green_snapshot/SHA256SUMS.txt (each `M ` / `A `, no unstaged delta; identical to the snapshot's status.txt); `sha256sum -c SHA256SUMS.txt` in the worktree: 13/13 OK, so no mutant was left behind; the golden 02b29cc6d3a649324f71b27472ae135cc015ba39e9659b49c0306d1e249e6176 and the RED file 843a6bab0215ca5289482a13f52646d9f9bbb0d334e4e5f78a2e9b1bd6c1ddae re-hashed equal; no .qa-mutation.lock.
- Byte copies of the four edited files before any edit: <scratchpad>/S81-09_fix1/before/ (CLAUDE.md, PR_BODY.md, test_s81_s09_device_quota.py, test_s81_s09_gate_rows.py).

## Edits (sha256 over the bytes on disk; git blob ids from `git ls-files -s` before / after `git add`)

| file | before | after | change |
|---|---|---|---|
| tests/test_s81_s09_device_quota.py | 843a6bab0215ca5289482a13f52646d9f9bbb0d334e4e5f78a2e9b1bd6c1ddae (87,170 B, blob d22d28d0) | 551a3167ac54d1ef842f76d1603c05c3a7e404384f6f161bb33bc1c4fad6963f (87,175 B, blob 6d3b0dff) | E1 = EK4 (F1-1, GC-14 amended): line 831 only, `[the synthetic share-token field: value elided for the docs hook, see the unit report]`; `cmp` byte-identical to <scratchpad>/S81-09_green/gitleaks/amended/test_s81_s09_device_quota.py; LF, 0 bytes > 127; the committed blob's content sha256 = 551a3167... (git cat-file HEAD:path) |
| tests/test_s81_s09_gate_rows.py | 992e2eab6af121dd180ff6408849378066c1f3f5c9a241fcc179fdaeaada153d (11,845 B, blob 22129bde) | a8e01fcf6f22c5dee37d10ba461176c642976fd930a7c5a750c99c0fa152ba5e (18,716 B, blob 579ab1aa) | E2: four rows (below), the row map in the docstring, the imports from the RED module (its own idiom); LF, 0 bytes > 127 |
| CLAUDE.md | 7403487481d6da9bab8ce04705b240fcfd6c04f4308e9915cb546c27de30b6ac (572,322 B, blob 0208eec9) | 471e4700f56a263eefd3f71345e03e02e7d7e52775e1ffa8a737fa55197a032e (573,927 B, blob 7b252d72) | E3 (the S81-09 block, 4 lines, Edit tool on the working copy = the staged content, CRLF kept: 990 CRLF / 0 LF-only before and after; bytes > 127: 3,931 before and after, so every inserted byte is ASCII): GC-1..GC-14 cited (F1-7); the flip-window sentence per F1-7; preconditions gain (6) the referral-copy OTA (F1-10; the old (6) is now (7)); stated limits gain (12) / (13) = F1-6 (a) / (b) and (14) / (15) = F1-11 (a) / (b). `git diff --numstat` of the round: 4 / 4 lines; vs the base the file stays +9 / -2 |
| <scratchpad>/S81-09_green/PR_BODY.md | f64fc5022ffa96413451afa2f2fa007ee7028554ccd6540902f3ff78c4598032 (22,195 B) | 42a31e31bc889a1ce0b6d7d9b06c0ef2fe8308640f02d12de2831e4bac0096d7 (25,557 B, measured with python; cap 25,600) | patched IN PLACE by patch_pr_body.py (21 exact-string replacements, each asserted to match once, + the 'Commit blocked' section replaced by the EK4 section); copy at <scratchpad>/S81-09_fix1/PR_BODY.md (same sha) |

No app/ byte moved: the 7 app/ files' sha256 equal SHA256SUMS.txt before (E0) and after the round (g4_app_after.txt: 7/7 OK): image_routes 717d1e5a..., text_routes 767be445..., url_routes c0ff7eb2..., usage_routes 8645776f..., error_handler 56332100..., referral_service a928a6b6..., usage_service 570785b4...; the golden, the S05 and ST1 pin files likewise unchanged (02b29cc6..., 49d0b015..., 6380fff9...).

## The four new gate rows (tests/test_s81_s09_gate_rows.py; 20 + 4 = 24 nodes)

- test_f1_2_status_after_21_utc_reads_the_riyadh_day (F1-2, m1 / X10): quota + RIYADH ON at T2 and T3 (21:00:00Z / 21:00:30Z): the status GETs exactly the 2026-10-30 (Riyadh) account + device keys, never the 2026-10-29 (UTC) keys holding 3 / 3; the raw body literal (r19's with resets_at 2026-10-31T00:00:00+03:00).
- test_f1_3_null_tier_status_renders_the_base_body (F1-3, m2 / X07): quota ON, NULL tier: the raw /usage/status text equals the flag-OFF text of the same state (full configuration in both runs); no device-key GET, no counted_scope / resets_at / limits.device_daily.
- test_f1_4_code_2_on_an_account_only_call_is_a_bad_reply (F1-4, m3 / X01): _parse_consume_reply([2, 0, 0], False) is None and ([2, 0, 0], True) == (2, 0, 0); an account-only consume (no header bound) given reply [2, 0, 0] fails open (allowed, consumed False, no consumed_keys), ONE consume EVAL over [account key], ONE WARNING type=BadReply, and the later refund makes no EVAL (GETs only).
- test_f1_12_the_debit_stash_cannot_cross_requests (F1-12, m-QB-4 / B40; the billing lens's probe P1 form): one TestClient; request 1 under the quota flag delivers (device + account debited by the EVAL); the flag goes OFF and request 2 fails: 1 consume EVAL, 0 refund EVALs, device key 1, account daily 1, monthly 0.

## Every [pyt] line (pyt.py, .venv-qaren, one pytest process at a time; flags exported to one runner call only)

Pre-commit probes (run BEFORE the ONE commit so a red row could still be fixed; the official gates below re-ran on the committed, identical bytes):

- [pyt] tag=s09fix1-pre-gaterows start=2026-11-02 11:40:21 end=2026-11-02 11:40:25 elapsed=4s bound=600s status=OK rc=0 -- 24 passed in 3.32s; [hermeticity] sentinel checked 24 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=s09fix1-pre-mut-mf2 start=2026-11-02 11:41:28 end=2026-11-02 11:41:32 elapsed=4s bound=600s status=FAIL rc=1 -- mutant MF2 KILLED: 1 failed, 23 deselected, 11 warnings in 3.20s (test_f1_2_status_after_21_utc_reads_the_riyadh_day:failure:AssertionError)
- [pyt] tag=s09fix1-pre-mut-mf3 start=2026-11-02 11:41:32 end=2026-11-02 11:41:36 elapsed=4s bound=600s status=FAIL rc=1 -- mutant MF3 KILLED: 1 failed, 23 deselected, 11 warnings in 3.13s (test_f1_3_null_tier_status_renders_the_base_body:failure:AssertionError)
- [pyt] tag=s09fix1-pre-mut-mf4 start=2026-11-02 11:41:36 end=2026-11-02 11:41:40 elapsed=4s bound=600s status=FAIL rc=1 -- mutant MF4 KILLED: 1 failed, 23 deselected, 11 warnings in 3.08s (test_f1_4_code_2_on_an_account_only_call_is_a_bad_reply:failure:assert (2, 0, 0) is None)
- [pyt] tag=s09fix1-pre-mut-mf12 start=2026-11-02 11:41:40 end=2026-11-02 11:41:44 elapsed=4s bound=600s status=FAIL rc=1 -- mutant MF12 KILLED: 1 failed, 23 deselected, 11 warnings in 3.15s (test_f1_12_the_debit_stash_cannot_cross_requests:failure:AssertionError)

G1 (after the commit):

- [pyt] tag=s09fix1-unit-off start=2026-11-02 11:45:44 end=2026-11-02 11:45:48 elapsed=4s bound=600s status=OK rc=0 -- 193 passed, 11 warnings in 3.44s; [hermeticity] sentinel checked 193 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=s09fix1-unit-on start=2026-11-02 11:45:48 end=2026-11-02 11:45:52 elapsed=4s bound=600s status=OK rc=0 -- 193 passed, 11 warnings in 3.46s; [hermeticity] sentinel checked 193 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=s09fix1-gaterows-off start=2026-11-02 11:45:52 end=2026-11-02 11:45:56 elapsed=3s bound=600s status=OK rc=0 -- 24 passed, 10 warnings in 2.65s; [hermeticity] sentinel checked 24 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
- [pyt] tag=s09fix1-gaterows-on start=2026-11-02 11:45:56 end=2026-11-02 11:45:59 elapsed=3s bound=600s status=OK rc=0 -- 24 passed, 10 warnings in 2.68s; [hermeticity] sentinel checked 24 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)

(s09fix1-unit-on and s09fix1-gaterows-on exported ENABLE_DEVICE_DAILY_QUOTA=true ENABLE_RIYADH_RESET=true to that one runner call; the OFF runs had neither set. RED file 193 / 193 OFF and ON; gate rows 24 / 24 OFF and ON.)

G2 (after the commit; the four new mutants on byte copies in place under <worktree>/.qa-mutation.lock, each an exact-string edit matching once in app/services/usage_service.py (CRLF), compile-checked, its named row alone via -k, junit-classified, restored from the byte copy and sha256-verified; the lock removed):

| id | mutant | killing row | verdict | restore | [pyt] |
|---|---|---|---|---|---|
| MF2 | the quota-path status keys on the UTC day under RIYADH ON (X10 form) | test_f1_2_status_after_21_utc_reads_the_riyadh_day | KILLED (1 failed, 23 deselected, 11 warnings in 3.14s) | sha 570785b4 -> 570785b4 OK | `[pyt] tag=s09fix1-post-mut-mf2 start=2026-11-02 11:46:06 end=2026-11-02 11:46:10 elapsed=4s bound=600s status=FAIL rc=1` |
| MF3 | the quota-path status caps a NULL tier (status side of R-S09-5; X07 form) | test_f1_3_null_tier_status_renders_the_base_body | KILLED (1 failed, 23 deselected, 11 warnings in 3.16s) | sha 570785b4 -> 570785b4 OK | `[pyt] tag=s09fix1-post-mut-mf3 start=2026-11-02 11:46:10 end=2026-11-02 11:46:14 elapsed=4s bound=600s status=FAIL rc=1` |
| MF4 | _parse_consume_reply: the 'code 2 only with a device key' clause dropped (X01 form) | test_f1_4_code_2_on_an_account_only_call_is_a_bad_reply | KILLED (1 failed, 23 deselected, 11 warnings in 3.05s) | sha 570785b4 -> 570785b4 OK | `[pyt] tag=s09fix1-post-mut-mf4 start=2026-11-02 11:46:14 end=2026-11-02 11:46:18 elapsed=4s bound=600s status=FAIL rc=1` |
| MF12 | the debit stash as a process-global holder, not a ContextVar (B40 form) | test_f1_12_the_debit_stash_cannot_cross_requests | KILLED (1 failed, 23 deselected, 11 warnings in 3.17s) | sha 570785b4 -> 570785b4 OK | `[pyt] tag=s09fix1-post-mut-mf12 start=2026-11-02 11:46:18 end=2026-11-02 11:46:22 elapsed=4s bound=600s status=FAIL rc=1` |

G3 (after the commit):

- ruff 0.16.5 `check --select E9,F63,F7,F82 --no-cache` on tests/test_s81_s09_device_quota.py + tests/test_s81_s09_gate_rows.py: All checks passed (rc 0); py_compile of both: rc 0.
- [pyt] tag=s09fix1-ci-order start=2026-11-02 11:46:40 end=2026-11-02 11:47:22 elapsed=41s bound=1200s status=OK rc=0 -- 1313 passed, 345 warnings in 40.01s; [hermeticity] sentinel checked 1313 test(s); [netguard] blocked 5 attempt(s) from 4 node(s)
- [pyt] tag=s09fix1-secret start=2026-11-02 11:47:22 end=2026-11-02 11:47:27 elapsed=5s bound=600s status=OK rc=0 -- 31 passed, 1 warning in 4.15s; [hermeticity] sentinel checked 31 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)

(s09fix1-ci-order = the 25 files of <scratchpad>/S81-09_green/ci_order_files.txt, flags OFF: 1313 = 1309 + the 4 new rows, 0 failed; the netguard count equals GREEN's s09green-ci-order. s09fix1-secret = tests/test_secret_scan_static.py ALONE (GC-7, every later round) with the three new files now TRACKED: 31 passed incl. test_tracked_binaries_carry_the_magic_bytes_of_their_extension.)

G4: NO comm re-run and NO client-fence re-run (F1-14): no app/ byte moved in this round (the 7 app/ shas above, equal before and after); the fourteen fences and the comm set are re-run at the rebase.

G5: the pre-commit hook passed on the commit (`git commit` rc 0; hook output: ruff 'All checks passed!', black '1 file would be left unchanged'; the hook's gitleaks step (gitleaks 8.30.1 on PATH, `--staged --ignore-gitleaks-allow --config <HEAD:.gitleaks.toml>`) prints its report only on a refusal and the commit went through, so 0 findings; confirmed by a read-only re-scan of e7c81956..HEAD with the hook's flags and the same config: rc 0, 0 findings, gl/commit_scan.json). `git diff --name-only e7c81956...HEAD` sorted = exactly the 13 snapshot paths (names_base.txt; the gate-rows file and the RED file among them); `git status --short` EMPTY.

## Footprint (origin/main = 6c14ac954f601902d322547de04982033aca5925; merge-base = e7c81956)

```
CLAUDE.md
app/api/image_routes.py
app/api/text_routes.py
app/api/url_routes.py
app/api/usage_routes.py
app/middleware/error_handler.py
app/services/referral_service.py
app/services/usage_service.py
tests/fixtures/s81_s09_flag_off_golden.json
tests/test_s81_s05_request_context.py
tests/test_s81_s09_device_quota.py
tests/test_s81_s09_gate_rows.py
tests/test_s81_st1_usage_path_offloop.py
```

= exactly the 13 paths of SHA256SUMS.txt (diff against snapshot_names.txt: empty); this round adds no file. `git diff --check origin/main...HEAD`: clean (rc 0). `git diff --stat origin/main...HEAD`:

```
 CLAUDE.md                                   |   11 +-
 app/api/image_routes.py                     |    5 +-
 app/api/text_routes.py                      |   17 +-
 app/api/url_routes.py                       |    7 +-
 app/api/usage_routes.py                     |   17 +-
 app/middleware/error_handler.py             |   29 +
 app/services/referral_service.py            |   44 +-
 app/services/usage_service.py               |  490 ++++++-
 tests/fixtures/s81_s09_flag_off_golden.json |  722 ++++++++++
 tests/test_s81_s05_request_context.py       |   31 +-
 tests/test_s81_s09_device_quota.py          | 2068 +++++++++++++++++++++++++++
 tests/test_s81_s09_gate_rows.py             |  389 +++++
 tests/test_s81_st1_usage_path_offloop.py    |   22 +-
 13 files changed, 3815 insertions(+), 37 deletions(-)
```

No whole-file diff (CLAUDE.md +9 / -2 as at GREEN; every app/ file's numstat as at GREEN; the gate-rows file +389 / -0 as a new file).

## PR body patch summary (<scratchpad>/S81-09_green/PR_BODY.md, in place; copy in S81-09_fix1/)

- size / sha256: 22,195 B f64fc502... -> 25,557 B 42a31e31... (<= 25,600, measured with python).
- HEAD = 990f06d85a016f3d9f7f0f64f22849c99a4ba8e8 (base e7c81956; the rebase onto the current main follows in its own round); both adversary verdicts (SOUND, 0 / 0, 10 + 5 minors) and RULINGS_FIX1_S81_09 cited; GC-1..GC-14.
- the EK4 statement with both blob sha256 values (843a6bab... 87,170 B -> 551a3167... 87,175 B) and the commit's hook / gitleaks result, replacing the 'Commit blocked' section.
- the E-rows heading: E1 + E2 + E3 = exactly 8 nodes, as both adversaries measured (the quota-and-billing re-measure s09adv-qb-erows: 8 failed, 699 passed); the E3 reason reworded per F1-8 (GC-13 as applied, header_state allowed for usage_service.py only, the reason r22).
- the files table (CLAUDE.md 471e4700..., the RED file 551a3167... (EK4), the gate rows +389 / a8e01fcf...); the node map (24 gate rows; f1_2, f1_3, f1_4, f1_12 placed on their requirement rows).
- the flip-window sentence (F1-7) on the ENABLE_RIYADH_RESET bullet; the stated limits gain 12-15 (F1-6 a / b, F1-11 a / b) and 16 (F1-5: X03 equivalent); limit 7 and the flip order gain the referral-copy OTA (F1-10, the new step 6; the old 6 is 7).
- the secret-scan node stated MEASURED by the quota-and-billing adversary (F1-13: s09adv-qb-secret, 31 passed) and re-run at HEAD (s09fix1-secret); a 'Fix round 1 gates' section (G1-G4 counts); the GC-13 deviation bullet marked ruled (GC-14 (a), F1-8).
- bytes > 127: only the 4 bytes of the mandated attribution trailer's emoji (kept: 'keep every other byte'); every inserted byte is ASCII.

## Deviations

1. The worktree line of the task says `git status --short` EMPTY before anything; E0 and the Procedure say exactly the 13 staged paths. Observed: the 13 staged paths (as E0 requires); proceeded on E0.
2. Pre-commit probes: the gate-rows file once (24 passed) and the four mutants once (4/4 KILLED, restores verified, lock removed) BEFORE the commit, because the ONE-commit rule leaves no way to fix a red row after it; the official G1 / G2 ran after the commit on byte-identical files.
3. The commit message = the given subject + GREEN's prepared body (<scratchpad>/S81-09_green/commit_msg_body.txt) + one fix-round paragraph + the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` (this agent's model). Message file: <scratchpad>/S81-09_fix1/commit_msg.txt.
4. tests/test_secret_scan_static.py was also run alone at HEAD (GC-7: 'every later round'; not in the task's G-list): 31 passed. A read-only gitleaks re-scan of e7c81956..HEAD was added as positive evidence for G5.
5. The PR body was patched in place at S81-09_green/PR_BODY.md (the task's PR BODY section) AND copied to S81-09_fix1/PR_BODY.md (the Procedure's 'under <scratchpad>/S81-09_fix1/'); same bytes. The git blob ids (d22d28d0 -> 6d3b0dff) are in this report only (the PR body carries the sha256 values; size).
6. CLAUDE.md: the F1-10 precondition went in as (6) and the old (6) became (7); the owner-steps line was left unchanged (F1-10 names the preconditions only).
7. py_compile wrote __pycache__ (gitignored; `git status --short` stays empty).

## NOT MEASURED

- The comm set and the fourteen client fences at HEAD (F1-14: not re-run, no app/ byte moved; the rebase round recomputes them at the moved main with a fresh base record, LC-6).
- The FULL jest suite (LC-7: once, in the last round before the PR).
- The Lua scripts on a real Redis / Upstash (no Lua runtime on the box; the canary is the first execution).
- The hook test files tests/test_precommit_hook*.py (no .githooks change).

## Added-line sweep

This round's added lines (143: gate rows 138, CLAUDE.md 4, the RED file 1; round_added_*.txt) swept for @gmail, +973, a standalone 8-digit run, sk- / AKIA / xox / eyJ / PEM / credentialed-URL shapes: 0 hits. Synthetic values only (the RED module's constants).

## git status --short (worktree, at the end)

```
(empty)
```

## Paths

- Notes / logs / scripts: C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_fix1/ (notes.md, before/, mutate_fix1.py, mut/, mut_results_pre.json, mut_results_post.json, run_gates.py, gates_g1.json, gates_g3.json, *.log, patch_pr_body.py, PR_BODY.md, commit_msg.txt, commit.out, gl/, names_base.txt, footprint_names.txt, g4_app_after.txt, final_shas.txt)
- PR body: C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_green/PR_BODY.md (copy C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_fix1/PR_BODY.md)
- This report: C:/Users/SYNACK~1/AppData/Local/Temp/claude/C--Users-SynAckITPC-Documents-AI/fe82d828-54b9-4af1-9c1d-685173488382/scratchpad/S81-09_fix1/PINFIX_REPORT.md
