/**
 * Bundle D — Claude-Design tokens (additive namespace, R10 invariant).
 *
 * This file is the landing zone for Ahmed's Claude-Design tokens.json
 * output. Existing `src/theme/index.ts` tokens (colors / spacing / radii /
 * typography / shadows) STAY UNCHANGED — current surfaces keep referencing
 * the legacy namespace until they're individually migrated to the redesign.
 *
 * R10 invariant per `memory/BUNDLE_D_FRONTEND_ANCHOR.md`:
 *   "Frontend extends theme, doesn't replace; tokens applied additively;
 *    cross-QA verifies no breaking theme change."
 *
 * Drop-in workflow when Claude-Design lands:
 *   1. Paste tokens.json values into each object below
 *   2. Re-run `__tests__/HomeScreen.bundleB.contract.test.tsx` — 47 tests
 *      still PASS (preservation framework verifies no legacy token broke)
 *   3. Flip the 2 `it.todo` placeholders in Section 12 to `.test`:
 *        - "theme/index.ts retains all pre-Bundle-D color tokens"
 *        - "theme/index.ts adds Claude-Design tokens under a new namespace"
 *   4. Each redesigned page imports the bundleD namespace AND the legacy
 *      namespace — gradual per-page migration, never bulk replacement
 *
 * Why empty objects today:
 *   Empty literals keep TS + jest happy on the import surface so test
 *   files can `import { bundleDColors } from '../theme/bundleD'` already.
 *   Populating with placeholder values risks "looks done but uses
 *   wrong values" silent bugs.
 */

export const bundleDColors = {
  // primary, secondary, accent, surface, background, text, border, etc.
  // Add `as const` after population so callers get string-literal types.
};

export const bundleDTypography = {
  // Per-style entries with { fontFamily, fontSize, lineHeight, fontWeight,
  // letterSpacing? }. Mirror the shape of the legacy `typography` export
  // (hero / display / title / body / bodyEmphasis / caption / eyebrow /
  // small) so layouts can swap one-for-one when a page migrates.
};

export const bundleDSpacing = {
  // xs / sm / md / base / lg / xl / 2xl / 3xl scale.
};

export const bundleDRadii = {
  // sm / md / lg / xl / full token set.
};

export const bundleDShadows = {
  // sm / md / lg + none. iOS uses shadowColor/Offset/Opacity/Radius;
  // Android uses elevation. Mirror existing `shadows.card` shape.
};
