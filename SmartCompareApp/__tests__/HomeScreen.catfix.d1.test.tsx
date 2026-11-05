/**
 * catfix Workstream D — Task D1 contract test (FE null-default + conditional send + nudge).
 *
 * Plan:   docs/plans/2026-06-20-fragrance-category-allcat-implementation.md § D1
 * Design: docs/plans/2026-06-20-fragrance-category-allcat-design.md § Section 1 (Frontend)
 *
 * The bug this guards: HomeScreen seeded `selectedCategory` with a silent
 * `'electronics'` default, so EVERY two-box / link compare shipped
 * `selected_category: 'electronics'` even for a fragrance pair — biasing
 * the backend's category resolution. D1 makes the default `null` and sends
 * `selected_category` ONLY when the user taps a chip; a gentle non-blocking
 * nudge invites a pick while nothing is selected.
 *
 * Approach: source-grep on the current code paths (same pattern as
 * HomeScreen.bundleB.contract.test.tsx). HomeScreen's render harness is
 * heavy (camera / navigation / SSE / reanimated); the load-bearing behavior
 * here is the literal code shape — default value, conditional spread at the
 * two compare sites, and the null-gated nudge — all of which a grep pins
 * precisely. If a future commit reintroduces a hardcoded default or makes
 * the key unconditional, the matching assertion goes RED.
 */

import * as fs from 'fs';
import * as path from 'path';

const HOME_PATH = path.resolve(__dirname, '../src/screens/HomeScreen.tsx');
const HOME_SRC = fs.readFileSync(HOME_PATH, 'utf8');

const EN = JSON.parse(
  fs.readFileSync(path.resolve(__dirname, '../src/i18n/en.json'), 'utf8')
) as Record<string, string>;
const AR = JSON.parse(
  fs.readFileSync(path.resolve(__dirname, '../src/i18n/ar.json'), 'utf8')
) as Record<string, string>;

// ---------------------------------------------------------------------
// Section 1 — null default (no silent 'electronics')
// ---------------------------------------------------------------------

describe('catfix D1 — selectedCategory defaults to null', () => {
  it('useState is typed string | null and initialized to null', () => {
    expect(HOME_SRC).toMatch(
      /useState<string \| null>\(null\)/
    );
    // The specific selectedCategory declaration uses the null default.
    expect(HOME_SRC).toMatch(
      /const \[selectedCategory, setSelectedCategory\] = useState<string \| null>\(null\)/
    );
  });

  it('the silent \'electronics\' default is GONE from the state seed', () => {
    // Negative guard — the exact prior seed must never come back. (A chip
    // VALUE of 'electronics' still exists in CategorySelector; this only
    // forbids it as the useState initializer.)
    expect(HOME_SRC).not.toMatch(
      /useState<string>\(\s*['"]electronics['"]\s*\)/
    );
    expect(HOME_SRC).not.toMatch(
      /setSelectedCategory\] = useState<string>\(\s*['"]electronics['"]\s*\)/
    );
  });
});

// ---------------------------------------------------------------------
// Section 2 — conditional send: omit selected_category when null
// Both the SSE stream path (~options arg) and the URL body must spread
// the key conditionally on a truthy selectedCategory.
// ---------------------------------------------------------------------

describe('catfix D1 — selected_category sent only when a chip is selected', () => {
  it('stream + url paths use the conditional spread guard', () => {
    // S81-11 (E9, R-S11-15 / R-S11-3): re-pinned to the categoryToSend form,
    // same count semantics: `...(sendCategory ? { selected_category: sendCategory } : {})`
    // where sendCategory = categoryToSend(selectedCategory, launchSurfaces).
    const conditionalSpread =
      /\.\.\.\(\s*sendCategory\s*\?\s*\{\s*selected_category:\s*sendCategory\s*\}\s*:\s*\{\}\s*\)/g;
    const matches = HOME_SRC.match(conditionalSpread) ?? [];
    // One for the streamComparison options arg, one for the url/compare body.
    expect(matches.length).toBeGreaterThanOrEqual(2);
    const gated =
      HOME_SRC.match(/const\s+sendCategory\s*=\s*categoryToSend\(\s*selectedCategory\s*,\s*launchSurfaces\s*\)/g) ?? [];
    expect(gated.length).toBeGreaterThanOrEqual(2);
  });

  it('does NOT pass selected_category unconditionally (object-literal property)', () => {
    // The pre-D1 shapes were `{ selected_category: selectedCategory }` as a
    // bare options object and `selected_category: selectedCategory,` as a
    // url-body property. Neither may survive OUTSIDE the conditional spread.
    // Strip every conditional-spread occurrence, then assert the bare forms
    // are gone from what remains.
    const stripped = HOME_SRC.replace(
      /\.\.\.\(\s*selectedCategory\s*\?\s*\{\s*selected_category:\s*selectedCategory\s*\}\s*:\s*\{\}\s*\)/g,
      ''
    );
    // bare options object `{ selected_category: selectedCategory }`
    expect(stripped).not.toMatch(
      /\{\s*selected_category:\s*selectedCategory\s*\}/
    );
    // bare url-body property `selected_category: selectedCategory,`
    expect(stripped).not.toMatch(
      /^\s*selected_category:\s*selectedCategory\s*,?\s*$/m
    );
  });

  it('streamComparison still forwards the { product_a, product_b } pair (no regression)', () => {
    expect(HOME_SRC).toMatch(
      /streamComparison\(\s*\{\s*product_a\s*:\s*\w+\s*,\s*product_b\s*:\s*\w+\s*\}/
    );
  });
});

// ---------------------------------------------------------------------
// Section 3 — non-blocking nudge, gated on selectedCategory == null
// ---------------------------------------------------------------------

// S81-11 (E9, C11): the nudge is replaced by the fragrance-only line, which
// renders whatever the chip state (no selectedCategory gate).
describe('catfix D1 — category nudge', () => {
  it('renders the fragrance-only line whatever the chip state (S81-11)', () => {
    expect(HOME_SRC).toMatch(/canCompare && \([\s\S]{0,200}testID="home-fragrance-only-line"/);
    expect(HOME_SRC).not.toMatch(/selectedCategory == null &&[\s\S]{0,200}testID="home-fragrance-only-line"/);
    expect(HOME_SRC).not.toMatch(/testID="home-category-nudge"/);
  });

  it('uses the home.categories.fragrancesOnly i18n key, not the nudge (S81-11)', () => {
    expect(HOME_SRC).toMatch(/t\(\s*['"]home\.categories\.fragrancesOnly['"]/);
    expect(HOME_SRC).not.toMatch(/['"]home\.categories\.nudge['"]/);
  });

  it('en.json + ar.json define home.categories.fragrancesOnly and drop the nudge (S81-11)', () => {
    expect(EN['home.categories.fragrancesOnly']).toBe('Fragrances only for now');
    expect(typeof AR['home.categories.fragrancesOnly']).toBe('string');
    expect(AR['home.categories.fragrancesOnly'].length).toBeGreaterThan(0);
    expect(EN['home.categories.nudge']).toBeUndefined();
    expect(AR['home.categories.nudge']).toBeUndefined();
  });
});
