# S81-11e AR-COPY GREEN REPORT (GREEN agent, Opus 5.5, 2026-11-07 15:04-15:16 AST)

Written through the shell (python heredoc) under <scratchpad>/S81-11e_green/; <scratchpad> = C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/ac74dbc6-6547-489d-9b8b-5df68ffc4f2f/scratchpad.

Unit: S81-11e AR-COPY, CLIENT, SAFE (R-S11E-7), NO runtime flag (flag ON / OFF runs = not applicable; the identity invariant replaces flag-OFF identity).
Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s11e; branch feature/s81-s11e-ar-copy cut from 39ac80ba437760d1a77eaac9670faeea505f08f4 (`git checkout -b`, the one branch command); HEAD 989e9a39e550962d3519f0d6f26b3ef823948c1a (one commit through the .githooks pre-commit hook, no --no-verify; trailer Co-Authored-By: Claude Opus 5.5). No push, no PR, no rebase. `git status --short` after the commit: empty.

## RED file re-hash
First (15:04): b63c39c446052c3afe009380b9887fbdbc05f64f5b976bbaee0f1bf9278e9111 = GC-1. Last (after commit): same. No pin-fix (see the native read). HEAD blob d2a00c64.

## Native read (GC-6 C1)
Each of the twelve EXPECTED values re-read as a Gulf Arabic reader against the EN meaning, placeholders and render site (spec 1.5): all twelve adopted as written; no improvement made, so the RED file is unchanged. Notes for the adversary: tag_echoes_body drops the EN 'just' (recency) - judged acceptable for a notification-tag description; quote_3 uses the more correct 'al-itr nafsuh' order while tag_echoes_body keeps the everyday 'nafs al-muntajayn' order (both standard); lastSeen 'akhir rasd fi {{date}}' depends on formatAsOfDate giving a date phrase (unchanged code).

## Files (byte copies before: <scratchpad>/S81-11e_green_before/ + SHA256SUMS.txt)
| file | sha256 before (working) | sha256 after (working) | LF blob base -> head | numstat |
|---|---|---|---|---|
| SmartCompareApp/src/i18n/ar.json | 6b9471c6a03b5d322278afc26f09877158df598bf575cf0346f51735c7165f68 | e40b52365d0c709d9d098a0e4082e8f66131586fd3b7c9d97a719b4d3f88519b | f4510e72 -> ae93f901 | +12 -12 |
| SmartCompareApp/__tests__/fixtures/b3a_copy.json | 43a6378a09bb68e7301f99a4c26b1f3c6771bdd1d19228d559c85f983dc71fc2 | 76ed94a382c3d648902e547df6cc00702244f891a8336d2424d7230265deace2 | c09ba224 -> ca06964c | +1 -1 |
| CLAUDE.md | 07ec1c0cdf372137a3c0f219ab8f63c3504b80f09bd9ac3d1c2f3b5f210fa2d0 | 57465c15d88a7a5cad05df4624f8eaf56b748faa9566f4c7f0928cfb58e546e4 | b53bbbe2 -> 60b53996 | +1 -0 |
| SmartCompareApp/__tests__/s11e/arCopy.s11e.test.ts (RED, frozen) | (untracked) b63c39c4... | b63c39c446052c3afe009380b9887fbdbc05f64f5b976bbaee0f1bf9278e9111 | new -> d2a00c64 | +180 -0 |
The ar.json and fixture after-shas equal the RED prototype shas (e40b5236..., 76ed94a3...). CRLF: ar.json CR = LF = 1,074; fixture 99 / 99; CLAUDE.md 1,079 / 1,079 (one line added). Index is LF (core.autocrlf=true, i/lf w/crlf).
C1 by script apply.py (the EXPECTED lines 37-48 of the RED file parsed, never retyped; each old line matched once). C3 E1 line 79: old = the base quote_3 transliteration value, new = the EXPECTED quote_3 value (diff only). C4 by claude_md.py: inserted as line 583 after the S81-11 'Stated limits' bullet (:582), before the blank line; pure ASCII (0 bytes > 127); the spec 8 text verbatim. No EN, locales, src code, package or junction change.

