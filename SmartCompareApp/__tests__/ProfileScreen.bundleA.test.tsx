/**
 * ProfileScreen — Bundle A integration check (Task 4.9)
 *
 * Contract (Bundle A design §3 + plan Task 2.7):
 * - Inline name-edit + delete-account-row REMOVED from Profile (moved to
 *   the dedicated EditProfile screen)
 * - 5 inline <Switch> rows REPLACED by <ToggleRow> components
 *   (aiSharing + notifications master + 3 sub-toggles)
 * - "Edit Profile" row navigates to EditProfile (not inline edit)
 * - "Preferences" row navigates to EditPreferences (not the pre-auth Onboarding)
 * - "Privacy Policy" / "Terms" / "Contact Us" rows wired to nav
 *
 * Approach: source-string assertions. Rendering ProfileScreen end-to-end
 * pulls in 20+ services (auth, push tokens, preferences, demographics,
 * referrals, style profile, ai sharing, notifications). The structural
 * contract here is "the right Switch→ToggleRow swap happened + the right
 * nav handlers are wired" — captured concisely by source matching.
 */

import * as fs from 'fs';
import * as path from 'path';

const PROFILE_PATH = path.resolve(
  __dirname,
  '../src/screens/ProfileScreen.tsx',
);
const SOURCE = fs.readFileSync(PROFILE_PATH, 'utf8');

describe('ProfileScreen — Bundle A Switch→ToggleRow swap (4.9)', () => {
  it('imports ToggleRow', () => {
    expect(SOURCE).toMatch(/import\s+ToggleRow\s+from\s+['"]\.\.\/components\/ToggleRow['"]/);
  });

  it('uses ToggleRow at least 5 times (aiSharing + 4 notifications)', () => {
    const matches = SOURCE.match(/<ToggleRow\b/g) ?? [];
    expect(matches.length).toBeGreaterThanOrEqual(5);
  });

  it('removes the inline <Switch> rows that ToggleRow replaced', () => {
    // The 5 inline switches all had `trackColor={{ false: colors.border.medium`
    // — this exact pattern was the giveaway for the privacyRow/subToggleRow
    // shape. Any future <Switch> use must NOT use this style.
    const switchTrackColorMatches =
      SOURCE.match(/<Switch[\s\S]*?trackColor=\{\{\s*false:/g) ?? [];
    expect(switchTrackColorMatches.length).toBe(0);
  });
});

describe('ProfileScreen — Bundle A nav wiring (4.9)', () => {
  it('Edit Profile row navigates to EditProfile (not inline edit)', () => {
    expect(SOURCE).toMatch(/navigation\.navigate\(\s*['"]EditProfile['"]\s*\)/);
    // The legacy inline-edit pattern (setEditingName toggle in JSX action) is gone.
    expect(SOURCE).not.toMatch(/setEditingName\(\s*!\s*editingName\s*\)/);
  });

  // Bundle E F-S1.5c (c.2.i ruling): the Profile→Preferences row is
  // removed per JSX ProfileScreen.jsx:259-261 (ACCOUNT group has only
  // Edit profile / Change password / Language + the spec-added Upgrade).
  // EditPreferences is now reached via EditProfile → "Edit style profile"
  // linkRow per JSX EditProfileScreen.jsx:189-190. The EditPreferences
  // nav-contract assertion moves to
  // __tests__/EditProfileScreen.editPreferences.test.tsx where it pins
  // the new gateway. The Profile→PrioritiesInline "Tune" CTA also routes
  // to EditPreferences for parity (single canonical lighter-edit target).
  it('Profile handleEditStyleProfile routes to EditPreferences (not legacy Onboarding(mode=edit))', () => {
    expect(SOURCE).toMatch(/handleEditStyleProfile[\s\S]{0,400}navigation\.navigate\(\s*['"]EditPreferences['"]\s*\)/);
    expect(SOURCE).not.toMatch(/handleEditStyleProfile[\s\S]{0,400}Onboarding[\s\S]{0,40}mode:\s*['"]edit['"]/);
  });

  it('Privacy Policy row navigates to Legal with doc=privacy', () => {
    expect(SOURCE).toMatch(/navigation\.navigate\(\s*['"]Legal['"]\s*,\s*\{\s*doc:\s*['"]privacy['"]\s*\}/);
  });

  it('Terms row navigates to Legal with doc=terms', () => {
    expect(SOURCE).toMatch(/navigation\.navigate\(\s*['"]Legal['"]\s*,\s*\{\s*doc:\s*['"]terms['"]\s*\}/);
  });

  it('Contact Us row navigates to ContactUs (no longer a dead `() => {}` handler)', () => {
    expect(SOURCE).toMatch(/navigation\.navigate\(\s*['"]ContactUs['"]\s*\)/);
  });
});

describe('ProfileScreen — Bundle A relocations (4.9)', () => {
  it('no longer renders an inline name-edit TextInput in Profile', () => {
    // The legacy editNameRow + nameInput + handleUpdateName submit lived
    // inline; Bundle A relocates them to EditProfile.
    expect(SOURCE).not.toMatch(/editingName\s*\?\s*\(/);
    expect(SOURCE).not.toMatch(/handleUpdateName/);
  });

  it('no longer renders an inline Delete Account row in Profile', () => {
    // The legacy danger card had a "Delete account" row triggering
    // handleDeleteAccount. Bundle A relocates this to EditProfile.
    expect(SOURCE).not.toMatch(/handleDeleteAccount/);
  });

  it('uses t(...) for the Change Password row label', () => {
    // Pre-Bundle A: literal "Change Password" string. Post: i18n key.
    expect(SOURCE).toMatch(/t\(\s*['"]profile\.changePassword['"]\s*\)/);
    expect(SOURCE).not.toMatch(/['"]Change Password['"]/);
  });
});

/**
 * RED→GREEN trajectory: verified against the parent commit of 66e0894.
 * The pre-fix ProfileScreen had:
 *  - Inline <Switch trackColor={{ false: colors.border.medium ... 5 times
 *  - editingName ? <TextInput .../> in JSX
 *  - handleDeleteAccount handler
 *  - Literal 'Change Password' string
 *  - Preferences row → navigation.navigate('Onboarding', { mode: 'edit' })
 *  - Edit row → setEditingName(!editingName)
 *  - Contact Us row → () => {}
 *
 * All 11 assertions fail at the parent; all 11 pass at HEAD.
 */
