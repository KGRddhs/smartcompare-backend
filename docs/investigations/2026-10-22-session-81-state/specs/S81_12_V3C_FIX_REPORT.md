# V3C_FIX_REPORT: S81-12 LEGAL-V3, PATH C of item 26 (fix round, Opus 5.5 fix agent, 2026-11-12)

Verdict: COMMITTED. HEAD before a0244f4403c55326ddf0171455805e7d2a5879aa; HEAD after 35b603f3720800ee68e2c025ef286af58b4da808 (one parent a0244f44; through the hook, 'All checks passed!'); branch feature/s81-legal-v3; main 6b909e0a92067d6b3562eee325e4956c116441f7 (git fetch origin main at 06:31: unmoved). Not pushed. git status --short at the end: empty.

## Steps (V3C-7)
(1) opening checks: branch, HEAD a0244f44, empty status, fetch = 6b909e0a, the 12 check values of V3C_INPUTS.txt equal (6 artefacts, 3 frozen files, 2 machinery data files, CLAUDE.md); legal_v3_window.json absent; junction present.
(2) RED: the fixture + V3C-1..V3C-5 appended after G-o; at a0244f44 28 / 28 red, every one an AssertionError (28 'E   AssertionError' lines, no other error).
(3) GREEN through the machinery (v3c_machinery_fix.py = the amendment's script + C2 inside variant C + D3 in the Terms snapshots :45): machinery rc 0; fill_in_legal.py rc 0; --dry-run rc 0 with 0 bytes; render_legal_landing.py --check rc 0; cmp of the six artefacts (LF) with s12/v3c/final/expected: all BYTE-EQUAL. Committed blobs re-hashed from git: f5be1e21 / a5fb7538 / 61263e7f / 1d504d89 / 24b0f10f / 6c666d3e; fence digest from the committed catalogs 040af0c5....
(4) pins and C7 as the E table below.
(5)-(8) gates (every pytest after the cross-session probe; waits 2-75 s; one foreign S81-07 round seen live at 06:36 and 07:04-07:09 and waited out):
  red:
    [hermeticity] sentinel checked 28 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_no_ended_story_about_openai[en]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_no_ended_story_about_openai[ar]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[en-S1]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[en-S2]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[en-B1]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[en-P4g]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[en-P4r]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[en-P4k]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[en-C5]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[en-S3]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[en-S4]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[en-J8]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[ar-S1]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[ar-S2]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[ar-B1]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[ar-P4g]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[ar-P4r]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[ar-P4k]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[ar-C5]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[ar-S3]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[ar-S4]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_restored_sentences_equal_live[ar-J8]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_s4_scope_phrase[en] - Asserti...
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_s4_scope_phrase[ar] - Asserti...
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_s4_applies_sentence_scoped[en]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_s4_applies_sentence_scoped[ar]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_terms_s6_verify_before_relying[en]
    FAILED tests/test_s81_12_gate_rows.py::test_v3c_terms_s6_verify_before_relying[ar]
    [pyt] tag=s12f-red start=2026-11-12 06:39:08 end=2026-11-12 06:39:27 elapsed=18s bound=600s status=FAIL rc=1
  diag1:
    ================= 2 failed, 585 passed, 11 warnings in 30.60s =================
    [hermeticity] sentinel checked 587 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    FAILED tests/test_s81_12_legal_v3.py::test_r14_consent_v3_version_copy_and_fence
    FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded - Asserti...
    [pyt] tag=s12f-diag1 start=2026-11-12 06:52:29 end=2026-11-12 06:53:01 elapsed=32s bound=1200s status=FAIL rc=1
  unit:
    =================== 1 failed, 92 passed, 1 warning in 4.41s ===================
    [hermeticity] sentinel checked 93 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded - Asserti...
    [pyt] tag=s12f-unit start=2026-11-12 06:56:44 end=2026-11-12 06:56:49 elapsed=5s bound=600s status=FAIL rc=1
  legalset:
    ================= 1 failed, 586 passed, 11 warnings in 41.34s =================
    [hermeticity] sentinel checked 587 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded - Asserti...
    [pyt] tag=s12f-legalset start=2026-11-12 06:56:57 end=2026-11-12 06:57:40 elapsed=43s bound=1200s status=FAIL rc=1
  ciorder:
    ================ 1 failed, 1203 passed, 13 warnings in 53.48s =================
    [hermeticity] sentinel checked 1204 test(s)
    [netguard] blocked 24 attempt(s) from 2 node(s)
    FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded - Asserti...
    [pyt] tag=s12f-ciorder start=2026-11-12 06:57:49 end=2026-11-12 06:58:47 elapsed=58s bound=1200s status=FAIL rc=1
  unit2:
    =================== 1 failed, 92 passed, 1 warning in 3.62s ===================
    [hermeticity] sentinel checked 93 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded - Asserti...
    [pyt] tag=s12f-unit2 start=2026-11-12 07:00:40 end=2026-11-12 07:00:44 elapsed=5s bound=600s status=FAIL rc=1
  legalset2:
    ================= 1 failed, 586 passed, 11 warnings in 30.30s =================
    [hermeticity] sentinel checked 587 test(s)
    [netguard] blocked 0 attempt(s) from 0 node(s)
    FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded - Asserti...
    [pyt] tag=s12f-legalset2 start=2026-11-12 07:00:52 end=2026-11-12 07:01:24 elapsed=32s bound=1200s status=FAIL rc=1
  ciorder2:
    =========== 1 failed, 1203 passed, 13 warnings in 64.96s (0:01:04) ============
    [hermeticity] sentinel checked 1204 test(s)
    [netguard] blocked 24 attempt(s) from 2 node(s)
    FAILED tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded - Asserti...
    [pyt] tag=s12f-ciorder2 start=2026-11-12 07:02:05 end=2026-11-12 07:03:12 elapsed=67s bound=1200s status=FAIL rc=1
  readers:
    ====================== 510 passed, 13 warnings in 17.40s ======================
    [hermeticity] sentinel checked 510 test(s)
    [netguard] blocked 24 attempt(s) from 2 node(s)
    [pyt] tag=s12f-readers start=2026-11-12 07:03:19 end=2026-11-12 07:03:38 elapsed=19s bound=1200s status=OK rc=0
  (diag1 was a diagnostic run before the client fence edit; unit / legalset / ciorder were re-run as unit2 / legalset2 / ciorder2 after the CLAUDE.md edit, plus the six CLAUDE.md readers by the import graph.)
  client rows by path: [jest] tag=s12f-jest-rows start=06:55:53 end=06:56:11 rc=0 -- Test Suites: 8 passed, 8 total; Tests: 75 passed, 75 total (legalV3.s81_12, aiConsentVersion.s69, aiConsentV2.s75, aiConsentSheetScroll.s75, aiDispatchFence.s69, aiProcessingConsent.s69, step05Trust.s69, landing.brand.s69); jest 29.7.0
  tsc: TypeScript 5.9.3, [tsc] tag=s12f-tsc start=06:56:22 end=06:56:30 rc=0, 0 lines
  C7: the TypeScript printer (removeComments) output of HEAD vs new is byte-identical for both files
  FULL jest ONCE:
    [wait] jest-full waited 315s; probe clean at 07:09:13
    junction ok
    29.7.0
    [jest] tag=s12f-jest-full start=07:09:16 end=07:10:05 rc=1
    FAIL __tests__/config/nativeBundle.w37.test.ts (8.147 s)
    FAIL __tests__/config/nativeBundle.w37.test.ts (8.147 s)
    Test Suites: 1 failed, 3 skipped, 408 passed, 409 of 412 total
    Tests:       4 failed, 13 skipped, 13 todo, 4039 passed, 4069 total
    Snapshots:   41 passed, 41 total
  lint: ruff E9,F63,F7,F82 clean and py_compile ok on the seven edited test files; JSON parse ok on the eight JSON files; git diff --check clean; added-line sweep (@gmail, +973, 8-digit runs, key shapes) empty.
(9) CLAUDE.md (claude_md_edit.py, 10 replacements, each count 1, from the git bytes, CRLF written back; diff 3 lines), the PR body (<notes>/PR_BODY.md, 25,574 bytes, ASCII apart from the attribution line, ends with it), the ONE commit.
(10) THE COMM SET at the committed head:
comm set: 192 members (set sha256 4e9a695d..., identical to the stored record's member list); base = the stored record harness/base_records/6b909e0a.../4e9a695d....txt (18 failed ids, reused: no member added); head = 8 chunks at 35b603f3:
  comm-head-hchunk_00.out: ====================== 915 passed, 21 warnings in 46.53s ======================
  comm-head-hchunk_00.out: [hermeticity] sentinel checked 915 test(s)
  comm-head-hchunk_00.out: [netguard] blocked 3 attempt(s) from 1 node(s)
  comm-head-hchunk_00.out: [pyt] tag=s12f-comm-head-hchunk_00 start=2026-11-12 07:23:39 end=2026-11-12 07:24:28 elapsed=49s bound=1200s status=OK rc=0
  comm-head-hchunk_01.out: =========== 2471 passed, 1 skipped, 18 warnings in 96.93s (0:01:36) ===========
  comm-head-hchunk_01.out: [pyt] tag=s12f-comm-head-hchunk_01 start=2026-11-12 07:28:18 end=2026-11-12 07:29:57 elapsed=99s bound=1200s status=OK rc=0
  comm-head-hchunk_02.out: =============== 686 passed, 4 deselected, 11 warnings in 28.40s ===============
  comm-head-hchunk_02.out: [hermeticity] sentinel checked 686 test(s)
  comm-head-hchunk_02.out: [netguard] blocked 0 attempt(s) from 0 node(s)
  comm-head-hchunk_02.out: [pyt] tag=s12f-comm-head-hchunk_02 start=2026-11-12 07:31:58 end=2026-11-12 07:32:28 elapsed=30s bound=1200s status=OK rc=0
  comm-head-hchunk_03.out: = 997 passed, 26 skipped, 2 deselected, 1 xfailed, 13 warnings, 2 errors in 83.69s (0:01:23) =
  comm-head-hchunk_03.out: [pyt] tag=s12f-comm-head-hchunk_03 start=2026-11-12 07:33:22 end=2026-11-12 07:34:47 elapsed=85s bound=1200s status=FAIL rc=1
  comm-head-hchunk_04.out: =========== 1 failed, 2452 passed, 260 warnings in 95.97s (0:01:35) ===========
  comm-head-hchunk_04.out: [hermeticity] sentinel checked 2453 test(s)
  comm-head-hchunk_04.out: [netguard] blocked 0 attempt(s) from 0 node(s)
  comm-head-hchunk_04.out: [pyt] tag=s12f-comm-head-hchunk_04 start=2026-11-12 07:35:44 end=2026-11-12 07:37:23 elapsed=99s bound=1200s status=FAIL rc=1
  comm-head-hchunk_05.out: ========== 12 failed, 2891 passed, 64 warnings in 105.31s (0:01:45) ===========
  comm-head-hchunk_05.out: [hermeticity] sentinel checked 2903 test(s)
  comm-head-hchunk_05.out: [netguard] blocked 24 attempt(s) from 2 node(s)
  comm-head-hchunk_05.out: [pyt] tag=s12f-comm-head-hchunk_05 start=2026-11-12 07:38:18 end=2026-11-12 07:40:06 elapsed=108s bound=1200s status=FAIL rc=1
  comm-head-hchunk_06.out: ====== 4 failed, 1797 passed, 1 xfailed, 47 warnings in 78.33s (0:01:18) ======
  comm-head-hchunk_06.out: [pyt] tag=s12f-comm-head-hchunk_06 start=2026-11-12 07:40:59 end=2026-11-12 07:42:21 elapsed=81s bound=1200s status=FAIL rc=1
  comm-head-hchunk_07.out: ========== 1090 passed, 1 skipped, 35 xfailed, 16 warnings in 46.75s ==========
  comm-head-hchunk_07.out: [pyt] tag=s12f-comm-head-hchunk_07 start=2026-11-12 07:43:14 end=2026-11-12 07:44:03 elapsed=49s bound=1200s status=OK rc=0
  head failed ids: 19; comm -13 (branch-only-new): ['tests/test_s81_12_legal_v3.py::test_h1_merge_window_recorded']
  comm -23 (base-only, fixed or absent at head): []


## E-rows (file : place, old -> new, why at least as strict, class)
| file : place | old | new | strictness | class |
|---|---|---|---|---|
| tests/test_s81_12_legal_v3.py R2 (:533) EK7 | count of the dated 'programme ended on <date>' sentence in s4 == 1; no present-tense sentence anywhere | present-tense programme sentence == 1 in privacy s2, s4 (with the scope regex SCOPED_EN / _AR once) and Terms s8; region count == source count; the three EN ended regexes and the three AR ended phrases (marks-insensitive) absent from sources + regions | exact per-section counts + position of the scope + absence of every ended form: stricter than one count | EK (frozen, sanctioned) |
| tests/test_s81_12_legal_v3.py R3 (:557) EK8 + C6 | bare promise present in s2 / s8; APART absent | carve-out form exactly once in privacy s2 and Terms s8; EN: the sentence-initial bare promise absent in every section and both regions; AR: in every section and both regions count(NOT_SOLD_AR) == count(carve-out form from the fixture S1) | count + form + AR twin of the forbid (C6) | EK |
| tests/test_s81_12_legal_v3.py R4 (:578) EK9 | s5 dated 'data shared with OpenAI before <date>' (EN), any AR date | two AI bullets, D9 kept; main's undated carve-out line (fixture C5) exactly once as a line; no EN / AR date in s5 | byte-equal line + no date | EK |
| tests/test_s81_12_legal_v3.py R10 (:727) EK10 | d3 'A'; forks retired | d3 'C'; d3_training answer / inline / docs == main's; A + B equal to main's by digest (MAIN_D3_AB_SHA256 1a96f76c...); C == P4s + P4g + C2 + P4r from the fixture; openai_retention == main's by digest (MAIN_RETENTION_FORK_SHA256 9df7d8b9...); the rest of the row unchanged | every fork byte pinned by digest | EK |
| tests/test_s81_12_legal_v3.py R13 (:956) EK11 | privacy s4 carries the AI_SWITCH_DATE value | the value == TERMS_VERSION == effective dates (unchanged); the notice line of privacy and Terms (EN + AR) carries it; the value occurs exactly twice per document (effective-date line, then the notice line); privacy s4 and s5 carry no EN / AR date | adds the s5 no-date and the per-line census | EK |
| tests/test_s81_12_legal_v3.py R14 (:986) EK12 + C6 | EN body has no training claim | EN body 5 sentences, TRAINING_CLAIM_EN once and in sentence [3], [2] the transition ('some or all', OpenAI), [4] the not-sent sentence; AR: fixture J8 once and == AR sentence [3] of 5; the AR v2-digest check and the fence (version 3 + current digest) kept | position + count + AR twin | EK |
| tests/test_s81_12_legal_v3.py R16 (:1090) EK13 | OpenAI only in privacy s2/s4/s5; class 'history' | privacy {2,3,4,5}: s3 only via main's s3.6 bullet (fixture B1, once, inside 3.6, OpenAI count equal); classes: the programme (present, scoped), main's carve-out; C2 admitted in s4 by exact text; regions equal | named exceptions only | EK |
| tests/test_s81_12_legal_v3.py H1 / _h1_problems / _h1_tree (:1150-:1192) EK14 | record key openai_sharing_off_on | record key window_date; same comparison to TERMS_VERSION and AI_SWITCH_DATE / _AR; H1b's seven cases unchanged, written with window_date | the same comparison | EK |
| tests/test_s81_12_legal_v3.py constants + _v3c_text + row map docstring | - | SCOPED_EN / _AR, ENDED_EN / _AR, MARKS_AR, V3C_FIXTURE, the two main digests, OPENAI_SECTIONS / classes (EK13), the fixture reader | support of EK7-EK14 | EK |
| tests/test_s81_12_gate_rows.py G-a EK15 (renamed test_g_a_openai_30_day_sentence_below_the_programme) | SINCE sentence once in s4 | main's P4k once in s4, the last sentence of its paragraph, after P4g in the same paragraph; SINCE (EN, AR) absent from the four sources + regions | fact + position + absence | EK |
| tests/test_s81_12_gate_rows.py G-b EK16 | allow-list = the one dated history sentence | allow-list = S2, P4s, S4 by exact text (fixture); any other OpenAI + training + permission sentence refused (sources + regions) | three exact texts instead of one | EK |
| tests/test_s81_12_gate_rows.py G-c EK17 | CARVE sentence once in s4 | main's governed sentence once in s4; CARVE (EN, AR) absent from sources + regions; Terms s13 deletion sentence (fixture T95, main :91) once and inside s13 | fact + absence + T95 | EK |
| tests/test_s81_12_gate_rows.py G-h EK18 + C5 | EN three-clause notice; AR six elements incl. OpenAI / programme / ended | EN notice literal (two clauses) == the fixture's line; AR line == the fixture's N1 / N2 line exactly (date formatted), Anthropic + 'permission again' present, OpenAI / the programme name / 'ended' absent; regions carry the notice | exact line in both languages (was elements only in AR) | EK |
| tests/test_s81_12_gate_rows.py G-o EK19 | the ARFIX common construction once in s4 and s5 | main's AR governed sentence once in s4 and main's AR carve-out line once in s5 (fixture P4g / C5); the rare passive still forbidden | exact restored text | EK |
| tests/test_s81_12_gate_rows.py import + helpers + docstring | imported D3_HISTORY_* from the U8 suite | the import goes (C3); _history_sentence -> _v3c_text; NOTICE_FORBIDDEN_AR; +import json | support | EK |
| tests/test_s81_12_gate_rows.py V3C-1..V3C-5 (NEW, after G-o) | - | 28 nodes, red at a0244f44 on AssertionError only | new | NEW ROWS |
| tests/fixtures/legal_v3c_live_sentences.json (NEW) | - | live: 22 entries (S1 S2 B1 P4g P4r P4k C5 S3 S4 J8 T95, EN + AR) copied from main 6b909e0a with main path:line; ruled: 10 (P4s C2 N1 N2 D3, EN + AR) from the expected files, the notice date templated {date} | fixture | NEW |
| tests/test_legal_docs_u8.py (C3) | S81-12 docstring (d3 A, retired forks, history allow-list), D3_FORBIDDEN_EN['A'] widened, D3_HISTORY_EN / _AR, _d3_scan_text, T8 scans of the reduced text, test_t8_history_allow_list_is_exact | main's form (diff against 6b909e0a = the Anthropic E9 keys, PUBLIC_NAME_IDS, latin_ok and a reduced docstring paragraph only) | main's body | MAIN FORM |
| tests/test_legal_docs_u8_d3c.py (C4 + table E) | retired-fork rows (a) x3, (c), (d), (e) x2, (i), (j), (n) x2 + constants | main's bytes + COMPLETE_VALUES_EN AI_SWITCH_DATE (the notice scaffold) + TERMS_LICENCE_EN 'our AI providers' (EF6a) + docstring paragraph + (a) locatable: main's cross-fork check AND the head's per-fork loop | main's assertions back; locatable stronger than both | MAIN FORM / ADAPTED |
| tests/fixtures/legal_d3c_u8.json (OUTSIDE the V3C-8 (b) list: E-row) | S81-12 AR values (privacy_s2 / s5_carveout / terms_derived ended forms, retired list, s5_carveout_head, retired_d3_c) | main's bytes + the AI_SWITCH_DATE_AR key + the head's AR terms_licence (EF6c) | needed by C4's main form (the AR twins the d3c rows read) | MAIN FORM (deviation D1) |
| tests/test_legal_disclosure_s77.py | S81-12 ended-story constants and d1 / d2 / d3 / d4 rewrites | main's bytes + PRIVACY_PAGE_ADDRESSES 15 (crawler page) + d2 ADAPTED (scoped < governed < applies < exchange < retention in one paragraph, the photo guidance the next paragraph, C ends with the exchange, A / B carry neither, main's 'every comparison' anchor absent) + V3C_FIXTURE | main's body for d1 d3 d4 d5 d10; d2 order + paragraph checks | MAIN FORM / ADAPTED |
| tests/fixtures/legal_disclosure_s77.json | S81-12 AR ended values | main's bytes | main | MAIN FORM |
| tests/test_legal_s78.py r11 | dated CARVEOUT_EN template + R11 date formatting | main's CARVEOUT_EN and R11 head | main | MAIN FORM |
| tests/fixtures/legal_s78.json s5_carveout_ar | dated AR carve-out | main's value (tos_s8_openai_ar keeps the ARFIX T1 value) | main | MAIN FORM |
| tests/test_legal_docs_u8_polish.py a16, b4 | fork retirement / territories flip | main's bodies; the COMPLETE_VALUES comment re-worded (the notices) | main | MAIN FORM |
| scripts/legal_variants_u8.json, tests/fixtures/legal_fill_in_u8.json, the four pre-fill snapshots | - | machinery sources (OPTION F + C2 + D3), v3c_machinery_fix.py | - | MACHINERY |
| SmartCompareApp/__tests__/consent/aiConsentVersion.s69.test.ts | sha256 adfc77d2..., comment 'drops the training sentence' | sha256 040af0c5...; comment re-told (the training sentence stays; re-recorded with version 3) | recipe | CLASS T |
| SmartCompareApp/__tests__/consent/aiConsentV2.s75.test.ts | EN_SENTENCE = transition; retired-count 0; separators 3 | EN_SENTENCE / AR_SENTENCE = main's v2 sentence (main's form: it precedes the final), EN_TRANSITION / AR_TRANSITION + transitionPrecedes == 1, separators 4, AR_SECTION2 = the current five-sentence body | main's assertions + one more | MAIN FORM + CLASS T |
| SmartCompareApp/__tests__/s81_12/legalV3.s81_12.test.ts C3 (EK-C1) | 4 sentences; not.toMatch(TRAINING_CLAIM_EN) | 5 sentences; [3] matches TRAINING_CLAIM_EN, exactly once in the body; [4] not-sent; AR 5 sentences, [2] and [3] name OpenAI; header comments re-told | position + count | EK-C1 |
| SmartCompareApp/src/components/AiConsentSheet.tsx, src/services/aiConsent.ts (C7) | S81-12 deleted main's D3 = C comment sentences | main's sentences restored by script; the S81-12 sentence re-told; TS printer output without comments byte-identical HEAD vs new (34d605e3... / efedd538...) | no executable token | C7 comment-only |
| CLAUDE.md | U8 row ended story, consent row 'is gone' + adfc77d2, S81-12 row ended story / switch step | 10 exact replacements (claude_md_edit.log): :17, :199 x2, :641 x7 incl. the ONE V3C sentence (C2, D3, V3C-1..V3C-5, window_date) | - | DOCS |

