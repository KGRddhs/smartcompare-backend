# CL3 adversarial spec review (lens 1: correctness / RED design / comm set)

- Spec: .qa-s80/CL3_UNIT_SPEC.md, sha256 194ee86fedca67777fe43cb985fc4979974f33ce6aed1cf8b95608d81c321a02
  (re-hashed at the start of this review: MATCH; 993 lines).
- Base: a74caba7e3ff66b12e94178c912197c845ccbd14 (`git rev-parse HEAD` in the worktree; `git status --short`
  empty before and after this review apart from this file under the gitignored .qa-s80/).
- Brief read first: specs/CL3_BRIEF.md (R-CL3-1..14, Q1-Q7); PLAN_S81 :175; DEFECT_LEDGER :64-65;
  S81_SF1_BRIEF R-SF1-2 / R-SF1-8; RULINGS_S81_24 R-S24-25; newest ledger lines (2026-11-11 17:5x): no
  ENABLE_FEEDBACK_V2 ON line (OFF); ENABLE_PROXY_AWARE_RATELIMIT never set (session-81 ledger, names read).
- Probes: scratchpad CL3REV/ (probe_feedback.py: FastAPI TestClient over the real feedback router,
  save_feedback stubbed, run with cwd = the worktree, nothing written there).
- Jest: NOT MEASURED (no junction), as the brief states; every jest statement below is BY READING.

## Verdict

APPROVE_WITH_CHANGES. The wire answers (Q3), the reader answers (Q2, with two readers added below), the
id carriers (Q1) and the riders are correct at the base sha. Three items must be corrected before RED:
one RED row a correct GREEN cannot pass (V9), a comm-set gap (three suites that import the edited
catalogs), and a details-step design gap (the keyboard covers the only text field and eats the Send tap).

## Measurements (re-measured at a74caba7)

Bounded runner:
- tests/test_feedback_allowlist_superset.py: `11 passed` / `[hermeticity] sentinel checked 11 test(s)` /
  `[netguard] blocked 0 attempt(s) from 0 node(s)` /
  `[pyt] tag=cl3-rev-allow start=2026-11-11 18:05:15 end=2026-11-11 18:05:19 elapsed=4s bound=600s status=OK rc=0`

Probe (POST /api/v1/feedback through the real router + the real validation handler):

| Body | ENABLE_FEEDBACK_V2 false | true |
|---|---|---|
| Q1 `{identity_correct, compare_request_id}` | 422 VALIDATION_ERROR "body -> useful: Field required" | 200 |
| Q1 with no ids | 422 (same) | 200 |
| details `{identity_correct:'wrong', wrong_side:'second', correction, id}` | 422 | 200 |
| correction with U+2028 / U+0085 | 422 | 200 (not refused server-side) |
| correction of 81 chars | 422 | 422 "String should have at most 80 characters" |
| correction ending in a lone surrogate (raw JSON `\ud83d`) | - | 200 (accepted; the DB write NOT MEASURED) |
| Q2 `{preference:'first', id}` | 422 | 200 |
| upper-case compare_request_id | 422 | 200 (server canonicalises; client drops it) |
| ContactUs `{useful, mattered_most:[], change_suggestion, source:'contact'}` | 200 | 200 |

So spec 1.3 and 2.7 are CONFIRMED, and R-CL3-12's stop condition does not fire (confirmed).

Citations re-read and CONFIRMED: FeedbackCard.tsx:18-22 / :33 / :49-50 / :52-56 / :114; ResultsContent.tsx
:94 / :218 / :227 / :303-306 / :421-425 / :669-681; ResultsScreen.tsx :195 / :337 / :459 / :615-617 /
:645 / :960-964; HomeScreen.tsx :247 / :458 / :485 / :611-612 / :642; api.ts :272 / :311 / :417 / :692 /
:1028 / :1041 / :1065-1073; requestContext.ts:46 (the UUID_V4 pattern, not exported); feedback_routes.py
:151-174 / :178-190 / :196-259 / :358-400; cron_learning.py :69 / :120 / :556; cron_compare_judge.py
:611-623; features.ts export census (7 names) = cl2/scope P14 :18-26; en.json / ar.json 1,011 keys each;
the six removed keys at en :140-146 / ar :137-143; copy.s11 :186-191 and arCopy.s11e :132 / :140;
AuthService.requestPasswordReset :846-858; error_handler 429 envelopes (no `detail` key); the chunk-A
count (29 grep hits - 2 fixtures - 2 precommit files = 25) and the 5 chunk-B CLAUDE.md readers.

