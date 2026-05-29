/**
 * F-S1.5j regression — App.tsx must not register two Stack.Screens with the
 * name "Onboarding" across conditional branches.
 *
 * React Navigation v7 collapses conditional `<Stack.Screen>` with identical
 * `name` props into the same logical route, so when the parent's conditional
 * flips (e.g. `needsPreferences: true → false`), the navigator refuses to
 * swap routes and the user stays stuck on the first instance. This bit us
 * on Step 17 Finish (Bundle E F-S1.5j) and earlier on the same Onboarding
 * shape (main-lane hotfix 2e1ceb7 — never merged into the bundle-e
 * worktree until this fix).
 *
 * The matching memory file is `feedback_react_navigation_duplicate_route_name.md`.
 *
 * This test pins the Onboarding split specifically because that is the
 * regression we shipped to fix. A separate audit of the wider App.tsx
 * Stack.Screen registry (ReferralLanding ×2, InviteeQuiz ×2 across Auth
 * + Main branches) is a known latent risk — those tracks haven't reproduced
 * a user-visible stuck-route bug yet, so they're documented as a follow-up
 * rather than a hard fail here. If they DO reproduce, extend this test to
 * cover the full name table.
 */

import * as fs from 'fs';
import * as path from 'path';

const APP_PATH = path.resolve(__dirname, '../App.tsx');
const SOURCE = fs.readFileSync(APP_PATH, 'utf8');

function collectStackScreenNames(): string[] {
  const names: string[] = [];
  const re = /<Stack\.Screen[\s\S]{0,200}?name=["']([A-Za-z][A-Za-z0-9]*)["']/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(SOURCE)) !== null) {
    names.push(m[1]);
  }
  return names;
}

describe('F-S1.5j — App.tsx Onboarding Stack.Screen names are distinct', () => {
  it('exactly one Stack.Screen registers name="Onboarding"', () => {
    const names = collectStackScreenNames();
    const onboardingCount = names.filter((n) => n === 'Onboarding').length;
    expect(onboardingCount).toBe(1);
  });

  it('the post-auth modal re-entry uses name="OnboardingEdit"', () => {
    const names = collectStackScreenNames();
    expect(names).toContain('OnboardingEdit');
  });
});
