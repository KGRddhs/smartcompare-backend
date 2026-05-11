# Bundle A — Pre-launch P0 Fixes — Design

**Date:** 2026-05-11
**Author:** Ahmed + Claude (brainstorm session)
**Status:** Approved — ready for implementation planning
**Bundle:** A of A→B→C→D pre-launch sequence

---

## Why this bundle exists

Pre-launch tester feedback surfaced ~22 distinct complaints. Triage grouped them into 4 bundles; this design covers **Bundle A — P0 fixes that block usable testing.** Bundles B (Arabic deep clean), C (brand polish), D (performance) get their own design docs after Bundle A ships and is verified stable.

**Bundle A is NOT abandoning the deferred items** — it's gating them behind a confirmed-stable Bundle A merge. Each later bundle gets its own brainstorm, design doc, and implementation plan.

---

## Goals + non-goals

**Goals:**
- Kill the `Cannot read property 'products' of undefined` render crash from History
- Wire the four dead `() => {}` handlers in Profile (Preferences, Privacy, Terms, Contact Us)
- Promote inline name-edit to a real `EditProfileScreen`
- Close the word-of-mouth referral gap (no UI to enter a code today)
- Lock the free-tier counter to device fingerprint (anti freebie-farming via re-signup)
- Make every switch row tappable, every Arabic surface actually Arabic
- Guarantee every row visible in History is renderable

**Non-goals (deferred to later bundles, NOT abandoned):**
- Camera 2-product limit (today allows up to 4) → Bundle C
- Category chips emojis → icon glyphs → Bundle C
- Logo glyph inside app headers → Bundle C
- Cal-AI-grade animation polish → Bundle C
- Arabic-as-default → **dropped** (user confirmed device-locale stays)
- Branch.io / AppsFlyer deferred deep-link install survival → Bundle C/D
- Avatar photo upload (initial letter stays in Bundle A) → later (needs S3 + image picker)
- Bundle size / Reanimated profiling / SVG audit → Bundle D
- Phone heat on Expo Go → not a real bug; use EAS dev build to evaluate
- ToS / Privacy policy CONTENT rewrite → owned by `docs/plans/2026-05-06-tos-fact-base.md`, fed by `~/Downloads/legal_policies_app_store_play_guide_english.pdf`

---

## Section 1 — Gift system (referral) completion

**Root cause of "gift system needs fixing":** Today the redemption path is deep-link-only. ReferralLandingScreen → InviteeQuiz → Register with `invite_id` from `route.params`. If a friend tells you the code verbally ("use QR-ATAUX9"), there is no surface in the app to type it. Profile "Copy" puts only the 9-char code on clipboard with no shareable link.

### 1.1 — Code redemption is signup-only (Redeem-A locked, Redeem-D dropped)

**Decision:** Code can ONLY be entered at Register, never post-hoc. Tighter abuse boundary; cleaner Profile; no new endpoint needed.

**Frontend — `RegisterScreen.tsx`:**
- Add optional text input "Have an invite code? (optional)" above Sign Up button
- Format-validate `^QR-[unambiguous-alphabet]{6}$`
- If `route.params.code` arrived via deep link → pre-fill + lock with "× clear" affordance
- Pass `invite_code` in register payload

