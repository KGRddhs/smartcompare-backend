# S81-11e AR-COPY: the 12 Arabic strings of the first OTA re-read

Base 39ac80ba437760d1a77eaac9670faeea505f08f4; HEAD 989e9a39e550962d3519f0d6f26b3ef823948c1a (branch feature/s81-s11e-ar-copy; the final round replays it onto the then-main).

## Summary
The owner ruling of 2026-11-07 14:04 ("Fix strings first"): the first post-approval OTA waits on this unit. The delegated native read (specs/S81_11E_AR_COPY_REVIEW.md, sha256 9d6e3687...) found 1 WRONG and 11 AWKWARD Arabic values among the strings that ship in that OTA. This PR rewrites exactly those twelve AR values in SmartCompareApp/src/i18n/ar.json. A CLIENT unit, SAFE (R-S11E-7), NO runtime flag: it merges now and reaches users only in the first post-approval OTA. EN, every key and every placeholder are unchanged.

## Change list (4 files, +194 / -13)
- SmartCompareApp/src/i18n/ar.json: the twelve value lines only (12 / 12), raw UTF-8, CRLF kept.
- SmartCompareApp/__tests__/s11e/arCopy.s11e.test.ts: NEW, the frozen RED file (54 nodes), unchanged by GREEN (sha256 b63c39c4...).
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

## E-rows
| E | file:line | change | LF blob base -> head |
|---|---|---|---|
| E1 | SmartCompareApp/__tests__/fixtures/b3a_copy.json:79 | the AR onboarding.s1.quote_3 value = the new catalog value (b3a r26 pins live AR to the fixture) | c09ba224 -> ca06964c |

## Counts
- RED file: 54 nodes (15 RED + 39 PIN); at base 15 failed / 39 passed (every failure a toEqual); at HEAD 54 / 54 passed.
- Mutants: 19 / 19 KILLED at the RED (M1-M12 old value per key, M13-M15 placeholder dropped, M16 shadda, M17 EN change, M18 banned pattern, M19 key deleted).
- The 29-suite key set at HEAD: 29 / 29 suites, 406 / 406 tests.

## Identity (gate-time script, R-S11E-8)
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

## Comm set and fences (jest 29.7.0, node v24.11.1, by path through the junction)
- Comm set (113 suites, specs/S81_11E_COMM_SET.txt) + the RED file = 114: at HEAD 113 passed / 1 failed suites, 1,446 passed / 4 failed tests; at base (RED run) 1,392 passed / 4 failed of the 113. Failing nodes at HEAD = at base = the four config/nativeBundle.w37 drift nodes (d5, k2, k4, k5); branch-only-new EMPTY.
- Fences (15 backend-scanning client fence files + b3a/honestCopy): 15 / 16 suites, 257 passed / 4 failed tests (the same four w37 nodes); b3a green.
- eslint 9.39.4 on the RED file rc 0; tsc 5.9.3 --noEmit -p tsconfig.json rc 0.
- The six CLAUDE.md readers by the import graph (the unit's only pytest):
  [pyt] tag=s11e-cmdreaders start=2026-11-07 15:10:44 end=2026-11-07 15:11:03 elapsed=19s bound=1200s status=OK rc=0 (510 passed)
- Not applicable: the hook test files, the backend comm set and the corpus gate (no backend, .githooks or migration file). The FULL jest runs once in the final round (LC-7; baseline 3,976 passed + the four w37 nodes).

## Stated limits
- L1 The native read is an agent's (the delegated reader, the GREEN re-read, the adversary's second pass), not a human Gulf speaker's; the owner's final look is this diff.
- L2 Bidi on device is not tested: quote_3 and both compare boxes hold Latin EDP / EDT inside RTL lines, and lastSeen keeps the Latin store name first; jest checks bytes, not Hermes / iOS layout.
- L3 The OTA follows the merge and is the relay's step; this PR ships nothing by itself.
- L4 No EN change and nothing else in src/: the stale EN defaultValue of onboarding.s17.tag_echoes_body in Step17Notifications.tsx:121-122 stays (it renders only if the key were missing).
- L5 The 16 NATURAL rows and the two Arabic words for 'brand' in the catalog are unchanged.

## Owner steps
None to merge (merge on 7 / 7 green). The owner's final look at the diff; after the merge the relay re-runs the OTA preflight at the new main and publishes the first post-approval OTA.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
