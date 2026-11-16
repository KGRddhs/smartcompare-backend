# INC-I2e GUARD-SHORT-LINE: GREEN report (S96, s96e-green agent, Opus 5.5, 2026-11-16)

Worktree C:/Users/SynAckITPC/Documents/AI/sc-s96-i2e, branch fix/inc-i2e-guard-short-line, base b0ad260363e0cf0074e4ee596b140d073466e92a. Notes: this folder (notes.md). Written through the shell.

## 1 Implementation
- app/services/image_relevance.py = the RED prototype byte copy (red/proto/image_relevance.py sha256 3f59c994..., git blob a2e8f399 = proto.diff index) plus ONE GC-3 edit: `zip(toks, toks[1:])` -> `zip(toks, toks[1:], strict=False)` in _candidate_keys. Diff vs proto.diff: that one line only (checked by diffing the +/- lines).
- CLAUDE.md = the prototype byte copy (sha256 08fe8fb6..., blob d930e009) plus GC-4: the prototype's one-line "Stated limits" bullet of the INC-I2e block is replaced by (a) an "Input paths (measured at b0ad2603)" bullet, (b) a "What changes on the phone with this switch alone (resolver OFF)" bullet, (c) "Stated limits (one line each; no new log key):" with sub-bullets L-1..L-6. New text pure ASCII (the block's existing convention: the degree sign is spelled in words; CLAUDE.md holds no degree sign at all). No other CLAUDE.md change (the Feature Flags sentence is the prototype's).
- .github/black-clean-paths.txt: tests/test_inc_i2e_guard_short_line.py appended at the end (the file orders by unit append: mon1, i1, r1, now i2e; no sortedness pin), CRLF kept.
- Line endings: every file CRLF as at HEAD; git diff --stat 3 files +177/-1 before commit (no whole-file diff). (a) claims spot-checked: HomeScreen.tsx:458-459 streamComparison({product_a, product_b}); compareTextPair defined in src/services/api.ts:1041 with no screen caller; product_resolver.apply_resolution sets brand = side.brand, name = side.line.

## 2 RED file at the change (sha256 38090ba9... unchanged on disk and in the commit blob)
[pyt] tag=s96e-green-red start=2026-11-16 20:31:21 end=2026-11-16 20:31:24 elapsed=2s bound=600s status=OK rc=0 (20 passed)
[hermeticity] sentinel checked 20 test(s) / [netguard] blocked 0 attempt(s) from 0 node(s)
ENABLE_IMAGE_GUARD_SHORT_LINE=true exported for that one call:
[pyt] tag=s96e-green-red-son start=2026-11-16 20:31:29 end=2026-11-16 20:31:32 elapsed=3s bound=600s status=OK rc=0 (20 passed)
[hermeticity] sentinel checked 20 test(s) / [netguard] blocked 0 attempt(s) from 0 node(s)

## 3 Comm set
Re-derived with the RED builder (build_comm.py, copied here) on the changed tree: 206 files, 9 chunks, set sha256 84667417af6ad095d2cd4eb8f1aa642adaf0f071ea506ee3d2016d2b8c9076e9 = the RED round; chunk files byte-identical. LC-6: the cached base record harness/base_records/b0ad2603.../84667417....txt REUSED (no new base run).
Result: 22 failing ids = the base record's 22 (comm -13 EMPTY, comm -23 EMPTY; also equal to the RED prototype set); per-chunk pass/fail/skip counts identical to the RED base chunks. new_failures: none.
[pyt] tag=s96e-green-c01 start=2026-11-16 20:32:17 end=2026-11-16 20:32:55 elapsed=38s bound=1200s status=OK rc=0
[pyt] tag=s96e-green-c02 start=2026-11-16 20:32:55 end=2026-11-16 20:34:11 elapsed=75s bound=1200s status=OK rc=0
[hermeticity] sentinel checked 964 test(s)
[netguard] blocked 13 attempt(s) from 2 node(s)
[pyt] tag=s96e-green-c03 start=2026-11-16 20:34:11 end=2026-11-16 20:35:19 elapsed=68s bound=1200s status=OK rc=0
[hermeticity] sentinel checked 973 test(s)
[netguard] blocked 8 attempt(s) from 4 node(s)
[pyt] tag=s96e-green-c04 start=2026-11-16 20:35:20 end=2026-11-16 20:35:55 elapsed=35s bound=1200s status=OK rc=0
[hermeticity] sentinel checked 2284 test(s)
[netguard] blocked 4 attempt(s) from 2 node(s)
[pyt] tag=s96e-green-c05 start=2026-11-16 20:35:55 end=2026-11-16 20:38:30 elapsed=155s bound=1200s status=FAIL rc=1
[hermeticity] sentinel checked 2843 test(s)
[netguard] blocked 24 attempt(s) from 2 node(s)
[pyt] tag=s96e-green-c06 start=2026-11-16 20:38:31 end=2026-11-16 20:40:30 elapsed=119s bound=1200s status=FAIL rc=1
[pyt] tag=s96e-green-c07 start=2026-11-16 20:40:30 end=2026-11-16 20:41:43 elapsed=73s bound=1200s status=FAIL rc=1
[pyt] tag=s96e-green-c08 start=2026-11-16 20:41:44 end=2026-11-16 20:42:44 elapsed=60s bound=1200s status=OK rc=0
[hermeticity] sentinel checked 277 test(s)
[netguard] blocked 0 attempt(s) from 0 node(s)
[pyt] tag=s96e-green-c09 start=2026-11-16 20:42:44 end=2026-11-16 20:42:50 elapsed=5s bound=1200s status=OK rc=0

## 4 Lint
black 26.5.1 --check --diff on image_relevance.py and the RED file: 2 files would be left unchanged; the CI allowlist step over the whole black-clean-paths.txt (with the new entry): 41 files unchanged. ruff 0.16.5 --select E9,F63,F7,F82 --no-cache on the two files: All checks passed; over app/ scripts/ tests/ (the CI step): All checks passed. The repo's full ruff config on the two files (report-only): All checks passed (the prototype's B905 is gone). py_compile OK. Black prints the box's standing "Python 3.12 cannot parse code formatted for Python 3.15" warning; verdict unaffected.

