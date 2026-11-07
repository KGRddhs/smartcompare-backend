# S81-11e AR-COPY -- group spec (one-unit group form)

Spec writer: Opus agent of wf_2988ab34-388 (scripts/wf_group_spec.js, one-unit form), 2026-11-07.
Base sha for every measurement: 39ac80ba437760d1a77eaac9670faeea505f08f4 (worktree
C:/Users/SynAckITPC/Documents/AI/sc-s81-s11e, detached, `git status --short` empty before and after
this run). Source of truth: specs/S81_11E_AR_COPY_REVIEW.md (10,991 B, sha256
9d6e368742bed107176f40f0fb4d9109c9e0d6bdf3f6403061b8073337a6f996, re-hashed in this run) under the
brief specs/S81_11E_BRIEF.md (R-S11E-0..6). Binding: s81-common.txt LC-1..LC-9, PLAN_S81, PLAN_S80
section 0 + R-A13 (evidence standard), the copy policy src/i18n/.copy-policy.json.

Byte note: this file is pure ASCII and LF EXCEPT the lines that quote an Arabic value (the tables in
1.2, 1.3, 2.1 and 4.1); the report lists them by line number. The Arabic quoted here is read from the
file bytes by a script (json.load of ar.json at base, and the suggestion column of the review table),
never retyped.

---------------------------------------------------------------------------------------------------

## 0. The group

- Group: S81-11e (ONE unit: S81-11e AR-COPY). Class: CLIENT, SAFE under LC-1 as ruled by R-S11E-0
  (see 12.5 for the surface check and the one open question it raises).
- Branch: feature/s81-s11e-ar-copy, cut from the then-main at GREEN (R-S11E-0). The worktree is
  re-pointed to the then-main with `git checkout --detach` by the orchestrator before the RED.
- Flags: NONE. A client unit: React Native reads no per-call env flag; no new `features.ts` constant.
  It merges to main now and reaches users only in the first post-approval OTA, which WAITS on it
  (owner ruling 2026-11-07 14:04, "Fix strings first"). The main invariant in place of flag-OFF
  identity = the IDENTITY INVARIANT: every other key of src/i18n/ar.json byte-identical (999 of 1,011
  values), src/i18n/en.json untouched, both key sets unchanged (1,011 each, parity 0),
  locales/ar.json untouched.
- Change list (the one unit): (1) SmartCompareApp/src/i18n/ar.json (12 value lines);
  (2) NEW SmartCompareApp/__tests__/s11e/arCopy.s11e.test.ts; (3) E-row
  SmartCompareApp/__tests__/fixtures/b3a_copy.json (1 line: the AR quote_3 value); (4) CLAUDE.md
  (one dated bullet inside the S81-11 client block). Nothing else in src/; no EN change; no package
  manager; no backend file.
- Files two units share: none (one unit). Apply order at GREEN: ar.json, then the fixture line (the
  RED already carries the fixture E-row, see 4.1), then CLAUDE.md.

---------------------------------------------------------------------------------------------------

## Unit S81-11e

### 1. Base state (MEASURED at 39ac80ba)

1.1 Tool versions (printed in this run from sc-s81-s11e/SmartCompareApp through the live junction):
jest 29.7.0 (`node node_modules/jest/bin/jest.js --version`), node v24.11.1, tsc 5.9.3
(`node node_modules/typescript/bin/tsc --version`), eslint v9.39.4. No pytest in this unit: no
backend file is touched, so the backend comm set, pyt.py and the corpus gate do not apply (R-S11E-3);
the bounded runner was not used.

1.2 Which catalog is live.
- SmartCompareApp/src/i18n/index.ts:12 `import en from './en.json';`, :13 `import ar from
  './ar.json';`, :32 `resources: { en: { translation: en }, ar: { translation: ar } }` (lines 31-35).
  src/i18n/ar.json is the live runtime catalog.
- SmartCompareApp/locales/ar.json (747 B, sha256 1a1ade19...) holds ONLY the iOS InfoPlist strings
  (one object "ios" with CFBundleDisplayName, NSCameraUsageDescription,
  NSPhotoLibraryUsageDescription, NSMicrophoneUsageDescription), wired by app.json:17-18
  (`"en": "./locales/en.json"`, `"ar": "./locales/ar.json"`). It holds none of the 12 keys, so it does
  NOT mirror them; no test compares it with src/i18n/ar.json (the only reader of its strings is
  __tests__/b3a/nativeStrings.b3a.test.ts through the fixture's `native` block, which carries only
  NSCameraUsageDescription and NSPhotoLibraryUsageDescription). VERDICT: locales/ar.json is OUT of
  scope and stays byte-identical.
- src/i18n/ar.json: 72,844 B, sha256 6b9471c6a03b5d322278afc26f09877158df598bf575cf0346f51735c7165f68,
  UTF-8 without BOM, CRLF (1,074 CR = 1,074 LF), final newline present, FLAT dotted keys (one
  `  "a.b.c": "value",` line per key, raw UTF-8, no \u escapes), 1,011 keys.
  src/i18n/en.json: sha256 89c6bc1d04fd94c44f27466e356aed1651ea7b79ba8dfb8dc052a266c9f5612f,
  1,011 keys; key parity 0 both ways.
- The GREEN edits ar.json by exact line replacement keeping CRLF and the raw-UTF-8 style (the
  prototype in 5.6 did exactly this: `git diff --numstat` = 12 / 12, CR = LF = 1,074 after).

1.3 The 12 current values (quoted from the file bytes; line = ar.json line at base; the EN line is
the en.json line):

