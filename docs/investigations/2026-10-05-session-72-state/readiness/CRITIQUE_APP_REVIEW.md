# CRITIQUE (lens: App Review) of LAUNCH_PUNCH_LIST.md

- Critic: critic-app-review (Opus, read-only). Written 2026-10-05 14:17-14:50 AST.
- Code: `C:/Users/SynAckITPC/Documents/AI/sc-s71-u13` at `845ece15f118a8e3e99c9778fab7985a96f19bb3` (clean; no git writes).
- Method: wrote an independent first-submission rejection checklist into `notes.md` BEFORE reading the list, then read the list, the runbook (sections 2/3/4/6/7), the session-71 state (section 0), the implementation plan and owner answers, the client and backend finder reports, and re-derived every App-Review-relevant claim in code. No pytest/jest/tsc run (read-only critique; no code changed).
- Web: official Apple pages only, no project data in any query (URLs in section 10).

## 1. Verdict: SOUND_WITH_CORRECTIONS

The punch list's hard stops, critical path and C1 units are broadly right for App Review. Its DONE rows that matter to a reviewer re-derive in code (section 3). It misses one reviewer-path cluster that is a real guideline problem and needs no owner input except a copy call, it misstates one decision consequence (D6), and it leaves out three Apple-account gates that sit on Hussain, not Ahmed. None of this moves the date more than a fraction of one loop if folded into existing steps.

Top corrections, ranked:
1. **AR-1 (high, MISSING).** The Share sheet promises a reward that does not exist ("+1 Deep Review credit now"; toast "Your next comparison goes 2x deeper on reviews"), shows a weekly counter for a lifetime cap, and renders a literal placeholder link `https://qaren.app/r/QR-XXXXXX`. It is reached from History -> any saved comparison -> Share. Guideline 2.3.1(a) (promoting a service the app does not offer) and 2.1(a) (placeholder text).
2. **AR-2 (medium, MISSING).** The listing description claims "photograph one and type the other"; the client requires two photos. Guideline 2.3.
3. **AR-3 (medium, MISSING).** The review notes say "(premium tier)" for a tier no user can buy or reach. That invites a 3.1.1 / 2.1 information request.
4. **AR-4 (medium, REFUTES D6).** D6 says the login wall has "Consequence: none for review". Guideline 5.1.1(v) says otherwise, and the runbook itself says guest mode "removes the 5.1.1(v) risk". The mitigation is the review-note sentence LISTING-TRUTH must keep.
5. **AR-6 / AR-7 (high if applicable, MISSING).** Territory choice drives the EU DSA trader declaration, and the Program License Agreement and membership must be current. Both are Account Holder (Hussain) actions and belong in step 7, not step 21.

## 2. Independent checklist (step 3) vs the list

Each item is from `notes.md` (written before reading the list). "List" = the line that covers it.

