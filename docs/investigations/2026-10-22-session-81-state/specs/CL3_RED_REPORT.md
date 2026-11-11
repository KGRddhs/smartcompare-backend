# CL3 RED REPORT (unit CL3 + S81-24e + ContactUs source + RIDER (d))
Agent: the CL3 RED agent (Claude Opus 5.5). Base a74caba7e3ff66b12e94178c912197c845ccbd14. Worktree C:/Users/SynAckITPC/Documents/AI/sc-s81-cl3.

## Summary

- 7 RED files + 1 ASCII fixture under SmartCompareApp/__tests__/cl3/ (72 nodes): card.cl3.test.tsx (R1-R19 + R6b x2, R10b, R11b), reveal.cl3.test.tsx (V1-V10 + V2b, V3b, K1, K1b), idsHome.cl3.test.tsx (I1, I2, I3, I7), idsResults.cl3.test.tsx (I4, I5, I5b, I6), copyPrivacy.cl3.test.tsx (C1-C5, P1-P4), riders.cl3.test.tsx (F1, F2, F2b, F2c, F3, F4, F5, K1 contact), referralCopy.cl3.test.ts (RIDER (d): RD1-RD3, PB1-PB4).
- BASE (a74caba7, real worktree): 60 failed / 12 passed. Every failure is an assertion (`Error: expect(...)`, read from the json; 0 suite errors, 0 TypeError / module errors). The 12 passing are exactly the PIN rows: V10, K1b, I3, I7, F3, F4, F5, P4, PB1, PB2, PB3, PB4.
  [jest] tag=cl3-red-base-final-plain start=2026-11-11 18:44:21 end=2026-11-11 18:44:25 rc=1 (Test Suites: 7 failed; Tests: 60 failed, 12 passed, 72 total)
  (first base run 18:33:12-18:33:22 rc=1: 61 failed / 11 passed; then F5 was rewritten as a static PIN and R16 moved to the RNTL pure entry; V4 gained a scroll-back sub-assertion after mutant M20 survived run 1.)
- PROTOTYPE (in place, byte copies, .qa-mutation.lock, restored + sha-checked: 12 files + 1 new file deleted): 72 passed / 0 failed.
  [jest] tag=cl3-proto-final start=2026-11-11 18:44:03 end=2026-11-11 18:44:07 (Tests: 72 passed, 72 total). Q2 ON is driven inside R16 by jest.doMock(requireActual + true); with the constant false nothing of Q2 renders (R15).
- MUTANTS: 64 run, 64 KILLED (M20 survived run 1 and is killed by the strengthened V4; M45 is killed by the existing copy-policy fence, not a cl3 row). No equivalent survivor.
- Backend comm set at base (38 files, chunks 25 + 13): 2,858 passed, 0 failed. Base record stored: harness/base_records/a74caba7e3ff66b12e94178c912197c845ccbd14/078677731bc09069c55895db4987f5d692f76abb39aef30ebfd1abc057a0e93f.txt
  [pyt] tag=cl3-red-comm1 start=2026-11-11 18:44:37 end=2026-11-11 18:45:14 elapsed=36s bound=1200s status=OK rc=0 (1856 passed, 4 deselected; [hermeticity] sentinel checked 1856 test(s); [netguard] blocked 2 attempt(s) from 2 node(s))
  [pyt] tag=cl3-red-comm2 start=2026-11-11 18:45:20 end=2026-11-11 18:46:10 elapsed=50s bound=1200s status=OK rc=0 (1002 passed; [hermeticity] sentinel checked 1002 test(s); [netguard] blocked 61 attempt(s) from 29 node(s))