**Backend — `app/api/auth_routes.py::register()`:**
- Existing payload already accepts `invite_id`. Extend Pydantic `RegisterRequest` to also accept `invite_code: Optional[str]`.
- Server-side: if `invite_code` present and `invite_id` absent, resolve `invite_code → user.referral_code` → create a fresh `referral_invites` row with `source='code_redeem'` → set resolved `invite_id` → continue existing `link_invite_to_user` path.
- Self-referral block: reject if `invite_code == current_user.referral_code` (can't happen at register, but defense-in-depth for future endpoints).
- Reject invalid format → 400 `INVITE_CODE_INVALID`. Unknown code → 404 `INVITE_CODE_NOT_FOUND`.

### 1.2 — Deep link route

**New universal link:** `qaren.app/r/{code}`
- iOS `apple-app-site-association` + Android `assetlinks.json` declare the path
- App-installed → opens `qaren://redeem?code=QR-XXXXXX` → routes to Register pre-filled
- App-not-installed → web fallback shows "Download Qaren and use code QR-XXXXXX" landing page
- **Branch.io deferred deep-link install survival is OUT OF SCOPE** — Bundle A accepts that App Store installs from social shares lose the code at the install wall; user types it manually on Register

### 1.3 — Share message + Copy fix

**New copy** (replaces "compare products in the GCC" framing):

- **EN:** *"I overthink every purchase. Qaren ends the debate in 30 seconds. Try it: https://qaren.app/r/QR-ATAUX9 (or use code QR-ATAUX9 in the app)"*
- **AR:** *"أفكر زيادة قبل أي شراء. قارن يحسم الجدال في 30 ثانية. جربه: https://qaren.app/r/QR-ATAUX9 (أو استخدم رمز QR-ATAUX9 داخل التطبيق)"*

**Liability framing rationale:** "Ends the debate" claims decision *closure*, not decision *correctness* — defensible if reliance theory is ever raised under GCC consumer law. The string is user-shared content (not Qaren advertisement), and the pending ToS clickwrap (`docs/plans/2026-05-06-tos-fact-base.md`) gates anyone who downloads. Two layers of protection.

**Apply everywhere:**
- `ShareBottomSheet.tsx` — pre-fill native share intent with this string
- `ReferralStatusCard.tsx` Copy button — put the full string on clipboard, not just the code
- Add new i18n keys `referrals.share.copy.en` / `referrals.share.copy.ar` with `{code}` interpolation

### 1.4 — Env-var verification (not code)

Confirm `ENABLE_REFERRAL_SYSTEM=true` in Railway. If OFF, the entire `/referrals/*` namespace returns 404 — could be the real root cause of all gift bugs (silent feature flag).

### 1.5 — Tests

- `tests/test_referral_routes.py` — `test_register_with_invite_code`, `test_register_invite_code_invalid_format`, `test_register_unknown_invite_code`
- `tests/test_auth_routes.py` — extend `test_register_links_invite` to cover code-based path
- Frontend Jest — `RegisterScreen` accepts code field; deep-link route pre-fills code; ShareBottomSheet / ReferralStatusCard put correct string on clipboard

---

## Section 1.5 — Device-bound free tier

**Goal:** Prevent freebie-farming via re-signup. User can log out + create a second account on the same device, but the free tier (3 lifetime + 10/month + 3/day) is exhausted from the moment the second account logs in.

### 1.5.1 — Schema

**Migration 021_device_fingerprint_users.sql:**
```sql
ALTER TABLE users ADD COLUMN device_fingerprint_hash TEXT;
CREATE INDEX idx_users_device_fp ON users(device_fingerprint_hash)
    WHERE device_fingerprint_hash IS NOT NULL;
COMMENT ON COLUMN users.device_fingerprint_hash IS
    'SHA-256 hash of expo-application bundle id + expo-device os build id + per-install nonce. Used to lock free-tier counter across re-signups on same device.';
```

Apply via Supabase MCP `apply_migration`, not SQL Editor (per CLAUDE.md).

### 1.5.2 — Frontend fingerprint generation

**New `SmartCompareApp/src/services/deviceFingerprint.ts`:**
```ts
import * as Application from 'expo-application';
import * as Device from 'expo-device';
import * as SecureStore from 'expo-secure-store';
import * as Crypto from 'expo-crypto';

export async function getDeviceFingerprint(): Promise<string> {
  let nonce = await SecureStore.getItemAsync('device_fp_nonce');
  if (!nonce) {
    nonce = Crypto.randomUUID();
    await SecureStore.setItemAsync('device_fp_nonce', nonce);
  }
  const raw = [
    Application.applicationId,
    Device.osBuildId ?? Device.osInternalBuildId ?? '',
    nonce,
  ].join('|');
  return await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    raw,
  );
}
```

The nonce in SecureStore stays stable across app launches but resets on full uninstall — which is the intended grace path: a user who actually uninstalls and reinstalls gets fresh freebies. The nonce makes the hash unique per install, preventing false-positives across two unrelated devices that happen to share `applicationId + osBuildId`.

### 1.5.3 — Register flow change

**Frontend** sends `X-Device-Fingerprint: <hash>` header on `POST /api/v1/auth/register`.

**Backend `register()` (in `auth_routes.py`):**
```python
fp = request.headers.get("X-Device-Fingerprint")
inherited_lifetime = 0
if fp:
    prior = await supabase.table("users") \
        .select("lifetime_comparisons_used") \
        .eq("device_fingerprint_hash", fp) \
        .order("lifetime_comparisons_used", desc=True) \
        .limit(1) \
        .execute()
    if prior.data:
        inherited_lifetime = prior.data[0].get("lifetime_comparisons_used", 0)

new_user = {
    ...,
    "device_fingerprint_hash": fp,
    "lifetime_comparisons_used": inherited_lifetime,
}
```

Subsequent usage tracking is unchanged (still per-user) — the only change is the *starting* value is inherited. The freemium gate in `check_usage_allowed()` then sees `lifetime_used >= limit` and blocks immediately for re-signed-up accounts.

**Edge cases (acceptable):**
- Family share device: 2nd user on same physical phone gets no freebies. Acceptable per product decision.
- Genuine device reset / new device: fingerprint changes → freebies refresh. Intended.
- Premium subscription: per-account, unaffected. User can subscribe on the new account if they want.

### 1.5.4 — Tests

- `tests/test_auth_routes.py` — `test_register_inherits_device_lifetime_counter`, `test_register_without_fingerprint_starts_at_zero`, `test_register_fingerprint_first_signup_starts_at_zero`
- Frontend Jest — `deviceFingerprint.test.ts` verifies SHA-256 stability across calls and nonce persistence

---

## Section 2 — Preferences flow (B2 sequential)

**Replace** `navigation.navigate('Onboarding', { mode: 'edit' })` (dead — Onboarding lives in pre-auth stack) with a real per-question flow.

### 2.1 — Architecture

**New route in MainTabs stack:** `EditPreferences` (modal stack, slide-from-right per page).

**Orchestrator:** new `EditPreferencesFlow.tsx` manages pageIndex state (0..3), local form state for all 4 dimensions, navigation handlers.

**4 pages, one question each:**

| Page | Question | Component | Source |
|---|---|---|---|
| 1 | Priorities — pick up to 3 | Reuse `Step08Priorities` body extracted to `PrioritiesPicker` | Existing |
| 2 | Budget — budget / mid / premium | Reuse `Step09Budget` body extracted to `BudgetPicker` | Existing |
| 3 | Lifestyle — pick 0+ of 11 tags | **New `LifestylePicker`** (chip grid, multi-select) | New ~50 LOC |
| 4 | Brand attitude — radio | Reuse `Step10BrandAttitude` body extracted to `BrandAttitudePicker` | Existing |

### 2.2 — Navigation

- Each page: back arrow (← previous, or close on page 1) + Continue at bottom
- Page 4's button = "Save"
- Save → single `PUT /api/v1/auth/preferences` call with all 4 merged → success toast → pop modal stack → back to Profile
- Cancel = discard all changes, state is local to flow until Save

### 2.3 — Pre-fill + empty-state

- On mount, fetch `GET /api/v1/auth/preferences`
- Pre-fill all 4 pages with current values (works for both `user_stated` and `inferred`)
- Backend auto-flips `_sources` to `user_stated` on save (existing behavior)
- If `GET /preferences` returns 404 (legacy user pre-preferences-system), seed with category defaults so the flow still works

### 2.4 — i18n

- Reuse existing onboarding keys (`onboarding.step08.*`, `onboarding.step09.*`, `onboarding.step10.*`)
- New keys `preferences.lifestyle.*` for 11 tags × 2 locales = 22 strings
- New keys `preferences.flow.continue`, `preferences.flow.save`, `preferences.flow.cancel`, `preferences.saved.toast`

### 2.5 — Tests

- Jest `EditPreferencesFlow.test.tsx` — pre-fill happy path, navigation forward/back, Save calls PUT once with merged payload, Cancel resets, page 4 button label is "Save"
- Component tests for the reused step bodies are already present from onboarding
- No backend changes — existing `PUT /auth/preferences`

---

## Section 3 — EditProfileScreen (Edit-2)

**Goal:** Promote cramped inline name-edit to a real screen consolidating account-level edits.

### 3.1 — Structure

**New route:** `EditProfile` (modal stack from Profile).

| Section | Field | Behavior | Endpoint |
|---|---|---|---|
| Avatar | Circle with initial | **Stub** — non-tappable, "Photo upload coming soon" caption. No upload yet (deferred). | None |
| Display name | Text input | Pre-filled, max 100 chars, Save enables on dirty | Existing `PUT /api/v1/auth/profile` |
| Email | Read-only row showing email address (no edit option) | Display only | None |
| Edit style profile | Row "Edit style profile →" | Opens existing cohort modal (relocated from Profile) | Existing `PUT /api/v1/auth/demographics` |
| Danger zone | "Delete account" red row | Existing confirm flow, relocated from Profile bottom | Existing `delete_user_cascade()` |

### 3.2 — Profile screen cleanup (post-relocation)

- Remove inline name-edit (`setEditingName` + TextInput at lines 323-331)
- Remove "Delete account" row at Profile bottom (relocated)
- Replace green "Edit Profile" link with `navigation.navigate('EditProfile')`

### 3.3 — Removed from scope

- Email change → user said useless, dropped
- Avatar photo upload → deferred (needs S3/Supabase Storage + image picker + crop UI)
- 2FA toggle → not in current product

### 3.4 — i18n

- New keys `editProfile.title`, `editProfile.avatar.placeholder`, `editProfile.section.account`, `editProfile.editStyleProfile`, `editProfile.dangerZone`, `editProfile.deleteAccount`, etc. ~10 strings × 2 locales.

### 3.5 — Tests

- Jest `EditProfileScreen.test.tsx` — pre-fills name/email, save button gates on dirty, opens cohort modal, delete-account confirm flow works
- No backend changes

---

## Section 4 — Support screens (Privacy / Terms / Contact Us)

**Goal:** Wire the three `() => {}` no-op handlers in Profile's Support card.

### 4.1 — LegalScreen (Privacy + Terms shared)

**New `SmartCompareApp/src/screens/LegalScreen.tsx`:**
- Route param `doc: 'privacy' | 'terms'`
- Fetches markdown from existing `GET /api/v1/legal/privacy_policy` or `/terms_of_service`
- Renders via `react-native-markdown-display` (new dep, ~30KB) with Qaren theme tokens
- Loading skeleton; error state with retry; AsyncStorage cache for offline viewing

**⚠ Content note:** Backend markdown at `app/legal/{privacy_policy,terms_of_service}.md` is stale ("SmartCompare" / `@smartcompare.app`). Bundle A wires the *screen*; content rewrite is owned by `docs/plans/2026-05-06-tos-fact-base.md`, fed by `~/Downloads/legal_policies_app_store_play_guide_english.pdf`. Add TODO comment cross-referencing both.

### 4.2 — ContactUsScreen

**New `SmartCompareApp/src/screens/ContactUsScreen.tsx`:**
- Form:
  - Category segmented control: `Bug` / `Suggestion` / `Business Inquiry` / `Other`
  - Subject (optional, max 120 chars)
  - Message (required, max 2000 chars, Submit disabled until ≥10 chars)
  - Submit button
  - Footer link: "Or email us directly →" → `mailto:support@qaren.app`
- POST to existing `/api/v1/feedback` with `feedback_type: contact_us_{category}` + `message: "{subject}\n\n{body}"`
- Success: replace form with static success state — *"Thanks — we read every message. We'll reply within 2 business days if a response is needed."*
- Error: inline error, retry-friendly (idempotent post)
- Client-side rate limit: 1 submission per 30s

### 4.3 — Profile wiring

- `ProfileScreen.tsx:485` Privacy `() => {}` → `navigation.navigate('Legal', { doc: 'privacy' })`
- `ProfileScreen.tsx:491` Terms `() => {}` → `navigation.navigate('Legal', { doc: 'terms' })`
- `ProfileScreen.tsx:497` Contact `() => {}` → `navigation.navigate('ContactUs')`

### 4.4 — i18n

- New keys `legal.loading`, `legal.error.title`, `legal.error.retry`, `legal.offline.banner`
- New keys `contact.title`, `contact.category.bug`, `contact.category.suggestion`, `contact.category.business`, `contact.category.other`, `contact.subject.placeholder`, `contact.message.placeholder`, `contact.submit`, `contact.submit.again`, `contact.success.title`, `contact.success.body`, `contact.error`, `contact.email.fallback`
- ~15 strings × 2 locales

### 4.5 — Tests

- Jest `LegalScreen.test.tsx` — fetches and renders, error state retries, offline cache works
- Jest `ContactUsScreen.test.tsx` — form validation, submits with correct payload, success state, error retry, rate-limit guard
- No backend tests needed (existing `/feedback` + `/legal/*` paths)

### 4.6 — Dependency add

- `npm install react-native-markdown-display` in `SmartCompareApp/`
- Verify `expo-doctor` after install

---

## Section 5 — History stability + Results render fix

**Root cause analysis:**
1. `ResultsScreen.tsx:117` does `result.products` with no guard. Old saved comparisons stored full_response in a different shape; new structured format uses `result.overview.products`.
2. `HistoryScreen.tsx:187` tries to read `item.full_response?.products` — but the **list endpoint only returns summary fields** (`product_names: []` is returned but unused). So every row renders `undefined undefined vs undefined undefined` which collapses to just "vs".

### 5.1 — Migration 020

**`migrations/020_comparisons_schema_version.sql`:**
```sql
ALTER TABLE comparisons ADD COLUMN schema_version INT NOT NULL DEFAULT 1;
ALTER TABLE comparisons ALTER COLUMN schema_version SET DEFAULT 2;
CREATE INDEX idx_comparisons_user_schema ON comparisons (user_id, schema_version, created_at DESC);
COMMENT ON COLUMN comparisons.schema_version IS
    'v1 = legacy pre-structured-response (hidden from history). v2 = full structured response, renderable. Bumped on every breaking shape change to ResultsScreen contract.';
```

Apply via Supabase MCP.

All existing rows default to v1. All new rows default to v2 (after the ALTER ... SET DEFAULT). Old rows stay in DB but invisible.

### 5.2 — Backend changes

**`app/services/database_service.py::save_comparison()`:**
1. Add `_validate_renderable(payload)` helper:
   ```python
   def _validate_renderable(payload: dict) -> bool:
       products = (payload.get("overview", {}).get("products")
                   or payload.get("products") or [])
       return (len(products) >= 2
               and all(p.get("name") for p in products[:2])
               and bool(payload.get("metadata", {}).get("query")))
   ```
2. Call before INSERT. If False → log warning + Sentry breadcrumb tag `comparison_renderable=false` + skip the save. User's comparison still renders live; just don't pollute history.
3. Always populate `product_names = [p["name"] for p in products[:2]]` from validated payload.
4. Always set `schema_version = 2`.

**`app/api/history_routes.py`:**
- `list_comparisons()` add `.eq("schema_version", 2)` filter to query
- `get_comparison(id)` return 404 if `schema_version < 2`

### 5.3 — Frontend changes

**`SmartCompareApp/src/screens/ResultsScreen.tsx`:**
1. Defensive guards at every `result.x.products` access (lines 117, 325, 335, 373, 706, 709). Pattern: `result?.overview?.products ?? result?.products ?? []`.
2. Top-of-component shape check before render: if `products.length < 2`, render one-screen empty state — *"This comparison couldn't be loaded. Try a fresh comparison?"* + "Go home" button. No crash, no spinner.
3. Min-display floor 1.2s preserved (existing, no change).

**`SmartCompareApp/src/screens/HistoryScreen.tsx`:**
1. Line 173: delete `const products = item.full_response?.products || []` (never worked — list endpoint doesn't return full_response).
2. Line 187: rewrite to `${item.product_names[0]} vs ${item.product_names[1]}` with truncation if combined > 40 chars.
3. Fallback chain: empty `product_names` → `item.query`. Empty `query` → `t('history.row.untitled')`.

### 5.4 — Invariant

> **Every row visible in History is GUARANTEED to render in ResultsScreen without crash.**
>
> - v1 rows hidden by list-endpoint filter
> - v2 rows gated by `_validate_renderable` at save time
> - Defensive `?.` guards in ResultsScreen as belt-and-braces

### 5.5 — Tests

- `tests/test_database_service.py` — `test_save_skipped_when_no_products`, `test_save_skipped_when_query_missing`, `test_save_populates_product_names`, `test_save_sets_schema_version_2`
- `tests/test_history_routes.py` — `test_list_filters_v1`, `test_get_returns_404_for_v1`, `test_list_returns_v2_with_product_names`
- Jest `ResultsScreen.test.tsx` — `renders_with_new_format`, `renders_with_legacy_alias`, `empty_state_when_products_missing`, `does_not_crash_when_overview_undefined`
- Jest `HistoryScreen.test.tsx` — `renders_product_names_from_summary`, `falls_back_to_query`, `truncates_long_combined_names`

---

## Section 6 — Switches + i18n cleanup

### 6.1 — Row-tappable switches

**New `SmartCompareApp/src/components/ToggleRow.tsx`:**
```tsx
<TouchableOpacity
  onPress={() => { Haptics.selectionAsync(); onValueChange(!value); }}
  activeOpacity={0.7}
>
  <View style={row}>
    {icon}
    <Text style={label}>{label}</Text>
    <Switch
      value={value}
      onValueChange={(v) => { Haptics.selectionAsync(); onValueChange(v); }}
      trackColor={...}
      thumbColor={...}
    />
  </View>
</TouchableOpacity>
```

Replace 5 inline switch rows on Profile:
- Help-improve-AI-quality (Privacy section)
- Smart-Decision-Notifications master
- 3 sub-toggles: Decision Insights, Peer Decision Updates, Decision Retrospectives

Net: ~80 LOC removed from Profile, ~40 added in ToggleRow.

### 6.2 — i18n leftover-EN sweep

**Visible-now issues (from screenshots 8, 9, 10):**
- "Change Password" label (`ProfileScreen.tsx:383`) stays English in Arabic mode
- Date formatter shows "Mar 20" / "Mar 18" in both locales
- Relative time shows "2d ago" / "11m ago" in both locales

**Fixes:**
- `ProfileScreen.tsx:383` → `t('profile.changePassword')` with EN `"Change Password"` / AR `"تغيير كلمة المرور"`
- New helper `SmartCompareApp/src/utils/formatDate.ts` — `formatDate(d, language)` uses `'ar-SA'` locale when AR (produces "٢٠ مارس")
- Extend existing `formatTimeAgo()` to accept `language`, return `منذ ٢ يوم` / `منذ ١٦ دقيقة` in AR
- "vs" stays in both locales (decision locked — modern Arabic adopts it widely)

**Discipline:** add eslint rule `i18next/no-literal-string` (or custom regex CI check) that fails build on hardcoded English in `src/screens/` + `src/components/`. Prevents regression.

**Full grep audit during implementation:**
```bash
grep -rn '"[A-Z][a-z]' SmartCompareApp/src/screens SmartCompareApp/src/components \
  | grep -v 'colors\.\|styles\.\|typography\.\|spacing\.'
```
Convert each surfaced string to `t('...')` call.

### 6.3 — Tests

- Jest snapshot tests for ProfileScreen + HistoryScreen in both locales
- Custom CI check on hardcoded strings
- No backend changes

---

## Section 7 — Verification + rollout

### 7.1 — Pre-merge gates (all must pass)

**Backend:**
```bash
python -m py_compile $(git diff --name-only main -- 'app/**/*.py')
python -m pytest tests/ -v -m "not (live_unit or live_db or integration)" --timeout=180
python -m pytest tests/test_security_regression.py -v  # ~98 tests, must stay 100%
pip-audit -r requirements.txt --strict
```

**Frontend:**
```bash
cd SmartCompareApp
npx tsc --noEmit                  # ground truth — ignore LSP diagnostics
npm test -- --coverage            # jest, target ≥80% on new files
npx expo-doctor                   # dep alignment check
npm audit --audit-level=high
```

**Migration smoke (post-apply):**
```bash
curl https://web-production-58776.up.railway.app/api/v1/comparisons/history \
  -H "Authorization: Bearer <test-token>" | jq '.comparisons[0]'
# Verify product_names populated, schema_version 2, old rows hidden
```

### 7.2 — Manual QA checklist (run on EAS dev build, NOT Expo Go)

Expo Go is what's making your phone hot and feels slow — it bundles every dev dep including the JS debugger. EAS dev build is the realistic perf signal.

1. ✅ Tap History row → opens ResultsScreen without crash
2. ✅ History rows show real product names (e.g., "iPhone 15 vs Galaxy S24"), not "vs"
3. ✅ Profile → Preferences → walks all 4 pages → Save → returns to Profile, persisted
4. ✅ Profile → Edit Profile → rename works, email read-only, delete account confirms before destroying
5. ✅ Profile → Privacy → markdown renders; Terms → markdown renders; Contact Us → form submits, success state shows
6. ✅ Profile → tap anywhere on a switch row (not just thumb) → toggle flips + haptic
7. ✅ Profile (AR locale) → no English strings (Change Password, dates, ago-suffixes)
8. ✅ Register with friend's code QR-XXXXXX → backend links → first comparison → friend's gift counter increments
9. ✅ Share from Profile/Results → message includes both link AND code
10. ✅ Tap qaren.app/r/QR-XXXXXX deep link → opens Register pre-filled
11. ✅ Log out → create second account on same device → free tier starts at 0 freebies (anti-farming verified)
12. ✅ History shows only schema_v2 rows; v1 rows invisible

### 7.3 — Sentry one-time setup

- Sign up for Sentry free tier (5K events/month)
- Paste DSN into Railway `SENTRY_DSN`
- Deliberate `raise Exception("sentry test")` in dev → verify event in dashboard within 30s with stack trace + scrubbed PII → revert the throw

### 7.4 — Railway env-var checklist before merge

- `ENABLE_REFERRAL_SYSTEM=true` (verify, may currently be OFF)
- `SENTRY_DSN` (new)
- All others unchanged

### 7.5 — Rollout sequence

1. Apply migrations 020 + 021 via Supabase MCP `apply_migration`
2. Confirm `ENABLE_REFERRAL_SYSTEM=true` and `SENTRY_DSN` set in Railway
3. `git push origin main` → Railway auto-deploys backend (~90s)
4. `eas update --branch preview` → JS bundle to existing testers
5. Smoke-test all 12 manual QA items on a real device (EAS dev build)
6. If green → `eas update --branch production` when ready for App Store soft-launch

---

## Section 8 — Team execution requirements (for writing-plans handoff)

**Team composition: 4 Opus agents via `TeamCreate`. NOT Sonnet, NOT Haiku.**

| Role | File ownership (non-overlapping) |
|---|---|
| **backend-opus** | `app/**/*.py`, `migrations/020_*.sql`, `migrations/021_*.sql`, `tests/test_*.py` for backend |
| **frontend-opus** | `SmartCompareApp/src/screens/**`, `SmartCompareApp/src/components/**`, `SmartCompareApp/src/services/**`, `SmartCompareApp/src/utils/**` |
| **i18n-opus** | `SmartCompareApp/src/i18n/**` (both en.json and ar.json), the leftover-EN audit grep, the eslint rule |
| **qa-opus** | Jest test files in `SmartCompareApp/src/__tests__/`, backend QA cross-checks, manual QA checklist execution |

**Cross-QA gate (BLOCKING — team does NOT disassemble until all checks pass):**

- Every member's deliverable must be QA'd by a DIFFERENT member before sign-off:
  - backend-opus reviews i18n-opus and qa-opus
  - frontend-opus reviews backend-opus
  - i18n-opus reviews frontend-opus
  - qa-opus reviews backend-opus and frontend-opus
- If QA finds work subpar, missed, or broken → review sends it BACK with specific reasons. The owning agent fixes and re-submits. Do NOT approve subpar work to keep the schedule.

**Idle-state behavior (BLOCKING rule — no idle waiting):**

- If an agent has no current task AND is waiting for QA results on their submitted work, they MUST do one of:
  - **Write red-green tests** targeting the bundle's new code, pushing coverage toward 80% on every new file
  - **Wait actively** for QA results (poll `TaskList`, respond when re-assigned)
- Agents do NOT pick up another member's owned files. File ownership is exclusive to prevent merge conflicts (per Session 35 lesson).

**Team disassembly conditions (ALL must be true):**

1. All 7 sections of this design are 100% complete in code
2. All pre-merge verification gates from §7.1 pass
3. All 12 manual QA items from §7.2 verified on EAS dev build
4. Every deliverable has been QA'd by a different agent and approved
5. No outstanding "send-back" reviews
6. CLAUDE.md + MEMORY.md + `docs/CONTEXT_SESSION_LOG.md` updated with Bundle A session log

**Operating mode:** `bypassPermissions` (per Session 26+ Agent Team Pattern, MEMORY.md).

**Coordination cadence:** Each agent posts a status update in TaskList every 15-20 minutes of active work, or on task transition. Long silence (>30 min idle without TaskList update) = the team coordinator (Claude main thread) pokes them.

---

## Appendix A — Files touched (estimate)

**New files:**
- `migrations/020_comparisons_schema_version.sql`
- `migrations/021_device_fingerprint_users.sql`
- `SmartCompareApp/src/screens/LegalScreen.tsx`
- `SmartCompareApp/src/screens/ContactUsScreen.tsx`
- `SmartCompareApp/src/screens/EditProfileScreen.tsx`
- `SmartCompareApp/src/screens/EditPreferencesFlow.tsx`
- `SmartCompareApp/src/components/ToggleRow.tsx`
- `SmartCompareApp/src/components/PrioritiesPicker.tsx`
- `SmartCompareApp/src/components/BudgetPicker.tsx`
- `SmartCompareApp/src/components/LifestylePicker.tsx`
- `SmartCompareApp/src/components/BrandAttitudePicker.tsx`
- `SmartCompareApp/src/services/deviceFingerprint.ts`
- `SmartCompareApp/src/utils/formatDate.ts`
- ~8 new Jest test files

**Modified files:**
- `app/api/auth_routes.py` (invite_code support, device fingerprint inheritance)
- `app/api/history_routes.py` (schema_version filter)
- `app/services/database_service.py` (validator + schema_version)
- `app/services/usage_service.py` (no change — counter is already per-user)
- `SmartCompareApp/src/screens/ProfileScreen.tsx` (relocations + ToggleRow swaps)
- `SmartCompareApp/src/screens/ResultsScreen.tsx` (defensive guards + empty state)
- `SmartCompareApp/src/screens/HistoryScreen.tsx` (product_names rendering)
- `SmartCompareApp/src/screens/RegisterScreen.tsx` (invite code field)
- `SmartCompareApp/src/services/authService.ts` (register payload + fingerprint header)
- `SmartCompareApp/src/services/referralService.ts` (share message copy)
- `SmartCompareApp/src/components/ShareBottomSheet.tsx` (share message)
- `SmartCompareApp/src/components/ReferralStatusCard.tsx` (Copy button)
- `SmartCompareApp/src/i18n/en.json` + `ar.json` (~60 new strings)
- `SmartCompareApp/package.json` (react-native-markdown-display)
- `CLAUDE.md` + `MEMORY.md` (session log entry)

**Estimated LOC:** ~2,000 new + ~500 modified, ~150 deleted (inline name-edit, dead handlers, broken full_response lookup).

---

## Appendix B — What we deliberately did NOT do

- ❌ Branch.io / AppsFlyer integration for deferred deep-link install survival
- ❌ Avatar photo upload (S3 + image picker + crop)
- ❌ Email change UI (user said useless)
- ❌ 2FA setup
- ❌ Backfill old v1 history rows
- ❌ Camera 2-product enforcement (Bundle C)
- ❌ Category chip emoji removal (Bundle C)
- ❌ Logo placement (Bundle C)
- ❌ Animation polish toward Cal AI smoothness (Bundle C)
- ❌ Arabic-as-default (dropped, device locale stays)
- ❌ Performance / bundle size / heat profiling (Bundle D)
- ❌ ToS / Privacy policy CONTENT rewrite (owned by `docs/plans/2026-05-06-tos-fact-base.md`)

Each deferred item gets its own design doc when its bundle starts.
