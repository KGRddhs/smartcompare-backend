# Bundle D — TestFlight Internal Tester Invite Runbook

**Task:** 3.N.2 (ASC upload + TestFlight invite). Runbook for Ahmed to execute AFTER `eas submit` lands the production build in ASC.
**Author:** native-ops
**Date drafted:** 2026-05-23
**Prerequisites:**
- Task 3.N.1 EAS production build complete → `.ipa` uploaded to ASC via `eas submit --profile production --platform ios --latest`
- App Store Connect access (Ahmed Apple ID at developer.apple.com with App Manager role on the Qaren app record)
- Bundle ID `com.qaren.app` claimed in ASC (Task 1.N.1 complete)
- Apple Developer Team ID `8K562M549D` configured in EAS
- iPhone with TestFlight app installed (Ahmed device)
- A4 Sentry sourcemap upload enabled (commit `43cca75`) — crashes will resolve to original TS/TSX source lines

## Time budget

- ASC processing of upload: **~30 min** (R8 — Apple's static analyzer pass + Privacy Manifest check + IPA validation)
- Internal test group setup: ~5 min
- Email invite delivery: ~1 min (usually instant)
- TestFlight app install + accept + Qaren install: ~3 min
- Cold-start smoke + Sentry first-crash check: ~5 min
- **Total Phase 3.N.2 window:** ~45 min from `eas submit` complete to "Ahmed has Qaren running on iPhone"

## Step-by-step

### Step 0 — Confirm ASC received the upload
```bash
# After eas submit completes:
cd C:\Users\SynAckITPC\Documents\ai\smartcompare-bundle-d\SmartCompareApp
eas submit:list --platform ios --limit 1
# Expect: "Submission completed" status with ASC build number
```

Or via ASC web UI:
- https://appstoreconnect.apple.com → My Apps → **Qaren**
- TestFlight tab → **Builds** section
- Newest build shows "Processing" status (Apple's ~30-min validation)
- DO NOT proceed until status flips to "Ready to Submit" or "Ready to Test"

### Step 1 — Wait for "Ready to Test" status
While waiting (~30 min), Ahmed can:
- Sip coffee
- Verify the Apple Sign-In Service ID `app.qaren.signin` is still active at https://developer.apple.com/account/resources/identifiers/list/serviceId
- Verify Supabase Auth Apple provider toggle stays ON at https://supabase.com/dashboard/project/qulajmyxdbdkchvecmvc/auth/providers

When status flips to "Ready to Test" (sometimes shows "Ready to Submit" first then transitions), proceed to Step 2.

**If Apple rejects the upload** (rare for first internal-only submission):
- Common rejection causes: missing Privacy Manifest reason codes (our 4 in `app.json:21-42` should cover the iOS 17+ requirement), missing app icon (A5 unresolved — if Ahmed shipped placeholder concentric circles, ICN-0001 rejects this here; see Task 32 status), missing required Info.plist usage strings (cameraPermission + photosPermission already at app.json:71/77).
- Apple's rejection email arrives within ~30 min of upload completion. Cite the rejection code and ping native-ops; a fix-up + re-`eas submit` is usually <1 hour turnaround.

### Step 2 — Create Internal Test Group
ASC web UI:
- TestFlight tab → **Internal Testing** in left sidebar → click **+** (Create New Test Group)
- Group name: `Qaren Internal` (Ahmed picks)
- Click **Create**

### Step 3 — Add Ahmed's Apple ID to the test group
- Click into the `Qaren Internal` group
- **Testers** sub-tab → **+** (Add Testers)
- Enter Ahmed's Apple ID email (the one signed in to the test iPhone)
- Click **Add**

ASC sends an invite email immediately. Internal testers (max 100, must be team members in App Store Connect) skip Apple's beta review — so the build is testable as soon as it appears in the group.

### Step 4 — Attach the build to the group
- Same group page → **Builds** sub-tab
- Find the newest build (the one from `eas submit` in Step 0)
- Click **+** next to the build OR drag the build into the group's slot

If the build isn't visible:
- Check the **Builds** section at the top-level TestFlight tab to confirm it's still "Ready to Test"
- Sometimes the group's Builds dropdown takes ~30s to refresh after a build state change

### Step 5 — Ahmed installs TestFlight + accepts invite + installs Qaren
On iPhone:
1. App Store → search "TestFlight" → install (if not already installed)
2. Open invite email from Apple ("Test [Qaren — Compare Smart] in TestFlight")
3. Tap **View in TestFlight** → opens TestFlight app
4. Tap **Accept** → tap **Install** → Qaren installs
5. Tap **Open** → cold-start

Alternatively, if the invite email is missed: open TestFlight app → it auto-detects builds the signed-in Apple ID has access to → Qaren appears in the **Apps** list.

### Step 6 — Cold-start smoke (Ahmed)
Verify the following touch-points work without crash:
- App launches past splash → onboarding step 1 renders
- Tap through onboarding 1 → 17 (no need to fill demographics survey fully; just tap through)
- Forced sign-in at Step 16 → Apple Sign-In button works (R4 + R14 chain — Service ID + Supabase provider + entitlement all green)
- Google Sign-In also works (parity, pre-Bundle-D verified)
- Reach HomeScreen
- Run one text comparison (e.g., "iPhone 16 vs Galaxy S25")
- Run one camera comparison (snap a photo of any product)
- Navigate to History tab → see the 2 comparisons just made
- Navigate to Profile tab → see preferences toggles + the new `العربية` language switch
- Settings → toggle a sub-toggle (R18 Profile optimistic toggles) → verify no crash

### Step 7 — Sentry crash triage (first hour)
If ANY crash during Step 6:
- https://sentry.io → qaren-rr organization → react-native project → Issues tab
- Filter by `release:com.qaren.app@1.0.0+<build_number>` (the build number is in ASC TestFlight tab)
- Click into the issue → "View Stack Trace"
- **With A4 enabled (`43cca75`):** stack trace shows original TypeScript line numbers + file paths like `src/screens/HomeScreen.tsx:142`. Otherwise it'd show minified Hermes line numbers like `index.bundle:38427:11` (useless for triage).
- Native-ops can be pinged with the Sentry issue URL for SDK-side fixes; frontend can be pinged for screen-component fixes.

If NO crash during Step 6:
- Ahmed pings team-lead "TestFlight smoke GREEN, ready for additional internal testers"

### Step 8 — Add additional internal testers (optional, after Step 7 green)
Per CLAUDE.md "Canary phasing: with <10 testers pre-launch":
- Same Internal Testing group → **Testers** sub-tab → **+** → add 1-9 more Apple IDs of Ahmed's choosing
- Each new tester receives the invite email; flow from Step 5 onward repeats per-tester

Stay under 100 internal testers (Apple's hard cap; we won't approach it for v1).

## What this runbook does NOT cover (intentional)

- **External Testing** (Apple beta review ~24-48h turnaround, up to 10,000 testers): skip for v1; only flip to External when Ahmed wants public TestFlight link sharing. Internal-only is sufficient for soft-launch + Phase 4 close-out.
- **App Store production submission**: blocked on Task #32 asset replacement (real branded icons vs current Expo placeholders). When that lands, dispatcher will queue the production submit step separately.
- **App Review** for App Store listing: separate ASC workflow; only triggered when Ahmed clicks "Submit for Review" after entering all metadata per `docs/plans/bundle-d-asc-submission-checklist.md`.

## Rollback / recovery recipes

- **Bad build (crashes on cold start):** ASC TestFlight → click into the build → **Expire Build**. Old testers' app installs continue working (they have the bundle locally), but new installs can't pull the bad build. Triggers a new `eas build --profile production --platform ios` + `eas submit` cycle.
- **Tester locked out (TestFlight app says "expired build"):** the build expires 90 days after upload. Push a new build before that; ASC sends a reminder email at 14 days remaining.
- **Sentry doesn't show crashes:** verify `SENTRY_AUTH_TOKEN` env var visible in `eas env:list --environment production`. If absent, the post-A4 sourcemap upload silently failed; re-run `eas env:create --name SENTRY_AUTH_TOKEN --visibility secret --environment production` and rebuild.
- **Apple Sign-In returns "invalid id_token":** R4 green (Supabase provider enabled), R14 green (entitlement injected at prebuild). If still broken, native-ops checks the device's `Settings → Apple ID → Sign-In with Apple → see Qaren listed` and removes/re-adds the trust. Usually one of: (a) Service ID `app.qaren.signin` `Client IDs` field in Supabase missing one of the two audiences (`app.qaren.signin,com.qaren.app`), (b) nonce mismatch between client + Supabase validation.

## Verification commands (post-Step-6)

```bash
# Verify Sentry sees the build:
# (open https://sentry.io/issues/?project=react-native&query=release%3A1.0.0)

# Verify the install fingerprint shows up in the device-fingerprint table:
# (Supabase SQL editor query):
#   SELECT id, email, device_fingerprint_hash, created_at FROM users
#   ORDER BY created_at DESC LIMIT 5;
# Ahmed's user row should have a 64-char hex device_fingerprint_hash.

# Verify backend usage_service counters incremented:
# (Railway logs at https://railway.app/project/...):
#   grep -i "usage.*recorded\|comparison.*saved" | tail -10
```

## Next steps after this runbook completes successfully

- Phase 4 close-out kicks in: native-ops updates CLAUDE.md + MEMORY.md (Task #69), DNS cutover for landing/ via Railway (Task #68), R12 reengagement flag flip on Railway (Task #56 backend), R19 force-update env vars sequencing (Task #57 backend).
- Task #32 Apple submission gate (real branded icons) becomes the blocker for App Store production submission, not TestFlight internal.
- R8 (ASC 30-min upload window) flips from PENDING to ADDRESSED via the Step 1 wait observation.

## Authority + verification trail

This runbook anchors on:
- R4 (Apple 3-leg checkpoint) ADDRESSED — backend `faead5e`
- R5 (`expo-apple-authentication` plugin) ADDRESSED — native-ops `03cdc1e`
- R14 (Sign-In-with-Apple entitlement BOTH-gate) ADDRESSED — native-ops `3095304`
- A4 (Sentry sourcemap upload) ENABLED — native-ops `43cca75`
- Privacy Manifest (`app.json:21-42`) shipped — native-ops `10ff816`
- Bundle ID `com.qaren.app` + Team ID `8K562M549D` confirmed via Ahmed A3-A7 session
- Privacy Nutrition Labels draft at `docs/plans/bundle-d-asc-privacy-nutrition-labels-draft.md` — awaits Ahmed D1-D11 sign-off

All artifacts above are committed on `feature/bundle-d-testflight-readiness`.
