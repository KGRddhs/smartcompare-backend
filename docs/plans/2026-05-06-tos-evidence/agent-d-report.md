# Agent D — Existing Legal + Store Config Audit

**Model:** Sonnet | **Returned:** 2026-05-06

---

# SECTION 1: Privacy Policy — What It Covers

**File:** `app/legal/privacy_policy.md`
**Date stated in the doc:** `*Last Updated: March 26, 2026*` (line 5)
**Date hardcoded in `legal_routes.py`:** `"last_updated": "2026-03-26"` (line 23) — matches.
**Draft status:** The document opens and closes with `*DRAFT — This document is a template. The business and legal team must review and finalize before publication.*` (lines 7 and 95). This warning is visible in the raw markdown that `GET /api/v1/legal/privacy` serves to the public.
**Entity name:** Still titled `"SmartCompare — Product Comparison App"` (line 3) and uses the "we/us" name "SmartCompare" throughout — not updated to "Qaren."

**Topics addressed:**

**Data collected (Section 2):**
- Account info: "Email address, display name, and password when you create an account." (line 16)
- Preferences: "Product comparison preferences including priorities, budget level, lifestyle tags, and brand attitude." (line 17)
- Feedback: "Comparison feedback (thumbs up/down, suggestions) you voluntarily submit." (line 18)
- Usage data: "Product comparison queries, search history, event interactions (tab switches, source clicks, view durations)." (line 21)
- Device info: "Device type, operating system, and app version." (line 22)
- Camera data: "Photos taken within the App for product identification are processed in real-time and not stored on our servers." (line 23)
- Social login: "If you sign in with Google or Apple, we receive your email address and basic profile information from the respective provider." (line 26)

**Purpose of use (Section 3):** Covers personalization, history, service improvement, usage analysis, service communications ("with your consent"), and abuse detection. (lines 31-37)

**Data sharing (Section 4):**
- Does not sell personal information (line 40)
- Names specific processors: "Cloud hosting (Railway), database (Supabase), AI processing (OpenAI), search (Serper), caching (Upstash), and error tracking (Sentry)" (line 41)
- Legal disclosure (line 42)

**Retention (Section 5):**
- Account data retained while active, deleted on account deletion (line 46-47)
- Comparison history retained while active (line 48)
- Anonymous analytics may be retained indefinitely (line 49)
- Cache TTLs: "Product prices cached for 24 hours; specs and reviews cached for 7 days." (line 50)

**User rights (Section 6):** Access, correction, deletion, export ("by contacting us"), and withdrawal of consent listed. (lines 53-58)

**Security (Section 7):** "Encrypted data transmission (HTTPS/TLS), Secure authentication with JWT tokens, Rate limiting to prevent abuse, Server-side input validation." (lines 63-66)

**Children (Section 8):** "The App is not intended for children under 13. We do not knowingly collect personal information from children under 13." (line 70)

**Regional/GCC (Section 9):** "SmartCompare operates primarily in the GCC region (Bahrain, Saudi Arabia, UAE, Kuwait, Qatar, Oman). We comply with applicable data protection laws in these jurisdictions." (line 74) No specific law is named except implicitly in Section 11.

**Policy change notification (Section 10):** "We will notify you of material changes through the App or via email." (line 78)

**AI quality / OpenAI data sharing (Section 11):** This section is notable — it explicitly describes participation in "OpenAI's Data Sharing Program" (line 82), lists what is and is not shared, and provides a GCC-law-anchored opt-out: "Under Bahrain's PDPL, Saudi Arabia's PDPL, and similar GCC regulations, you can disable AI sharing in *Settings → Privacy → 'Help improve AI quality.'*" (line 88). The opt-out path (`Settings → Privacy → "Help improve AI quality"`) does not correspond to any screen visible in the current codebase (ProfileScreen exists, but that settings path is not implemented).

**Contact (Section 12):** Single email address: `privacy@smartcompare.app` (line 93). Domain mismatch — app is branded Qaren, not SmartCompare.

---

# SECTION 2: Privacy Policy — What It Does NOT Cover (Gaps vs. the Question Checklist)

