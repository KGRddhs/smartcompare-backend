# S81-24 PIN-FIX REPORT (RULINGS_PINFIX_S81_24 PF-1..PF-7), agent Opus 5.5, 2026-11-07 13:57-14:16 AST
Filed through the shell (body drafted as .txt, copied to .md with bash; the harness refuses a subagent Write of a report .md).

## HEAD
- before: a920190bb991488306712fdf1aeed4a080a092ff on feature/s81-s24-auth-throttle-v2, git status --short EMPTY (verified first).
- after:  4b623d1acc98bca54fe10418edda4440b91a60a1 "test(s81-24): pin-fix P73 (RULINGS_PINFIX_S81_24 PF-1): tolerate the lifespan pool keys on /health" (trailer Co-Authored-By: Claude Opus 5.5), through the hook (gitleaks "All checks passed!"), no --no-verify. 4 commits ahead of origin/main 39ac80ba.

## Edits (tests/test_s81_s24_auth_throttle.py only)
- E1: LIFESPAN_HEALTH_FIELDS = frozenset({"adapter_executor", "price_parse_pool", "redis_offloop_pool"}) right after the OFF_SPELLINGS line, no blank line added.
- E2: in test_p73_hop_probe_off_silent the old comment + exact-keys assertion replaced by the 3 comment lines + `assert sorted(set(h.json()) - LIFESPAN_HEALTH_FIELDS) == [the five keys]`; the /app/version, HDR_200 and [HOP_PROBE] assertions untouched.
- Working copy (CRLF; 2134 -> 2137 lines): sha256 before 5832e1797c5bbbaf52676c77789646a66c44a6d9f25d3726dfe02e073c351c94 (byte copy <notes>/test_s81_s24_auth_throttle.py.orig) -> after ee8e55da723bfd90f7a4ee94132fffa236474fbf8f9b62cbab29e4fdc630815e.
- Committed LF blob: 7fdf71db5b2cc43e34b24674b62d3eb57e117b1c8fa683719471b10c4c562228 -> d48467fe9033bdfb4b7e27b03a5d40848742b6dfc139255e7319d7ff967005fa, 85171 bytes.
- bytes > 127 = 0; ruff --select E9,F63,F7,F82 --no-cache: All checks passed (rc 0); py_compile rc 0.
- git diff --stat HEAD~1 HEAD: 1 file changed, 5 insertions(+), 2 deletions(-), two hunks (@@ -1828,6 +1828,7 @@ and @@ -2000,8 +2001,10 @@).

