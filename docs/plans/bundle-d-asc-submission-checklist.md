# Bundle D — App Store Connect Submission Checklist + Metadata Draft

**Task:** 3.N.2-prep (pre-build for Phase 3 ASC upload + TestFlight invite)
**Author:** native-ops
**Date drafted:** 2026-05-23
**Status:** DRAFT — Ahmed signs off § "Ahmed-decision rows" + § "Metadata draft" before Phase 3.

## Why this exists

Phase 3 Task 3.N.2 (`eas submit --profile production --platform ios --latest` → ASC upload → TestFlight invite) involves Ahmed pasting ~12 free-text fields into the ASC web UI. Pre-drafting these lets the upload window (~30 min Apple processing per R8) finish without us still typing fields. Same idle-leverage pattern used for Privacy Nutrition Labels (Task 3.N.3 drafted in Phase 1).

## Ahmed-decision rows (sign off each before ASC submission)

| # | Field | Char limit | Draft | Ahmed sign-off |
|---|---|---|---|---|
| 1 | App Name (listing title) | 30 | **Qaren — Compare Smart** (20 chars) | ☐ |
| 2 | Subtitle | 30 | **Smart Compare for the GCC** (24 chars) — or — **Compare products instantly** (26 chars) | ☐ |
| 3 | Promotional Text | 170 | see § Metadata draft | ☐ |
| 4 | Description | 4000 | see § Metadata draft | ☐ |
| 5 | Keywords (comma-sep) | 100 | see § Metadata draft | ☐ |
| 6 | Privacy Policy URL | — | `https://qaren.app/privacy.html` (post-Vercel-cutover) OR Railway endpoint as fallback (see § fallback) | ☐ |
| 7 | Support URL | — | `https://qaren.app/support` (post-Vercel-cutover) OR Ahmed Gmail mailto: as fallback | ☐ |
| 8 | Marketing URL (optional) | — | `https://qaren.app/` OR LEAVE BLANK | ☐ |
| 9 | Copyright | — | `© 2026 Qaren` — placeholder until legal entity name decided (one of the 25 DECISIONS REQUIRED items in `docs/plans/2026-05-06-tos-fact-base.md`) | ☐ |
| 10 | Primary Category | — | Shopping | ☐ |
| 11 | Secondary Category (optional) | — | Lifestyle | ☐ |
| 12 | Age Rating | — | 12+ (per CLAUDE.md "Age policy locked: 13+ general audience"; Apple's 12+ rating maps to "13+ general audience" — do NOT enroll in Kids/Families) | ☐ |
| 13 | Content Advisory (within age rating) | — | None of the optional flags apply (no gambling, no profanity, no mature themes) — leave all toggles OFF | ☐ |
| 14 | Demographics | — | Audience: 13+; Languages: English, Arabic | ☐ |
| 15 | Pricing | — | Free | ☐ |
| 16 | Availability (countries) | — | Bahrain, Saudi Arabia, UAE, Kuwait, Qatar, Oman (the 6 GCC countries from CLAUDE.md project purpose). Optionally extend to all of MENA later. | ☐ |
| 17 | App Privacy (Nutrition Labels) | — | See `docs/plans/bundle-d-asc-privacy-nutrition-labels-draft.md` (commit `5b24dee` + correction `8101248`) | ☐ |

---

## Metadata draft

### Promotional Text (170-char limit — editable any time without resubmitting binary)

```
The smartest way to compare products in the Gulf. Get instant verdicts on electronics, supplements, fragrances, and more — sourced from authorized retailers.
```

165 chars. Editable any time, so safe to iterate post-launch.

### Description (4000-char limit)

```
Qaren is the GCC's intelligent product comparison engine. We give you a clear, confident answer about which product is right for YOU — not just a side-by-side spec sheet.

WHAT MAKES QAREN DIFFERENT

• Real prices from authorized retailers across Bahrain, Saudi Arabia, UAE, Kuwait, Qatar, and Oman — not just inflated US dollars converted at random rates.
• AI verdicts in seconds. Tell us what matters to you (battery life, build quality, value for money) and we surface the product that fits your priorities.
• Camera-first product capture. Snap a photo of any product and we identify it, find its competitor, and tell you which one wins.
• Personalized to your cohort. Qaren learns from people in your region, age range, and lifestyle — so you get advice that matches your context, not generic recommendations.
• Honest about uncertainty. Every comparison shows our confidence level. When prices are estimated or specs are unverified, we say so clearly.

WHAT YOU CAN COMPARE

• Electronics — phones, laptops, headphones, tablets, smartwatches
• Supplements & health — vitamins, protein, omega-3, multivitamins (with Bahrain pharmacy authorized brand data)
• Beauty — makeup, skincare, haircare
• Fragrances — including luxury houses
• Fashion
• Grocery

DESIGNED FOR THE GCC

Qaren respects local context. We show BHD/SAR/AED prices, surface retailers that actually deliver to your country, and offer the app fully in English and Arabic with proper right-to-left support.

PRIVACY-FIRST

We don't sell your data. We don't track you across apps. We don't run third-party advertising. You can opt out of AI quality improvement at any time. Read our privacy policy to see exactly what we collect (it's not much) and why.

COMING SOON

• Voice input for hands-free comparisons
• Decision insights from people in your cohort
• Re-engagement reminders for products you saved

Qaren is in active development. Your feedback shapes what we build next.

Questions, suggestions, or want to report a bug? Email us at support@qaren.app.

© 2026 Qaren. All rights reserved.
```

~1950 chars. Well under the 4000-char limit. Easy to extend later.

### Keywords (100-char limit, comma-separated)

```
compare,GCC,Bahrain,Saudi,UAE,Kuwait,Qatar,Oman,shopping,products,reviews,prices,smart,AI,verdict
```

96 chars. Apple does NOT count spaces between commas, so the cleanest format is `a,b,c` with no spaces. Each word indexes independently.

**Discarded candidates** (over 100-char limit if added): `electronics`, `supplements`, `cosmetics`, `fragrances`, `iherb`, `ounass`, `noon`. The 6-country list ate ~30 chars; trim further if Ahmed wants more product-category keywords. Safe to iterate via ASC; keywords editable any time.

---

## Privacy URL fallback strategy

Apple requires a working Privacy Policy URL at submission. The intended URL is `https://qaren.app/privacy.html` post-Vercel-cutover (Phase 2 Task 2.N.2). If ASC submission happens BEFORE the cutover, fallback options:

1. **Railway endpoint:** `https://web-production-58776.up.railway.app/api/v1/legal/privacy_policy` — works today (Task 1.B.1 routing fix in commit `eeaea11`); returns the markdown which renders browser-readable. Apple accepts.
2. **GitHub Pages fallback:** if for some reason Vercel deploy stalls, the `landing/` directory could be pushed to a `gh-pages` branch and served at `https://kgrddhs.github.io/smartcompare-backend/privacy.html` in ~5 min. Listed in DNS runbook rollback.

Update Apple's Privacy URL via ASC web UI any time post-submission — does NOT require resubmitting binary.

## Support URL fallback strategy

Same situation. Intended: `https://qaren.app/support` (post-cutover; resolves to `support.html` via `cleanUrls: true`).

Fallback: `mailto:support@qaren.app` directly. Apple accepts mailto URLs for the Support URL field.

---

## App Privacy Manifest (PrivacyInfo.xcprivacy)

**Risk:** Apple requires the `PrivacyInfo.xcprivacy` privacy manifest for iOS 17+ SDK use (enforced since May 2024). Apps with restricted-reason API usage missing declared reasons trigger an Apple email warning post-submission, and in some cases a soft rejection.

**Current state:** Verified via Context7 `/expo/expo` docs + Grep on `SmartCompareApp/app.json`:
- ZERO `privacyManifests` block in `app.json`
- ZERO `NSPrivacyAccessedAPIType` declarations anywhere
- Spot-checked 3 Expo packages: `expo-notifications` ships its own `PrivacyInfo.xcprivacy` in `node_modules/expo-notifications/ios/`; `expo-secure-store` + `expo-camera` do NOT.

Per Expo docs ("Privacy manifests > Configuration in app config"): "Apple does not correctly parse all the PrivacyInfo files included by static CocoaPods dependencies such as Expo SDK packages... You may need to include the required reasons for the APIs used by those dependencies in your app's PrivacyInfo.xcprivacy file or the configuration in the app.json."

**Likely required reason codes for Qaren** (based on the 13 plugins in `app.json` + standard React Native runtime APIs):

```json
{
  "expo": {
    "ios": {
      "privacyManifests": {
        "NSPrivacyTracking": false,
        "NSPrivacyAccessedAPITypes": [
          {
            "NSPrivacyAccessedAPIType": "NSPrivacyAccessedAPICategoryUserDefaults",
            "NSPrivacyAccessedAPITypeReasons": ["CA92.1"]
          },
          {
            "NSPrivacyAccessedAPIType": "NSPrivacyAccessedAPICategoryFileTimestamp",
            "NSPrivacyAccessedAPITypeReasons": ["C617.1"]
          },
          {
            "NSPrivacyAccessedAPIType": "NSPrivacyAccessedAPICategorySystemBootTime",
            "NSPrivacyAccessedAPITypeReasons": ["35F9.1"]
          },
          {
            "NSPrivacyAccessedAPIType": "NSPrivacyAccessedAPICategoryDiskSpace",
            "NSPrivacyAccessedAPITypeReasons": ["E174.1"]
          }
        ]
      }
    }
  }
}
```

Reason code rationale:
- **`CA92.1`** UserDefaults — React Native uses `NSUserDefaults` internally. Reason `CA92.1` = "Read/write access to data within the same app."
- **`C617.1`** FileTimestamp — Expo file system access (image-picker, camera, secure-store all touch files). Reason `C617.1` = "Provide functionality requested by user."
- **`35F9.1`** SystemBootTime — `@sentry/react-native` reads `mach_absolute_time` for performance tracing. Reason `35F9.1` = "Measure time elapsed."
- **`E174.1`** DiskSpace — Reanimated + image-picker may check available disk for media operations. Reason `E174.1` = "Display free disk space to user." (alternatively `85F4.1` if just operational, not user-facing)

**`NSPrivacyTracking: false`** — confirmed during Privacy Nutrition Labels drafting (no third-party advertising SDKs, no IDFA access).

**`NSPrivacyTrackingDomains`** — empty array OR omit entirely. We don't have any.

**`NSPrivacyCollectedDataTypes`** — Apple primarily reads this from the App Privacy Nutrition Labels (Task 3.N.3 doc) entered via ASC web UI, not from the manifest file. Can be omitted from app.json.

**Recommended Phase 2/3 commit (separate from this checklist):** add the `privacyManifests` block to `app.json`. Will trigger Expo prebuild to write `ios/Qaren/PrivacyInfo.xcprivacy` during the next EAS build. **CAUTION:** EXACT reason codes need verification against actual code usage; some Expo SDK 54 packages auto-add to the manifest at prebuild time and may conflict with manual entries. Recommend a separate commit AFTER the first EAS preview build (Task 2.N.1) so we can inspect the generated `PrivacyInfo.xcprivacy` and confirm what's already included. Filed as new task 40.

---

## EAS production-build credentials block (pre-stage for Task 3.N.1)

Currently `eas.json` `production` profile has no `ios.credentials` block. First production build runs `eas credentials -p ios --profile production` interactively to create Apple Distribution cert + provisioning profile.

EAS Build's auto-managed credentials flow (default) handles this without explicit `ios.credentials` config — recommend NOT pre-staging, let EAS prompt during Ahmed's first build. The interactive flow asks for Apple ID + password; uses the Team ID `8K562M549D` we already have; creates the dist cert + profile on Apple Dev Portal. This is the recommended path per EAS docs.

If we later want explicit local-credentials management, `eas.json` can grow:
```json
{
  "build": {
    "production": {
      "ios": {
        "credentialsSource": "remote",
        "autoIncrement": true
      }
    }
  }
}
```

Leave default (no explicit `credentialsSource`) for first build; revisit if reproducibility becomes an issue.

## Build version + version-source

Already correct in repo:
- `app.json:5` `expo.version: "1.0.0"` — first App Store version.
- `eas.json:4` `appVersionSource: "remote"` — EAS owns build numbers (auto-increments via `production` profile `autoIncrement: true` at `eas.json:23`).

First production build will be marketing version `1.0.0` build `1`. Subsequent builds increment build number only.

## Screenshots

Apple requires:
- 6.7" iPhone (e.g., iPhone 15 Pro Max, 1290×2796) — 1-10 screenshots, minimum 1
- 6.5" iPhone (e.g., iPhone 11 Pro Max, 1242×2688) — alternative to 6.7", recommended both
- iPad Pro 12.9" (2048×2732) — required if `ios.supportsTablet: true` in app.json (it IS true per `app.json:18`)
- App Preview videos optional (15-30s)

**Action item for Ahmed:** capture screenshots from the EAS preview build (Task 2.N.1). Need at minimum:
- Onboarding step 1 (Cal-AI-Lite intro)
- Onboarding step 14 (theatrical loading 3.2s)
- HomeScreen with TwoInputShell (Bundle B redesign)
- Results / Winner Reveal screen
- Cohort badge moment
- History tab populated

Native-ops can write the screenshot capture runbook + recommend sequence; actual capture needs the running iOS Simulator + iPad simulator. Filed as follow-up task 41.

## TestFlight beta-tester invite path

Per `eas submit --profile production --platform ios --latest`:
1. Wait ~30 min Apple processing (R8) — build appears in TestFlight tab with "Processing" → "Ready to Submit" → "Ready to Test."
2. Create internal test group in ASC > TestFlight > Internal Testing. Add Ahmed's Apple ID email.
3. Ahmed opens TestFlight app on iOS → tap "Redeem" or click invite link from email → install Qaren → cold-start smoke.
4. Cold-start verdict: Google Sign-In + Apple Sign-In + camera capture + text query + auth flow.

External test group (max 10,000 users) requires Apple's beta review — typically 24-48h turnaround. Internal test group (max 100, must be team members in App Store Connect) skips beta review. **First TestFlight build = INTERNAL ONLY** (just Ahmed) per CLAUDE.md "Canary phasing: with <10 testers pre-launch."

---

## Apple-required collateral (not metadata; just ASC asset checklist)

| Asset | Status | Notes |
|---|---|---|
| App icon (1024×1024 PNG opaque) | A5 BLOCKED — Expo placeholder currently | Per `docs/runbooks/bundle-d-asset-audit-2026-05-23.md` — Apple submission gate ICN-0001 rejects generic create-expo-app icons. MUST resolve before Phase 3 production build. |
| App Preview video (optional) | Out of scope v1 | Adds 5-30% conversion lift; defer to v1.1. |
| Screenshots (6.7" + iPad Pro 12.9") | Pending Phase 2 EAS build | Listed above; runbook to follow. |
| Promotional text | Drafted above (D2) | 165 chars |
| Description | Drafted above (D2) | ~1950 chars |
| Keywords | Drafted above (D2) | 96 chars |
| Build for distribution | Phase 3 Task 3.N.1 | `eas build --profile production --platform ios --non-interactive` |
| Privacy policy URL | Drafted above (D2) | Vercel post-cutover, Railway fallback |
| Support URL | Drafted above (D2) | mailto fallback |
| Privacy Nutrition Labels | Drafted in `bundle-d-asc-privacy-nutrition-labels-draft.md` | D1 sign-off pending |

---

## Decisions required from Ahmed (D-series, extends D1-D5 from Privacy Nutrition Labels)

In addition to D1-D5 (Privacy Nutrition Labels row sign-offs), the following ASC submission decisions need answer before Phase 3:

- **D6:** Sign off on Subtitle final choice — "Smart Compare for the GCC" (24 chars) OR "Compare products instantly" (26 chars) OR alternate suggestion?
- **D7:** Sign off on Description draft above. Open to rewrites; current draft is starting point.
- **D8:** Sign off on Keywords list. Add/remove? (Currently 96/100 chars used; 4-char headroom.)
- **D9:** Marketing URL — leave blank, OR add `https://qaren.app/`?
- **D10:** Copyright string — `© 2026 Qaren` placeholder is fine to ship as-is, OR specify legal entity (e.g., `© 2026 Qaren by Ahmed Eldenari`)?
- **D11:** Privacy Manifest reason codes — accept the 4 I drafted (`CA92.1`, `C617.1`, `35F9.1`, `E174.1`) OR wait for first EAS build to inspect what Expo auto-generates before declaring?

---

## Next actions for native-ops

After Phase 1 close + Phase 2 begins:
1. Inspect generated `ios/Qaren/PrivacyInfo.xcprivacy` from first EAS build (Task 2.N.1) → reconcile with the draft block above → ship `app.json` `privacyManifests` patch as separate commit. (Task 40)
2. Write screenshot capture runbook for Ahmed (Task 41).
3. Substitute Android signing cert SHA-256 placeholder in `landing/.well-known/assetlinks.json` (Task 32 cross-references this).

After all D1-D11 sign-offs:
4. Commit final ASC metadata as paste-ready snippets in this doc (replace any [bracketed] placeholders with Ahmed's final choices).