- Client jest comm set at base (the spec's 189 minus the 2 non-suite helpers + the 3 src/utils/__tests__ catalog importers of review B2 = 190 paths): 4 failed = the 4 accepted config/nativeBundle.w37 drift nodes (d5, k2, k4, k5); 2,100 passed, 13 skipped, 13 todo.
  [jest] tag=cl3-red-jest-comm-base start=2026-11-11 18:47:04 end=2026-11-11 18:47:23 rc=1. List: cl3_red/jest_comm.txt.
- Restore check: real worktree HEAD a74caba7, `git status --short` = `?? SmartCompareApp/__tests__/cl3/` only, `git diff --quiet` clean, 0 modified tracked files; .qa-mutation.lock removed; no scratch worktree was created (the client prototype and mutants ran IN PLACE per the client RED rule; no backend probe needed one); no orphan pytest of mine.

## Contract choices the RED rows fix (GREEN must match them)

- testIDs: feedback-card, feedback-q1, feedback-q1-yes/-no/-unsure, feedback-details (accessibilityLiveRegion="polite": the RN jest mock exports no AccessibilityInfo, so the announce is the live region, C10), feedback-side-first/-second/-both (role radio, accessibilityState.selected), feedback-correction-input (maxLength 80, multiline false, textContentType "none", autoComplete "off", autoCorrect false, placeholder + accessibilityLabel = results.feedback.correctionPlaceholder), feedback-send (accessibilityState.disabled + an in-handler guard, C1), feedback-skip, feedback-q2, feedback-q2-first/-second/-neither/-unsure, feedback-thanks. Every pressable minHeight (or height) >= 44.
- src/services/feedbackAnswers.ts exports FEEDBACK_DWELL_MS = 8000, CORRECTION_MAX = 80, sanitizeCorrection (C0, DEL, C1, U+2028, U+2029 removed; unpaired surrogates removed; an 80-unit cut never ends in a high surrogate, C3), feedbackIds, attachCompareRequestId, isCompareRequestId.
- ResultsContent: the dwell effect runs once per mount (deps []), eligibility = resultOrigin !== 'stored' ONLY (R-CL3-16: partial and degraded KEEP the card); reveal on scroll only after a verdict layout; the card has no entering animation of its own (V9 structural, B1); the ScrollView gains keyboardShouldPersistTaps="handled" AND automaticallyAdjustKeyboardInsets (K1, B3; RN 0.81 prop, no dependency).
- ResultsScreen always passes the NEW prop feedbackCompareRequestId (undefined on a History reopen or a malformed id, I5b / I6); the camera id comes from data.compareRequestId (not data.result).
- Home attaches the id to the result object (R-CL3-17) on the stream and Link paths; no new route param (I7 PIN).
- S81-24e: the client can read the retry hint ONLY as the envelope retry_after_seconds (parseApiError withRetryAfter, api.ts:1114-1126); the Retry-After header is not read. Hint absent or <= 120 -> common.errors.rateLimited; > 120 -> ONE new common.errors.* key present in both catalogs (the rows do not name it; the prototype used common.errors.rateLimitedLater). Every other branch byte-identical (F3 / F4 / F5 PINs).
- Leaf count per catalog after CL3 = 1,011 - 6 (card) - 3 (rider) + 11 (card) + 1 (S81-24e long-limit key) = 1,014 (C4).
- RIDER (d): referrals.share.reward.title / .later and referrals.loop1.counter leave both catalogs (RD1); no src file renders share-reward-block or reads a removed key (RD2); no new reward / bonus / paused / unlock referrals key in the sheet or the Results toast (RD3). PINs: the Home +N pill (PB1), its a11y text with the bonus arg in both branches + both catalogs (PB2), profile.month.bonus (PB3), the share flow + the Loop 1 thanks toast (PB4).
- P4 PIN: compareRequestId appears (comments stripped) only in api.ts, requestContext.ts, feedbackAnswers.ts, HomeScreen.tsx, ResultsScreen.tsx, ResultsContent.tsx, FeedbackCard.tsx, types.ts (the share POST carries only the comparison id, api.ts:1230-1233).

## E-rows GREEN needs (measured: the neighbour suites run against the prototype)

[jest] tag=cl3-proto-neighbors start=2026-11-11 18:36:19 end=2026-11-11 18:36:29 (44 suites: 6 failed, 38 passed; 15 failed nodes):
- E1 components/FeedbackCard.designChips (3 nodes): delete per spec.
- E2 s11/copy.s11 'parity 0 and 1,011 leaves' (1) and E3 s11e/arCopy.s11e P3 (1): the count becomes 1,014 (not the spec's 1,016: rider -3, S81-24e +1).
- E4 cl2/scope.cl2 P14 (1): the export census gains ENABLE_FEEDBACK_PREFERENCE_Q2.
- E6 NEW (rider): ShareBottomSheet.redesign.test.tsx 4 nodes (reward block, reward keys, reward-above-toggles, reward + toast keys).
- E7 NEW (rider): clientTruth/shareTruth.s74.test.tsx 5 nodes (CT-S1, CT-S2, CT2 GUARD, CT1 + Y10, CT2 cap). One of the FOURTEEN backend-scanning client fences: an E-row on a fence, re-aimed so the absence of the promise is pinned, never weakened.
- E5 tests/test_feedback_allowlist_superset.py (backend, R-CL3-19): not exercised against the prototype (backend pytest ran at base only); per the spec two of its rows go red once the send site is removed.
- Green under the prototype (no E-row): copy-policy, i18n/* (no-missing-referenced-keys, no-deleted-keys, ...), b3a/honestCopy, ResultsContent.render / rewriteOrder, ResultsScreen.bundleE.s3, Results.memo.m21, ResultsEntryParams.a18, HomeScreen.minDisplayFloor, ContactUsScreen, Screens.bundleD.contract, s81_08/*, cl2/homeFloor, i18n.test, consent/aiConsentV2.s75, rtl/*, config/features.

## R-CL3-22 measurement (the useful readers)

- vw_cohort_feedback_lift (migrations/013:46-58) is read only by the admin route admin_routes.py:736-750 (verify_admin_key) and the static admin page app/static/admin/cohort.html:148. Admin only.
- winner_agreement: structured_comparison_service.py:5948 selects comparison_feedback.useful (the fire-and-forget profile update, unflagged; ENABLE_BEHAVIOR_PROFILE_REBUILD changes only the comparison / event columns) -> behavior_service.py:99-105,166 writes it into users.behavior_profile. grep over app/, scripts/ and SmartCompareApp/src: NO reader of winner_agreement / agreement_rate. NULL useful rows count as neither agreed nor disagreed.
- Verdict: no request-path consumer under a production-ON flag -> SF1b is NOT a precondition of the CL3 OTA; both stay stated limits.

## Deviations (reported, not silently changed)

1. R-CL3-20's literal EN for the long-limit key, "Too many attempts. Please try again later.", contains the copy-policy scary_vocab_en term "try again": mutant M45 (that string in en.json) is killed by __tests__/copy-policy.test.ts. The RED does not pin the EN string; GREEN needs an orchestrator wording (the prototype's "Lots of attempts on this account right now. Please come back later." passes the fence).
2. The leaf count is 1,014, not the spec's 1,016 (rider -3, S81-24e +1).
3. V6 rewritten per R-CL3-16 (a partial result KEEPS the card); M22 is now "partial excluded", killed by V6.
4. V9 structural per B1 (nearest host ancestor with an entering prop = results-content-feedback), with the not-at-mount precondition first.
5. F5 is a static PIN of authService.requestPasswordReset (rethrow unless detail) plus a check that the coded envelope has no detail key: the isolateModules behavioural form did not reproduce the error object under jest (the caught error had no response).
6. R16 uses '@testing-library/react-native/pure' inside jest.isolateModules (the default entry registers an afterEach hook inside a test body).
7. The client prototype and the mutants ran IN PLACE in the real worktree (client RED rule; byte copies + lock), not in a scratch worktree (no node_modules there, and no junction may be made). No scratch worktree was created.
8. Spec I2's "expo-crypto mock mints ID": the default jest expo-crypto mock returns a non-v4 shape (newCompareRequestId -> null), so idsHome mocks expo-crypto to a canonical v4 built at run time.
9. Rows added beyond the spec: R10b (C3), R11b (C10), I5b, V2b, V3b (C4), K1 + K1b (B3), F2b, F2c (the R-CL3-20 boundary), P4 (R-CL3-17), RD1-RD3 + PB1-PB4 (R-CL3-26).
10. BOX RULE SLIP: before comm chunk 2 the foreign-pytest check returned 2 processes and my call did not wait (check and launch chained in one command). They were lane A's (sc-s81-s04c; created 18:44:39 and 18:46:11) and also overlapped chunk 1 (started after my pre-check). Both my chunks finished OK with 0 failures; nothing foreign was touched or killed.

## Open questions for the gate

- Q-A The EN / AR text and the key name of the S81-24e long-limit key (deviation 1).
- Q-B E6 / E7 (rider) are not in the spec's E-list; E7 is a fourteen-fence suite: confirm the re-aim.
- Q-C K1 pins automaticallyAdjustKeyboardInsets (the smallest RN 0.81 form); a GREEN choosing scrollToEnd-on-focus would need the row amended.
- Q-D The prototype's AR draft for the long-limit key is not pinned; [NATIVE READ] if GREEN keeps it.

## Not measured

- The FULL jest suite (LC-7: the final round's).
- The fourteen backend-scanning client fences as their own run (they run at GREEN; most sit inside the 190-path jest comm set, green at base except the 4 w37 drift nodes).
- tsc / eslint over the new test files (GREEN's gates; ts-jest isolatedModules does not type-check).
- E5 (backend) under the prototype.

## Files

- Scratch cl3_red/: notes.md, proto.py + proto/ (the prototype), orig/ + orig_manifest.json (byte copies), mutants.py, mutation_rows.json (+ run1), mut/*.json, base_final.json, proto_final.json, proto_neighbors.json, comm_list.txt (38), comm_reasons.tsv, comm_chunk1.txt, comm_chunk2.txt, comm1.log, comm2.log, jest_comm.txt (190), jest_comm_base.json.

## Test files (sha256 over the bytes on disk)
- SmartCompareApp/__tests__/cl3/card.cl3.test.tsx 21657 B sha256 af8942c2a2b4ccaec44424afc77a71327d779872c91fe7488514ba5eeec4f0ba (bytes>127: 0, CR: 0)
- SmartCompareApp/__tests__/cl3/copyPrivacy.cl3.test.tsx 11441 B sha256 4a5c53f0a938bac7a8121462800d4dd77425fcce26610f7fa14f5a0f7f21e169 (bytes>127: 0, CR: 0)
- SmartCompareApp/__tests__/cl3/idsHome.cl3.test.tsx 9040 B sha256 29b13848260c03e181b13c91f8c1280701bda50fa9d506c6e921b6717bd3ed12 (bytes>127: 0, CR: 0)
- SmartCompareApp/__tests__/cl3/idsResults.cl3.test.tsx 6731 B sha256 3a22b5545b47214d49f77d4b57c79f7e810124a743b7e626e7e15e0424d8a1ee (bytes>127: 0, CR: 0)
- SmartCompareApp/__tests__/cl3/referralCopy.cl3.test.ts 5718 B sha256 a962787e4230d37e7344200376acb86a5eb2ca618f597211d602e4fc6c2e7f5b (bytes>127: 0, CR: 0)
- SmartCompareApp/__tests__/cl3/reveal.cl3.test.tsx 14557 B sha256 ccdaf6ba4790348de2efed5f6bb84cb6a41fe6c5ce868e960a7b771028bf432a (bytes>127: 0, CR: 0)
- SmartCompareApp/__tests__/cl3/riders.cl3.test.tsx 9205 B sha256 bdd1f50aa40c4f20a82f1e014e98d9f47418dffe25ce2ce98a4371dc6a28bad3 (bytes>127: 0, CR: 0)
- SmartCompareApp/__tests__/cl3/fixtures/cl3_copy.json 2823 B sha256 aadc50632092c4480b63ed502b532e463f2076dca85b0ec5e2bdd5cf0ae37ae4 (bytes>127: 0, CR: 0)

## Per-node result: BASE (a74caba7, the real worktree) -- 12 passed / 60 failed

- FAIL referralCopy.cl3.test.ts :: RD1 the three promise keys are absent from both catalogs
- FAIL referralCopy.cl3.test.ts :: RD2 no src file renders the reward block or reads a removed key (comments stripped)
- FAIL referralCopy.cl3.test.ts :: RD3 no replacement promise and no paused banner: the share sheet and the Loop 1 toast read no new referrals.* reward / bonus / paused key
- PASS referralCopy.cl3.test.ts :: PB1 PIN the Home +N bonus pill renders the remaining bonus
- PASS referralCopy.cl3.test.ts :: PB2 PIN the Home pill accessibility text keeps the bonus count (a11y + a11yResets, both catalogs)
- PASS referralCopy.cl3.test.ts :: PB3 PIN profile.month.bonus stays in both catalogs and is still rendered by the Profile month card
- PASS referralCopy.cl3.test.ts :: PB4 PIN the share flow itself is untouched: the five targets, the privacy toggles and the Loop 1 thanks toast stay
- FAIL card.cl3.test.tsx :: R1 Q1 renders: question + Yes / No / Not sure; no base title, no chips
- FAIL card.cl3.test.tsx :: R2 Yes posts ONE exact row and shows thanks; onSubmitted once
- FAIL card.cl3.test.tsx :: R3 Not sure posts ONE exact row and shows thanks; onSubmitted once
- FAIL card.cl3.test.tsx :: R4 No is recorded AT THE TAP, then the details step with the two names in body order
- FAIL card.cl3.test.tsx :: R5 Send is disabled and inert with nothing chosen, also after a whitespace-only text (C1)
- FAIL card.cl3.test.tsx :: R6 Send with side second + padded text posts ONE more exact row; thanks; onSubmitted once
- FAIL card.cl3.test.tsx :: R6b feedback-side-first maps to wrong_side first (no correction key)
- FAIL card.cl3.test.tsx :: R6b feedback-side-both maps to wrong_side both (no correction key)
- FAIL card.cl3.test.tsx :: R7 text only: no wrong_side key
- FAIL card.cl3.test.tsx :: R8 Skip posts nothing more; thanks; onSubmitted once
- FAIL card.cl3.test.tsx :: R9 leaving the screen on the details step posts nothing more
- FAIL card.cl3.test.tsx :: R10 sanitisation: C0 / DEL / C1 / U+2028 / U+2029 removed, trimmed (C2)
- FAIL card.cl3.test.tsx :: R10b surrogate-safe cut: an 80-unit cut never ends in a lone high surrogate (C3)
- FAIL card.cl3.test.tsx :: R11 length: maxLength 80 on the input, CORRECTION_MAX 80, a 120-char text sends <= 80
- FAIL card.cl3.test.tsx :: R11b the field: single line, no autofill (textContentType none), no autocorrect (C10)
- FAIL card.cl3.test.tsx :: R12 double-tap: two synchronous presses post once (Yes, No, Send)
- FAIL card.cl3.test.tsx :: R13 a rejected POST is silent: Yes still thanks, No still shows details, no error text
- FAIL card.cl3.test.tsx :: R14 ids omitted when absent or malformed, never minted
- FAIL card.cl3.test.tsx :: R15 Q2 OFF (the real features module): after Yes no Q2 and no preference, thanks at once
- FAIL card.cl3.test.tsx :: R15s the constant is declared false in features.ts
- FAIL card.cl3.test.tsx :: R16 Q2 ON (jest.doMock with requireActual): Yes -> Q2 -> preference row only; never after No / Not sure
- FAIL card.cl3.test.tsx :: R17 roles, labels, 44 pt targets, radio state, input label, details announced (C10)
- FAIL card.cl3.test.tsx :: R18 a long name is one tail-ellipsized line; RTL keeps the logical order first, second, both
- FAIL card.cl3.test.tsx :: R18b a blank first name omits that choice; second and Both remain
- FAIL card.cl3.test.tsx :: R19 the parent flag submitted=true renders thanks only (no Q1)
- FAIL riders.cl3.test.tsx :: F1 slowapi 429 (retry 60 s): renders common.errors.rateLimited, never the raw text or the number
- FAIL riders.cl3.test.tsx :: F2 throttle 429 (retry 86,400 s): ONE other common.errors key present in both catalogs, never "give it a moment"
- FAIL riders.cl3.test.tsx :: F2b a coded 429 with NO retry hint renders common.errors.rateLimited
- FAIL riders.cl3.test.tsx :: F2c the boundary: a hint of exactly 120 s is common.errors.rateLimited; 121 s is the long-limit key
- PASS riders.cl3.test.tsx :: F3 PIN every other error renders exactly what parseApiError renders at base
- PASS riders.cl3.test.tsx :: F4 PIN the same answer: success shows auth.resetSent; an empty email shows auth.emailRequired
- PASS riders.cl3.test.tsx :: F5 PIN requestPasswordReset rethrows the axios error unchanged unless the body has a detail key (the coded envelope has none)
- FAIL riders.cl3.test.tsx :: K1 a Suggestion posts useful true + source contact; a Bug posts useful false + source contact (exact bodies)
- FAIL reveal.cl3.test.tsx :: V1 not rendered at mount; the wrapper is
- FAIL reveal.cl3.test.tsx :: V2 the dwell: absent at 7,999 ms, present at 8,000 ms
- FAIL reveal.cl3.test.tsx :: V2b a re-render with new-identity props at 4 s does not restart the dwell (C4b)
- FAIL reveal.cl3.test.tsx :: V3 the verdict bottom scrolled into view reveals before 8 s
- FAIL reveal.cl3.test.tsx :: V3b a scroll BEFORE any verdict layout does not reveal (C4a)
- FAIL reveal.cl3.test.tsx :: V4 once revealed it stays (scroll back to 0, 20 s more)
- FAIL reveal.cl3.test.tsx :: V5 a History reopen (resultOrigin stored) never shows the card
- FAIL reveal.cl3.test.tsx :: V6 a partial result KEEPS the card (R-CL3-16): absent at mount, present at 8 s
- FAIL reveal.cl3.test.tsx :: V6b a degraded result KEEPS the card: absent at mount, present at 8 s
- FAIL reveal.cl3.test.tsx :: V7 the revealed card gets comparisonId, compareRequestId, productNames (body order), submitted, onSubmitted
- FAIL reveal.cl3.test.tsx :: V8 the dwell timer is armed with FEEDBACK_DWELL_MS and cleared on unmount (C5)
- FAIL reveal.cl3.test.tsx :: V9 the revealed card has NO entering animation of its own: its nearest entering ancestor is the wrapper (B1)
- PASS reveal.cl3.test.tsx :: V10 PIN after the reveal the feedback wrapper is still the LAST anchor of the scroll content
- FAIL reveal.cl3.test.tsx :: K1 the Results ScrollView keeps taps for the Send button and adjusts for the iOS keyboard
- PASS reveal.cl3.test.tsx :: K1b PIN the ScrollView keeps its base style and content style props
- FAIL idsHome.cl3.test.tsx :: I1 text stream: the navigated result carries the stream compareRequestId
- FAIL idsHome.cl3.test.tsx :: I2 Link mode: the navigated result carries the minted id; the request carried the same id
- PASS idsHome.cl3.test.tsx :: I3 PIN no id from the stream: the navigated result gains NO compareRequestId key
- PASS idsHome.cl3.test.tsx :: I7 PIN the navigate payload keys stay within the declared set { result, fastHit }
- FAIL copyPrivacy.cl3.test.tsx :: C1 the 11 added keys exist in both catalogs with the fixture EN / AR values
- FAIL copyPrivacy.cl3.test.tsx :: C2 the 6 removed keys are absent from both catalogs and from every src file
- FAIL copyPrivacy.cl3.test.tsx :: C3 the reworded thanks equals the fixture in both catalogs; the AR value carries no diacritic
- FAIL copyPrivacy.cl3.test.tsx :: C4 parity 0; each catalog = 1,011 - 6 - 3 (rider) + 11 + 1 (S81-24e long-limit key) = 1,014 leaves
- FAIL copyPrivacy.cl3.test.tsx :: C5 the 12 new or changed values obey the fences (policy, diacritics, digits, bidi, verb, brand, promises)
- FAIL copyPrivacy.cl3.test.tsx :: P1 static: the card and feedbackAnswers (comments stripped) log, track, store and navigate nothing
- FAIL copyPrivacy.cl3.test.tsx :: P2 behavioural: a run-time sentinel reaches ONLY the submitFeedback body
- FAIL copyPrivacy.cl3.test.tsx :: P3 the wire carrier: submitFeedback posts (url, data) with no config; useful optional; no source member
- PASS copyPrivacy.cl3.test.tsx :: P4 PIN the client-only compareRequestId is read by no src file outside the plumbing set
- FAIL idsResults.cl3.test.tsx :: I4 camera: a body nested under data.result still yields the id carried on data
- FAIL idsResults.cl3.test.tsx :: I5 a text result carrying compareRequestId passes it through
- FAIL idsResults.cl3.test.tsx :: I5b a malformed id on the result is not passed
- FAIL idsResults.cl3.test.tsx :: I6 a History reopen (comparison_id param) passes the prop as undefined

## Per-node result: PROTOTYPE (in place, Q2 constant false; R16 drives Q2 ON by jest.doMock) -- 72 passed / 0 failed

- PASS referralCopy.cl3.test.ts :: RD1 the three promise keys are absent from both catalogs
- PASS referralCopy.cl3.test.ts :: RD2 no src file renders the reward block or reads a removed key (comments stripped)
- PASS referralCopy.cl3.test.ts :: RD3 no replacement promise and no paused banner: the share sheet and the Loop 1 toast read no new referrals.* reward / bonus / paused key
- PASS referralCopy.cl3.test.ts :: PB1 PIN the Home +N bonus pill renders the remaining bonus
- PASS referralCopy.cl3.test.ts :: PB2 PIN the Home pill accessibility text keeps the bonus count (a11y + a11yResets, both catalogs)
- PASS referralCopy.cl3.test.ts :: PB3 PIN profile.month.bonus stays in both catalogs and is still rendered by the Profile month card
- PASS referralCopy.cl3.test.ts :: PB4 PIN the share flow itself is untouched: the five targets, the privacy toggles and the Loop 1 thanks toast stay
- PASS card.cl3.test.tsx :: R1 Q1 renders: question + Yes / No / Not sure; no base title, no chips
- PASS card.cl3.test.tsx :: R2 Yes posts ONE exact row and shows thanks; onSubmitted once
- PASS card.cl3.test.tsx :: R3 Not sure posts ONE exact row and shows thanks; onSubmitted once
- PASS card.cl3.test.tsx :: R4 No is recorded AT THE TAP, then the details step with the two names in body order
- PASS card.cl3.test.tsx :: R5 Send is disabled and inert with nothing chosen, also after a whitespace-only text (C1)
- PASS card.cl3.test.tsx :: R6 Send with side second + padded text posts ONE more exact row; thanks; onSubmitted once
- PASS card.cl3.test.tsx :: R6b feedback-side-first maps to wrong_side first (no correction key)
- PASS card.cl3.test.tsx :: R6b feedback-side-both maps to wrong_side both (no correction key)
- PASS card.cl3.test.tsx :: R7 text only: no wrong_side key
- PASS card.cl3.test.tsx :: R8 Skip posts nothing more; thanks; onSubmitted once
- PASS card.cl3.test.tsx :: R9 leaving the screen on the details step posts nothing more
- PASS card.cl3.test.tsx :: R10 sanitisation: C0 / DEL / C1 / U+2028 / U+2029 removed, trimmed (C2)
- PASS card.cl3.test.tsx :: R10b surrogate-safe cut: an 80-unit cut never ends in a lone high surrogate (C3)
- PASS card.cl3.test.tsx :: R11 length: maxLength 80 on the input, CORRECTION_MAX 80, a 120-char text sends <= 80
- PASS card.cl3.test.tsx :: R11b the field: single line, no autofill (textContentType none), no autocorrect (C10)
- PASS card.cl3.test.tsx :: R12 double-tap: two synchronous presses post once (Yes, No, Send)
- PASS card.cl3.test.tsx :: R13 a rejected POST is silent: Yes still thanks, No still shows details, no error text
- PASS card.cl3.test.tsx :: R14 ids omitted when absent or malformed, never minted
- PASS card.cl3.test.tsx :: R15 Q2 OFF (the real features module): after Yes no Q2 and no preference, thanks at once
- PASS card.cl3.test.tsx :: R15s the constant is declared false in features.ts
- PASS card.cl3.test.tsx :: R16 Q2 ON (jest.doMock with requireActual): Yes -> Q2 -> preference row only; never after No / Not sure
- PASS card.cl3.test.tsx :: R17 roles, labels, 44 pt targets, radio state, input label, details announced (C10)
- PASS card.cl3.test.tsx :: R18 a long name is one tail-ellipsized line; RTL keeps the logical order first, second, both
- PASS card.cl3.test.tsx :: R18b a blank first name omits that choice; second and Both remain
- PASS card.cl3.test.tsx :: R19 the parent flag submitted=true renders thanks only (no Q1)
- PASS riders.cl3.test.tsx :: F1 slowapi 429 (retry 60 s): renders common.errors.rateLimited, never the raw text or the number
- PASS riders.cl3.test.tsx :: F2 throttle 429 (retry 86,400 s): ONE other common.errors key present in both catalogs, never "give it a moment"
- PASS riders.cl3.test.tsx :: F2b a coded 429 with NO retry hint renders common.errors.rateLimited
- PASS riders.cl3.test.tsx :: F2c the boundary: a hint of exactly 120 s is common.errors.rateLimited; 121 s is the long-limit key
- PASS riders.cl3.test.tsx :: F3 PIN every other error renders exactly what parseApiError renders at base
- PASS riders.cl3.test.tsx :: F4 PIN the same answer: success shows auth.resetSent; an empty email shows auth.emailRequired
- PASS riders.cl3.test.tsx :: F5 PIN requestPasswordReset rethrows the axios error unchanged unless the body has a detail key (the coded envelope has none)
- PASS riders.cl3.test.tsx :: K1 a Suggestion posts useful true + source contact; a Bug posts useful false + source contact (exact bodies)
- PASS reveal.cl3.test.tsx :: V1 not rendered at mount; the wrapper is
- PASS reveal.cl3.test.tsx :: V2 the dwell: absent at 7,999 ms, present at 8,000 ms
- PASS reveal.cl3.test.tsx :: V2b a re-render with new-identity props at 4 s does not restart the dwell (C4b)
- PASS reveal.cl3.test.tsx :: V3 the verdict bottom scrolled into view reveals before 8 s
- PASS reveal.cl3.test.tsx :: V3b a scroll BEFORE any verdict layout does not reveal (C4a)
- PASS reveal.cl3.test.tsx :: V4 once revealed it stays (scroll back to 0, 20 s more)
- PASS reveal.cl3.test.tsx :: V5 a History reopen (resultOrigin stored) never shows the card
- PASS reveal.cl3.test.tsx :: V6 a partial result KEEPS the card (R-CL3-16): absent at mount, present at 8 s
- PASS reveal.cl3.test.tsx :: V6b a degraded result KEEPS the card: absent at mount, present at 8 s
- PASS reveal.cl3.test.tsx :: V7 the revealed card gets comparisonId, compareRequestId, productNames (body order), submitted, onSubmitted
- PASS reveal.cl3.test.tsx :: V8 the dwell timer is armed with FEEDBACK_DWELL_MS and cleared on unmount (C5)
- PASS reveal.cl3.test.tsx :: V9 the revealed card has NO entering animation of its own: its nearest entering ancestor is the wrapper (B1)
- PASS reveal.cl3.test.tsx :: V10 PIN after the reveal the feedback wrapper is still the LAST anchor of the scroll content
- PASS reveal.cl3.test.tsx :: K1 the Results ScrollView keeps taps for the Send button and adjusts for the iOS keyboard
- PASS reveal.cl3.test.tsx :: K1b PIN the ScrollView keeps its base style and content style props
- PASS idsResults.cl3.test.tsx :: I4 camera: a body nested under data.result still yields the id carried on data
- PASS idsResults.cl3.test.tsx :: I5 a text result carrying compareRequestId passes it through
- PASS idsResults.cl3.test.tsx :: I5b a malformed id on the result is not passed
- PASS idsResults.cl3.test.tsx :: I6 a History reopen (comparison_id param) passes the prop as undefined
- PASS idsHome.cl3.test.tsx :: I1 text stream: the navigated result carries the stream compareRequestId
- PASS idsHome.cl3.test.tsx :: I2 Link mode: the navigated result carries the minted id; the request carried the same id
- PASS idsHome.cl3.test.tsx :: I3 PIN no id from the stream: the navigated result gains NO compareRequestId key
- PASS idsHome.cl3.test.tsx :: I7 PIN the navigate payload keys stay within the declared set { result, fastHit }
- PASS copyPrivacy.cl3.test.tsx :: C1 the 11 added keys exist in both catalogs with the fixture EN / AR values
- PASS copyPrivacy.cl3.test.tsx :: C2 the 6 removed keys are absent from both catalogs and from every src file
- PASS copyPrivacy.cl3.test.tsx :: C3 the reworded thanks equals the fixture in both catalogs; the AR value carries no diacritic
- PASS copyPrivacy.cl3.test.tsx :: C4 parity 0; each catalog = 1,011 - 6 - 3 (rider) + 11 + 1 (S81-24e long-limit key) = 1,014 leaves
- PASS copyPrivacy.cl3.test.tsx :: C5 the 12 new or changed values obey the fences (policy, diacritics, digits, bidi, verb, brand, promises)
- PASS copyPrivacy.cl3.test.tsx :: P1 static: the card and feedbackAnswers (comments stripped) log, track, store and navigate nothing
- PASS copyPrivacy.cl3.test.tsx :: P2 behavioural: a run-time sentinel reaches ONLY the submitFeedback body
- PASS copyPrivacy.cl3.test.tsx :: P3 the wire carrier: submitFeedback posts (url, data) with no config; useful optional; no source member
- PASS copyPrivacy.cl3.test.tsx :: P4 PIN the client-only compareRequestId is read by no src file outside the plumbing set

## Mutation table (each on byte snapshots of the prototype, exact-once edits, jest by path, restored and sha-checked)

| M | mutant | killed by (failing rows) | verdict |
|---|---|---|---|
| M1 | card body adds useful: true | R14, R2, R3, R4 | KILLED |
| M2 | card adds mattered_most: [] | R14, R16, R2, R3, R4, R6, R6b, R7 | KILLED |
| M3 | No posts nothing at the tap | R10, R11, R12, R14, R4, R5, R6, R6b, R7, R8 ... | KILLED |
| M4 | details body drops identity_correct | R14, R6, R6b, R7 | KILLED |
| M5 | Send enabled with nothing chosen (no in-handler guard) | R5 | KILLED |
| M6 | Skip posts a wrong row | R8 | KILLED |
| M7 | sanitize keeps U+000A | R10 | KILLED |
| M7b | sanitize keeps the C1 range | R10 | KILLED |
| M7c | sanitize keeps U+2029 | R10 | KILLED |
| M7d | surrogate handling removed (lone high surrogate kept / cut unsafe) | R10b | KILLED |
| M8 | CORRECTION_MAX = 100 (and maxLength) | R10b, R11 | KILLED |
| M9 | latch removed | R12 | KILLED |
| M10 | thanks waits on the POST (await, no catch) | R12, R13, R15, R2, R3 | KILLED |
| M11 | feedbackIds mints newCompareRequestId when absent | R14 | KILLED |
| M12 | ENABLE_FEEDBACK_PREFERENCE_Q2 = true | R13, R15, R15s, R2 | KILLED |
| M13 | Q2 shown after No (ON) | R16 | KILLED |
| M14 | Q2 body adds identity_correct | R16 | KILLED |
| M15 | side labels reversed | R16, R18, R18b, R4 | KILLED |
| M16 | wrong_side first <-> second swapped | R6, R6b | KILLED |
| M16b | details step not announced (no live region) | R17 | KILLED |
| M16c | textContentType none dropped | R11b | KILLED |
| M16d | Send / Skip below 44 pt (minHeight 36) | R17 | KILLED |
| M17 | FEEDBACK_DWELL_MS = 0 | V2, V2b, V8 | KILLED |
| M18 | FEEDBACK_DWELL_MS = 9000 | V2, V2b, V3b, V6, V6b, V7, V8, V9 | KILLED |
| M19 | scroll test against the verdict TOP | V3 | KILLED |
| M20 | scroll handler un-reveals below the verdict (re-run after the V4 scroll-back sub-assertion; run 1 SURVIVED) | V4 | KILLED |
| M21 | resultOrigin !== 'stored' dropped | V5 | KILLED |
| M22 | partial excluded (contradicts R-CL3-16) | V6 | KILLED |
| M23 | degraded excluded | V6b | KILLED |
| M24 | timer not cleared on unmount | V8 | KILLED |
| M25 | revealed card wrapped in Animated.View entering | V9 | KILLED |
| M25b | dwell effect restarts on a prop change | V2b | KILLED |
| M25c | reveal on scroll with no verdict layout (default 0) | V3b | KILLED |
| M25d | keyboardShouldPersistTaps dropped | K1 | KILLED |
| M25e | automaticallyAdjustKeyboardInsets dropped | K1 | KILLED |
| M25f | card props: productNames reversed | V7 | KILLED |
| M26 | Home stream: attach line removed | I1 | KILLED |
| M27 | URL path: attach line removed | I2 | KILLED |
| M27b | attach without the uuid check | I3 | KILLED |
| M28 | camera id read from data.result | I4 | KILLED |
| M29 | History reopen passes the result id | I6 | KILLED |
| M29b | result id passed unvalidated | I5b | KILLED |
| M30 | console.log of the body in the card | P1, P2 | KILLED |
| M31 | trackEvent with the body | P1, P2 | KILLED |
| M32 | card sends source: 'result' | R14, R16, R2, R3, R4, R6, R6b, R7 | KILLED |
| M32b | submitFeedback type gains source | P3 | KILLED |
| M32c | submitFeedback posts with a config | P3 | KILLED |
| M32d | share sheet reads result.compareRequestId | P4 | KILLED |
| M33 | ForgotPassword mapping reverted | F1, F2, F2b, F2c | KILLED |
| M34 | ForgotPassword maps EVERY error | F3 | KILLED |
| M34b | retry boundary >= 120 | F2c | KILLED |
| M34c | the long-limit key never used | F2, F2c | KILLED |
| M35 | ContactUs source removed | K1 | KILLED |
| M36 | old key results.feedback.title kept (EN only) | C2, C4 | KILLED |
| M37 | AR thanks with a tanween | C3, C5 | KILLED |
| M38 | EN q1 reworded | C1 | KILLED |
| M38b | EN thanks with a scary phrase | C3, C5 | KILLED |
| M39 | rider: reward block kept (base ShareBottomSheet) | RD2, RD3 | KILLED |
| M40 | rider: loop1.counter kept in both catalogs | RD1 | KILLED |
| M41 | rider: Home +N pill removed | PB1 | KILLED |
| M42 | rider: a11y bonus arg removed (one branch) | PB2 | KILLED |
| M43 | rider: profile.month.bonus removed (EN) | PB3 | KILLED |
| M44 | rider: a paused banner key added | RD3 | KILLED |
| M45 | the ruling's literal EN for the long-limit key (copy-policy fence) | en.json | KILLED |

The [jest] line of every mutant run:

- M1 [jest] tag=M1 start=2026-11-11 18:40:06 end=2026-11-11 18:40:11 rc=1
- M2 [jest] tag=M2 start=2026-11-11 18:40:11 end=2026-11-11 18:40:14 rc=1
- M3 [jest] tag=M3 start=2026-11-11 18:40:14 end=2026-11-11 18:40:17 rc=1
- M4 [jest] tag=M4 start=2026-11-11 18:40:17 end=2026-11-11 18:40:20 rc=1
- M5 [jest] tag=M5 start=2026-11-11 18:40:20 end=2026-11-11 18:40:23 rc=1
- M6 [jest] tag=M6 start=2026-11-11 18:40:23 end=2026-11-11 18:40:26 rc=1
- M7 [jest] tag=M7 start=2026-11-11 18:40:26 end=2026-11-11 18:40:29 rc=1
- M7b [jest] tag=M7b start=2026-11-11 18:40:29 end=2026-11-11 18:40:32 rc=1
- M7c [jest] tag=M7c start=2026-11-11 18:40:32 end=2026-11-11 18:40:35 rc=1
- M7d [jest] tag=M7d start=2026-11-11 18:40:35 end=2026-11-11 18:40:37 rc=1
- M8 [jest] tag=M8 start=2026-11-11 18:40:37 end=2026-11-11 18:40:41 rc=1
- M9 [jest] tag=M9 start=2026-11-11 18:40:41 end=2026-11-11 18:40:45 rc=1
- M10 [jest] tag=M10 start=2026-11-11 18:40:45 end=2026-11-11 18:40:48 rc=1
- M11 [jest] tag=M11 start=2026-11-11 18:40:48 end=2026-11-11 18:40:51 rc=1
- M12 [jest] tag=M12 start=2026-11-11 18:40:51 end=2026-11-11 18:40:54 rc=1
- M13 [jest] tag=M13 start=2026-11-11 18:40:54 end=2026-11-11 18:40:57 rc=1
- M14 [jest] tag=M14 start=2026-11-11 18:40:57 end=2026-11-11 18:41:00 rc=1
- M15 [jest] tag=M15 start=2026-11-11 18:41:00 end=2026-11-11 18:41:03 rc=1
- M16 [jest] tag=M16 start=2026-11-11 18:41:03 end=2026-11-11 18:41:06 rc=1
- M16b [jest] tag=M16b start=2026-11-11 18:41:06 end=2026-11-11 18:41:09 rc=1
- M16c [jest] tag=M16c start=2026-11-11 18:41:09 end=2026-11-11 18:41:12 rc=1
- M16d [jest] tag=M16d start=2026-11-11 18:41:12 end=2026-11-11 18:41:15 rc=1
- M17 [jest] tag=M17 start=2026-11-11 18:41:15 end=2026-11-11 18:41:19 rc=1
- M18 [jest] tag=M18 start=2026-11-11 18:41:19 end=2026-11-11 18:41:22 rc=1
- M19 [jest] tag=M19 start=2026-11-11 18:41:22 end=2026-11-11 18:41:26 rc=1
- M20 [jest] tag=M20 start=2026-11-11 18:43:51 end=2026-11-11 18:43:54 rc=1
- M21 [jest] tag=M21 start=2026-11-11 18:41:29 end=2026-11-11 18:41:32 rc=1
- M22 [jest] tag=M22 start=2026-11-11 18:41:32 end=2026-11-11 18:41:34 rc=1
- M23 [jest] tag=M23 start=2026-11-11 18:41:34 end=2026-11-11 18:41:37 rc=1
- M24 [jest] tag=M24 start=2026-11-11 18:41:37 end=2026-11-11 18:41:40 rc=1
- M25 [jest] tag=M25 start=2026-11-11 18:41:40 end=2026-11-11 18:41:43 rc=1
- M25b [jest] tag=M25b start=2026-11-11 18:41:43 end=2026-11-11 18:41:46 rc=1
- M25c [jest] tag=M25c start=2026-11-11 18:41:46 end=2026-11-11 18:41:50 rc=1
- M25d [jest] tag=M25d start=2026-11-11 18:41:50 end=2026-11-11 18:41:53 rc=1
- M25e [jest] tag=M25e start=2026-11-11 18:41:53 end=2026-11-11 18:41:55 rc=1
- M25f [jest] tag=M25f start=2026-11-11 18:41:55 end=2026-11-11 18:42:17 rc=1
- M26 [jest] tag=M26 start=2026-11-11 18:42:18 end=2026-11-11 18:42:21 rc=1
- M27 [jest] tag=M27 start=2026-11-11 18:42:21 end=2026-11-11 18:42:24 rc=1
- M27b [jest] tag=M27b start=2026-11-11 18:42:24 end=2026-11-11 18:42:28 rc=1
- M28 [jest] tag=M28 start=2026-11-11 18:42:28 end=2026-11-11 18:42:31 rc=1
- M29 [jest] tag=M29 start=2026-11-11 18:42:31 end=2026-11-11 18:42:34 rc=1
- M29b [jest] tag=M29b start=2026-11-11 18:42:34 end=2026-11-11 18:42:37 rc=1
- M30 [jest] tag=M30 start=2026-11-11 18:42:37 end=2026-11-11 18:42:40 rc=1
- M31 [jest] tag=M31 start=2026-11-11 18:42:40 end=2026-11-11 18:42:43 rc=1
- M32 [jest] tag=M32 start=2026-11-11 18:42:43 end=2026-11-11 18:42:46 rc=1
- M32b [jest] tag=M32b start=2026-11-11 18:42:46 end=2026-11-11 18:42:49 rc=1
- M32c [jest] tag=M32c start=2026-11-11 18:42:49 end=2026-11-11 18:42:52 rc=1
- M32d [jest] tag=M32d start=2026-11-11 18:42:52 end=2026-11-11 18:42:55 rc=1
- M33 [jest] tag=M33 start=2026-11-11 18:42:55 end=2026-11-11 18:42:58 rc=1
- M34 [jest] tag=M34 start=2026-11-11 18:42:58 end=2026-11-11 18:43:01 rc=1
- M34b [jest] tag=M34b start=2026-11-11 18:43:01 end=2026-11-11 18:43:04 rc=1
- M34c [jest] tag=M34c start=2026-11-11 18:43:04 end=2026-11-11 18:43:06 rc=1
- M35 [jest] tag=M35 start=2026-11-11 18:43:06 end=2026-11-11 18:43:09 rc=1
- M36 [jest] tag=M36 start=2026-11-11 18:43:09 end=2026-11-11 18:43:12 rc=1
- M37 [jest] tag=M37 start=2026-11-11 18:43:12 end=2026-11-11 18:43:15 rc=1
- M38 [jest] tag=M38 start=2026-11-11 18:43:15 end=2026-11-11 18:43:18 rc=1
- M38b [jest] tag=M38b start=2026-11-11 18:43:18 end=2026-11-11 18:43:21 rc=1
- M39 [jest] tag=M39 start=2026-11-11 18:43:21 end=2026-11-11 18:43:23 rc=1
- M40 [jest] tag=M40 start=2026-11-11 18:43:23 end=2026-11-11 18:43:26 rc=1
- M41 [jest] tag=M41 start=2026-11-11 18:43:26 end=2026-11-11 18:43:28 rc=1
- M42 [jest] tag=M42 start=2026-11-11 18:43:28 end=2026-11-11 18:43:31 rc=1
- M43 [jest] tag=M43 start=2026-11-11 18:43:31 end=2026-11-11 18:43:33 rc=1
- M44 [jest] tag=M44 start=2026-11-11 18:43:33 end=2026-11-11 18:43:37 rc=1
- M45 [jest] tag=M45 start=2026-11-11 18:43:37 end=2026-11-11 18:43:40 rc=1
