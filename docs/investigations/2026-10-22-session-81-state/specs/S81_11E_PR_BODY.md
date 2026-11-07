# S81-11e AR-COPY: the 12 Arabic strings of the first OTA re-read

Base origin/main f446155690c29aae54f79edfefff5bff93f96e1a; HEAD e18537057e5fa9f4e8a521d8aee4aa64c6f6bb48 (branch feature/s81-s11e-ar-copy; the GREEN commit 989e9a39 cut from 39ac80ba, replayed in the final round without conflict).

## Summary
The owner ruling of 2026-11-07 14:04 ("Fix strings first"): the first post-approval OTA waits on this unit. The delegated native read (specs/S81_11E_AR_COPY_REVIEW.md, sha256 9d6e3687...) found 1 WRONG and 11 AWKWARD Arabic values among the strings that ship in that OTA. This PR rewrites exactly those twelve AR values in SmartCompareApp/src/i18n/ar.json. A CLIENT unit, SAFE (R-S11E-7), NO runtime flag: it merges now and reaches users only in the first post-approval OTA. EN, every key and every placeholder are unchanged.

## Change list (4 files, +194 / -13)
- SmartCompareApp/src/i18n/ar.json: the twelve value lines only (12 / 12), raw UTF-8, CRLF kept.
- SmartCompareApp/__tests__/s11e/arCopy.s11e.test.ts: NEW, the frozen RED file (54 nodes), unchanged by GREEN and the final round (LF sha256 b63c39c446052c3afe009380b9887fbdbc05f64f5b976bbaee0f1bf9278e9111, blob d2a00c64).
- SmartCompareApp/__tests__/fixtures/b3a_copy.json: the E-row E1 (one line).
- CLAUDE.md: one dated bullet inside the S81-11 client block.

## [NATIVE READ] (the values live in the diff; verdict from the review table)
| key | review verdict |
|---|---|
| home.errors.comparison | WRONG (read as a roadmap promise) |
| home.errors.categoryNotLive | AWKWARD (verbless fragment) |
| home.errors.insufficientDataReason.placeholder_identity | AWKWARD (wrong verb sense) |
| home.errors.insufficientData | AWKWARD (calqued 'with', lost 'swap in') |
| results.honest.notListed | AWKWARD (calque; misplaced 'yet') |
| results.price.lastSeen | AWKWARD ('last online' sense) |
| results.price.lastSeenNoStore | AWKWARD ('last online' sense) |
| onboarding.s1.quote_3 | AWKWARD (transliteration opens with the word 'or') |
| onboarding.s17.tag_echoes_body | AWKWARD (redundant 'peers your age'; 'pair' ambiguity) |
| home.compare.box_a_text | AWKWARD ('or' collision; one EDP form) |
| home.compare.box_b_text | AWKWARD ('or' collision; one EDP form) |
| home.headerCounter.resets | AWKWARD (hour word missing; align with siblings) |

The GREEN agent re-read all twelve suggestions as a Gulf Arabic reader and adopted every one as written (no pin-fix of the RED EXPECTED table).

The ONE adversary (correctness, with the copy-policy, a11y, parity and bidi checks folded in; specs/S81_11E_ADV1_correctness.md) ran the second native-read pass of all twelve values against the EN meaning, the placeholders, the review reason and each render site: all twelve ADOPTED as written (OK, no improvement suggested, no MAJOR). Per key: home.errors.comparison OK (purpose clause + imperative; the roadmap-promise reading gone); home.errors.categoryNotLive OK (full clause, future verb; see L6); home.errors.insufficientDataReason.placeholder_identity OK; home.errors.insufficientData OK (carries 'swap in'); results.honest.notListed OK (agreement with the masculine Size / Concentration labels; 'yet' attaches to 'not listed'); results.price.lastSeen OK and results.price.lastSeenNoStore OK ({{date}} = formatAsOfDate, a date phrase); onboarding.s1.quote_3 OK (opens RTL; the two Latin tokens split by a strong-RTL word); onboarding.s17.tag_echoes_body OK (no 'pair' ambiguity; drops the EN 'just'); home.compare.box_a_text OK and home.compare.box_b_text OK (one EDP form); home.headerCounter.resets OK (the hour word, = the a11yResets / paywall siblings; see L7). Zero harakat / shadda / tanween, zero bidi controls, zero Arabic-Indic digits, no banned_ar / scary_vocab_ar hit, placeholders = EN in all twelve.