## Footprint (git diff --name-only a0244f44 35b603f3: 33 files; the V3C-8 (b) list + tests/fixtures/legal_d3c_u8.json, deviation D1) and sha256 of every changed file at the committed head
```
adeaea13... CLAUDE.md
ea7db539... SmartCompareApp/__tests__/consent/aiConsentV2.s75.test.ts
50837396... SmartCompareApp/__tests__/consent/aiConsentVersion.s69.test.ts
d86f058e... SmartCompareApp/__tests__/s81_12/legalV3.s81_12.test.ts
8e50ebbd... SmartCompareApp/src/components/AiConsentSheet.tsx
6c666d3e... SmartCompareApp/src/i18n/ar.json
24b0f10f... SmartCompareApp/src/i18n/en.json
11a7412a... SmartCompareApp/src/services/aiConsent.ts
f5be1e21... app/legal/privacy_policy.md
a5fb7538... app/legal/privacy_policy_ar.md
61263e7f... app/legal/terms_of_service.md
1d504d89... app/legal/terms_of_service_ar.md
3d5ed385... landing/ar/privacy.html
122bc66b... landing/ar/terms.html
16a4e0e9... landing/privacy.html
341ca971... landing/terms.html
51fa914f... scripts/legal_variants_u8.json
df87b31a... tests/fixtures/legal_d3c_u8.json
a376526a... tests/fixtures/legal_disclosure_s77.json
d5d55954... tests/fixtures/legal_fill_in_u8.json
267a797b... tests/fixtures/legal_prefill_u8/privacy_policy.md
3384c321... tests/fixtures/legal_prefill_u8/privacy_policy_ar.md
9789b4b0... tests/fixtures/legal_prefill_u8/terms_of_service.md
04884fbb... tests/fixtures/legal_prefill_u8/terms_of_service_ar.md
b79dac8e... tests/fixtures/legal_s78.json
7a59c176... tests/fixtures/legal_v3c_live_sentences.json
c196a316... tests/test_legal_disclosure_s77.py
ddc9c9f7... tests/test_legal_docs_u8.py
7530ed23... tests/test_legal_docs_u8_d3c.py
e5b3a933... tests/test_legal_docs_u8_polish.py
6b29b26f... tests/test_legal_s78.py
ea044e69... tests/test_s81_12_gate_rows.py
80ada4e8... tests/test_s81_12_legal_v3.py
```