## Refuted claims

1. Spec 1.2 "Admin: No comparison_feedback reader" and the Q2 answer "at base NO reader reads any CL3
   column ... double-counted by nothing today" are true for the CL3 columns but INCOMPLETE as the brief's
   Q2 asks for "any admin view": two readers of the column CL3 STOPS writing (`useful`) are missing.
   - migrations/013_demographics_cohort.sql:46-58 `vw_cohort_feedback_lift`: `COUNT(*)` as total and
     `COUNT(*) FILTER (WHERE cf.useful = true)` as useful_count, joined on comparison_id. After CL3 every
     card row has useful NULL, so it counts in total_feedback and never in useful_count: useful_pct falls
     for a reason that is not user sentiment.
   - app/services/structured_comparison_service.py:5948 -> behavior_service.py:99-105
     `_compute_winner_agreement`: after CL3 the only `useful` writer left is ContactUs (`useful: category
     !== 'bug'`), so `winner_agreement` becomes a ContactUs-derived number (bug reports = "disagreed").
     No consumer of winner_agreement was found outside behavior_service (grep app/), so no user-visible
     effect; it is a stated-limit omission, not a defect.
2. Spec 9 L-CL3-5 "the 30/minute route limit is per client key": FALSE as deployed. The limiter key is
   `get_remote_address` (the Railway edge-proxy peer) while ENABLE_PROXY_AWARE_RATELIMIT is OFF
   (app/middleware/rate_limiter.py:53 and the module comment :159-166: "one bucket per path for the whole
   deployment"; the session-71 ledger's names read shows ENABLE_PROXY_AWARE_RATELIMIT 0 and no later set).
   So /feedback's 30/minute is effectively ONE app-wide bucket; CL3 writes 1-2 rows per card and
   ContactUs shares the bucket. Rows past it 429 and are swallowed. The same fact explains why the
   ForgotPassword 3/minute slowapi 429 (S81-24e) is reachable by unrelated users today.
3. Spec 1.8 "`common.errors.rateLimited` exists in both catalogs (en.json / ar.json :377)": en.json is
   :380 (ar.json :377). Cosmetic.
4. Spec 1.4 "ResultsScreen calls `identifyFromImages` itself (:316)": the call is at :306 (:305 the dynamic
   import). Cosmetic.
5. Spec 7 "The 4 test_precommit_hook*.py files are excluded" vs 1.10 "minus ... the 2 test_precommit_hook
   files": the grep hits exactly 2 precommit files (test_precommit_hook_phase_b.py,
   test_precommit_hook_phase_b_round2.py). Internal inconsistency; 2 is the measured number.
6. Spec 5.2 V9 is stated "RED via V1 precondition" with the assertion "the reanimated mock's
   FadeIn.duration / FadeInDown.delay call counts unchanged by the reveal". A correct GREEN FAILS it:
   2.4 puts `feedbackRevealed` state in ResultsContent, so the reveal re-renders ResultsContent and every
   `entering={FadeInDown.delay(..).duration(..)}` / `FadeIn.duration(400)` expression in its JSX
   (:308-309, :421-422, :672-673 and the rest) is evaluated again; the mock builders are module-level
   `jest.fn`s (__mocks__/react-native-reanimated.ts:72-84) and jest.config.js sets no clearMocks, so the
   counts move on ANY re-render. See B1.
7. Spec 7 "Client jest set: grep ... __tests__ src/services/__tests__ at base = 189 suites": jest's
   testMatch is `**/__tests__/**/*.test.ts(x)` (jest.config.js:4) and src/ holds THREE test dirs
   (src/components/__tests__, src/services/__tests__, src/utils/__tests__). src/utils/__tests__/
   currencyDisplay.test.ts:15-16, formatDate.test.ts:16-17 and formatNumber.test.ts:18-19 import
   `../../i18n/en.json` and `../../i18n/ar.json`, which this unit edits; none is in Appendix A. See B2.

## Blocking issues (apply before RED)

