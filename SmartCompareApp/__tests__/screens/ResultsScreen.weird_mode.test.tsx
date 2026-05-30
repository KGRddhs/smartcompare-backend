/**
 * Bundle C — ResultsScreen weird-mode em-dash hero (Plan B.6.2 + B.6.3, spec § 2e).
 *
 * Source-assertion test (mirrors ResultsScreen.redesign.test.tsx pattern):
 * full-render via RNTL on ResultsScreen would require reproducing the
 * Reanimated entering animation surface + every dependent hook (see
 * existing redesign test header). Source assertions verify the
 * weird-mode branch + em-dash render + banner absence at the code level.
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

  it('compares comparison_quality === "weird" to gate hero swap', () => {
    // Either inline === check or a named const like isWeird; the literal
    // must appear in the file for the gate to exist.
    expect(SOURCE).toMatch(/['"]weird['"]/);
  });

  it('renders a stable em-dash testID node when weird (results-v2-hero-em-dash)', () => {
    expect(SOURCE).toMatch(/testID=['"]results-v2-hero-em-dash['"]/);
  });

  it('hides the HeroRings testID `results-v2-hero-rings` when weird', () => {
    // The branch must be a conditional render around HeroRings. Look
    // for a guard that prevents HeroRings rendering when isWeird.
    expect(SOURCE).toMatch(/!isWeird|isWeird\s*\?|comparison_quality\s*!==\s*['"]weird['"]/);
  });

  it('does NOT introduce a weird-comparison banner anywhere', () => {
    // Spec § 2e + critical rule #1 — verdict text carries the meaning
    // in weird mode; no banner, no top-of-screen apology.
    expect(SOURCE).not.toMatch(/testID=['"]results-weird-banner['"]/);
    expect(SOURCE).not.toMatch(/weird[-\s]*banner/i);
  });

  it('uses em-dash literal (\\u2014) in the suppressed hero state', () => {
    // The em-dash node should render the em-dash character ("—") so
    // verdict text reads naturally. (We also accept the \u2014 escape
    // form.)
    const hasEmDashLiteral = SOURCE.includes('—');
    const hasEmDashEscape = SOURCE.includes('\\u2014');
    expect(hasEmDashLiteral || hasEmDashEscape).toBe(true);
  });

  it('still imports HeroRings (only suppressed conditionally in weird mode)', () => {
    expect(SOURCE).toMatch(/import\s*\{\s*HeroRings\s*\}\s*from/);
  });
});