## Deviations
- D1 tests/fixtures/legal_d3c_u8.json is outside the V3C-8 (b) list: C4's main form of tests/test_legal_docs_u8_d3c.py reads main's AR twins (privacy_s2, s5_carveout, terms_derived) from this fixture; it is main's bytes plus two head lines (AI_SWITCH_DATE_AR for the notice scaffold, the ARFIX-era AR licence 'our AI providers'). An E-row with its reason (not a STOP by V3C-8 (b)).
- D2 the fixture carries one live entry beyond the ruled list: T95 (the unchanged Terms s13 deletion sentence, main :91 [2]) read by EK17 (G-c) as the ruling's 'Terms :95 carries its unchanged deletion sentence exactly once'; the notice lines N1 / N2 are stored with the date as '{date}' so the window commit's re-date does not need a fixture re-record.
- D3 no base scratch worktree was created: the re-derived member list (derive_comm.py with the V3C terms legal_v3c_live_sentences / AiConsentSheet / legal_variants added) is byte-identical to the stored set 4e9a695d (192 members), so every base result is the stored record (LC-6) and no member was added.
- D4 V3C-2's region check compares the region count with the source count (and >= 1) rather than '== 1' in the region (the same for every restored sentence, each of which occurs once).
- D5 the PR body's older [NATIVE READ] items (the ARFIX body's list) are replaced by a pointer to the evidence files to stay under 25,600 bytes; the C9 list of this round is kept in full; the comm-set figure is in this report (measured after the commit).
- D6 EK13 (R16) also pins the AR s3 OpenAI occurrence by the fixture's B1 text (the EN class rule is EN-only as before).

## Not measured
- the pre-commit hook test files (no .githooks change); mutants (the re-verifier's, V3C-10 (5)).
