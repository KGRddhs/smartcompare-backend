# S81-12 MERGE ROUND evidence (RULINGS_REBASE2_S81_12) -- BLOCKED at RB2-7 (3) / RB2-4 (c)

Worktree sc-s81-s12, branch feature/s81-legal-v3. HEAD before e8c8c1dc488a5547a874ccffb7dbd8a96ec7965c, status clean, node_modules junction live (untouched).

## RB2-1
git fetch origin main -> origin/main = 6b909e0a92067d6b3562eee325e4956c116441f7 (as expected).
git merge --no-ff --no-commit origin/main: CONFLICT only CLAUDE.md; auto-merged SmartCompareApp/src/i18n/ar.json, en.json, app/legal/processors.json, tests/fixtures/legal_s78.json, tests/test_s81_s06_anthropic_router.py. One conflict hunk (markers at working-copy lines 531/533/643: ours 1 line, theirs 109 lines).

## RB2-2
Union built by union.py from git bytes: theirs = contiguous slice of `git show origin/main:CLAUDE.md` (line index 530, unique), ours = slice of `git show e8c8c1dc:CLAUDE.md` (index 530, unique); both followed by '' and '## Tests'. Layout: main's 109 lines, one empty line, the S81-12 row. CRLF kept in the working copy.
`git show :CLAUDE.md` sha256 c92a650becf2531035c282fcd315a373d9bfcebde87707e4d8a9dbf900e5946e, 744,110 bytes, 1,105 lines = the ruled value; equal to claude_md_union_expected.txt (compared after building). No conflict marker; `git diff --cached --check` clean.

## RB2-3
Merge commit 6c71a5fa0e53aba81e750feed1239341acda19de through the hook (rc 0; hook output: eslint 0 errors / 90 warnings). Parents e8c8c1dc488a5547a874ccffb7dbd8a96ec7965c 6b909e0a92067d6b3562eee325e4956c116441f7. `git diff --name-only origin/main...HEAD` = 45 files, identical to footprint45.txt. HEAD:CLAUDE.md sha256 c92a650b... (= RB2-2).

## RB2-7 merge-agent gates before the round commit
(1) frozen blobs byte-identical to e8c8c1dc:
- tests/test_s81_12_legal_v3.py 9163cfcb01e4d15fab1e799743a6998ebf6760982fa846611a81f223dcd3c2a6
- SmartCompareApp/__tests__/s81_12/legalV3.s81_12.test.ts f8f21f89a9bfac2fb9a02d00f4c59171177c2f1dec385cfcb7e432b8a6528646
- tests/test_s81_12_gate_rows.py b98caa6aebff37eea7ad4c8078cad55e9fde3538c261da4d9609f56b52c10436
RB2-6 `git diff --quiet e8c8c1dc HEAD -- <17 paths>` rc 0; aiConsent.body, onboarding.s5.privacy_anon_head, onboarding.s5.privacy_anon_body EN + AR byte-equal to e8c8c1dc.
(2) tsc 5.9.3 --noEmit: [tsc] tag=s12m-tsc start=21:07:01 end=21:07:09 rc=0, 0 errors. eslint v9.39.4 on the 13 unit client files: [eslint] tag=s12m-eslint start=21:07:17 end=21:07:27 rc=0 (0 errors, 3 warnings).
(3) unit file + gate rows:
[pyt] tag=s12m-unit-pre start=2026-11-11 21:07:39 end=2026-11-11 21:07:43 elapsed=4s bound=600s status=FAIL rc=1
3 failed, 57 passed; [hermeticity] sentinel checked 60 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
FAILED tests/test_s81_12_legal_v3.py::test_r9_manifest_anthropic_row_public_and_named   <-- NOT EXPECTED
FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded (by design)
FAILED tests/test_s81_12_legal_v3.py::test_p3_i18n_key_sets_equal_and_unchanged (expected before EK4: 1011 keys, sha 2d351a2c1fb2)
Gate rows: 22 / 22 passed (57 passed = 35 unit + 22 gate rows).

R9 traceback head (tests/test_s81_12_legal_v3.py:717):
  AssertionError: R9: the anthropic processors row:
      - the openai row changed (OpenAI stays a transition processor, R-S12-1)
