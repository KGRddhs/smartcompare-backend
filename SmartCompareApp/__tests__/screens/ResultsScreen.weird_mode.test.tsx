/**
 * Weird-mode hero contract (spec § 2e, updated by Faithful-results Phase 2.1).
 *
 * Source-assertion test (mirrors ResultsScreen.redesign.test.tsx pattern):
 * full-render via RNTL on ResultsScreen would require reproducing the
 * Reanimated entering animation surface + every dependent hook (see existing
 * redesign test header). Source assertions verify the weird-mode branch +
 * banner absence at the code level.
 *
 * Faithful-results Phase 2.1 — the score-rings "hero card" and its weird-mode
 * em-dash stand-in were PRUNED (neither is in the Qaren design-system Results
 * layout, `ResultsScreen.jsx`). The weird-mode CONCEPT survives: the source
 * still derives `isWeird` from `comparison_quality === 'weird'` and uses it to
 * suppress the winner-reveal celebration (RevealBurst). The weird meaning is
 * carried by the backend-rewritten verdict prose. Still NO banner anywhere.
 */
import * as fs from 'fs';
import * as path from 'path';

const RESULTS_PATH = path.resolve(__dirname, '../../src/screens/ResultsScreen.tsx');
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

describe('ResultsScreen weird-mode hero suppression (spec § 2e)', () => {
  it('reads scoring_v2.comparison_quality somewhere in the source', () => {
    expect(SOURCE).toMatch(/scoring_v2[?.\s]*\.?comparison_quality/);
  });

  it('compares comparison_quality === "weird" to gate the celebration swap', () => {
    // Either inline === check or a named const like isWeird; the literal
    // must appear in the file for the gate to exist.
    expect(SOURCE).toMatch(/['"]weird['"]/);
  });

  it('derives an isWeird guard that suppresses the winner-reveal celebration', () => {
    // Faithful-results Phase 2.1 — the guard now gates RevealBurst (the
    // emerald winner-reveal moment), not a rings/em-dash swap. The
    // `!isWeird` form (or an equivalent comparison_quality !== "weird"
    // check) must remain so weird comparisons stay calm.
    expect(SOURCE).toMatch(/!isWeird|isWeird\s*\?|comparison_quality\s*!==\s*['"]weird['"]/);
  });

  it('no longer renders the pruned em-dash hero placeholder', () => {
    // Faithful-results Phase 2.1 — the `results-v2-hero-em-dash` node is
    // gone with the rest of the rings card.
    expect(SOURCE).not.toMatch(/testID=['"]results-v2-hero-em-dash['"]/);
  });

  it('no longer renders the pruned HeroRings score-rings card', () => {
    // The rings testID + the JSX usage are both removed from the render path.
    expect(SOURCE).not.toMatch(/testID=['"]results-v2-hero-rings['"]/);
    expect(SOURCE).not.toMatch(/<HeroRings\b/);
  });

  it('does NOT introduce a weird-comparison banner anywhere', () => {
    // Spec § 2e + critical rule #1 — verdict text carries the meaning
    // in weird mode; no banner, no top-of-screen apology.
    expect(SOURCE).not.toMatch(/testID=['"]results-weird-banner['"]/);
    expect(SOURCE).not.toMatch(/weird[-\s]*banner/i);
  });
});
