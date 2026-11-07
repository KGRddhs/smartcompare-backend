# S81-11e AR-COPY RED REPORT (RED agent, Opus 5.5, 2026-11-07 14:49-15:00 AST)

Unit: S81-11e AR-COPY (CLIENT, SAFE under LC-1 per R-S11E-7; NO runtime flag). Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-s11e at 39ac80ba437760d1a77eaac9670faeea505f08f4 (detached). Report written through the shell (python heredoc); the harness refuses a subagent Write of a report .md.

NOT APPLICABLE in this unit (per R-S11E-10 / R-S11E-12): no pytest, no pyt.py (so no [pyt] lines exist), no backend comm set, no corpus gate, no hook test files, no scratch worktree (the prototype and every mutant ran IN PLACE on byte copies, restored and sha-checked), no junction change, no git write command, no package manager, no network. The CLAUDE.md readers run through pyt.py at GREEN only. The full jest is the final round's (LC-7).

## Tools (by path from sc-s81-s11e/SmartCompareApp; junction checked: node_modules/@babel/core and node_modules/.bin/jest exist)
node v24.11.1; jest 29.7.0; tsc Version 5.9.3; eslint v9.39.4.
- eslint: `node node_modules/eslint/bin/eslint.js __tests__/s11e/arCopy.s11e.test.ts` -> rc=0, no output.
- tsc: `node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json` -> rc=0, 0 errors (14:54:41-14:54:50); `--listFilesOnly` confirms the new file is in the program.

## The file (the only new file; nothing else added or edited)
SmartCompareApp/__tests__/s11e/arCopy.s11e.test.ts: 9,195 B, 180 lines, LF (CR = 0; siblings __tests__/s11/copy.s11.test.tsx and __tests__/s81_08/i18nKeys.s81_08.test.ts are i/lf), sha256 b63c39c446052c3afe009380b9887fbdbc05f64f5b976bbaee0f1bf9278e9111.
Non-ASCII lines: 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48 = exactly the twelve EXPECTED entries (raw UTF-8). Every other Arabic is a \u escape (BRAND_AR, VERB_AR, OR_FORM, LAST_ONLINE, CLOCK_FORM, the diacritic / digit / bidi classes). The EXPECTED values were extracted by script from the spec's 2.1 table (never retyped) and each was confirmed present verbatim in specs/S81_11E_AR_COPY_REVIEW.md (sha256 9d6e3687...6f996 re-hashed); EN_TABLE = the spec's 1.3 EN column (ASCII, \u2014 / \u00b7 escapes), each confirmed equal to en.json at base.
Constant names: I18N_DIR, AR, EN, POLICY, EXPECTED, EN_TABLE, TWELVE, AR_LETTER, BRAND_AR, VERB_AR, AR_DIACRITICS, AR_INDIC_DIGIT, BIDI_CONTROL, ASCII_DIGIT, OR_FORM, LAST_ONLINE, CLOCK_FORM: none carries access / auth / api / credential / creds / key / password / secret / token.
Hermetic: fs.readFileSync + JSON.parse of src/i18n/ar.json, en.json, .copy-policy.json; no render, no mock, no network. Failure messages print keys and booleans only: the RED failure log holds 0 Arabic characters (measured).

## Rows (15 RED + 39 PIN = 54 nodes)
- R1-R12 it.each(TWELVE): expect({ k, matches: AR[k] === EXPECTED[k] }).toEqual({ k, matches: true }).
- R13 one concentration form: for quote_3 / box_a_text / box_b_text {k, orForm: includes(OR_FORM), tokens: EDP/EDT present} toEqual {orForm false, tokens [EDP,EDT] / [EDP] / [EDP]}.
- R14 {k, lastOnline} for lastSeen + lastSeenNoStore toEqual false.
- R15 {k, clock: includes(CLOCK_FORM)} for resets, a11yResets, paywall.limit.resets_at toEqual true.
- P1 (12) AR placeholder set == EN; P2 (12) EXPECTED placeholder set == EN; P3 the 12 keys in both catalogs, key sets equal both ways, 1,011 / 1,011; P4 no diacritic (brand word split out), no Arabic-Indic digit, no bidi control, no ASCII digit outside {{...}}; P5 banned_ar.length >= 5 and scary_vocab_ar.length >= 4 asserted first, then no banned_ar pattern (new RegExp(pattern,'u')), no scary word, no standalone verb (the brand.myez wordRe form), no brand word (escaped Arabic brand / MYEZ); P6 (12) EN[k] == EN_TABLE[k].

