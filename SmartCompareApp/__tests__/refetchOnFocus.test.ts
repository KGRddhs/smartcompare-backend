/**
 * F-S1.5k regression — ProfileScreen + EditProfileScreen refetch on focus.
 *
 * Ahmed round-3 OTA: after saving a name change in EditProfile or
 * priorities in EditPreferences, Profile didn't refresh because the
 * load functions only fired once on mount via `useEffect`. The β fix
 * for F-S1.5i made the save itself land cleanly; this fix wires
 * navigation focus events through `useFocusEffect` so the very next
 * Profile render reflects the new state.
 *
 * Also pins the write-through cache update so getSavedUser() returns
 * the latest display_name immediately after a successful PUT
 * /auth/profile, instead of waiting for a full session refresh.
 *
 * Source-grep approach — full render pulls in 20+ services; the
 * structural contract is what matters here.
 */

import * as fs from 'fs';
import * as path from 'path';

const PROFILE_PATH = path.resolve(__dirname, '../src/screens/ProfileScreen.tsx');
const EDIT_PROFILE_PATH = path.resolve(
  __dirname,
  '../src/screens/EditProfileScreen.tsx',
);
const AUTH_SERVICE_PATH = path.resolve(
  __dirname,
  '../src/services/authService.ts',
);

const PROFILE_SRC = fs.readFileSync(PROFILE_PATH, 'utf8');
const EDIT_PROFILE_SRC = fs.readFileSync(EDIT_PROFILE_PATH, 'utf8');
const AUTH_SRC = fs.readFileSync(AUTH_SERVICE_PATH, 'utf8');

describe('F-S1.5k — ProfileScreen refetch on focus', () => {
  it('imports useFocusEffect from @react-navigation/native', () => {
    expect(PROFILE_SRC).toMatch(
      /import\s*\{\s*useFocusEffect\s*\}\s*from\s*['"]@react-navigation\/native['"]/,
    );
  });

  it('wires useFocusEffect that re-fires loadUser + loadCohortProfile + loadPreferences', () => {
    // The callback inside useFocusEffect must invoke all 3 load functions
    // so any save elsewhere reflects on the next focus event.
    expect(PROFILE_SRC).toMatch(
      /useFocusEffect\([\s\S]{0,400}loadUser\(\)[\s\S]{0,200}loadCohortProfile\(\)[\s\S]{0,200}loadPreferences\(\)/,
    );
  });

  it('does NOT keep the legacy mount-only useEffect that re-fires the same load functions', () => {
    // The legacy line was `useEffect(() => { loadUser(); loadCohortProfile();
    // loadPreferences(); }, []);` — must be removed so it doesn't double-fire.
    expect(PROFILE_SRC).not.toMatch(
      /useEffect\(\s*\(\)\s*=>\s*\{[\s\S]{0,200}loadUser\(\)[\s\S]{0,200}loadCohortProfile\(\)[\s\S]{0,200}loadPreferences\(\)[\s\S]{0,200}\}\s*,\s*\[\s*\]\s*\)/,
    );
  });
});

describe('F-S1.5k — EditProfileScreen refetch on focus', () => {
  it('imports useFocusEffect from @react-navigation/native', () => {
    expect(EDIT_PROFILE_SRC).toMatch(
      /import\s*\{\s*useFocusEffect\s*\}\s*from\s*['"]@react-navigation\/native['"]/,
    );
  });

  it('wires useFocusEffect that re-reads getSavedUser into local state', () => {
    expect(EDIT_PROFILE_SRC).toMatch(
      /useFocusEffect\([\s\S]{0,500}getSavedUser\(\)[\s\S]{0,400}setDisplayName/,
    );
  });

  it('handleSave write-throughs the new display_name into the cached user', () => {
    // After a successful updateProfile, EditProfile must call
    // updateSavedUserDisplayName so the next Profile focus refetch
    // picks up the new name without waiting for a full session refresh.
    expect(EDIT_PROFILE_SRC).toMatch(
      /import\s*\{[\s\S]{0,200}updateSavedUserDisplayName[\s\S]{0,200}\}\s*from\s*['"]\.\.\/services\/authService['"]/,
    );
    expect(EDIT_PROFILE_SRC).toMatch(
      /result\.success[\s\S]{0,400}updateSavedUserDisplayName\(\s*trimmed\s*\)/,
    );
  });
});

describe('F-S1.5k — authService exposes updateSavedUserDisplayName helper', () => {
  it('exports updateSavedUserDisplayName(displayName)', () => {
    expect(AUTH_SRC).toMatch(
      /export\s+async\s+function\s+updateSavedUserDisplayName\s*\([\s\S]{0,200}displayName\s*:\s*string[\s\S]{0,200}\)/,
    );
  });

  it('preserves the other fields by spreading the existing user record', () => {
    // The helper must merge into the existing User shape, not blow it
    // away with a partial — otherwise `email` / `id` / `auth_provider`
    // would be lost from the cache.
    expect(AUTH_SRC).toMatch(
      /updateSavedUserDisplayName[\s\S]{0,400}\.\.\.current[\s\S]{0,200}display_name\s*:\s*displayName/,
    );
  });

  it('no-ops when the cache is empty (getSavedUser returns null)', () => {
    // Mid-logout race or fresh boot: we shouldn't crash, just skip.
    expect(AUTH_SRC).toMatch(
      /updateSavedUserDisplayName[\s\S]{0,300}!current[\s\S]{0,100}return/,
    );
  });
});