Only that one problem: the anthropic row (public_name, hosts, names in both policies, PUBLIC_NAME_IDS) passes.
Cause: main's #398 S81-G10 (commit aed1393b) deleted "app/services/verdict_critique_service.py" from the openai row's modules list in app/legal/processors.json (the hunk at line 64; auto-merged here). R9 pins the openai row by BASE_OPENAI_ROW_SHA256 (tests/test_s81_12_legal_v3.py:224, sha256 of json.dumps(row, sort_keys=True, ensure_ascii=True)):
  6c14ac95 / e8c8c1dc: c7453e562284c96555331424f44dd6d400d72e25bf6b4fb0d31a9db9d00a1287 (= the pinned value)
  6b909e0a / merge HEAD: c67cb8088079d6afe8f1146530b41f6801d618cd7d6d79798b72b9762caa0320
Base result of the node at 6b909e0a: the node does not exist on main (tests/test_s81_12_legal_v3.py is a branch-only file), so no base run is possible; the cause is main's own processors.json bytes.
Classification: the pin sits in this unit's OWN frozen RED file, not a merged row outside the footprint; it is neither CLASS V (consent digit / TERMS_VERSION date) nor CLASS M (the anthropic row as non-public / PUBLIC_NAME_IDS). RB2-4 (c) and the RB2-7 (3) expectation ("P3 and H1 red, nothing else") => STOP, BLOCKED. A candidate ruling (NOT applied): an EK5 amendment of the one constant BASE_OPENAI_ROW_SHA256 -> c67cb808...0320 recorded from `git show origin/main:app/legal/processors.json` (split literal, the EK3/EK4 precedent).

