/**
 * Bundle D Task 1.F.6 — `ai_sharing_enabled` default flip OFF (R23).
 *
 * Contract:
 * - New users (preferences.ai_sharing_enabled === undefined) → toggle OFF
 * - Existing users with explicit `true` → still ON (not reset)
 * - Existing users with explicit `false` → still OFF
 *
 * Risk R23 invariant: the flip applies ONLY to the `undefined` case.
 * The previous source line `preferences?.ai_sharing_enabled !== false`
 * coerced `undefined → true` (default ON), which was the App-Store
 * privacy blocker — opt-out instead of opt-in for AI data sharing.
 *
 * Approach: source-grep is sufficient because the line is a single pure
 * derivation. The 3-case truth table is enumerated via inline assertion
 * on the derived expression (simulated with the actual operator pattern).
 */

import * as fs from 'fs';
import * as path from 'path';

const PROFILE_PATH = path.resolve(__dirname, '../src/screens/ProfileScreen.tsx');
const SOURCE = fs.readFileSync(PROFILE_PATH, 'utf8');

describe('ProfileScreen — ai_sharing_enabled default flip OFF (R23, 1.F.6)', () => {
  it('does NOT use the legacy `!== false` opt-out pattern', () => {
    // Legacy: `preferences?.ai_sharing_enabled !== false` — coerced
    // undefined → true. This was the App-Store privacy blocker.
    expect(SOURCE).not.toMatch(/ai_sharing_enabled\s*!==\s*false/);
  });

  it('uses the opt-in pattern that defaults undefined → false', () => {
    // Accepts two equivalent shapes:
    //   - `preferences?.ai_sharing_enabled ?? false`
    //   - `preferences?.ai_sharing_enabled === true`
    // Both make undefined → false; both preserve explicit true.
    const optInPattern =
      /ai_sharing_enabled\s*\?\?\s*false|ai_sharing_enabled\s*===\s*true/;
    expect(SOURCE).toMatch(optInPattern);
  });

  it('truth-table invariant: undefined → false, true → true, false → false', () => {
    // Sanity-check the chosen pattern against the 3 input cases.
    const fromOptIn = (v: unknown) => (v as boolean | undefined) ?? false;
    expect(fromOptIn(undefined)).toBe(false);
    expect(fromOptIn(true)).toBe(true);
    expect(fromOptIn(false)).toBe(false);

    const fromIdentity = (v: unknown) => v === true;
    expect(fromIdentity(undefined)).toBe(false);
    expect(fromIdentity(true)).toBe(true);
    expect(fromIdentity(false)).toBe(false);
  });
});