| # | key | verdict | ar.json line | en.json line | EN (ASCII-escaped) | AR at base |
|---|---|---|---|---|---|---|
| 1 | home.errors.categoryNotLive | AWKWARD | 698 | 701 | We compare fragrances for now. More categories are coming soon. | نقارن العطور حاليا. فئات أخرى قريبا. |
| 2 | home.errors.insufficientDataReason.placeholder_identity | AWKWARD | 700 | 703 | We need clearer names to tell which products these are. Add the brand and the fragrance name. | نحتاج أسماء أوضح لنعرف المنتجين. أضف اسم الماركة واسم العطر. |
| 3 | results.honest.notListed | AWKWARD | 702 | 705 | Not listed by the stores we can read yet | غير مذكور لدى المتاجر التي نقرؤها حتى الآن |
| 4 | results.price.lastSeen | AWKWARD | 705 | 708 | {{store}}, last seen {{date}} | {{store}}، آخر ظهور {{date}} |
| 5 | results.price.lastSeenNoStore | AWKWARD | 706 | 709 | Last seen {{date}} | آخر ظهور {{date}} |
| 6 | home.errors.comparison | WRONG | 108 | 111 | Sharper match coming up \u2014 add the brand and the fragrance name. | نطابق بدقة أكبر قريبا — اكتب اسم الماركة واسم العطر. |
| 7 | home.errors.insufficientData | AWKWARD | 109 | 112 | Thin data on that pair \u2014 swap in two fragrances with the brand and name. | البيانات قليلة عن هذين المنتجين — جرب عطرين مع اسم الماركة واسم العطر. |
| 8 | onboarding.s1.quote_3 | AWKWARD | 525 | 528 | EDP or EDT of the same scent? See how size and price compare. | أو دو بارفان أم أو دو تواليت لنفس العطر؟ اعرف الفرق في الحجم والسعر. |
| 9 | onboarding.s17.tag_echoes_body | AWKWARD | 681 | 684 | When peers your age just compared the same pair. | عندما يقارن أقرانك في عمرك نفس الزوج. |
| 10 | home.compare.box_a_text | AWKWARD | 731 | 734 | Product A \u00b7 e.g. Dior Sauvage EDP | المنتج أ · مثال: ديور سوفاج أو دو بارفان |
| 11 | home.compare.box_b_text | AWKWARD | 732 | 735 | Product B \u00b7 e.g. Bleu de Chanel EDP | المنتج ب · مثال: بلو دو شانيل أو دو بارفان |
| 12 | home.headerCounter.resets | AWKWARD | 712 | 715 | resets {{time}} | تتجدد {{time}} |

1.4 The siblings the review names (read at base):

| sibling key | ar.json line | EN (ASCII-escaped) | AR at base |
|---|---|---|---|
| home.headerCounter.a11yResets | 713 | {{free}} of {{total}} free comparisons, plus {{bonus}} bonus. Free comparisons refresh at {{time}} | {{free}} من {{total}} مقارنات مجانية، بالإضافة إلى {{bonus}} إضافية، وتتجدد المقارنات المجانية الساعة {{time}} |
| paywall.limit.resets_at | 371 | Your free comparisons refresh at {{time}}. | تتجدد مقارناتك المجانية الساعة {{time}}. |
| paywall.limit.resets_daily | 368 | Your free comparisons refresh every day. | تتجدد مقارناتك المجانية كل يوم. |
| paywall.limit.resets_monthly | 369 | Your free comparisons refresh at the start of each month. | تتجدد مقارناتك المجانية في بداية كل شهر. |
| onboarding.s1.quote_1 | 523 | Sauvage or Bleu de Chanel? See their prices and details side by side. | سوفاج أم بلو دو شانيل؟ اعرض الأسعار والتفاصيل جنبا إلى جنب. |
| onboarding.s1.quote_2 | 524 | Two oud perfumes? See which one fits your budget. | عطران من العود؟ اعرف أيهما يناسب ميزانيتك. |

The resets form: home.headerCounter.a11yResets and paywall.limit.resets_at both put the word for
"the hour" before {{time}}; home.headerCounter.resets is the only one of the three without it.
The quote_3 / box form: quote_1 transliterates the brand ("Bleu de Chanel"); box_a, box_b and quote_3
transliterate the concentration (EDP / EDT) with a two-letter opening that is the Arabic word "or".

1.5 Source consumers of the 12 keys (unchanged by this unit; listed so the GREEN knows where each
string renders): src/services/errorCopy.ts:95 (insufficientData), :97 (categoryNotLive), :109
(comparison), :93 (the insufficientDataReason.<reason> template; placeholder_identity listed at :42);
src/screens/ResultsScreen.tsx:875 (categoryNotLive empty state); src/components/results/
ResultsAccordion.tsx:125, :150 and ResultsContent.tsx:373 (notListed); ResultsContent.tsx:173
(lastSeen / lastSeenNoStore, `date` from formatAsOfDate); src/screens/onboarding/Step01Welcome.tsx:98
(quote_3); src/screens/onboarding/Step17Notifications.tsx:120 (tag_echoes_body, with an EN
defaultValue 'When 5+ peers your age just compared the same pair.' at :121-122: see L4);
src/components/TwoInputShell.tsx:488-489 (box_a_text / box_b_text as placeholders);
src/screens/HomeScreen.tsx:1078 (resets, `time: pillResetClock`, :1009 formatResetClock).