## 5 Jest (W/SmartCompareApp, node v24.11.1, jest 29.7.0 by path through the junction; @babel/core and .bin/jest present)
Fences (18 files: the fourteen named fences = 15 files (clipboardFallbackService and playInstallReferrerService each with .edges) plus 3 found by a path-join scan reaching outside SmartCompareApp: HomeScreen.eS3hf.dedupe (docs/), landing.brand.s69 and landing.handoff.s69 (landing/); no client suite reads CLAUDE.md (13 mention it in comments only)):
[jest] tag=s96e-green-jest-fences start=2026-11-16 20:43:45 end=2026-11-16 20:43:55 rc=1 -> Test Suites 1 failed, 17 passed, 18; Tests 4 failed, 282 passed, 286. The 4 = nativeBundle.w37 d5, k2, k4, k5 (the accepted drift).
Full suite:
[jest] tag=s96e-green-jest-full start=2026-11-16 20:43:59 end=2026-11-16 20:44:16 rc=1 -> Test Suites 1 failed, 3 skipped, 409 passed, 410 of 413; Tests 4 failed, 13 skipped, 13 todo, 4042 passed, 4072. Only failures: the same 4 nativeBundle.w37 drift nodes. No other failure.

## 6 Commit (GC-7)
c070d1366723f18b4772f1eaac393af8f6e7d9ad on fix/inc-i2e-guard-short-line (parent b0ad2603), exactly four paths staged by name, 4 files changed +839/-1. Hook ran (ruff "All checks passed!", black "2 files would be left unchanged"), no --no-verify, not pushed. git status --short after: empty.
Final sha256 (disk / committed blob): image_relevance.py cd5f829e... / 24c0beb3... (blob c8a5b383); CLAUDE.md a6a23aa4... / 47e2714f... (blob c1aadfbb); black-clean-paths.txt 46cb2750... / 72517bdb... (blob baa7da87); RED file 38090ba9... / 38090ba9... (blob 511c9e0a).
Added-line sweep (@gmail, +973, 8-digit runs, key shapes, credentialed URLs): no hit.

## 7 Deviations
- G-D1 CLAUDE.md GC-4 (c): the prototype's one-line stated-limits bullet is REPLACED by the L-1..L-6 sub-bullets (it duplicated L-1..L-4); its "no new log key" moved into the new heading.
- G-D2 GC-4 (b) text: the degree-sign spellings are written in words (`CHANEL N 5` title spelled with the degree sign) to keep the block ASCII like the prototype.
- G-D3 the jest fence run carried 18 files (the named 15 + 3 scan extras), a superset of the fourteen fences.
- G-D4 comm chunks ran from a neutral background driver (comm_drive.sh) and the jest runs from client_drive.sh, waitfree before each; I waited outside every runner.

## 8 Open questions
- Q-G1 GC-4 (c) names L-1..L-6; L-7 (adjacent title tokens may join by chance) is NOT in CLAUDE.md (gate wording followed); it belongs in the PR body.
- NOT MEASURED: nothing in the gate list.
