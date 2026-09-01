/**
 * ResultsScreen — Bundle E Task 0.1 RED guards
 *
 * Plan: docs/plans/2026-05-13-results-quality-overhaul.md
 * Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 1.
 *
 * Bundle A already added an empty-state when `products.length < 2`
 * (see ResultsScreen.guards.test.tsx). Bundle E extends that with two
 * additional crash modes the History → Results path can hit:
 *
 *   (a) `route.params` itself is undefined (e.g. when deep-linked or
 *       when an old serialized v1 row is rehydrated without params).
 *       Today the component destructures `const { result } = route.params`
 *       on line 96 with no guard → TypeError before the products-length
 *       branch ever runs.
 *
 *   (b) Line 210 reads `(result as any).comparison_id` WITHOUT an
 *       optional chain. When `result` is undefined this throws even
 *       before the empty-state return. Design § 1a says: rewrite to
 *       `(result as any)?.comparison_id`. Three other call sites
 *       (lines 418, 422, 1057-58, 1067-68) have the same shape and
 *       must also be optional-chained for the empty-state branch to
 *       reach its early return.
 *
 * Following the convention established by ResultsScreen.guards.test.tsx
 * + ResultsScreen.redesign.test.tsx (source-string assertions), we
 * verify the structural fix in source rather than fully rendering
 * ResultsScreen — full render would require mocking Reanimated
 * FadeIn/FadeInDown, useSharedValue, useAnimatedStyle, plus all 9+
 * service modules and bottom-tabs navigation. The runtime contract
 * (no throw on undefined route.params; empty-state still reachable) is
 * validated on EAS dev build per the Phase 4 QA gate.
 *
 * RED→GREEN trajectory: at HEAD (pre-Task 0.1 implementation) all
 * Bundle-E-specific assertions below MUST fail. After frontend-opus
 * lands the fix from design § 1a they MUST pass.
 */

import * as fs from 'fs';
import * as path from 'path';

const RESULTS_PATH = path.resolve(
  __dirname,
  '../../src/screens/ResultsScreen.tsx',
);
// Bundle E S3 — Lane A2: presentation extracted to ResultsContent.tsx.
const RESULTS_CONTENT_PATH = path.resolve(
  __dirname,
  '../../src/components/results/ResultsContent.tsx',
);
const RESULTS_ACCORDION_PATH = path.resolve(
  __dirname,
  '../../src/components/results/ResultsAccordion.tsx',
);
const SOURCE = [
  fs.readFileSync(RESULTS_PATH, 'utf8'),
  fs.existsSync(RESULTS_CONTENT_PATH)
    ? fs.readFileSync(RESULTS_CONTENT_PATH, 'utf8')
    : '',
  fs.existsSync(RESULTS_ACCORDION_PATH)
    ? fs.readFileSync(RESULTS_ACCORDION_PATH, 'utf8')
    : '',
].join('\n');

describe('ResultsScreen — Bundle E Task 0.1 defensive guards', () => {
  it('handles undefined route.params without crashing (early return)', () => {
    // Design § 1a — "Add a defensive early-return at the top of the
    // component when `result` is undefined". The fix must short-circuit
    // BEFORE the existing `(result as any).comparison_id` line, otherwise
    // the destructure on line 96 + the non-optional access on line 210
    // both throw before the products-length empty-state at line 371.
    //
    // Two acceptable shapes:
    //   const result = route?.params?.result;
    //   if (!result) return <EmptyState ... />;
    // OR an inline ternary returning the empty state.
    //
    // We assert two structural signals together: optional access on
    // route.params AND the empty-state testID being reachable via a
    // top-level branch that depends on `result` being falsy.
    expect(SOURCE).toMatch(/route\?\.params|route\.params\?\./);
    // Empty-state testID must be referenced from the early-return path,
    // not just from the products.length<2 branch. Easy proxy: the
    // testID appears at least twice (Bundle A's branch + Bundle E's
    // top-level guard). If frontend-opus reuses the same JSX in a
    // helper that's also fine — the count will still be ≥2 because
    // the early-return JSX renders it.
    const matches = SOURCE.match(/results-empty-state/g) ?? [];
    expect(matches.length).toBeGreaterThanOrEqual(2);
  });

  it('uses optional chaining on the comparison id read (line 210 fix, M18-updated)', () => {
    // Design § 1a intent: never a non-optional `result.` access that can
    // throw before the empty-state early return. M18 MB-contract-01/03
    // replaced the any-cast phantom-key read with the typed, still
    // optional-chained real id (`result?.comparison_id ??
    // route?.params?.comparison_id`) — the crash guard this pin protects
    // is preserved.
    expect(SOURCE).toMatch(
      /result\?\.comparison_id\s*\?\?\s*route\?\.params\?\.comparison_id/,
    );
    // Negative assertion: the non-optional form must NOT remain in source.
    expect(SOURCE).not.toMatch(/\(result as any\)\.comparison_id/);
  });

  it('optional-chains all `(result as any).*` accesses (defense in depth)', () => {
    // Lines 418 / 422 / 1057-58 / 1067-68 today read
    // `(result as any).category_switched`, `(result as any).category_used`,
    // `(result as any).cohort_summary`, `(result as any).personalization`.
    // Each is unreachable when result is undefined because the empty-state
    // returns first — but the design's intent is "no non-optional `result`
    // access anywhere", because future refactors might move code above
    // the guard. Enforce the invariant structurally: no
    // `(result as any).<word>` without `?`.
    //
    // Allowed: `(result as any)?.foo`, `(result as any)?.foo?.bar`.
    // Forbidden: `(result as any).foo` (no `?` before `.`).
    const offenders = SOURCE.match(/\(result as any\)\.[a-zA-Z_]/g) ?? [];
    expect(offenders).toEqual([]);
  });

  it('legacy v1 row falls through to empty-state (defense vs. server filter)', () => {
    // Migration 020 hides v1 rows server-side (schema_version=2 filter),
    // but a stale client cache might still hand a v1-shape result to
    // ResultsScreen. The Bundle A products fallback chain handles this:
    // overview?.products ?? products ?? [] → empty array → empty state.
    // Re-assert the chain so a future refactor that drops one branch
    // gets caught. This duplicates the Bundle A guard intentionally —
    // Bundle E should not regress it.
    expect(SOURCE).toMatch(
      /overview\?\.products[\s\S]*?\?\?[\s\S]*?result[\s\S]*?\?\.products[\s\S]*?\?\?[\s\S]*?\[\]/,
    );
  });

  it('sharable id survives for history rows (M18-updated: real id, phantom metadata tail removed)', () => {
    // STALE-PIN UPDATE (M18 MB-contract-03): the old assertion protected a
    // `(metadata as any)?.comparison_id` tail on the belief that live SSE
    // responses carry `result.metadata.comparison_id`. Verified false —
    // response_builder.py has ZERO comparison_id emit sites, so that tail
    // could never fire and the sharable id was permanently null (share
    // Loop-1 unreachable). The invariant this pin exists for — a history
    // row's sharable id must survive into ShareBottomSheet — now holds via
    // the real id: getComparison surfaces wrapper.comparison.id as
    // result.comparison_id, with route.params.comparison_id as fallback,
    // and sharableComparisonId is that same id.
    expect(SOURCE).toMatch(/const\s+sharableComparisonId\s*=\s*comparisonId/);
    expect(SOURCE).not.toMatch(/\(metadata as any\)\?\.comparison_id/);
  });
});