## E-rows
| E | file:line | change | LF blob base -> head |
|---|---|---|---|
| E1 | SmartCompareApp/__tests__/fixtures/b3a_copy.json:79 | the AR onboarding.s1.quote_3 value = the new catalog value (b3a r26 pins live AR to the fixture) | c09ba224 -> ca06964c |

## Counts
- RED file: 54 nodes (15 RED + 39 PIN); at base 15 failed / 39 passed (every failure a toEqual); at HEAD 54 / 54 passed.
- Mutants: 19 / 19 KILLED at the RED (M1-M12 old value per key, M13-M15 placeholder dropped, M16 shadda, M17 EN change, M18 banned pattern, M19 key deleted).
- The 29-suite key set at HEAD: 29 / 29 suites, 406 / 406 tests.

## Adversary and final round
- Adversary (specs/S81_11E_ADV1_correctness.md): SOUND, 0 blocking / 0 major / 3 minors (m1 -> L6, m2 -> L7, m3 -> the prove-nothing note below). It re-applied 14 of the 19 spec mutants plus 5 of its own (A1 a sibling resets_at loses the hour word -> R15; A2 E1 undone -> b3a r26; A3 a non-twelve AR key changed -> the identity script rc 1; A4 an RLM before EDP -> P4 + R11; A5 quote_3 EDT transliterated -> R8 + R13): 19 / 19 KILLED, every restore sha-verified.
- Rulings: specs/RULINGS_S81_11E.md (R-S11E-7..12), specs/GATE_S81_11E.md (GC-1..10), specs/RULINGS_REBASE_S81_11E.md (RB-11E-1..6). No fix round, no re-verifier, no round commit (RB-11E-3): no pin rows were added.
- Final round (RB-11E-2): the GREEN commit 989e9a39 replayed with git rebase --onto from base 39ac80ba onto origin/main f446155690c29aae54f79edfefff5bff93f96e1a (#395 S81-24) -> HEAD e18537057e5fa9f4e8a521d8aee4aa64c6f6bb48. No conflict. Patch-id equal: the commit (7d2784ad... before and after) and each of the four file hunks. Main changed no SmartCompareApp/ file between 39ac80ba and f4461556 (its 8 files: CLAUDE.md, app/api/auth_routes.py, app/middleware/request_id.py, app/services/auth_throttle.py and four tests/ files), so the client base record of the RED round stands for the new base.
- The frozen RED file: LF blob d2a00c64 unchanged; LF sha256 b63c39c446052c3afe009380b9887fbdbc05f64f5b976bbaee0f1bf9278e9111 = GC-1 (the rebase checkout wrote the working copy CRLF under core.autocrlf=true; git status clean). ar.json working sha256 e40b5236... and b3a_copy.json 76ed94a3... unchanged.

## Identity (R-S11E-8; re-run at the replayed HEAD against origin/main f4461556, rc 0)
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

## Gates at the replayed HEAD (jest 29.7.0, node v24.11.1, tsc 5.9.3, eslint 9.39.4; by path from SmartCompareApp through the junction; one jest at a time, a foreign G9 jest waited for, never killed)
- The RED file: 1 suite, 54 / 54 passed.
- The 29-suite key set: 29 / 29 suites, 406 / 406 tests.
- Comm set, MEASURED at HEAD: the 113 members of specs/S81_11E_COMM_SET.txt + the RED file = 114 suites in one run: 113 passed / 1 failed suites; 1,446 passed / 4 failed of 1,450 tests. The 4 = the config/nativeBundle.w37 drift nodes d5, k2, k4, k5 = the base record (the RED round at 39ac80ba: 1,392 passed / 4 failed of the 113; main has changed no client file since). branch-only-new = EMPTY.
- Fences (the 15 backend-scanning client fence files + b3a/honestCopy): 15 / 16 suites, 257 passed / 4 failed of 261 (the same four w37 nodes); b3a green.
- eslint on the RED file rc 0, no output; tsc --noEmit -p tsconfig.json rc 0, no output.
- The six CLAUDE.md readers by the import graph, once (the unit's only pytest; the then-main CLAUDE.md carries the S81-24 block):
  [pyt] tag=s11e-fin-cmdreaders start=2026-11-07 15:31:08 end=2026-11-07 15:31:34 elapsed=26s bound=1200s status=OK rc=0 (510 passed, 13 warnings; netguard blocked 24 attempts from the 2 usual S81-04 nodes)
- FULL jest once (LC-7; full.json): 411 suites (406 passed, 2 failed, 3 pending); 4,060 tests = 4,029 passed + 5 failed + 13 pending + 13 todo; this unit's 54 inside. The 5 failed = the four w37 drift nodes + HistoryScreen.mobileJank.m21 MB-flows-08 on a jest 5,000 ms test timeout under box load (the suite reads none of the twelve keys; re-run alone twice: 4 / 4 passed both times). Against the baseline 3,976 passed + the four w37 nodes + 13 + 13: 3,976 + 54 = 4,030 expected passed, measured 4,029 + the one timeout node green alone.
- git diff --name-only origin/main...HEAD = exactly the four files; git diff --check clean; no conflict markers.
- Not applicable / not run: the hook test files (the unit touches no .githooks file; RB-11E-4), the backend comm set, the CI-order set and the corpus gate (no backend, migration or app/ file), ruff / py_compile (no python file), flag ON / OFF (no runtime flag; the identity script replaces flag-OFF identity), a base full jest in a scratch worktree (GC-9: a scratch worktree has no node_modules and no junction may be created).

## Stated limits
- L1 The native read is an agent's (the delegated reader, the GREEN re-read, the adversary's second pass), not a human Gulf speaker's; the owner's final look is this diff.
- L2 Bidi on device is not tested: quote_3 and both compare boxes hold Latin EDP / EDT inside RTL lines, and lastSeen keeps the Latin store name first; jest checks bytes, not Hermes / iOS layout.
- L3 The OTA follows the merge and is the relay's step; this PR ships nothing by itself.
- L4 No EN change and nothing else in src/: the stale EN defaultValue of onboarding.s17.tag_echoes_body in Step17Notifications.tsx:121-122 stays (it renders only if the key were missing).
- L5 The 16 NATURAL rows and the two Arabic words for 'brand' in the catalog are unchanged.
- L6 (adversary m1) The fragrance-only empty state (ResultsScreen.tsx:875) pairs the title home.categories.fragrancesOnly with the body home.errors.categoryNotLive; both end in the word for 'for now', so it repeats. The pairing pre-exists this unit (the old body ended the same way); not a defect of the new value.
- L7 (adversary m2) home.headerCounter.resets gains one word (about six characters) inside the header pill (HomeScreen.tsx:1078: fixed 28 pt height, no numberOfLines / flexShrink); its fit at narrow RTL widths is unmeasured in jest and belongs to the owner TestFlight device check (S81-11 owner step 5), beside L2.
- Prove-nothing note (adversary m3): R13 / R14 on the twelve keys are subsumed by R1-R12; P2 checks the test table itself; P1 / P4 / P5 on the twelve hold whenever R1-R12 hold (they add weight only as co-killers: M16, M18, A4); R15 carries independent weight only through the two siblings (A1). No jest row pins the identity of the non-twelve keys or the CLAUDE.md bullet text: the identity script and the six CLAUDE.md readers are the only gates there.

## Owner steps
None to merge (merge on 7 / 7 green). The owner's final look at the diff; after the merge the relay re-runs the OTA preflight at the new main and publishes the first post-approval OTA (eas update --channel production); nothing for this PR on the EAS side.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
