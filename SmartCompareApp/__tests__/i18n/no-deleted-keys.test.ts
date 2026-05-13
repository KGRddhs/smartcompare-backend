/**
 * i18n key removal guard — Bundle E Task 0.2
 *
 * Plan: docs/plans/2026-05-13-results-quality-overhaul.md
 * Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 6.
 *
 * Bundle E removes two Results footer CTAs that the Phase 3 redesign
 * shipped but which have no working backend:
 *
 *   - `results.whatsNext` — the "What's next?" CTA throws
 *     `NAVIGATE` errors because the target route was never wired up.
 *   - `results.save` — the bookmark CTA shows a toast but never
 *     persists state. Useless surface area; misleading affordance.
 *
 * Decision 6 strips the buttons AND the i18n keys (no dead translations
 * sitting in en.json/ar.json waiting for someone to wonder what they
 * mean). This test guards that decision so a future contributor
 * doesn't reintroduce the key with the buttons.
 *
 * Parity guard: the EN/AR keysets are already enforced equal by the
 * top-level `i18n.test.ts` file. We add a stricter form here — the EXACT
 * same key COUNT, which catches one-sided deletions that the equality
 * check would also catch but with a more legible failure (a count
 * mismatch points at the recent removal, while a set-equality failure
 * dumps a giant diff).
 */

import en from '../../src/i18n/en.json';
import ar from '../../src/i18n/ar.json';

describe('i18n no-deleted-keys guard — Bundle E Task 0.2', () => {
  const enRecord = en as Record<string, string>;
  const arRecord = ar as Record<string, string>;

  it('removes `results.whatsNext` from en.json', () => {
    expect(enRecord['results.whatsNext']).toBeUndefined();
    // Belt-and-braces: also ensure no NESTED variant (results.whatsNext.X)
    // crept in via a future schema migration.
    const offenders = Object.keys(enRecord).filter((k) =>
      k.startsWith('results.whatsNext'),
    );
    expect(offenders).toEqual([]);
  });

  it('removes `results.whatsNext` from ar.json', () => {
    expect(arRecord['results.whatsNext']).toBeUndefined();
    const offenders = Object.keys(arRecord).filter((k) =>
      k.startsWith('results.whatsNext'),
    );
    expect(offenders).toEqual([]);
  });

  it('removes `results.save` from en.json', () => {
    expect(enRecord['results.save']).toBeUndefined();
  });

  it('removes `results.save` from ar.json', () => {
    expect(arRecord['results.save']).toBeUndefined();
  });

  it('en.json and ar.json have identical key counts (parity)', () => {
    // Top-level i18n.test.ts already asserts set equality. This is the
    // count-level companion: it catches "we deleted in EN but forgot AR"
    // with a much more legible failure (numbers vs. diff dump).
    expect(Object.keys(enRecord).length).toBe(Object.keys(arRecord).length);
  });

  it('redesign keys that REPLACE whatsNext stay intact (no regression)', () => {
    // Phase 3 added results.whyWePicked + results.runnerUpWins to land
    // the new "answer" framing. Those keys MUST survive Bundle E — only
    // the broken whatsNext/save CTAs are pruned.
    for (const key of ['results.whyWePicked', 'results.runnerUpWins']) {
      expect(enRecord[key]).toBeDefined();
      expect(arRecord[key]).toBeDefined();
    }
  });
});

/**
 * RED→GREEN trajectory:
 *
 *  - Pre-Task-0.2 (HEAD before frontend-opus commit): `results.whatsNext`
 *    + `results.save` both exist in en.json (lines 490 + 98) and ar.json
 *    (lines 490 + 98). Four absence assertions FAIL. Count parity passes
 *    (both files already balanced). The whyWePicked/runnerUpWins
 *    non-regression passes (Phase 3 already shipped).
 *  - Post-Task-0.2: all six assertions pass.
 */