## Identity script (<scratchpad>/S81-11e_green/identity_check.py, R-S11E-8; at HEAD, rc 0)
```
PASS ar.json differing keys == the twelve (got 12: same set)
PASS ar.json key order and count equal (1011 / 1011)
PASS ar.json key set == en.json key set
PASS every AR placeholder set == EN (mismatches 0)
PASS ar.json every byte outside the twelve value lines identical to base
PASS ar.json working tree CRLF kept (CR == LF == 1074)
PASS SmartCompareApp/src/i18n/en.json byte-equal to base (working sha256 89c6bc1d)
PASS SmartCompareApp/locales/ar.json byte-equal to base (working sha256 1a1ade19)
PASS SmartCompareApp/locales/en.json byte-equal to base (working sha256 4673ffc8)
ar.json LF blob base c75ea2df head aef1f588 working e40b5236
IDENTITY OK
```

## Gates (tool versions: node v24.11.1, jest 29.7.0, tsc Version 5.9.3, eslint v9.39.4; junction checked: node_modules/@babel/core + .bin/jest exist; every jest by path from sc-s81-s11e/SmartCompareApp through jr.py, a foreign-jest check before each launch: none)
[jest] tag=green_red start=15:06:53 end=15:06:56 rc=0 waited=0s -> 1 suite, 54 passed / 54
[jest] tag=green_set29 start=15:07:03 end=15:07:12 rc=0 waited=0s -> 29 / 29 suites, 406 / 406 tests
[jest] tag=green_comm start=15:07:13 end=15:07:24 rc=1 waited=0s -> 113 COMM_SET + the RED file = 114: 1 failed / 113 passed suites; 4 failed / 1,446 passed / 1,450 tests
[jest] tag=green_fences start=15:07:34 end=15:07:41 rc=1 waited=0s -> 15 fence files + b3a = 16 suites: 1 failed / 15 passed; 4 failed / 257 passed; b3a green
- HEAD failures (comm): the four config/nativeBundle.w37 nodes d5, k2, k4, k5. Base failures (RED comm_base.log, 113 files): the same four. branch-only-new = comm -13 base head = EMPTY.
- eslint by path __tests__/s11e/arCopy.s11e.test.ts rc 0, no output; tsc --noEmit -p tsconfig.json rc 0, 0 lines (15:07:46-15:07:52).
- CLAUDE.md readers by the import graph, ONCE through pyt.py after the CLAUDE.md edit (the unit's only pytest; venv .venv-qaren):
[pyt] tag=s11e-cmdreaders start=2026-11-07 15:10:44 end=2026-11-07 15:11:03 elapsed=19s bound=1200s status=OK rc=0 log=<scratchpad>/S81-11e_green/cmdreaders.log (510 passed, 13 warnings; netguard blocked 24 attempts from 2 S81-04 nodes as usual)
- Not run / not applicable: the FULL jest (LC-7, the final round); the hook test files, the backend comm set, the CI-order set and the corpus gate (no backend, .githooks, migration or app/ file); ruff / py_compile (no python file changed); flag ON / OFF (no flag).

## PR body draft
<scratchpad>/S81-11e_green/PR_BODY.md: 5,710 bytes (python), LF, pure ASCII except line 75 (the attribution line); title, the twelve keys with verdicts, E-rows, counts, identity output, comm / fence figures, L1-L5, owner steps.

## Deviations
- DV1 The harness prompt calls this agent 'Fable' and its template trailer names Claude Fable 5.1; the agent runs on Opus 5.5, and GC-8 says the trailer names the agent's own model: the trailer is Co-Authored-By: Claude Opus 5.5.
- DV2 The identity script compares on LF-normalised bytes: `git show <base>:<path>` returns the LF index blob (core.autocrlf=true) while the working tree is CRLF; a raw compare reports every file different. CRLF in the working ar.json is checked separately.
- DV3 The generic procedure's flag ON / OFF runs, ruff, py_compile, the pytest comm chunks and the CI-order set do not apply to this client unit (GC-7 governs).

## Open questions
None.
