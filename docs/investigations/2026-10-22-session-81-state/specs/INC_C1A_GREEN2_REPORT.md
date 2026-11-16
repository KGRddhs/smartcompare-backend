# INC-C1a SIZE-LABEL: GREEN-2 report (S96, GREEN-2 agent, 2026-11-16 21:30:53-21:36 AST)

Worktree sc-s96-c1a, branch fix/inc-c1a-size-label. Written through the shell. Gate ADDENDUM 1 / CC-8 applied.

## VERDICT: GREEN, committed 2abcbf44aa5d93851c97afe1ace2996649f33934 (parent b0ad260363e0cf0074e4ee596b140d073466e92a). Not pushed.

## Inherited state (verified before any edit)
- HEAD b0ad2603; git status --short = 12 M (6 src + 6 moved-pin tests) + ?? SmartCompareApp/__tests__/c1a/; no .qa-mutation.lock.
- sha256 of all 13 files in green/shas.txt: 13 OK (the list had CRLF line ends; checked from an LF copy green2/shas_in.txt). G-1 / G-2 untouched.
- tests/test_s81_12_legal_v3.py at HEAD sha 6215f38d98317a553f2686435949bab9c49a1f40ff972bebc729c9c664a66434, unmodified; byte copy green2/bak/.

## CC-8 (applied exactly; python exact replacement, 1 match, CRLF kept 1448/1448 lines, 0 non-ASCII)
tests/test_s81_12_legal_v3.py (base :239-241 -> :239-242):
- inserted after :239 (the "Recorded base values" comment), above the two constants: `# INC-C1a (2026-11-16) re-recorded: + results.price.withSize, results.price.perMl, results.price.differentSizes (CC-8)`
- :240 `BASE_I18N_KEY_COUNT = 1011` -> `BASE_I18N_KEY_COUNT = 1014`
- :241 `"2d351a2c1fb2c25109ff3363d2ccd6bb24" "e114762d07f5a9acced9d4d9a1f543"` -> `"cd5995fb42987f33165330732c5fdf1b1c" "88dfc639676d0742fa431077bfe8e6"` (two literals)
- git diff --stat: 1 file, +3 -2. New sha256 9f93e03b681adb899b6325d4a08b2d30e6cfc8673128cdc4731ea7b50e681018.

## Runs (waitfree.ps1 -OwnTagPrefix s96c- before every gate; first wait 21:31:45-21:32:15 behind another lane's pyt.py, then free)
- [pyt] tag=s96c-green-legalv3 start=2026-11-16 21:32:20 end=2026-11-16 21:32:23 elapsed=3s bound=600s status=OK rc=0: 38 passed; [hermeticity] sentinel checked 38 test(s); [netguard] blocked 0 attempt(s) from 0 node(s).
- [pyt] tag=s96c-green-fences2 start=2026-11-16 21:32:35 end=2026-11-16 21:32:50 elapsed=15s bound=600s status=OK rc=0: 303 passed (the nine: test_comparison_id_echo, test_dimension_label_catalog_parity_w414, test_legal_docs_u8, test_legal_docs_u8_d3c, test_s81_12_gate_rows, test_s81_12_legal_v3, test_register_benefits_parity_s69, test_events_allowlist_superset, test_security_regression); [hermeticity] sentinel checked 303 test(s); [netguard] blocked 12 attempt(s) from 6 node(s) (test_security_regression sentinels, same as GREEN-1).
- jest 29.7.0 (node_modules/@babel/core and .bin/jest present): [jest] tag=s96c-green-pins start=2026-11-16 21:33:02 end=2026-11-16 21:33:04 rc=0: 7 suites passed, 129/129 (the RED file + api.cameraAuthRetry.u13c, s11/copy.s11, s11e/arCopy.s11e, s81_08/cameraHeaders, requestHeaders, sseHeaders).
- [jest] tag=s96c-green-red start=2026-11-16 21:33:13 end=2026-11-16 21:33:15 rc=0 --verbose: 9 passed of 9 (C1-C7, P1, P2 each listed).
- tsc 5.9.3 --noEmit: [tsc] tag=s96c-green-tsc start=2026-11-16 21:33:21 end=2026-11-16 21:33:27 rc=0, 0 lines.
- eslint: not re-run as its own gate (client bytes identical to GREEN-1: rc=0, 0 errors / 147 warnings on src, none on an added line); the pre-commit hook ran eslint on the staged client files: 0 errors, 9 warnings, all on pre-existing lines (ResultsContent 49, 310; requestContext 117, 120; types 25-28, 453), none on an added line.

## Inherited (NOT re-run, LC-7; GREEN-1 on these exact client bytes, sha-verified identical above)
- FULL jest (GREEN-1): [jest] tag=s96c-green-full start=21:25:48 end=21:26:00 rc=1: 414 suites (410 passed, 1 failed, 3 skipped), 4081 tests: 4051 passed, 4 failed, 13 skipped, 13 todo; snapshots 41/41; the only FAIL suite config/nativeBundle.w37 (d5, k2, k4, k5) = the 4 accepted nodes.
- --runInBand pairs (GREEN-1, order-preserving sequencer): [jest] tag=s96c-green-pair-ab 21:28:14-21:28:16 rc=0 sizeLabel > requestHeaders 31/31; [jest] tag=s96c-green-pair-ba 21:28:16-21:28:18 rc=0 requestHeaders > sizeLabel 31/31.
- The 28 moved-pin hunks (18 tests): green/pin_edit_list.txt.

## G-5 commit
- [commit] start=2026-11-16 21:33:57 end=2026-11-16 21:34:05 rc=0, through .githooks/pre-commit (core.hooksPath=.githooks; ruff "All checks passed!", gitleaks, eslint 0 errors); no --no-verify; not pushed.
- 2abcbf44 "feat(results): INC-C1a SIZE-LABEL bottle size and per-ml line beside a shown price; declare price_size", body 5 lines, trailer Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>.
- Staged by name, 14 files, +705 -31: the six src files (ResultsContent.tsx, ar.json, en.json, requestContext.ts, types.ts, formatNumber.ts), the RED file (A), the six moved-pin test files, tests/test_s81_12_legal_v3.py. No package, lock or app.json path in the commit.
- git status --short afterwards: empty.

## Final sha256 (bytes on disk; green2/shas_final.txt)
The 13 client files equal green/shas.txt exactly (ResultsContent 1e603e66..., ar.json f122dc8e..., en.json d8c8d205..., requestContext bd0757b5..., types 0970e0a3..., formatNumber 9ab5aa22..., u13c 01d4f6dc..., copy.s11 abeca05d..., arCopy.s11e 3ed9db30..., cameraHeaders 3dd69d4e..., requestHeaders c20f83fe..., sseHeaders 7be5e108...); RED file 7a9f3fffcb66005736a929a55d8498f41526b3b562816856b331c94e36ada05d (unchanged); tests/test_s81_12_legal_v3.py 9f93e03b681adb899b6325d4a08b2d30e6cfc8673128cdc4731ea7b50e681018.

## Deviations
- D1 eslint not run as a separate gate in this round (client bytes unchanged since GREEN-1's clean run; the hook's eslint pass on the staged client files is quoted above).
- D2 the commit body is 5 lines and carries one U+00B7 (the EN separator) in its description of the label.
- D3 the git add warned "LF will be replaced by CRLF" for the untracked RED file (working copy LF; index stores LF under core.autocrlf=true); its bytes on disk are unchanged (sha checked after the commit).

## NOT MEASURED
- the full jest suite in this round (LC-7, inherited); nothing on a device; CI.

## Open questions
- none.