Cross-referencing `C:\Users\SynAckITPC\Downloads\qaren_ai_tos_questions_english.md` against the existing `privacy_policy.md`:

**Section 4 — Data Collected:**
- Q4.4 Age or age group — not mentioned. The app collects `age_group` via the demographics endpoint (`PUT /api/v1/auth/demographics`) and stores it in `users.demographics_profile`. The privacy policy makes no mention of this.
- Q4.5 Gender — not mentioned. Also collected via demographics endpoint and stored in `users.demographics_profile`.
- Q4.6 Country or city / Q4.7 Geographic location — not mentioned explicitly. Governorate is collected; country is derived from `CF-IPCountry` header automatically. Neither is disclosed.
- Q4.17 IP address — not mentioned. The backend derives country from the Cloudflare `CF-IPCountry` header, meaning IP-derived location is processed without disclosure.
- Q4.18 Crash logs — not mentioned. Sentry is named as a processor in Section 4 of the policy but the nature of what Sentry receives (stack traces, request data, error context) is not described.
- Q4.19 Analytics events — Section 2.2 mentions "event interactions (tab switches, source clicks, view durations)" but does not list specific event names (sign_up, compare, recommendation_view, etc.) or state that events are tied to user IDs.
- Q4.20 Push notification token — not mentioned. The app registers Expo push tokens (`push_token` column in `users` table per migration 015), which is a persistent device identifier. Not disclosed anywhere in the privacy policy.
- Q4.21 Referral and behavioral profile data — the `behavior_profile` JSONB column, decay-weighted purchase pattern data, and referral invite/redemption data are not mentioned.

**Section 5 — Onboarding / Survey:**
- Q5.10 Clear consent before collecting onboarding answers — not addressed. The policy mentions preferences are collected but says nothing about whether consent is obtained before the onboarding survey or demographics collection.

**Section 7 — Sensitive Data:**
- Q7.1 Health data — Supplements category comparisons use the Bahrain Drug Database (655 registered health products). User search queries for supplements (e.g., vitamins, medications) are processed by OpenAI and passed to Serper. The policy does not address health-adjacent data.
- Q7.9 User scoring / buyer type classification — the behavioral profile, cohort matching, and scoring method (`scoring_method: "behavioral"/"personalized"/"category_weighted"`) constitute a form of consumer profiling. Not disclosed.

**Section 8 — SDKs and External Services:**
- Q8 (entire section) — The policy names Railway, Supabase, OpenAI, Serper, Upstash, and Sentry (line 41). It does not name or describe: `@react-native-google-signin/google-signin`, `expo-apple-authentication`, `expo-secure-store`, `expo-localization`, `expo-camera`, `expo-image-picker`, or `expo-notifications`. For each named service there is no disclosure of: what data is transmitted, whether data leaves Bahrain, whether the service is mandatory, or how to opt out.

**Section 10 — Analytics and Tracking:**
- Q10.3 Whether analytics are linked to a user ID — not stated.
- Q10.6/Q10.7 Cross-app tracking / advertising tracking — not addressed (the app does not appear to do this, but absence of a denial leaves it open).
- Q10.10 Whether the user can disable analytics — not addressed. The policy says communications can be stopped "with your consent" (line 34) but says nothing about analytics opt-out.

**Section 14 — Children and Minors:**
- Q14.2 Age limit enforcement inside the app — the policy states the app "is not intended for children under 13" and "we do not knowingly collect" their data, but there is no statement about how this is enforced (no age gate, no date-of-birth field, no parental consent flow).
- Q14.3 Date of birth — the app collects `age_group` (e.g., "25-34") but not date of birth. The difference is not clarified.

