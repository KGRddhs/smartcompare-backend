# MYEZ 1.0.0: App Store Connect submission packet (session 76, 2026-10-10)

iOS only. Bundle `com.qaren.app`, EAS project owner `kersher2` (projectId `387a4fcb-76f6-4857-a2fb-39482ca4bd40`), Apple team `8K562M549D` (Hussain Aseeri, Individual). Source: repo main `a8f4552b`. Identifiers stay `qaren`; the brand is MYEZ / ميّز (D12 = A, D13 = A).

Tags: **VERIFIED (URL)** = read today on that official page; **VERIFIED (repo)** = read at main `a8f4552b` (file:line); **UNVERIFIED** = not confirmed today (the reason is given). Every field length below was measured with `measure.py` (Python `len` = characters, `.encode("utf-8")` = bytes); the full table is in section 12.

## 0. Read this first

What the orchestrator can finish in App Store Connect TODAY, and what stays blocked:

| Step | Today? | Why |
|---|---|---|
| Section 1 portal checks, section 2 New App, section 3 App Information, section 4 App Privacy answers (without the Privacy Policy URL), section 7 screenshot folders, section 8 pricing and availability | yes | no dependency on the build or on PR #330 |
| Section 5 version text, section 6 review information | yes, as a draft | the copyright needs L1; the demo accounts must exist first |
| Privacy Policy URL (App Privacy -> Privacy Policy -> Edit) | **no** | PR #330 is not merged and still carries placeholders; its HEAD `3533e860` `landing/privacy.html:246` still says "we have not opted in", which is false under D3 = C (ruling OA2). The URL is pasted only after the OA2 fork lands in #330, #330 merges and the landing redeploys |
| Build upload and "Add for Review" | **no** | UB-R4: no store build before PR #330 is live; canary 7a FAILED with every FANOUT flag OFF (`docs/investigations/2026-10-09-session-75-state/canary/canary7a.json`); signing needs the Account Holder |

Decisions that change this packet (VERIFIED (repo) `docs/investigations/2026-10-08-session-74-state/specs/DECISIONS_ACCEPTED_2026-10-08.md:6-13`, meanings in `docs/investigations/2026-10-05-session-72-state/readiness/LAUNCH_PUNCH_LIST.md:262-332`):