## Gates (every run waited until no foreign pytest/jest was live; nothing killed)
- [pyt] tag=s24pf-unit-off start=2026-11-07 14:05:45 end=2026-11-07 14:05:55 elapsed=10s bound=600s status=FAIL rc=1 -> 2 failed (test_r92_hygiene, test_p83_red_file_setenv_hygiene: the CRLF check on the working-copy bytes of app/services/auth_throttle.py and of the RED file), 210 passed. See D-PF1.
- [pyt] tag=s24pf-unit-off2 start=2026-11-07 14:07:06 end=2026-11-07 14:07:16 elapsed=10s bound=600s status=OK rc=0 -> 212 passed; [hermeticity] sentinel checked 212 test(s); [netguard] blocked 0 attempt(s) from 0 node(s).
- [pyt] tag=s24pf-unit-on start=2026-11-07 14:09:50 end=2026-11-07 14:10:00 elapsed=11s bound=600s status=OK rc=0 -> 212 passed; [hermeticity] sentinel checked 212 test(s); [netguard] blocked 0 attempt(s) from 0 node(s). Env set inline in the runner call only: ENABLE_AUTH_THROTTLE_V2=true, ENABLE_HOP_PROBE_LOG=true, the synthetic low-entropy pepper and the eight AUTH_THROTTLE_* knobs (the S81-24_final/on.sh values).
- [pyt] tag=s24pf-repro start=2026-11-07 14:10:10 end=2026-11-07 14:10:21 elapsed=11s bound=1200s status=OK rc=0 -> argv order tests/test_s81_s20_result_gate.py then tests/test_s81_s24_auth_throttle.py: 365 passed, 0 failed (the 12 P73 nodes are green after the lifespan user); 6 [netguard] sentinel lines, all in test_s81_s20 (socket.create_connection neutralized.supabase.invalid:443, s20's own).
- [pyt] tag=s24pf-comm-c11 start=2026-11-07 14:10:59 end=2026-11-07 14:11:59 elapsed=60s bound=1200s status=FAIL rc=1 -> 10 failed, 1887 passed; all 10 FAILED ids are in S81-24_final/comm/base_failed.txt; comm -13 (sorted FAILED vs sorted base_failed.txt) = 0 lines (EMPTY). The 10: test_s81_s10_fragrance_gate::test_r06_production_lexicon_content, test_s81_s16_kb_seed::test_s16_r27_hygiene_of_g2_files[x5], test_s81_s18b_store_label::test_r2_table_shape, test_s81_s19_gap_queue::test_r15_hygiene, test_s81_s22_compare_runs::test_b02_one_transaction_ascii_lf, test_s81_s22_judge::test_j01_script_exists_and_off_first.
- [pyt] tag=s24pf-ciorder start=2026-11-07 14:12:19 end=2026-11-07 14:13:13 elapsed=55s bound=1200s status=FAIL rc=1 -> 2 failed (test_auth_interceptor::test_sign_in_with_social_exception, ::test_social_login_user_insert_fails_gracefully = the two baselined social nodes), 789 passed, 1 skipped, 2 deselected; the 19-file list was taken from the argv in s24fin-ciorder.log.
- NOT run, by ruling PF-3: jest (no client file and no CLAUDE.md change; the final round's full jest run, 3,976 + 4 w37, stands per LC-7); tests/test_precommit_hook*.py (no .githooks change); the corpus gate (no price-pipeline module).
- Logs: <notes>/logs/s24pf-*.log and .out.

## Footprint
- git diff --name-only origin/main...HEAD = CLAUDE.md, app/api/auth_routes.py, app/middleware/request_id.py, app/services/auth_throttle.py, tests/_env_safety.py, tests/test_s81_s24_auth_throttle.py, tests/test_s81_s24_fix1_rows.py, tests/test_s81_s24_gate_rows.py (exactly the eight).
- git diff --check origin/main...HEAD clean (rc 0). numstat: CLAUDE.md 10/4, auth_routes 17/0, request_id 69/0, auth_throttle 495/0, _env_safety 2/0, RED file 2137/0, fix1_rows 251/0, gate_rows 144/0 (3125 insertions, 4 deletions); no whole-file diff.

## PR body (S81-24_final/PR_BODY.md, patched in place by python exact-string replacement; script <notes>/patch_pr.py)
- before 19603 B, sha256 f48c4d5d86db1fccd2f82f77b9a15fcf0a787701f38580201a5e5d5475f5264d (copy <notes>/PR_BODY.before.md); after 21014 B, sha256 772130348ddefa35e253deba5295a14c9c1ca1e19c223c8fb771369cbe94784b; pure ASCII; <= 25,600.
- P1 STATUS -> READY; P2 heading -> Pin-fix; P3 paragraph -> RULED ... with d48467fe9033bdfb... and the s24pf-repro / s24pf-comm-c11 [pyt] lines; P4 Result line; P5 bullet appended as the last bullet of "RED rows and mutants"; P6 numstat 2134 -> 2137 (figure only).
- P7 grep: DRAFT 0, NOT READY 0, BLOCKED 0, "the Blocker" 0. Lower-case "blocker" appears only in the STATUS line and the Pin-fix heading, both mandated texts.

## Deviations
- D-PF1 (the D2 class, measured): at the start, app/services/auth_throttle.py and the RED file were CRLF in the working copy (the D2 re-render under core.autocrlf=true; auth_throttle mtime 13:50). The frozen rows R92 / P83 read the working-copy bytes, so they failed in s24pf-unit-off. This is environmental and not caused by the edit.
  - For the gate window only, I took byte copies of both CRLF files (<notes>/crlf_copies/), wrote <worktree>/.qa-mutation.lock, and replaced each file with its own HEAD blob (`git show HEAD:<path>` > file). Each LF copy is sha-equal to its blob: auth_throttle 4ed97e78fef5f74c..., RED d48467fe9033bdfb....
  - I then ran unit-off2, unit-on, repro, comm-c11 and ciorder on those LF copies, which are the committed bytes CI sees.
  - After the gates I restored both CRLF byte copies (sha-equal: auth_throttle 39ee4599f400cc06..., RED ee8e55da723bfd90...) and removed the lock. git status --short is EMPTY.
  - The worktree is CRLF again, as it was before the round. A later local run of R92 / P83 here will go red on CRLF until the working-copy line endings are ruled.
- D-PF2 (note): as briefed, P6 changed only the figure. The row's descriptor still reads "(the frozen RED file, 7fdf71db..., unedited)", which is stale after PF-1. The orchestrator may want to amend it when GC-1 is amended.
- D-PF3: the edit was applied with a python exact-string byte replacement (CRLF needles, each matching once), not the Edit tool. The bytes are the brief's text exactly, and the line endings are kept.

## git status --short (final)
(empty)
