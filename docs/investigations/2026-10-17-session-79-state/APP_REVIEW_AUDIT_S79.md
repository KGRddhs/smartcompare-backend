# MYEZ 1.0.0: App Review compliance audit and resubmission plan (session 79, 2026-10-17)

Synthesis of five Opus audit lenses (metadata, privacy and sign-in, functionality, business and legal, design) and the refutation pass on every critical and high finding. Read-only audit. Sources: CLIENT = scratchpad/build2_eed0f628/SmartCompareApp (the JavaScript inside build 1.0.0 (2)); BACKEND = scratchpad/base_e0f3e475 (the live backend and legal texts); ASC = scratchpad/audit/ASC_FACTS_2026-10-17.md; the uploaded screenshot contact sheet; NOTES_DRAFT_v2.txt and REPLY_DRAFT_v2.txt (session-79 state folder); Apple's App Review Guidelines fetched 2026-10-17.

Lens notes: scratchpad/audit_lens1_metadata, audit_privacy, audit_lens3, audit_lens4, audit_lens5_design. Refuter notes: scratchpad/audit_refute_*, audit_verify_L3-04, audit_L4-01_verify. Synthesizer notes and proposed texts: scratchpad/audit_synth/.

---

## 1. Verdict: NEW_BUILD_RECOMMENDED

Build 1.0.0 (2) cannot produce what Apple asked for. Apple's 2.1 Information Needed message (2026-10-13, session-78 ledger line 6) asks for a screen recording on a physical device, from launch, covering registration, login and deletion. In build 2 the sign-in, sign-up, forgot-password and reset-password screens all call `usePreventScreenCapture()` (CLIENT src/screens/LoginScreen.tsx:194, RegisterScreen.tsx:40, ForgotPasswordScreen.tsx:34, ResetPasswordScreen.tsx:54; re-checked by the synthesizer). The pinned expo-screen-capture 8.0.10 places a black full-screen view over the window whenever iOS reports the screen is being captured. So the recording, as scripted in RECORDING_SCRIPT_v2 (B1, B2, B9, B10, B13), would be black exactly where Apple wants to see sign-in and registration. The reply would then describe footage the video does not contain.

The workarounds are worse than a build. Filming the phone with a second camera is not the "screen recording" Apple asked for. An OTA update breaks the standing "no OTA before approval" rule and the reply names the reviewed build.

Two further gates block resubmission whatever the build: the review accounts and "Sign-in required" (L3-02, critical), and the device check of Google Sign-In, Sign in with Apple and the photo compare (L3-05, high). The Account Holder must also accept the updated Program License Agreement before ASC accepts any resubmission (L3-03, a precondition, not a review risk).

Everything else is text, metadata, backend or post-approval work. Build 1.0.0 (3) should be cut from eed0f628 with a small, listed set of changes (section 3) so the truth-checked Notes stay valid.

Critical path, in order:
1. Account Holder accepts the Program License Agreement.
2. 20-second device check on build 2: start Screen Recording, open MYEZ, look at "Welcome back." (confirms L5-01).
3. Device gate on build 2: Continue with Google, Continue with Apple, Scan > Open camera > Compare. The results decide the build-3 scope (hide Google if it fails).
4. Owner approves build 1.0.0 (3) scope; build, upload, TestFlight; repeat the 20-second check on build 3.
5. Supabase checks (Confirm email OFF; Forgot Password link works); Railway names-only check.
6. Review accounts 1 and 2 created, SQL checks A/B, tier raise C, one sign-in with account 1.
7. ASC: select build 3 for version 1.0.0; tick Sign-in required, owner types credentials; paste Notes v3; description and keywords edits; approved screenshot set.
8. Record the video on build 3; send Reply v3 with it; Resubmit. Warm the review pair within 2 h before, then every 12-24 h until a decision.

---

## 2. Ranked action plan

Severity is the final severity after refutation. "Merged" lists duplicate findings from other lenses. Fix owner values: client_code_new_build (ships in build 1.0.0 (3) or later binary), client_code_ota_after_approval (JS-only; ships after approval), backend_code, reply_text, asc_metadata, owner_account_action.

### Critical