## RED at base
[jest] tag=red_base start=14:55:13 end=14:55:16 rc=1 waited=0s
Tests: 15 failed, 39 passed, 54 total. Every failure = `expect(received).toEqual(expected) // deep equality` (15 of 15; 0 SyntaxError / TypeError / ReferenceError / Cannot find in the log). Failing nodes (describe "S81-11e AR-COPY RED rows (fail at base on the old values)"):
R1-R12 the AR value of <k> equals the EXPECTED table, for k = home.errors.categoryNotLive, home.errors.insufficientDataReason.placeholder_identity, results.honest.notListed, results.price.lastSeen, results.price.lastSeenNoStore, home.errors.comparison, home.errors.insufficientData, onboarding.s1.quote_3, onboarding.s17.tag_echoes_body, home.compare.box_a_text, home.compare.box_b_text, home.headerCounter.resets (12, toEqual); R13 one concentration form in quote_3 and both compare boxes (toEqual); R14 the "last online" phrase is gone from lastSeen and lastSeenNoStore (toEqual); R15 the clock form: the hour word before {{time}} in resets and both siblings (toEqual). All 39 PIN nodes passed.
Re-run after the restore: [jest] tag=red_base_after_restore start=14:58:51 end=14:58:53 rc=1 waited=0s -> 15 failed, 39 passed, 54 total.

