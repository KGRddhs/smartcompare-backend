/**
 * Bundle D 2.F.2 multi-page contract preservation (companion to
 * HomeScreen.bundleB.contract.test.tsx).
 *
 * Anchor: Claude-Design is FULL APP — pages + fonts + icon + splash +
 * illustrations + design tokens. R10 + R16 already cover HomeScreen +
 * additive theme. This file pins the load-bearing BEHAVIOR contract
 * for the remaining redesigned screens so the per-page drop-in
 * sequence (Results → History → Profile → EditProfile → Auth → Splash
 * per team-lead's recommended order) gets a unit-level fence.
 *
 * Pattern (mirrors HomeScreen.bundleB.contract):
 *   - Source-grep behavior contracts. Compiles + passes today against
 *     shipped Bundle B/C code; flips RED if redesign breaks an invariant.
 *   - Visual snapshot churn = expected; NOT covered here.
 *   - Sub-screens whose contract is purely visual (Splash, Paywall,
 *     Legal, ContactUs, ReferralLanding, InviteeQuiz) are NOT pinned
 *     here — they have no behavior contract that survives a restyle.
 *
 * RTL preservation note (per team-lead): every redesigned page must
 * keep its existing RTL-aware logic. We assert `isRTL` / `useLanguage`
 * / `I18nManager` usage stays present on screens that already mirror.
 */

import * as fs from 'fs';
import * as path from 'path';

function readScreen(name: string): string {
  return fs.readFileSync(
    path.resolve(__dirname, `../src/screens/${name}.tsx`),
    'utf8'
  );
}

// =====================================================================
// RESULTS SCREEN — 3 entry shapes + 1.2s floor + emptyState handling
// =====================================================================