**1. L5-01 (merged L3-01). Sign-in and sign-up screens go black in an iOS screen recording.** Guideline 2.1 (Apple's Information Needed request for a recording of registration, login and deletion). Evidence above (section 1); package-lock.json:7450 pins expo-screen-capture 8.0.10; the native module adds a black blockView when UIScreen.main.isCaptured (ScreenCaptureModule.swift:99-109, read from an installed 8.0.10 copy). Refuted sub-claim: the cover does NOT stay up after leaving the auth screens in 8.0.10 (allowScreenCapture removes it, line 57), so the questionnaire, tabs and comparisons record normally. Fix: remove `usePreventScreenCapture()` and its import from LoginScreen.tsx (46, 194) and RegisterScreen.tsx (20, 40); optionally also ForgotPassword/ResetPassword (ResetPasswordScreen.w36.test.tsx:161 pins the hook there, so update that test if removed). secureTextEntry already hides password text in captures. Update jest mocks/pins, run the FULL jest suite, cut build 1.0.0 (3), repeat the 20-second recording check on it, attach it to version 1.0.0, change "1.0.0 (2)" to "1.0.0 (3)" in reply item 1, RECORDING_SCRIPT_v2 A.2 and OWNER_ACTIONS steps 3, 5, 6. Fallback only on the owner's ruling: second-camera film plus the reply wording in section 5. Owner: client_code_new_build. New build: yes. Effort: hours.

**2. L3-02. No working review account; "Sign-in required" unchecked.** Guideline 2.1(a): "include demo account info (and turn on your back-end service!) if your app includes a login." ASC facts line 28 (unchecked; accounts do not exist). Apple's message item 3 asked for "setup instructions with login credentials". CLIENT App.tsx:365-368 renders only the Auth stack while signed out. Self sign-up is weaker than it looks: it needs Confirm email OFF (RegisterScreen.tsx:236-241) and a new sign-up inherits the device's lifetime counter (BACKEND auth_routes.py:488-524). Fix: OWNER_ACTIONS B3-B4 (accounts 1 and 2, checks A/B, tier raise C is required), then D8 (tick Sign-in required, owner types account 1), then prove it: log out, sign in with exactly the stored values, land on the Main tabs. Never compare on account 1 and never delete it. Owner: owner_account_action. New build: no. Effort: hours.

### High

**3. L3-05. Google Sign-In and the photo compare have never run on a device, yet the Notes, reply and description point the reviewer at both.** Guideline 2.1(a): "Make sure your app has been tested on-device ... We will reject ... binaries that crash or exhibit obvious technical problems." ASC facts line 30. CLIENT LoginScreen.tsx:441-449 and RegisterScreen.tsx:425-427 render Google unconditionally; a failure shows "Google sign-in didn't complete" (en.json:1007). Google works only if Supabase "Skip nonce checks" is ON (authService.ts:896-903). The 4.8 citation was dropped: Sign in with Apple is offered (LoginScreen.tsx:429-435), so 4.8 holds either way. Fix: make OWNER_ACTIONS C6 a hard gate. Owner taps Continue with Google, Continue with Apple, and Scan > Open camera (two real products > Compare) on the latest iOS. If Google fails: check the Google iOS OAuth client and the Supabase Google provider (authorized client IDs, Skip nonce checks) and retest; if it still fails, hide the Google button in build 3 and remove Google from the Notes SERVICES line and reply item 4. A text-only edit is NOT enough because the button stays. If the photo compare fails: fix it in build 3, or rewrite Notes step 4, the description's Camera bullet and reply item 1 ("a comparison of two product links"). Owner: owner_account_action. New build: no (yes if a check fails). Effort: minutes.

### Medium

**4. L1-01 (merged L3-10, L4-06, L5-03). Notes and reply misdescribe Share and omit the referral bonus and the invite-code field.** Guideline 2.3.1(a): "All new features, functionality, and product changes must be described with specificity in the Notes for Review ... (generic descriptions will be rejected)". A fresh result shares plain text with no link (ResultsScreen.tsx:532-549); a History comparison opens ShareBottomSheet with a reward block (ShareBottomSheet.tsx:234-251; en.json:435), privacy toggles (ShareBottomSheet.tsx:257-279; en.json:437-442) and a link plus invite code (en.json:869). Sign Up shows "Invite code (optional)" (RegisterScreen.tsx:355-399). Backend: 5 comparisons, 7 days, 3 per device (referral_service.py:40, 46, 838; Terms s9). The v2 texts say Share "only passes a private link". Downgraded from high: the programme is visible and published, and 3.2.2(x) allows in-app incentives with nothing sold. Fix: Notes v3 last paragraph and reply v3 item 1 (section 5). Optional description bullet "invite them for bonus comparisons" (section 4). Owner: reply_text. New build: no. Effort: minutes.

**5. P2. Every feature sits behind sign-up; the reply never says why.** Guideline 5.1.1(v): "If your app doesn't include significant account-based features, let people use it without a login." CLIENT App.tsx:365-370 and LoginScreen.tsx:408-415. MYEZ has real account-based features: saved priorities and budget feed the verdict (BACKEND text_routes.py:599-604, 643; extraction_service.py:1926-1950, 2564-2565), per-account History and allowance. Downgraded from high. Fix: reply v3 item 3 adds "An account is required because MYEZ is account-based: ..."; Notes SIGN-IN says "the saved preferences each verdict uses". Fallback only if Apple rejects under 5.1.1(v): a guest mode via Supabase anonymous sign-in with 1-3 comparisons; do NOT turn the U13 compare-auth flag off (the device fingerprint is a client header the backend only format-checks). Owner: reply_text. New build: no. Effort: minutes.

**6. L3-04 (merged L5-04). A reviewer-chosen compare can fail with a 400 INSUFFICIENT_DATA alert that blames the input; the warm-up cadence regressed.** Guideline 2.1(a) (obvious technical problems; the 4.0 citation was dropped, it concerns removal after approval). BACKEND structured_comparison_service.py:3884-3895 and text_routes.py:544-551; CLIENT errorCopy.ts:76-79 and HomeScreen.tsx:457-458, 515-516 ("Hold on - give it another tap." over "Thin data on that pair - swap in two products with brand and model."). Overstated sub-claim: the Notes pair (iPhone 15 vs Galaxy S24) passed every recorded run and its specs cache for 7 days, so the exposure is mainly cold pairs the reviewer picks, including the step-4 photo compare. Fix: (a) do not wait on fix 8 (it only swaps one failure alert for another); (b) warm-up: run scripts/review_warmup.py on the review pair (app shape, --timeout 35, 2 runs) within 2 h before Resubmit and every 12-24 h until a decision, grep the web log for "unified search timeout", keep Tom Ford Tobacco Vanille vs Creed Aventus as the backup pair; (c) consider flipping the two merged dark levers (#355 residual guard, #356 Serper key memo) only after their canaries pass and with the owner's yes; (d) optional build-3 copy: own title for INSUFFICIENT_DATA that does not blame the input. Owner: backend_code. New build: no. Effort: hours.

**7. L4-01. Apple's third-party-material question is answered with claims only, while images come from Google's image results.** Guidelines 5.2.2: "ensure that you are specifically permitted to do so under the service's terms of use. Authorization must be provided upon request." and 5.2.1. REPLY_DRAFT_v2 item 6; BACKEND image_service.py:86-92 (Knowledge Graph image first), 238-245, 247-262 (Serper Images), 264-273 (GPT-picked image URL); all live (structured_comparison_service.py:5739-5750); CLIENT ProductImage.tsx:101 hotlinks. ASC Content Rights = Yes. Downgraded from high: a clear basis statement usually suffices. Corrections to the lens fix: do NOT claim "only where robots.txt allows" (Scrape.do is an anti-bot fallback, scrapedo_service.py:3) or "nothing is resold" (Terms s8 allows selling aggregated statistics); Terms s7 is a correction route, not a takedown clause. Fix: preferred, backend-only: stop returning Tier 1.5b, Tier 1 and Tier 3 images, let the retailer-page image override (structured_comparison_service.py:5867-5877) supply the image or show the placeholder, re-warm and check images; then use variant A texts. Otherwise use variant B ("publishing site or a search engine's image server"). Owner confirms "no content partnerships" and commits to honouring removal requests. Later: a removal sentence in Terms s7; counsel on the Content Rights basis. Owner: reply_text (+ backend_code). New build: no. Effort: hours.

**8. L3-06 (merged L5-07). One tap on a "Popular comparisons" row starts a compare, but 5 of the 6 curated pairs ended partial at the 30 s cap; three screenshots feature fragrance pairs.** Guideline 2.1(a). BACKEND data/trending_curated.json (6 pairs); RECORDING_SCRIPT_v2 A9 and :18; CLIENT HomeScreen.tsx:666-672. Fix: swap the curated file to pairs that pass the warm-up completely (data file, no build) and add them to the scheduled warm-up; build the screenshot set around the proven pair. Owner: backend_code. New build: no. Effort: hours.

**9. P1 (merged L3-17). Deleting an account never revokes the Sign in with Apple token; the app never sends an authorization code.** Guideline 5.1.1(v) ("you must also offer account deletion within the app" - met) plus Apple's account-deletion guidance ("Apps that support Sign in with Apple should use the Sign in with Apple REST API to revoke user tokens") and TN3194. CLIENT authService.ts:1022-1100 (only id_token and nonce sent); BACKEND auth_service.py:1008-1023 (no appleid.apple.com call). Downgraded from high: the guideline is met; reviewers test deletion with email accounts. Fix: client half in build 3 if it does not delay it (fail-soft: for auth_provider 'apple', which the User type already carries at authService.ts:68, call signInAsync for a fresh authorizationCode and send it in DELETE /api/v1/auth/account; register addRevokeListener; show the manual Settings path when revocation is not confirmed). Backend: exchange the code at /auth/token with an ES256 client_secret, POST the refresh token to /auth/revoke before the cascade, fail-soft, log outcome only, return apple_revoked. Owner: create a Sign in with Apple key (.p8) and store it as Railway secrets (never committed). Optional now: one policy s9 sentence on stopping Apple ID use in iOS Settings. Never claim revocation in the texts until it ships. Owner: client_code_new_build. New build: yes. Effort: days.

**10. P3. User inputs and outputs go to OpenAI for its own model training, in exchange for free usage, and the listing says so.** Guideline 5.1.2(i): "Data collected from apps may only be shared with third parties to improve the app or serve advertising". ASC facts line 30 (sharing ON); ASC description; BACKEND privacy_policy.md:15, 69; CLIENT en.json:702. The disclosure and explicit-permission parts of 5.1.2(i) are met. Owner decision (D3 was "sharing stays ON" on 2026-10-08). Safest: turn the OpenAI organisation data-sharing setting off, then remove the training sentences from the description, policy s2/s4, Terms and the Notes AI PROCESSING line (all server or metadata); align the consent sheet later. If kept ON, the owner accepts the risk knowingly and every disclosure stays as is. Owner: owner_account_action. New build: no. Effort: minutes (decision), hours (texts).

**11. P5. The privacy policy carves OpenAI and the mailbox provider out of the equal-protection confirmation.** Guideline 5.1.1(i): the policy must "Confirm that any third party with whom an app shares user data ... will provide the same or equal protection of user data as stated in the app's privacy policy". BACKEND privacy_policy.md:87 (live). Fix (server legal text, EN + AR, landing redeploy): if P3 sharing goes off, drop the carve-out and confirm equal protection for all providers; if it stays on, add a truthful confirmation that OpenAI and the mailbox provider are bound by their published terms to protect the data at least as well (owner or counsel confirms). Owner: backend_code. New build: no. Effort: hours.

**12. L1-02. The description says prices are "gathered from retailers across the GCC"; by default the main shopping search is US Google Shopping converted to BHD.** Guideline 2.3 (metadata must accurately reflect the app) and 2.3.1(a). BACKEND serper_service.py:686-716, price_service.py:10424-10426, source_router.py:473-484; CLIENT en.json:156, 189. Fix: the description edit in section 4. Owner: asc_metadata. New build: no. Effort: minutes.

**13. L1-05 (merged L3-13, L4-08, L1-07). Every compare loader says "Save any comparison to revisit later - even offline" (no offline storage exists) and "25+ retailers" (a fixed number on a timer).** Guidelines 2.3.1(a) and 1.1.6. CLIENT en.json:279, 285, 287, 749; LoadingScreenVariants.tsx:176-180 (save_offline is a default tip, re-checked). The two lenses disagree on "25+" (275 catalogue rows exist but the GCC catalogue is off by default, source_router.py:473-484), so remove the number either way. Fix in build 3: drop loading.tip.save_offline from DEFAULT_COMPARISON_TIP_KEYS; replace the "25+ retailers" stage and tips with "Checking retailer prices" / "MYEZ checks several retailers for each product". Until build 3, trim the recording around the tip. Owner: client_code_new_build. New build: yes. Effort: minutes.

**14. L1-06. The country step claims "Currency, retailers, and peer cohort all calibrate to your region", but prices are BHD for every country.** Guidelines 2.3.1(a), 2.1. CLIENT en.json:551 (re-checked), ar.json:548, Step04Country.tsx:88-94; Notes REGIONS and reply item 5. Fix in build 3: "Prices are shown in Bahraini Dinar for now; your country helps tailor the advice." (EN + AR). Owner: client_code_new_build. New build: yes. Effort: minutes.

**15. L3-08 (merged L5-02). Choosing Arabic on questionnaire step 2 reloads the app and restarts at step 1, which reads as a crash.** Guideline 2.1(a). CLIENT Step02Language.tsx:26-30, useLanguage.ts:17-23 (Updates.reloadAsync), OnboardingFlow state in useState. Fix: build 3 saves the language and current step before reloadAsync and resumes at step 3 (or defers the RTL reload to the end of the questionnaire). Notes v3 already says "Choosing Arabic reloads the app once for right-to-left", which is true with or without the fix; confirm the reload happens in the owner's dry run (expo-updates in the store build is UNVERIFIED). Owner: client_code_new_build. New build: yes. Effort: hours.

**16. L3-09. Change Password allows 6+ characters but the server needs 10+, so the reviewer sees a raw "Validation error: body -> new_password ..."; the row also shows for Apple and Google accounts.** Guideline 2.1(a). CLIENT ProfileScreen.tsx:255-258, 280; BACKEND auth_routes.py:165-172; error_handler.py:146-162. Fix in build 3: 10+/upper/lower/digit rule and localized copy, map 422 to a friendly key, hide the row for social-only accounts. Owner: client_code_new_build. New build: yes. Effort: hours.

**17. L3-07. After camera access is denied, "Turn on camera" does nothing.** Guideline 2.1(a). CLIENT HomeScreen.tsx:731, 765; ScanCameraScreen.tsx:327-330; no Linking.openSettings in src/. "Or pick from gallery" still works. Fix in build 3: when status is denied and canAskAgain is false, show "Open Settings" calling Linking.openSettings() (EN + AR). Owner: client_code_new_build. New build: yes. Effort: hours.

**18. L3-11. Registration skips the inbox only if Supabase "Confirm email" is OFF, last read 2026-10-08.** Guideline 2.1(a). CLIENT RegisterScreen.tsx (needsEmailConfirmation branch); Notes "No email confirmation needed"; OWNER_ACTIONS 4a. Fix: owner check before sending; if ON, turn it off or drop the sentence from Notes v3 and reply v3 item 3. Owner: owner_account_action. New build: no. Effort: minutes.

**19. L3-12. Forgot Password has not been proven end to end; the in-app reset link sits behind an OFF flag.** Guideline 2.1(a). BACKEND auth_service.py:1033-1066 (ENABLE_PASSWORD_RESET_DEEP_LINK default false); landing apple-app-site-association covers only /r/*, /c/*, /q/*. Fix: send one reset email to a test account on the device and confirm the link reaches a working reset page or screen; if not, allow-list qaren://reset-password in Supabase and set the flag (env only), or point the Site URL at a working page. Owner: owner_account_action. New build: no. Effort: minutes.

**20. SS (merged L1-03, L4-07, L1-04, L5-06, L5-05, L1-18, L1-14, L1-10 screenshot part, L4-02, L1-17, L5-16, L5-17, L5-13 screenshot part). The uploaded set makes inaccurate claims; the redesign must not add new ones.** Guidelines 2.3 and 2.3.3 ("Screenshots should show the app in use"), 2.3.1(a), 2.3.7 ("screenshots ... should not include prices, terms ..."), 5.2.1, 4.1(a). Frame 5: "THIS MONTH ~330 BHD shopped smarter" is an all-time sum of price gaps (BACKEND migrations/036_home_savings_aggregate.sql:54-90, no date filter) and "popular" is a curated list (home_routes.py:8, 128-134). Frame 3: "Owners consistently highlight opens with ..." is stale template output under an "Owner reviews" headline. Three frames show the "3/3 free" pill; no frame shows the verdict. Fix: replace the whole set with the redesigned set after applying section 7; until then leave the current set only if the redesign is not ready. Owner: asc_metadata. New build: no. Effort: hours.

**21. L4-03. Supplement and OTC-medicine comparisons use a "pharmacist" persona and can show dose instructions from training data.** Guideline 1.4.1 (medical information "may be reviewed with greater scrutiny"; remind users to check with a doctor). BACKEND prompt_personalities.py:20-25; extraction_service.py:502-512, 598 (ENABLE_SPECS_NO_FABRICATION default off); drug_database_service.py:58; CLIENT resultHonesty.ts:41-45, en.json:800. Mitigations present: not-medical-advice note (ResultsContent.tsx:380-387) and Terms s6. Fix (backend, no build): drop the dosage field for supplements unless snippet-cited; neutral label-comparison persona with no efficacy or "clinical dose" wording; reword the drug-registry context without "dosage". The description edit adds "ask a pharmacist or doctor". Owner: backend_code. New build: no. Effort: hours.

**22. L4-04. The written IP assignment or licence from the second team member is still open.** Guideline 5.2.1 ("Apps should be submitted by the person or legal entity that owns or has licensed the intellectual property"). OWNER_ACTIONS_S79 item 12; Terms line 53. Fix: a short signed assignment or exclusive licence to the developer from every contributor of code, design and brand assets, kept on file before release. Owner: owner_account_action. New build: no. Effort: days.

**23. P4. The only in-app way to withdraw AI-processing consent is deleting the account.** Guideline 5.1.1(ii): "Apps must also provide the customer with an easily accessible and understandable way to withdraw consent." CLIENT aiConsent.ts:33-37 (clearAiConsent only from deletion, EditProfileScreen.tsx:142); ProfileScreen.tsx:463-531; BACKEND privacy_policy.md:67, 124. Fix: a Profile > Privacy row "AI processing permission" that calls clearAiConsent and re-asks on the next comparison; optionally "Clear my optional answers". Put it in build 3 only if trivial; otherwise OTA after approval; update policy s4 and s10 when it ships. Owner: client_code_ota_after_approval. New build: no. Effort: hours.

### Low

**24. L3-03. Program License Agreement not accepted (submission precondition).** Not a review clause; ASC enforces it before submission (ASC facts line 29; OWNER_ACTIONS A1). Downgraded from high. Fix: the Account Holder signs in at developer.apple.com/account and accepts it; confirm the banner is gone and Business > Agreements shows nothing pending. Do not mention it to App Review. Owner: owner_account_action. New build: no. Effort: minutes.

**25. L1-10. The description does not state the usage limits; the screenshots show "3/3 free".** Guideline 2.3. Fix: "Free to use: up to 3 comparisons a day and 10 a month." in the description (section 4); crop the pill out of the redesigned frames. Owner: asc_metadata. Effort: minutes.

**26. L1-11. The description's privacy paragraph understates what goes to OpenAI.** Guideline 2.3. Notes AI PROCESSING and the live policy list links, preferences, country, language and area. Fix: section 4 privacy paragraph. Owner: asc_metadata. Effort: minutes.

**27. L1-09. "battery" is given as a priority you can choose; it is not one.** Guideline 2.3. CLIENT en.json:592-599 (re-checked). Fix: "like price, quality or durability" (section 4). Owner: asc_metadata. Effort: minutes.

**28. L4-05. The review account's "raised daily allowance" is unexplained and could suggest a paid tier.** Guideline 3.1.1. BACKEND usage_service.py:137-148 (premium tier set by SQL only). Fix: in Notes v3 and reply v3 ("MYEZ sells nothing; no user can buy a higher limit"). Owner: reply_text. Effort: minutes.

**29. L1-12 (merged P11). The Support URL redirects straight to mailto and has no help content or deletion steps.** Guideline 1.5 (met minimally). BACKEND landing/support.html:9, 196-211. Fix: remove the meta refresh; add a short EN + AR FAQ: deleting the account (Profile > gear > Delete account; email privacy@getmyez.com if you cannot sign in), daily and monthly limits, how prices are sourced and converted, contact email. Landing redeploy. Owner: backend_code. Effort: hours.

**30. L1-13 (merged L4-11). Copyright reads "2026 Hussain Aseeri"; the membership and live legal pages spell "Husain".** Guidelines 2.3, 5.2.1 (consistent developer identity). The owner kept "Hussain" for the App Review contact (ledger 05:04); the Copyright line is still open (OWNER_ACTIONS item 13). Fix: with the owner's yes, Copyright "2026 Husain Aseeri" to match the seller name shown on the store. Owner: owner_account_action. Effort: minutes.

**31. L1-16. Keyword "shopping" repeats the primary category.** Guideline 2.3.7 (polish). Fix: keywords in section 4 (97 chars). Owner: asc_metadata. Effort: minutes.

**32. L1-15 (merged L3-16, L4-10, P8). Age buckets start at 18-24 in a 13+ app; "how did you hear about us" is required while the policy calls it optional; the step-1 back chevron is inert.** Guidelines 5.1.1(v) (personal information only where core) and 2.3. CLIENT Step06Age.tsx:21 and OnboardingFlow.tsx:189-190 (both re-checked); BACKEND privacy_policy.md:37, 56, 61. Fix now: Notes v3 says age is optional; amend policy line 61 to say the onboarding asks for priorities, budget and brand attitude, and that the attribution answer becomes optional when the client change ships. After approval (OTA): make step 11 skippable, add a 13-17 band only if the backend cohort contract accepts it, hide the step-1 back chevron. Owner: client_code_ota_after_approval. Effort: hours.

**33. L1-08 (merged L5-15). Onboarding shows unattributed testimonial-style quotes under "By people like you" and claims "Trained by your peers".** Guidelines 2.3.1(a), 5.6. CLIENT Step01Welcome.tsx:84-104, QuoteRow.tsx:4, en.json:535-537, 631-637, 665; BACKEND cohort_service.py:14-16 (static 388-response survey). Fix: label as "Example picks" or remove; "Informed by a survey of GCC shoppers". Build 3 if cheap, else OTA after approval. Owner: client_code_ota_after_approval. Effort: minutes.

**34. L5-09. The first screen greets everyone with "Welcome back. Your advisor and credits are waiting." in an app that sells nothing.** Guideline 4.0 / 3.1.1 wording. CLIENT LoginScreen.tsx:408-415. Fix: "Sign in to MYEZ" / "Compare any two products in seconds."; replace "credits" with "free comparisons" (EN + AR). Owner: client_code_ota_after_approval. Effort: minutes.

**35. L5-13. The "Today's tailored pick" card shows raw English server strings ("OTHER", "Older"), also in Arabic; visible in screenshots.** Guideline 4.0. CLIENT HomeEditorialSections.tsx:98-108; BACKEND home_routes.py:480-517, 603-604. Fix: client formats time and category from catalog keys (OTA after approval); crop the card out of screenshots now. Owner: client_code_ota_after_approval. Effort: hours.

**36. L3-14. Cancelling the Google sheet shows "Google sign-in didn't complete".** Guideline 2.1(a). CLIENT authService.ts:872-876; @react-native-google-signin 16.1.2 returns {type:'cancelled'}. Fix in build 3: treat isCancelledResponse as a silent cancel. Owner: client_code_new_build. New build: yes. Effort: minutes.

**37. L3-15. Hard-coded English strings in the Arabic UI (sign-up validation, Change Password, "Matching to peers in ...").** Guideline 2.1(a) completeness. CLIENT RegisterScreen.tsx:182-205; ProfileScreen.tsx:256-258; Step13Anticipation.tsx:154; Step14Loading.tsx:185. Fix: move to existing en/ar keys (build 3 if cheap, else OTA). Owner: client_code_ota_after_approval. Effort: hours.

**38. L3-18. The pill reads "0/3 free" on the raised-tier review account; its fallback counter is per device.** CLIENT useComparisonCounter.ts; HomeScreen.tsx header. The Notes already explain the pill. Fix after approval: show today's remaining count; key the fallback by user id. Owner: client_code_ota_after_approval. Effort: hours.

**39. L5-14. Forgot Password shows raw error text and nothing on a timeout.** Guideline 4.0. CLIENT ForgotPasswordScreen.tsx:53; api.ts:1095, 1110-1123. Fix: map codes to catalog copy via errorCopy.ts. Owner: client_code_ota_after_approval. Effort: minutes.

**40. L5-08, L5-10, L5-11, L5-12. Auth-screen polish: Apple button below Google on Sign Up; typed "G" placeholder logo; fixed heights clip at large text sizes; hard-coded paddingTop 50.** HIG (Sign in with Apple prominence, Dynamic Type, safe areas); 4.8 itself is met. CLIENT RegisterScreen.tsx:402-446; LoginScreen.tsx:114-123, 557, 654-656, 706-711, 731-733; PaywallScreen.tsx:189; ResultsContent.tsx:622. Fix: mirror the sign-in order on Sign Up, official Google asset on its own row, minHeight and maxFontSizeMultiplier ~1.6, useSafeAreaInsets. Build 3 only if it does not delay it; these screens appear in the recording, so re-run the 20-second check after any change. Owner: client_code_new_build. New build: yes. Effort: hours.

**41. P6. Camera and photo purpose strings do not say photos leave the device.** Guideline 5.1.1(ii): purpose strings must "clearly and completely describe your use of the data". CLIENT locales/en.json:4-5, app.json:213, 221. Fix in build 3 (native strings): camera, "MYEZ uses the camera to photograph the two products you want to compare. The photos are sent to MYEZ and OpenAI to identify the products; MYEZ does not store them." Same shape for the library, plus Arabic. Owner: client_code_new_build. New build: yes. Effort: minutes.

**42. P7. The privacy manifest omits the "Other Purposes" the published App Privacy labels declare.** App Privacy consistency. CLIENT app.json:41-118; ASC facts line 24; BACKEND docs/privacy-data-inventory.md:29-43. Fix in build 3: add NSPrivacyCollectedDataTypePurposeOther to the five entries and the inventory together (nativeBundle.w37.test.ts deep-equals them). Owner: client_code_new_build. New build: yes. Effort: minutes.

**43. P9. Google Sign-In asks for offline access it never uses; logout and deletion never sign out of or revoke Google.** Guideline 5.1.1(iii). CLIENT authService.ts:844; no signOut/revokeAccess in src/. Fix: offlineAccess false; signOut on logout; revokeAccess on deletion for Google users (build 3 or OTA). Owner: client_code_ota_after_approval. Effort: minutes.

**44. P10. The user-chosen governorate is declared only as Other Data Types; Apple may class it as Coarse Location.** App Privacy completeness (uncertain). BACKEND extraction_service.py:2020-2025; ASC facts line 24. Fix: owner judgement; the conservative option is adding Coarse Location (App Functionality, Product Personalization, Other Purposes; linked; not tracking) and publishing. Owner: asc_metadata. Effort: minutes.

**45. L4-09. User-chosen display names reach other people with no content filter.** Guideline 1.2 (minimal surface). BACKEND referral_service.py:406, 455, 929-932. Fix: run display names through the existing blocklist and omni-moderation (content_safety_service.py) on save, fall back to "A friend". Owner: backend_code. Effort: hours.

**46. L4-12. The privacy policy names complaint authorities only for Bahrain and Saudi Arabia, though the app is in six GCC storefronts.** Legal polish (no App Review clause). BACKEND privacy_policy.md:127. Fix: counsel decides on "or the data protection authority of the country where you live" (EN + AR). Owner: backend_code. Effort: hours.

**47. L4-13. The result screen never says it is AI-written or that prices should be checked.** Guideline 5.6 adjacency. CLIENT ResultsContent.tsx:363-387; en.json has no such string. Fix after approval: one footer line "Written with AI from public sources. Check the price with the retailer before you buy." (EN + AR). Owner: client_code_ota_after_approval. Effort: minutes.

### Refuted or corrected sub-claims (kept out of the plan)

- L3-01 "the black cover stays up after leaving the auth screens": refuted for 8.0.10 (allowScreenCapture removes it).
- L3-01 2.1(a) "obvious technical problem" angle: does not apply to the reviewer's own run (the screen is not being captured).
- L3-04 headline "can appear for the very pair the Notes recommend": no run supports it; the 4.0 citation dropped.
- L3-05 4.8 citation: dropped (Sign in with Apple is offered).
- L4-01 lens fix wording "only where robots.txt allows" and "nothing is resold": both false; not used.
- P1 "no server-only fix" and the provider either/or: the client already has auth_provider; a policy sentence partly covers TN3194 step 2 now.
- P2 fallback "turn the U13 flag off": rejected (the fingerprint limits nothing).
- Lens conflict on "25+ retailers" (L1-07 vs a lens-5 checked item): unresolved; the fix removes the number either way.
- L1-04 vs L5-06 on the owner-review template: the live backend now rewrites verb leads ("Owners say it ..."), so frame 3 shows stale output; the frame still goes.

---

## 3. Build 1.0.0 (3): scope

Cut from eed0f628 plus only the changes below (if cut from a later main, re-run the truth check of the Notes and reply against that JavaScript first). Present the plan before implementation and gate RED to GREEN per the build orchestrator rules. Run npm ls before any EAS command and the FULL jest suite before the PR (source-scanning suites pin these screens).

Must:
- Remove usePreventScreenCapture from LoginScreen and RegisterScreen (plan item 1). Optionally ForgotPassword/ResetPassword with their pinned test updated.
- If the device gate fails for Google: hide the Google button on Login and Register (item 3).

Should (copy or small logic; none changes a flow the Notes describe):
- Drop the "even offline" tip; remove "25+" from the loader stage and tips (13).
- Country-step subtitle (14).
- Arabic step-2 reload resumes at step 3 (15).
- Change Password rule, friendly 422, hidden for social accounts (16).
- Camera denied: "Open Settings" (17).
- Google cancel is silent (36).
- Purpose strings EN + AR (41); privacy manifest Other Purposes (42).

Could (only if they do not delay the build): Apple token revocation client half, fail-soft (9); AI-consent withdrawal row (23); onboarding quote labels (33); "Welcome back ... credits" copy (34); auth-screen polish (40).

Not in build 3 (keeps the Notes valid): making step 11 skippable or adding an age band (32), the pill counter change (38). Anything shipped after approval goes by OTA only after approval.

After the build: upload, TestFlight, install, 20-second recording check, then select build (3) for version 1.0.0 in ASC.

---

## 4. App Store Connect edits that can be made today (exact text)

Proposed files: scratchpad/audit_synth/DESCRIPTION_v2_proposed.txt (2,079 characters, limit 4,000).

1. Description: replace the whole text with DESCRIPTION_v2_proposed.txt. Changes: links mentioned; "compile the specs with AI" (specs are AI-compiled, truth-check ruling ledger 02:41); price bullet (L1-02); priorities "price, quality or durability" (L1-09); share and invite bullet (L1-01); limits bullet (L1-10); "Supplement and medicine comparisons are general information, not medical advice; ask a pharmacist or doctor." (L4-03); privacy paragraph (L1-11). Keep the existing bullet characters. If the photo device check fails, delete the "Camera compare" bullet and "or photograph them" / "link or photograph" until it works. If P3 sharing is turned off, delete the sentence "OpenAI may use what we send and the replies it generates to evaluate and train its models."
2. Keywords: `prices,reviews,fragrance,perfume,phone,laptop,supplements,skincare,makeup,electronics,Bahrain,GCC` (97 characters).
3. App Review Information > Notes: replace NOTES_DRAFT_v2 (pasted 05:05) with Notes v3 (section 5). Variant B is true today; switch to A only after the backend image change ships.
4. Copyright (only with the owner's yes on the spelling): `2026 Husain Aseeri`.
5. Screenshots: replace all five with the approved redesigned set once section 7 is applied.
6. After the accounts exist: tick "Sign-in required"; the owner types account 1's user name and password.
7. After build 3 processes: select build 1.0.0 (3) for version 1.0.0.
8. No change needed: name, subtitle, promotional text, categories, age rating, licence, pricing, availability.
9. Optional, owner judgement: App Privacy Coarse Location (item 44).

---

## 5. Notes v3 and Reply v3

Full texts, measured (ASCII, LF; ASC counts each newline as one character):
- scratchpad/audit_synth/NOTES_v3_B_search_images.txt: 3,990 characters (use today).
- scratchpad/audit_synth/NOTES_v3_A_store_page_images.txt: 3,959 (only after the image change).
- scratchpad/audit_synth/REPLY_v3_B_search_images.txt: 3,985 (a 4,000 reply limit is UNVERIFIED; kept under it).
- scratchpad/audit_synth/REPLY_v3_A_store_page_images.txt: 3,966.
- Generator: scratchpad/audit_synth/build_texts.py.

Amendments relative to v2:

Notes
- PURPOSE: "MYEZ is a free shopping decision aid" becomes "a free shopping decision aid"; "attached to our 1.0.0 App Review reply" becomes "attached to our App Review reply".
- SIGN-IN: "it also holds History and preferences." becomes "it also holds History and the saved preferences each verdict uses."; the review-account sentences become "Review account: in the Sign-In Information fields. It has finished the questionnaire; we raised its daily allowance for review (MYEZ sells nothing; no user can buy a higher limit)."
- NEW ACCOUNT: "(to test sign-up and deletion; keep the review account)" becomes "(to test sign-up and deletion)"; "a password of 10+ characters" becomes "a 10+ character password"; "Create Account." becomes "Create Account (Invite code is optional)."; after "how you heard of us" add "; age is optional"; add "Choosing Arabic reloads the app once for right-to-left." before "New accounts:".
- HOW TO TEST 2: "The first comparison, camera or photo-picker use shows" becomes "The first comparison or photo use shows".
- REGIONS: "REGIONS: six storefronts (Bahrain, Kuwait, Oman, Qatar, Saudi Arabia, UAE), identical features. Typed and photo comparisons search Bahrain prices, shown in BHD whatever country the user picks; an international-only price is converted to BHD and labelled. Link uses the linked page's price."
- AI PROCESSING: "and the profile preferences, ... are sent to OpenAI to write the comparison. OpenAI may use" becomes "and the preferences, country, language and area named on the sheet go to OpenAI to write the comparison; OpenAI may use".
- SERVICES: "SERVICES: OpenAI; Supabase (database, sign-in); Sign in with Apple; Google Sign-In; Railway; Upstash; Serper; retailer sites, Firecrawl, Scrape.do; Expo (APNs push); Sentry. No payment, ad or analytics SDK."
- REGULATION (B): "REGULATION: not regulated; no sales, payments, marketplace or affiliate links; Terms: not medical, health or financial advice. No licence applies: no hosted, streamed or sold third-party media, no content partnerships; names only identify products; review praise is summarised (no quotes); ratings only if published. Images: publishing site or search-engine image server." (A ends "Images: the store page.")
- Last paragraph: "No purchases, subscriptions, ads, tracking, feed, comments, chat or public profiles, so no reporting or blocking flow. SHARE: a new result shares a text summary. A comparison opened from History opens an invite sheet: a link to it (the user can hide name, result, reasons) and an invite code. REFERRALS: when an invited friend signs up and runs a first comparison, the inviter gets 5 bonus comparisons for 7 days, max 3 friends per device; no cash value." (The daily-limit sentence is dropped for space.)

Reply
- Item 1: "build 1.0.0 (2)" becomes "build 1.0.0 (3)"; the last sentence becomes "MYEZ has no feed, comments, chat, public profiles or paid content, so there is no reporting, blocking or purchase flow. Share sends a text summary of a new result, or, from History, a link to that comparison plus the user's invite code; when an invited friend signs up and runs a first comparison, the sender gets 5 bonus comparisons for 7 days (at most 3 friends, no cash value)."
- Item 2: "It replaces the many searches needed to compare two products' specs, reviews and prices." becomes "It replaces many searches for specs, reviews and prices."
- Item 3: after "the app opens on the sign-in screen." add "An account is required because MYEZ is account-based: each verdict is personalised to the priorities and budget saved in it, History is kept per account, and the daily allowance covering the paid AI and search requests is per account."; the sign-in sentences become "Please sign in with the account in the Sign-In Information fields; we raised its daily limit for review (MYEZ sells nothing; no user can buy a higher limit)."; "so the review account stays usable" dropped; password wording "a 10+ character password"; compare step "MYEZ tab > Type > "iPhone 15" and "Samsung Galaxy S24" > Compare > "Agree and continue"."; the optional-sheet sentence dropped (it is in the Notes); "No email confirmation is needed." becomes "No email confirmation needed."
- Item 4: "OpenAI API (identifies products, extracts data, writes and moderates the comparison)"; "Upstash (cache)"; "retailer websites and store search, fetched by our servers, with Firecrawl and Scrape.do as fallbacks"; "Expo (updates, push via APNs)".
- Item 5: "typed and photo comparisons search Bahrain prices and show them in Bahraini Dinar (BHD) whatever country the user picks; an international-only price is converted to BHD and labelled."
- Item 6 (B): "6. Regulation and third-party material: MYEZ is not in a regulated industry. It has no sales, payments, marketplace or affiliate links; its Terms say it is not medical, financial or professional advice. No licence document applies: MYEZ hosts, streams and sells no third-party media and has no content partnerships. It shows product names only to identify products, retailer prices, AI-compiled specs, a review-praise summary (no quotes) and ratings only when a source publishes one. Images load from the publishing site or a search engine's image server. Owners may ask support@getmyez.com for removal." (A: "Images load from the store page that publishes them.")

Conditional edits
- Google fails the device gate and is hidden in build 3: delete "Google Sign-In; " from Notes SERVICES and reply item 4.
- Photo compare fails: reply item 1 "a photo comparison" becomes "a comparison of two product links"; rewrite Notes step 4 and remove "photographs" claims until fixed.
- Confirm email is ON: delete "No email confirmation needed." from both.
- The Arabic reload does not happen in the dry run: delete "Choosing Arabic reloads the app once for right-to-left."
- ENABLE_COMPARISON_ID_ECHO is ON in production: every result opens the invite sheet; change "a new result shares a text summary" accordingly.
- P3 sharing turned off: Notes AI PROCESSING drops "OpenAI may use inputs and outputs to evaluate and train models, as the sheet says."
- Second-camera fallback (only if the owner refuses build 3): reply item 1 starts "Video: attached. It was filmed with a second camera pointed at an iPhone running the latest iOS and the submitted build 1.0.0 (2) from TestFlight, because the sign-in and registration screens block iOS screen recording to protect passwords." and the Notes PURPOSE says "The video is attached".
- Never claim Sign in with Apple token revocation until it ships.

---

## 6. Owner steps (in order)

1. Account Holder: accept the updated Apple Developer Program License Agreement at developer.apple.com/account; confirm the ASC banner is gone and nothing is pending under Business > Agreements.
2. On the iPhone (latest iOS, build 1.0.0 (2) from TestFlight): start Screen Recording, open MYEZ, check whether "Welcome back." is black on the phone and in the clip, and whether the Email field still takes a tap. Report the result.
3. Device gate on build 2 with your own account: tap Continue with Google, Continue with Apple, and Scan > Open camera > photograph two products > Compare. Also pick Arabic in a fresh questionnaire (account 2) and note whether the app reloads. Report each result; nothing is sent until all pass or build 3 covers the failures.
4. Approve the build 1.0.0 (3) scope (section 3). After it reaches TestFlight, install it and repeat step 2: sign-in and Sign Up must be visible in the recording.
5. Supabase: Authentication > Email > "Confirm email" must be OFF. Send one Forgot Password email to a test account and confirm the link reaches a working reset page or screen.
6. Railway web variables, names only, in your own terminal (never pasted into chat): OPENAI_BASE_URL unset; FIRECRAWL_API_KEY + ENABLE_FIRECRAWL and SCRAPEDO_API_TOKEN + ENABLE_SCRAPEDO present; also whether ENABLE_COMPARISON_ID_ECHO is set.
7. Create review accounts 1 and 2 as in DEMO_ACCOUNTS_SQL.md section 1; finish the questionnaire; log out. Run checks A and B (expect 2 rows, preferences_completed true), then the tier raise C. Log out, sign in once with exactly the stored account-1 values, confirm the Main tabs, log out.
8. Decide D3 again in the light of guideline 5.1.2(i): keep OpenAI organisation data sharing ON (accept the risk) or turn it off (Claude then updates the description, policy, Terms and Notes).
9. Decide the Copyright spelling (recommended: the membership spelling).
10. Confirm, for reply item 6, that MYEZ has no content partnerships and that removal requests to support@getmyez.com will be honoured; decide whether the backend should stop using search-engine images (variant A) or keep them (variant B).
11. If Apple token revocation is in scope: create a Sign in with Apple key (.p8) for com.qaren.app and store the key, key ID and team ID as Railway secrets.
12. Approve the redesigned screenshot set after the section-7 changes; if you want the Arabic localization in this submission, take the Arabic captures (on build 3 if attached) and approve the Arabic listing texts after a truth check.
13. Say "yes, fill App Store Connect": Claude pastes Notes v3, the description, keywords and screenshots and selects build (3); you tick Sign-in required and type account 1's credentials.
14. Record the video on build 3 per RECORDING_SCRIPT_v2 (build number updated); trim; move it to the PC.
15. Say "yes, send": Claude warms the review pair within 2 h; you attach the video; Reply v3 is sent; "Resubmit to App Review". Claude re-warms every 12-24 h until a decision.
16. Before release (not blocking review): the written IP assignment or licence from the second team member; counsel on the Content Rights basis, complaint authorities and the under-18 guardian clause.

---

## 7. Screenshot redesign: truthful-claims guidance (Cal AI-style set)

Format the owner wants: white or near-white field, one short bold headline per slide, the real screen in a phone frame. Borrow the layout only (guideline 4.1(a): no copying another app's look, words or device art). Every frame is a real capture of the build attached for review (build 3 once attached; its shown screens are unchanged from build 2 unless a build-3 change touches them, in which case recapture). Crops and scaling of real pixels are fine; altering numbers or text is not.

Claims provable from the code (safe as headlines or sublines)
- "Two products. One clear pick." / "One clear verdict": winner, reasons, TOP MATCH (results screen; the subtitle already uses it).
- "Just type two names": Type mode (home.mode.*).
- "Or paste two links": Link mode.
- "Or snap a photo": Scan mode (camera, or two photos from the library) - only after the device photo check passes.
- "Pros and cons for both" / "Not just for the winner": results.accordion.prosConsLabel "Each product, both sides".
- "See where the runner-up wins": only on a capture where that section renders (it is conditional).
- "Prices in Bahraini Dinar": true; show a real BHD line as captured.
- "See how much data backs each pick": the "What we know" panel with Price/Reviews/Specs levels.
- "Picks for your priorities": saved priorities feed the verdict (extraction_service.py:1926-1950).
- "Your comparisons, saved in History": HistoryScreen.
- "English and Arabic, right to left": the interface only.
- "No ads. No tracking.": no ad SDK in package.json; NSPrivacyTracking false; no data type used to track.
- "Delete your account any time, in the app": EditProfileScreen deletion path.
- "Reviews, summed up": a synthesized praise summary with no quotes.

Claims NOT provable or not allowed (do not use)
- "Free" in a headline, eyebrow or badge (guideline 2.3.7: screenshots should not include prices or terms); also "unlimited". Put the limits in the description instead.
- Savings: "save", "shopped smarter", "BHD saved", any "this month" figure (an all-time sum of price gaps, not money saved).
- "Popular", "trending", "most compared": the list is curated by an admin. Use "Suggested".
- Retailer counts or reach: "25+ retailers", "every retailer", "across the GCC", "local prices", "live prices", "best price", "lowest price", "cheapest".
- "Owner reviews", "what owners say", "real reviews", "verified reviews", "what users say": the text is a synthesized summary.
- Star badges, laurels, "#1", "Editor's choice", user counts, "trusted by", press logos, testimonials: none exist (brand-new app, no ratings).
- "Trained by your peers", "real people": the cohort data is a static survey.
- "Offline", "instant", "in 30 seconds" or other timing claims (compares take 20-35 s).
- "Accurate", "unbiased", "expert", "AI-verified", "official specs": specs are AI-compiled and may come from training data.
- "Arabic verdicts" or any Arabic-language result text: write-ups are English only.
- "Never paid by sellers": code shows no affiliate links, but the business claim needs the owner's confirmation; prefer "No ads".
- Medical or health benefit claims for supplements.

Frame hygiene
- Crop out the "x/3 free" pill (slides 2, 3, 6 of the draft show it).
- Crop out the "Today's tailored pick" card (raw "OTHER"/"Older" strings and Tom Ford bottle photos in slides 2 and 3 of the draft).
- Do not use luxury-brand bottle photography or logos as hero art; brand names only as they appear small in the real UI. Prefer the Notes pair (iPhone 15 vs Samsung Galaxy S24), which completes reliably, so screenshots, Notes and recording agree.
- No truncated rows, clipped pills or values without units.

Review of the current Fable draft (_s79_screenshots/v4_6.9, the v4b state)
- Slide 1 "Two products. One clear pick." with the "BHD 6.77 less" magnifier: acceptable as a real capture; prefer the iPhone 15 vs Galaxy S24 result for the hero.
- Slide 2 "Just type two names" and slide 3 "Or snap a photo": crop above "Today's tailored pick" and remove the pill; slide 3 only after the photo check passes.
- Slide 4 "Pros and cons for both / Not just for the winner": acceptable.
- Slide 5 "Specs, side by side / The numbers that matter, in one table": the magnified row shows "10 | LONGEVITY | 6-8 hours" (a value without its unit); recapture on the electronics pair; consider the subline "Key specs, side by side".
- Slide 6 "FREE / Free. No ads. No tracking. / Popular comparisons, one tap away.": change to eyebrow "PRIVATE", headline "No ads. No tracking.", subline "Suggested comparisons, one tap away." - or better, use a History or Delete-account capture ("Your comparisons, saved" / "Delete your account any time").
- Arabic set (SCREENSHOTS_AR_PLAN.md and render_v4.py AR_SLIDES): drop the word for "Free" (majjani) from slide 6; replace "popular comparisons" (al-muqaranat al-sha'ia) with "suggested comparisons"; do not use the plan's slide 05 "what users say" (ra'y al-mustakhdimin) headline; the Arabic description must say write-ups are in English. An Arabic localization is optional; no clause requires it.

---

## 8. Unverified (not findings)

- Apple's exact 2026-10-13 wording (only the session-78 paraphrase exists), including question 6 and any "Prevent common issues" list.
- On-device behaviour of build 2: the black recording cover, whether it also swallows taps, Google and Apple sign-in, the photo compare, the Arabic reload (expo-updates enabled in the store build).
- Production flags: ENABLE_COMPARISON_ID_ECHO, ENABLE_SPECS_NO_FABRICATION, ENABLE_BH_GCC_CATALOG_SOURCES, ENABLE_ARABIC_VERDICT_OUTPUT, ENABLE_PASSWORD_RESET_DEEP_LINK, Supabase Confirm email, migration 043 applied.
- A 4,000-character limit on the Resolution Center reply.
- Whether the onboarding age enum accepts a 13-17 band on the backend.
- OpenAI's current data-sharing programme terms (decides the truthful P5 wording).
- Rights of retailers, Google (via Serper) and review platforms to automated access and display; trade-name and trademark clearance for MYEZ in the GCC.
- The real number of retailers queried per comparison.
