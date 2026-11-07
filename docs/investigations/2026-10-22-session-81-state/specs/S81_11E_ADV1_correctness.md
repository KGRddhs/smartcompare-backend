# S81-11e AR-COPY ADVERSARY REPORT - lens correctness (Opus 5.5, 2026-11-07 15:14-15:22 AST)

Written under <scratchpad>/S81-11e_adv/ (the shell heredoc was refused by the box's ~7 KB Bash command limit, so the body went through the Write tool; ASCII / LF checked by the shell afterwards); <scratchpad> = C:/Users/SYNACK~1/AppData/Local/Temp/claude/cde30765822f13ce/ac74dbc6-6547-489d-9b8b-5df68ffc4f2f/scratchpad.

VERDICT: SOUND (0 blocking, 0 major, 3 minor -> stated limits per LC-4).

## Where the work ran
GC-9 governs: the REAL worktree sc-s81-s11e at the GREEN HEAD (the harness's scratch-worktree sentence does not apply to this client unit: no node_modules there and no junction may be created). Every probe on byte copies (<scratchpad>/S81-11e_adv/copies/, sha-verified) under the lock directory .qa-mutation.lock/ (gitignored by .qa-*/), restored and sha-verified after each probe; lock removed at the end; `git status --short` EMPTY at the end; HEAD unchanged; the node_modules junction untouched. One jest at a time (foreign-jest check before each launch: none waited). No pytest run by this agent (none assigned by GC-9).

## HEAD verification
- HEAD 989e9a39e550962d3519f0d6f26b3ef823948c1a on feature/s81-s11e-ar-copy, parent 39ac80ba (one commit). numstat: CLAUDE.md +1/-0, b3a_copy.json +1/-1, arCopy.s11e.test.ts +180/-0, ar.json +12/-12 (= +194 / -13 as the PR body says).
- RED file sha256 b63c39c446052c3afe009380b9887fbdbc05f64f5b976bbaee0f1bf9278e9111 = GC-1 (first and last); no pin-fix was made.
- Working shas = the GREEN table: ar.json e40b5236..., b3a_copy.json 76ed94a3..., CLAUDE.md 57465c15..., en.json 89c6bc1d... (unchanged).

## Re-runs from the exact bytes (node v24.11.1, jest 29.7.0, by path through the junction)
[jest] tag=adv_red start=15:15:24 end=15:15:25 rc=0 -> 1 suite, 54 / 54 passed
[jest] tag=adv_set29 start=15:15:27 end=15:15:34 rc=0 -> 29 / 29 suites, 406 / 406 tests (includes copy-policy.test.ts, i18n.test.ts, no-missing-referenced-keys, no-deleted-keys, plurals, digitPolicy: the EN/AR parity and copy-policy suites)
[jest] tag=adv_comm start=15:18:15 end=15:18:28 rc=1 -> 114 suites (113 COMM_SET + RED): 113 passed / 1 failed; 1,446 passed / 4 failed; the 4 = config/nativeBundle.w37 d5, k2, k4, k5 (the base drift baseline, comm_base.log 4 failed / 1,392 passed of 113): nothing new
[jest] tag=adv_fences start=15:18:31 end=15:18:37 rc=1 -> 16 suites: 15 passed / 1 failed; 257 passed / 4 failed (the same four w37 nodes); b3a green
Flag ON / OFF: not applicable (no runtime flag; the identity invariant replaces flag-OFF identity). The error-handler mapping, billing R-A3 and the PLAN section 0 contract freeze are not touched (no src code, no backend, no API key or shape change): verified by the diff (only ar.json values, one fixture line, one CLAUDE.md line, the RED file).

## Identity (re-run of <scratchpad>/S81-11e_green/identity_check.py, rc 0; output <scratchpad>/S81-11e_adv/identity.out)
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
Independent proofs: `git diff -U0 39ac80ba HEAD -- ar.json` adds exactly twelve `+  "<key>"` lines, the twelve keys. Against the review table (sha256 9d6e3687..., = the PR body): every WRONG / AWKWARD row's suggestion == the live HEAD value (12 / 12 MATCH), every NATURAL row's live value == the table (16 / 16). A scan of the 634 ts/tsx/json/js/md files under SmartCompareApp (node_modules, ios, android excluded) finds none of the twelve BASE values anywhere (no stale fixture or snapshot left).

## Mutants (on byte copies; <scratchpad>/S81-11e_adv/amut.py, results amutants.json; every restore sha-OK)
| id | mutant | result | killed by |
|---|---|---|---|
| M1 | categoryNotLive = base | 1 failed | R1 |
| M3 | notListed = base | 1 failed | R3 |
| M4 | lastSeen = base | 2 failed | R4 + R14 |
| M6 | comparison = base | 1 failed | R6 |
| M8 | quote_3 = base | 2 failed | R8 + R13 |
| M9 | tag_echoes_body = base | 1 failed | R9 |
| M10 | box_a_text = base | 2 failed | R10 + R13 |
| M12 | resets = base | 2 failed | R12 + R15 |
| M13 | lastSeen {{store}} dropped | 2 failed | P1 + R4 |
| M15 | resets {{time}} dropped | 3 failed | P1 + R12 + R15 |
| M16 | shadda in comparison | 2 failed | P4 + R6 |
| M17 | EN box_a EDP->EDT | 1 failed | P6 |
| M18 | banned_ar[0] appended to notListed | 2 failed | P5 + R3 |
| M19 | box_b_text deleted | 4 failed | P1 + P3 + R11 + R13 |
| A1 (own) | paywall.limit.resets_at loses the hour word (a sibling, not of the twelve) | 1 failed | R15 |
| A2 (own) | E1 undone (fixture quote_3 = base value) | 1 failed of 17 (b3a pair) | b3a r26 |
| A3 (own) | a non-twelve AR key changed (home.categories.comingSoon) | identity rc 1 | identity script (2 FAIL lines); no jest row (by design, R-S11E-8) |
| A4 (own) | RLM inserted before EDP in box_b | 2 failed | P4 + R11 |
| A5 (own) | quote_3 EDT replaced by the Arabic 'or'-form transliteration | 2 failed | R8 + R13 |
14 of the 19 spec mutants + 5 own: 19 / 19 KILLED.

## The second native-read pass (Gulf Arabic reader; EN meaning, placeholders, review reason, render site)
| key | render site | read | verdict |
|---|---|---|---|
| home.errors.comparison | services/errorCopy.ts:109 | a purpose clause + imperative ('for a more precise match, type the brand and the fragrance name'); the roadmap-promise reading is gone; carries the EN intent | OK |
| home.errors.categoryNotLive | errorCopy.ts:97; ResultsScreen.tsx:875 empty-state body | a full clause with the future verb; natural | OK (see m1) |
| home.errors.insufficientDataReason.placeholder_identity | the S81-20 reason sentence | 'to identify the two products' carries 'tell which products these are' | OK |
| home.errors.insufficientData | errorCopy.ts:95 | 'try two other fragrances and type the brand and name' carries 'swap in'; natural | OK |
| results.honest.notListed | ResultsAccordion.tsx:125 and :150 ('<label>: <value>' with Size / Concentration, both masculine), ResultsContent.tsx:373 | 'not mentioned yet by the stores we follow'; agreement with the masculine labels correct; 'yet' now attaches to 'not listed' | OK |
| results.price.lastSeen | ResultsContent.tsx:173 (stale provenance, numberOfLines 1) | '{{store}}, last spotted on {{date}}'; {{date}} = formatAsOfDate (fieldStatusView.ts:91, ar-SA-u-ca-gregory month + day: a date phrase, never a relative word), so the preposition before the date reads right | OK |
| results.price.lastSeenNoStore | same | same, without the store | OK |
| onboarding.s1.quote_3 | Step01Welcome.tsx:98 | 'An EDP or EDT version of the same perfume?'; the 'or ... or' collision is gone; opens with an Arabic word so the base direction is RTL; the two Latin tokens are separated by a strong-RTL word, so no LTR run merges them; Arabic question mark | OK |
| onboarding.s17.tag_echoes_body | Step17Notifications.tsx:120 (NotificationTag body) | 'when shoppers your age compare the same two products'; no 'husband' ambiguity; drops the EN 'just' (acceptable for a tag description) | OK |
| home.compare.box_a_text | TwoInputShell.tsx:488 (TextInput placeholder) | one product, one form; the trailing Latin EDP sits at the line end of an RTL placeholder | OK |
| home.compare.box_b_text | same | same | OK |
| home.headerCounter.resets | HomeScreen.tsx:1078 (header pill, after the middle dot) | 'renew at {{time}}' with the hour word, = the a11yResets and paywall siblings; {{time}} = formatResetClock HH:MM (utils/resetTime.ts:62-71), so the hour word is right | OK (see m2) |
Checks by reading and by script: placeholders identical to EN in all twelve; zero harakat / shadda / tanween in the twelve (the brand word does not occur in them); zero bidi controls; zero Arabic-Indic digits; no banned_ar or scary_vocab_ar hit (policy read from src/i18n/.copy-policy.json); no standalone compare verb, no brand word. No value reads wrong or awkward: NO MAJOR, no suggested replacement.

## CLAUDE.md bullet and PR body against the bytes
- CLAUDE.md line 583, directly after the S81-11 'Stated limits' bullet (:582) and before the blank line; pure ASCII; CRLF kept (CR == LF == 1,079); the text is in the spec section 8 verbatim; it names all twelve keys; its claims (1 WRONG + 11 AWKWARD; EN, keys, placeholders unchanged; pinned by the RED file; the OTA waits on the unit) hold.
- PR_BODY.md: 5,710 bytes, LF, non-ASCII only on line 75 (the attribution); title as ruled; the twelve keys with verdicts (= the review table); E1 at b3a_copy.json:79 (verified); counts verified against the logs (RED at base 15 failed / 39 passed; 15 RED + 39 PIN = 54; mutants 19 / 19 killed with every restore sha-OK in the RED mutants.json; set29 29 / 406; comm 1,446 / 4 at HEAD vs 1,392 / 4 at base; fences 257 / 4); the identity block equals my re-run; the [pyt] line equals cmdreaders.log (510 passed); L1-L5 and the owner steps present; no personal value.

## Findings
Blocking: none. Major: none.
Minor (stated limits, LC-4):
- m1 categoryNotLive in the ResultsScreen empty state sits under the title home.categories.fragrancesOnly, which also ends in the word for 'for now'; the word repeats in title and body (the pairing pre-exists; the body already ended so; not a defect of the new value).
- m2 home.headerCounter.resets grows by one word (about 6 characters) inside the 28 pt header pill (styles.headerCounter: row, fixed height; the Text has no numberOfLines / flexShrink); the narrow-width RTL fit is unmeasured in jest and belongs to the owner's TestFlight device check (S81-11 owner step 5), beside the PR body's L2 bidi limit.
- m3 the prove-nothing rows below are redundant, not wrong.

## Prove-nothing rows
- R13 and R14 on the twelve keys are subsumed by R1-R12 (any change to those values fails R1-R12 first; no mutant kills R13 / R14 alone); R15 carries independent weight only through the two siblings (killed alone by A1).
- P2 checks the test's own EXPECTED table, not the product.
- P4 and P5 on the twelve values hold whenever R1-R12 hold (they certify the EXPECTED table is policy-clean); they add weight only as co-killers (M16, M18, A4).
- P1 is subsumed by R1-R12 + P2 for the twelve.
- No jest row pins the non-twelve keys' identity or the CLAUDE.md bullet text; the identity script (A3) and the six CLAUDE.md readers (the GREEN's [pyt] OK) are the only gates there.

## Not run / not applicable
The FULL jest (LC-7, the final round); pytest (GC-9 assigns none to the adversary; the GREEN's `[pyt] tag=s11e-cmdreaders ... status=OK rc=0` with 510 passed is cited, not re-run); the hook test files, the backend comm set, the CI-order set, the corpus gate, ruff / py_compile (no backend, .githooks, migration or python file).
