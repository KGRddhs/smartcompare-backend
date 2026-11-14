# S95-LG URL-WINNER-GUARD: FIX-1 report (Opus 5.5, 2026-11-14)

VERDICT: COMMITTED. HEAD baf675841b3070a85faf1e90e0a0dd4957392a42 on feature/s95-url-winner-guard (parent 731bcddf531a7e123963246168ca19f262859337); one commit, five paths, through the hook, no push.
Time: first tool call 21:12, commit 21:16:22, report 21:18 (local). Notes: this folder (notes.md and every log / out file).
Read in full at the start and again before this report: GATE_S95_LG.md (GL-1..GL-8 + ADDENDUM 1 GL-9..GL-11), S95_LG_UNIT_SPEC.md, red/S95_LG_RED_REPORT.md, green/S95_LG_GREEN_REPORT.md, s81-common.txt.

## 1. Start state (verified before any write; verify_start.py)
- git rev-parse HEAD = 731bcddf531a7e123963246168ca19f262859337; branch feature/s95-url-winner-guard; no .qa-mutation.lock.
- git status --short = ` M CLAUDE.md`, ` M app/services/url_extraction_service.py`, ` M tests/test_s81_s07c_role_fix.py`, `?? tests/test_s95_lg_url_winner_guard.py`, `?? tests/test_s95_lg_url_winner_guard_adapter.py` (exactly the three + two); numstat 10/0, 75/1, 71/4.
- RED file sha256 7b6aec460c27b91ea832694287e72a0ef4302b7731770248e90b717e401cb537 (match); adapter d5b801985f0219e96a72ec0c218ea1274d84116e0c0d686e6f6d0295c97d59a4 (match).
- url_extraction_service.py sha256 8eca4929628cf8e9b6513d53bfb43d20fd3470461e49d6b579345b6787a6c27d, 75965 bytes, CRLF 1643, bare LF 0: BYTE-EQUAL to green/green_ues.py (GREEN's copy of the final module; the GREEN report section 11 sha).
- role_fix 3a67f214... (36564 B, CRLF) and CLAUDE.md 7110ee48... (789030 B, CRLF 1156, bare LF 0) = the GREEN report section 11 values.
- Non-ASCII: the module 18 bytes = base_ues.py 18; CLAUDE.md 3904 = base_CLAUDE.md 3904 (no added non-ASCII byte).

## 2. GL-9 (the ruled pin-fix of RED G2; gl9_copy.py -> gl9_copy.out)
- Byte copy of the frozen RED bytes first: fix1/red_frozen_copy.py (sha 7b6aec46... match).
- shutil.copyfile(green/red_g2_pinfix_candidate.py -> W/tests/test_s95_lg_url_winner_guard.py).
- New RED sha256 24ed90c0278482bc0296b2cdf825c3be5a3542400efaaecfe3e9140868746027 (starts 24ed90c0278482bc: yes), 19693 bytes, LF only (0 CR), 0 non-ASCII; 475 lines before and after.
- Diff against the frozen bytes: exactly ONE line, :207 (fix1/gl9.diff, 589 bytes, sha256 c3396f394cb79603fc8ff3dfb9a4b7514b38186cd2a302d18e2d9938c5dcb44c, byte-equal to green/red_g2_pinfix_candidate.diff):
  - old: `    result = service.compute_scores(copy.deepcopy(products))`
  - new: `    result = service.compute_scores([dict(p, rating=p["reviews"]["rating"], review_count=p["reviews"]["count"]) for p in copy.deepcopy(products)])`
- ruff 0.16.5 --select E9,F63,F7,F82 --no-cache on the pin-fixed RED file: All checks passed; py_compile rc 0.

## 3. GL-10 (waitfree.ps1 -OwnTagPrefix s95g- before each pytest)
- waitfree: 21:13:37 busy (a foreign lane's pyt.py / pytest on tests/test_inc_i1_...; not touched), `free poll=1 21:14:08`.
- [pyt] tag=s95g-fix1-red start=2026-11-14 21:14:29 end=2026-11-14 21:14:32 elapsed=3s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\fix1\red.log
  - [hermeticity] sentinel checked 24 test(s) / [netguard] blocked 0 attempt(s) from 0 node(s) / 24 passed in 2.31s (RED 22 + adapter 2)
- waitfree: `free poll=0 21:14:41`.
- [pyt] tag=s95g-fix1-rolefix start=2026-11-14 21:14:46 end=2026-11-14 21:14:52 elapsed=5s bound=600s status=OK rc=0 log=C:\Users\SYNACK~1\AppData\Local\Temp\claude\cde30765822f13ce\1747a1ff-764f-4854-8a50-4573c5c07f43\scratchpad\s95lg\fix1\rolefix.log
  - [hermeticity] sentinel checked 17 test(s) / [netguard] blocked 0 attempt(s) from 0 node(s) / 17 passed, 15 warnings in 4.35s (the same 15 DeprecationWarnings as green/rolefix_green.log)
- The comm set NOT re-run (GL-10: no module byte moved after GREEN's comm run; the pin-fix touches only the RED file, which is not a comm member).

## 4. GL-7 (the ONE commit)
- Pre-stage: the five working-copy sha256 re-checked = section 5; the added-line sweep (sweep.py -> sweep.out; its ten patterns self-tested live on run-time probes): 843 added lines, 0 non-ASCII bytes, 0 hits (@gmail, +973, 8-digit runs, sk- / AKIA / xox / eyJ / PRIVATE KEY / credentialed URL / email shapes). core.hooksPath = .githooks; core.autocrlf = true; none of the five paths is on .github/black-clean-paths.txt.
- `git -C $W add -- <the five paths by name>` rc 0 (two informational warnings: LF will be replaced by CRLF the next time Git touches the two LF test files); staged numstat CLAUDE.md 10/0, app/services/url_extraction_service.py 75/1, tests/test_s81_s07c_role_fix.py 71/4, tests/test_s95_lg_url_winner_guard.py 474/0, tests/test_s95_lg_url_winner_guard_adapter.py 211/0.
- `git -C $W commit -F fix1/commit_msg.txt` (441 bytes, ASCII, LF; never --no-verify) 21:16:20-21:16:22, rc 0. Hook output, verbatim (commit_hook.out):
  - `All checks passed!`
  - `[feature/s95-url-winner-guard baf67584] feat(s95): ENABLE_URL_WINNER_GUARD gives link compares the scorer's winner and the prose reconcile (dark)`
  - ` 5 files changed, 841 insertions(+), 5 deletions(-)` / ` create mode 100644 tests/test_s95_lg_url_winner_guard.py` / ` create mode 100644 tests/test_s95_lg_url_winner_guard_adapter.py`
- Message (git log -1 --format=%B): the GL-7 subject exactly; body 4 lines: `Link compares under the flag get the deterministic scorer on rating-lifted` / `copies, the scores summary and the scorer winner in the verdict prompt, and` / `the prose reconcile after a delivered verdict. OFF is byte-identical.` / `E1 re-pins the S81-07c V09 pin; the RED files guard it.`; trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Verified after: HEAD moved 731bcddf -> baf675841b3070a85faf1e90e0a0dd4957392a42 (parent 731bcddf531a7e123963246168ca19f262859337); `git status --short` EMPTY; `git show --stat HEAD` = exactly the five paths (CLAUDE.md +10; ues 76 = +75/-1; role_fix 75 = +71/-4; RED +474; adapter +211; 841 / 5); no upstream (status -sb `## feature/s95-url-winner-guard`), nothing pushed.

## 5. The five committed paths
| path | working-copy bytes | working-copy sha256 | HEAD blob |
|---|---|---|---|
| app/services/url_extraction_service.py | 75965 (CRLF) | 8eca4929628cf8e9b6513d53bfb43d20fd3470461e49d6b579345b6787a6c27d | cb217967764570857fa3ac3e1a6923ad3cbf4ec0 |
| tests/test_s95_lg_url_winner_guard.py | 19693 (LF) | 24ed90c0278482bc0296b2cdf825c3be5a3542400efaaecfe3e9140868746027 | e25c5596eeba4dac13b0cbcb1d45651114b78fad |
| tests/test_s95_lg_url_winner_guard_adapter.py | 9096 (LF) | d5b801985f0219e96a72ec0c218ea1274d84116e0c0d686e6f6d0295c97d59a4 | 159dcd400905ea45cc3ad943cb76980ac3c0d057 |
| tests/test_s81_s07c_role_fix.py | 36564 (CRLF) | 3a67f2140125303b788a813fac6eb915010ed5ed1b6a2a60c46e5f7b006671d2 | c34925fb14d3e5bece61a5473511008ceaad239b |
| CLAUDE.md | 789030 (CRLF) | 7110ee480f53d7668ef1cc4cd3b35b8a90264f413728721f5e13bf3daebd0256 | 61ff73c2d8f3fd78f87d6081b202f5849170723d |
- The four non-RED blobs equal the GREEN report section 11 would-be blobs; the RED blob: git hash-object of the working file = e25c5596..., and sha256 of `git show HEAD:tests/test_s95_lg_url_winner_guard.py` = 24ed90c0... (19693 bytes), its :207 = the GL-9 line.

## 6. Deviations
- None from the procedure. Extra cheap checks, stated: ruff + py_compile on the pin-fixed RED file; the added-line sweep with a pattern self-test; a check that no path is on the black allowlist.
- GL-10 ran as two runner calls (the two RED files together; the role-fix file alone), each after its own waitfree.ps1.
- No mutation was run, so no .qa-mutation.lock was created; the frozen RED bytes were byte-copied (fix1/red_frozen_copy.py, sha 7b6aec46...) before the GL-9 copy.

## 7. NOT MEASURED (by this round)
- The pin-fixed RED file at the BASE module bytes (GREEN measured it: 15 assertion failures + 9 passes across the two RED files, GL-9); not re-measured here.
- The comm set (GL-10: not re-run); the client jest fences (no client-read literal moved); the full jest suite (backend unit); no live, network, Railway or provider measurement.

## 8. git -C W status --short (end)
(empty) - HEAD baf675841b3070a85faf1e90e0a0dd4957392a42, branch feature/s95-url-winner-guard, no lock file.
