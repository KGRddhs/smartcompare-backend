/**
 * F-S1.5j + F-S1.5m regression — App.tsx must not register any two
 * Stack.Screens with the same name across conditional branches.
 *
 * React Navigation v7 collapses conditional `<Stack.Screen>` with
 * identical `name` props into the same logical route, so when the
 * parent's conditional flips (e.g. `needsPreferences: true → false`),
 * the navigator refuses to swap routes and the user stays stuck on
 * the first instance.
 *
 * F-S1.5j (Onboarding) and F-S1.5m (ReferralLanding + InviteeQuiz)
 * both shipped fixes for this pattern; this test enforces the global
 * invariant so any future duplicate is caught before merge.
 *
 * Matching memory file: `feedback_react_navigation_duplicate_route_name.md`.
 *
 * Implementation: static source scan. Counts every `<Stack.Screen name="X"`
 * occurrence (handles both single-line and multi-line attribute forms)
 * and asserts each name appears exactly once. Failure surfaces the full
 * list of duplicate names so the offender is unambiguous.
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

describe('F-S1.5j + F-S1.5m — App.tsx Stack.Screen names are globally unique', () => {
  it('every Stack.Screen registers a distinct name', () => {
    const names = collectStackScreenNames();
    expect(names.length).toBeGreaterThan(0);

    const counts = new Map<string, number>();
    for (const n of names) counts.set(n, (counts.get(n) ?? 0) + 1);

    const duplicates = Array.from(counts.entries())
      .filter(([, c]) => c > 1)
      .map(([n, c]) => `${n} (×${c})`);

    expect(duplicates).toEqual([]);
  });

  it('the post-auth Onboarding modal uses name="OnboardingEdit" (F-S1.5j)', () => {
    const names = collectStackScreenNames();
    expect(names).toContain('OnboardingEdit');
    expect(names.filter((n) => n === 'Onboarding').length).toBe(1);
  });

  it('ReferralLanding + InviteeQuiz are registered exactly once each (F-S1.5m)', () => {
    const names = collectStackScreenNames();
    expect(names.filter((n) => n === 'ReferralLanding').length).toBe(1);
    expect(names.filter((n) => n === 'InviteeQuiz').length).toBe(1);
  });
});
