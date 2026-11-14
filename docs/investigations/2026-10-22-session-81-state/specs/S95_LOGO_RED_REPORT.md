# S95-LOGO RESULT-LOGO-OVERLAY: RED round report (2026-11-14, RED agent, Opus 5.5)

Unit S95-LOGO (client, no flag, SAFE by LC-1). Worktree W = C:/Users/SynAckITPC/Documents/AI/sc-s95-logo, branch fix/s95-result-logo-overlay, HEAD = base 731bcddf531a7e123963246168ca19f262859337. Notes folder = this folder (notes.md is the running log; every log / json named below lives here). Window 18:30 - 18:48 (budget 90 min).

## 1. Files written
- W/SmartCompareApp/__tests__/s95logo/resultLogo.s95logo.test.tsx (the ONE added file): 14501 bytes, sha256 5d729de8048c86a3aa8759c20a9fb9f478f051ad6eb3b1eb8019631dceb75f64, 0 non-ASCII bytes, 0 CR (LF only), ends with LF. Written in NOTES first (Write tool), copied with shutil.copyfile; identical copy at NOTES/resultLogo.s95logo.test.tsx.
- NOTES only: notes.md, proto.py (line-exact prototype / mutant / restore harness), proto.diff, bytecopies/ (base_*, proto_*, mut_M1/M2/M4_*), base/ (git show copies), run*.log / run*.json, this report.
- ResultsContent.tsx and ResultsScreen.tsx were edited ONLY inside the prototype step under the lock and end byte-identical to base (section 8).

## 2. Base facts (git -C W show HEAD:...)
CONFIRMED: ResultsContent.tsx:73 the RevealBurst import; :89 / :105 the two interface fields; :127 / :136 destructured; :529 const isWeird (only reader :536); :543 the only comparisonId reader (:677 passes feedbackComparisonId); :872-880 revealBurstSlot; comments naming RevealBurst at :20, :32, :117, :519, :868. RevealBurst.tsx :71 BADGE_R = 56, :156 particle fade, :200 badge spring to 1, :232 testID reveal-burst-badge, :243 QarenLogo size BADGE_R. ResultsScreen.tsx :102 the unused import; :207 state, :503 setWinnerRevealed(true), :968 / :969 props. git grep at HEAD: only ResultsContent.tsx and ResultsScreen.tsx import hero/RevealBurst; nothing under src/components/results/ nor ResultsScreen imports or renders QarenLogo.
LINE NOTES (no stop): the slot EXPRESSION is :536-:549 (its closing ') : null}' line is :549) and the blank after it is :550 (the spec says :536-548; its words 'the whole expression and the blank line after it' are exact); :866 is a BLANK line, the slot comment is :867-:871.
SHA256: section 1 lists GIT bytes; git show bytes match all four exactly. The working copy is CRLF (core.autocrlf=true), so RAW disk sha256 differ: ResultsContent.tsx 4358e4c68fa7d4b2b6b0efcc78384cd009ad7521b64b29109a8f7f7055f5e0d9, ResultsScreen.tsx 4d5a907c977da13d301e9e0701da401d794e04dc6faac458d9a384f27d6ab0a3, ResultsContent.render.test.tsx 91f31492e74217a4395225c6e3f4d6be1717f4cecca19dd39aac1a4f270ab62d, ResultsScreen.bundleE.s3.test.tsx c8cb6630ecf06cd56f9de09ca08371f7a61764ec4da876c1ea81a74771929f5a. For all four: disk bytes with CRLF->LF == git show bytes (sha == section 1), no bare CR, and git hash-object of the disk file == git rev-parse HEAD:path. Read as NOT a content mismatch (section 1 says 'git bytes'); proceeded, deviation D1.

