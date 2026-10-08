# adv5 notes (final adversary round 5, T0b Phase B)
start 2026-10-07 21:06:22 AST; budget 90 min -> 22:36
## start hashes: 9/9 equal to the fix report files_changed (hook 4e9a583c, ci 05c4ff90, r2 test a9383736, rest = snapshot). HEAD 845ece15. git status = the 9 paths.
## tools: sh=/usr/bin/sh (MSYS bash), dash, gawk 5.3.2, GNU grep 3.0, gitleaks 8.30.1 (WinGet), node -e 0 = 0.3 s (healthy)
## LF copies: hook.lf (691 lines; sh -n 0, dash -n 0), base.lf (405 lines, git show 845ece15)
## read: rules file, round-3 rulings TBF10-20, the hook in full, the ci.yml secret-scan job, the round-2 test diff vs the fix-2 snapshot
## 21:13 additivity harness (adv5.py: imports round-4 adv.py scenarios read-only; 42 not-run first, then 30 new backstop scenarios, then the 29) started bg, 3 workers. Box: new hook 8.8 s alone, base 4.2 s (another workflow s73-u8-green running, cpu 65%).
## 21:17 own mutants: mut5.py, 19 mutants on round-3 lines (byte copy, line-checked edit, pyt -k, restore, sha). First launch died on argv bug before touching the hook (sha 4e9a583c verified); relaunched 21:18.
## 21:20 adv5b part1 (shims, xtrace, signals) bg.
## analysis: final grep -qE of each backstop block has no LC_ALL=C (only the 4 upstream stages do); NUL->LF drops the '+' of a segment after a NUL on the same diff line (dead-awk only; base also blind there).
## no hook test anywhere pins 'a commit that DELETES a credential line passes' (grep -i remov/delet in the 4 hook files: only pin_315_deleted_binary_passes).
## 21:30 mutant run 1 was too slow under load (~55 s/node). Killed its tree (taskkill /T) mid bs1_fail_to_echo; hook was at mutant 15a9c9a0 -> restored from hook.bak (shutil), sha 4e9a583c verified. Void: bs1_fail_to_echo run 1. Kept: bs1_removed, bs2_removed, bs_both_removed, probe_gate_restored = KILLED (pyt lines in mut5.jsonl).
## 21:37 mutant run 2 (MUT_SH_ONLY=1, 7 killed-expected mutants, one sh node each); survivors replayed on LF copies (lfmut.py), never the worktree.
## 21:44 additivity 60/101 streamed: 0 violations; dead-awk gap: da_textattr_nul_same_line_akia base 0 new 0 (NUL->LF loses '+' of the after-NUL segment; working awk refuses).
## shims: err0/rc1report/rc1empty/rc2 refuse, infwrn0 pass, colorerr0/errstdout0 pass (stated limit TBF1); config: HEAD none -> default-only, HEAD unit -> HEAD copy, hostile wt ignored; hostile GITLEAKS_CONFIG(_TOML) blanked in the gitleaks child env.
## TBF5(b) interaction: the pre-authorised mawk fix `tr -d '\000'` at the views is the m3 shape the round-3 rationale rejected (joins UTF-16 -> i315 message changes).
## 22:02 own mutants via pyt -k: KILLED bs1_removed, bs2_removed, bs_both_removed, probe_gate_restored, bs1_fail_to_echo, bs1_akia_dropped, bs1_pk_dropped (2nd try; 1st = 120 s per-test Timeout under load, void), bs2_jwt_dropped (2nd try; same), bs_messages_swapped, bs1_q_dropped (key piece printed), bs2_q_dropped (JWT piece printed). Every restore sha 4e9a583c.
## LF replays (lfmut): m4 / m1 / m2 killing designs confirmed (base 0, cur 1, mut 0). bs1_sk_dropped and bs1_xox_dropped: base 1, cur 1, mut 0 -> an ADDITIVITY regression no node catches (dead-awk node inventory = AKIA, JWT, PK header only). bs2_credurl_dropped: base 0 cur 1 mut 0.
## pipefail probe: SHELLOPTS=pipefail + 120k-line file with AKIA on line 1: base 0 / new 0 (sh=bash imports SHELLOPTS); small diff 1/1. Pre-existing, same in base; the backstop is not immune.
## signals TERM/HUP during gitleaks (sh, dash): rc 143/129, no temp dir left. xtrace: no .env value, no staged AKIA in trace; binary head 12 bytes in trace (F6, TBF17).
## CI replay (step text under bash -e -o pipefail, real 8.30.1): pr_clean 0; pr_ghp 1; noisy textconv 1 (plain ' ERR ', no ANSI); pr_base_missing 1 before scan; push_ghp 1; head-widened config 1 (base config used). No sentinel in output.
## real hook: hostile wt config ignored (github-pat refused sh+dash); gitleaks:allow ignored (refused); .gitleaksignore refused.
## 22:13 bs1_sk_dropped vs (b3_ or f1_) and not dash: [pyt] status=TIMEOUT rc=124 at 605 s (13 nodes, load) -> NOT MEASURED by pytest; restore 4e9a583c verified; no pytest left. Survival rests on the node inventory + LF replay.
## 22:15 additivity complete: 101 scenarios (71 defined + 30 new), 0 violations, 0 shell diffs, 0 leaks, 0 temp leftovers; 27 new refusals, all ruled classes or backstop new-only.
## real: docs checkpoint (s72 specs + SHA256SUMS) HEAD unit 0/0; HEAD none 1 (generic-api-key in t0b_b_ref/gitleaks_narrowed.toml:56, TBF20 ordering covers it). Unit nine files HEAD none: 0 (sh, with pyproject.toml; first try refused by ruff for a missing pyproject.toml in the scratch repo = harness artifact).
## eslint: 70 files -> 64+6; 129 -> 64+64+1; 1 partial -> stdin; 12/11 partial -> NOTE + by-path; 70 with 3 partial -> 64+3 by path, 3 stdin. All rc 0.