1.6 Every suite, snapshot or fixture that pins one of the 12 OLD values.
- Grep of the 12 old AR values (distinctive substrings of each) over __tests__/, src/ (minus the
  catalog), .maestro and the repo's tests/ + docs: ONE hit:
  __tests__/fixtures/b3a_copy.json:79 (the fixture's AR value of onboarding.s1.quote_3). Its reader
  __tests__/b3a/honestCopy.b3a.test.tsx r26 (:186-193) asserts AR[k] === FX.ar[k] for every
  changed_keys entry, and changed_keys includes onboarding.s1.quote_3; r31 (:334) and r31b (:359) run
  the copy / brand / diacritics fences over FX.ar and the live AR for the same keys. MEASURED: with
  ar.json changed and the fixture NOT changed, r26 fails with ["ar:onboarding.s1.quote_3"]
  (1 failed, 10 passed). This is the unit's only E-row (4.1). The fixture is CRLF (99 CR = 99 LF),
  sha256 43a6378a09bb68e7301f99a4c26b1f3c6771bdd1d19228d559c85f983dc71fc2; its EN quote_3 at :52 is
  unchanged.
- No snapshot (.snap) holds any of the 12 values; no test hashes ar.json (the only catalog digest is
  __tests__/consent/aiConsentVersion.s69.test.ts PINNED.sha256 over aiConsent.title / aiConsent.body,
  which this unit does not touch).
- Key-referencing suites that read the values DYNAMICALLY (green before and after, no edit):
  __tests__/s11/copy.s11.test.tsx (CHANGE_EXACT pins the EN values at :82-83, :86; AR only
  "non-empty and not English" :148-151, R-S11-32 "no digit in tag_echoes_body" :167-172, parity 1,011
  :186-192, F2 copy policy :195-213); __tests__/s81_08/i18nKeys.s81_08.test.ts (H1 {{time}} present
  :55-75; H2 AR_DISHONEST :35-44 + banned_ar + scary_vocab_ar + DIACRITICS [\u064b-\u0652] :46 + digits
  :77-116; H3 key parity); __tests__/s81_08/resetRender.s81_08.test.tsx:370-379 and
  __tests__/s81_08/gateRows.s81_08.test.ts:399-411 (compare with inst.t at run time);
  __tests__/s11/{refusals,refusalsCamera,gateRows,sseFallback,honestUnknowns}.s11 (keys only);
  __tests__/errorCopy.{a11,engineUnavailable.s69,w314}.test.ts, HomeScreen.arabicAlerts.w311,
  HomeScreen.errorCopy.a11, ResultsScreen.networkMatrix.m18 (keys and fences; their Arabic literals
  are scary-word lists and a diacritics class, not values); __tests__/screens/onboarding/
  Step01Welcome.test.tsx:48 and src/components/__tests__/TwoInputShell.test.tsx:170-171, :913 (the
  key is the mocked text).

1.7 The parity and copy-policy tests by name:
- __tests__/i18n.test.ts:8 'English and Arabic have the same keys', :28 'interpolation variables
  match between EN and AR' (plus :20 no empty Arabic values).
- __tests__/copy-policy.test.ts:112 'ar.json contains no banned absolute-superlative or endorsement
  vocabulary', :186 'ar.json values contain no scary vocabulary from .copy-policy.json
  scary_vocab_ar' (policy at src/i18n/.copy-policy.json: banned_ar 5 patterns, scary_vocab_ar 4 words).
- __tests__/i18n/brand.myez.s69.test.ts:127 (the standalone verb "compare" only on the 10 verb keys),
  :150 (the brand word only on the 26 brand keys); __tests__/i18n/digitPolicy.w311.test.ts:49 (no
  Arabic-Indic digit in any ar.json value).

1.8 The b3a fence rows that read ar.json: __tests__/b3a/honestCopy.b3a.test.tsx:19 (AR =
require('../../src/i18n/ar.json')), :62 (the mocked react-i18next instance), r26 :186, r27 :195 (key
sets equal), r28 :207 (every AR value: the 25-store / offline claims), r31 :334 and r31b :359 (over
ALL_KEYS = changed + new + learning fixture keys; quote_3 is the only one of the 12 in that set).
The diacritics class of r31b is AR_DIACRITICS = U+064B..U+0652 plus U+0670 (:42), the brand word
split out first.

1.9 Backend readers of the touched files (no pytest run; CI runs them): ar.json is read by
tests/test_legal_docs_u8.py:193 / :1264 (aiConsent.body), tests/test_legal_docs_u8_d3c.py:90 / :242 /
:1018 (aiConsent.body, profile.title, profile.settings, editProfile.deleteAccount) and
tests/test_dimension_label_catalog_parity_w414.py (results.dimension.*): none of the 12 keys.
CLAUDE.md is read by tests/test_ci_gates.py:1392 (the phrase "never `--branch production`"),
tests/test_s81_s04_spend_breaker.py:1657 (the S81-04 row, cut at the next "\n**SESSION"),
tests/test_s81_s23_bypass_retire.py:316 (five forbidden phrases :290-296 + the S81-G1 block) and
tests/test_paid_route_metering.py (docstring mention only). The new CLAUDE.md bullet (section 8)
carries none of those phrases, starts with " - " (not "**SESSION") and sits inside the S81-11 block,
so none of these readers can move; no jest suite reads CLAUDE.md (every jest hit is a comment).

1.10 Base pass state (jest by path, one jest at a time on the box: no other jest process was
running at each launch, checked with Win32_Process):
- The 11 key suites (b3a/honestCopy, b3a/nativeStrings, copy-policy, i18n, s11/copy,
  s81_08/{i18nKeys,resetRender,gateRows}, Step01Welcome, TwoInputShell, i18n/brand.myez.s69):
  11 suites passed, 144 tests passed, 5.09 s.
- The full comm set of section 7 (113 files): Test Suites 1 failed, 112 passed; Tests 4 failed,
  1,392 passed, 1,396 total; 11.7 s. The 4 failures are the known config/nativeBundle.w37 drift
  nodes (d5 react-native-gesture-handler; k2, k4, k5 the SDK-54 patch level), the same four the
  LC-7 baseline names; they are box drift (installed node_modules vs lock), not this unit's.

### 2. Contract

2.1 Per key, the new AR value = the review table's suggested value AS WRITTEN (read from the table's
suggestion column by script; placeholders listed):

| # | key | new AR value (= the review suggestion as written) | placeholders (= EN) |
|---|---|---|---|
| 1 | home.errors.categoryNotLive | نقارن العطور حاليا، وستتوفر فئات أخرى قريبا. | (none) |
| 2 | home.errors.insufficientDataReason.placeholder_identity | نحتاج أسماء أوضح لنحدد المنتجين. أضف اسم الماركة واسم العطر. | (none) |
| 3 | results.honest.notListed | غير مذكور بعد لدى المتاجر التي نتابعها | (none) |
| 4 | results.price.lastSeen | {{store}}، آخر رصد في {{date}} | {{date}} {{store}} |
| 5 | results.price.lastSeenNoStore | آخر رصد في {{date}} | {{date}} |
| 6 | home.errors.comparison | لمطابقة أدق، اكتب اسم الماركة واسم العطر. | (none) |
| 7 | home.errors.insufficientData | البيانات قليلة عن هذين المنتجين — جرب عطرين آخرين واكتب اسم الماركة واسم العطر. | (none) |
| 8 | onboarding.s1.quote_3 | نسخة EDP أم EDT من العطر نفسه؟ اعرف الفرق في الحجم والسعر. | (none) |
| 9 | onboarding.s17.tag_echoes_body | عندما يقارن متسوقون في عمرك نفس المنتجين. | (none) |
| 10 | home.compare.box_a_text | المنتج أ · مثال: ديور سوفاج EDP | (none) |
| 11 | home.compare.box_b_text | المنتج ب · مثال: بلو دو شانيل EDP | (none) |
| 12 | home.headerCounter.resets | تتجدد الساعة {{time}} | {{time}} |