**Section 15 — Storage, Retention, Deletion:**
- Q15.3 Country/region where data is stored — not stated. Supabase and Upstash may store data outside Bahrain. This is a material omission under GCC data localisation considerations.
- Q15.4 Backups — not mentioned.
- Q15.6 Deletion period for logs (audit_log, search_logs) — not stated. The `admin_audit_log` table is described in CLAUDE.md as permanent security-event storage; no retention limit is disclosed.
- Q15.7 Deletion period for prompts/AI outputs — not mentioned. OpenAI API calls are made per-request; whether OpenAI retains them under its data sharing program is covered indirectly in Section 11, but no explicit retention window is given.
- Q15.9 Partial deletion (delete only comparison history without deleting account) — not addressed.
- Q15.13 Who has permission to view user data — not stated. Admin access via `X-Admin-Key` is not disclosed.

**Section 16 — Security:**
- Q16.8 Encryption at rest — not mentioned.
- Q16.9 Incident response plan — not mentioned.

**Section 17 — Product and Store Links:**
- Q17.9 Disclaimer that price and availability may change — the privacy policy does not address this (it is partially covered in the ToS, see Section 3 below).

**Additional structural gaps:**
- The document still uses the brand name "SmartCompare" throughout, not "Qaren." The contact email `privacy@smartcompare.app` uses the old domain.
- The opt-out path referenced in Section 11 (`Settings → Privacy → "Help improve AI quality"`) does not exist in the current frontend.
- No mention of the referral system and what data it processes (share tokens, abuse-detection device fingerprints, push notifications to referrers).
- No mention of the cohort personalization system: that Fillout survey responses were used to build aggregate priors, or that new users may have preferences seeded from population cohorts without explicit action.

---

# SECTION 3: Terms of Service — What It Covers vs. Gaps

**File:** `app/legal/terms_of_service.md`
**Date stated in the doc:** `*Last Updated: March 26, 2026*` (line 3)
**Date hardcoded in `legal_routes.py`:** `"last_updated": "2026-03-26"` (line 30) — matches.
**Draft status:** Opens and closes with `*DRAFT — This document is a template. The business and legal team must review and finalize before publication.*` (lines 7 and 98). Served publicly.
**Entity name:** Still "SmartCompare — Product Comparison App" (line 3); uses "SmartCompare" throughout.

**Topics addressed:**

- Acceptance mechanism (Section 1): "By downloading, installing, or using the SmartCompare application..." (line 10). No explicit checkbox consent at registration is described.
- Service description (Section 2): Lists electronics, groceries, supplements, cosmetics, fashion, fragrances. (lines 14-19)
- Account rules (Section 3): Accuracy requirement, credential responsibility, 13-year minimum age, one-account rule, no automated creation. (lines 22-27)
- Acceptable use (Section 4): 7 prohibitions including reverse engineering, rate-limit circumvention, scraping, malicious input, and "automated purchasing decisions without human review." (lines 30-37)
- IP ownership (Section 5): App IP belongs to SmartCompare; product data belongs to respective owners; comparison history/preferences belong to the user. (lines 40-43)
- Disclaimers (Section 6): "AS IS" and "AS AVAILABLE" disclaimer. Specific callouts for price accuracy ("Prices marked as 'estimated' are approximations"), spec accuracy, review accuracy ("AI-generated aggregations"), and recommendation disclaimer ("do not constitute professional advice"). (lines 46-52)
- Liability limitation (Section 7): Excludes liability for purchasing decisions, inaccurate data, downtime, data loss, indirect damages. (lines 55-60)
- Account termination (Section 8): User self-deletion available; company can suspend for ToS violations. (lines 63-67)
- Modification of terms (Section 9): Material changes communicated through the app; continued use = acceptance. (line 71)
- Governing law (Section 10): "Kingdom of Bahrain" (line 75).
- Dispute resolution (Section 11): Informal negotiation first, then "competent courts in the Kingdom of Bahrain." (lines 79-80)
- Smart Decision Referrals (Section 12): Describes reward mechanics (Deep Review credit, 5/10 comparisons per conversion, 15/month cap, 3-shares/week limit), abuse detection signals ("device fingerprints, email validation, and behavior signals"), and reward terms ("no cash value," "expire 30 days after grant"). (lines 82-87)
- Smart Decision Notifications (Section 13): Describes notification types (review insights, peer-decision updates, 14-day retrospectives), frequency cap ("up to 1 re-engagement notification per week"), and opt-out path (`Settings → Notifications`). (lines 90-92)
- Contact (Section 14): `legal@smartcompare.app` (line 95). Domain mismatch — app is Qaren.

