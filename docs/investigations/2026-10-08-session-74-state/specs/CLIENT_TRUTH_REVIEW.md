# CLIENT-TRUTH spec - adversarial review (session 74, 2026-10-08)

Spec: `scratchpad/s74-state/specs/CLIENT_TRUTH_SPEC.md` sha256 35156eaedbf9e9d0f3d5e9dc557ba24b39c7bc46881b6d9af6b44b5617933f3b (re-hashed at start, matches).
Code: main dfbda511 in `sc-s71-t0b` (HEAD dfbda511, status clean; read-only). U8 branch read-only in `sc-s70-u4b` (HEAD 6c74d9b6).
Nothing executed except reads, greps and two read-only Python catalog scans (`client-truth/review/scan_ar.py`, `keylines.py`). No jest/tsc/eslint (spec-only round).

## Verdict
AMEND BEFORE RED. 0 blocking, 6 major, 4 minor, 8 notes. The spec's code truth table is accurate (every anchor below re-checked); the gaps are (a) false claims on the same referral/reviewer surfaces that the spec leaves in place, (b) one rewritten claim that no RED node pins, (c) a cross-unit contradiction on the bonus expiry, (d) the OTC half of AR-5.

## Verified (true at dfbda511)
- ShareBottomSheet.tsx: Gift import :29; previewMessage :140-145; weekly branch :218-219; reward block :238-267 (now-row :251-258, later-row :259-266); preview :319-325; styles messagePreview* :495-509.
- RegisterScreen.tsx: import :25; state :53-56; effect :84-116 (clipboard half :101-112); handlers :118-128; banner :383-419; styles :645-693 (all nine `consent*` styles are used only inside the banner).
- EditProfileScreen.tsx delete flow :125-156 (api.delete :137, clearAiConsent :140, clearSession :141); the only account-deletion path in src.
- HomeScreen.tsx:94/:304/:322 key `@qaren_recent_searches`; ResultsContent.tsx:140 price pending, :366-373 degraded note, :73 resultHonesty import; confidenceDetailsLines.ts:52 `{ n }`.
- referral_service.py:284-289 (no weekly raise), :336-345 Loop 1 credit, :46 BONUS_EXPIRY_DAYS=7, :682-693 device cap, :700 grant 10 premium / 5 free; usage_service.py:350-356 bonus raises the MONTHLY cap only.
- app.json:56-62 SearchHistory purposes; inventory row 5 :35 and fence :117-124; nativeBundle c3 sorts entries by type but compares purpose arrays in order (:676-685), c5 sorts purposes (:715-770), u14 uses toContain (:1470-1479).
- sentry.ts:37 rung, :99-106 value scrub; sentry_service.py:44-46 tuple (same ten names, same order), :361-369 R1, :524-526 order (R1, R2, outbound, then patterns). Only sentry.test.ts:108-120 pins pre-R1 text; no node pins product_a unredacted.
- 388 provenance: `data/cohort_priors.json:4` total_responses 388 (the spec's "not verified" item is now verified).
- Package parity: `git diff --stat dfbda511 6c74d9b6 -- SmartCompareApp/package.json SmartCompareApp/package-lock.json` empty; sc-s70-u4b status clean; `node_modules/@babel/core` and `.bin/jest` present; installed i18next 26.1.0 = lock.
- No snapshot suite renders a changed component (17 suites with toMatchSnapshot; none imports ShareBottomSheet, RegisterScreen, EditProfileScreen, ResultsContent, Step12, ConfidenceDetailsSheet).
- U8 `test_fix_a1` (test_legal_docs_u8.py:1449-1498) is conditional: once the rung has product_a/product_b the "product names" sentence becomes optional; U8 stays green either way. U8's en/ar edit is at en:880 (legal.*), 14+ lines from CLIENT-TRUTH's nearest edit (en:860-863): no textual conflict expected.
- Email prefix in the Loop 2 push (referral_service.py:926-929) is U3c's (U3C_PRIVACY_PINS_SPEC.md:12, :59-74; ruling UP4 A15 gate). No CLIENT-TRUTH action.

## Findings

### CTR-1 (major) The rewritten reward line is pinned by no RED node
- Evidence: CT-S1 asserts only that `reward.later` renders (green at main with "+5 comparisons if they sign up", en:424); CT-S3's regex `/Deep Review|this week|weekly|2\s*x-sign/` does not match the old reward.later. If GREEN forgets C1's catalog change, every CT node passes and the AR-1 core claim ("+5 if they sign up": wrong trigger, wrong tier) ships.
- Fix: add CT-S5 (copyTruth or shareTruth): EN and AR `referrals.share.reward.later` contain no "+5"/"+10"/"if they sign up"; EN contains `${BONUS_EXPIRY_DAYS} days` where BONUS_EXPIRY_DAYS is read from `../app/services/referral_service.py` (`^BONUS_EXPIRY_DAYS = (\d+)`, same cross-package read pattern as CT-Y3) and the phrase "first comparison". RED at main: "+5 comparisons if they sign up". Also strip the code defaultValue (:263) - CT-S4 can pin "no '+5' literal in ShareBottomSheet.tsx".

### CTR-2 (major) Reward block stays unconditional, so the new line is false for capped users
- Evidence: Loop 2 stops at the device lifetime cap (referral_service.py:682-693, LIFETIME_CAP 3 :40). The sheet renders the reward block regardless of `atLifetimeLimit` (ShareBottomSheet.tsx:242-267), and ResultsScreen passes `lifetimeRemaining` only after a share in the same screen (ResultsScreen.tsx:229 null, set only at :556, passed at :954), so a capped user always sees "Bonus comparisons for 7 days when a friend ... signs up".
- Fix (pick one, both cheap): (a) render the reward block only when `!atLifetimeLimit` AND state the cap in the copy ("... for each of up to 3 friends who ..."), so the first-open case (cap unknown) stays true; or (b) wording with the cap only. Add a node: lifetimeRemaining 0 -> no `share-reward-block` (ShareBottomSheet.lifetimeLimit harness). Note ShareBottomSheet.redesign.test.tsx:22-24 pins the testID in source only (stays green).

### CTR-3 (major, scope) Push pre-prompt promises a feature that does not exist (reviewer-reachable)
- Evidence: en:691 / ar:688 `notifications.prePrompt.body` "... If you invite friends, it also tells you when one joins or when a bonus is about to expire." rendered by PushPrePrompt.tsx:60 on Results. No bonus-expiry push exists: push_service.py has send_push (:29, no caller), send_loop2_push (:54), send_reengagement_push (:88, event types decision_insight / cohort_curiosity / decision_retrospective, reengagement_service.py:323-363); referral_service.py:44 is a comment only. Same guideline class as AR-1 (2.3.1(a)).
- Fix: drop "or when a bonus is about to expire" (EN + AR, native review). Constraints: BRAND_KEY (brand.myez.s69.test.ts:59-90) and pushPrompt.s69.test.tsx T3.15/T3.16 (:320-345: must name MYEZ and Profile, no price words, AR no diacritics except the brand). Add a CT node (no /expire/i in EN body). Outside plan row 96's literal list: orchestrator/Fable decides fold-in vs follow-up.

### CTR-4 (major) "Try MYEZ free - 5 comparisons" is false and sits in the block the spec edits
- Evidence: en:491 / ar:488 `referrals.quiz.signupCtaSoft` + defaultValues InviteeQuizScreen.tsx:270 and :275, directly under the `signupBody` the spec rewrites (C6, :264). Free tier = lifetime_free 3, daily 3, monthly 10 (usage_service.py:138-149); the invitee's only grant is a Deep Review row (referral_service.py:876-879), no comparisons. S69 U6 fixed the same "5" in register.benefits (honestCounts.s69.test.tsx:5-10) and missed this key. Pinned false by InviteeQuizScreen.redesign.test.tsx:84-86 (`/"Try MYEZ free.*5 comparisons"/`).
- Fix: EN "Try MYEZ free" (AR keeps the brand word: BRAND_KEY), drop the "5" from both defaultValues, assigned amendment of InviteeQuizScreen.redesign.test.tsx:84-86 (+ its docblock :8), CT node "signupCtaSoft EN/AR contain no digit". Reach: invitee path only (not the reviewer's).

### CTR-5 (major, cross-unit) The Loop 2 push says "Expires in 3 days"; the new in-app line says 7
- Evidence: push_service.py:173-194 `_loop2_copy` EN "Expires in 3 days." and the AR twin; BONUS_EXPIRY_DAYS = 7 (referral_service.py:46, applied :847-860). U3c keeps the named copy byte-identical (U3C_PRIVACY_PINS_SPEC.md:88-92, its T16), so neither unit fixes it and U3c will pin the false text. `tests/test_loop2_gift_copy.py:42-47` accepts "expires" alone, so a fix there stays green.
- Fix: a backend line (U3c is the natural home since it already edits `_loop2_copy`, or a rider unit): body text derived from BONUS_EXPIRY_DAYS (EN + AR, native review), U3c T16 expectation updated. CLIENT-TRUTH's copy is the true one; record the dependency in the PR body.

### CTR-6 (major) OTC medicines get no medical note
- Evidence: AR-5 (CRITIQUE_APP_REVIEW.md row AR-5) is "Supplement and OTC comparisons". The spec's trigger is supplements only. `classify_category_from_text` (extraction_service.py:1307-1341) returns supplements for OTC only through the tablet veto (:1334), which needs the token "tablet(s)" AND flag ENABLE_CATEGORY_TOKEN_FIX (`category_token_fix_enabled` :603, default OFF per the docstring); `is_supplement_query` (price_service.py:1295-1330) has no OTC drug tokens (SUPPLEMENT_* sets :604-652: no paracetamol/ibuprofen/panadol/aspirin). So "Panadol Extra vs Adol" lands in "other" (or the GPT-mini classifier) and shows no note.
- Fix options for the Fable gate: (a) extend `isSupplementComparison` with a name check mirroring `_PHARMACY_TABLET_TOKENS` (extraction_service.py:1259) + a dose regex (mg|mcg|iu|ml after a number, cf. `_TABLET_DOSE_RE` :1272) over product names, with a node per arm; (b) accept supplements-only as the literal MED=A wording and log OTC as residual 1.4.1 risk. The reviewer's warm-up pair (Vitamin D3) is covered either way.

### CTR-7 (minor) Share error path still shows raw backend/axios English text
- Evidence: ShareBottomSheet.tsx:221 `setErrorMessage(ref?.message ?? t('referrals.share.error.generic'))`; referralService.ts:79-103 `normalizeError` always sets a message (detail.error, data.error, detail string, err.message, 'Unknown error'), so the catalog line is unreachable and AR users see English ("Request failed with status code 500", "Network Error"). The spec rewrites the adjacent branch (C4) and keeps this.
- Fix: after dropping the weekly branch, always `setErrorMessage(t('referrals.share.error.generic'))` (house rule W3-14, EditProfileScreen.tsx:145-151). Node: createShare rejects with a ReferralError('Request failed with status code 500') -> generic copy shown.

### CTR-8 (minor) Fence set omits suites that load the changed modules
- Evidence: suites importing a changed file and absent from the spec's fence command: RegisterScreen.inviteCode / inviteId / emailConfirmation.m18, AuthScreens(.socialDiagnostic/.socialTimeout), auth/appleButton.s69, screens/authBrandMark.u4d, EditProfileScreen.bundleE.s3 / appleRelay / editPreferences, ResultsContent.partialNote / imageUrl / scoreGuard / v2Wiring, components/ResultsContent.a11y.w311 / rewriteOrder / runnerUp, ResultsScreen.pushPrePrompt.u6 + screens/ResultsScreen / .bundle_c_integration / .degraded.s69 / .integration, Screens.bundleD.contract, services/pushPrompt.s69, InviteeQuizScreen.degraded.s69, i18n/plurals + referralExpiryPlurals (inside `__tests__/i18n`, already covered).
- Fix: either add them or state that the full suite is ALSO run at the RED commit (to prove that only CT nodes are red). Checked: none of them pins a removed key or the clipboard read except the four assigned RegisterScreen.deferredCode nodes.

### CTR-9 (minor) The assigned sentry.test.ts amendment must not re-add the JWT literal
- Evidence: sentry.test.ts:109-110 holds a JWT-shaped literal; the pre-commit hook greps ADDED lines with JWT_RE (.githooks/pre-commit:189-193, backstop :219-221) and gitleaks runs with the default jwt rule (.gitleaks.toml:21-22 useDefault). Re-indenting or rewriting the node turns :109-110 into '+' lines and the commit is refused.
- Fix: the amendment changes only :119 (and optionally the title :108); new CT-Y4 builds its sentinel at runtime.

### CTR-10 (minor) Stale text left behind
- ShareBottomSheet.tsx:134-139 comment ("We swap to the comparison-specific preview only when no link is available yet"); EditProfileScreen.tsx:8 header ("Photo upload coming soon"); RegisterScreen.deferredCode.test.tsx:1-11 docblock (clipboard chain); `referrals.share.subtitle` en:421 "What we share when you send this." now heads a sheet without the preview it described (product call: keep, or reword in the same native-review batch).

### Notes
- N1 Recent searches survive sign-out (clearSession, authService.ts:626-637, removes tokens + user only): the next account on a shared device sees them in Home. `@qaren_onboarding_draft_v1` (onboardingDraft.ts:53) is also not cleared at deletion. Outside #295; follow-up. The U8 policy s14 sentence ("deleting your account also removes the AI permission record", sc-s70-u4b app/legal/privacy_policy.md:142) under-claims after this unit (still true); tighten after both merge.
- N2 Worktree plan verified (see Verified). Hazard: the CLIENT-TRUTH junction depends on sc-s70-u4b/SmartCompareApp/node_modules; sc-s70-u4b must not be removed or cleaned (U8 merge cleanup) before the CLIENT-TRUTH junction is unlinked with `cmd /c rmdir`. Run at most one jest process per node_modules at a time (box limit of 2 gate-heavy workflows).
- N3 cloudflare-workers/qaren-redirect/src/index.ts:86-92 tells users "The invite code is already on your clipboard" and writes it; undeployed (idTBD). After this unit the app no longer reads it: the re-enable note must also gate the Worker deploy. No deployed landing page writes the clipboard (landing/open.html hands off via qaren://r/<code>), so no live path loses a code.
- N4 CT-C3 uses "no digit": JS `\d` misses Arabic-Indic digits; use `[0-9\u0660-\u0669\u06F0-\u06F9]` (digitPolicy.w311 already forbids them, so belt-and-braces).
- N5 The medical note is absent where supplement verdicts also appear: InviteeQuizScreen result ("Ideal for you", invitee path) and the text-only share body (ResultsScreen.tsx:536-543). Low reach.
- N6 `NSPrivacyCollectedDataTypePurposeAnalytics` verified only against the repo (already used at app.json for OtherUserContent, UserID, ProductInteraction, PerformanceData; c2 regex :668-670). No Apple/Expo doc read (no web). ASC labels are refilled from the inventory at listing time (FABLE_RULINGS_U8.md UL4).
- N7 Dead keys with false claims kept: `referrals.share.toast.confirm` en:425 ("We'll add 5 more if they sign up", pinned by ShareBottomSheet.redesign.test.tsx:67-70), `referrals.status.subtitle` en:500 (BRAND_KEY), `referrals.quiz.placeholder` en:466. Unrendered (no t() reader in src), so not user-visible; A9's "remove dead false claims" rationale is applied unevenly but harmlessly.
- N8 Until U8 merges, the in-app Terms (LegalScreen -> app/legal/terms_of_service.md:83-85) and landing/terms.html:263 still say sharing earns a Deep Review credit; U8's branch removes it. Both units are preconditions of the production build; order is free, but the store binary must not ship ahead of U8's legal text.

## Answers to the attack list
1 Missed surfaces: CTR-3 (pre-prompt), CTR-4 (signupCtaSoft), CTR-5 (push 3 days); email prefix = U3c (verified); onboarding: no Deep Review / weekly copy beyond s12 (cohort.trainedBy, s14.cohort_footer, tips.cohort_match have no renderer).
2 Fences: none silently broken by the spec's diff (i18n parity, pluralFamilies, no-missing-referenced-keys, BRAND_KEYS, copy-policy, brand.hardcoded (case-sensitive /Qaren/, so '@qaren_' literals pass), aiDispatchFence (dispatch sites only), AI_CONSENT_VERSION untouched, nativeBundle c3/c5/u14/(d)); fixing CTR-3/CTR-4 adds pushPrompt.s69 T3.15/T3.16 and InviteeQuizScreen.redesign:84-86 to the list.
3 Supplements note: CTR-6 (OTC); no duplicate in-app disclaimer (0 hits disclaimer/medical in en.json); wording matches 1.4.1's "check with a doctor" ask.
4 Clipboard: no live path depends on it (N3); deep link (linking.ts r/:code), Android PIR and manual typing remain; CT-R3 guards the deep link.
5 Deletion: key name correct; N1 for sign-out and the onboarding draft.
6 app.json: N6.
7 Sentry: rung names and order equal the backend tuple; `[^&#]*` + alternation backtracking keeps `urls=`/`product_a_id=` intact; exception blanking is hermetically testable; the only existing pin of the old behaviour is sentry.test.ts:108-120 (amend, CTR-9); no node pins the old rung names.
8 RED/tautology: CTR-1 (CT-S1 later-row half is tautological); others red for the stated reasons.
9 Worktree: N2.