2.2 Rules (binding on GREEN):
- KEYS unchanged (no key added, removed or renamed in either catalog); EN unchanged (en.json
  byte-identical); placeholders verbatim: results.price.lastSeen keeps {{store}} and {{date}},
  lastSeenNoStore keeps {{date}}, home.headerCounter.resets keeps {{time}}; the other 9 carry none
  (equal to their EN sets: none of the 12 uses {{count}}, so no i18next plural family is involved).
- The GREEN re-reads each value as a native Gulf speaker and MAY IMPROVE a suggestion; it NEVER
  reverts a row to its old value (the old value is the defect). An improvement is a RULED pin-fix of
  the unit's own RED row: the EXPECTED table entry changes in the same GREEN commit, recorded in the
  GREEN report with the test file's new sha256; the constraint rows R13-R15 (5.2) must stay green
  under any improvement, so an improvement cannot bring back the "or"-collision, the
  "last online" phrase or the bare clock.
- Diacritics: no harakat, shadda or tanween (U+064B..U+0652, U+0670) in any of the 12 values (the
  brand word is in none of them); no Arabic-Indic digit (U+0660..U+0669, U+06F0..U+06F9, U+066A); no
  bidi control character (U+200E, U+200F, U+202A..U+202E, U+2066..U+2069).
- Copy policy: none of banned_ar, none of scary_vocab_ar; no standalone verb "compare" (the
  brand.myez fence); no brand word; no digit outside {{...}} (R-S11-32 for tag_echoes_body).
  MEASURED: the 12 suggestions pass every one of these checks (script sat.py, 5.6).
