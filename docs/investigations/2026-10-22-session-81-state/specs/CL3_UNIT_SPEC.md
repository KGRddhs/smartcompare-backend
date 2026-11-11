# CL3 TWO-QUESTION FEEDBACK CARD (+ S81-24e + the ContactUs source line) -- unit spec

- Unit: CL3 (client FOCUS: an App-Review-visible surface that takes user-entered text), carrying
  S81-24e (ForgotPassword RATE_LIMITED mapping, R-S24-25) and the ContactUs `source: 'contact'` line.
- Flag: NONE at runtime (a client unit; React Native reads no per-call env flag). ONE compile-time
  constant `ENABLE_FEEDBACK_PREFERENCE_Q2 = false` in `SmartCompareApp/src/config/features.ts` (R-CL3-8).
  Ships ONLY in the SECOND OTA, and only after the dated ledger line of `ENABLE_FEEDBACK_V2` ON on web
  (R-SF1-15 amended, R-CL3-14).
- Worktree: C:/Users/SynAckITPC/Documents/AI/sc-s81-cl3 (detached at the base sha; read-only for the
  spec writer; NO node_modules junction at the spec stage, so NO jest run in this round: every jest
  claim below is MEASURED BY READING or marked NOT MEASURED).
- Branch: feature/s81-cl3-feedback-card (the DEFECT_LEDGER row name), cut at GREEN from the then-main.
- Base sha (every measurement): a74caba7e3ff66b12e94178c912197c845ccbd14 (`git rev-parse HEAD` in the
  worktree, read in this run). `git status --short` EMPTY before this run and after it (the spec file
  lives under the gitignored `.qa-s80/`).
- Evidence pointers: the brief specs/CL3_BRIEF.md (R-CL3-1..14, Q1-Q7); PLAN_S81 :175 (the CL3 unit
  text); PLAN_S80 section 0 + runs/research/contract_freeze.json (the contract freeze); specs/
  RULINGS_S81_SF1.md + specs/S81_SF1_BRIEF.md (R-SF1-2 the meaning of every 046 column, R-SF1-15 the
  flip order, R-SF1-32 the no-answer 422, R-SF1-34 the control-character refusal); specs/
  RULINGS_S81_11.md (the client FOCUS precedent: AR copy rules, the App-Review lens, R-S11-27 the
  events fence); specs/S81_24_PR_BODY.md + RULINGS_S81_24.md R-S24-25 (S81-24e); DEFECT_LEDGER.md rows
  CL3 (:64) and S81-24e (:65); ledger.md (newest dated lines read 2026-11-11 17:39; no
  `ENABLE_FEEDBACK_V2` ON line exists: the flag is OFF in production; `ENABLE_COMPARISON_ID_ECHO` has no
  ON line either: OFF).
- Measurement location: <scratchpad>/CL3/ (C:/Users/SYNACK~1/AppData/Local/Temp/claude/
  cde30765822f13ce/b7d52d72-660d-49c1-9369-740355c48e44/scratchpad/CL3/): baseA.log, baseB.log,
  allow.log, sf1on.log, chunkA.txt, chunkB.txt, jest_comm.txt, ar_escaped.json.