**Gaps vs. question checklist:**

**Section 6 — AI (checklist):**
- Q6.2/Q6.3 Which AI provider / data sent to external AI — the ToS describes the app as "AI-powered" (line 15) but does not name OpenAI or describe what user data is transmitted for AI processing. This is handled partially in the privacy policy (Section 11) but absent from the ToS entirely.
- Q6.12 Guardrails / safety measures — not mentioned. The ToS prohibits the user from uploading "malicious content" (line 35) but does not describe what the service itself does to prevent harmful or misleading outputs.
- Q6.13 In-app AI disclaimer — not referenced in the ToS. Section 6 has the disclaimer of warranties for recommendations, but there is no mention of an in-context AI disclaimer screen or label shown to users at the point of receiving a comparison result.
- Q6.15 User ability to delete AI history — the ToS says account deletion removes "all your data" (line 65) but does not address whether individual comparison history or AI outputs can be deleted independently.

**Section 11 — Notifications (checklist):**
- Q11.3 Whether push notification opt-in is obtained — Section 13 of the ToS describes notifications but does not state that users must opt in before receiving push notifications, or how that consent is obtained.
- Q11.6/Q11.8 Unsubscribe method — the ToS says "Disable any type in *Settings → Notifications*" (line 92). This is stated but there is no mention of email unsubscribe or whether consent records are stored.

**Section 12 — Payments (checklist):**
- Q12.1-Q12.9 (entire payments section) — not addressed in the ToS at all. The freemium model (3 lifetime free comparisons, 10/month free, premium tier at 70/month) is implemented in the backend (`usage_service.py`) but not mentioned in the ToS. There is no statement about subscription pricing, how users upgrade, what payment processor is used, refund policy, or what happens to the premium tier on account deletion.

**Section 13 — UGC (checklist):**
- Q13.1/Q13.2 User comments or reviews — not addressed. The ToS describes the app as a comparison tool but does not clarify that users cannot publish reviews visible to other users, which could be mistaken for a UGC platform.
- Q13.3 User image uploads — the ToS covers prohibited uses (malicious uploads, line 35) but does not describe the camera/image-picker flow, what images are processed, or that they are not stored.

**Section 17 — Product and Store Links (checklist):**
- Q17.6 Agreements with stores — not mentioned. The ToS states that product data "belongs to their respective owners" (line 42) but does not address whether there are commercial agreements with retailers whose prices are displayed.
- Q17.8 Affiliate links — not mentioned at all. If the app ever adds affiliate links, this omission would be a material disclosure failure.
- Q17.9 Price/availability disclaimer — the Section 6 disclaimer covers price accuracy ("may not reflect current retail prices," line 49) but does not include a real-time availability disclaimer or a prompt for users to verify before purchasing.
- Q17.10 Liability for third-party stores — the ToS limits SmartCompare's own liability but does not address the liability of the third-party retailers whose links are surfaced.

**Section 19 — Legal Texts Inside the App (checklist):**
- Q19.3 Whether users agree to ToS during registration — not described in the ToS itself. The acceptance clause says "By downloading, installing, or using" (line 10) which is a browsewrap model. There is no reference to a registration-time checkbox or explicit consent click.
- Q19.4 Consent screen for survey/onboarding — not mentioned.
- Q19.5 In-app AI disclaimer before/after recommendation — not referenced.
- Q19.6 Beta disclaimer — not mentioned, despite the document itself being marked DRAFT.

**Additional structural gaps:**
- The entity name "SmartCompare" is used throughout; needs to be "Qaren" (or the legal entity behind it).
- Contact email `legal@smartcompare.app` uses the old domain.
- No governing law statement for the referral or notification sections specifically (Sections 12-13 of ToS reference no jurisdiction).
- No mention of what constitutes a "real comparison" for Loop 2 referral redemption, leaving the abuse-detection criteria opaque to users despite the ToS describing abuse detection signals.

---

