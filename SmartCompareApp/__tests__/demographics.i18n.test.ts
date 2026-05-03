/**
 * Targeted i18n tests for the new demographics + style profile keys.
 * Complements __tests__/i18n.test.ts (which tests parity at the file level)
 * by pinning specific keys important to the cohort feature.
 */

import en from '../src/i18n/en.json';
import ar from '../src/i18n/ar.json';

const enDict = en as Record<string, string>;
const arDict = ar as Record<string, string>;

describe('demographics i18n keys', () => {
  const REQUIRED_KEYS = [
    'demographics.title',
    'demographics.subtitle',
    'demographics.age',
    'demographics.age.18_24',
    'demographics.age.25_34',
    'demographics.age.35_44',
    'demographics.age.45_54',
    'demographics.age.55_plus',
    'demographics.gender',
    'demographics.gender.female',
    'demographics.gender.male',
    'demographics.governorate',
    'demographics.governorate.capital',
    'demographics.governorate.muharraq',
    'demographics.governorate.northern',
    'demographics.governorate.southern',
    'demographics.governorate.other',
    'demographics.preferNotToSay',
    'demographics.skip',
    'demographics.save',
    'demographics.error.network',
  ];

  it.each(REQUIRED_KEYS)('en + ar both define "%s" with non-empty values', (key) => {
    expect(enDict[key]).toBeDefined();
    expect(enDict[key]).not.toBe('');
    expect(arDict[key]).toBeDefined();
    expect(arDict[key]).not.toBe('');
  });

  it('age values do NOT contain digits in keys (semver-safe key naming)', () => {
    // Assert the age keys use underscored variants ("18_24" not "18-24")
    // so they're safe in i18next dotted-path style.
    expect(enDict['demographics.age.18_24']).toBeDefined();
    expect(enDict['demographics.age.55_plus']).toBeDefined();
    expect(enDict['demographics.age.18-24']).toBeUndefined();
  });
});

describe('style profile i18n keys', () => {
  const REQUIRED_KEYS = [
    'profile.styleProfile.title',
    'profile.styleProfile.basedOn',
    'profile.styleProfile.priorities',
    'profile.styleProfile.budget',
    'profile.styleProfile.style',
    'profile.styleProfile.editButton',
    'profile.styleProfile.banner',
    'profile.demographicsCta',
  ];

  it.each(REQUIRED_KEYS)('en + ar both define "%s"', (key) => {
    expect(enDict[key]).toBeDefined();
    expect(arDict[key]).toBeDefined();
  });

  it('basedOn includes {{count}} interpolation in BOTH languages', () => {
    expect(enDict['profile.styleProfile.basedOn']).toContain('{{count}}');
    expect(arDict['profile.styleProfile.basedOn']).toContain('{{count}}');
  });

  it('Arabic strings are non-Latin (sanity check translations are real)', () => {
    const arabicTitle = arDict['profile.styleProfile.title'];
    // Arabic Unicode block: U+0600 to U+06FF
    const hasArabic = /[\u0600-\u06FF]/.test(arabicTitle);
    expect(hasArabic).toBe(true);
  });
});