- Sister units and contracts: SF1 (#392, merged; the wire contract this unit WRITES to); S81-08 (#377;
  the compare request id carriers `newCompareRequestId` / `withRequestContext` /
  `IdentifyResultWithRequestId` / `streamComparison(...).compareRequestId`, R-S08-15); S81-24 (#395; the
  auth throttle 429 envelope); CL2 (#387; the Home floor and the features.ts export census P14); S81-11
  / S81-11e (#389 / #396; the catalog count pins and the AR copy fences); D22 (#388; the learning job,
  stated limit L13) and S81-22 (#393; the judge): both are READERS this unit measures (Q2) and does
  not edit; D22b is the recorded reader-side follow-up. Known rebase hunks: none in flight on these
  files at the base (the S81-04c lane is backend-only).
- Personal-data rule: no real name, email, phone, Apple id, device id or account id in any file, test,
  fixture or log line. Product names in fixtures are synthetic ("Alpha Eau de Parfum 100ml" style);
  every correction sentinel is built at run time by concatenation; compare ids are minted by the
  expo-crypto mock or built from a constant uuid4 shape at run time.
- Byte rule: this file is pure ASCII and LF. The Arabic values in 2.6 are written as JSON escapes
  (ASCII), produced by a script from the typed strings and round-trip checked (`json.loads` of the
  escaped form equals the typed dict); GREEN pastes the decoded values into ar.json.

---------------------------------------------------------------------------------------------------

## 0. What the unit does

The Results screen asks the one question the learning loop needs: did we compare the right products.
At base `FeedbackCard.tsx` (132 lines) renders "Was this helpful?" and three positive-only chips that
post `{useful: true, comparison_id, mattered_most: [chip]}`; no client code writes `identity_correct`,
`wrong_side`, `preference` or `correction` (the D22 stated limit L13: no client writer of the
correctness signal). CL3 replaces the card:

1. Q1, always, ONE tap: "Did we compare the right products?" Yes / No / Not sure ->
   `identity_correct` correct / wrong / unsure. Yes and Not sure: ONE POST, then thanks.
2. No is RECORDED AT THE TAP (one POST `{identity_correct: 'wrong'}`), then an OPTIONAL details step:
   "Which one did we get wrong?" with the two product names (body order) + Both, one single-line field
   (maxLength 80, optional) and Send / Skip. Send posts ONE more row `{identity_correct: 'wrong',
   wrong_side?, correction?}`; Skip or leaving posts nothing more.
3. Q2 ("Which one would you pick?" = `preference`) exists behind the compile-time constant, value
   false: nothing of Q2 renders and `preference` is never sent.
4. The card appears only after 8 s of dwell on a delivered comparison or once the verdict section is
   scrolled into view, never on a History reopen and never on a partial result; once revealed it
   stays; once answered it shows thanks for that result.
5. Ids: `comparison_id` when the result has one; `compare_request_id` = the id the compare's own
   requests carried (text stream / REST fallback, link, camera), plumbed additively; never minted for
   feedback.
6. The correction text travels ONLY in the feedback POST body.
7. Riders: S81-24e (ForgotPassword renders `common.errors.rateLimited` for the coded RATE_LIMITED);
   ContactUs adds `source: 'contact'` and keeps `useful`.

No backend app/ file changes. One backend TEST file changes deliberately (E5, open question Q-1).

---------------------------------------------------------------------------------------------------

## 1. Base state (MEASURED at a74caba7 in this run)

### 1.1 The card and its mount

| Site | file:line (base) | Measured fact |
|---|---|---|
| Card component | SmartCompareApp/src/components/FeedbackCard.tsx:1-132 | Header :1-11; `MATTERED_OPTIONS` :18-22 (`{ key: 'accurate' / 'detailed' / 'fast', i18nKey }`); props `comparisonId?`, `submitted?`, `onSubmitted?` :24-28; `submitted = parentSubmitted ?? localSubmitted` :33 (the parent always passes a boolean, so the local flag is dead; thanks follows `onSubmitted` -> parent state); guard `if (submitting) return; setSubmitting(true)` :49-50 (a STATE guard: two presses in one frame both pass it); POST `{useful: true, comparison_id, mattered_most: [chipKey]}` :52-56 awaited inside try / `catch {}` :57-59; thanks :36-42 text `results.feedback.thanks`; title :67 `results.feedback.title`; chips testID `feedback-chip-${key}` :72, `accessibilityRole="button"` :73, height 36 :114 (below 44 pt). No trackEvent, console, Sentry or storage call. |
| Mount | SmartCompareApp/src/components/results/ResultsContent.tsx:669-681 | `# 8 Feedback prompt` comment :669; wrapper `<Animated.View entering={FadeInDown.delay(600).duration(400)} testID="results-content-feedback">` :672-674; `<FeedbackCard comparisonId={feedbackComparisonId} submitted={feedbackSubmitted} onSubmitted={onFeedbackSubmitted} />` :676-680; LAST child of the `<ScrollView>` (:303-682). The card mounts unconditionally whenever ResultsContent renders. |
| Scroll container | ResultsContent.tsx:303-306 | `<ScrollView style={styles.scroll} contentContainerStyle={styles.scrollContent}>`: no onScroll, no testID, no scrollEventThrottle. |
| Verdict section | ResultsContent.tsx:421-425 | `<Animated.View entering={FadeInDown.delay(200).duration(400)} style={styles.sectionLean} testID="results-content-why">`: a direct child of the scroll content (onLayout y is content-relative). |
| Partial / degraded | ResultsContent.tsx:218 / :227 | `isPartial = metadata.partial === true`; `isDegraded = isDegradedComparison(result)`. BOTH render the card at base. |
| Stored vs live | ResultsContent.tsx:94 (prop), :154; ResultsScreen.tsx:960 | `resultOrigin={route?.params?.comparison_id ? 'stored' : 'live'}`. |
| Parent state | ResultsScreen.tsx:195, :615-617, :962-964 | `feedbackSubmitted` state; `onFeedbackSubmittedStable = useCallback(() => setFeedbackSubmitted(true))`; props `feedbackSubmitted`, `onFeedbackSubmitted`, `feedbackComparisonId={comparisonId}`. |
| comparison_id | ResultsScreen.tsx:459 | `comparisonId = result?.comparison_id ?? route?.params?.comparison_id`; comment :450-458: fresh compares carry NO id (the backend echo `ENABLE_COMPARISON_ID_ECHO` is OFF per the ledger). |
| History reopen | ResultsScreen.tsx:645 | `openedFromHistory = !!route?.params?.comparison_id` (the push pre-prompt effect). Re-open entries: HistoryScreen.tsx:801 / :810, HomeScreen.tsx:1242, ProfileScreen.tsx:412: all `{ comparison_id }`. |
| Not-delivered states | ResultsScreen.tsx:806-900 (timeout / auth / error states), :909-940 (`products.length < 2` empty state) | Refusals (CATEGORY_NOT_LIVE, same_identity, category_conflict), timeouts, vision failures and engine outages render a state screen and NEVER ResultsContent; Home navigates to Results only on `data.success` (HomeScreen.tsx:479 / :640). So the only non-full results that reach the card are `metadata.partial` and degraded bodies. |

### 1.2 The wire (submitFeedback, the route, the readers)

| Site | file:line | Measured fact |
|---|---|---|
| submitFeedback | SmartCompareApp/src/services/api.ts:1065-1073 | `data: { useful: boolean; comparison_id?; mattered_most?; change_suggestion? }` -> `api.post('/api/v1/feedback', data)` with NO config (not on the metered allowlist: no device / consent / id header; pinned by s81_08/requestHeaders B18 :622-636). |
| Route | app/api/feedback_routes.py:358-400 | `@limiter.limit("30/minute")` :359; auth-optional; `v2 = feedback_v2_enabled()`; the six v2 kwargs reach `save_feedback` only ON (:385-393); response `{"success": True, "message": "Feedback received"}` after a fire-and-forget write. |
| OFF model | feedback_routes.py:195-226 | `_FeedbackRequestBase` (the frozen base model: `useful: bool` REQUIRED :201; pydantic default extra = ignore, no model_config); the OFF before-validator :250-258 validates the dict through it and returns ONLY its dump, so every v2 key is accepted and dropped. |
| ON model | feedback_routes.py:229-249, :260-306 | `useful: Optional[bool]`; `identity_correct` correct/wrong/unsure; `wrong_side` first/second/both; `preference` first/second/neither/unsure; `correction` (raw cap 1,000, C0 + DEL refused, strip, blank -> None, <= 80 after strip; :151-157, :260-280); `source: Literal["result","contact"] = "result"`; `compare_request_id` uuid (:163-174); ON a body with no answer field 422s with NO_ANSWER_MESSAGE (:178-190, :255-257). |
| Writer | app/services/feedback_service.py:145-232 | ON: `useful` written only when not None; each 046 column only when not None; the except arm logs `type=%s code=%s` only (R-SF1-27), never the row. |
| Learning job | scripts/cron_learning.py:69, :86, :120-134, :370-388, :538-566 | Reads `comparison_feedback` with `FEEDBACK_COLUMNS = "id,user_id,comparison_id,useful,winner_correct,price_correct,specs_correct,created_at"` (:69): NOT `identity_correct` / `wrong_side` / `preference` / `correction`. `identity_wrong` comes ONLY from `kb_feedback` (:120, :587-588). Cases dedupe per (bucket, case_id) (:370-382) where case_id = ("cf", comparison_id) or ("cf-row", row id) when comparison_id is absent (:556). |
| Judge | scripts/cron_compare_judge.py:611-623 | `_user_wrong` selects `comparison_id,winner_correct` ONLY, keyed by comparison_id, into a SET (a second row for the same comparison cannot double count). |
| Admin | app/api/admin_routes.py | No `comparison_feedback` reader (grep: no hit). structured_comparison_service.py:5948 reads `useful` only (the behaviour profile). |

Q2 answer (R-CL3-3): at base NO reader reads any CL3 column, so CL3's one-or-two rows per card are
double-counted by nothing today. CL3 alone therefore does NOT feed the D22 buckets or the judge's
user-wrong trigger: closing L13 end to end needs the reader-side D22b follow-up (read
`identity_correct` / `wrong_side`, key a case by comparison_id, else compare_request_id, else the row
id, so the details row of a No collapses into the same case). Recorded as stated limit L-CL3-1.

### 1.3 Q3: the flag-OFF and flag-ON answers for the bodies CL3 sends (from the code + the SF1 pins)

| Body | OFF (prod today) | ON |
|---|---|---|
| Q1 row `{identity_correct, comparison_id?, compare_request_id?}` | 422 `Validation error: body -> useful: Field required` (pinned: tests/test_s81_sf1_surfaces_be.py P10 row `new_no_useful` :414, P10_MODEL :439-440); the card swallows it: the answer is LOST | 200; `useful` None not written; `identity_correct` + ids stored, `source` 'result' (R13 :505-519, R14 :530-549) |
| Details row `{identity_correct: 'wrong', wrong_side?, correction?, ids}` | 422 (same) | 200; correction stripped, <= 80, control chars refused (R15 :557-573, R15b :575-587) |
| Q2 row `{preference, ids}` (constant false: never sent) | 422 | 200 (`preference` alone is an answer: R15c :589-603) |
| Contact row `{useful, mattered_most: [], change_suggestion, source: 'contact'}` | 200; `source` accepted and DROPPED; stored row byte-identical to base (P11 :468-481, P12 :484-502) | 200; `source` = 'contact' stored (R16 :605-611) |

So R-CL3-12's stop condition does NOT fire: the flag-OFF model accepts the extra `source` (no 422).
The card's rows 422 while OFF: that is why the unit ships only after the ON ledger line (R-CL3-14;
stated limit L-CL3-2 for a rollback). Rate limit: 30/minute per client key (slowapi); a card writes at
most 2 rows (3 if Q2 is ever turned on).

### 1.4 Q1: the compare request id carriers (R-CL3-5)

| Entry | Where the id is minted | Reaches Results at base? |
|---|---|---|
| Text (SSE or the single REST compare) | api.ts:692 `streamComparison` mints ONE id per attempt, returns it as `compareRequestId` (:685-686, :1028) | NO: HomeScreen.tsx:458 destructures only `{ subscribe, abort }`; onComplete calls `navigateToResultsWithFloor(data)` (:485) -> `navigate('Results', fastHit ? { result, fastHit: true } : { result })` (:247). |
| Link (URL) | HomeScreen.tsx:611-612 `urlCompareRequestId` + `urlCompareRequestIdRef` ("kept for SF1 / CL3") | NO: `navigateToResultsWithFloor(response.data)` (:642). |
| Camera / gallery | ResultsScreen calls `identifyFromImages` itself (:316); api.ts:311 mints the id and attaches it as `data.compareRequestId` (:417; type `IdentifyResultWithRequestId` :272) | PARTLY: on the screen, but `setResult((data.result ?? data))` (:337) DROPS it when the body nests under `data.result`. |
| `compareTextPair` | api.ts:1041-1060 mints internally | No screen calls it (grep: no caller under src/ outside api.ts). |
| History / Profile / push / Smart-pick reopen | none | Only `comparison_id`; no card anyway. |

Proposed smallest plumbing (2.3): attach the id to the RESULT OBJECT in Home (as S81-08 already does
for identify), not as a new route param: a route param would re-pin `ResultsEntryParams.a18`
(declared-param list :156-161) and the three `HomeScreen.minDisplayFloor` regexes (:119, :124, :160);
attaching keeps both green and unedited. The alternative is open question Q-3.

### 1.5 Q4: readers of what is removed or changed

| Removed / changed | Readers (grep over SmartCompareApp/ and tests/, measured) |
|---|---|
| keys `results.feedback.title/.accurate/.detailed/.fast/.placeholder/.submit` | src: FeedbackCard.tsx only (title, accurate, detailed, fast; placeholder and submit have NO src reader at base). Tests: `__tests__/components/FeedbackCard.designChips.test.tsx` :34, :39 only. No defaultValue literal, no backend reader. |
| testIDs `feedback-chip-*` | FeedbackCard.designChips.test.tsx :35-37, :47, :59, :70 only. |
| `FeedbackCard` default export / props | 12 suites mock the module (render :101, rewriteOrder :115, a11y.w311 :90, runnerUp :80, confidenceSheet :55, imageUrl :70, partialNote :77, perCategory :51, scoreGuard :73, specsComparisonShape :55, v2Wiring :55, medicalNote.s74 :112, s11/gateRows :258, s11/honestUnknowns :116, screens/ResultsScreen.degraded.s69 :101); NONE asserts on the mocked card's output (grep for `mock-feedback` outside the mock definitions: no hit). Wrapper testID `results-content-feedback` asserted present at mount by render.test :205, rewriteOrder :234 / :285, ResultsScreen.bundleE.s3 :133: the wrapper STAYS mounted, only its child is deferred. |
| `submitFeedback` | Mocked in 8 suites with `jest.fn()`; called for real by s81_08/requestHeaders B18 :625 with `{ useful: true }` (still type-valid after the widening). |
| `mattered_most: [chipKey]` + the chip literals | BACKEND tests/test_feedback_allowlist_superset.py (reads FeedbackCard.tsx by path): `test_chip_keys_are_the_values_sent_as_mattered_most` (asserts the literal `mattered_most: [chipKey]`), `test_some_chip_keys_discovered` (>= 3 `{ key: '...' }` literals), `test_valid_mattered_most_is_superset_of_feedback_chips` (a NEW `{ key: 'x' }` literal not in VALID_MATTERED_MOST would go red). E5. |
| Key count 1,011 | s11/copy.s11.test.tsx :186-191 (`1013 - DELETED + ADD`), s11e/arCopy.s11e.test.ts :132 / :140 (`{ ar: 1011, en: 1011 }`). E2 / E3. |
| features.ts export names | cl2/scope.cl2.test.ts P14 :18-26 / :40-47 (exact export list). E4. |
| ContactUs body | ContactUsScreen.test.tsx :105-112 / :124-133 (`expect.objectContaining`: an extra `source` key stays green). |
| ForgotPassword source | Screens.bundleD.contract.test.ts :261-279 (the import, `requestPasswordReset(email.trim().toLowerCase())`, the Login nav): untouched by the mapping. AuthScreens.test.tsx :170-176 (deferred). |

### 1.6 Q5: "a rendered, delivered comparison"

Home navigates only on a COMPLETE success (SSE `onComplete` with `data.success`, :479; URL
`response.data.success`, :640); the Results screen never streams. Camera: ResultsScreen sets `result`
only on `action === 'comparison'` with success. So "delivered" = ResultsContent mounted with a
result (ResultsScreen.tsx:953-970). The dwell clock starts at ResultsContent's mount (after the
camera floor / history floor have elapsed, because ResultsContent mounts only then).

### 1.7 Q6: RTL, long names, accessibility (measured base conventions)

- Product names: `products[i].name` (ResultsContent hero and DimensionBars :564-565). Body order is
  `wrong_side`'s order (R-SF1-2: "in the body's product order").
- RTL: rows use `flexDirection: 'row'`, which RN mirrors under RTL; the textAlign fence
  `__tests__/rtl/textAlignLogical.contract.test.ts` forbids `textAlign: I18nManager.isRTL ?` anywhere
  in src/ (:171-200).
- Reduce motion: no `useReducedMotion` / `AccessibilityInfo.isReduceMotionEnabled` call exists in src/
  and the jest mocks (`__mocks__/react-native-reanimated.ts`, `__mocks__/react-native.ts`) export
  neither; ruled design: the revealed card has NO entering animation at all (2.4), so no mock change.
- 44 pt: the base chips are 36 tall (FeedbackCard.tsx:114).

### 1.8 Q7: ForgotPassword and the 429

- ForgotPasswordScreen.tsx:37-55: `requestPasswordReset(email.trim().toLowerCase())`; catch ->
  `setError(parseApiError(err).message)` (:50-51); rendered at :96-98.
- authService.ts:846-858 `requestPasswordReset`: rethrows the axios error unchanged unless
  `error.response.data.detail` exists.
- The 429 envelope (both forms): the slowapi `@limiter.limit("3/minute")` (auth_routes.py:1136) ->
  `rate_limit_handler` (error_handler.py:309-334); the S81-24 gate `auth_throttle.gate("password_reset")`
  (auth_routes.py:1141-1142, auth_throttle.py:460-463 `HTTPException(429, detail={"error":
  THROTTLED_MESSAGE, "code": "RATE_LIMITED", "retry_after": n})`) -> `http_exception_handler`
  (error_handler.py:172-197). Both render `{success: false, error: "Rate limit exceeded. Please try
  again later.", code: "RATE_LIMITED", request_id, retry_after_seconds}` + `Retry-After` (W1-9), and NO
  `detail` key. So the error reaches the screen unchanged and `parseApiError` (api.ts:1130-1218) returns
  `{ message: data.error, code: 'RATE_LIMITED', retryAfterSeconds }`: TODAY the screen renders the raw
  English server text (which contains the copy-policy scary phrase "try again") in both locales, on the
  existing slowapi 3/minute limit and, once ENABLE_AUTH_THROTTLE_V2 flips, on the throttle.
