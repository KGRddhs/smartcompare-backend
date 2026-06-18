/**
 * FA4 walk-fix 2026-06-18 — fashion CategoryProfile labels must be the
 * clearest form that fits ONE LINE in the narrow 2-up profile column (no
 * wrap/clip per the #20 overflow fix). Concise single words unless a word is
 * ambiguous (then a short 2-word form). This guard pins the readability
 * requirement: every fashion `results.spec.<key>` exists in EN + AR and the
 * EN label stays within a one-line-safe budget. A future regression that
 * re-lengthens a label (e.g. back to "Design details" / "Size options")
 * trips this.
 */
import en from '../../src/i18n/en.json';
import ar from '../../src/i18n/ar.json';

const enRec = en as Record<string, string>;
const arRec = ar as Record<string, string>;

// The fashion category schema fields (CATEGORY_SPEC_SCHEMAS.fashion).
const FASHION_KEYS = [
  'material',
  'style',
  'closure_type',
  'size_options',
  'care_instructions',
  'craftsmanship',
  'collection_season',
  'origin',
  'color',
  'design_details',
];

// One-line-safe budget for the narrow uppercase 11px profile-column label.
// "Craftsmanship" (13) is the longest legitimate single-word fashion term.
const MAX_LABEL_CHARS = 14;

describe('FA4 — fashion CategoryProfile labels are one-line readable', () => {
  it.each(FASHION_KEYS)('results.spec.%s has an EN + AR label', (key) => {
    const k = `results.spec.${key}`;
    expect(typeof enRec[k]).toBe('string');
    expect(enRec[k].length).toBeGreaterThan(0);
    expect(typeof arRec[k]).toBe('string');
    expect(arRec[k].length).toBeGreaterThan(0);
  });

  it.each(FASHION_KEYS)(
    'results.spec.%s EN label fits one line (<= %i chars)',
    (key) => {
      expect(enRec[`results.spec.${key}`].length).toBeLessThanOrEqual(
        MAX_LABEL_CHARS,
      );
    },
  );

  it('the previously-too-long labels are now the concise forms', () => {
    // Regression pins for the exact FA4 shortenings.
    expect(enRec['results.spec.size_options']).toBe('Sizes');
    expect(enRec['results.spec.design_details']).toBe('Design');
    // AR single-word forms (one-line in the RTL column).
    expect(arRec['results.spec.closure_type']).toBe('الإغلاق');
    expect(arRec['results.spec.size_options']).toBe('المقاسات');
    expect(arRec['results.spec.origin']).toBe('المنشأ');
    expect(arRec['results.spec.design_details']).toBe('التصميم');
  });
});
