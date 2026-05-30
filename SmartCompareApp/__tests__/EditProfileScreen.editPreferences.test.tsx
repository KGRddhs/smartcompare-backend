/**
 * EditProfileScreen — EditPreferences gateway pin (Bundle E F-S1.5c)
 *
 * Migrated from `__tests__/ProfileScreen.bundleA.test.tsx:56-62` after the
 * F-S1.5c rewrite dropped Profile→Preferences in favor of the JSX
 * EditProfileScreen.jsx:189-190 "Edit style profile" gateway. The
 * EditPreferences navigation contract still holds — it just lives on
 * EditProfile now, so the assertion lives next to its new owner.
 *
 * Contract (JSX EditProfileScreen.jsx:189-190):
 *   - One "Edit style profile" row on EditProfile, subtitled
 *     "Update priorities, budget, and brand stance"
 *   - handleEditStyleProfile navigates to EditPreferences (the lighter
 *     Bundle A § 3.2 flow), NOT to Onboarding(mode='edit') (the heavier
 *     17-step re-onboarding)
 *
 * Approach: source-grep, matching the pattern used by the bundleA suite.
 * Full render is overkill — the structural contract is one nav call.
 */

import * as fs from 'fs';
import * as path from 'path';

const EDIT_PROFILE_PATH = path.resolve(
  __dirname,
  '../src/screens/EditProfileScreen.tsx',
);
const SOURCE = fs.readFileSync(EDIT_PROFILE_PATH, 'utf8');

describe('EditProfileScreen — EditPreferences gateway (Bundle E F-S1.5c)', () => {
  it('handleEditStyleProfile navigates to EditPreferences', () => {
    expect(SOURCE).toMatch(
      /handleEditStyleProfile[\s\S]{0,500}navigation\.navigate\(\s*['"]EditPreferences['"]\s*\)/,
    );
  });

  it('handleEditStyleProfile no longer routes to Onboarding(mode=edit)', () => {
    // Legacy pre-Bundle-E path. Onboarding remains in code for full
    // re-onboarding but has no user-facing entry-point from EditProfile.
    expect(SOURCE).not.toMatch(
      /handleEditStyleProfile[\s\S]{0,500}Onboarding[\s\S]{0,60}mode:\s*['"]edit['"]/,
    );
  });

  it('renders an "Edit style profile" linkRow wired to handleEditStyleProfile', () => {
    // The label is i18n-keyed; matches the t('editProfile.editStyleProfile')
    // call shape. The TouchableOpacity must have onPress wired to the
    // repointed handler.
    expect(SOURCE).toMatch(/t\(\s*['"]editProfile\.editStyleProfile['"]\s*\)/);
    expect(SOURCE).toMatch(/onPress=\{\s*handleEditStyleProfile\s*\}/);
  });
});