## Satisfiability prototype (IN PLACE, restored)
Byte copies: <scratchpad>/S81-11e_red/copies/ar.json.base (6b9471c6a03b5d322278afc26f09877158df598bf575cf0346f51735c7165f68), b3a_copy.json.base (43a6378a09bb68e7301f99a4c26b1f3c6771bdd1d19228d559c85f983dc71fc2), en.json.base (89c6bc1d04fd94c44f27466e356aed1651ea7b79ba8dfb8dc052a266c9f5612f, for M17).
C1 (proto.py): the twelve value lines by exact line replacement (each old line matched once), CRLF kept: 12 keys differ, key order equal, CR = LF = 1,074; prototype sha e40b52365d0c709d9d098a0e4082e8f66131586fd3b7c9d97a719b4d3f88519b. C3: the fixture quote_3 AR value (line 79) replaced once, CR = LF = 99; prototype sha 76ed94a382c3d648902e547df6cc00702244f891a8336d2424d7230265deace2.
- [jest] tag=proto_red start=14:55:54 end=14:55:57 rc=0 waited=0s -> Tests: 54 passed, 54 total.
- [jest] tag=proto_set29 start=14:55:59 end=14:56:06 rc=0 waited=0s -> Test Suites: 29 passed, 29 total; Tests: 406 passed, 406 total (the spec's 388 was measured with its 36-node prototype file; 388 - 36 + 54 = 406, consistent). List: <scratchpad>/S81-11e_red/set29.txt.
- [jest] tag=proto_fences start=14:56:08 end=14:56:15 rc=1 waited=0s -> Test Suites: 1 failed, 15 passed, 16 total; Tests: 4 failed, 257 passed, 261 total. The 4 = config/nativeBundle.w37 d5, k2, k4, k5 (the known drift); b3a/honestCopy green. The spec's "fourteen" fence list names 15 files when clipboardFallbackService(+.edges) and playInstallReferrerService(+.edges) are counted separately: 15 fence files + b3a = 16 suites run (list <scratchpad>/S81-11e_red/fences.txt); the only failing suite is nativeBundle.w37 (so 14 / 15 fences green + b3a green).

## Mutation table (on the prototype bytes in place; each restored to the prototype sha and verified; jest = the RED file only)
| M | Mutant | [jest] line | Tests | Killing rows (all toEqual) | Restore sha ok |
|---|---|---|---|---|---|
| M1 | home.errors.categoryNotLive = old value | [jest] tag=mut_M1 start=14:56:42 end=14:56:46 rc=1 waited=0s | 1 failed, 53 passed, 54 total | R1-R12 the AR value of home.errors.categoryNotLive equals the EXPECTED table | True |
| M2 | home.errors.insufficientDataReason.placeholder_identity = old value | [jest] tag=mut_M2 start=14:56:47 end=14:56:52 rc=1 waited=0s | 1 failed, 53 passed, 54 total | R1-R12 the AR value of home.errors.insufficientDataReason.placeholder_identity equals the EXPECTED table | True |
| M3 | results.honest.notListed = old value | [jest] tag=mut_M3 start=14:56:53 end=14:56:56 rc=1 waited=0s | 1 failed, 53 passed, 54 total | R1-R12 the AR value of results.honest.notListed equals the EXPECTED table | True |
| M4 | results.price.lastSeen = old value | [jest] tag=mut_M4 start=14:56:57 end=14:57:01 rc=1 waited=0s | 2 failed, 52 passed, 54 total | R1-R12 the AR value of results.price.lastSeen equals the EXPECTED table; R14 the "last online" phrase is gone from lastSeen and lastSeenNoStore | True |
| M5 | results.price.lastSeenNoStore = old value | [jest] tag=mut_M5 start=14:57:01 end=14:57:08 rc=1 waited=0s | 2 failed, 52 passed, 54 total | R1-R12 the AR value of results.price.lastSeenNoStore equals the EXPECTED table; R14 the "last online" phrase is gone from lastSeen and lastSeenNoStore | True |
| M6 | home.errors.comparison = old value | [jest] tag=mut_M6 start=14:57:08 end=14:57:12 rc=1 waited=0s | 1 failed, 53 passed, 54 total | R1-R12 the AR value of home.errors.comparison equals the EXPECTED table | True |
| M7 | home.errors.insufficientData = old value | [jest] tag=mut_M7 start=14:57:13 end=14:57:16 rc=1 waited=0s | 1 failed, 53 passed, 54 total | R1-R12 the AR value of home.errors.insufficientData equals the EXPECTED table | True |
| M8 | onboarding.s1.quote_3 = old value | [jest] tag=mut_M8 start=14:57:17 end=14:57:21 rc=1 waited=0s | 2 failed, 52 passed, 54 total | R1-R12 the AR value of onboarding.s1.quote_3 equals the EXPECTED table; R13 one concentration form in quote_3 and both compare boxes | True |
| M9 | onboarding.s17.tag_echoes_body = old value | [jest] tag=mut_M9 start=14:57:21 end=14:57:25 rc=1 waited=0s | 1 failed, 53 passed, 54 total | R1-R12 the AR value of onboarding.s17.tag_echoes_body equals the EXPECTED table | True |
| M10 | home.compare.box_a_text = old value | [jest] tag=mut_M10 start=14:57:26 end=14:57:29 rc=1 waited=0s | 2 failed, 52 passed, 54 total | R1-R12 the AR value of home.compare.box_a_text equals the EXPECTED table; R13 one concentration form in quote_3 and both compare boxes | True |
| M11 | home.compare.box_b_text = old value | [jest] tag=mut_M11 start=14:57:30 end=14:57:34 rc=1 waited=0s | 2 failed, 52 passed, 54 total | R1-R12 the AR value of home.compare.box_b_text equals the EXPECTED table; R13 one concentration form in quote_3 and both compare boxes | True |
| M12 | home.headerCounter.resets = old value | [jest] tag=mut_M12 start=14:57:34 end=14:57:38 rc=1 waited=0s | 2 failed, 52 passed, 54 total | R1-R12 the AR value of home.headerCounter.resets equals the EXPECTED table; R15 the clock form: the hour word before {{time}} in resets and both siblings | True |
| M13 | lastSeen new value with {{store}} dropped | [jest] tag=mut_M13 start=14:57:39 end=14:57:42 rc=1 waited=0s | 2 failed, 52 passed, 54 total | P1 the AR placeholder set of results.price.lastSeen equals EN; R1-R12 the AR value of results.price.lastSeen equals the EXPECTED table | True |
| M14 | lastSeenNoStore new value with {{date}} dropped | [jest] tag=mut_M14 start=14:57:43 end=14:57:46 rc=1 waited=0s | 2 failed, 52 passed, 54 total | P1 the AR placeholder set of results.price.lastSeenNoStore equals EN; R1-R12 the AR value of results.price.lastSeenNoStore equals the EXPECTED table | True |
| M15 | resets new value with {{time}} dropped | [jest] tag=mut_M15 start=14:57:47 end=14:57:50 rc=1 waited=0s | 3 failed, 51 passed, 54 total | P1 the AR placeholder set of home.headerCounter.resets equals EN; R1-R12 the AR value of home.headerCounter.resets equals the EXPECTED table; R15 the clock form: the hour word before {{time}} in resets and both siblings | True |
| M16 | a shadda (U+0651) added after the 2nd char of home.errors.comparison | [jest] tag=mut_M16 start=14:57:51 end=14:57:55 rc=1 waited=0s | 2 failed, 52 passed, 54 total | P4 the twelve AR values: no diacritic, no Arabic-Indic digit, no bidi control, no stray ASCII digit; R1-R12 the AR value of home.errors.comparison equals the EXPECTED table | True |
| M17 | EN home.compare.box_a_text changed (EDP -> EDT) | [jest] tag=mut_M17 start=14:57:56 end=14:57:59 rc=1 waited=0s | 1 failed, 53 passed, 54 total | P6 the EN value of home.compare.box_a_text equals the EN table | True |
| M18 | banned_ar[0] pattern appended to results.honest.notListed | [jest] tag=mut_M18 start=14:58:00 end=14:58:03 rc=1 waited=0s | 2 failed, 52 passed, 54 total | P5 the twelve AR values pass the copy policy (non-vacuous), carry no standalone verb and no brand word; R1-R12 the AR value of results.honest.notListed equals the EXPECTED table | True |
| M19 | home.compare.box_b_text deleted from ar.json | [jest] tag=mut_M19 start=14:58:04 end=14:58:08 rc=1 waited=0s | 4 failed, 50 passed, 54 total | P1 the AR placeholder set of home.compare.box_b_text equals EN; P3 the twelve keys exist in both catalogs and the key sets are equal (1,011 each); R1-R12 the AR value of home.compare.box_b_text equals the EXPECTED table; R13 one concentration form in quote_3 and both compare boxes | True |

Result: 19 / 19 KILLED, 0 SURVIVED, no equivalent mutant; every kill is a toEqual assertion (0 load / type errors in any mutant log). M17 edited src/i18n/en.json in place (byte copy en.json.base, restored to 89c6bc1d... and verified): see deviations.

## Comm set at base (spec section 7)
List: <scratchpad>/S81-11e_red/COMM_SET.txt (113 files, extracted by script from the spec's section 7, all present); reasons: <scratchpad>/S81-11e_red/COMM_SET_reasons.tsv (per file: reads ar.json / src/i18n / .copy-policy / b3a fixture, names one of the 12 keys, member of s11 / s81_08 / b3a, or backend-scanning client fence; every file has at least one grep reason). Run by path in ONE jest call:
[jest] tag=comm_base start=14:58:37 end=14:58:50 rc=1 waited=0s
Test Suites: 1 failed, 112 passed, 113 total; Tests: 4 failed, 1392 passed, 1396 total; Time 10.462 s. Failing nodes = exactly the baseline: config/nativeBundle.w37 "W3-7 (d) ... d5 react-native-gesture-handler is removed ...", "session 70 U4b ... k2 ...", "... k4 eslint-config-expo ...", "... k5 offline expo-install consistency ...". Matches spec 1.10 (1 failed / 112 passed suites, 4 failed / 1,392 passed tests). With the RED file at HEAD the set is 114 (the RED file adds its 15 RED + 39 PIN).

## Every [jest] line (my own wrapper jr.py; each launch first checked Win32_Process for a foreign node jest: none found, waited=0s every time)
[jest] tag=red_base start=14:55:13 end=14:55:16 rc=1 waited=0s
[jest] tag=proto_red start=14:55:54 end=14:55:57 rc=0 waited=0s
[jest] tag=proto_set29 start=14:55:59 end=14:56:06 rc=0 waited=0s
[jest] tag=proto_fences start=14:56:08 end=14:56:15 rc=1 waited=0s
[jest] tag=mut_M1 .. mut_M19 14:56:42 .. 14:58:08, each rc=1 waited=0s (table above)
[jest] tag=comm_base start=14:58:37 end=14:58:50 rc=1 waited=0s
[jest] tag=red_base_after_restore start=14:58:51 end=14:58:53 rc=1 waited=0s

## Restore check
ar.json written back from ar.json.base -> sha256 6b9471c6a03b5d322278afc26f09877158df598bf575cf0346f51735c7165f68 (= base); b3a_copy.json from b3a_copy.json.base -> 43a6378a09bb68e7301f99a4c26b1f3c6771bdd1d19228d559c85f983dc71fc2 (= base); en.json 89c6bc1d04fd94c44f27466e356aed1651ea7b79ba8dfb8dc052a266c9f5612f (= base). `git status --short --untracked-files=all` = `?? SmartCompareApp/__tests__/s11e/arCopy.s11e.test.ts` only (the __tests__/s11e directory holds only that file); HEAD 39ac80ba437760d1a77eaac9670faeea505f08f4. No scratch worktree was made, so none to remove; no jest left running (all foreground).

## Deviations
D1 (assertion form of R1-R12 and R15): the spec's 5.2 writes R1-R12 as expect({ k, v: AR[k] }).toEqual({ k, v: EXPECTED[k] }) and R15 as a contains check. That form prints the Arabic old / new values in the failure diff, which the brief forbids ("failure messages print keys, never Arabic values"). The file compares inside the expect and asserts a boolean: expect({ k, matches: AR[k] === EXPECTED[k] }).toEqual({ k, matches: true }); R13-R15 likewise compare booleans / ASCII tokens. Same kill power (every M1-M19 killed); the assertion kind is toEqual for all 15 RED nodes (no toBe / toContain used as the RED assertion; P3 uses toBe / toEqual).
D2 (M17 in place on en.json): the mutation table's M17 needs an EN edit; it was applied to src/i18n/en.json in place from a byte copy and restored to the base sha (verified), the only tracked file touched beyond the C1 / C3 prototype files. Ruling asked if the orchestrator wants M17 measured differently.
D3 (counts): the 29-suite prototype set is 406 tests (not the spec's 388) because the real RED file has 54 nodes where the spec's prototype file had 36; the fence run is 16 suites (15 fence files + b3a), the spec's section 7 names 15 fence files under the label "fourteen"; all 15 were run and recorded as measured.
D4 (E1 / r26): per R-S11E-11 the fixture E-row is GREEN's: the RED did not edit b3a_copy.json (only inside the restored prototype), so b3a/honestCopy r26 is GREEN at base (measured in the comm set: honestCopy passed); the spec 4.1 "r26 RED at base" no longer applies.

## Open questions for the gate
Q1 D2: accept M17 measured in place on en.json (byte copy, restored, sha-verified)?
Q2 D1: accept the boolean-compare form of R1-R12 / R15 (keys-only failure messages) in place of the spec's value-in-diff form?

## Files
- SmartCompareApp/__tests__/s11e/arCopy.s11e.test.ts sha256 b63c39c446052c3afe009380b9887fbdbc05f64f5b976bbaee0f1bf9278e9111 (9,195 B)
- scratch: notes.md, extract.json, template.ts, proto.py, mut.py, jr.py, mutants.json, set29.txt, fences.txt, COMM_SET.txt, COMM_SET_reasons.tsv, copies/*, *.log under <scratchpad>/S81-11e_red/
<scratchpad> = C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/ac74dbc6-6547-489d-9b8b-5df68ffc4f2f/scratchpad
