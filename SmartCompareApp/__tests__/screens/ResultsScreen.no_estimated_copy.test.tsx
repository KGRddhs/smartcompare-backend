/**
 * Bundle C — ResultsScreen never renders provenance copy (spec § 5c).
 *
 * D.2.6 send-back from qa-bundle-c: pre-existing block at
 * ResultsScreen.tsx:666-668 rendered `(estimated)` / `(تقديري)` as a
 * price caption whenever `source_method === 'estimated'`. Direct
 * violation of `memory/feedback_no_estimated_word_in_ui.md` + spec
 * § 5c "no provenance copy ANYWHERE in the UI" + plan D.2.6 grep
 * acceptance.
 *
 * Source-assertion test (same pattern as ResultsScreen.weird_mode +
 * ResultsScreen.redesign): full-render is out of scope due to
 * Reanimated entering-animation surface. These assertions catch the
 * regression at the source level, which is exactly what plan D.2.6's
 * grep acceptance prescribes.
 */
import * as fs from 'fs';
import * as path from 'path';

const RESULTS_PATH = path.resolve(__dirname, '../../src/screens/ResultsScreen.tsx');
const SOURCE = fs.readFileSync(RESULTS_PATH, 'utf8');

const EN_I18N = fs.readFileSync(
  path.resolve(__dirname, '../../src/i18n/en.json'),
  'utf8',
);
const AR_I18N = fs.readFileSync(
  path.resolve(__dirname, '../../src/i18n/ar.json'),
  'utf8',
);

describe('ResultsScreen never renders provenance copy (spec § 5c)', () => {
  it('does NOT reference the legacy `results.estimated` i18n key', () => {
    expect(SOURCE).not.toMatch(/results\.estimated/);
  });

  it('does NOT branch on product.price.estimated to render UI copy', () => {
    // The legacy block used `product.price?.estimated || ... === 'estimated'`
    // to render a `(estimated)` caption. The branch must be gone — silent UI
    // per spec § 5c is enforced via ConfidencePills `hidePricePill` instead.
    expect(SOURCE).not.toMatch(/source_method\s*===\s*['"]estimated['"]/);
  });
});

describe('i18n bundles do NOT carry provenance copy (spec § 5c + plan D.2.6 grep)', () => {
  const FORBIDDEN_EN_KEYS = ['results.estimated'];
  const FORBIDDEN_AR_PATTERNS = [/(تقدير|مُقدَّر)/];
  const FORBIDDEN_EN_PATTERNS = [/\(estimated\)/i, /\breference price\b/i, /\bindicative\b/i];

  it('en.json drops the legacy results.estimated key', () => {
    for (const k of FORBIDDEN_EN_KEYS) {
      expect(EN_I18N).not.toContain(`"${k}"`);
    }
  });

  it('ar.json drops the legacy results.estimated key', () => {
    for (const k of FORBIDDEN_EN_KEYS) {
      expect(AR_I18N).not.toContain(`"${k}"`);
    }
  });

  it('en.json has zero matches for the provenance vocabulary', () => {
    for (const p of FORBIDDEN_EN_PATTERNS) {
      expect(EN_I18N).not.toMatch(p);
    }
  });

  it('ar.json has zero matches for the Arabic provenance vocabulary', () => {
    for (const p of FORBIDDEN_AR_PATTERNS) {
      expect(AR_I18N).not.toMatch(p);
    }
  });
});
