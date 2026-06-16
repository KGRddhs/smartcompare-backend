/**
 * ResultsScreen — Bundle E Task 3.5 INTEGRATION CONTRACT
 *
 * Plan: docs/plans/2026-05-13-results-quality-overhaul.md § Task 3.5
 * Design: docs/plans/2026-05-13-results-quality-overhaul-design.md
 *         § Decision 2 (dimensions[] contract) + § Decision 3 (hero card)
 *         + § Decision 6 (one-release backward-compat with legacy scoring)
 *
 * Task 3.5 wires the four Bundle E components — HeroRings, DimensionBars,
 * TopMatchBadge, FactualVerdict — into ResultsScreen.tsx and gates them
 * on `result.scoring_v2` while keeping the legacy `scoring` block as a
 * single-release fallback for users on older EAS bundles.
 *
 * Why source-string assertions: ResultsScreen renders with Reanimated
 * (FadeIn/FadeInDown + useSharedValue/useAnimatedStyle), 9+ service
 * mocks, bottom-tabs navigation, and 1,700 lines of conditional UI.
 * Per ResultsScreen.test.tsx convention (existing Bundle E guard test
 * in the same dir), we verify the structural contract in source so
 * the failure mode is precise + the test runs in <1s. Full render is
 * covered by the EAS dev-build manual QA pass (Phase 4 § 4.6).
 *
 * RED→GREEN trajectory: at HEAD frontend-opus has the wiring on disk
 * but has NOT committed it (verified via `git status` 2026-05-16). All
 * assertions below must hold against the COMMITTED ResultsScreen.tsx.
 * If frontend-opus reverts any of the four imports, swaps a banned
 * orange/red score color, or removes the v2-vs-legacy gate, this test
 * goes RED and surfaces it loudly.
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
const SOURCE = [
  fs.readFileSync(RESULTS_PATH, 'utf8'),
  fs.existsSync(RESULTS_CONTENT_PATH)
    ? fs.readFileSync(RESULTS_CONTENT_PATH, 'utf8')
    : '',
].join('\n');

describe('ResultsScreen — Task 3.5 scoring_v2 wiring', () => {
  describe('imports the four Bundle E components', () => {
    // Design § Decision 3 + plan § Task 3.5 list these as the new
    // surface. If any import goes missing the render breaks silently
    // because of the gate below.
    it('imports HeroRings from components/results/HeroRings', () => {
      expect(SOURCE).toMatch(
        /import\s*\{\s*HeroRings\s*\}\s*from\s*['"]\.\.\/components\/results\/HeroRings['"]/,
      );
    });

    it('imports DimensionBars from components/results/DimensionBars', () => {
      expect(SOURCE).toMatch(
        /import\s*\{\s*DimensionBars\s*\}\s*from\s*['"]\.\.\/components\/results\/DimensionBars['"]/,
      );
    });

    it('imports TopMatchBadge from components/results/TopMatchBadge', () => {
      expect(SOURCE).toMatch(
        /import\s*\{\s*TopMatchBadge\s*\}\s*from\s*['"]\.\.\/components\/results\/TopMatchBadge['"]/,
      );
    });

    it('imports FactualVerdict from components/results/FactualVerdict', () => {
      expect(SOURCE).toMatch(
        /import\s*\{\s*FactualVerdict\s*\}\s*from\s*['"]\.\.\/components\/results\/FactualVerdict['"]/,
      );
    });
  });

  describe('reads scoring_v2 off result with defensive optional chaining', () => {
    it('extracts scoring_v2 via optional chaining on result', () => {
      // Design § Decision 1 (defensive guards) — `result` may be
      // undefined on a v1 history rehydrate. Optional chain or local
      // const fallback both acceptable; we just require it not be a
      // raw `result.scoring_v2` that throws.
      expect(SOURCE).toMatch(/\(result as any\)\?\.scoring_v2|result\?\.scoring_v2/);
    });
  });

  describe('renders the v2 hero card only when scoring_v2 is shapely', () => {
    it('gates v2 card on dimensions array existence + length >= 3', () => {
      // Design § Decision 2: dimensions[] MUST have >=3 entries to
      // ship the v2 contract. <3 indicates incomplete data — fall
      // back to legacy. The wiring must enforce this in JSX, not
      // rely on the components themselves to no-op.
      expect(SOURCE).toMatch(
        /scoring_v2\s*&&\s*scoring_v2\.dimensions\s*&&\s*scoring_v2\.dimensions\.length\s*>=\s*3/,
      );
    });

    it('mounts the v2 card under a discoverable testID', () => {
      // testID on the Animated.View so QA + integration tests can
      // assert the v2 path was taken. Plan § Task 3.5 + hard rule:
      // "Every new component must have testID props on key elements".
      expect(SOURCE).toMatch(/testID=['"]results-scoring-v2['"]/);
    });
  });

  describe('passes correct props to each Bundle E component', () => {
    it('HeroRings receives scoreA, scoreB, winnerIndex from overall_score', () => {
      // Design § Decision 3: rings read overall_score.product_a/b
      // and compute winnerIndex from the comparison. Direct prop pass
      // with `?? 0` fallback for null overall_score.
      expect(SOURCE).toMatch(
        /HeroRings[\s\S]{0,400}scoreA=\{scoring_v2\.overall_score\?\.product_a\s*\?\?\s*0\}/,
      );
      expect(SOURCE).toMatch(
        /HeroRings[\s\S]{0,400}scoreB=\{scoring_v2\.overall_score\?\.product_b\s*\?\?\s*0\}/,
      );
      expect(SOURCE).toMatch(/HeroRings[\s\S]{0,400}winnerIndex=/);
    });

    it('DimensionBars receives dimensions array + winnerIndex', () => {
      // Design § Decision 2: bars take the same dimensions[] array
      // the gate above checked for length>=3. Phase 4.3 wraps the prop in
      // a price-pending filter (pricePending ? ...filter(price) :
      // scoring_v2.dimensions) — the array is still scoring_v2.dimensions.
      expect(SOURCE).toMatch(
        /DimensionBars[\s\S]{0,400}dimensions=\{[\s\S]{0,200}scoring_v2\.dimensions/,
      );
      expect(SOURCE).toMatch(/DimensionBars[\s\S]{0,400}winnerIndex=/);
    });

    it('FactualVerdict only renders when line1 is present', () => {
      // Design § Decision 5: factual_verdict is optional — runner-up
      // with no meaningful delta has no verdict line. The wiring must
      // gate the component on `factual_verdict?.line1` truthiness.
      expect(SOURCE).toMatch(
        /scoring_v2\.factual_verdict\?\.line1\s*&&[\s\S]{0,200}FactualVerdict/,
      );
    });

    it('FactualVerdict receives line1 + line2 props with empty-string fallback', () => {
      // line2 may be undefined (no alternative recommendation); the
      // component must never receive `undefined` as a string prop.
      expect(SOURCE).toMatch(
        /FactualVerdict[\s\S]{0,400}line1=\{scoring_v2\.factual_verdict\.line1\s*\?\?\s*['"]\s*['"]\}/,
      );
      expect(SOURCE).toMatch(
        /FactualVerdict[\s\S]{0,400}line2=\{scoring_v2\.factual_verdict\.line2\s*\?\?\s*['"]\s*['"]\}/,
      );
    });
  });

  describe('one-release backward-compat with legacy scoring', () => {
    it('renders the legacy scoring block only when scoring_v2 is absent', () => {
      // Design § Decision 6: one-release migration. New backend serves
      // scoring_v2 → render v2 card, hide legacy. Old backend serves
      // legacy scoring → render legacy block. NEVER render both — they
      // visually conflict and waste vertical space.
      expect(SOURCE).toMatch(/!\s*scoring_v2\s*&&\s*scoring/);
    });
  });

  describe('color discipline — emerald winner / gray loser only', () => {
    // Plan § Task 3.5 hard rule + design § Decision 3:
    // "Never use orange or red on any score bar/ring/badge.
    //  Only emerald (colors.accent) for winners and gray for losers."
    //
    // The hard rule applies to NEW Bundle E surfaces. The legacy
    // scoring block (now gated off when v2 is present) keeps its old
    // color ramp via getScoreColor — that's intentional one-release
    // backward-compat and ships out on the next release. We scope this
    // check to the v2 section only.
    it('the v2 scoring section uses no orange/red color tokens', () => {
      // Slice the source to just the v2 card region — between the
      // `{/* 8a. Bundle E` comment and the legacy `{!scoring_v2 &&`
      // gate. Banned: any hex literal in the F-row (warning oranges)
      // OR explicit `orange|red|destructive` token names.
      const v2Start = SOURCE.indexOf('Bundle E § Decision 2/3 — scoring_v2 hero card');
      const v2End = SOURCE.indexOf('!scoring_v2', v2Start);
      expect(v2Start).toBeGreaterThan(-1);
      expect(v2End).toBeGreaterThan(v2Start);
      const v2Block = SOURCE.slice(v2Start, v2End);
      expect(v2Block).not.toMatch(/#F[0-9A-F]{2}[0-9A-F]{4}/i); // warning orange family
      expect(v2Block).not.toMatch(/\borange\b|\bdestructive\b|\bred\b/i);
    });
  });
});