(4) measured read-only for the ruling (no edit): the 15-file legal set + both unit files
[pyt] tag=s12m-legalset-pre start=2026-11-11 21:08:23 end=2026-11-11 21:09:08 elapsed=46s bound=1200s status=FAIL rc=1
3 failed, 552 passed; [hermeticity] sentinel checked 555 test(s); [netguard] blocked 0 attempt(s) from 0 node(s)
FAILED = the same three nodes (R9, H1, P3); every legal-set file green.
DEVIATION: the foreign-process probe printed probe_count=4 before this call (the incident lane's inc-mon1-green-pins pytest was live) and the call was not held back; it overlapped that run. Results hermetic; recorded as a deviation.

## Not run (STOP)
RB2-4 round commit (the nineteen CLAUDE.md edits, EK4), RB2-7 (5), (6), (7) full jest, (8), the PR body draft. Tree left at the merge commit 6c71a5fa, git status clean.


# RUN 2 (continuation under the addendum + RB2-13), 2026-11-11 21:14-21:56 AST

## Verify (not redone)
HEAD 6c71a5fa0e53aba81e750feed1239341acda19de on feature/s81-legal-v3; parents e8c8c1dc488a5547a874ccffb7dbd8a96ec7965c 6b909e0a92067d6b3562eee325e4956c116441f7; git status --short empty; HEAD:CLAUDE.md sha256 c92a650b... (= RB2-2); git fetch origin main -> FETCH_HEAD = origin/main = 6b909e0a92067d6b3562eee325e4956c116441f7 (main did not move). git merge NOT run.
Frozen blobs at 6c71a5fa == e8c8c1dc: test_s81_12_legal_v3.py 9163cfcb..., legalV3.s81_12.test.ts f8f21f89..., test_s81_12_gate_rows.py b98caa6a....

## EK values (ek_values.py, from git bytes)
origin/main: i18n 1011 keys, EN==AR, nameset 2d351a2c1fb2c25109ff3363d2ccd6bb24e114762d07f5a9acced9d4d9a1f543; openai row _jsha c67cb8088079d6afe8f1146530b41f6801d618cd7d6d79798b72b9762caa0320
HEAD (6c71a5fa): identical (1011 / 2d351a2c...; c67cb808...) -> CLASS B proof (main == HEAD)
e8c8c1dc: 1013 / 3d786372...; c7453e56...

## RB2-4 round commit
apply_round.py: the 19 edits of claude_edits.json applied in order on LF text, each count == 1 (P0, E9a, E9b, E5, E7, E8, E1, E2, E3, E4, RW1, RW2, RW3, RW4, RW6, RW9, RW7, RW5, RW8); CRLF kept; LF text sha256 41606c55c39de2fc73ba19e3d9aa07528ad7ead097d335d2af765f7369444449, 747,357 bytes, 1,105 lines, byte-equal to claude_md_round_expected.txt (compared after building).
apply_test.py (EK4 + EK5): exactly three constant lines, each count == 1; split literals; CRLF kept:
  BASE_I18N_KEY_COUNT = 1013 -> 1011
  BASE_I18N_NAMESET_SHA256 3d786372... -> "2d351a2c1fb2c25109ff3363d2ccd6bb24" "e114762d07f5a9acced9d4d9a1f543"
  BASE_OPENAI_ROW_SHA256 c7453e56... -> "c67cb8088079" "d6afe8f" "1146530b41f6801d618cd7d6d79798b72b9762caa0320"
  (my first script's ASCII-hex check aborted BEFORE the test file was written: a pre-existing 64-hex literal at line 219 (BASE_S7 en, base bytes, untouched); the check was narrowed to the two edited lines; no partial write.)
Staged blobs: CLAUDE.md 41606c55... (= RB2-4 ruled value); tests/test_s81_12_legal_v3.py 9163cfcb... -> e860e18dbe06941ec8a0bc9fac8742b642f67fa2b84e09f4d662cf7399d264e0. git diff --cached --check clean; ruff E9/F63/F7/F82 All checks passed; py_compile ok; non-ASCII lines in the test file 0.
Round commit dd9738f77650fbda370ca75a99c8596e44d00412 (parent 6c71a5fa) through the hook rc 0 (hook output: ruff All checks passed); 2 files, +13/-13; trailer Co-Authored-By: Claude Opus 5.5.
After: HEAD:CLAUDE.md 41606c55...; 6c71a5fa:CLAUDE.md c92a650b...; HEAD test file e860e18d...; legalV3 f8f21f89... and gate rows b98caa6a... unchanged; git diff --name-only origin/main...HEAD == footprint45.txt (45 files); git diff --name-only 6c71a5fa HEAD = CLAUDE.md, tests/test_s81_12_legal_v3.py; git status --short empty.
RB2-6 at HEAD: git diff --quiet e8c8c1dc HEAD -- <17 paths> rc 0; aiConsent.body, onboarding.s5.privacy_anon_head, onboarding.s5.privacy_anon_body EN + AR equal to e8c8c1dc. git diff --check (e8c8c1dc..HEAD and 6c71a5fa..HEAD) clean; no conflict marker under CLAUDE.md, app/, tests/, SmartCompareApp/src, SmartCompareApp/__tests__ (git grep).
E-rows CLASS V / CLASS M: none (no merged row red).

## EK5 positive control (RB2-13 (a))
.qa-mutation.lock created; byte copy of app/legal/processors.json (sha 37670d55...); removed app/services/content_safety_service.py from the openai row (exact 2-line anchor, count 1; mutated sha 06b6332b...).
[pyt] tag=s12m-pc-r9 start=2026-11-11 21:44:09 end=2026-11-11 21:44:15 elapsed=6s bound=600s status=FAIL rc=1 (-k r9: 1 failed, 37 deselected)
  E AssertionError: R9: the anthropic processors row: - the openai row changed (OpenAI stays a transition processor, R-S12-1)
Restored from the copy: sha 37670d55... == copy; lock removed; git diff --quiet app/legal/processors.json.

## RB2-7 merge-agent gates
(1) frozen blobs: above. (2) tsc / eslint: measured at 6c71a5fa in run 1 (tsc rc 0; eslint 0 errors / 3 warnings on the 13 unit client files); the round commit moves no client byte, so not re-run.
(3) unit file + gate rows after EK4 + EK5:
[pyt] 2026-11-11 21:42:40 tag=s12m-unit-post (clean probe; final [pyt] line not captured, stdout discarded): 1 failed, 59 passed, H1 only
[pyt] tag=s12m-unit-post2 start=2026-11-11 21:42:59 end=2026-11-11 21:43:03 elapsed=5s bound=600s status=FAIL rc=1
  1 failed, 59 passed; [hermeticity] sentinel checked 60 test(s); [netguard] blocked 0 attempt(s) from 0 node(s); FAILED test_h1_merge_window_recorded (by design)
  => unit file 38 nodes = 37 passed + H1; gate rows 22 / 22.
  DEVIATION: unit-post2 started while a foreign inc-mon1 pytest was live (the probe printed 4; the call was not held). Hermetic; identical to unit-post (clean probe). Every later pytest went through gated.sh (hard wait on a clean probe).
(4) the 15-file legal set + both unit files:
[pyt] tag=s12m-legalset-post start=2026-11-11 21:44:31 end=2026-11-11 21:45:03 elapsed=31s bound=1200s status=FAIL rc=1
  1 failed, 554 passed; [hermeticity] sentinel checked 555 test(s); [netguard] blocked 0 attempt(s) from 0 node(s); FAILED = H1 only
(5) alone:
[pyt] tag=s12m-alone-test_s81_s06_anthropic_router start=21:45:39 end=21:45:57 elapsed=18s status=OK rc=0 (333 passed)
[pyt] tag=s12m-alone-test_legal_s78 start=21:47:02 end=21:47:07 elapsed=5s status=OK rc=0 (29 passed)
[pyt] tag=s12m-alone-test_legal_docs_u8 start=21:47:09 end=21:47:16 elapsed=7s status=OK rc=0 (48 passed)
[pyt] tag=s12m-alone-test_legal_disclosure_s77 start=21:47:18 end=21:47:22 elapsed=4s status=OK rc=0 (31 passed)
[pyt] tag=s12m-alone-test_s81_s22b_self_critique_retire start=21:47:24 end=21:47:28 elapsed=4s status=OK rc=0 (19 passed)
[pyt] tag=s12m-alone-test_consent_capture_w3_16 start=21:47:30 end=21:47:34 elapsed=4s status=OK rc=0 (17 passed)
  each: [netguard] blocked 0 attempt(s); [hermeticity] sentinel checked = the node count
(6) client by path (jest 29.7.0; no foreign jest live):
[jest] tag=s12m-jest-unit6 start=21:32:16 end=21:32:26 rc=0 Test Suites: 6 passed, 6 total; Tests: 64 passed, 64 total; Snapshots: 0 total
[jest] tag=s12m-jest-s81_08 start=21:32:33 end=21:32:39 rc=0 Test Suites: 10 passed, 10 total; Tests: 100 passed, 100 total; Snapshots: 0 total
(7) FULL jest once, at HEAD dd9738f7 (no foreign jest live):
[jest] tag=s12m-jest-full start=21:48:17 end=21:48:34 rc=1
  Test Suites: 1 failed, 3 skipped, 408 passed, 409 of 412 total
  Tests:       4 failed, 13 skipped, 13 todo, 4039 passed, 4069 total
  Snapshots:   41 passed, 41 total
  FAIL __tests__/config/nativeBundle.w37.test.ts: d5, k2, k4, k5 (the accepted drift nodes); nothing else.
  Accounting: 4,039 - 4,030 = 9 = the nodes of the one new suite __tests__/s81_12/legalV3.s81_12.test.ts (412 suites vs main's 411). The five edited suites have the same node counts at origin/main and HEAD (static it/test count: aiConsentV2.s75 10, aiConsentVersion.s69 1, aiProcessingConsent.s69 26, landing.brand.s69 5, step05Trust.s69 13 = 55; 64 - 55 = 9 for legalV3: 6 literal calls + one .each); requestHeaders / resetRender .s81_08 22 / 15 at both. The fourteen backend-scanning client fences run inside the full suite. No -u; no .snap in the diff.
(8) scripts/fill_in_legal.py --dry-run rc 0 (no output, no file moved); scripts/render_legal_landing.py --check rc 0; ruff + py_compile on the touched python file clean; git diff --check clean; no conflict marker.

## Not run by this agent (the gates agent's, RB2-7 (9)-(14))
The CI-order set (19 files), the R8 pair, tests/test_paid_route_metering.py, the CLAUDE.md readers by the import graph, the comm set (RB2-8); the hook test files tests/test_precommit_hook*.py NOT RUN (no .githooks change).

## PR body draft
PR_BODY.md in this folder: 24,491 bytes, pure ASCII, no attribution line (the orchestrator appends it); five TO-FILL-BY-GATES markers (CI-order set, R8 pair, paid route metering, CLAUDE.md readers, comm set); headroom for the gates agent 1,109 bytes under 25,600. Built by build_pr_body.py from S81_12_PR_BODY_378.md.