describe('ResultsScreen — Bundle E Task 0.2 button removal', () => {
  it('removes the "What\'s next?" button (testID + i18n key)', () => {
    // Decision 6 — `results-whats-next` testID + `t('results.whatsNext')`
    // call must be GONE from source. The button throws a NAVIGATE error
    // in production because the target route isn't wired; deleting the
    // button is cheaper than fixing the route.
    expect(SOURCE).not.toMatch(/results-whats-next/);
    expect(SOURCE).not.toMatch(/t\(['"]results\.whatsNext['"]\)/);
  });

  it('removes the Save (bookmark) button (i18n key + Bookmark icon usage)', () => {
    // The Save TouchableOpacity calls `t('results.save')` and renders
    // the `Bookmark` icon from lucide. Both signals must be gone — the
    // button has no working backend and ships dead.
    expect(SOURCE).not.toMatch(/t\(['"]results\.save['"]\)/);
    // Bookmark may legitimately survive if a future feature reuses it
    // elsewhere; we don't assert removal of the import. We DO assert
    // the active-button JSX is gone: no `<Bookmark ... />` rendered
    // inside an actionButton context. Spot-check via the line where it
    // sits between `Share2` action and `</View>` closing actionsRow.
    // Simplest reliable signal: the literal `<Bookmark` JSX usage is
    // removed (the lone use today is the Save button at line 981).
    expect(SOURCE).not.toMatch(/<Bookmark\s/);
  });

  it('keeps the Share button intact (no regression)', () => {
    // Decision 6 deletes whatsNext + save, NOT share. Make sure the
    // share affordance survives the prune. Bundle E S3 also pruned the
    // duplicate `results.share`-labeled actions row below feedback per
    // JSX; the header Share button (icon + handleShare) is the lone
    // remaining affordance.
    expect(SOURCE).toMatch(/<Share2\s/);
    expect(SOURCE).toMatch(/onShare|handleShare/);
  });
});

/**
 * Verification plan:
 *
 * 1. Run this file against the pre-fix source — expect failing assertions:
 *    Task 0.1:
 *       - "handles undefined route.params" (no `route?.params`)
 *       - "uses optional chaining on `result.comparison_id`"
 *       - "optional-chains all `(result as any).*` accesses"
 *       - "v2 row with comparison_id still uses metadata fallback"
 *    Task 0.2:
 *       - "removes the What's next? button" (testID + key still present)
 *       - "removes the Save (bookmark) button" (key + Bookmark JSX still present)
 *
 * 2. After frontend-opus applies design § 1a + § 6 all tests pass.
 *
 * 3. Re-run alongside ResultsScreen.guards.test.tsx and
 *    ResultsScreen.redesign.test.tsx + __tests__/i18n/no-deleted-keys.test.ts —
 *    no regressions in Bundle A contract (empty-state JSX + i18n keys)
 *    or Phase 3 redesign contract (whyWePicked / runnerUpWins / specs-collapsed).
 *    NOTE: ResultsScreen.redesign.test.tsx today asserts that
 *    `t('results.whatsNext')` IS in source (line 44). frontend-opus
 *    will need to drop that assertion when removing the button —
 *    the test is mutually exclusive with this Bundle E test by design,
 *    and the Phase 3 contract is intentionally being overridden here.
 */