- One form for the concentration label: quote_3, box_a_text and box_b_text all use the Latin
  EDP / EDT labels (the review's preferred form). If the GREEN prefers an Arabic form instead it must
  use it in all three and must not open with the two-letter "or" word (R13 pins that).
- Latin inside an RTL line: the new quote_3 opens with an Arabic word, so the base direction stays
  RTL; box_a / box_b end with "EDP" after Arabic text. A device bidi look is the owner's (L2).

2.3 Failure table (what a wrong value does; none crashes): a missing key falls back to EN
(fallbackLng 'en', index.ts) and is caught by i18n.test :8 and the s11e P3 row; a dropped
placeholder renders a literal hole and is caught by i18n.test :28 and s11e P1; a banned / scary word
is caught by copy-policy :112 / :186 and s11e P5; a diacritic by s11e P4 (and r31b for quote_3).

2.4 Contract freeze (PLAN_S80 section 0 and runs/research/contract_freeze.json re-read): no API path,
code or envelope changes; the error-code to key map in src/services/errorCopy.ts is untouched; only
the Arabic text behind four of its keys changes. Never a bare 503: not applicable (no backend).

2.5 Seams: none new. The catalog is data; the test reads it with fs + JSON.parse (no i18next
instance, no React render), so it is hermetic and needs no mock.

### 3. Change list

| # | File | Change | Bytes |
|---|---|---|---|
| C1 | SmartCompareApp/src/i18n/ar.json | the 12 value lines of 1.3 replaced by the 2.1 values, by exact line, CRLF and raw UTF-8 kept | 12 lines; every other byte identical |
| C2 | SmartCompareApp/__tests__/s11e/arCopy.s11e.test.ts | NEW (the RED, section 5) | ASCII except the EXPECTED table's 12 AR strings |
| C3 | SmartCompareApp/__tests__/fixtures/b3a_copy.json | E-row E1: line 79 (the AR quote_3) = the new quote_3 value, CRLF kept | 1 line |
| C4 | CLAUDE.md | one dated bullet inserted after line 582 (inside the S81-11 client block, before the blank line 583), CRLF | 1 line |

Not touched: src/i18n/en.json, SmartCompareApp/locales/*.json, every src/ .ts/.tsx file
(Step17Notifications.tsx's stale EN defaultValue included: L4), app/, scripts/, docs/, .github/,
.githooks/, package.json / the lock, the node_modules junction.

### 4. Existing pins

4.1 Deliberate changes (the unit's own E-rows, written IN THE RED with the old and new lines):

| E | file:line | old line (base) | new line (RED) |
|---|---|---|---|
| E1 | SmartCompareApp/__tests__/fixtures/b3a_copy.json:79 (CRLF kept) | `"onboarding.s1.quote_3": "أو دو بارفان أم أو دو تواليت لنفس العطر؟ اعرف الفرق في الحجم والسعر.",` | `"onboarding.s1.quote_3": "نسخة EDP أم EDT من العطر نفسه؟ اعرف الفرق في الحجم والسعر.",` |

Reason: the fixture is the B3-A copy contract for quote_3 (a changed_keys entry); r26 pins the
live AR to it, so the fixture must carry the new value; r31 and r31b then fence the new value (both
measured green with it, 5.6). This is the unit's own E-row, never a frozen row of another unit
(R-S11E-2). The RED writes it together with the new test, which makes r26 RED at base too (live AR
old vs fixture new) until GREEN changes ar.json; the RED report lists r26 as an expected base
failure ON AN ASSERTION (the measured message ["ar:onboarding.s1.quote_3"]).

4.2 Must stay green (unchanged files): every file of the comm set (section 7) other than the new
test and r26 at the RED; in particular i18n.test :8 / :28, copy-policy :112 / :186, s11/copy (all),
s81_08/i18nKeys H1-H3, resetRender, gateRows, b3a/honestCopy r27-r32, b3a/nativeStrings,
brand.myez.s69 :127 / :150, digitPolicy.w311 :49, consent/aiConsentVersion.s69 (the consent digest:
the identity invariant keeps it), and the fourteen backend-scanning fences.

### 5. RED tests

5.1 File: SmartCompareApp/__tests__/s11e/arCopy.s11e.test.ts (a client unit: the house
tests/test_s81_<unit>_*.py form does not apply; the brief names the jest path). Hermetic: reads
src/i18n/ar.json, src/i18n/en.json and src/i18n/.copy-policy.json with fs.readFileSync +
JSON.parse (CRLF-safe: JSON.parse ignores the CR); no render, no mock, no network. Bytes: ASCII
everywhere EXCEPT the 12 AR strings of the EXPECTED table (raw UTF-8; the RED byte-checks and lists
those lines); every other Arabic in the file (the constraint rows) is written as \u escapes; failure
messages print keys, never Arabic values (the b3a convention). LF line endings (the repo's .ts tests
are LF; the RED checks `git ls-files --eol` of a sibling and matches it).

5.2 Rows (RED rows fail at base on an assertion only; PIN rows are green at base):

| Row | Kind | Assertion | At base |
|---|---|---|---|
| R1-R12 | RED | it.each over the 12 keys: `expect({ k, v: AR[k] }).toEqual({ k, v: EXPECTED[k] })` | 12 fail (old value), measured |
| R13 | RED | the one concentration form: none of quote_3, box_a_text, box_b_text contains the transliteration that opens with the "or" word (the escapes \u0623\u0648 \u062f\u0648, i.e. alef-hamza waw, space, dal waw), and all three contain the same concentration token set (each of box_a / box_b contains EDP; quote_3 contains EDP and EDT) | fail (all three hold the transliteration) |
| R14 | RED | no AR value of results.price.lastSeen / lastSeenNoStore contains the "last online" phrase (\u0622\u062e\u0631 \u0638\u0647\u0648\u0631) | fail |
| R15 | RED | the clock form: home.headerCounter.resets contains "\u0627\u0644\u0633\u0627\u0639\u0629 {{time}}" (the hour word + space + {{time}}), as both siblings a11yResets and paywall.limit.resets_at do (the row asserts all three) | fail on resets only |
| P1 | PIN | it.each: placeholder set of AR[k] == placeholder set of EN[k] | 12 green |
| P2 | PIN | it.each: placeholder set of EXPECTED[k] == EN[k] (the table self-check) | 12 green |
| P3 | PIN | the 12 keys exist in both catalogs; EN and AR key sets equal; 1,011 each | green |
| P4 | PIN | for the 12 AR values: no U+064B..U+0652 / U+0670 (brand word split out), no Arabic-Indic digit, no bidi control, no ASCII digit outside {{...}} | green (the old values pass too: measured, the review's only diacritic is in a key outside the 12) |
| P5 | PIN | for the 12 AR values: no banned_ar pattern, no scary_vocab_ar word (read from .copy-policy.json, non-vacuous: banned_ar.length >= 5 and scary_vocab_ar.length >= 4 asserted first), no standalone verb "compare" (the brand.myez wordRe form with \u escapes), no brand word | green |
| P6 | PIN | it.each: EN[k] equals an EN table in the test (ASCII with \u00b7 and \u2014 escapes for the middle dot and the em dash) | 12 green |

Counts: 15 RED rows (R1-R15), 39 PIN rows (P1 12 + P2 12 + P3 1 + P4 1 + P5 1 + P6 12). Plus the
E-row r26 red at base by construction (4.1).

5.3 The EXPECTED table = section 2.1 verbatim. The EN table (P6) = the EN column of 1.3 (escaped).

5.4 Hygiene for the RED (and every later round): the new file's bytes > 127 occur only on the 12
EXPECTED lines (listed with line numbers in the RED report); no constant name carries a gitleaks
generic-api-key keyword (access / auth / api / credential / creds / key / password / secret / token:
EXPECTED, EN_TABLE and TWELVE are fine; a name such as KEYS_12 or KEY_DIGEST is not); eslint by
path on the new file; tsc --noEmit by path once; jest by path.

5.5 RED-at-base proof (measured in this run with a prototype of R1-R12 + P1 + P2): 36 tests, 12 failed
(exactly the 12 value rows, each `expect(received).toEqual(expected) // deep equality`), 24 passed.

5.6 Satisfiability prototype (IN PLACE, measured, restored):
- Byte copies of src/i18n/ar.json (sha 6b9471c6...) and __tests__/fixtures/b3a_copy.json
  (sha 43a6378a...) taken to the scratchpad; the 12 values applied to ar.json and the quote_3 value
  to the fixture by exact string replacement (CRLF kept: CR = LF = 1,074 and 99); a prototype test
  placed at __tests__/s11e/proto.s11e.test.ts.
- With the change: 29 suites (the prototype, the 11 key suites, s11/{honestUnknowns,refusals,
  refusalsCamera,gateRows,sseFallback}, errorCopy x3, HomeScreen.arabicAlerts.w311,
  HomeScreen.errorCopy.a11, ResultsScreen.networkMatrix.m18, consent/aiConsentVersion.s69,
  i18n/{digitPolicy.w311,no-missing-referenced-keys,no-deleted-keys,plurals,pluralFamilies.fence.w311})
  = 29 passed, 388 tests passed, 0 failed.
- Without the fixture E-row: honestCopy r26 fails (["ar:onboarding.s1.quote_3"]) -> the E-row is
  required.
- An in-memory check (script sat.py) of the 12 suggestions against 2.2: no same-as-old value, the
  placeholder sets equal EN, no diacritic, no banned / scary word, no standalone verb, no brand
  word, no Arabic-Indic or stray ASCII digit, no bidi control: BAD = [].
- Restored: both files copied back from the byte copies, sha256 re-checked equal to the base
  (6b9471c6..., 43a6378a...), the prototype file and the __tests__/s11e directory removed,
  `git status --short` empty, HEAD 39ac80ba. No scratch worktree and no junction was used.

### 6. Mutation table (applied to byte copies with a sha-checked restore; M1-M15 MEASURED in this
run against the prototype, M16-M19 specified for the RED to measure against the real file)

| M | Mutant | Killed by | Measured |
|---|---|---|---|
| M1 | home.errors.categoryNotLive = old value | R (value) | killed |
| M2 | home.errors.insufficientDataReason.placeholder_identity = old | R | killed |
| M3 | results.honest.notListed = old | R | killed |
| M4 | results.price.lastSeen = old | R (+ R14 in the real file) | killed |
| M5 | results.price.lastSeenNoStore = old | R (+ R14) | killed |
| M6 | home.errors.comparison = old | R | killed |
| M7 | home.errors.insufficientData = old | R | killed |
| M8 | onboarding.s1.quote_3 = old | R (+ R13, + b3a r26 via the fixture) | killed |
| M9 | onboarding.s17.tag_echoes_body = old | R | killed |
| M10 | home.compare.box_a_text = old | R (+ R13) | killed |
| M11 | home.compare.box_b_text = old | R (+ R13) | killed |
| M12 | home.headerCounter.resets = old | R (+ R15) | killed |
| M13 | results.price.lastSeen new value with {{store}} dropped | R + P1 | killed (value + placeholders) |
| M14 | results.price.lastSeenNoStore new value with {{date}} dropped | R + P1 | killed (value + placeholders) |
| M15 | home.headerCounter.resets new value with {{time}} dropped | R + P1 (+ R15, + s81_08 H1) | killed (value + placeholders) |
| M16 | a shadda added inside home.errors.comparison | R + P4 | RED measures |
| M17 | EN home.compare.box_a_text changed | P6 (+ s11/copy CHANGE_EXACT) | RED measures |
| M18 | a banned_ar phrase appended to results.honest.notListed | R + P5 (+ copy-policy :112) | RED measures |
| M19 | home.compare.box_b_text deleted from ar.json | R + P3 (+ i18n.test :8) | RED measures |

Restore rule: never `git checkout --` a file; restore from the byte copy and sha-check (the S81
mutation rule). The identity invariant itself (an untouched key changed) is checked at the gate by
a script (12.1), not by a permanent test row (open question Q2).

### 7. Comm set (union rule; jest by path from sc-s81-s11e/SmartCompareApp)

Union of: (a) every suite that reads ar.json, the i18n folder or index, the copy policy or the b3a
fixture (grep over __tests__ and src for ar.json / src/i18n / /i18n' / i18n/index / .copy-policy /
b3a_copy); (b) every suite naming one of the 12 keys; (c) all of __tests__/s11/, __tests__/s81_08/,
__tests__/b3a/; (d) the fourteen backend-scanning client fences (brand/inAppMark.u4c,
clientTruth/{medicalNote,privacyManifest,shareTruth}.s74, clipboardFallbackService(+.edges),
config/nativeBundle.w37, DimensionBars.perCategory, honestCounts.s69, landing.domain.s76,
navigation/linking.w315, onboarding/step05Trust.s69, playInstallReferrerService(+.edges),
ResultsScreen.timeout): this unit moves no literal they read (no app/, scripts/, docs/, .github/
change), they run as hygiene. Suites that reach the catalog only transitively (a screen importing
src/i18n) are covered by the FULL jest once in the last round (LC-7).
113 files at base (+ the new s11e test = 114):

- SmartCompareApp/__tests__/App.bootGuard.b5.test.ts
- SmartCompareApp/__tests__/AuthScreens.socialDiagnostic.pa8.test.tsx
- SmartCompareApp/__tests__/AuthScreens.socialTimeout.a8.test.tsx
- SmartCompareApp/__tests__/CameraHelpOverlay.test.tsx
- SmartCompareApp/__tests__/ConsentRow.copy.w3-16.test.tsx
- SmartCompareApp/__tests__/DimensionBars.perCategory.test.tsx
- SmartCompareApp/__tests__/EditProfileScreen.appleRelay.test.tsx
- SmartCompareApp/__tests__/EditProfileScreen.bundleE.s3.test.tsx
- SmartCompareApp/__tests__/EditProfileScreen.deleteCopy.w314.test.tsx
- SmartCompareApp/__tests__/HistoryScreen.timeAgo.w311.test.tsx
- SmartCompareApp/__tests__/HomeScreen.arabicAlerts.w311.test.tsx
- SmartCompareApp/__tests__/HomeScreen.bundleE.s3.test.tsx
- SmartCompareApp/__tests__/HomeScreen.catfix.d1.test.tsx
- SmartCompareApp/__tests__/HomeScreen.currentDesign.contract.test.ts
- SmartCompareApp/__tests__/HomeScreen.engineUnavailable.s69.test.tsx
- SmartCompareApp/__tests__/HomeScreen.errorCopy.a11.test.tsx
- SmartCompareApp/__tests__/HomeScreen.rateLimitedSeconds.w314.test.tsx
- SmartCompareApp/__tests__/HomeScreen.trending.s69.test.tsx
- SmartCompareApp/__tests__/InviteeQuizScreen.redesign.test.tsx
- SmartCompareApp/__tests__/LoadingScreenVariants.a2Pacing.test.tsx
- SmartCompareApp/__tests__/LoadingScreenVariants.wave2.test.tsx
- SmartCompareApp/__tests__/ProfileEditorialSections.timeAgo.w311.test.tsx
- SmartCompareApp/__tests__/ProfileScreen.logoutCopy.b6.test.tsx
- SmartCompareApp/__tests__/ProfileScreen.toggles.w314.test.tsx
- SmartCompareApp/__tests__/ReferralLandingScreen.test.tsx
- SmartCompareApp/__tests__/ResultsContent.partialNote.test.tsx
- SmartCompareApp/__tests__/ResultsScreen.historyDetailFetch.test.ts
- SmartCompareApp/__tests__/ResultsScreen.networkMatrix.m18.test.ts
- SmartCompareApp/__tests__/ResultsScreen.redesign.test.tsx
- SmartCompareApp/__tests__/ResultsScreen.timeout.test.tsx
- SmartCompareApp/__tests__/ResultsScreen.usageFetch.a15.test.tsx
- SmartCompareApp/__tests__/ScanCameraScreen.captureFailure.b9.test.tsx
- SmartCompareApp/__tests__/ShareBottomSheet.redesign.test.tsx
- SmartCompareApp/__tests__/api.outputLang.w414.test.ts
- SmartCompareApp/__tests__/auth/authErrorCopy.s69.test.ts
- SmartCompareApp/__tests__/b3a/appleAuthCode.b3a.test.ts
- SmartCompareApp/__tests__/b3a/authNoScreenCapture.b3a.test.tsx
- SmartCompareApp/__tests__/b3a/cameraDenied.b3a.test.tsx
- SmartCompareApp/__tests__/b3a/googleButton.b3a.test.tsx
- SmartCompareApp/__tests__/b3a/honestCopy.b3a.test.tsx
- SmartCompareApp/__tests__/b3a/nativeStrings.b3a.test.ts
- SmartCompareApp/__tests__/b3a/onboardingResume.b3a.test.tsx
- SmartCompareApp/__tests__/brand/inAppMark.u4c.test.ts
- SmartCompareApp/__tests__/clientTruth/copyTruth.s74.test.ts
- SmartCompareApp/__tests__/clientTruth/medicalNote.s74.test.tsx
- SmartCompareApp/__tests__/clientTruth/privacyManifest.s74.test.ts
- SmartCompareApp/__tests__/clientTruth/shareTruth.s74.test.tsx
- SmartCompareApp/__tests__/clipboardFallbackService.edges.test.ts
- SmartCompareApp/__tests__/clipboardFallbackService.test.ts
- SmartCompareApp/__tests__/components/DimensionBars.arabicLabels.w414.test.tsx
- SmartCompareApp/__tests__/components/ResultsAccordion.digitPolicy.w311.test.tsx
- SmartCompareApp/__tests__/components/ResultsAccordion.v2.test.tsx
- SmartCompareApp/__tests__/components/RunnerUpWinsCard.arabicLabels.w414.test.tsx
- SmartCompareApp/__tests__/config/nativeBundle.w37.test.ts
- SmartCompareApp/__tests__/consent/aiConsentSheetScroll.s75.test.tsx
- SmartCompareApp/__tests__/consent/aiConsentV2.s75.test.ts
- SmartCompareApp/__tests__/consent/aiConsentVersion.s69.test.ts
- SmartCompareApp/__tests__/consent/aiProcessingConsent.s69.test.tsx
- SmartCompareApp/__tests__/copy-policy.test.ts
- SmartCompareApp/__tests__/demographics.i18n.test.ts
- SmartCompareApp/__tests__/errorCopy.a11.test.ts
- SmartCompareApp/__tests__/errorCopy.engineUnavailable.s69.test.ts
- SmartCompareApp/__tests__/errorCopy.w314.test.ts
- SmartCompareApp/__tests__/honestCounts.s69.test.tsx
- SmartCompareApp/__tests__/i18n.bundle_c.test.ts
- SmartCompareApp/__tests__/i18n.test.ts
- SmartCompareApp/__tests__/i18n/brand.myez.s69.test.ts
- SmartCompareApp/__tests__/i18n/digitPolicy.w311.test.ts
- SmartCompareApp/__tests__/i18n/dimensionLabels.w414.test.ts
- SmartCompareApp/__tests__/i18n/fashionLabels.test.ts
- SmartCompareApp/__tests__/i18n/no-deleted-keys.test.ts
- SmartCompareApp/__tests__/i18n/no-missing-referenced-keys.test.ts
- SmartCompareApp/__tests__/i18n/pluralFamilies.fence.w311.test.ts
- SmartCompareApp/__tests__/i18n/plurals.test.ts
- SmartCompareApp/__tests__/i18n/priceDigits.crossScreen.w414.test.ts
- SmartCompareApp/__tests__/i18n/referralExpiryPlurals.w414.test.ts
- SmartCompareApp/__tests__/landing.domain.s76.test.ts
- SmartCompareApp/__tests__/navigation/linking.w315.test.ts
- SmartCompareApp/__tests__/onboarding/step05Trust.s69.test.tsx
- SmartCompareApp/__tests__/playInstallReferrerService.edges.test.ts
- SmartCompareApp/__tests__/playInstallReferrerService.test.ts
- SmartCompareApp/__tests__/rtlBootstrap.s69.test.tsx
- SmartCompareApp/__tests__/s11/categoryRow.s11.test.tsx
- SmartCompareApp/__tests__/s11/copy.s11.test.tsx
- SmartCompareApp/__tests__/s11/fabricated.s11.test.tsx
- SmartCompareApp/__tests__/s11/gateRows.s11.test.tsx
- SmartCompareApp/__tests__/s11/honestUnknowns.s11.test.tsx
- SmartCompareApp/__tests__/s11/launchSurfaces.s11.test.ts
- SmartCompareApp/__tests__/s11/refusals.s11.test.tsx
- SmartCompareApp/__tests__/s11/refusalsCamera.s11.test.tsx
- SmartCompareApp/__tests__/s11/sseFallback.s11.test.ts
- SmartCompareApp/__tests__/s81_08/cameraHeaders.s81_08.test.ts
- SmartCompareApp/__tests__/s81_08/consentRecord.s81_08.test.ts
- SmartCompareApp/__tests__/s81_08/deviceId.s81_08.test.ts
- SmartCompareApp/__tests__/s81_08/gateRows.s81_08.test.ts
- SmartCompareApp/__tests__/s81_08/i18nKeys.s81_08.test.ts
- SmartCompareApp/__tests__/s81_08/requestHeaders.s81_08.test.ts
- SmartCompareApp/__tests__/s81_08/resetRender.s81_08.test.tsx
- SmartCompareApp/__tests__/s81_08/resetTime.s81_08.test.ts
- SmartCompareApp/__tests__/s81_08/socialLegacy.s81_08.test.ts
- SmartCompareApp/__tests__/s81_08/sseHeaders.s81_08.test.ts
- SmartCompareApp/__tests__/screens/LimitReachedSheet.s69.test.tsx
- SmartCompareApp/__tests__/screens/ResultsScreen.degraded.s69.test.tsx
- SmartCompareApp/__tests__/screens/ResultsScreen.no_estimated_copy.test.tsx
- SmartCompareApp/__tests__/screens/onboarding/Step01Welcome.test.tsx
- SmartCompareApp/__tests__/screens/paywall.noSubscriptionUi.s69.test.ts
- SmartCompareApp/__tests__/services/pushPrompt.s69.test.tsx
- SmartCompareApp/__tests__/utils/dimensionLabel.w414.test.ts
- SmartCompareApp/src/components/__tests__/PaywallBanner.test.tsx
- SmartCompareApp/src/components/__tests__/TwoInputShell.test.tsx
- SmartCompareApp/src/utils/__tests__/currencyDisplay.test.ts
- SmartCompareApp/src/utils/__tests__/formatDate.test.ts
- SmartCompareApp/src/utils/__tests__/formatNumber.test.ts

Gates: RED = the new file + r26 + the 113 (expected: the 15 RED rows + r26 red on assertions, the
four nativeBundle.w37 drift nodes red as at base, everything else green). GREEN = the same set, all
green except the four drift nodes; eslint by path on __tests__/s11e/arCopy.s11e.test.ts
(`node node_modules/eslint/bin/eslint.js __tests__/s11e/arCopy.s11e.test.ts`); tsc --noEmit by path
once (`node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json` scoped as the house rounds do,
or the file by path with the project's compiler options); the pre-commit hook on the commit. LAST
round (the rebase): the FULL jest ONCE (LC-7) against the baseline 3,976 passed + the four
config/nativeBundle.w37 drift nodes + 13 pending + 13 todo, expected 3,976 + the new rows passed.
The backend comm set, pyt.py, the base record and the corpus gate do not apply (no backend file).

### 8. CLAUDE.md (the one dated bullet; R-S11E-4) and owner steps

Inserted after CLAUDE.md line 582 (the S81-11 block's "Stated limits" bullet), before the blank
line 583, CRLF, ASCII, names only:

 - **AR copy re-read (S81-11e AR-COPY, 2026-11-07):** the delegated native read of the first-OTA Arabic strings (1 WRONG + 11 AWKWARD, `specs/S81_11E_AR_COPY_REVIEW.md` in the session-81 state folder) re-wrote the AR values of `home.errors.categoryNotLive`, `home.errors.insufficientDataReason.placeholder_identity`, `results.honest.notListed`, `results.price.lastSeen`, `results.price.lastSeenNoStore`, `home.errors.comparison`, `home.errors.insufficientData`, `onboarding.s1.quote_3`, `onboarding.s17.tag_echoes_body`, `home.compare.box_a_text`, `home.compare.box_b_text`, `home.headerCounter.resets` in `SmartCompareApp/src/i18n/ar.json` (EN, keys and placeholders unchanged; pinned by `__tests__/s11e/arCopy.s11e.test.ts`); the first post-approval OTA waits on this unit.

Owner steps: none to merge (merge on 7 / 7 green). After the merge the relay re-runs the OTA
preflight at the new main in its own worktree and an Opus agent publishes the first post-approval
OTA (eas update --channel production) per R-S11E-5; the owner's final look is the diff. Nothing for
S88 on the EAS side.

### 9. Stated limits

- L1 The native read is the delegated agent's (an Opus reader of the review table), not a human
  Gulf speaker's; the GREEN's re-read and the adversary's second native-read pass are agents too.
  The owner's final look is the PR diff.
- L2 Bidi on device is not tested: quote_3 / box_a / box_b now hold Latin EDP / EDT inside RTL
  lines, and lastSeen keeps the Latin store name first; jest checks bytes, not Hermes / iOS layout.
- L3 The OTA follows the merge and is the relay's step; this unit ships nothing by itself.
- L4 No EN change and nothing else in src/: the stale EN defaultValue of onboarding.s17.
  tag_echoes_body in Step17Notifications.tsx:121-122 ('When 5+ peers ...', a digit the catalog no
  longer carries) stays; it renders only if the key were missing.
- L5 The other NATURAL rows and the 'brand' wording split (two Arabic words for brand in the
  catalog, review note 1) are unchanged.

### 10. Out of scope

locales/*.json (InfoPlist), en.json, any key add / remove, the 16 NATURAL rows, any src/ code,
the OTA itself, backend, the Step17 defaultValue (L4), a catalog-wide diacritics sweep.

### 11. Open questions for the orchestrator (LC-8)

- Q1 SAFE vs FOCUS: LC-1 lists "the App-Review-visible client surface" as FOCUS; these 12 strings
  are user-visible (onboarding, the compare boxes, the error copy, the quota-counter pill
  home.headerCounter.resets). R-S11E-0 already rules the unit SAFE (copy only, after approval, no
  consent / legal / auth copy). Confirm the ruling stands (12.5).
- Q2 The identity invariant: keep it as a gate-time script (ar.json at base vs GREEN: exactly the 12
  values differ, key order equal; en.json and locales byte-equal) rather than a permanent digest row,
  so later copy units do not inherit a frozen digest? (Recommended: the gate script.)
- Q3 No DEFECT_LEDGER id exists for S81-11e (grep found none); file one (e.g. the native-read
  WRONG row home.errors.comparison) or record it as the owner ruling of 2026-11-07 14:04 only?
- Q4 Should the four backend tests that read CLAUDE.md (1.9) run once through pyt.py at GREEN even
  though the brief says no pytest? This spec says not needed (measured: the bullet cannot move them;
  CI runs them).

---------------------------------------------------------------------------------------------------

## 12. The group

12.1 Combined comm set and CI order: section 7 (114 files with the new test); CI order = the
frontend-tests job runs the full jest; the backend job runs the pytest suite unchanged (no backend
byte moves; the CLAUDE.md readers of 1.9 are inside it). Gate-time identity script: json.load of
ar.json at base and at GREEN -> the differing keys == the 12 exactly, list(keys) equal; sha256 of
en.json, locales/ar.json, locales/en.json equal to base (89c6bc1d..., 1a1ade19..., 4673ffc8...).

12.2 Combined footprint: 4 files (ar.json 12 lines, the new test ~150 lines, the fixture 1 line,
CLAUDE.md 1 line).

12.3 Shared-file plan: one unit, no shared file.

12.4 PR plan: ONE PR, title "S81-11e AR-COPY: the 12 Arabic strings of the first OTA re-read";
body <= 25,600 B measured with python, pure ASCII except the attribution line; sections: summary
(the owner ruling, the review table by name and sha), the change list, the [NATIVE READ] list =
the 12 keys by name only (home.errors.comparison, home.errors.categoryNotLive,
home.errors.insufficientData, home.errors.insufficientDataReason.placeholder_identity,
results.honest.notListed, results.price.lastSeen, results.price.lastSeenNoStore,
onboarding.s1.quote_3, onboarding.s17.tag_echoes_body, home.compare.box_a_text,
home.compare.box_b_text, home.headerCounter.resets; the values live in the diff), the E-rows table
(E1 the fixture line 79), the counts (15 RED + 39 PIN rows, the mutation count by reference to a
specs/ file), the comm result, the full-jest figure, the stated limits L1-L5, no owner step to
merge. Merge on 7 / 7 green; the bookkeeping per R-S11E-5 (a client unit: no backend base-record
change).

12.5 SAFE check (surfaces the group touches):
- auth / tokens / sessions: no. quota / billing / refunds: no logic; one DISPLAY string of the quota
  counter pill (home.headerCounter.resets) changes wording only, {{time}} kept. legal or privacy
  text: no (aiConsent.*, the legal keys and locales InfoPlist untouched; the consent digest stays
  green). consent path: no. security middleware: no. migrations: no. Redis / Lua: no. secrets or
  key handling: no.
- App-Review-visible client surface: YES in the literal sense (user-visible Arabic copy on onboarding,
  Home, Results and the counter pill); it is copy only, ships after approval through the OTA, and
  R-S11E-0 rules it SAFE. Named in focus_surfaces_found so the orchestrator can confirm (Q1).