- `common.errors.rateLimited` exists in both catalogs (en.json / ar.json :377).
- No resend-verification caller exists under src/ (grep: no hit), so R-S24-25's "any resend caller
  that appears" adds nothing.

### 1.9 Libraries and guards (pinned, read from package.json; NOT MEASURED on node_modules)

@sentry/react-native ~7.2.0 (`sendDefaultPii: false`, sentry.ts:282; no replay integration; the
breadcrumb scrubbers sentry.ts:153-213 scrub data dicts and URLs; an XHR breadcrumb carries method /
url / status, not the body: NOT MEASURED on the pinned SDK, no node_modules here); react-native
0.81.5; react-native-reanimated ~4.1.1; @testing-library/react-native ^13.3.3; jest ^29.7.0; expo
~54.0.37. Guards the new code must not trip: the copy policy (src/i18n/.copy-policy.json: banned_en,
banned_ar, scary_vocab_en incl. "try again", scary_vocab_ar), the honestCopy diacritic rule, the
textAlign fence, i18n/no-missing-referenced-keys (every `t('...')` key exists), the events allowlist
fence (tests/test_events_allowlist_superset.py: NO new trackEvent), test_security_regression
(no SERVICE_KEY in src/, no bare console in api.ts / authService.ts), brand.hardcoded.s69, the
features.ts export census (E4), ResultsEntryParams.a18 (kept green by 2.3), HomeScreen.minDisplayFloor
(kept green), Results.memo.m21 (ResultsContent stays React.memo; new props are strings).

### 1.10 Line endings and base pass state

Every file this unit edits is index LF / working-copy CRLF (`git ls-files --eol`: i/lf w/crlf;
`grep -c $'\r$'` equals the line count): FeedbackCard.tsx 132, ResultsContent.tsx 883,
ResultsScreen.tsx 1134, HomeScreen.tsx 1644, ContactUsScreen.tsx 358, ForgotPasswordScreen.tsx 240,
features.ts 123, api.ts 1511, types.ts 683, en.json 1077, ar.json 1074, cl2/scope.cl2.test.ts 92,
s11/copy.s11.test.tsx 261, s11e/arCopy.s11e.test.ts 180, FeedbackCard.designChips.test.tsx 72,
tests/test_feedback_allowlist_superset.py 184, CLAUDE.md 1099. The Edit tool preserves CRLF; a
whole-file diff in `git diff --stat` is a defect. New files: LF, ASCII.

Base runs (bounded runner, .venv-qaren, flags unset unless named):

- Chunk A = the 25 SmartCompareApp-scanning backend tests (grep -rl SmartCompareApp tests/ minus 2
  fixtures and the 2 test_precommit_hook files; list in chunkA.txt):
  `2047 passed, 4 deselected` /
  `[hermeticity] sentinel checked 2047 test(s)` / `[netguard] blocked 39 attempt(s) from 29 node(s)` /
  `[pyt] tag=cl3-spec-baseA start=2026-11-11 17:42:42 end=2026-11-11 17:43:37 elapsed=54s bound=1200s status=OK rc=0`
- Chunk B = the CLAUDE.md readers not in A (test_behavior_dimension_translation, test_s81_s04_spend_breaker,
  test_s81_s08b_legacy_fingerprint, test_s81_s08b_gate_rows, test_s81_s23_bypass_retire):
  `458 passed` / `[hermeticity] sentinel checked 458 test(s)` /
  `[pyt] tag=cl3-spec-baseB start=2026-11-11 17:43:41 end=2026-11-11 17:43:58 elapsed=17s bound=1200s status=OK rc=0`
- The E5 file alone: tests/test_feedback_allowlist_superset.py `11 passed` /
  `[netguard] blocked 0 attempt(s) from 0 node(s)` /
  `[pyt] tag=cl3-spec-allow start=2026-11-11 17:44:05 end=2026-11-11 17:44:09 elapsed=4s bound=600s status=OK rc=0`
- The SF1 contract pins + E5 with `ENABLE_FEEDBACK_V2=true` exported for that one call
  (test_s81_sf1_surfaces_be.py, test_s81_sf1_gate_rows.py, test_feedback_allowlist_superset.py):
  `213 passed` / `[pyt] tag=cl3-spec-sf1on start=2026-11-11 17:44:09 end=2026-11-11 17:44:18 elapsed=9s bound=600s status=OK rc=0`

So the backend base record of the CL3 set at a74caba7 = 30 files, 2,505 passed, 0 failed (failed
node-id set EMPTY). Jest at base: NOT MEASURED in this round (no junction); the accepted jest baseline
is the brief's (4,030 passed + the four config/nativeBundle.w37 drift nodes + 13 skipped + 13 todo).

---------------------------------------------------------------------------------------------------

## 2. Contract

### 2.1 Flag and constants

- No runtime flag. `export const ENABLE_FEEDBACK_PREFERENCE_Q2 = false;` in
  src/config/features.ts (one new export, placed after `ENABLE_EXPO_FETCH_SSE_DEFAULT`, with a comment
  naming R-CL3-8 and the precondition "turn on only by a later OTA after Q1's answer rate is read").
  Read directly by the card (no getter, no test override setter: the ON path is tested by
  `jest.mock('../../src/config/features', ...)`), so the export census grows by exactly ONE name (E4).