## 3. RED rows (every title starts with its row id)
- L1: render the REAL ResultsContent with the REAL RevealBurst (no mock of its path; the other mocks + baseProps of ResultsContent.render.test.tsx, synthetic names), winnerRevealed=true, normal mode, 3 dimensions; one toEqual over {results-v2-reveal-burst-slot rendered: false, reveal-burst-badge rendered: false, QarenLogo instances (UNSAFE_queryAllByType(QarenLogo)): 0}.
- L2 (PIN): the same render; getByTestId('results-v2-bars') and getByTestId('results-scoring-v2') present.
- L3 (PIN): winnerRevealed=false, and comparison_quality='weird' + winnerRevealed=true; per case {reveal-burst-badge rendered false, QarenLogo instances 0, results-v2-bars rendered true}.
- L4: TypeScript AST (the installed typescript, the inAppMark.u4c SourceFile recipe) over src/screens/ResultsScreen.tsx + every .tsx under src/components/results/ (recursive, sorted): no import / export-from / import=require / require() / import() whose specifier ends with hero/RevealBurst or /QarenLogo (optional .ts/.tsx), no JSX element (self-closing or opening) whose tag is RevealBurst / QarenLogo (or a dotted tag ending in one); each offence reads 'file:line imports SPEC' or 'file:line renders <Tag>'. Non-vacuity guard: the scanned list contains ResultsScreen.tsx and ResultsContent.tsx.
- L5: AST of ResultsContent.tsx: no PropertyAssignment named revealBurstSlot (each hit reads 'file:line revealBurstSlot'). Non-vacuity guard: exactly one StyleSheet.create call parsed.
Mocks: plain jest.mock(name, factory) only, no virtual mock; react-native / reanimated / svg resolve to the project moduleNameMapper mocks of jest.config.js, the same way brand/revealGlyph.u4d renders RevealBurst with no mock. No snapshot, no timer, no personal value.

## 4. Runs (each jest / tsc call preceded by waitfree.ps1 -OwnTagPrefix s95l- returning 'free poll=0'; jest 29.7.0, tsc 5.9.3, eslint v9.39.4, node v24.11.1; node_modules/@babel/core and node_modules/jest/bin/jest.js present; node_modules is the junction to the clone)
1. [jest] tag=s95l-red-base start=18:39:08 end=18:39:12 rc=1 | Test Suites: 1 failed, 1 total | Tests: 3 failed, 2 passed, 5 total
2. [tsc] tag=s95l-red-tsc-base start=18:39:44 end=18:39:50 rc=0 | 0 errors (none in the RED file; 0 pre-existing)
3. [tsc] tag=s95l-red-tsc-list start=18:40:08 end=18:40:10 rc=0 | --listFilesOnly: 1884 files incl. __tests__/s95logo/resultLogo.s95logo.test.tsx (the RED file is in the tsc program)
4. [eslint] tag=s95l-red-eslint start=18:40:22 end=18:40:32 rc=0 | RED file: 0 errors, 10 warnings (8 no-require-imports in the copied mock factories, 2 import/first: the copied render-test pattern)
5. [jest] tag=s95l-red-proto start=18:43:40 end=18:43:41 rc=0 | Test Suites: 1 passed, 1 total | Tests: 5 passed, 5 total
6. [jest] tag=s95l-red-erows-proto start=18:43:52 end=18:43:54 rc=1 | Test Suites: 2 failed, 2 total | Tests: 2 failed, 65 passed, 67 total
7. [tsc] tag=s95l-red-tsc-proto start=18:44:05 end=18:44:11 rc=0 | 0 errors (no new error)
8. [jest] tag=s95l-red-M1 start=18:44:36 end=18:44:38 rc=1 | Test Suites: 1 failed, 1 total | Tests: 1 failed, 4 passed, 5 total
9. [jest] tag=s95l-red-M2 start=18:44:49 end=18:44:51 rc=1 | Test Suites: 1 failed, 1 total | Tests: 3 failed, 2 passed, 5 total
10. [jest] tag=s95l-red-M4 start=18:45:01 end=18:45:03 rc=1 | Test Suites: 1 failed, 1 total | Tests: 3 failed, 2 passed, 5 total
11. [jest] tag=s95l-red-base-after-restore start=18:45:37 end=18:45:39 rc=1 | Test Suites: 1 failed, 1 total | Tests: 3 failed, 2 passed, 5 total (the base verdict reproduced after the restore)