- **D11 = B: English only for 1.0.** The ar-SA localization is NOT added in 1.0 (no native-review dependency). The Arabic blocks are kept, measured and corrected, in Appendix A, marked HOLD. If the owner reverses D11 today, Appendix A is paste-ready except for the native review.
- D5 = A (Hussain as an individual publisher), D9 = A (honest questionnaire, Override to 13+, Age Assurance No), DEMO = A (two accounts with a raised limit; the review notes never say "premium"), TERR = A (GCC storefronts only), D3 = C (OpenAI organisation data sharing ON, disclosed; OA2: "used to train AI models" = YES for the comparison inputs; Tracking = No), SHARE / MED / CLIP applied by CLIENT-TRUTH (#334).

Corrections to the session-69 runbook section 6 text that this packet applies (each checked against code or a later ruling):

| Runbook text | Why it changed | Source |
|---|---|---|
| "when a price is estimated ... we say so"; promo "we always show how confident we are"; notes "some are labelled estimated" | The client never labels an estimated price; it hides the Price pill when any price is estimated. The confidence pills render only when `scoring_v2.confidence_legs` exists | VERIFIED (repo) `SmartCompareApp/src/services/sourceMethod.ts:1-15, :37-41`; `src/components/results/ResultsContent.tsx:517`; finding BE-03 (`2026-10-05-session-72-state/readiness/READINESS_BACKEND.md:147`) |
| "Prices from stores serving Bahrain, Saudi Arabia, the UAE, Kuwait, Qatar and Oman" | Results use the Bahrain market (BHD) only | BE-09 (`READINESS_BACKEND.md:153`); inventory "Not collected" (`docs/privacy-data-inventory.md`, region hard-coded `'bahrain'`) |
| "Available in English and Arabic" | The interface is bilingual; verdict, spec and review prose stays English (`ENABLE_ARABIC_VERDICT_OUTPUT` dark) | BE-08 (`READINESS_BACKEND.md:152`) |
| "photograph one and type the other" | Not verified in the client | `LAUNCH_PUNCH_LIST.md` section F |
| "Sign in with Apple and Google are also available" | Google sign-in unverified since session 54 (GOO = A: hide it if the preview build fails) | BE-04 (`READINESS_BACKEND.md:148`) |
| "Your searches and photos are processed by OpenAI" only | D3 = C: OpenAI may use the inputs and outputs to evaluate and train its models; the consent sheet says so | VERIFIED (repo) `SmartCompareApp/src/i18n/en.json` key `aiConsent.body`; ruling OA2 |
| "We don't sell your data" | Dropped from the listing: the organisation receives complimentary daily OpenAI tokens while data sharing is on (OA2), and whether that is a "sale" under any applicable law is a legal question nobody has answered. The listing is safer silent; the PR #330 policy line 192 still says "We do not sell" (legal item, section 11) | OA2 (`FABLE_RULINGS_S74_OPENAI.md`); sc-s70-u4b `landing/privacy.html:192` |
| "delete your account and its data" | Full erasure is true only after migration 043 is applied (M043 = A, not yet run) | `AHMED_TASKS_TO_SUBMIT.md` section 3 |
| "(premium tier)" in the notes; deletion path "gear icon -> Edit profile -> Delete account" | DEMO rule: never "premium"; the gear opens Edit Profile directly | `AHMED_TASKS_TO_SUBMIT.md` 7.3; VERIFIED (repo) `SmartCompareApp/src/screens/ProfileScreen.tsx:333-342`, `src/screens/EditProfileScreen.tsx:266-280` |

---

## 1. Developer portal prerequisites (developer.apple.com/account, then App Store Connect)

### 1.1 Who must be signed in

- The Apple team `8K562M549D` is an **Individual** membership (runbook section 1). For Individual accounts "only the Account Holder role can generate app signing credentials" (distribution certificate, provisioning profile, push key). **VERIFIED** https://docs.expo.dev/app-signing/apple-developer-program-roles-and-permissions/
- A new app record cannot be added "until the Account Holder signs the latest agreement in the Business section". **VERIFIED** https://developer.apple.com/help/app-store-connect/create-an-app-record/add-a-new-app
- API access is requested by the Account Holder; a Team key needs Account Holder or Admin. **VERIFIED** https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-api
- **First check (orchestrator, in the browser):** App Store Connect -> Users and Access -> the signed-in person's role. If it is not Account Holder, step 1.3 (request access), the signing step `eas credentials` (section 9.3) and the agreement need Hussain. UNVERIFIED today: who is signed in ("im logged in apple developer" does not say which Apple ID).

### 1.2 App ID `com.qaren.app` and its capabilities

What the app declares (VERIFIED (repo) `SmartCompareApp/app.json`):

| Capability | Declared by | Entitlement it generates |
|---|---|---|
| Sign in with Apple | `ios.usesAppleSignIn: true` + plugin `expo-apple-authentication` | `com.apple.developer.applesignin` = `["Default"]` (VERIFIED locally: `sc-s70-u4b/SmartCompareApp/node_modules/expo-apple-authentication/plugin/build/withAppleAuthIOS.js:23`) |
| Associated Domains | `ios.associatedDomains: ["applinks:qaren.app"]` | `com.apple.developer.associated-domains` (`@expo/config-plugins/build/ios/Entitlements.js`) |
| Push Notifications | plugin `expo-notifications` (0.32.17) | `aps-environment` (VERIFIED locally: `expo-notifications/plugin/build/withNotificationsIOS.js:11-12`) |

- **EAS syncs these.** "EAS Build automatically synchronizes capabilities on the Apple Developer Console" with the entitlements when `eas build` runs; Sign in with Apple, Associated Domains and Push Notifications are all in the supported list; a capability enabled remotely but missing locally is disabled; opt-out `EXPO_NO_CAPABILITY_SYNC=1`. **VERIFIED** https://docs.expo.dev/build-reference/ios-capabilities/ . So nothing needs ticking by hand on the App ID; do NOT set `EXPO_NO_CAPABILITY_SYNC`.
- The App ID itself very likely exists already (internal preview builds were signed for this bundle; the AASA appID is `8K562M549D.com.qaren.app`, runbook section 7). UNVERIFIED in the portal today: check Certificates, Identifiers & Profiles -> Identifiers for `com.qaren.app`. If it is missing, the New App dialog cannot offer it: register it there (+ -> App IDs -> App -> Explicit -> `com.qaren.app`, description `MYEZ`), capabilities can be left to the EAS sync. (UI path UNVERIFIED; the help page does not cover it.)
- APNs key: "You can have a maximum of 2 APN keys"; "Push notification keys do not expire". **VERIFIED** https://docs.expo.dev/app-signing/app-credentials/ . `eas credentials` offers to create or reuse one (answer yes, runbook 3C4).
- Distribution certificate: "You may only have one distribution certificate associated with your Apple Developer account" (same URL, VERIFIED); the runbook records the existing one as valid to May 2027 (UNVERIFIED today): reuse it.

### 1.3 App Store Connect API key (Team key)

1. App Store Connect -> **Users and Access** -> **Integrations** (opens on App Store Connect API) -> **Request Access** (Account Holder only; Apple reviews the request "on a case-by-case basis"). **VERIFIED** https://developer.apple.com/help/app-store-connect/get-started/app-store-connect-api
2. **Team Keys** -> **Generate API Key** (or + if one exists) -> name `MYEZ EAS submit` -> **Access**: `Admin` (runbook 3C1; a narrower role such as App Manager may be enough for upload, UNVERIFIED) -> **Generate**. Team keys apply to all apps. **VERIFIED** (same URL).
3. **Download the `.p8` once.** Apple: "API keys are private and can only be downloaded once" (stated on that page for individual keys; the runbook and the API docs say the same for team keys, UNVERIFIED for team keys today). Store it OUTSIDE the repo (e.g. `C:\Users\<user>\secure\AuthKey_<KEYID>.p8`); `*.p8` is gitignored anyway. Never paste it into chat, never commit it.
4. Record the **Key ID** (keys table) and the **Issuer ID** (shown above the keys list). Location UNVERIFIED today (the Apple doc page renders client-side and could not be read); runbook 3C1 says the same. Neither goes into chat; they go into `eas credentials` (section 9) or a local env file.
5. Since eas-cli 24.8.0 an **individual** key is also accepted for submissions ("Accept individual App Store Connect API keys for submissions, TestFlight setup, and metadata"). **VERIFIED** https://github.com/expo/eas-cli/releases . The Team key stays the recommendation (it does not die with one user's access).

### 1.4 Sign in with Apple key (optional, U11 = A: after launch)

Not needed for 1.0 (U11 = A). Recorded so nobody creates it today.

---

## 2. New App form (Apps -> + -> New App)

Required role: Account Holder, App Manager or Admin. **VERIFIED** https://developer.apple.com/help/app-store-connect/create-an-app-record/add-a-new-app

| Field | Paste | Limit / rule | Measured |
|---|---|---|---|
| Platforms | `iOS` | - | - |
| Name | see below | 2-30 characters (VERIFIED https://developer.apple.com/help/app-store-connect/reference/app-information/app-information); guideline 2.3.7 "App names must be limited to 30 characters" (VERIFIED https://developer.apple.com/app-store/review/guidelines/) | 20 chars |
| Primary Language | `English (U.S.)` | changeable later ("You can change the primary language at any time", app-information page, VERIFIED). Choice = the eas-cli submit default `en-US` (VERIFIED https://docs.expo.dev/eas/json/) | - |
| Bundle ID | `com.qaren.app` (pick from the dropdown) | "You can't change this property after you upload a build" (app-information page, VERIFIED) | - |
| SKU | `qaren-ios` | letters, numbers, hyphens, periods, underscores, not starting with - . _ ; "You can't change the SKU after you add the app" (VERIFIED, app-information page) | 9 chars, valid |
| User Access | `Full Access` | Limited Access restricts users; Account Holder / Admin see all apps anyway (VERIFIED, add-a-new-app page) | - |

Name (EN, primary): <!-- field:EN_NAME -->
```
MYEZ — Compare Smart
```
20 characters / 22 bytes (the dash is U+2014 EM DASH, as in runbook section 6). If the em dash is unwanted, the owner-task-list spelling is <!-- field:EN_NAME_ALT_HYPHEN --> `MYEZ - Compare Smart` (20 / 20). If the name is taken, fall back to <!-- field:EN_NAME_FALLBACK --> `MYEZ` (4 / 4). A name is unique "per localization"; if another developer holds it, Apple's trademark claim route applies (VERIFIED, add-a-new-app FAQ).

AR name under ar-SA: HOLD per D11 = B (Appendix A: `ميّز - مقارنة المنتجات`, 22 characters). The ar-SA name is entered later as a localization of the same record, not in the New App dialog.

After **Create**: App Information -> General Information -> **Apple ID** (numeric). That number is `ascAppId` for U10 (section 9). "In App Store Connect, go to Apps, open your app, select the App Store tab, then App Information under General ... listed under General Information as 'Apple ID'". **VERIFIED** https://docs.expo.dev/submit/ios/

---

## 3. App Information (sidebar: General -> App Information)

| Field | Paste / choose | Rule | Status |
|---|---|---|---|
| Name | as section 2 | 30 chars | 20 chars |
| Subtitle | <!-- field:EN_SUBTITLE --> `Two products. One clear pick.` | "can't be longer than 30 characters" (VERIFIED, app-information page) | 29 chars / 29 bytes |
| Category, primary | `Shopping` ("Apps that support the purchase of consumer goods or materially enhance the shopping experience") | VERIFIED https://developer.apple.com/app-store/categories/ | runbook section 6 |
| Category, secondary | `Lifestyle` (alternative `Utilities`) | both exist (same page, VERIFIED) | runbook section 6 |
| Content Rights | "Apps that contain, show, or access third-party content must have all the necessary rights to that content or be otherwise permitted to use it" (VERIFIED, app-information page). MYEZ shows retailer prices, product names and specs and summarises public reviews gathered from third-party sites, so the honest first answer is **Yes, it contains/shows/accesses third-party content**; the rights confirmation is an **owner legal call** (section 11) | exact ASC wording of the question UNVERIFIED | owner |
| Age Rating | section 3.1 | "This property is required" (VERIFIED, app-information page) | D9 = A |
| License Agreement | leave **Apple's standard EULA** ("Apple provides a standard EULA ... that applies in all regions"; a custom one is optional) | VERIFIED, app-information page | default |
| DSA trader status | App Information -> App Store Regulations and Permits -> Digital Services Act (or account-wide: Business -> Agreements -> Compliance). "Even if you don't distribute apps in the EU, you'll still need to declare a trader status"; ASC asks "next time you submit a new app". Under TERR = A (GCC only) the page says a developer who does not distribute in the EU is "not acting as a trader on the App Store". The choice ("This is a trader account." / "This is not a trader account.") is an **owner declaration** (section 11) | VERIFIED https://developer.apple.com/help/app-store-connect/manage-compliance-information/manage-european-union-digital-services-act-trader-requirements | owner |

### 3.1 Age rating (D9 = A) under the current questionnaire

Where: App Information -> Age Ratings -> **Set Up Age Ratings** (or Edit). Flow: in-app controls and capabilities first, then each section with NONE / INFREQUENT / FREQUENT (or YES / NO) answers, then "Age Categories and Override", then Save. **VERIFIED** https://developer.apple.com/help/app-store-connect/manage-app-information/set-an-app-age-rating

Questionnaire sections today: In-App Controls (Parental Controls; Age Assurance), Capabilities (Unrestricted Web Access; User-Generated Content; Social Media; Social Media Disabled for Users Under 13; Messaging and Chat; Advertising), Mature Themes, Medical or Wellness (Medical or Treatment Information; Health or Wellness Topics), Sexuality or Nudity, Violence, Chance-Based Activities (Gambling; Simulated Gambling; Contests; Loot Boxes). Values 4+, 9+, 13+, 16+, 18+, Unrated ("An Unrated app can't be published on the App Store"). **VERIFIED** https://developer.apple.com/help/app-store-connect/reference/app-information/age-ratings-values-and-definitions

| Question | Answer | Reason |
|---|---|---|
| Parental Controls | No | none in the app |
| Age Assurance | **No** (D9 = A) | Apple's examples: "declared age range API; age estimation capabilities; age verification via government-issued passport ..." (VERIFIED, definitions page). The "I am 13 or older" checkbox is none of these |
| Unrestricted Web Access | No | no web view or in-app browser; retailer links open externally (finding SA-08: `Linking.openURL` only) |
| User-Generated Content | No | Apple: "broad distribution of content created by users"; a shared result is app-generated and sent by the user to chosen people; no feed |
| Social Media / Social Media Disabled for Under 13 | No / No | no social features |
| Messaging and Chat | No | none |
| Advertising | No | no ad SDK, `NSPrivacyTracking` false |
| Mature Themes (Profanity, Horror, Alcohol/Tobacco/Drug use or references) | None | - |
| Medical or Treatment Information | **Infrequent** (owner judgement) | Apple: "diagnoses or guidance around the management of medical conditions ... May include: medication guidance". Over-the-counter pharmacy products can be compared (supplements category incl. OTC tablets with a pharmacy signal, `app/services/extraction_service.py:1252-1340` per CLIENT-TRUTH spec T11) and the verdict picks one; the app adds "General information only, not medical advice" (`results.medicalNote`). Infrequent = 13+ |
| Health or Wellness Topics | **Infrequent / Yes** | supplement and vitamin comparisons are "self-care or lifestyle recommendations" (9+ item) |
| Sexuality or Nudity (all) | None | - |
| Violence (all, incl. Guns or Other Weapons) | None | - |
| Gambling / Simulated Gambling / Contests / Loot Boxes | No / None / None / No | the referral bonus is not a contest |
| Age Categories and Override | if the calculated rating is **13+**: `Not Applicable`; if it is lower (e.g. Medical answered None gives 9+): **Override to Higher Age Rating -> 13+** | "If your app has a EULA with minimum age requirements that exceed the rating that Apple calculated, you must override to a rating that adheres to the requirements"; the override "will apply in all regions" and the content descriptions still reflect the answers (VERIFIED, set-an-app-age-rating page). The ToS minimum age is 13 |
| Made for Kids | never | 13+ audience; 2.3.8 |
| Age Suitability URL | leave empty (optional) | VERIFIED, same page |

The 13+ mapping: "Infrequent medical or treatment information" is a 13+ item; "Health and wellness topics" is a 9+ item (VERIFIED, definitions page). Expected result: **13+** either way after the override.

---

## 4. App Privacy (sidebar: App Privacy -> Get Started)

Flow: "indicate whether you or your third-party partners collect data" -> **Yes, we collect data from this app** -> tick every data type below -> Save -> click each type and answer -> **Publish** (a dialog confirms the answers are accurate). **VERIFIED** https://developer.apple.com/help/app-store-connect/manage-app-information/manage-app-privacy

Definitions used (VERIFIED https://developer.apple.com/app-store/app-privacy-details/): "Collect" = transmitting data off the device so you or partners can access it "longer than what is necessary to service the transmitted request in real time"; "Personal Information" and "Personal Data" are "considered linked to the user"; "Tracking" = linking with Third-Party Data for targeted advertising or advertising measurement, or sharing with a data broker. MYEZ does neither: **Tracking = No on every row.**

**AI training (OA2).** Neither the App Privacy details page nor the Manage-app-privacy help page has any question about AI, model training or third-party AI (both VERIFIED today: "No AI question exists on this page"). The only Apple text on third-party AI is guideline 5.1.2(i): "You must clearly disclose where personal data will be shared with third parties, including with third-party AI, and obtain explicit permission before doing so" (VERIFIED https://developer.apple.com/app-store/review/guidelines/), which the U3b consent sheet and the policy cover. OA2's "used to train AI models = YES" therefore maps onto the closest existing control: Apple asks for the purposes "you and/or your third-party partners" use the data for, and OpenAI's use (identify usage patterns, measure model quality, inform evaluation and training) is none of the five named purposes, so the packet adds **Other Purposes** ("Any other purposes not listed", VERIFIED) to the three comparison-input rows the inventory names (rows 3, 4, 12). **Orchestrator ruling needed before Publish** (assumption: over-disclosure costs nothing at review, under-disclosure is a 5.1.1/5.1.2 risk). Consequence: the ASC label then differs from the `app.json` manifest on those three rows (manifest = native-only; matching it needs a new build plus the c3/c5 jest pins). If the ruling is "manifest only", drop the Other Purposes cells and nothing else changes.

| # (inventory) | ASC category -> data type | Linked to user | Tracking | Purposes to tick |
|---|---|---|---|---|
| 1 | Contact Info -> **Email Address** | Yes | No | App Functionality |
| 2 | Contact Info -> **Name** | Yes | No | App Functionality |
| 3 | User Content -> **Photos or Videos** | Yes | No | App Functionality; **Other Purposes** (OA2) |
| 4 | User Content -> **Other User Content** | Yes | No | App Functionality; Analytics; **Other Purposes** (OA2) |
| 13 | User Content -> **Customer Support** | Yes | No | App Functionality |
| 5 | Search History -> **Search History** | Yes | No | App Functionality; Analytics; Product Personalization |
| 6 | Identifiers -> **User ID** | Yes | No | App Functionality; Analytics |
| 7 | Identifiers -> **Device ID** | Yes | No | App Functionality (the fingerprint hash and the Expo push token; Apple's App Functionality includes "prevent fraud") |
| 8 | Usage Data -> **Product Interaction** | Yes | No | Analytics; Product Personalization |
| 9 | Diagnostics -> **Crash Data** | Yes (conservative) | No | App Functionality |
| 10 | Diagnostics -> **Performance Data** | Yes (conservative) | No | App Functionality; Analytics |
| 11 | Diagnostics -> **Other Diagnostic Data** | Yes (conservative) | No | App Functionality |
| 12 | Other Data -> **Other Data Types** | Yes | No | App Functionality; Product Personalization; **Other Purposes** (OA2) |

Rows, Linked, Tracking and the non-OA2 purposes are the inventory and the manifest verbatim (VERIFIED (repo) `docs/privacy-data-inventory.md` table + JSON fence; `SmartCompareApp/app.json` `ios.privacyManifests`; 13 entries, SearchHistory carries Analytics since CLIENT-TRUTH).

Leave UNTICKED (not collected per the inventory "Not collected" section): Phone Number, Physical Address, Other User Contact Info, Health, Fitness, Payment Info, Credit Info, Other Financial Info, Precise Location, Coarse Location, Sensitive Info, Contacts, Emails or Text Messages, Audio Data, Gameplay Content, Browsing History, Purchase History, Advertising Data, Other Usage Data, Environment Scanning, Hands, Head.

Conditions that must still hold when Publish is clicked (inventory PM-8): the API is not behind Cloudflare and `ENABLE_PROXY_AWARE_RATELIMIT` is OFF (otherwise IP address / Coarse Location become declarable). Open classification for legal (not changed today): the user-chosen governorate inside demographics is filed under Other Data Types, not Coarse Location (inventory row 12).

**Privacy Policy URL** (App Privacy -> Privacy Policy -> Edit; "A privacy policy URL is required for all apps"; "Any changes to the URLs releases with your next app version", VERIFIED manage-app-privacy page): paste ONLY after section 0's #330 gate.

<!-- field:EN_PRIVACY_URL -->
```
https://qaren-landing-production.up.railway.app/privacy.html
```
User Privacy Choices URL: leave empty (optional, VERIFIED same page).

---

## 5. Version 1.0.0 page (sidebar: iOS App -> 1.0 Prepare for Submission)

Limits: Promotional Text "can't be longer than 170 characters"; Description "Limited to 4000 characters", plain text; Keywords "up to 100 bytes", each keyword "greater than two characters", no app or company names, no words already in the name; Support URL required and "must lead to actual contact information"; Marketing URL optional; Copyright required, "The copyright symbol is added automatically". **VERIFIED** https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information . Guideline 2.3.7: no "trademarked terms, popular app names, pricing information" in metadata (VERIFIED, guidelines page).

### Promotional Text (170 characters; 158 measured, 158 bytes)
<!-- field:EN_PROMO -->
```
Type or photograph two products and get a clear verdict built from specs, reviews and Bahrain-market prices. Check the price with the retailer before you buy.
```

### Description (4000 characters; 1735 measured, 1747 bytes)
<!-- field:EN_DESCRIPTION -->
```
MYEZ helps you choose between two products with confidence. Type two product names or photograph them, and we gather specs, reviews and retailer prices, then give you a clear verdict: which one fits you better, why, and where the other one wins.

WHAT YOU GET
• A clear verdict instead of a long spec sheet: the winner, the reason, and where the runner-up is stronger.
• Prices for the Bahrain market in Bahraini Dinar (BHD), gathered from retailers across the GCC. Prices change over time, so check the price with the retailer before you buy.
• A "What we know" panel that shows how much price, spec and review data stands behind a verdict.
• Camera compare: photograph two products, or pick two photos from your library.
• Results that respect your priorities: tell us what matters to you, like battery, quality or value.
• A history of your comparisons, and a way to share a result with friends.

CATEGORIES
Electronics, supplements, fragrances, makeup, skin and hair care, fashion and groceries. Supplement comparisons are general information, not medical advice.

BUILT FOR THE GULF
The interface is available in English and Arabic, with full right-to-left support. Comparison write-ups are in English.

YOUR PRIVACY
To write each comparison, MYEZ sends the products you type or photograph to OpenAI, and the app asks your permission before your first comparison. OpenAI may use what we send and the replies it generates to evaluate and train its models. We show no third-party ads and we don't track you across other companies' apps. You can delete your account from inside the app at any time.

Note: MYEZ is a decision aid. Information is gathered from public sources and may not always be accurate.

Support: support@qaren.app
```
Each claim's anchor: "What we know" = `results.whatWeKnow` / `results.confidence.sheet.title`; gallery = `home.camera.gallery` "Pick from gallery"; priorities = preferences (inventory row 12); share = ShareBottomSheet; medical line = `results.medicalNote` (MED = A); OpenAI sentence = `aiConsent.body` meaning (D3 = C, OA2); no ads / no tracking = `NSPrivacyTracking: false`; deletion = `EditProfileScreen.tsx:266-280`. The last line stays only if `support@qaren.app` delivers (owner test mail, LL-13); otherwise delete the line and the blank line before it (28 characters fewer: 1707).

### Keywords (100 bytes)
Recommended (B; 98 bytes, 12 keywords, none of 2 characters or fewer, no word from the name, no brand): <!-- field:EN_KEYWORDS_B_RECOMMENDED -->
```
prices,shopping,fragrance,perfume,phone,laptop,supplements,skincare,makeup,electronics,Bahrain,GCC
```
Runbook option (A; 95 bytes, 13 keywords): <!-- field:EN_KEYWORDS_A_RUNBOOK -->
```
prices,shopping,fragrance,perfume,phone,supplements,skincare,GCC,Bahrain,Saudi,UAE,Kuwait,Qatar
```
Why B: results use the Bahrain market only (BE-09); the four other country names could read as a promise of local prices there (2.3.7 "keywords that accurately describe your app"). `fragrance,perfume` stay only if the Tom Ford / Creed pair passes the warm-up (runbook E2); if it fails, use `prices,shopping,vitamins,headphones,phone,laptop,supplements,skincare,makeup,electronics,Bahrain,GCC` (measured: 100 bytes, 12 keywords: exactly at the limit).

### URLs
| Field | Paste | Measured |
|---|---|---|
| Support URL (required) | <!-- field:EN_SUPPORT_URL --> `https://qaren-landing-production.up.railway.app/support` | 55 chars |
| Marketing URL (optional) | leave **blank** (runbook section 6 and checklist row 8: until `qaren.app` is attached to the landing service) | - |
| Privacy Policy URL | section 4 (App Privacy page, after #330) | 60 chars |

Support page fact (VERIFIED (repo) `landing/support.html:7-15, :199-207`; nginx `location = /support` -> `/support.html`, `landing/nginx.conf.template:34-35`): it shows `support@qaren.app` and immediately meta-refreshes to `mailto:support@qaren.app`. Apple asks that the Support URL "lead to actual contact information (legal address, email address, telephone number), as may be required by local law": an email is contact information; whether a legal address is "required by local law" for a Bahrain individual is UNVERIFIED (L3 could be added to the page in #330).

### Version, copyright, sign-in
| Field | Paste | Note |
|---|---|---|
| Version | `1.0.0` | `expo.version` (app.json); the build number is owned by EAS (`appVersionSource: remote`, production `autoIncrement: true`), section 9 |
| Copyright (required) | <!-- field:EN_COPYRIGHT --> `2026 <L1: exact legal name on the Apple Developer membership>` | no ©: ASC adds it (VERIFIED, platform-version page). L1 is OPEN (owner) |
| What's New | not shown for the first version ("isn't available for the first version", VERIFIED) | - |
| Sign in with Apple | nothing to enter on this page. The app offers Sign in with Apple next to Google (guideline 4.8 "equivalent option", VERIFIED guidelines page); the review notes (section 6) warn that a Sign in with Apple login creates a new account with the standard free allowance. SIWA token revocation on deletion is U11 = A (after launch) | - |
| Screenshots | section 7 | - |
| Build | added after `eas submit` processing (section 9); blocked today (section 0) | - |

---

## 6. App Review Information (bottom of the 1.0 page)

Rules: the Contact section is required, phone "in international format, including a plus sign (+) followed by the country code"; Sign-in information is required "If your app requires a login", the demo account "must not expire"; "The Notes field can contain up to 4000 bytes"; the section "can be edited at any time". **VERIFIED** https://developer.apple.com/help/app-store-connect/reference/app-information/platform-version-information . Guideline 2.1(a): "include demo account info (and turn on your back-end service!) if your app includes a login" (VERIFIED, guidelines page).

| Field | Paste |
|---|---|
| Sign-in required | **Yes** (every compare needs an account since U13) |
| User name | `<REVIEW EMAIL 1>` |
| Password | `<REVIEW PASSWORD 1>` (typed by the owner in his own browser; never in chat or the repo) |
| Contact first name | `<FIRST NAME>` |
| Contact last name | `<LAST NAME>` |
| Phone | `<+973 ...>` (international format, + and country code) |
| Email | `<CONTACT EMAIL>` (a monitored inbox) |
| Attachment | none |

The ASC UI may show the contact name as one field or as first/last: the help page lists "name, email, phone" together (UI split UNVERIFIED).

### Notes (4000 bytes; 1851 measured, all ASCII). Paste only after the demo accounts exist, the warm-up passed and canary 7 passed (section 11).
<!-- field:REVIEW_NOTES -->
```
Sign-in is required: the account holds the user's comparison history, preferences and per-account comparison allowance.

Review account 1: <REVIEW EMAIL 1> / <REVIEW PASSWORD 1>
Review account 2 (spare, in case account 1 is deleted): <REVIEW EMAIL 2> / <REVIEW PASSWORD 2>
Both review accounts have a raised daily comparison limit. Sign in with Apple is also available; it creates a new account with the standard free allowance.

How to test:
1. Sign in with review account 1. Before the first comparison or scan, the app shows a one-time permission sheet ("Your comparison is written with AI") that names OpenAI and explains what is sent. Tap "Agree and continue". Without this permission the app cannot run comparisons.
2. On Home, type two products, for example "<PAIR A>" and "<PAIR B>" (a pair that passed our warm-up today), then tap Compare. A comparison usually takes 20-40 seconds while we gather specs, reviews and prices.
3. Or tap Scan Product to photograph two products; "Pick from gallery" selects photos from the library instead.
4. Results show the winner, the reasons, where the runner-up wins, and a price for each product when one is found.

Market: results use the Bahrain market. Prices are in Bahraini Dinar (BHD), gathered from retailers across the GCC, and change over time.
AI processing: the product names, links (with the text of those pages), photos and the profile preferences named on the permission sheet are sent to OpenAI to write the comparison. OpenAI may use these inputs and its outputs to evaluate and train its models; the permission sheet says so. The user's name, email and account details are not sent.
Account deletion: Profile tab -> gear icon (top right) -> Delete account (bottom of the Edit Profile screen) -> confirm.
This version has no in-app purchases, subscriptions or ads, and does not track users.
```
Anchors (VERIFIED (repo) at main): sheet title `aiConsent.title` "Your comparison is written with AI", button `aiConsent.agree` "Agree and continue", body `aiConsent.body` (names OpenAI, the inputs, the training sentence, "Your name, email and account details are not sent"); `home.compare.cta` "Compare"; `home.scan` "Scan Product"; `home.camera.gallery` "Pick from gallery"; gear `ProfileScreen.tsx:333-342` (a11y label "Settings") -> `EditProfile`; `EditProfileScreen.tsx:266-280` "Delete account" (`editProfile.deleteAccount`) -> confirm `profile.deleteConfirm`. "20-40 seconds" is the runbook figure; canary 7a measured every cold compare at the 30 s cap with the FANOUT flags OFF, so this line is true only after the flips pass canary 7 (section 11). Replace `<PAIR A>` / `<PAIR B>` with one READY pair from the warm-up table (runbook E2). If Google sign-in passes the preview-build check (GOO), the owner may add "Google sign-in is also available." after the Sign in with Apple sentence (+34 bytes with the leading space); otherwise leave it out. The real email and password change the byte count by a few dozen bytes; the 4000-byte ceiling is far away.

---

## 7. Screenshots (1.0 page -> Previews and Screenshots -> iPhone)

**Apple's current rule (changed since session 69):** "To submit your app, you must provide screenshots for the following required display sizes: iPhone: At least one screenshot for iPhone with Dynamic Island (medium display)." Separately, iPhone with Face ID (large display) is "Required if app runs on iPhone and screenshots for iPhone with Dynamic Island (large display) aren't provided". 1 to 10 screenshots per size, `.jpeg` / `.jpg` / `.png`, "Images can't include alpha channels or transparencies". **VERIFIED** https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications

| ASC size (page label) | Accepted portrait pixels | Devices (Apple's list) | Upload? |
|---|---|---|---|
| iPhone with Dynamic Island (medium display), shown in ASC as 6.3" | 1206 x 2622 or 1179 x 2556 | iPhone 18 Pro, 17 Pro, 17, 16 Pro, 16, 15 Pro, 15, 14 Pro | **REQUIRED**: upload the 1206 x 2622 set |
| iPhone with Dynamic Island (large display), 6.9" | 1320 x 2868, 1290 x 2796 or 1260 x 2736 | iPhone Air, 18 Pro Max, 17 Pro Max, 16 Pro Max, 16 Plus, 15 Pro Max, 15 Plus, 14 Pro Max | **upload too** (1320 x 2868): it removes the 6.5" requirement |
| iPhone with Face ID (large display), 6.5" | 1284 x 2778 or 1242 x 2688 | iPhone 14 Plus, 13/12/11 Pro Max, 11, XS Max, XR | not needed once the 6.9" set exists |
| iPad 13" | 2064 x 2752 / 2048 x 2732 | - | not needed: `supportsTablet: false` (app.json; D1 = A) |

The inch labels next to the page labels are inferred from the page's icon names, not its text (UNVERIFIED wording; the pixel sizes are VERIFIED). The session-69 checklist's "6.9" or 6.5" for the first submission" is superseded by the quote above.

Six scenes (owner list, `AHMED_TASKS_TO_SUBMIT.md` 8.1; runbook E3), same order in both sizes:
1. Home with two products entered
2. Results winner card
3. Dimension bars / "Where the runner-up wins"
4. "What we know" confidence pills
5. The camera framing two products
6. History with 3 or more entries

Never: splash, sign-in, loading, the AI-consent sheet or the limit sheet (2.3.3: screenshots "should show the app in use, and not merely the title art, login page, or splash screen", quoted in finding SA-01). Capture on a physical iPhone with side button + volume up, from a build that carries CLIENT-TRUTH and U3b, signed in to a review account, after the warm-up (a Results screen needs a working compare).

Resize and strip alpha (Claude's step; Pillow 12.3.0 in the pinned venv, script tested today on synthetic RGBA 1179 x 2556, RGB 1320 x 2868, JPEG 1170 x 2532 and a landscape image, which it refuses):
```
PYTHONIOENCODING=utf-8 C:/Users/SynAckITPC/Documents/AI/.venv-qaren/Scripts/python.exe -I <notes>/ascpack/prep_screenshots.py <captures_dir> <out_dir>
```
It writes `<out_dir>/iphone_6.3_1206x2622/` and `<out_dir>/iphone_6.9_1320x2868/` (RGB PNG, alpha flattened onto white, cover-scale + centre crop, a warning above 1 % aspect drift) and re-opens every output to check size, mode and the absence of an alpha band. Upload the 6.3" folder to the Dynamic Island (medium) slot and the 6.9" folder to the Dynamic Island (large) slot. Arabic screenshots wait for D11 (Appendix A).

---

## 8. Pricing and Availability (sidebar: Monetization -> Pricing and Availability)

| Item | Choose | Source |
|---|---|---|
| Price | **Price Schedule -> Add Pricing -> base country `Bahrain` -> Free (0.00)** -> Confirm. Pricing must be set before review; without a Paid Apps Agreement an app can only be free (no agreement needed) | VERIFIED via Apple's "Set a price" help page as summarised by search (https://developer.apple.com/help/app-store-connect/manage-app-pricing/set-a-price); the page itself was not opened, so the exact button labels are UNVERIFIED |
| Availability | **App Availability -> Set Up Availability -> Specific Countries or Regions** -> tick exactly: Bahrain, Kuwait, Oman, Qatar, Saudi Arabia, United Arab Emirates -> leave the "all future countries or regions" box at the bottom **unticked** -> Next -> Confirm | VERIFIED https://developer.apple.com/help/app-store-connect/manage-your-apps-availability/manage-availability-for-your-app-on-the-app-store ; TERR = A |
| Pre-order | **No** (do not choose "Publish as Pre-Order"; it would also auto-add future regions) | same page, VERIFIED |
| Version release (on the 1.0 page) | **Manual** ("Manually release this version"): the version waits in Pending Developer Release after approval | options Manual / Automatic / Automatic no earlier than: VERIFIED platform-version page; the exact radio label is UNVERIFIED |
| In-app purchases / subscriptions | none (D2 = A, PR #255) | runbook row 2 |

---

## 9. U10: `eas.json` submit block and the build / submit commands

### 9.1 Installed tools (measured today on this box)

- `eas` on PATH = global **eas-cli 18.8.1** (`C:\Users\SynAckITPC\AppData\Roaming\npm\node_modules\eas-cli\package.json`); an npx cache holds 19.1.0. **No eas-cli 24.x is installed here**, contrary to the task brief. Latest release: **v24.12.1** (08 Oct). VERIFIED https://github.com/expo/eas-cli/releases ; the docs.expo.dev CLI reference is generated for 24.12.1 (VERIFIED https://docs.expo.dev/eas/cli/).
- `eas.json` `cli.version` is `">= 18.8.1"` (VERIFIED (repo) `SmartCompareApp/eas.json`): both 18.8.1 and 24.12.1 satisfy it.
- Upgrade (a package-manager action: the orchestrator or the owner runs it, not this agent): `npm install -g eas-cli@24.12.1`. Node here is v24.11.1; eas-cli 24.4.0+ requires Node `^20.18.3 || >=22.0.0` (VERIFIED https://raw.githubusercontent.com/expo/eas-cli/main/CHANGELOG.md). Breaking changes between 19.0.0 and 24.12.1 (same changelog): 19.0.0 browser login is the default for `eas login` (`--no-browser` for the old flow); 20/22/23/24 rename observe / simulator / `--json` build objects; 21.0.0 removes `eas onboarding`. None touches `eas build -p ios --profile production` or `eas submit`. Useful additions: 20.2.0 uses the ASC API key stored in EAS credentials for submissions; 21.5.0 adds `eas submit:list/view/retry/cancel/status`; 22.0.0 sets up the internal TestFlight group when submitting interactively with an existing `ascAppId`; 24.0.0 makes the issuer ID optional in credentials types; 24.8.0 accepts individual ASC API keys.

### 9.2 The submit block (U10 fills `SmartCompareApp/eas.json`, which today has `"submit": {"production": {}}`)

Option names, all VERIFIED https://docs.expo.dev/eas/json/ : `ascAppId` ("App Store Connect unique application Apple ID number. When set, results in skipping the app creation step"), `appleTeamId` ("Your Apple Developer Team ID"), `ascApiKeyPath` ("The path to your App Store Connect Api Key .p8 file"), `ascApiKeyIssuerId`, `ascApiKeyId`; also `sku`, `language` (default "en-US"), `groups` (TestFlight internal groups).

**Recommended (key stored on EAS, no local path in the repo):**
```json
"submit": {
  "production": {
    "ios": {
      "ascAppId": "<digits from App Information -> Apple ID>",
      "appleTeamId": "8K562M549D"
    }
  }
}
```
Then put the key on EAS once, in a real terminal: `eas credentials -p ios` -> production -> "App Store Connect: Manage your API Key" -> set up the project to use an API Key for EAS Submit (VERIFIED https://docs.expo.dev/submit/ios/). `ascAppId` is a quoted string of digits (the U10 pin in `LAUNCH_PUNCH_LIST.md:207`).

**Alternative (key file on the build machine):**
```json
"submit": {
  "production": {
    "ios": {
      "ascAppId": "<digits>",
      "appleTeamId": "8K562M549D",
      "ascApiKeyPath": "<ABSOLUTE path outside the repo>/AuthKey_<KEY_ID>.p8",
      "ascApiKeyIssuerId": "<issuer UUID>",
      "ascApiKeyId": "<KEY_ID>"
    }
  }
}
```
Do not commit the alternative with a real path: it names the owner's disk layout; prefer the EAS-stored key.

### 9.3 Command sequence (owner's real terminal, clean checkout of the release commit, not the shared clone)

Gate first: PR #330 merged and the landing redeployed (UB-R4); CLIENT-TRUTH and U3b are on main already (#334, #342).

```
cd SmartCompareApp
npm ci
npx tsc --noEmit
npx jest --ci
npx eslint "src/**/*.{ts,tsx}"
npx expo install --check          # clean except the react-native-svg exclude; "exits with non-zero in CI"
npx expo-doctor                   # app config / dependency / New Architecture checks
npx expo config --type introspect # mic string present, no Face ID key, CFBundleLocalizations en+ar, iPhone only
npm audit --audit-level=high      # report only
eas --version                     # 18.8.1 today; 24.12.1 after the upgrade
eas whoami                        # kersher2
eas credentials -p ios            # production: reuse the distribution cert, App Store profile, APNs key yes, ASC API key for submit (Account Holder Apple ID)
eas build -p ios --profile preview        # smoke on the 2 registered iPhones (sign-ins, camera, compare, push, Arabic, consent sheet)
eas build -p ios --profile production     # remote buildNumber auto-incremented, channel production
eas submit -p ios --profile production --latest
```
Sources: `npx expo install --check` "Check which installed packages need to be updated" and its CI exit rule (VERIFIED https://docs.expo.dev/more/expo-cli/); expo-doctor as a pre-build diagnostic (VERIFIED via search of docs.expo.dev: https://docs.expo.dev/develop/tools/ , https://docs.expo.dev/build-reference/ios-builds/); `eas submit [-p android|ios|all] [-e <value>] [--latest | --id <value> | --path <value> | --url <value>]`, `-e, --profile` defaults to "production", `--latest` "Submit the latest build for specified platform" (VERIFIED https://docs.expo.dev/eas/cli/). `--profile` is the long form of `-e` (same page). Changed vs the runbook: only the eas-cli version line and the login default (browser) - every other step is unchanged.

Version facts: `appVersionSource: "remote"` means "EAS servers can store and manage your app's developer-facing build version" and the app-config build numbers "are ignored"; `autoIncrement: true` on production increments the remote buildNumber on each build; the remote value is initialised from the local project (no `ios.buildNumber` in app.json -> the first build is 1). VERIFIED https://docs.expo.dev/build-reference/app-versions/ . The marketing version stays `expo.version` = `1.0.0` (app.json; that it is still read from app config under remote is an inference, UNVERIFIED on that page).

After upload: the build appears in TestFlight after processing, "usually within 10 to 15 minutes" (VERIFIED https://docs.expo.dev/submit/ios/). Internal TestFlight smoke on the exact binary, read the processing email for ITMS-90683 / 91053 / 91061 (runbook D3), then select the build on the 1.0 page.

Optional: `SENTRY_ALLOW_FAILURE=true` in the EAS production environment, or confirm `SENTRY_AUTH_TOKEN` there (runbook section 5; owner task 5.4).

---

## 10. Export compliance

- `ios.infoPlist.ITSAppUsesNonExemptEncryption: false` is set (VERIFIED (repo) `SmartCompareApp/app.json`, `ios.infoPlist`). It reaches the binary at prebuild.
- Apple: set the Info.plist key "so that you don't need to answer encryption questions with each app submission". VERIFIED https://developer.apple.com/help/app-store-connect/manage-app-information/overview-of-export-compliance . The runbook's reason it is correct (HTTPS/TLS, SPKI pinning and expo-crypto only) is from session 69 (runbook section 7), not re-verified today.
- What ASC still asks: no per-build encryption questions with the key set. The page adds that France controls encryption apps (Secure Storage, Secure Communications, Security Anti-Virus): not relevant to GCC-only availability (TERR = A). The DSA trader declaration (section 3) is a separate compliance prompt at new-app submission. Whether ASC shows any one-time export question on the first build despite the key: UNVERIFIED (Apple's encryption documentation page renders client-side and could not be read); if it appears, answer that the app uses only exempt encryption (standard HTTPS through the OS) and nothing proprietary.

---

## 11. Owner-only items, with the exact place each is entered

| Item | Where it is entered | Blocks |
|---|---|---|
| Who is signed in: Account Holder or not | ASC -> Users and Access | 1.3, 1.5 signing, agreements |
| Latest agreements accepted (Account Holder) | ASC -> Business -> Agreements | New App |
| API access request + Team key (`.p8` once, outside the repo; Key ID, Issuer ID never in chat) | ASC -> Users and Access -> Integrations -> App Store Connect API -> Team Keys | section 9 |
| `eas credentials -p ios` (Account Holder Apple ID; reuse cert, App Store profile, APNs yes, ASC key) | owner's real terminal in `SmartCompareApp` | builds |
| **L1** exact legal name on the Apple membership | ASC 1.0 page -> **Copyright** (`2026 <L1>`); and the U8 fill-in (controller name) in PR #330 | copyright field, #330 |
| **L3** postal address | the U8 fill-in (policy controller line) in PR #330; optionally the support page | #330 |
| D3 = C wording in #330 (OA2 fork: replace the "we have not opted in" sentence, EN `landing/privacy.html:246` and AR twin) + "We do not sell" (line 192) reviewed against the complimentary-token arrangement | PR #330 (legal) | Privacy Policy URL |
| PR #330 merged, then `railway up landing --path-as-root -s qaren-landing -d` | GitHub; owner terminal | Privacy URL; UB-R4 store build |
| Privacy Policy URL pasted | ASC -> App Privacy -> Privacy Policy -> Edit | submission |
| App Privacy ruling on "Other Purposes" (section 4) | orchestrator / Fable ruling, then ASC -> App Privacy -> Publish | Publish |
| Content Rights answer (third-party content: yes; rights confirmation) | ASC -> App Information -> Content Rights | submission |
| DSA trader status ("not a trader" under TERR = A, the owner's declaration) | ASC -> App Information -> App Store Regulations and Permits, or Business -> Agreements -> Compliance | new-app submission |
| Medical or Treatment Information = Infrequent vs None (judgement) | ASC -> App Information -> Age Ratings | rating |
| Two review accounts: register in the app, confirm email if required, onboard once, `users.subscription_tier = premium` in the Supabase table editor | the app; Supabase -> Authentication -> Users; Table editor `users` | notes, sign-in fields |
| Review account 1 credentials | ASC 1.0 page -> App Review Information -> Sign-In Information | submission |
| Review account 2 credentials | the Notes text placeholders (section 6) | - |
| Review contact first/last name, +973 phone, email | ASC 1.0 page -> App Review Information -> Contact Information | submission |
| Test mail to `support@`, `privacy@`, `legal@qaren.app` (LL-13) | any mail client | the Support line in the description |
| Migration **043** (PRECHECK sitting, then ONE_PASTE / POSTCHECK) | Supabase -> SQL editor (files in `2026-10-03-session-71-state/`) | deletion truth ("and its data") |
| Bright Data token renewal | per `docs/runbooks/brightdata-token-renewal.md` | prices |
| **FANOUT flips**, one per canary window, `run_canary.sh canary7b` after each: `ENABLE_PHASE2_RESIDUAL_GUARD=true`, then `ENABLE_UNIFIED_SEARCH_BOUND=true`, then `ENABLE_PARSE_PRESPLIT=true` and `ENABLE_PARSE_BUDGET=true` | Railway -> `web` -> Variables (owner) | the "20-40 seconds" line; review |
| Canary 7 PASS and the warm-up READY pair | owner terminal (`railway run -s web -- ...`) | notes `<PAIR A>`/`<PAIR B>` |
| Google sign-in check on the preview build (GOO) | device | the optional Google sentence |
| Six screenshots on a physical iPhone | device -> Claude resizes (section 7) -> ASC 1.0 page -> Previews and Screenshots | submission |
| D11 reversal (if wanted) + native Arabic review of Appendix A and of `aiConsent.body` AR | owner / reviewer | ar-SA localization |

---

## 12. Measurements (script `measure.py` over `fields.txt`; Python len and UTF-8 bytes; run 2026-10-10)

```
key | chars | utf8_bytes | limit | unit | verdict | non_ascii_chars | format_chars
EN_NAME | 20 | 22 | 30 | chars | PASS | 1 | -
EN_NAME_ALT_HYPHEN | 20 | 20 | 30 | chars | PASS | 0 | -
EN_NAME_FALLBACK | 4 | 4 | 30 | chars | PASS | 0 | -
EN_SUBTITLE | 29 | 29 | 30 | chars | PASS | 0 | -
EN_PROMO | 158 | 158 | 170 | chars | PASS | 0 | -
EN_KEYWORDS_A_RUNBOOK | 95 | 95 | 100 | bytes | PASS | 0 | -
EN_KEYWORDS_B_RECOMMENDED | 98 | 98 | 100 | bytes | PASS | 0 | -
EN_DESCRIPTION | 1735 | 1747 | 4000 | chars | PASS | 6 | -
EN_COPYRIGHT | 61 | 61 | - | chars | n/a | 0 | -
EN_SUPPORT_URL | 55 | 55 | - | chars | n/a | 0 | -
EN_PRIVACY_URL | 60 | 60 | - | chars | n/a | 0 | -
AR_SUPPORT_URL | 58 | 58 | - | chars | n/a | 0 | -
AR_PRIVACY_URL | 63 | 63 | - | chars | n/a | 0 | -
REVIEW_NOTES | 1851 | 1851 | 4000 | bytes | PASS | 0 | -
AR_NAME | 22 | 40 | 30 | chars | PASS | 18 | -
AR_NAME_ALT | 20 | 36 | 30 | chars | PASS | 16 | -
AR_SUBTITLE | 30 | 55 | 30 | chars | PASS | 25 | -
AR_PROMO | 130 | 237 | 170 | chars | PASS | 107 | -
AR_KEYWORDS_SA06 | 51 | 95 | 100 | bytes | PASS | 44 | -
AR_KEYWORDS_RECOMMENDED | 48 | 89 | 100 | bytes | PASS | 41 | -
AR_DESCRIPTION | 1433 | 2588 | 4000 | chars | PASS | 1149 | -

EN_KEYWORDS_A_RUNBOOK: 13 keywords; <=2-char keywords: 0; padded: 0; duplicates: False
EN_KEYWORDS_B_RECOMMENDED: 12 keywords; <=2-char keywords: 0; padded: 0; duplicates: False
AR_KEYWORDS_SA06: 8 keywords; <=2-char keywords: 0; padded: 0; duplicates: False
AR_KEYWORDS_RECOMMENDED: 8 keywords; <=2-char keywords: 0; padded: 0; duplicates: False
```
The first run measured an earlier keyword option B at 102 bytes (FAIL); it was trimmed and re-measured (98, PASS). `check_packet.py` confirms that every field block in this file is byte-identical to `fields.txt`.

---

## Appendix A. ar-SA localization (HOLD: D11 = B, English only for 1.0; native Arabic review required before any paste)

Source: the SA-06 draft (`docs/investigations/2026-09-29-session-69-state/appstore_findings_verified.json`, findings[25] `fix`), with the old name قارن replaced by ميّز (U+0645 U+064A U+0651 U+0632, the same code points as `SmartCompareApp/locales/ar.json` `ios.CFBundleDisplayName`), and the same truth corrections as the English text. Lines marked [NEW] were not in SA-06 and were composed today (closest native review). ASC language label: Arabic.

| Field | Paste | Measured |
|---|---|---|
| Name | <!-- field:AR_NAME --> `ميّز - مقارنة المنتجات` (runbook section 6) | 22 chars / 40 bytes |
| Name alternative | <!-- field:AR_NAME_ALT --> `ميّز: قرار شراء أذكى` | 20 / 36 |
| Subtitle | <!-- field:AR_SUBTITLE --> `قارن منتجين واحصل على حكم واضح` (here قارن is the verb "compare", not the old brand; the reviewer confirms it does not read as the old name) | 30 / 55 (at the limit) |
| Support URL | <!-- field:AR_SUPPORT_URL --> `https://qaren-landing-production.up.railway.app/ar/support` | 58 |
| Privacy URL (after #330) | <!-- field:AR_PRIVACY_URL --> `https://qaren-landing-production.up.railway.app/ar/privacy.html` | 63 |

Promotional text [NEW: SA-06's "prices are live ... we always show the confidence level" removed (BE-03), "Gulf store prices" -> "Bahrain market prices" (BE-09)] (130 chars / 237 bytes):
<!-- field:AR_PROMO -->
```
اكتب منتجين أو صوّرهما، واحصل على حكم واضح مبني على المواصفات والتقييمات وأسعار سوق البحرين. تحقّق من السعر لدى المتجر قبل الشراء.
```

Keywords, recommended (89 bytes; drops مقارنة, which repeats a word of the name, and السعودية per BE-09; adds مكياج and الخليج):
<!-- field:AR_KEYWORDS_RECOMMENDED -->
```
أسعار,تسوق,عطور,جوال,مكملات,مكياج,البحرين,الخليج
```
SA-06 original (95 bytes):
<!-- field:AR_KEYWORDS_SA06 -->
```
مقارنة,أسعار,تسوق,عطور,جوال,مكملات,البحرين,السعودية
```

Description (1433 chars / 2588 bytes). [NEW] lines: the price bullet, the "What we know" bullet, the camera bullet (gallery instead of "photograph one and type the other"), the medical sentence, the write-ups-in-English clause, the whole privacy paragraph (OpenAI + training sentence; "we don't sell your data" removed; "and its data" removed until 043):
<!-- field:AR_DESCRIPTION -->
```
ميّز يساعدك على الاختيار بين منتجين بثقة. اكتب اسمي المنتجين أو صوّرهما، فنجمع المواصفات والتقييمات وأسعار المتاجر، ثم نعطيك حكماً واضحاً: أيهما يناسبك أكثر، ولماذا، وأين يتفوق الآخر.

ما الذي تحصل عليه
• حكم واضح بدل جدول مواصفات طويل: الفائز، وسبب اختياره، وأين يتفوق المنافس.
• أسعار لسوق البحرين بالدينار البحريني، نجمعها من متاجر في دول الخليج. الأسعار تتغير مع الوقت، لذا تحقّق من السعر لدى المتجر قبل الشراء.
• لوحة «ما الذي نعرفه» تبيّن حجم بيانات السعر والمواصفات والتقييمات التي يستند إليها الحكم.
• المقارنة بالكاميرا: صوّر المنتجين، أو اختر صورتين من مكتبة الصور.
• نتائج تراعي أولوياتك: أخبرنا بما يهمك مثل البطارية أو الجودة أو القيمة مقابل السعر.
• سجل لمقارناتك السابقة، ومشاركة النتيجة مع من تحب.

الفئات
الإلكترونيات، المكملات الغذائية، العطور، المكياج، العناية بالبشرة والشعر، الأزياء، والبقالة. مقارنات المكملات معلومات عامة وليست نصيحة طبية.

مصمم للخليج
واجهة التطبيق متوفرة بالعربية والإنجليزية مع دعم كامل للكتابة من اليمين إلى اليسار، ونصوص المقارنات باللغة الإنجليزية.

خصوصيتك
لكتابة كل مقارنة يرسل ميّز المنتجات التي تكتبها أو تصوّرها إلى OpenAI، ويطلب التطبيق إذنك قبل أول مقارنة. وقد تستخدم OpenAI ما نرسله والردود التي تنتجها في تقييم نماذجها وتدريبها. لا نعرض إعلانات من جهات خارجية، ولا نتتبعك عبر تطبيقات الشركات الأخرى. يمكنك حذف حسابك من داخل التطبيق في أي وقت.

تنبيه: ميّز أداة مساعدة لاتخاذ القرار، والمعلومات مجمّعة من مصادر عامة وقد لا تكون دقيقة دائماً.

للدعم والاقتراحات: support@qaren.app
```
The «ما الذي نعرفه» label equals the app's AR value of `results.whatWeKnow`, the Results eyebrow (`ResultsContent.tsx:523`; checked by code point against `SmartCompareApp/src/i18n/ar.json:761` at main); the AR training sentence paraphrases the shipped `aiConsent.body` AR sentence (NATIVE_REVIEW_S75.md) and must keep its meaning.