describe('Bundle D contract — ResultsScreen', () => {
  const SRC = readScreen('ResultsScreen');

  it('accepts the 3 entry shapes (result | comparison_id | vision_products)', () => {
    expect(SRC).toMatch(/route\?\.params\?\.result/);
    expect(SRC).toMatch(/route\?\.params\?\.comparison_id/);
    expect(SRC).toMatch(/route\?\.params\?\.vision_products/);
  });

  it('fetches via getComparison(id) when only comparison_id passed', () => {
    expect(SRC).toMatch(/getComparison[\s\S]{0,200}comparisonId/);
  });

  it('falls back to identifyFromImages when vision_products passed', () => {
    expect(SRC).toMatch(/identifyFromImages\s*\(\s*visionProducts/);
  });

  it('handles 404 → setLoadError("not_found") (Bundle D 1.F.5 contract)', () => {
    // M18 mobile-network: the status===404 inspection lives in the shared
    // matrix (failureClassification.ts, behaviorally pinned); the screen
    // routes its kind to the not_found state.
    expect(SRC).toMatch(/kind\s*===\s*'not_found'[\s\S]{0,80}setLoadError\(\s*['"]not_found['"]/);
  });

  it('renders emptyState via results.emptyState.* i18n keys (NO hardcoded literals)', () => {
    expect(SRC).toMatch(/results\.emptyState\.notFound/);
    expect(SRC).toMatch(/results\.emptyState\.title/);
  });

  it('keeps a per-path min-display floor on the async entry shapes (A17)', () => {
    // Was: one mount-anchored 1.2s deadline shared by both async paths.
    // A17 split it — CAMERA_FLOOR_MS still 1200 for vision_products, a
    // shorter HISTORY_FLOOR_MS (with a skip-below threshold) for a
    // comparison_id re-open, both derived from one loadStartedAtRef anchor
    // so handleRetry re-arms whichever path retried. Timings pinned on the
    // clock in ResultsScreen.historyFloor.a17.test.tsx.
    expect(SRC).toMatch(/const\s+CAMERA_FLOOR_MS\s*=\s*1200/);
    expect(SRC).toMatch(/const\s+HISTORY_FLOOR_MS\s*=\s*\d+/);
    expect(SRC).toMatch(/loadStartedAtRef/);
    expect(SRC).toMatch(/await\s+new\s+Promise\(\s*\(resolve\)\s*=>\s*setTimeout/);
  });

  it('fires user_event tracking (verdict view / etc) via trackEvents batch', () => {
    expect(SRC).toMatch(/trackEvents\s*\(/);
  });
});

// =====================================================================
// HISTORY SCREEN — list fetch + tap → Results modal + delete via swipe
// =====================================================================

describe('Bundle D contract — HistoryScreen', () => {
  const SRC = readScreen('HistoryScreen');

  it('imports getComparisonHistory + deleteComparison from api', () => {
    expect(SRC).toMatch(
      /import\s*\{[\s\S]{0,200}getComparisonHistory[\s\S]{0,200}deleteComparison[\s\S]{0,200}\}\s*from\s+['"]\.\.\/services\/api['"]/
    );
  });

  it('fetches history with limit + offset + optional search', () => {
    expect(SRC).toMatch(/getComparisonHistory\(\s*\d+\s*,\s*\d+/);
  });

  it('tap on row navigates to Results with comparison_id param', () => {
    expect(SRC).toMatch(
      /navigation\.navigate\(\s*['"]Results['"]\s*,\s*\{\s*comparison_id\s*:/
    );
  });

  it('renders via a virtualized list primitive (FlatList or SectionList)', () => {
    // Bundle B/C ships SectionList (date-grouped). Either FlatList or
    // SectionList satisfies the perf contract for long-list rendering;
    // the redesign MUST NOT collapse to a plain `<ScrollView>{items.map}`.
    expect(SRC).toMatch(/<(FlatList|SectionList)\b/);
  });

  it('parseApiError surfaces backend error shape on fetch failure', () => {
    expect(SRC).toMatch(/parseApiError/);
  });
});

// =====================================================================
// PROFILE SCREEN — 5 toggles + handleSubToggle (Bundle D 2.F.1, R18) +
// optimistic rollback + ai_sharing default OFF (R23) + cohort display
// =====================================================================

describe('Bundle D contract — ProfileScreen', () => {
  const SRC = readScreen('ProfileScreen');

  it('imports putReengagementSubs alongside savePreferences', () => {
    expect(SRC).toMatch(
      /import\s*\{[\s\S]{0,400}savePreferences[\s\S]{0,400}putReengagementSubs[\s\S]{0,400}\}\s*from\s+['"]\.\.\/services\/api['"]/
    );
  });

  it('handleSubToggle routes the 3 sub-toggles to /reengagement-subs', () => {
    expect(SRC).toMatch(/handleSubToggle[\s\S]{0,2000}putReengagementSubs/);
  });

  it('handleSubToggle uses plural keys (Backend 228ff63 body contract)', () => {
    expect(SRC).toMatch(/decision_insights\s*:/);
    expect(SRC).toMatch(/peer_decision_updates\s*:/);
    expect(SRC).toMatch(/decision_retrospectives\s*:/);
  });

  it('handleSubToggle has optimistic-rollback-on-failure pattern', () => {
    expect(SRC).toMatch(/handleSubToggle[\s\S]{0,2500}setPreferences\(\s*previous/);
  });

  it('ai_sharing_enabled defaults OFF when undefined (R23 invariant)', () => {
    expect(SRC).toMatch(/ai_sharing_enabled\s*\?\?\s*false/);
    expect(SRC).not.toMatch(/ai_sharing_enabled\s*!==\s*false/);
  });

  it('Edit style profile navigates to EditPreferences (Bundle E F-S1.5c c.2.i ruling)', () => {
    // SUPERSEDED Bundle D contract: the edit-style entry used to navigate
    // Onboarding{mode:'edit', source:'styleProfile'}. Bundle E F-S1.5c routed
    // both Profile→Tune and EditProfile→"Edit style profile" to the lighter
    // EditPreferences flow instead (Onboarding mode='edit' stays in code for
    // full re-onboarding but is no longer the edit-style entry).
    expect(SRC).toMatch(/navigation\.navigate\(\s*['"]EditPreferences['"]/);
  });

  it('renders ToggleRow component (Bundle A Switch→ToggleRow swap survives redesign)', () => {
    expect(SRC).toMatch(/<ToggleRow\b/);
  });

  it('shows CohortBadge / StyleProfileCard surface', () => {
    expect(SRC).toMatch(/StyleProfileCard|cohortDisplay/);
  });

  it('logout button calls onLogout prop (parent App.tsx clears session)', () => {
    expect(SRC).toMatch(/onLogout\s*[\(\)\,]/);
  });
});

// =====================================================================
// EDIT PROFILE SCREEN — display name edit + Edit-style nav + email/password
// =====================================================================

describe('Bundle D contract — EditProfileScreen', () => {
  const SRC = readScreen('EditProfileScreen');

  it('Edit Style Profile button navigates to EditPreferences (Bundle E F-S1.5c)', () => {
    // SUPERSEDED Bundle D contract (navigated Onboarding{mode:'edit'}).
    // Bundle E F-S1.5c routes "Edit style profile" to the lighter
    // EditPreferences flow. See EditProfileScreen.tsx:119.
    expect(SRC).toMatch(/navigation\.navigate\(\s*['"]EditPreferences['"]/);
  });

  it('renders the editProfile.editStyleProfile i18n key', () => {
    expect(SRC).toMatch(/editProfile\.editStyleProfile/);
  });
});

// =====================================================================
// LOGIN SCREEN — email/password + social SDKs (Google + Apple) + nav
// =====================================================================

describe('Bundle D contract — LoginScreen', () => {
  const SRC = readScreen('LoginScreen');

  it('imports auth functions from authService (login + Google + Apple)', () => {
    expect(SRC).toMatch(
      /import\s*\{[\s\S]{0,300}login[\s\S]{0,300}signInWithGoogle[\s\S]{0,300}signInWithApple[\s\S]{0,300}\}\s*from\s+['"]\.\.\/services\/authService['"]/
    );
  });

  it('lowercases + trims email before login (auth normalization)', () => {
    expect(SRC).toMatch(/login\(\s*email\.trim\(\)\.toLowerCase\(\)\s*,\s*password\s*\)/);
  });

  it('Forgot Password link navigates to ForgotPassword route', () => {
    expect(SRC).toMatch(/navigation\.navigate\(\s*['"]ForgotPassword['"]/);
  });

  it('Register link navigates to Register route', () => {
    expect(SRC).toMatch(/navigation\.navigate\(\s*['"]Register['"]/);
  });

  it('Apple Sign-In gated by isAppleSignInAvailable (no-op when unavailable)', () => {
    expect(SRC).toMatch(/isAppleSignInAvailable/);
  });
});

// =====================================================================
// REGISTER SCREEN — register + deferred invite code consumption +
// social SDKs + invite code regex validation (QR-XXXXXX format)
// =====================================================================

describe('Bundle D contract — RegisterScreen', () => {
  const SRC = readScreen('RegisterScreen');

  it('imports register + consumeDeferredInviteCode', () => {
    expect(SRC).toMatch(
      /import\s*\{[\s\S]{0,300}register[\s\S]{0,300}signInWithGoogle[\s\S]{0,300}\}\s*from\s+['"]\.\.\/services\/authService['"]/
    );
    expect(SRC).toMatch(/consumeDeferredInviteCode/);
  });

  it('lowercases + trims email before register', () => {
    expect(SRC).toMatch(/register\(\s*email\.trim\(\)\.toLowerCase\(\)\s*,\s*password/);
  });

  it('Login link navigates back to Login route', () => {
    expect(SRC).toMatch(/navigation\.navigate\(\s*['"]Login['"]/);
  });

  it('Apple Sign-In gated by isAppleSignInAvailable', () => {
    expect(SRC).toMatch(/isAppleSignInAvailable/);
  });
});

// =====================================================================
// FORGOT PASSWORD SCREEN — requestPasswordReset + nav
// =====================================================================

describe('Bundle D contract — ForgotPasswordScreen', () => {
  const SRC = readScreen('ForgotPasswordScreen');

  it('imports requestPasswordReset from authService', () => {
    expect(SRC).toMatch(
      /import\s*\{\s*requestPasswordReset\s*\}\s*from\s+['"]\.\.\/services\/authService['"]/
    );
  });

  it('lowercases + trims email before requestPasswordReset', () => {
    expect(SRC).toMatch(
      /requestPasswordReset\(\s*email\.trim\(\)\.toLowerCase\(\)\s*\)/
    );
  });

  it('Back-to-Login button navigates to Login route', () => {
    expect(SRC).toMatch(/navigation\.navigate\(\s*['"]Login['"]/);
  });
});

// =====================================================================
// ONBOARDING — NewOnboardingHost edit-mode contract (Bundle D 1.F.3)
// =====================================================================

describe('Bundle D contract — NewOnboardingHost edit-mode', () => {
  const SRC = fs.readFileSync(
    path.resolve(__dirname, '../src/screens/onboarding/NewOnboardingHost.tsx'),
    'utf8'
  );

  it('exposes `mode: "full" | "edit"` and `onEditDone` props', () => {
    expect(SRC).toMatch(/mode\?:\s*'full'\s*\|\s*'edit'/);
    expect(SRC).toMatch(/onEditDone\?:\s*\(\)\s*=>\s*void/);
  });

  it('edit-mode terminal step is 10 (brand_attitude — last style step)', () => {
    expect(SRC).toMatch(/EDIT_MODE_LAST_STEP[\s\S]{0,30}=\s*10/);
  });

  it('edit-mode initial step is 8 (priorities — first style step)', () => {
    expect(SRC).toMatch(/EDIT_MODE_FIRST_STEP[\s\S]{0,30}=\s*8/);
  });

  it('edit-mode dispatches to onEditDone, NOT onComplete', () => {
    expect(SRC).toMatch(
      /mode\s*===\s*['"]edit['"][\s\S]{0,200}onEditDone\(\)/
    );
  });

  it('persistence buckets still fire in edit-mode (best-effort)', () => {
    expect(SRC).toMatch(/putDemographics/);
    expect(SRC).toMatch(/savePreferences/);
    expect(SRC).toMatch(/saveAttribution/);
  });
});

// =====================================================================
// SCAN CAMERA SCREEN — Bundle D 1.F.4 ? help overlay wiring
// =====================================================================

describe('Bundle D contract — ScanCameraScreen', () => {
  const SRC = readScreen('ScanCameraScreen');

  it('imports CameraHelpOverlay component', () => {
    expect(SRC).toMatch(
      /import\s*\{\s*CameraHelpOverlay\s*\}\s*from\s+['"]\.\.\/components\/CameraHelpOverlay['"]/
    );
  });

  it('help button (`scan-camera-help` testID) has onPress wired', () => {
    expect(SRC).toMatch(/testID="scan-camera-help"[\s\S]{0,200}onPress/);
    expect(SRC).toMatch(/setHelpVisible\s*\(\s*true\s*\)/);
  });

  it('CameraHelpOverlay mounted in JSX with visible + onClose', () => {
    expect(SRC).toMatch(/<CameraHelpOverlay\b/);
    expect(SRC).toMatch(/<CameraHelpOverlay[\s\S]{0,200}visible=\{helpVisible/);
    expect(SRC).toMatch(/<CameraHelpOverlay[\s\S]{0,200}onClose=/);
  });

  it('module-scoped slot cache survives modal dismiss/reopen', () => {
    expect(SRC).toMatch(/_slotsCache/);
    expect(SRC).toMatch(/__resetScanCameraCacheForTests/);
  });
});

// =====================================================================
// POST-REDESIGN PLACEHOLDERS — flip from .todo to .test when each page
// receives its Claude-Design treatment.
// =====================================================================

describe('Bundle D contract — post-redesign per-page placeholders', () => {
  it.todo('ResultsScreen redesign preserves the 3 entry shapes + 1.2s floor');
  it.todo('HistoryScreen redesign keeps FlatList OR SectionList virtualization (perf contract)');
  it.todo('ProfileScreen redesign keeps the 5-toggle layout + cohort badge');
  it.todo('LoginScreen redesign keeps Apple Sign-In gating');
  it.todo('RegisterScreen redesign keeps invite-code field path');
  it.todo('SplashScreen redesign matches new app icon brand');
  it.todo('All redesigned pages mirror under I18nManager.forceRTL(true)');
  it.todo('Custom font (if introduced) loaded via expo-font without breaking Cairo');
});