## 5. RED at base (run 1): L1, L4, L5 FAIL on assertions; L2, L3 PASS
- L1: expect(received).toEqual(expected) // deep equality: received {"QarenLogo instances": 1, "results-v2-reveal-burst-slot rendered": true, "reveal-burst-badge rendered": true}, expected 0 / false / false (resultLogo.s95logo.test.tsx:313)
- L4: expect(received).toEqual(expected) // deep equality: received ["src/screens/ResultsScreen.tsx:102 imports '../components/hero/RevealBurst'", "src/components/results/ResultsContent.tsx:73 imports '../hero/RevealBurst'", "src/components/results/ResultsContent.tsx:542 renders <RevealBurst>"], expected [] (:362)
- L5: expect(received).toEqual(expected) // deep equality: received ["src/components/results/ResultsContent.tsx:872 revealBurstSlot"], expected [] (:384)
Every failure is a toEqual assertion; no render crash, import or setup error. The real RevealBurst renders under jest with NO extra mock of reanimated or svg internals.

## 6. Prototype IN PLACE
- W/.qa-mutation.lock created 18:43:29 ('S95-LOGO RED agent (Opus 5.5) prototype + mutants 2026-11-14 18:43:29'); byte copies NOTES/bytecopies/base_ResultsContent.tsx and base_ResultsScreen.tsx (shutil.copyfile; LF-normalized sha == section 1).
- NOTES/proto.py applied spec 3.1 (a)-(f) and 3.2 line-exactly (each base line asserted before its edit; CRLF kept): diff stat 2 files, 10 insertions, 43 deletions, 0 non-ASCII bytes on added lines; NOTES/proto.diff (149 lines). Proto ResultsContent.tsx 35096 bytes sha 20078f144cf1c0faca9dfb7bd9d949160090b488114a8f3f5a883ef6a2c99714; proto ResultsScreen.tsx 48298 bytes sha fb2fef98eff7dc8c8d0b1f4422d1271399ff3852051f42a9de28732fc8063359.
- Choices: (e) deleted :866 (the blank) through :880; (f) :20 rewritten ' *  4. Dimension bars   - DimensionBars + sheet' padded to the (JSX 348-353) column 62 (that line's em dash written as ASCII '-'); :32 drops '/ RevealBurst'; :117 reads 'frame the winner spring. With memo, only prop'; :519-523 say the celebration (RevealBurst) is no longer mounted on the result page (S95-LOGO: its MYEZ badge never faded and stayed over the bars; the owner ruled the logo must not show); (d) '  /** Kept for the call sites, not read since S95-LOGO. */' above each kept field.
- RED at the prototype: 5 of 5 pass (run 5).
- E-row files at the prototype (run 6): EXACTLY two failures, every other test passes:
  E1 = __tests__/components/ResultsContent.render.test.tsx 'renders RevealBurst slot when winnerRevealed=true and not weird' (Error: Unable to find an element with testID: results-v2-reveal-burst-slot); that file 27 passed, 1 failed.
  E2 = __tests__/ResultsScreen.bundleE.s3.test.tsx 'orchestrator still renders RevealBurst keyed on comparisonId, fireOnce' (expect(received).toMatch(expected), pattern /<RevealBurst/); that file 38 passed, 1 failed.
- tsc at the prototype: rc=0, 0 errors (run 7).

## 7. Mutants (each from the prototype byte copy; the RED file alone; the prototype restored after each, its sha re-checked)
- M1 re-add only the ResultsContent import: KILLED by L4 (offence 'ResultsContent.tsx:73 imports ../hero/RevealBurst'); L1 L2 L3 L5 pass.
- M2 re-add <RevealBurst fireOnce particleCount={6} size={220} /> directly in the results-scoring-v2 section (no slot View), with the import: KILLED by L1 (badge true, QarenLogo 1, slot false), L3 (badge / QarenLogo in both cases: the mutant is ungated), L4 (:73 import + :535 renders <RevealBurst>).
- M4 <QarenLogo size={56} /> inside that section, with its import: KILLED by L1 (QarenLogo 1), L3 (QarenLogo 1 in both cases), L4 (:73 imports ../QarenLogo + :535 renders <QarenLogo>).
All kills are toEqual assertion failures. M3 not run (not in this round's procedure; spec section 6 gives it to GREEN / the adversary).

## 8. Restore proof
- base byte copies copied back with shutil.copyfile: ResultsContent.tsx raw 4358e4c68fa7d4b2b6b0efcc78384cd009ad7521b64b29109a8f7f7055f5e0d9 == byte copy, LF-normalized 53b7d70c3447a396e89458275c93c2d021dae05d98b0756932f78b40ec7ee055 == section 1; ResultsScreen.tsx raw 4d5a907c977da13d301e9e0701da401d794e04dc6faac458d9a384f27d6ab0a3 == byte copy, LF-normalized fbefbd983764ff4cb2ae6a368595328178390f52c9b4c825e3764a360faed0c5 == section 1; git hash-object == HEAD blob for both (cd28785deaf2227f1b0844a0d30efe42fecbcbb0, 8c6c7bb43c7dd2c5f62853d8ced11ad7ef2f87a0).
- lock removed (ls: No such file or directory).
- git -C W status --short -uall: '?? SmartCompareApp/__tests__/s95logo/resultLogo.s95logo.test.tsx' (only the RED file); git diff --stat empty.
- run 11 at the restored base reproduces L1 / L4 / L5 FAIL and L2 / L3 PASS. No jest / tsc process of this agent left running (node.exe list: MCP and language servers only).

## 9. Deviations
- D1: section 1 sha256 = git bytes; the CRLF working copy (core.autocrlf=true) makes RAW disk sha256 differ. Not stopped: disk == HEAD blob (hash-object) and LF-normalized sha == section 1 for all four files; the restore is proved three ways (raw == byte copy, LF-normalized == section 1, hash-object == HEAD blob).
- D2: spec line ranges: the slot expression ends at :549 (blank :550), not :548; :866 is blank (the comment starts :867).
- D3: L4 is a superset of the spec wording (also export-from / require() / import() / import=require, an optional .ts/.tsx extension, dotted JSX tags); L4 and L5 carry non-vacuity guards. All pass at base (the guards) and at the prototype.
- D4: three extra measurements: eslint on the RED file (0 errors, 10 warnings), a tsc --listFilesOnly call (the RED file is in the program), a jest run at the restored base (run 11).
- D5: M2 omits key={comparisonId ...} (comparisonId is not destructured at the prototype: a key on it would crash, not assert); M2 and M4 are ungated, so L3 also kills them.
- D6: product / brand / store names of the copied baseProps replaced by synthetic ones (Sample Scent Alpha / Beta, Brand Alpha / Beta, Store One); comparisonId 'cmp-s95-logo'.
- D7: this report is written in four python heredoc parts (one Bash call over about 7 KB is refused on this box).

## 10. Open questions (for the gate)
- Q1: rule D1: accept 'LF-normalized disk sha == section 1 and hash-object == HEAD blob' as the section-1 match on this CRLF box (GREEN and the adversary meet the same raw-sha difference).
- Q2 (GREEN): 3.1 (e) start at :866 (the blank, as the prototype did) or :867 (the comment's first line); both satisfy L5.
- Q3 (GREEN): 3.1 (f) :20 keeps a non-ASCII em dash on the changed line unless it is written ASCII ('-', the prototype's choice).
- Q4: M3 (gated 'winnerRevealed && false') is left to GREEN / the adversary per spec section 6.