| Item (guideline / upload check) | List covers? | Status at 845ece15 | Evidence |
|---|---|---|---|
| ITMS-90683 purpose strings | B18 (processing email) | DONE: camera, photos, mic on both plugins, no Face ID string, AR strings in `locales/ar.json` | app.json:212-213, :220-221, :197; locales/en.json; locales/ar.json keys CFBundleDisplayName + 3 strings |
| ITMS-91053 required-reason APIs | B18 | DONE in app manifest: CA92.1, C617.1, 35F9.1, E174.1 | app.json:125-142 |
| ITMS-91061 SDK manifests | B18 | NOT VERIFIED (pods resolve at build); the processing email decides | package.json:18,22 (google-signin ^16.1.2, sentry ~7.2.0) |
| ITMS-90717 icon alpha | not listed | DONE: `assets/icon.png` 1024x1024 colour type 2 (RGB, no alpha); pixels are the MYEZ art | measured with the PNG IHDR; commit de66a25f (#279) |
| Xcode 26 / iOS 26 SDK (from 2026-04-28) | NOT LISTED | eas.json production has no `image` pin (eas.json:18-21); runbook section 7 says the SDK-54 image is Xcode 26.0 (2026-09-29, not re-verified) | AR-10 |
| Export compliance | B22/A3 | DONE `ITSAppUsesNonExemptEncryption: false` | app.json:145 |
| ATT not needed | B22 "Tracking = No" | DONE: no ad/attribution SDK, `NSPrivacyTracking false`, no `NSUserTrackingUsageDescription` | package.json:15-58; app.json:26 |
| 2.1 backend on, demo account | hard stops 1, 6; B17 | OPEN-AHMED (as listed) | - |
| 2.1(a) placeholder text | U-COPY (2 lines) | PARTLY: U-COPY misses the share-sheet placeholder | AR-1 |
| 2.3 metadata accuracy | LISTING-TRUTH | PARTLY: misses the camera claim and "premium tier" | AR-2, AR-3 |
| 2.3.1(a) features that do not exist | NOT LISTED | OPEN: Deep Review reward | AR-1 |
| 3.1.1 purchase wording | A3 limit sheet; U8 "Premium subscribers" | DONE in app (paywall keys have no price/trial/restore); OPEN in ToS:85 and the review notes | en.json:358-366; AR-3 |
| 4.8 login services | A3 (#269) | DONE: native Apple button wherever Google appears | runbook row 15; client report section 5 |
| 5.1.1(i) policy content incl. how to revoke consent | U8 | OPEN; U8 scope omits the revoke-consent path and the ToS:83-85 reward text | AR-13 |
| 5.1.1(iv) pre-permission screens | not listed | DONE: Step 17 "Maybe later"; AI sheet "Not now" | Step17Notifications.tsx:152-156; en.json:697-698 |
| 5.1.1(v) login wall | D6 | consequence misstated | AR-4 |
| 5.1.1(v) no forced personal data | not listed | DONE: age and gender have "Prefer not to say" | Step06Age.tsx:52-56; Step07Gender.tsx:55-59 |
| 5.1.1(v) in-app deletion | A3 | DONE (route + UI, no password re-entry so SIWA users can delete; service-role RPC so 037's revoke does not break it). Complete erasure needs 043 | EditProfileScreen.tsx:125-155; database_service.py:392-396; AR-14 |
| SIWA token revocation | C3 U11 | Apple wording re-read today: "should" | section 10 URL |
| 5.1.2(i) third-party AI consent | A3 #274; U3b | DONE before every Home dispatch; quiz path is zero-LLM; no deep link bypasses Home | HomeScreen.tsx:373, :534, :726, :732, :737, :779; referral_service.py:463-499; linking.ts:46-84 |
| 1.4.1 medical information (supplements) | NOT LISTED | OPEN: no disclaimer anywhere | AR-5 |
| Age rating answers | D9 | consequence partly stated | section 8 |
| Unrestricted web access = No | runbook section 6 | DONE: no webview package; links leave via `Linking.openURL` | package.json; ResultsScreen.tsx (`openRatingSource`) |
| Custom rating prompt | not listed | none (0 hits for StoreReview/requestReview) | grep |
| Screenshot blockers | B20 | `usePreventScreenCapture` only on the four auth screens | LoginScreen.tsx:194 and peers |
| Clipboard read on mount | NOT LISTED | iOS paste alert on Register | AR-8 |
| Territories / DSA trader | NOT LISTED | OPEN-AHMED | AR-6 |
| Agreements / membership current | NOT LISTED | NOT VERIFIED | AR-7 |
| Content Rights / 5.2.2 third-party content | NOT LISTED | OPEN | AR-12 |
| Fabricated ratings | not listed | checked and FINE: both payload product arrays null `rating` when `rating_derived` | response_builder.py:1580-1585 sets; ~:1916-1919 and ~:1988-1990 null it |

## 3. DONE rows re-derived (A3 and others)

| List row | Re-derived? | Evidence at 845ece15 |
|---|---|---|
| MYEZ launcher icon + launch screen (#279) | YES | icon.png 1024 RGB (no alpha), MYEZ pixels viewed; last commit de66a25f |
| supportsTablet false, mic strings, no Face ID, AR localization (#254) | YES | app.json:22, :197, :203-204, :212-213, :220-221; locales/ar.json carries all three purpose strings + display name |
| 13 certificate pins (#253) | YES | 13 unique 44-char SPKI strings in certificatePinning.ts |
| Honest limit sheet (#255) | YES | en.json:358-366 paywall keys: no price, trial, restore; PaywallScreen.tsx grep for BHD/trial/restore/subscribe/upgrade/price = 0 |
| AI consent sheet naming OpenAI (#274) | YES | en.json:694-698; gate sites listed in section 2 |
| Account deletion route (#290, #310) | YES (route + UI); erasure completeness depends on 043 | auth_routes.py:1165-1181; EditProfileScreen.tsx:125-155; auth_service.py:1008-1023 |
| Export compliance | YES | app.json:145 |
| U13 active | not re-derived (orchestrator measurement, 2026-10-05) | - |
| Camera 401 retry (#313), in-app mark (#288/#307), landing hand-off (#273), pip-audit (ci.yml:213-216) | NOT re-derived (outside the App Review lens) | - |

## 4. Refuted or corrected claims

| Line | Claim | What the code or source shows |
|---|---|---|
| A, line 27 | "Every Claude unit that needed no owner input has merged" | False. The list's own A2 (P1-P4) names six units that need no input and are unmerged: DOCS-CONFIG, BE-HARNESS, OBS, COST-METER, DEVICE-PURGE, SSRF. AR-1, AR-2 and AR-8 need only a copy call. |
| D6, line 304 | "Consequence: none for review" | Guideline 5.1.1(v), re-read today: "If your app doesn't include significant account-based features, let people use it without a login." The runbook section 3B says D6 guest mode "removes the 5.1.1(v) risk". The app gates everything behind Auth (App.tsx:365-371). The residual risk is real. The mitigation is the runbook section 6 review-note sentence "Sign-in is required because the account holds saved comparison history, personalization preferences and a per-account usage quota." |
| E3, line 357 | SIWA reviewer gets "3 lifetime compares, then the limit sheet" | usage_service.py:138-142: free = lifetime_free 3 + daily 3 + monthly 10. The client gate (useComparisonCounter.ts:76-82) allows a compare while daily and monthly remain. So it is 3 per day (reset 00:00 UTC), up to 10 a month. Within one review day the effect is the same 3. |
| F, line 388 | Screenshot sizes NOT VERIFIED against the live ASC page | Verified today: 6.9" accepts 1260x2736, 1290x2796, 1320x2868. 6.5" accepts 1284x2778, 1242x2688. 1-10 screenshots. 6.5" is required only when 6.9" is absent. B20 is correct. |
| F, line 406 | SIWA revocation wording not re-read | Re-read today: "Apps that support Sign in with Apple should use the Sign in with Apple REST API to revoke user tokens." G8 and U11 stand. |
| G9 | Age Assurance "not settled by evidence" | Apple's definition (re-read today) is "declared age range API; age estimation capabilities; age verification via government-issued passport, drivers license, national ID, or other means". A self-attested 13+ checkbox is none of these, so D9=A ("No") follows the official definition. |
| A hard stop 3 | "Each one alone blocks Submit" | App Review cannot observe whether a toggle routes anything. Row 3 is a 5.1.2 truth defect (high), not a submission gate. It stays necessary because U8 cannot describe the toggle truthfully. Keep the unit and correct the framing. |
| C1 U-COPY | `ResultsContent.tsx:139` | The `results.price.pending` call is at ResultsContent.tsx:140 (trivial). |
| A1 step 18 / B18 | The processing email is checked for ITMS-90683 / 91053 / 91061 | It omits Apple's 2026-04-28 rule: "Apps uploaded to App Store Connect must be built with Xcode 26 or later using an SDK for iOS 26". eas.json:18-21 has no `image`. See AR-10. |

## 5. Missing rows (schema: id | title | status | launch_severity | evidence | next_action)

| id | title | status | launch_severity | evidence | next_action |
|---|---|---|---|---|---|
| AR-1 | Share sheet advertises a non-existent "Deep Review" reward, a false "2x deeper" toast, a "this week" counter for a lifetime cap, and a literal placeholder link `https://qaren.app/r/QR-XXXXXX` | OPEN-BOTH | high | ShareBottomSheet.tsx:242-265 (reward block, unconditional), :141-145 + :320-324 (placeholder preview rendered); ResultsScreen.tsx:436, :526, :546-548 (the sheet opens whenever `comparison_id` exists = every History re-open), :958-968 (toast + `used: 3 - lifetimeRemaining, total: 3` under "this week"); en.json:422-424, :448-449, :489, :511; referral_service.py:336-345 grants `deep_review_credits`, and nothing in app/, scripts/ or migrations/ ever sets `consumed_at` on them (usage_service.py:600-607 reads `referral_redemptions`, a different table); terms_of_service.md:83-85 promises the credit. Guideline 2.3.1(a): "promoting content or services that it does not actually offer"; 2.1(a) placeholder text | Ahmed: decision SHARE. Claude: S client copy unit riding U-COPY (step 11): remove the "+1 Deep Review" line, the toast claim and the "this week" wording; show no placeholder URL in the preview; keep "+5 comparisons" only with wording true to Loop 2 (friend's first signed-in compare). U8 drops ToS:85. Must merge before step 15 |
| AR-2 | Listing claim "photograph one and type the other" is false | OPEN-CLAUDE | medium | ScanCameraScreen.tsx:288-292 (`onCompare` returns unless 2 photos); HomeScreen.tsx:684-705 (gallery needs 2, else an Alert); runbook section 6 description line 340. Resolves the backend finder's NOT VERIFIED "client half" | Claude: LISTING-TRUTH drops the clause (EN + AR) |
| AR-3 | Review notes call the demo account "(premium tier)", a tier with no purchase or user path | OPEN-CLAUDE | medium | runbook section 6 lines 322, 364; usage_service.py:144-148 (premium = 10/day, 70/month, set only by a DB edit per B17); no purchase UI (en.json paywall keys) | Claude (LISTING-TRUTH): "This review account has a raised daily limit so testing is not interrupted. MYEZ has no paid tier and no in-app purchases; all users get the same features." Keep "This version sells no subscriptions or in-app purchases." |
| AR-4 | 5.1.1(v) login wall: residual rejection risk, absent from E and misstated in D6 | OPEN-AHMED (accept) + OPEN-CLAUDE (notes) | medium | App.tsx:365-371; guideline text re-read today; runbook section 3B D6 | Claude: LISTING-TRUTH must keep the "Sign-in is required because ..." sentence verbatim. Add E risk "5.1.1(v) login required". D6 stays A with the risk stated |
| AR-5 | Supplement and OTC comparisons carry no "not medical advice" line; one warm-up pair is a supplement pair | OPEN-BOTH | medium | en.json: 0 hits for medical/doctor/pharmacist/consult; prompt_personalities.py:24 ("Like a pharmacist explaining supplement differences"); runbook section 3E pair "HealthAid Vitamin D3 / NOW Foods Vitamin D-3"; ToS:52 generic line sits in a DRAFT doc. Guideline 1.4.1 ("greater scrutiny") | Ahmed: decision MED. Claude: an XS EN+AR line on supplements results (rides U-COPY); a U8 health clause; age questionnaire "Medical or Treatment Information = Infrequent" (13+) |
| AR-6 | Availability territories and the EU DSA trader status are unplanned | OPEN-AHMED (+Hussain) | high if EU storefronts are selected; none if GCC-only | Apple: since 2024-10-16 trader status is required "to submit new apps ... for distribution in the European Union"; since 2025-02-17 apps without it are removed from the EU. A trader's address, phone and email are shown on EU product pages | Ahmed: decision TERR (A rec: GCC storefronts (+US optional) for 1.0, no EU). B: Hussain declares and verifies trader status in step 7 |
| AR-7 | Program License Agreement acceptance and active membership are unchecked | OPEN-AHMED (Hussain) | high if pending (record creation and upload are blocked); NOT VERIFIED | none of steps 7/18/21 mention it; the team is Hussain's Individual account | Hussain: open developer.apple.com/account and ASC Business at the start of step 7; accept pending agreements; confirm the renewal date |
| AR-8 | Register reads the clipboard on mount, so iOS shows a system "Allow Paste" alert to a reviewer who registers by email; the Worker that would copy a code is not deployed (`idTBD`) | OPEN-CLAUDE | low | RegisterScreen.tsx:101-108; clipboardFallbackService.ts:26-33; cloudflare-workers/qaren-redirect/src/index.ts:29 (`idTBD`, per list B24) | Ahmed: decision CLIP (A rec: drop the read for 1.0). Claude: XS, rides U-COPY |
| AR-10 | Upload-time SDK rule (Xcode 26 / iOS 26 SDK since 2026-04-28) is not on the checklist; Face ID purpose string is the one 90683 candidate not re-checked | OPEN-AHMED (read the build log) | low | eas.json:18-21 (no `image`); Apple upcoming-requirements page; app.json:197 `faceIDPermission:false` (whether ExpoSecureStore links LocalAuthentication is NOT VERIFIED) | Ahmed: in B16/B18 read the Xcode version in the EAS build log. Claude: if the processing email cites a missing purpose string, add an honest string in a hotfix build |
| AR-12 | ASC "Content Rights" (third-party content: retailer prices, product images, review summaries) and 5.2.2 readiness are not on the listing checklist | OPEN-BOTH | low | runbook section 6 field table has no Content Rights row; prices and images come from retailer pages and search APIs (CLAUDE.md price/image pipelines) | Ahmed: answer Content Rights in step 21. Claude: one review-note line on data sources (public retailer pages and search results; each price links to the retailer) |
| AR-13 | U8 scope omits two 5.1.1(i) items: how a user revokes AI consent (the U3b control) and the referral-reward text (ToS:83-85) | OPEN-CLAUDE | medium | punch list C1 U8 scope; guideline 5.1.1(i) ("how a user can revoke consent"); terms_of_service.md:83-85 | Claude: add both to the U8 spec; U8 waits on U3b's control design (section 7) |
| AR-14 | With 043 unapplied, deletion falls short of Apple's own deletion wording, not only of the policy text | OPEN-AHMED | high if M043=B | Apple page: "Offer to delete the entire account record, along with associated personal data"; list D M043 B consequence (FK branch B keeps email, name, demographics) | Ahmed: M043=A. State the Apple wording as the B consequence |

## 6. Over-scoping (MUST or blocker that does not block)

- **U-SPLASH (conditional MUST) + SPL=A (rec).** A short white flash between the launch screen and the JS splash is not an App Review rejection reason. SPL=A adds a native unit and one more preview build (about 1 day) to the critical path. Recommend SPL=B for 1.0 unless the flash is long or jarring; fix it in 1.0.1.
- **U-SNT (conditional MUST).** Mobile Sentry is ops safety, not a review gate. Keep it high, but it should not gate step 18 (the probe is OTA-capable after submission).
- **U-CANARY (MUST).** Under the recommended CAN=A it changes no binary byte: only the features.ts:26-29 comment ("MUST drop back to 10"), CLAUDE.md and the runbook. It should not gate step 15.
- **BE-HARNESS "MUST-before-production-build".** The build does not depend on it; steps 8 and 19 do. Retier it "MUST before submission".
- **Hard stop 3.** See section 4: high, not a submission gate.

## 7. Critical-path dependency defects

1. **Step 9 (U8)** must also wait on step 10's design (the U3b consent-withdrawal control the policy must describe, AR-13) and on decision SHARE (ToS:83-85).
2. **Step 7** must carry the Account Holder gates: agreements and membership (AR-7), and the DSA trader declaration and verification if EU is in scope (AR-6). Step 21 cannot do them: only Hussain can.
3. **Step 17 (demo accounts)** depends on 2/8 as well as 3/6. B17's own check is "a signed-in compare returns a real verdict", and B20 needs 3+ History entries.
4. **Step 18's TestFlight smoke "on the exact binary"** needs a funded backend: add 8.
5. **AR-1, AR-5 and AR-8 copy** join step 11 and must merge before step 15. The SHARE, MED and CLIP decisions join step 1.
6. **Step 12 (LISTING-TRUTH)** must absorb AR-2 and AR-3 and keep the 5.1.1(v) sentence (AR-4).

## 8. Decisions: consequences the list did not state

- **D5=A.** (a) The App Store "Seller" line shows Hussain's legal name. (b) With EU distribution and trader status, Hussain's address, phone and email are published on EU product pages. (c) A later move to an organization account is an App Transfer, and Sign in with Apple user identifiers are team-scoped, so existing SIWA users need Apple's transfer-identifier migration. (c) is from knowledge, NOT VERIFIED today.
- **D6=A.** Residual 5.1.1(v) risk (AR-4), not "none".
- **D8=A.** OpenAI's rate-limit tier follows cumulative paid amount and days since first payment. That source was not fetched (non-Apple), so this is NOT VERIFIED. A small prepayment made in submission week can leave the account at Tier 1, which is E1's modelled ceiling. Fund early enough to reach the next tier before review.
- **D9=A.** "Medical or Treatment Information: Infrequent" already yields 13+, so the override may be redundant. "Frequent" yields 16+ and, in EU/UK/US storefronts, forces the regulated-medical-device declaration. Category Shopping (not Health & Fitness or Medical) avoids it. Supplements make "None" a questionable answer (AR-5).
- **M043=B.** Fails Apple's "entire account record, along with associated personal data" (AR-14), not only the policy wording.
- **DEMO=A.** Premium is 10/day and 70/month (usage_service.py:144-148), so two accounts give the review team 20 compares a day. Never call it "premium" in the notes (AR-3).
- **SPL=A.** Over-scoped for review (section 6).
- **DNS=B.** The support page lists support@qaren.app (landing/support.html:7, :9, :199, :204, :207), so mail routing (L4) must still be verified. The share sheet still prints a qaren.app link (AR-1).
- **GOO=A.** Any account created with Google cannot sign in on 1.0 (likely none since session 54). No 4.8 effect, because Apple sign-in stays.
- **New decisions to add:** SHARE (AR-1; A rec: remove the Deep Review claims for 1.0), MED (AR-5; A rec: a disclaimer line + an "Infrequent" answer), TERR (AR-6; A rec: GCC-only for 1.0), CLIP (AR-8; A rec: drop the clipboard read).

## 9. Rejection risks to add to E (ranked into the existing list)

- After E1: **Share sheet advertises a reward that does not exist and shows a placeholder link** (AR-1), until fixed.
- After E3: **5.1.1(v) login required** (AR-4). The note sentence is the mitigation.
- After E4: **"(premium tier)" in the review notes** (AR-3); **camera claim** (AR-2).
- After E5: **1.4.1 supplement verdicts without a disclaimer** (AR-5).

## 10. Sources and NOT VERIFIED

Official pages read today (2026-10-05):
- https://developer.apple.com/app-store/review/guidelines/ (2.1(a), 2.3.1(a), 2.5.2, 3.1.1, 3.2.2(x), 4.8, 5.1.1(iv)/(v), 5.1.2(i), 1.4.1; the page shows no "last updated" date)
- https://developer.apple.com/news/upcoming-requirements/ (Xcode 26 / iOS 26 SDK from 2026-04-28; iOS 13 minimum from 2026-09-09; age-rating answers by 2026-01-31)
- https://developer.apple.com/news/upcoming-requirements/?id=10162024a and https://developer.apple.com/news/?id=einwn76m (DSA trader status, via search result summaries)
- https://developer.apple.com/support/offering-account-deletion-in-your-app/ (entire account record; SIWA "should" revoke)
- https://developer.apple.com/help/app-store-connect/reference/age-ratings-values-and-definitions/ (Medical/Treatment Infrequent 13+, Frequent 16+; Age Assurance definition; no AI question)
- https://developer.apple.com/help/app-store-connect/manage-app-information/declare-regulated-medical-device-status/ (Health & Fitness/Medical category or "Frequent" medical, EU/UK/US)
- https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/ (sizes in section 4)

NOT VERIFIED by this critic:
- ITMS-91061 pod manifests (GoogleSignIn and dependencies, Sentry): decided at upload.
- The EAS default image's Xcode version today.
- Whether ExpoSecureStore links LocalAuthentication (the Face ID 90683 contingency).
- Whether a live out-of-band DB function consumes `deep_review_credits`. The repo has none, and no compare path reads the table.
- OpenAI tier rules (D8); SIWA team transfer (D5c).
- Agreements and membership state (AR-7).
- No test was run.

## Files written

- `critic-app-review/notes.md`
- `critic-app-review/CRITIQUE.md` (this file)

sha256 values are in the structured output.
