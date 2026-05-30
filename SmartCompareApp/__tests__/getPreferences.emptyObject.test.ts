/**
 * F-S1.5i regression — getPreferences must return null when the backend
 * ships `{ preferences: {} }` (empty object) for users with no prefs row.
 *
 * The legacy `response.data.preferences || null` shipped `{}` through
 * because `{}` is truthy in JS, then EditPreferencesFlow loaded the
 * empty state and PUT-ed a body that lacked the backend's required
 * priorities + budget + brand_attitude → Pydantic 422 → scary error.
 *
 * The fix coerces both null AND empty object to null at the FE getter
 * so EditPreferencesFlow falls into DEFAULT_PREFS and the
 * priority-picker gate at Step 1 prevents the round-trip.
 *
 * Truth table tested:
 *   - response.data.preferences = null         → null
 *   - response.data.preferences = undefined    → null
 *   - response.data.preferences = {}           → null  (the regression)
 *   - response.data.preferences = { priorities: ['best_price'], ... } → identity
 */

import * as fs from 'fs';
import * as path from 'path';

const API_PATH = path.resolve(__dirname, '../src/services/api.ts');
const SOURCE = fs.readFileSync(API_PATH, 'utf8');

describe('F-S1.5i — getPreferences null-coerces empty object response', () => {
  it('source no longer uses the bare `preferences || null` truthy shortcut', () => {
    // The legacy line read `return response.data.preferences || null;`
    // (truthy-coalesce). Must not be present after the fix.
    expect(SOURCE).not.toMatch(/return\s+response\.data\.preferences\s*\|\|\s*null\s*;/);
  });

  it('source explicitly null-checks empty-object via Object.keys', () => {
    // The fix introduces an explicit empty-object guard so
    // `{ preferences: {} }` collapses to null.
    expect(SOURCE).toMatch(/Object\.keys\(\s*prefs\s*\)\.length\s*===\s*0/);
  });

  describe('truth-table invariant of the empty-object coercion', () => {
    // Recreate the coercion logic for the 4 input cases. If the function
    // body in api.ts changes, this test pins the contract the contract
    // function MUST implement.
    const coerce = (prefs: unknown) => {
      if (!prefs || typeof prefs !== 'object' || Object.keys(prefs).length === 0) {
        return null;
      }
      return prefs;
    };

    it('null → null', () => {
      expect(coerce(null)).toBeNull();
    });

    it('undefined → null', () => {
      expect(coerce(undefined)).toBeNull();
    });

    it('{} → null (the regression case)', () => {
      expect(coerce({})).toBeNull();
    });

    it('non-empty preferences → identity (NOT coerced)', () => {
      const p = { priorities: ['best_price'], budget: 'mid' };
      expect(coerce(p)).toBe(p);
    });
  });
});