- New pure module `src/services/feedbackAnswers.ts` (no React, no I/O, ASCII):
  - `FEEDBACK_DWELL_MS = 8000` (test seam; production value 8000).
  - `CORRECTION_MAX = 80` (= backend CORRECTION_MAX_CHARS).
  - `isCompareRequestId(v: unknown): v is string`: the S81-08 canonical lower-case uuid4 shape
    (`^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`, the same pattern as
    requestContext.ts:46, copied, because requestContext does not export it and its export set is not
    widened by this unit).
  - `sanitizeCorrection(raw: unknown): string | undefined`: non-string -> undefined; remove every
    code point in U+0000..U+001F, U+007F, U+0080..U+009F, U+2028, U+2029 (the regex built from
    `String.fromCharCode` ranges so the source stays ASCII); trim; take the first 80 UTF-16 units
    (`slice(0, 80)`; the TextInput maxLength already caps at 80 units, which is <= 80 code points, so
    the backend's 80-char cap after strip can never be exceeded); trim again; '' -> undefined.
  - `feedbackIds(comparisonId?: string, compareRequestId?: string)`: `{ comparison_id }` only when a
    non-empty string; `{ compare_request_id }` only when `isCompareRequestId`; never mints.
  - `attachCompareRequestId(body: unknown, id: string | null | undefined): void`: when `body` is a
    non-null object and `isCompareRequestId(id)`, sets `body.compareRequestId = id`; else no-op (the
    S81-08 identify precedent, api.ts:417).
- `submitFeedback` (api.ts:1065) parameter type widened ADDITIVELY: `useful?: boolean` (was
  required), plus `compare_request_id?: string`, `identity_correct?: 'correct' | 'wrong' | 'unsure'`,
  `wrong_side?: 'first' | 'second' | 'both'`, `preference?: 'first' | 'second' | 'neither' | 'unsure'`,
  `correction?: string`; NO `source` member (the card cannot send it: R-CL3-4). The body of the
  function is byte-identical (`api.post('/api/v1/feedback', data)`, no config: the request stays off
  the metered allowlist).
- `ComparisonResult` (types.ts:285) gains `compareRequestId?: string` with a comment: client-only,
  set by Home / the camera path from the compare's own X-Compare-Request-Id, never by the server.

### 2.2 The card (FeedbackCard.tsx, rewritten; default export and file path kept)

Props: `comparisonId?: string; compareRequestId?: string; productNames: [string, string]` (new,
body order) `; submitted?: boolean; onSubmitted?: () => void`.

States: `q1` -> (`thanks` | `details` | `q2`) -> `thanks`. `submitted === true` from the parent
renders `thanks` (parent's flag wins, as at base).

| Step | Renders (testIDs) | Action -> POST (exact body; `ids` = feedbackIds(...)) | Next |
|---|---|---|---|
| q1 | `feedback-card`, text `results.feedback.q1` (testID `feedback-q1`), buttons `feedback-q1-yes` / `feedback-q1-no` / `feedback-q1-unsure` (labels `results.feedback.yes` / `.no` / `.unsure`) | Yes -> `{identity_correct: 'correct', ...ids}`; Not sure -> `{identity_correct: 'unsure', ...ids}`; No -> `{identity_correct: 'wrong', ...ids}` | Yes: `q2` when `ENABLE_FEEDBACK_PREFERENCE_Q2` else `thanks`; Not sure: `thanks`; No: `details` |
| details | `feedback-details`, text `results.feedback.whichWrong`, side choices `feedback-side-first` / `feedback-side-second` (labels = productNames[0] / [1], trimmed; a blank name omits that choice) / `feedback-side-both` (`results.feedback.both`), input `feedback-correction-input` (placeholder + accessibilityLabel `results.feedback.correctionPlaceholder`, `maxLength={80}`, `multiline={false}`, `autoCorrect={false}`, `autoComplete="off"`, `returnKeyType="done"`), buttons `feedback-send` (`results.feedback.send`), `feedback-skip` (`results.feedback.skip`) | Send (enabled iff a side is chosen OR `sanitizeCorrection(text)` is defined) -> `{identity_correct: 'wrong', wrong_side?, correction?, ...ids}` (keys present only when set); Skip -> NO POST | `thanks` |
| q2 (constant true only) | `feedback-q2`, text `results.feedback.q2`, `feedback-q2-first` / `feedback-q2-second` (product names), `feedback-q2-neither` (`results.feedback.neither`), `feedback-q2-unsure` (`results.feedback.unsure`), `feedback-skip` | a choice -> `{preference: <first/second/neither/unsure>, ...ids}` (preference ONLY: Q-4); Skip -> no POST | `thanks` |
| thanks | `feedback-thanks`, text `results.feedback.thanks` | none | terminal; `onSubmitted()` called ONCE on entering it |

Rules:
- NEVER `useful`, `mattered_most`, `source`, `change_suggestion` in any card body (R-CL3-4).
- Fire-and-forget: each POST is started and NOT awaited for the UI: `submitFeedback(body).catch(() =>
  undefined)`; the step transition happens synchronously on the tap; a rejection never renders an
  error and never blocks thanks or the details step.
- Double-tap guard: a `useRef` latch per step (q1, details, q2) set synchronously BEFORE the POST; a
  second press of any control of a latched step is a no-op (stronger than the base state guard).
- `onSubmitted` is called exactly once, on entering `thanks` (so the No -> details step is NOT ended by
  the parent flag).
- Leaving the screen on `details` / `q2`: nothing more is posted (no unmount effect posts).
- The correction text lives only in component state and in the Send body: no trackEvent / trackEvents,
  no console.*, no Sentry call or breadcrumb, no AsyncStorage / SecureStore / swrCache write, no
  navigation param (R-CL3-7).
- Accessibility: every answer control `accessibilityRole="button"` with `accessibilityLabel` = its
  visible text; the side and Q2 choices `accessibilityRole="radio"` with `accessibilityState={{
  selected }}` (side) inside a container `accessibilityRole="radiogroup"` labelled by the question;
  Send exposes `accessibilityState={{ disabled }}`; every pressable `minHeight: 44` and `hitSlop` none
  needed; question text `accessibilityRole="header"`.
- Long names / RTL: side and Q2 labels `numberOfLines={1}` + `ellipsizeMode="tail"`; layout rows with
  `flexDirection: 'row'` + `flexWrap: 'wrap'` (RN mirrors under RTL; no textAlign ternary); the
  thanks text keeps `textAlign: 'center'`.
- No new dependency, no new event type, no animation inside the card.

### 2.3 Ids plumbing (R-CL3-5)

- HomeScreen.tsx:458: `const { subscribe, abort, compareRequestId } = streamComparison(` ; in
  onComplete, the line BEFORE `navigateToResultsWithFloor(data);` (:485):
  `attachCompareRequestId(data, compareRequestId);`.
- HomeScreen.tsx:642: the line BEFORE `navigateToResultsWithFloor(response.data);`:
  `attachCompareRequestId(response.data, urlCompareRequestId);` (the local minted at :611).
- ResultsScreen.tsx camera effect: a state `const [cameraCompareRequestId, setCameraCompareRequestId] =
  useState<string | undefined>(undefined);` set from `data?.compareRequestId` in the
  `action === 'comparison'` success branch, BEFORE `setResult(...)` (:337), only when
  `isCompareRequestId`.
- ResultsScreen derives `feedbackCompareRequestId = route?.params?.comparison_id ? undefined :
  (isCompareRequestId(cameraCompareRequestId) ? cameraCompareRequestId :
  isCompareRequestId(result?.compareRequestId) ? result.compareRequestId : undefined)` and passes it
  as the NEW optional ResultsContent prop `feedbackCompareRequestId` (beside `feedbackComparisonId`,
  :964). Nothing mints an id for feedback: `newCompareRequestId` is never called by ResultsScreen,
  ResultsContent, FeedbackCard or feedbackAnswers.
- Route params UNCHANGED (`ResultsEntryParams.a18` and `HomeScreen.minDisplayFloor` stay green,
  unedited).

### 2.4 The reveal (ResultsContent.tsx, R-CL3-6)

- `feedbackEligible = resultOrigin !== 'stored' && !isPartial` (degraded results stay eligible:
  the identity question is still meaningful when only the write-up failed; Q-2 asks the orchestrator
  to confirm the partial exclusion, which differs from the base mount condition).
- `const [feedbackRevealed, setFeedbackRevealed] = useState(false)`; an effect on mount, when
  eligible, `setTimeout(() => setFeedbackRevealed(true), FEEDBACK_DWELL_MS)`, cleared on unmount.
- The verdict wrapper (:421-425) gains `onLayout` storing `verdictBottom = y + height` in a ref;
  the ScrollView (:303) gains `onScroll={handleFeedbackScroll}` + `scrollEventThrottle={64}`;
  `handleFeedbackScroll` reveals when `contentOffset.y + layoutMeasurement.height >= verdictBottom`
  (the verdict's BOTTOM edge is inside the viewport) and a layout has been recorded. Only scroll
  events count (a mount where the verdict is already visible reveals at the first scroll or at 8 s).
- Once revealed it stays (no handler sets it back to false). Eligibility is fixed per mount.
- The wrapper `<Animated.View entering={FadeInDown.delay(600).duration(400)} testID="results-content-
  feedback">` stays mounted ALWAYS at the same place (the last scroll child), so nothing above it moves;
  its child is `{feedbackEligible && feedbackRevealed ? <FeedbackCard ... /> : null}` with NO entering
  animation of its own (reduce-motion users therefore get no animation from the reveal; the wrapper's
  existing mount animation is base behaviour, unchanged).
- Props passed: `comparisonId={feedbackComparisonId}`, `compareRequestId={feedbackCompareRequestId}`,
  `productNames={[products[0]?.name ?? '', products[1]?.name ?? '']}`, `submitted={feedbackSubmitted}`,
  `onSubmitted={onFeedbackSubmitted}`.

### 2.5 Riders

- S81-24e, ForgotPasswordScreen.tsx:50-51 becomes: `const parsed = parseApiError(err);
  setError(parsed.code === 'RATE_LIMITED' ? t('common.errors.rateLimited') : parsed.message);`.
  Every other branch (empty email, success, every non-RATE_LIMITED error) renders exactly what it
  renders at base; the screen's same answer for unknown emails (the success screen) is untouched. No
  number from `retry_after_seconds` is rendered.
- ContactUs, ContactUsScreen.tsx:91-99: the POST body gains `source: 'contact'` as its LAST key;
  `useful: category !== 'bug'`, `mattered_most: []`, `change_suggestion` unchanged.

### 2.6 Copy (Arabic-first; EN + AR complete; every AR value [NATIVE READ])

Keys REMOVED from both catalogs: `results.feedback.title`, `.accurate`, `.detailed`, `.fast`,
`.placeholder`, `.submit` (no other reader: 1.5). Key CHANGED: `results.feedback.thanks` (the base AR
value carries a tanween, a fence violation the reword removes). Keys ADDED (11): q1, yes, no, unsure,
whichWrong, both, correctionPlaceholder, send, skip, q2, neither. Leaf count 1,011 - 6 + 11 = 1,016
per catalog, parity 0. Inserted where the removed keys were (after `results.feedback.thanks`'s
position, en.json :140-146 / ar.json :137-143), in the order of the table.

| Key | EN | AR (JSON escapes below) |
|---|---|---|
| results.feedback.q1 | Did we compare the right products? | [NATIVE READ] |
| results.feedback.yes | Yes | [NATIVE READ] |
| results.feedback.no | No | [NATIVE READ] |
| results.feedback.unsure | Not sure | [NATIVE READ] |
| results.feedback.whichWrong | Which one did we get wrong? | [NATIVE READ] |
| results.feedback.both | Both | [NATIVE READ] |
| results.feedback.correctionPlaceholder | The right product name (optional) | [NATIVE READ] |
| results.feedback.send | Send | [NATIVE READ] |
| results.feedback.skip | Skip | [NATIVE READ] |
| results.feedback.thanks (changed) | Thanks. That helps us get it right. | [NATIVE READ] |
| results.feedback.q2 | Which one would you pick? | [NATIVE READ] |
| results.feedback.neither | Neither | [NATIVE READ] |

The AR values (decode with `json.loads`; written by a script, checked in this run: no character in
U+064B..U+0652 or U+0670, no ASCII or Arabic-Indic digit, none of the copy-policy banned_ar or
scary_vocab_ar terms, no standalone verb `qaarin` (the honestCopy VERB_AR word-boundary rule), no brand
word):

```json
{
 "results.feedback.q1": "\u0647\u0644 \u0642\u0627\u0631\u0646\u0627 \u0627\u0644\u0645\u0646\u062a\u062c\u064a\u0646 \u0627\u0644\u0635\u062d\u064a\u062d\u064a\u0646\u061f",
 "results.feedback.yes": "\u0646\u0639\u0645",
 "results.feedback.no": "\u0644\u0627",
 "results.feedback.unsure": "\u063a\u064a\u0631 \u0645\u062a\u0623\u0643\u062f",
 "results.feedback.whichWrong": "\u0623\u064a \u0645\u0646\u062a\u062c \u0623\u062e\u0637\u0623\u0646\u0627 \u0641\u064a\u0647\u061f",
 "results.feedback.both": "\u0643\u0644\u0627\u0647\u0645\u0627",
 "results.feedback.correctionPlaceholder": "\u0627\u0633\u0645 \u0627\u0644\u0645\u0646\u062a\u062c \u0627\u0644\u0635\u062d\u064a\u062d (\u0627\u062e\u062a\u064a\u0627\u0631\u064a)",
 "results.feedback.send": "\u0625\u0631\u0633\u0627\u0644",
 "results.feedback.skip": "\u062a\u062e\u0637\u064a",
 "results.feedback.thanks": "\u0634\u0643\u0631\u0627\u060c \u0647\u0630\u0627 \u064a\u0633\u0627\u0639\u062f\u0646\u0627 \u0639\u0644\u0649 \u0627\u0644\u062f\u0642\u0629.",
 "results.feedback.q2": "\u0623\u064a\u0647\u0645\u0627 \u062a\u062e\u062a\u0627\u0631 \u0623\u0646\u062a\u061f",
 "results.feedback.neither": "\u0644\u0627 \u0647\u0630\u0627 \u0648\u0644\u0627 \u0630\u0627\u0643"
}
```

Notes for the native read: q1 uses the first-person plural past tense of the compare verb (attached
suffix, so not the standalone verb the fences ban); unsure is the gender-neutral "not sure" form;
skip is the verbal-noun form common in Gulf app UI; thanks avoids the tanween of the base value;
neither is "not this and not that". EN checks: no banned_en, no scary_vocab_en ("try again" etc.), no
date, no promise of a reply, a fix or a reward.

### 2.7 Failure table

| Condition | Behaviour |
|---|---|
| `ENABLE_FEEDBACK_V2` OFF (prod today) | Every card row 422s (missing useful); swallowed; the UI shows thanks. The answers are LOST. Hence the shipping precondition (R-CL3-14) and L-CL3-2. ContactUs: 200, `source` dropped. |
| ON, network failure / 5xx / 429 | Swallowed; thanks / details unaffected; no retry, no queue (no storage of the correction). |
| ON, a malformed id | Cannot occur: ids are filtered by `isCompareRequestId` / non-empty before the body is built (a bad id would 422 the whole row and lose the answer). |
| Correction with control chars / newlines / > 80 | Removed / capped client-side before the send; never a 422 from the card. |
| Blank correction and no side | Send disabled; no POST. |
| Product name missing | That side choice omitted; Both and the text field remain. |
| History reopen / partial | No card (wrapper stays, empty). |
| ForgotPassword 429 RATE_LIMITED | `common.errors.rateLimited`. Other errors: base text. |

### 2.8 Identity invariants (the main invariant of a client unit)

- No backend app/ file changes: the backend contract is the SF1 one, frozen (PLAN_S80 section 0: no
  key removed, renamed or retyped; refusals keep their envelopes; nothing here produces a 503).
- With `ENABLE_FEEDBACK_PREFERENCE_Q2 = false`, nothing of Q2 renders (no `results.feedback.q2` /
  `.neither` text, no `feedback-q2*` testID) and no POST body carries `preference` (RED R15 + static
  R15s).
- No new event type, no trackEvent from the card (events fence); no new route param; no native or
  app.json change; no package.json change.
- `submitFeedback`'s body and request config unchanged (B18 stays green).
- Test seams: `FEEDBACK_DWELL_MS` [8000], `CORRECTION_MAX` [80], `ENABLE_FEEDBACK_PREFERENCE_Q2`
  [false] (jest.mock for the ON rows), the `submitFeedback` mock, fake timers for the dwell, `fireEvent
  (node, 'layout' | 'scroll', nativeEvent)` for the reveal.

---------------------------------------------------------------------------------------------------

## 3. Change list (the order GREEN applies it)

0. Byte copies (Python shutil.copyfile) of every edited file under the GREEN notes folder; sha256
   recorded; the RED files frozen by sha.
1. NEW `SmartCompareApp/src/services/feedbackAnswers.ts` (2.1).
2. `src/config/features.ts`: the one export (2.1).
3. `src/services/api.ts`: the `submitFeedback` type widening (2.1; body unchanged).
4. `src/types/types.ts`: `ComparisonResult.compareRequestId?` (2.1).
5. `src/components/FeedbackCard.tsx`: rewritten (2.2); header comment rewritten (no "Was this helpful?").
6. `src/components/results/ResultsContent.tsx`: the reveal (2.4), the new optional prop
   `feedbackCompareRequestId`, the header comment item 8 reworded ("Feedback prompt -- the CL3 identity
   question").
7. `src/screens/ResultsScreen.tsx`: the camera id state, `feedbackCompareRequestId`, the prop (2.3).
8. `src/screens/HomeScreen.tsx`: the destructure + two `attachCompareRequestId` lines (2.3).
9. `src/screens/ForgotPasswordScreen.tsx`: the RATE_LIMITED mapping (2.5).
10. `src/screens/ContactUsScreen.tsx`: `source: 'contact'` (2.5).
11. `src/i18n/en.json`, `src/i18n/ar.json`: 6 removed, 1 changed, 11 added (2.6); CRLF kept; JSON
    re-validated with json.loads; key parity checked.
12. E-rows (4.1): E1 delete `__tests__/components/FeedbackCard.designChips.test.tsx`; E2
    `__tests__/s11/copy.s11.test.tsx`; E3 `__tests__/s11e/arCopy.s11e.test.ts`; E4
    `__tests__/cl2/scope.cl2.test.ts`; E5 `tests/test_feedback_allowlist_superset.py` (subject to Q-1).
13. `CLAUDE.md`: the CL3 client block after the S81-G10 block (before `## Tests`, :637) with one blank
    line before its heading, and the :341 pointer sentence after the S81-G10 one (8).
14. The RED files under `SmartCompareApp/__tests__/cl3/` (5) are NOT edited by GREEN.

No other file.

---------------------------------------------------------------------------------------------------

## 4. Existing pins

### 4.1 Pins that change deliberately

| E | File:line (base) | Change | Reason |
|---|---|---|---|
| E1 | SmartCompareApp/__tests__/components/FeedbackCard.designChips.test.tsx (72 lines, 4 its) | DELETED | It pins the removed title, chips, `useful: true` + `mattered_most` (R-CL3-9); every behaviour it covered that survives (thanks on `submitted`, fire-and-forget) is re-pinned by the cl3 card rows R2 / R13 / R19. |
| E2 | __tests__/s11/copy.s11.test.tsx:186-191 (and the header :10) | the count expression gains a named CL3 delta (`- CL3_REMOVED.length + CL3_ADDED.length`, 6 and 11) -> 1,016; the title "1,016 leaves" | R-CL3-9 / 2.6. Parity assertions unchanged. |
| E3 | __tests__/s11e/arCopy.s11e.test.ts:132 / :140 | `{ ar: 1011, en: 1011 }` -> `{ ar: 1016, en: 1016 }`; title text | same |
| E4 | __tests__/cl2/scope.cl2.test.ts:18-26 (P14 :40-47) | `FEATURES_EXPORTS_AT_BASE` gains `'ENABLE_FEEDBACK_PREFERENCE_Q2'` (comment: CL3 R-CL3-8); the SSE-default assertion unchanged | R-CL3-8 requires a features.ts constant. |
| E5 | tests/test_feedback_allowlist_superset.py (backend TEST file; reads FeedbackCard.tsx by path) | Re-aim: `test_chip_keys_are_the_values_sent_as_mattered_most` -> `test_feedback_card_sends_no_mattered_most` (the card source and src/services/feedbackAnswers.ts contain no `mattered_most`); `test_some_chip_keys_discovered` + `test_valid_mattered_most_is_superset_of_feedback_chips` -> scoped to "any chip literal that remains" (vacuity guard replaced by the positive control that FeedbackCard.tsx exists and contains `submitFeedback`); `test_shipped_chip_keys_are_allowlisted` (the build-3 chips: builds in the field still send them), `test_existing_seven_values_are_not_removed` and the three route rows UNCHANGED. | The send site `mattered_most: [chipKey]` is removed by R-CL3-4/9; without E5 two rows go red and the superset row would read the new option literals as chips. This is a tests/ file, not app/: Q-1 asks whether R-CL3-1 "any backend file" admits it. |

### 4.2 Pins that must stay green and UNEDITED (measured or read)

Backend (green at base, 1.10): the 25 chunk-A files (incl. test_s81_sf1_surfaces_be.py P10 / P11 /
P12 / R13 / R14 / R15 / R15b / R15c / R16, test_s81_sf1_gate_rows.py, test_events_allowlist_superset.py,
test_security_regression.py, test_comparison_id_echo.py, test_b2_strict_optional_auth.py,
test_ci_gates.py, test_dimension_label_catalog_parity_w414.py, the legal readers) and the 5 chunk-B
CLAUDE.md readers. Client (by reading; NOT MEASURED until the junction): ResultsEntryParams.a18
(all rows), HomeScreen.minDisplayFloor (:114-160), cl2/homeFloor + cl2/gateRows (navigate args via
`objectContaining`), HomeScreen.cancelCompare.a4, HomeScreen.eS3hf.loaderVisibility,
ResultsContent.render (:205 wrapper present), ResultsContent.rewriteOrder (:222-245, :280-290),
ResultsScreen.bundleE.s3 (:118, :133), Results.memo.m21, s81_08/requestHeaders B18 (:622-636),
s81_08/sseHeaders D3 (:212-229), s81_08/cameraHeaders, ContactUsScreen.test (:105-133),
Screens.bundleD.contract ForgotPassword (:261-279), auth/authErrorCopy.s69, b3a/honestCopy
(r26-r31b over ITS keys), copy-policy.test, i18n/no-missing-referenced-keys, i18n/no-deleted-keys,
consent/aiConsentV2.s75 (:194 parity), rtl/textAlignLogical.contract, config/features.test, the 12
FeedbackCard-mocking suites of 1.5.

---------------------------------------------------------------------------------------------------

## 5. RED tests

Client RED files (jest, `SmartCompareApp/__tests__/cl3/*.cl3.test.ts(x)`), hermetic (api, authService,
expo-crypto, Sentry mocked with plain `jest.mock` of installed packages / local modules; never
`{ virtual: true }` for an installed package), CRLF-normalised source reads, fake timers for the dwell.
Every RED row fails at base on an AssertionError ONLY: missing symbols are read through `require`
inside the test with a guarded getter (e.g. `const mod = safeRequire('../../src/services/
feedbackAnswers')` returning `{}` on MODULE_NOT_FOUND and the row asserting `typeof mod.x ===
'function'` first). PIN rows are green at base and run WITH the full configuration (the real features
module, a recording submitFeedback mock, a recording trackEvents / console / Sentry spy) so a "not
gated" mutant is killable (B1 rule). No backend RED file (no backend behaviour changes); the backend
contract is held by the SF1 pins of 4.2.

Fixture: `__tests__/cl3/fixtures/cl3_copy.json` (ASCII JSON: the 12 EN values and the 12 AR values of
2.6 as escapes, the 6 removed keys). Product names: `'Alpha Eau de Parfum 100ml'`,
`'Beta Parfum 50ml'`, and a 120-character synthetic name built at run time for the long-name rows.
Tester scenario: the session-80 runs/research/eval_regression.json covers backend compare outcomes,
not this card; no row draws on it (stated).

### 5.1 `card.cl3.test.tsx` (FeedbackCard; submitFeedback mocked; `ID = <uuid4 built at run time>`)

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| R1 | Q1 renders | `feedback-q1`, `feedback-q1-yes/no/unsure` exist; text keys q1 / yes / no / unsure; `queryByText('results.feedback.title')` and `feedback-chip-*` null | RED (no testIDs) | 2.2 |
| R2 | Yes posts one exact row | one call; arg `toEqual({identity_correct: 'correct', comparison_id: CID, compare_request_id: ID})` (exact key set: no useful / mattered_most / source); `feedback-thanks` shown; onSubmitted 1x | RED | 2.2 |
| R3 | Not sure | `{identity_correct: 'unsure', ...}`; thanks; onSubmitted 1x | RED | 2.2 |
| R4 | No records at the tap | after ONLY the No press: 1 call `{identity_correct: 'wrong', ...ids}`; `feedback-details` shown; side labels are the two names in order; onSubmitted 0x | RED | 2.2 |
| R5 | Send gating | on details, `feedback-send` accessibilityState.disabled true; press -> still 1 call; after a whitespace-only text still disabled | RED | 2.2 |
| R6 | Send with side second + padded text | call 2 `toEqual({identity_correct: 'wrong', wrong_side: 'second', correction: 'Gamma Extrait', ...ids})`; thanks; onSubmitted 1x | RED | 2.2 |
| R6b | side first and Both map to 'first' / 'both' (two renders) | exact bodies | RED | 2.2 |
| R7 | text only | `{identity_correct: 'wrong', correction, ...ids}`, no `wrong_side` key | RED | 2.2 |
| R8 | Skip posts nothing | total calls 1; thanks; onSubmitted 1x | RED | 2.2 |
| R9 | unmount on details | total calls 1 after unmount + `jest.runOnlyPendingTimers()` | RED | 2.2 |
| R10 | sanitisation | text = 'A' + fromCharCode(10) + 'B' + fromCharCode(9) + 'C' + fromCharCode(0) + fromCharCode(127) + fromCharCode(0x2028) + ' D ' -> sent `correction === 'ABC D'` (no code point < 32, 127, 0x80-0x9F, 0x2028/9) | RED | 2.1 sanitizeCorrection |
| R11 | length | input `maxLength === 80`; a 120-char changeText -> sent correction length <= 80; `CORRECTION_MAX === 80` | RED | 2.1 / 2.2 |
| R12 | double-tap | two synchronous presses of Yes -> 1 call; of No -> 1 call; of Send -> 1 details call | RED | 2.2 latch |
| R13 | failure is silent | submitFeedback rejects: Yes -> thanks, no text from common.error*, no throw; No -> details still shown | RED | 2.2 |
| R14 | ids omitted / never minted | no ids -> body keys exactly ['identity_correct']; compareRequestId 'not-a-uuid' or upper-case -> no `compare_request_id`; `newCompareRequestId` spy (jest.spyOn on the requestContext module) 0 calls through every flow | RED | 2.1 feedbackIds |
| R15 | Q2 OFF (real features module) | after Yes: no `feedback-q2*`, no text q2 / neither; no call carries `preference`; thanks at once | RED (no Yes testID at base) | 2.1 / 2.2 |
| R15s | Q2 constant static | features.ts source matches `/^export const ENABLE_FEEDBACK_PREFERENCE_Q2 = false;$/m` | RED | 2.1 |
| R16 | Q2 ON (`jest.mock` features with the constant true) | Yes -> 1 call then `feedback-q2` with the two names + neither + unsure; `feedback-q2-first` -> call 2 `toEqual({preference: 'first', ...ids})`; after No or Not sure no `feedback-q2` | RED | 2.2 |
| R17 | a11y | every `feedback-q1-*`, `feedback-send`, `feedback-skip` role button + non-empty label; side choices role radio with `accessibilityState.selected` toggling; flattened style `minHeight >= 44` on every pressable; input accessibilityLabel = the placeholder key | RED | 2.2 |
| R18 | long name / RTL | a 120-char name renders with `numberOfLines === 1` and `ellipsizeMode === 'tail'`, label text = the full name (truncation is layout); with `I18nManager.isRTL = true` (mock) the side order in the tree is still first, second, both (logical order; RN mirrors visually) | RED | 2.2 |
| R18b | blank name | productNames ['', 'Beta'] -> no `feedback-side-first`; `feedback-side-second` + both present | RED | 2.2 |
| R19 | parent submitted | `submitted` true -> `feedback-thanks` only, no q1 | PIN-like but RED (testID new) | 2.2 |

### 5.2 `reveal.cl3.test.tsx` (ResultsContent; FeedbackCard mocked to a recorder rendering testID `cl3-card` and capturing props)

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| V1 | not at mount | live origin: `results-content-feedback` present, `cl3-card` absent | RED (card at mount) | 2.4 |
| V2 | dwell | `act(() => jest.advanceTimersByTime(7999))` absent; `+1` present | RED | 2.4 |
| V3 | verdict scroll | layout of `results-content-why` {y: 400, height: 200}; scroll {offset 0, viewport 500} absent; {offset 150, viewport 500} present before 8 s | RED | 2.4 |
| V4 | stays | after reveal, scroll to 0 and advance 20 s -> still present | RED | 2.4 |
| V5 | History reopen | `resultOrigin='stored'`: absent after 20 s and after a scroll past the verdict | RED | 2.4 |
| V6 | partial | `metadata.partial: true`: absent after 20 s and after scroll (subject to Q-2) | RED | 2.4 |
| V6b | degraded stays eligible | a degraded body: present at 8 s | RED (absent... base renders at mount, so the 7999 ms absence half fails) | 2.4 |
| V7 | props | the recorder got `comparisonId`, `compareRequestId`, `productNames` [products[0].name, products[1].name], `submitted`, `onSubmitted` | RED | 2.4 |
| V8 | timer cleanup | unmount before 8 s -> `jest.getTimerCount() === 0` and no act warning | RED (no timer at base: the count row passes vacuously, so the row first asserts the reveal timer EXISTS before unmount) | 2.4 |
| V9 | no reveal animation | the card's nearest Animated ancestor is the wrapper (no second `entering` builder call: the reanimated mock's `FadeIn.duration` / `FadeInDown.delay` call counts unchanged by the reveal) | RED via V1 precondition | 2.4 |
| V10 | order pin | the wrapper is still the LAST anchor (rewriteOrder pins re-run in this file with the real card revealed) | PIN (green at base) | base + 2.4 |

### 5.3 `ids.cl3.test.tsx` (Home + Results plumbing; the cl2/homeFloor harness pattern)

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| I1 | text stream | streamComparison mock returns `compareRequestId: ID`; onComplete success -> navigate('Results', objectContaining({ result: objectContaining({ compareRequestId: ID }) })) | RED | 2.3 |
| I2 | link | expo-crypto mock mints ID; api.post success -> the navigated result carries `compareRequestId === ID` and the post config header `X-Compare-Request-Id === ID` | RED | 2.3 |
| I3 | none minted | compareRequestId null -> the navigated result has no `compareRequestId` key | PIN (green at base) | 2.3 |
| I4 | camera nested | identifyFromImages mock resolves `{action: 'comparison', result: {...}, compareRequestId: ID}` -> ResultsContent (mocked recorder) receives `feedbackCompareRequestId === ID` | RED | 2.3 |
| I5 | text result param | route.params.result carries `compareRequestId: ID` -> prop ID | RED | 2.3 |
| I6 | History | route.params.comparison_id -> prop undefined | RED (prop absent at base: asserts the prop KEY is passed as undefined via `'feedbackCompareRequestId' in props`) | 2.3 |
| I7 | route contract | the navigate payload keys stay within ResultsEntryParams' declared set (re-uses the a18 parser on HomeScreen source) | PIN | 2.3 |

### 5.4 `copyPrivacy.cl3.test.ts` (catalogs, fences, privacy)

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| C1 | new keys | the 11 added keys exist in both catalogs with the fixture EN / AR values | RED | 2.6 |
| C2 | removed keys | the 6 keys absent from both catalogs; no src file contains `results.feedback.(title|accurate|detailed|fast|placeholder|submit)` | RED | 2.6 |
| C3 | thanks | EN and AR equal the fixture; AR has no U+064B..U+0652 / U+0670 | RED | 2.6 |
| C4 | counts | key sets equal, 1,016 each | RED | 2.6 |
| C5 | fences on the 12 values | banned_en / banned_ar / scary_vocab_en / scary_vocab_ar; no diacritic; no ASCII or Arabic-Indic digit; no bidi control (U+200E/F, U+202A..U+202E, U+2066..U+2069); no standalone VERB_AR; no brand word / MYEZ; EN no /reply|respond|fix|reward|credit|free|guarantee/i | RED (precondition: keys exist) | 2.6 |
| P1 | static privacy | FeedbackCard.tsx and feedbackAnswers.ts (comment-stripped) contain `submitFeedback` (card) and NONE of: trackEvent, trackEvents, console., Sentry, addBreadcrumb, AsyncStorage, SecureStore, swrCache, navigate( | RED (feedbackAnswers.ts missing; the card half is green at base) | 2.1 / 2.2 |
| P2 | behavioural privacy | a sentinel correction built at run time ('cl3-' + Date.now() + '-name'): after Send, the sentinel appears ONLY in the submitFeedback arg; console.log/warn/error/info spies, the Sentry mock (captureMessage, captureException, addBreadcrumb), trackEvents / trackEvent mocks, AsyncStorage.setItem and navigation.navigate never receive a string containing it | RED (no input at base) | 2.2 |
| P3 | wire carrier | api.ts `submitFeedback` source still `api.post('/api/v1/feedback', data)` with no third argument; its parameter type has no `source` member and `useful?` optional | RED (useful required at base) | 2.1 |

### 5.5 `riders.cl3.test.tsx` (S81-24e + ContactUs)

| # | Test | Assertion | At base | Satisfied by |
|---|---|---|---|---|
| F1 | slowapi 429 | requestPasswordReset (mocked) rejects with `{response: {status: 429, headers: {'retry-after': '60'}, data: {success: false, error: 'Rate limit exceeded. Please try again later.', code: 'RATE_LIMITED', request_id: 'r', retry_after_seconds: 60}}}` -> rendered text `common.errors.rateLimited`; the raw text absent; no '60' rendered | RED | 2.5 |
| F2 | throttle 429 | the same with retry_after_seconds 86400 | RED | 2.5 |
| F3 | other errors unchanged | a 400 `{error: 'Bad email', code: 'VALIDATION_ERROR'}` -> 'Bad email'; `new Error('Some detail')` -> 'Some detail'; a 503 codeless -> '' (TIMEOUT message) exactly as base | PIN | base |
| F4 | same answer | success for any email -> `auth.resetSent` screen; empty email -> `auth.emailRequired` | PIN | base |
| F5 | the wrapper passes the code | the REAL authService.requestPasswordReset with the api mocked to reject with the F1 error -> the caught error's `response.data.code === 'RATE_LIMITED'` (no `detail` key in the envelope) | PIN | base |
| K1 | contact source | a Suggestion submit -> body `toEqual({useful: true, mattered_most: [], change_suggestion: expect.stringMatching(/^\[Suggestion\] /), source: 'contact'})`; a Bug submit -> `useful: false`, `source: 'contact'` | RED | 2.5 |

Counts: RED 54 (R1-R19 incl. R6b / R15s / R18b = 22; V1-V9 incl. V6b = 10; I1, I2, I4, I5, I6 = 5;
C1-C5 + P1-P3 = 8; F1, F2, K1 = 3; plus the per-locale / per-answer parametrised halves counted once
each: 6 more for R2/R3 x locale-free, V3 / V6 split rows; the RED round states the final node count).
PIN 7 (V10, I3, I7, F3, F4, F5, and R19's thanks half). The RED round records every node with its
base failure line (AssertionError only).

---------------------------------------------------------------------------------------------------

## 6. Mutation table (each on a byte copy, an exact-string edit matching once, the killing rows by
path with `-t`, restore, sha256 compare; jest through the junction at RED / GREEN)

| M | Mutant (on the GREEN bytes) | Killed by |
|---|---|---|
| M1 | card Yes body adds `useful: true` | R2 |
| M2 | card adds `mattered_most: []` | R2, R6 |
| M3 | No posts nothing at the tap (POST moved to Send) | R4, R8 |
| M4 | details body drops `identity_correct` | R6, R7 |
| M5 | Send enabled with nothing chosen | R5 |
| M6 | Skip posts `{identity_correct: 'wrong'}` | R8 |
| M7 | sanitizeCorrection keeps U+000A | R10 |
| M8 | `maxLength={100}` / `CORRECTION_MAX = 100` | R11 |
| M9 | latch removed (state guard only) | R12 |
| M10 | `await submitFeedback` before the transition with no catch | R13 |
| M11 | feedbackIds mints `newCompareRequestId()` when absent | R14 |
| M12 | `ENABLE_FEEDBACK_PREFERENCE_Q2 = true` | R15, R15s |
| M13 | Q2 shown after No | R16 |
| M14 | Q2 body adds `identity_correct: 'correct'` | R16 |
| M15 | side labels reversed (names [1], [0]) | R4, R18 |
| M16 | wrong_side first <-> second swapped | R6, R6b |
| M17 | `FEEDBACK_DWELL_MS = 0` | V1, V2 |
| M18 | `FEEDBACK_DWELL_MS = 9000` | V2 |
| M19 | scroll test against the verdict TOP (y) | V3 |
| M20 | scroll handler sets revealed false below the verdict | V4 |
| M21 | `resultOrigin !== 'stored'` dropped | V5 |
| M22 | `!isPartial` dropped | V6 |
| M23 | `!isDegraded` added | V6b |
| M24 | timer not cleared on unmount | V8 |
| M25 | the revealed card wrapped in `Animated.View entering={FadeIn.duration(200)}` | V9 |
| M26 | Home stream path: attach line removed | I1 |
| M27 | URL path: attach line removed | I2 |
| M28 | camera id taken from `data.result.compareRequestId` | I4 |
| M29 | History reopen passes the result id | I6 |
| M30 | `if (__DEV__) console.log('[feedback]', body)` in the card | P1, P2 |
| M31 | `trackEvent('feedback_details', {correction})` | P1, P2 |
| M32 | submitFeedback type gains `source?` and the card sends `source: 'result'` | R2, P3 |
| M33 | ForgotPassword mapping reverted | F1, F2 |
| M34 | ForgotPassword maps EVERY error to rateLimited | F3 |
| M35 | ContactUs `source` removed | K1 |
| M36 | old key `results.feedback.title` kept | C2, C4 |
| M37 | AR thanks with a tanween | C3, C5 |
| M38 | en.json q1 = "Did we pick the best products?" (banned / changed) | C1, C5 |

38 mutants; equivalent survivors are reported for a ruling. Each restore is sha-checked against the
GREEN snapshot; a `.qa-mutation.lock` guards the worktree.

---------------------------------------------------------------------------------------------------

## 7. Comm set and gates (cheapest first)

Union rule (s81-common.txt): module / symbol reference grep UNION the source-scanning pins UNION the
CLAUDE.md readers UNION the SmartCompareApp-scanning backend tests (client-visible: yes).

- Client jest set: `grep -rlE "FeedbackCard|ResultsContent|ResultsScreen|HomeScreen|ContactUsScreen|
  ForgotPasswordScreen|config/features|submitFeedback|i18n/en\.json|i18n/ar\.json|i18n/\.copy-policy|
  types/types|streamComparison|identifyFromImages|requestContext|src/screens'|SRC_DIR|walk\("
  __tests__ src/services/__tests__` at base = 189 suites (jest_comm.txt), plus the 5 cl3 RED files.
- Backend set: chunk A (25) + chunk B (5) = 30 files, base record 2,505 passed / 0 failed at a74caba7
  (1.10). The 4 test_precommit_hook*.py files are excluded (no .githooks edit).
- Comm set of record: 189 + 30 = 219 files (+ the 5 RED files).

Gates, cheapest first:
1. Byte checks: every new file ASCII + LF (count bytes > 127 = 0 except en.json / ar.json values);
   every edited file keeps CRLF; `git diff --stat` shows no whole-file diff; en.json / ar.json
   `json.loads` OK and key parity 0, 1,016 each.
2. The gitleaks / hook keyword rule: no constant named with access / auth / api / credential / creds /
   key / password / secret / token holding a 64-hex value (none planned); no credential-shaped literal.
3. `node node_modules/typescript/bin/tsc --noEmit` rc 0 (from SmartCompareApp, through the junction).
4. `node node_modules/eslint/bin/eslint.js <the changed src + test files>` 0 errors.
5. Jest by path: the 5 cl3 RED files; E1-E4 files; the 4.2 client list; then the 189-suite set; the
   mutation rows.
6. Backend: chunk A + chunk B through pyt.py (bound 1200 each), base record above; `comm -13` of the
   sorted FAILED node-id sets EMPTY; E5's file must show only the re-aimed nodes as changed.
7. The FULL jest suite ONCE, in the last round before the PR (LC-7): baseline 4,030 passed + the four
   config/nativeBundle.w37 drift nodes + 13 skipped + 13 todo; expected after CL3 = base - 4 (E1's
   deleted its) + the cl3 nodes, the same 4 drift nodes.
8. CI is the arbiter (7 / 7 green).

---------------------------------------------------------------------------------------------------

## 8. CLAUDE.md row and owner steps

Block after the S81-G10 block (before `## Tests`), one blank line before its heading, ASCII:

**SESSION 81 client unit (CL3 TWO-QUESTION FEEDBACK CARD + S81-24e + the ContactUs source line,
2026-11-1x; NO runtime flag; ships only in the SECOND OTA, after the dated `ENABLE_FEEDBACK_V2` ON
line):**
- CL3: `SmartCompareApp/src/components/FeedbackCard.tsx` asks "Did we compare the right products?"
  (Yes / No / Not sure = `identity_correct` correct / wrong / unsure, one POST); a No is posted AT THE
  TAP, then optional details (`wrong_side` by the two product names in body order + Both, an optional
  80-char `correction`) as ONE more row on Send, nothing on Skip. The card never sends `useful`,
  `mattered_most` or `source`; ids: `comparison_id` when the result has one, `compare_request_id` =
  the compare's own X-Compare-Request-Id (attached to the result by Home and the camera path,
  `src/services/feedbackAnswers.ts`), never minted. Revealed after 8 s of dwell
  (`FEEDBACK_DWELL_MS`) or once the verdict section's bottom scrolls into view; never on a History
  reopen (`resultOrigin` stored) or a partial result; fire-and-forget. Q2 ("Which one would you
  pick?" = `preference`) sits behind the compile-time `ENABLE_FEEDBACK_PREFERENCE_Q2 = false`
  (features.ts): nothing of it renders. The correction text travels only in the POST body (no event,
  log, breadcrumb or storage). With `ENABLE_FEEDBACK_V2` OFF every card row 422s and is dropped
  silently: hence the OTA precondition. The learning job and the judge do not read the CL3 columns
  yet (D22b).
- S81-24e: ForgotPasswordScreen renders `common.errors.rateLimited` for the coded 429 RATE_LIMITED
  (slowapi 3/minute today; the S81-24 throttle once flipped); R-S24-25's client precondition for
  `ENABLE_AUTH_THROTTLE_V2` is MET once this OTA is live.
- ContactUs posts `source: 'contact'` (OFF: accepted and dropped; ON: stored).

The :341 clause gains, after the S81-G10 sentence: "CL3 TWO-QUESTION FEEDBACK CARD adds no runtime
flag (a client unit; the compile-time `ENABLE_FEEDBACK_PREFERENCE_Q2` stays false): the rows of the
**SESSION 81 client unit (CL3 ...)** block."

Owner steps (names only; a dated ledger line each):
1. Merge now (no runtime effect: client only).
2. `ENABLE_FEEDBACK_V2` ON on web (046 + 049 are applied, ledger 2026-11-07 12:05) with its dated
   ledger line BEFORE the second OTA (R-SF1-15 amended).
3. The App Store Connect App Privacy answers: confirm "Product Interaction" / "Other User Content"
   (the optional free-text product name in feedback, linked to the account when signed in, not used
   for tracking) BEFORE the second OTA; the privacy policy's feedback line covers a typed product name
   (the S81-12 v3 text: the orchestrator checks the wording in the legal window).
4. The [NATIVE READ] of the 12 AR values in 2.6 before the OTA.
5. Publish the SECOND OTA (the relay) from a main carrying CL3; then read Q1's answer rate (rows by
   `identity_correct` per day) before any Q2 OTA.
6. Rollback: if `ENABLE_FEEDBACK_V2` is unset after the OTA, the card's answers 422 and are dropped
   silently (L-CL3-2); revert by an OTA of the previous bundle if the loss matters.

---------------------------------------------------------------------------------------------------

## 9. Stated limits

- L-CL3-1: the readers do not read CL3's columns: `scripts/cron_learning.py` FEEDBACK_COLUMNS (:69)
  and the judge's `_user_wrong` (:611-623, winner_correct only) ignore `identity_correct` /
  `wrong_side` / `preference`; L13 is closed on the WRITER side only. D22b adds the reader with a
  case key of comparison_id, else compare_request_id, else the row id (a No with details writes two
  rows with the same ids: one case).
- L-CL3-2: if `ENABLE_FEEDBACK_V2` is rolled back after the OTA, every card row 422s (missing useful)
  and is dropped silently; the user still sees thanks.
- L-CL3-3: fresh compares carry no `comparison_id` while `ENABLE_COMPARISON_ID_ECHO` is OFF; rows are
  then joinable only through `compare_request_id` (search_logs / user_events / compare_runs, ON). A
  compare whose id could not be minted (expo-crypto failure) yields an id-less row.
- L-CL3-4: the dwell is wall-clock while ResultsContent is mounted (backgrounding the app counts).
- L-CL3-5: the 30/minute route limit is per client key; rows past it are dropped silently.
- L-CL3-6: Sentry's XHR breadcrumb for the POST carries method / url / status (scrubbed), not the
  body: read from the scrubber code, NOT MEASURED on the pinned SDK (no node_modules at the spec).
- L-CL3-7: the AR strings await the owner's native read; the base AR thanks value (with a tanween) is
  replaced, not kept.
- L-CL3-8: Q2 code ships dark in the bundle (constant false); its copy keys ship in both catalogs.
- L-CL3-9: a degraded result (write-up failed) keeps the card; a partial result loses it (Q-2).
- L-CL3-10: jest-side claims of this spec are by reading; the RED round measures them through the
  junction.

---------------------------------------------------------------------------------------------------

## 10. Out of scope

CL4; S81-11c / S81-11d; the `image_load_failed` emission; any backend app/ / scripts/ / migrations/
file (the D22b readers, a reader-side dedupe, the judge join); any native or app.json change; any new
event type; any new dependency or package.json edit; any remote flag; `ENABLE_COMPARISON_ID_ECHO`;
the ContactUs copy; the History screen; Sentry configuration.

---------------------------------------------------------------------------------------------------

## 11. Open questions for the orchestrator

- Q-1 (E5, R-CL3-1): tests/test_feedback_allowlist_superset.py is a BACKEND TEST file that reads
  FeedbackCard.tsx by path; two of its rows pin the removed send site and go red. Recommended: rule it
  in as E5 (tests/ only, no app/ change; the build-3 chip pins and the route rows stay). The
  alternative (leave it red) is not available.
- Q-2 (R-CL3-6, partial): the brief says "the spec states the existing mount condition and keeps it"
  AND "a partial has no card"; at base the card DOES mount on a partial (and on a degraded) result
  (ResultsContent.tsx:218, :669-681). This spec follows the explicit list: partial excluded, degraded
  kept. Confirm, or rule "keep the base condition" (then V6 / M22 drop and V6b changes).
- Q-3 (R-CL3-5, carrier): the id rides on the result object (`compareRequestId`, client-only, the
  S81-08 identify precedent) instead of a new Results route param; a route param would re-pin
  ResultsEntryParams.a18 and HomeScreen.minDisplayFloor (two E-rows). Confirm the result-object form.
- Q-4 (R-CL3-8): the Q2 row carries `preference` only (not `identity_correct: 'correct'` again), so a
  future reader never double counts a Yes; the details row of a No DOES repeat `identity_correct:
  'wrong'` per R-CL3-3. Confirm the asymmetry.
- Q-5 (S81-24e scope): the raw-English 429 text is ALSO rendered today by the slowapi 3/minute limit,
  independent of the throttle flag; the mapping fixes both. No other auth screen is in scope (Login /
  Register map by their own keys per authErrorCopy.s69). Confirm no other screen joins.
- Q-6 (owner step 3): the exact App Privacy category for the optional product-name text is the
  owner's / the legal window's call; the spec names the candidates only.

---------------------------------------------------------------------------------------------------

Not done in this spec: no jest run (no junction); no prototype of the change list; no mutant run; the
RED file node count is estimated, not measured; the client fences by path were read, not run.

## Appendix A: the client jest comm set at a74caba7 (189 suites, jest_comm.txt)

- __tests__/App.navigation.test.tsx
- __tests__/App.resetPasswordRoute.w36.test.ts
- __tests__/App.routing.test.tsx
- __tests__/App.sessionInvalid.m18.test.ts
- __tests__/AuthScreens.socialDiagnostic.pa8.test.tsx
- __tests__/AuthScreens.socialTimeout.a8.test.tsx
- __tests__/AuthScreens.test.tsx
- __tests__/CameraHelpOverlay.test.tsx
- __tests__/ConsentRow.copy.w3-16.test.tsx
- __tests__/ContactUsScreen.test.tsx
- __tests__/EditProfileScreen.appleRelay.test.tsx
- __tests__/EditProfileScreen.bundleE.s3.test.tsx
- __tests__/EditProfileScreen.deleteCopy.w314.test.tsx
- __tests__/HistoryScreen.productNames.test.tsx
- __tests__/HistoryScreen.timeAgo.w311.test.tsx
- __tests__/HomeScreen.abortOnUnmount.test.tsx
- __tests__/HomeScreen.arabicAlerts.w311.test.tsx
- __tests__/HomeScreen.bootDefer.b5.test.tsx
- __tests__/HomeScreen.bundleB.contract.test.tsx
- __tests__/HomeScreen.bundleE.contract.test.tsx
- __tests__/HomeScreen.bundleE.s3.integration.test.tsx
- __tests__/HomeScreen.bundleE.s3.test.tsx
- __tests__/HomeScreen.cancelCompare.a4.test.tsx
- __tests__/HomeScreen.catfix.d1.test.tsx
- __tests__/HomeScreen.currentDesign.contract.test.ts
- __tests__/HomeScreen.eS3hf.dedupe.test.tsx
- __tests__/HomeScreen.eS3hf.gateB.test.tsx
- __tests__/HomeScreen.eS3hf.loaderVisibility.test.tsx
- __tests__/HomeScreen.engineUnavailable.s69.test.tsx
- __tests__/HomeScreen.errorCopy.a11.test.tsx
- __tests__/HomeScreen.minDisplayFloor.test.ts
- __tests__/HomeScreen.modeChipAnim.test.tsx
- __tests__/HomeScreen.rateLimitedSeconds.w314.test.tsx
- __tests__/HomeScreen.redesign.test.tsx
- __tests__/HomeScreen.scanCamera.test.tsx
- __tests__/HomeScreen.test.ts
- __tests__/HomeScreen.trending.s69.test.tsx
- __tests__/InviteeQuizScreen.degraded.s69.test.tsx
- __tests__/InviteeQuizScreen.redesign.test.tsx
- __tests__/LoadingScreenVariants.a2Pacing.test.tsx
- __tests__/LoadingScreenVariants.wave2.test.tsx
- __tests__/ProductImage.resizeMode.test.tsx
- __tests__/ProductImage.test.tsx
- __tests__/ProfileEditorialSections.timeAgo.w311.test.tsx
- __tests__/ProfileScreen.bundleE.s3.integration.test.tsx
- __tests__/ProfileScreen.logoutCopy.b6.test.tsx
- __tests__/ProfileScreen.toggles.w314.test.tsx
- __tests__/Results.memo.m21.test.tsx
- __tests__/ResultsContent.confidenceSheet.test.tsx
- __tests__/ResultsContent.imageUrl.test.tsx
- __tests__/ResultsContent.partialNote.test.tsx
- __tests__/ResultsContent.perCategory.test.tsx
- __tests__/ResultsContent.scoreGuard.test.tsx
- __tests__/ResultsContent.specsComparisonShape.test.tsx
- __tests__/ResultsContent.v2Wiring.test.tsx
- __tests__/ResultsEntryParams.a18.test.ts
- __tests__/ResultsScreen.bundleE.s3.test.tsx
- __tests__/ResultsScreen.comparisonId.m18.test.ts
- __tests__/ResultsScreen.demographicsCopy.w314.test.ts
- __tests__/ResultsScreen.guards.test.tsx
- __tests__/ResultsScreen.historyDetailFetch.test.ts
- __tests__/ResultsScreen.historyFloor.a17.test.tsx
- __tests__/ResultsScreen.networkMatrix.m18.test.ts
- __tests__/ResultsScreen.pushPrePrompt.u6.test.tsx
- __tests__/ResultsScreen.redesign.test.tsx
- __tests__/ResultsScreen.timeout.test.tsx
- __tests__/ResultsScreen.usageFetch.a15.test.tsx
- __tests__/ScanCameraScreen.captureFailure.b9.test.tsx
- __tests__/Screens.bundleD.contract.test.ts
- __tests__/ShareBottomSheet.deviceFingerprint.w3-3.test.tsx
- __tests__/ShareBottomSheet.redesign.test.tsx
- __tests__/SmartPickCard.imageUrl.test.tsx
- __tests__/api.cameraAuthRetry.u13c.test.ts
- __tests__/api.expiredTokenRetry.b2.test.ts
- __tests__/api.getComparison.comparisonId.m18.test.ts
- __tests__/api.networkMatrix.m18.test.ts
- __tests__/api.networkMatrix.w314.test.ts
- __tests__/api.outputLang.w414.test.ts
- __tests__/api.settle.test.ts
- __tests__/api.settleTerminalLatch.a7.test.ts
- __tests__/api.streamComparison.expoFetch.test.ts
- __tests__/api.streamComparison.noBodyFallback.test.ts
- __tests__/api.terminalRouting.w311.test.ts
- __tests__/auth/authErrorCopy.s69.test.ts
- __tests__/b3a/authNoScreenCapture.b3a.test.tsx
- __tests__/b3a/cameraDenied.b3a.test.tsx
- __tests__/b3a/googleButton.b3a.test.tsx
- __tests__/b3a/honestCopy.b3a.test.tsx
- __tests__/brand.hardcoded.s69.test.ts
- __tests__/brand/inAppMark.u4c.test.ts
- __tests__/brand/revealGlyph.u4d.test.tsx
- __tests__/cl2/gateRows.cl2.test.tsx
- __tests__/cl2/homeFloor.cl2.test.tsx
- __tests__/cl2/imagePrefetch.cl2.test.ts
- __tests__/cl2/lazyScreens.cl2.test.tsx
- __tests__/cl2/metroSentry.cl2.test.ts
- __tests__/cl2/revealCut.cl2.test.tsx
- __tests__/cl2/scope.cl2.test.ts
- __tests__/cl2/sessionClear.cl2.test.ts
- __tests__/clientTruth/copyTruth.s74.test.ts
- __tests__/clientTruth/deviceData.s74.test.tsx
- __tests__/clientTruth/medicalNote.s74.test.tsx
- __tests__/clientTruth/shareTruth.s74.test.tsx
- __tests__/components/DimensionBars.arabicLabels.w414.test.tsx
- __tests__/components/FeedbackCard.designChips.test.tsx
- __tests__/components/ProgressBar.test.tsx
- __tests__/components/QarenLogo.test.tsx
- __tests__/components/ResultsAccordion.digitPolicy.w311.test.tsx
- __tests__/components/ResultsAccordion.hotfixSpecs.test.tsx
- __tests__/components/ResultsAccordion.render.test.tsx
- __tests__/components/ResultsAccordion.v2.test.tsx
- __tests__/components/ResultsContent.a11y.w311.test.tsx
- __tests__/components/ResultsContent.render.test.tsx
- __tests__/components/ResultsContent.rewriteOrder.test.tsx
- __tests__/components/ResultsContent.runnerUp.test.tsx
- __tests__/components/RunnerUpWinsCard.arabicLabels.w414.test.tsx
- __tests__/components/hero/RevealBurst.test.tsx
- __tests__/config/domain.s76.test.ts
- __tests__/config/features.test.ts
- __tests__/config/nativeBundle.w37.test.ts
- __tests__/consent/aiConsentSheetScroll.s75.test.tsx
- __tests__/consent/aiConsentV2.s75.test.ts
- __tests__/consent/aiConsentVersion.s69.test.ts
- __tests__/consent/aiDispatchFence.s69.test.ts
- __tests__/consent/aiProcessingConsent.s69.test.tsx
- __tests__/copy-policy.test.ts
- __tests__/demographics.i18n.test.ts
- __tests__/errorCopy.a11.test.ts
- __tests__/errorCopy.engineUnavailable.s69.test.ts
- __tests__/errorCopy.w314.test.ts
- __tests__/helpers/lucideFence.test.ts
- __tests__/helpers/lucideFence.ts
- __tests__/hero/LoadingRings.animation.test.tsx
- __tests__/hero/RevealBurst.test.tsx
- __tests__/honestCounts.s69.test.tsx
- __tests__/honestLoaders.u6.test.tsx
- __tests__/i18n.bundle_c.test.ts
- __tests__/i18n.test.ts
- __tests__/i18n/brand.myez.s69.test.ts
- __tests__/i18n/digitPolicy.w311.test.ts
- __tests__/i18n/dimensionLabels.w414.test.ts
- __tests__/i18n/fashionLabels.test.ts
- __tests__/i18n/no-deleted-keys.test.ts
- __tests__/i18n/no-missing-referenced-keys.test.ts
- __tests__/i18n/pluralFamilies.fence.w311.test.ts
- __tests__/i18n/plurals.test.ts
- __tests__/i18n/priceDigits.crossScreen.w414.test.ts
- __tests__/i18n/referralExpiryPlurals.w414.test.ts
- __tests__/icons/ModeIcons.test.tsx
- __tests__/navigation/linking.w315.test.ts
- __tests__/onboarding/step05Trust.s69.test.tsx
- __tests__/primitives/DimensionBar.test.tsx
- __tests__/primitives/MatchBadge.test.tsx
- __tests__/rtl/directionalIconWiring.contract.test.ts
- __tests__/rtl/textAlignLogical.contract.test.ts
- __tests__/s11/categoryRow.s11.test.tsx
- __tests__/s11/copy.s11.test.tsx
- __tests__/s11/fabricated.s11.test.tsx
- __tests__/s11/gateRows.s11.test.tsx
- __tests__/s11/honestUnknowns.s11.test.tsx
- __tests__/s11/launchSurfaces.s11.test.ts
- __tests__/s11/refusals.s11.test.tsx
- __tests__/s11/refusalsCamera.s11.test.tsx
- __tests__/s11/sseFallback.s11.test.ts
- __tests__/s11e/arCopy.s11e.test.ts
- __tests__/s81_08/cameraHeaders.s81_08.test.ts
- __tests__/s81_08/consentRecord.s81_08.test.ts
- __tests__/s81_08/gateRows.s81_08.test.ts
- __tests__/s81_08/i18nKeys.s81_08.test.ts
- __tests__/s81_08/requestHeaders.s81_08.test.ts
- __tests__/s81_08/resetRender.s81_08.test.tsx
- __tests__/s81_08/sseHeaders.s81_08.test.ts
- __tests__/screens/LimitReachedSheet.s69.test.tsx
- __tests__/screens/ResultsScreen.bundle_c_integration.test.tsx
- __tests__/screens/ResultsScreen.degraded.s69.test.tsx
- __tests__/screens/ResultsScreen.integration.test.tsx
- __tests__/screens/ResultsScreen.no_estimated_copy.test.tsx
- __tests__/screens/ResultsScreen.test.tsx
- __tests__/screens/ResultsScreen.weird_mode.test.tsx
- __tests__/screens/authBrandMark.u4d.test.tsx
- __tests__/screens/camera.authRequired.u13c.test.tsx
- __tests__/screens/camera.engineUnavailable.s69.test.tsx
- __tests__/screens/paywall.noSubscriptionUi.s69.test.ts
- __tests__/services/pushNavigation.w315.test.ts
- __tests__/services/pushPrompt.s69.test.tsx
- __tests__/setup.ts
- __tests__/theme/motion.test.ts
- __tests__/utils/deriveTone.test.ts
- __tests__/utils/dimensionLabel.w414.test.ts
