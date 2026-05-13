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

const SOURCE = fs.readFileSync(RESULTS_PATH, 'utf8');

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

  it('uses optional chaining on `result.comparison_id` (line 210 fix)', () => {
    // Design § 1a explicit before/after. The current source has
    // `(result as any).comparison_id || ...` — must become
    // `(result as any)?.comparison_id || ...`.
    expect(SOURCE).toMatch(
      /\(result as any\)\?\.comparison_id\s*\|\|\s*\(metadata as any\)\?\.comparison_id/,
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

  it('v2 row with comparison_id still uses metadata fallback (no regression)', () => {
    // The `|| (metadata as any)?.comparison_id` tail of the sharable id
    // must survive the fix. History rows persist the id at
    // `result.comparison_id` (top-level), while live SSE responses put
    // it at `result.metadata.comparison_id` — both must work.
    expect(SOURCE).toMatch(
      /sharableComparisonId\s*=\s*\(result as any\)\?\.comparison_id\s*\|\|\s*\(metadata as any\)\?\.comparison_id/,
    );
  });
});

/**
 * Verification plan:
 *
 * 1. Run this file against the pre-fix source — expect ≥3 failing
 *    assertions:
 *       - "handles undefined route.params" (no `route?.params`,
 *         empty-state appears only once)
 *       - "uses optional chaining on `result.comparison_id`"
 *         (current source has `(result as any).comparison_id`)
 *       - "optional-chains all `(result as any).*` accesses"
 *         (offenders includes .category_switched, .category_used,
 *          .cohort_summary, .personalization, .comparison_id)
 *
 * 2. After frontend-opus applies design § 1a all five tests pass.
 *
 * 3. Re-run alongside ResultsScreen.guards.test.tsx and
 *    ResultsScreen.redesign.test.tsx — no regressions in Bundle A
 *    contract (empty-state JSX + i18n keys) or Phase 3 redesign
 *    contract (whyWePicked / runnerUpWins / specs-collapsed).
 */