- B1 (V9 unsatisfiable; M25's only killer). Rewrite V9 structurally: in the rendered tree the
  `cl3-card` host's nearest ancestor that carries an `entering` prop is the `results-content-feedback`
  host (no intermediate host with `entering`), OR measure the builder-call DELTA of the reveal render
  against the delta of a no-op re-render of the same props (equal). Either form kills M25 and passes a
  correct GREEN. Also reset the builder mocks in the file's beforeEach (no global clearMocks).
- B2 (comm set). Add src/utils/__tests__/currencyDisplay.test.ts, formatDate.test.ts and
  formatNumber.test.ts to the client comm set (they import the two catalogs); re-run the comm grep over
  `__tests__ src/components/__tests__ src/services/__tests__ src/utils/__tests__` and restate the count
  (192 + the 5 cl3 files by this reading; the components/__tests__ hits PaywallBanner / TwoInputShell
  are comment-only mentions of HomeScreen and need not join).
- B3 (details step usable on a phone). The input is in the LAST card of a long ScrollView
  (ResultsContent.tsx:303-306: no keyboardShouldPersistTaps, no keyboard inset handling). On iOS the
  keyboard covers the field and the Send / Skip row, and with the default keyboardShouldPersistTaps
  ('never') the first tap on Send only dismisses the keyboard: the user taps twice or gives up, and the
  details row (the most valuable text R-CL3-3 asks for) is lost. 2.2 / 2.4 must add
  `keyboardShouldPersistTaps="handled"` and keyboard avoidance on that ScrollView (for example
  `automaticallyAdjustKeyboardInsets` on iOS, RN 0.81, or a scrollToEnd on input focus), plus a RED row
  that pins the ScrollView prop (by reading the rendered RCTScrollView props). This is a no-new-
  dependency change inside R-CL3-1 scope; it is App-Review lens material (2.1 / 4.0) for adversary 2.

## Corrections (non-blocking; fold into the spec before RED)

- C1 R5 / the Send guard: the jest TouchableOpacity / Pressable mocks pass `disabled` through as a prop
  only (__mocks__/react-native.ts:18-19, :71) and RNTL's fireEvent.press does not honour it, so R5's
  "press -> still 1 call" passes only if the handler itself returns when nothing is chosen. 2.2 must
  state the in-handler guard (and the `disabled` prop); otherwise R5 is red against a device-correct
  GREEN that relies on `disabled` alone.
- C2 R10 does not exercise two of the ranges 2.1 promises (U+0080..U+009F, U+2029): a mutant that drops
  the C1 range or U+2029 survives every row (M7 covers only U+000A). Add fromCharCode(0x85) and
  fromCharCode(0x2029) to R10's input.
- C3 sanitizeCorrection `slice(0, 80)` can cut a surrogate pair; the probe shows the ON route ACCEPTS a
  lone surrogate (200), so the failure would move to the fire-and-forget DB write (NOT MEASURED; a
  Postgres text value cannot hold an unpaired surrogate) and lose the whole details row incl.
  wrong_side. Make the cut surrogate-safe (drop a trailing high surrogate after the slice, or remove
  unpaired surrogates in the same pass as the control characters) and add one R10b row.
- C4 Reveal rows: (a) add V3b: a scroll event BEFORE any layout of `results-content-why` does not reveal
  (kills "reveal when no layout recorded" with a default verdictBottom of 0); (b) add V2b: a re-render
  of ResultsContent with new-identity props at 4 s still reveals at exactly 8 s (kills an effect whose
  deps restart the timer); state in 2.4 that the dwell effect runs once per mount (deps `[]`, eligibility
  captured at mount, as "eligibility is fixed per mount" already says).
- C5 V8: prefer `jest.spyOn(global, 'setTimeout')` -> the call with FEEDBACK_DWELL_MS, then
  `clearTimeout` called with its handle on unmount, over `jest.getTimerCount()`, which other subtree
  timers can make vacuous or red for reasons outside CL3 (by reading, no other ResultsContent child
  holds a JS timer today, so this is robustness, not a present defect).
- C6 R16 must mock features with `{ ...jest.requireActual(...), ENABLE_FEEDBACK_PREFERENCE_Q2: true }`
  (the card's dependency tree imports `features` / setters from the same module); state it.
- C7 Stated limits to add: L-CL3-11 the `useful` readers of refuted claim 1 (vw_cohort_feedback_lift's
  useful_pct falls; winner_agreement becomes ContactUs-derived); restate L-CL3-5 per refuted claim 2
  (one app-wide 30/minute bucket while ENABLE_PROXY_AWARE_RATELIMIT is OFF); L-CL3-3 add that an id-less
  No + details (no comparison_id, no compare_request_id) is two rows a row-id-keyed D22b reader counts
  twice.
- C8 Section 1.1 "Not-delivered states": name the S81-20 result-gate abstain explicitly (the brief lists
  "an abstain"): text_routes.py:614-636 raises a 400 through `_surface_comparison_failure`, so it reaches
  a state screen and never ResultsContent (confirmed by reading).
- C9 Fix the cosmetic citations of refuted claims 3-5.
- C10 The TextInput: add `textContentType="none"` (iOS) beside autoComplete="off" / autoCorrect={false}
  so the field is never offered contact or name autofill; and announce the step change for screen-reader
  users (accessibilityLiveRegion="polite" on the details container or an
  AccessibilityInfo.announceForAccessibility of the details question) with an R17 sub-assertion.

## Contract risks

- K1 Any OTA from a main carrying CL3 BEFORE the dated ENABLE_FEEDBACK_V2 ON line loses EVERY card
  answer (probe: 422 on every card body) AND removes the build-3 card's `useful: true` rows, which
  succeed today: during that window the app collects no result feedback at all. Owner step 1 "Merge now
  (no runtime effect)" holds only while no OTA ships. R-CL3-14 names "the SECOND OTA", but a hotfix OTA
  from main would be that OTA. The client cannot read the flag (version_routes' `surfaces` set is closed
  to chips, SF1). Recommend: flip ENABLE_FEEDBACK_V2 ON first (the build-3 body still 200s under ON:
  `useful` stays accepted), or record in the CLAUDE.md block and the eas-deploy runbook a hard stop "no
  OTA from a main carrying CL3 before the ON line".
- K2 Q-2 (partial excluded) has a large product effect the spec does not measure: ResultsContent.tsx
  :214-218 records that fragrance compares "routinely" hit the 30 s cap and return `metadata.partial`,
  and fragrances is the only live category. Excluding partials may suppress the card on a large share
  of launch traffic, while the identity question (resolved before the cap) is as meaningful there. The
  partial rate should be read (search_logs / compare_runs) before the ruling.
- K3 S81-24e copy: `common.errors.rateLimited` reads "give it a moment, then tap" (en.json:380), but the
  S81-24 throttle's day counter returns retry_after up to 86400 (spec F2). Mandated by R-S24-25, so not
  a spec defect; a copy-truth question for the owner once ENABLE_AUTH_THROTTLE_V2 flips.
- K4 `wrong_side` first / second = ResultsContent's `products`, i.e. `overview.products ?? products`
  (ResultsScreen.tsx:431-433). R-SF1-2 says "the body's product order". A D22b reader that joins a
  different array (search_logs product names, compare_runs) must use the same order; record it in the
  D22b follow-up.
- K5 No backend response key is removed, renamed or retyped; no refusal shape, billing path, cache key
  or error-code mapping changes (client-only; confirmed).

## Pin collisions

None missing from 4.1 beyond B2. Checked and clean by reading: brand.myez.s69 / brand.hardcoded.s69 /
honestCopy VERB_AR (the AR q1 "qaarnaa" has an Arabic letter after the root, so the standalone-word
regexes do not match); copy-policy (banned_en / banned_ar empty; scary_vocab_ar has no hit in the 12 AR
values); i18n/no-deleted-keys (pins only results.whatsNext / results.save); HomeScreen.minDisplayFloor
regexes (:118-160 survive an added line before each navigate call); ResultsScreen.comparisonId.m18
(:35-93 survive `result?.compareRequestId`); Results.memo.m21 (prop identifiers unchanged);
cl2/scope P14 (E4); no test pins `const { subscribe, abort } = streamComparison(` in HomeScreen source
(the only hit is HomeScreen.test.ts:126, its own fixture code). T23 OpenAPI, FY25 digests, w4_11 prompt
digests, test_retro_w2_1 URL pins and the W4-13 ledger fixture are untouched (no backend app/ change).

## Questions for the orchestrator

1. Q-2: rule partial in or out only after the partial share of fragrance compares is read (K2)?
2. K1: flip ENABLE_FEEDBACK_V2 before the merge, or add an explicit "no OTA from main before the ON
   line" stop to the CLAUDE.md block and the eas-deploy runbook?
3. B3: accept `keyboardShouldPersistTaps="handled"` + iOS keyboard insets on the Results ScrollView as
   in-scope for CL3?
4. PLAN_S81:175 says "(AR provided)" for Q1's copy; the spec writes its own AR. Is there an owner-provided
   AR string to use instead (none found in the session-81 runs/ or specs/)?
5. Q-1 (E5): rule tests/test_feedback_allowlist_superset.py in; and confirm the re-aimed vacuity guard
   (positive control) is not a fence weakening under the "never weaken a fence" rule.
6. Record refuted claim 1 (vw_cohort_feedback_lift, winner_agreement) as D22b scope or as a separate
   follow-up?