# SECTION 4: app.json Store Config Snapshot

**File:** `SmartCompareApp/app.json`

**App identity:**
- Display name: `"Qaren"` (line 3)
- Slug: `"qaren"` (line 4)
- Version: `"1.0.0"` (line 5)
- Orientation: `"portrait"` (line 6) — portrait-only, no landscape.
- User interface style: `"light"` (line 8) — light mode only, no dark mode support declared.
- New architecture: `"newArchEnabled": true` (line 9) — Expo new architecture is active.

**iOS configuration (`ios` block, lines 15-19):**
- Bundle identifier: `"com.qaren.app"`
- `"supportsTablet": true` — the app declares iPad support. Note: the codebase is `orientation: "portrait"` only; tablet support without landscape layout may raise App Review concerns on larger iPad screens.
- `"usesAppleSignIn": true` — Sign in with Apple is declared in the config. CLAUDE.md notes "Apple Sign-In: deferred — requires Apple Developer subscription ($99/year); code is ready." The `expo-apple-authentication` plugin is listed (line 53), so the entitlement will be requested at build time even though the feature is not live.

**Android configuration (`android` block, lines 21-28):**
- Package name: `"com.qaren.app"` (line 22)
- Adaptive icon: foreground `"./assets/adaptive-icon.png"`, background `"#ffffff"` (lines 24-26)
- `"edgeToEdgeEnabled": true` (line 27) — Android edge-to-edge display enabled.
- `"predictiveBackGestureEnabled": false` (line 28) — Android predictive back gesture disabled.

**Splash screen (lines 12-14):**
- Image: `"./assets/splash-icon.png"`, resize mode `"contain"`, background `"#ffffff"`

**Icon:** `"./assets/icon.png"` (line 7)

**Plugins (lines 32-62) — verbatim permission strings:**

| Plugin | Permission string |
|---|---|
| `expo-secure-store` | No permission string (uses iOS Keychain / Android Keystore, no runtime prompt) |
| `expo-localization` | No permission string (reads device locale, no prompt) |
| `expo-camera` | `"cameraPermission": "Qaren needs camera access to photograph products for comparison."` (line 39) |
| `expo-image-picker` | `"photosPermission": "Qaren needs photo library access to identify products from your photos."` (line 43) |
| `@react-native-google-signin/google-signin` | `"iosUrlScheme": "com.googleusercontent.apps.21336192767-38hi4t1ac23089iau7jdog1f43oc7rdm"` (lines 48-50) — iOS reverse client ID for Google OAuth, not a permission string. Exposes the Google OAuth client ID in the public config file (this is normal — OAuth client IDs are public by design). |
| `expo-apple-authentication` | No plugin config (just the plugin name, line 53) |
| `expo-build-properties` | iOS: `"networkInspector": false` (lines 56-60) — disables Expo network inspector in production builds. |

**Permissions not declared in app.json but present in runtime behavior:**
- Push notification permission — `expo-notifications` is used in the codebase (`pushTokenService.tryRegisterPushToken()`) but the `expo-notifications` plugin is not listed in `app.json`. This means the `NSUserNotificationUsageDescription` (iOS) and associated Android permission may not be automatically injected into the native manifest at build time, which could cause runtime failures or App Review rejection.
- Microphone — not declared (correct, the app does not use the microphone).
- Location — not declared (correct, precise location is not used).
- Tracking / ATT (`NSUserTrackingUsageDescription`) — not declared. If any third-party SDK (Google Sign-In) triggers ATT on iOS 14.5+, this will need to be present.

**Store reviewer notes:**
- The `web` block (lines 29-31) includes a favicon entry — this is for Expo web builds, not relevant to native store submission.
- No `scheme` (deep-link URL scheme) is declared in app.json despite the codebase using `qaren://` deep links for referral landing and push notification handling. This is likely configured elsewhere (e.g., EAS build config or bare workflow) but is absent from the visible `app.json`.
- No `privacy`, `supportURL`, or `marketingURL` fields are declared — these must be supplied separately in App Store Connect and Google Play Console, not in `app.json`.
