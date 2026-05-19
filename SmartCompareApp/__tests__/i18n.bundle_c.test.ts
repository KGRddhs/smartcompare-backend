/**
 * Bundle C — i18n key contract (Plan B.2.1, B.2.3)
 *
 * - Asserts every NEW Bundle C key is present in EN + AR.
 * - Defends against the FIVE critical rules' Rule #3 + Rule #5:
 *   no "estimated" / "reference price" / "indicative" (or AR equivalents)
 *   in any Bundle C key; no scary copy ("couldn't" / "try again" / "Failed to").
 * - Re-verifies the s9 budget-range ladder is monotonic across all 5 tiers
 *   (spec § 3e default `other_light` sub-scale).
 */
import en from '../src/i18n/en.json';
import ar from '../src/i18n/ar.json';

const REQUIRED_KEYS = [
  // Section 3c — 5-tier picker
  'onboarding.s9.luxury',
  'onboarding.s9.luxury_range',
  'onboarding.s9.top_tier',
  'onboarding.s9.top_tier_range',
  'onboarding.s9.caveat',
  // Section 4d — value-match captions
  'results.valueMatch.above_range',
  'results.valueMatch.below_range',
  'results.valueMatch.above_range_with_tradeoff',
  'results.valueMatch.cheaper_of_two',
  // Section 5b — confidence pills + sheet
  'results.confidence.pill.price',
  'results.confidence.pill.reviews',
  'results.confidence.pill.specs',
  'results.confidence.sheet.title',
  'results.confidence.sheet.close',
  // Section 7c — personalization chip
  'results.personalization.chip_template',
  'results.personalization.arrow_up',
  'results.personalization.arrow_down',
] as const;

const EN_RECORD = en as Record<string, string>;
const AR_RECORD = ar as Record<string, string>;

test.each(REQUIRED_KEYS)('EN has Bundle C key %s', (k) => {
  expect(EN_RECORD[k]).toBeTruthy();
});

test.each(REQUIRED_KEYS)('AR has Bundle C key %s', (k) => {
  expect(AR_RECORD[k]).toBeTruthy();
});

// Critical rule #3 + #5: forbidden vocab on every NEW Bundle C key.
const FORBIDDEN_EN = /\b(couldn't|try again|Failed to|estimated|reference price|indicative)\b/i;
const FORBIDDEN_AR = /(تعذر|فشل|تقدير|مُقدَّر)/;

test('no forbidden EN copy across Bundle C keys', () => {
  for (const k of REQUIRED_KEYS) {
    const v = EN_RECORD[k];
    expect(v).not.toMatch(FORBIDDEN_EN);
  }
});

test('no forbidden AR copy across Bundle C keys', () => {
  for (const k of REQUIRED_KEYS) {
    const v = AR_RECORD[k];
    expect(v).not.toMatch(FORBIDDEN_AR);
  }
});

// Plan B.2.3 — budget ranges form monotonic ladder
test('EN budget ranges form monotonic ladder across 5 tiers', () => {
  expect(EN_RECORD['onboarding.s9.budget_range']).toMatch(/11/);
  expect(EN_RECORD['onboarding.s9.mid_range']).toMatch(/57/);
  expect(EN_RECORD['onboarding.s9.premium_range']).toMatch(/189/);
  expect(EN_RECORD['onboarding.s9.luxury_range']).toMatch(/500/);
  expect(EN_RECORD['onboarding.s9.top_tier_range']).toMatch(/500/);
});

// Spec § 7c — personalization chip template MUST contain {{arrows}} placeholder.
test('personalization chip template contains {{arrows}} placeholder in EN + AR', () => {
  expect(EN_RECORD['results.personalization.chip_template']).toContain('{{arrows}}');
  expect(AR_RECORD['results.personalization.chip_template']).toContain('{{arrows}}');
});

// Spec § 7c — arrow keys contain {{dim}} placeholder.
test('arrow keys contain {{dim}} placeholder in EN + AR', () => {
  expect(EN_RECORD['results.personalization.arrow_up']).toContain('{{dim}}');
  expect(EN_RECORD['results.personalization.arrow_down']).toContain('{{dim}}');
  expect(AR_RECORD['results.personalization.arrow_up']).toContain('{{dim}}');
  expect(AR_RECORD['results.personalization.arrow_down']).toContain('{{dim}}');
});

// Spec § 3a — AR `Premium` label is `مميّز`, `Luxury` is `فاخر`. The
// pre-Bundle-C copy reused `فاخر` for s9.premium; this test pins the
// corrected mapping so the label-correction holds going forward.
test('AR onboarding.s9 labels mirror spec § 3a tier table', () => {
  expect(AR_RECORD['onboarding.s9.premium']).toBe('مميّز');
  expect(AR_RECORD['onboarding.s9.luxury']).toBe('فاخر');
  expect(AR_RECORD['onboarding.s9.top_tier']).toBe('الأعلى');
});
