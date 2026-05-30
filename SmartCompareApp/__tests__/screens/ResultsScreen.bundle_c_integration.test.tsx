/**
 * Bundle C — ResultsScreen integration (Plan B.8.1 - B.8.6, spec § 5b / § 5c / § 5d / § 7a).
 *
 * Source-assertion test (same pattern as ResultsScreen.redesign.test.tsx).
 * Verifies the legacy single-word confidence banner is removed AND that
 * the new Bundle C surfaces (ConfidencePills, ConfidenceDetailsSheet,
 * PersonalizationChip) are wired into the scoring_v2 hero card.
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

describe('ResultsScreen Bundle C integration — confidence pills + chip', () => {
  it('drops the legacy single-word confidence banner block (spec § 5d)', () => {
    // Old banner used a `confidenceBanner` style — gone.
    expect(SOURCE).not.toMatch(/styles\.confidenceBanner/);
    // Stylesheet entry also removed.
    expect(SOURCE).not.toMatch(/confidenceBanner:\s*\{/);
  });

  it('imports ConfidencePills + ConfidenceDetailsSheet from results/', () => {
    expect(SOURCE).toMatch(/import\s*\{\s*ConfidencePills\s*\}\s*from\s*['"]\.\.\/components\/results\/ConfidencePills['"]/);
    expect(SOURCE).toMatch(/import\s*\{\s*ConfidenceDetailsSheet\s*\}\s*from\s*['"]\.\.\/components\/results\/ConfidenceDetailsSheet['"]/);
  });

  it('imports anyEstimated helper from services/sourceMethod', () => {
    expect(SOURCE).toMatch(/import\s*\{\s*anyEstimated\s*\}\s*from\s*['"]\.\.\/services\/sourceMethod['"]/);
  });

  it('renders ConfidencePills with hidePricePill computed from anyEstimated(products)', () => {
    expect(SOURCE).toMatch(/<ConfidencePills/);
    // hidePricePill prop must be wired from the helper.
    expect(SOURCE).toMatch(/hidePricePill=\{anyEstimated\(products\)\}/);
  });

  it('renders ConfidenceDetailsSheet at the scoring_v2 layer with local sheetLeg state', () => {
    expect(SOURCE).toMatch(/<ConfidenceDetailsSheet/);
    // useState managing the open leg.
    expect(SOURCE).toMatch(/sheetLeg/);
    // onPillPress wires to setSheetLeg.
    expect(SOURCE).toMatch(/onPillPress=\{[^}]*setSheetLeg/);
  });

  it('imports + wires PersonalizationChip below the verdict section', () => {
    expect(SOURCE).toMatch(/import\s*\{\s*PersonalizationChip\s*\}\s*from\s*['"]\.\.\/components\/results\/PersonalizationChip['"]/);
    expect(SOURCE).toMatch(/<PersonalizationChip\s+appliedShifts=\{scoring_v2[^}]*personalization[^}]*applied_shifts\}/);
  });

  it('does NOT remove CohortBadge (spec § 7d — stays separate from personalization chip)', () => {
    // CohortBadge is its own slot per spec; ensure we don't accidentally merge.
    expect(SOURCE).toMatch(/<CohortBadge/);
    expect(SOURCE).toMatch(/results-cohort-badge-slot/);
  });

  it('FactualVerdict still wires line1 + line2 (spec § 1b backend contract)', () => {
    expect(SOURCE).toMatch(/scoring_v2\.factual_verdict\.line1/);
    expect(SOURCE).toMatch(/scoring_v2\.factual_verdict\.line2/);
  });
});
