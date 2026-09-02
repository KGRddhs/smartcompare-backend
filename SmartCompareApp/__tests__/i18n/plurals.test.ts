/**
 * Live {count} plural resolution — M21 W4 rtl-i18n (MB-i18n-rtl-07/08).
 *
 * Two live call sites interpolate {count} through keys that shipped with
 * NO plural forms, so English rendered "Across 1 decisions" and Arabic
 * (whose CLDR plural categories are zero/one/two/few/many/other) rendered
 * grammatically broken counts for 0, 1, 2, 3-10 and 11-99:
 *
 *   - HomeEditorialSections.tsx  -> t('home.savings.count', { count })
 *   - HistoryScreen.tsx          -> t('history.hero.count', { count })
 *
 * On Hermes there is a second failure layer: Intl.PluralRules is not
 * implemented, so i18next v24+ cannot resolve ANY plural category and
 * Arabic counts fall back to English forms. The `intl-pluralrules`
 * polyfill (guarded — installs only when the engine lacks a working
 * Intl.PluralRules) closes that layer; jest runs on node where Intl is
 * native, so the polyfill CLASS is exercised directly here.
 */
import i18next from 'i18next';
import * as fs from 'fs';
import * as path from 'path';
import en from '../../src/i18n/en.json';
import ar from '../../src/i18n/ar.json';

// The polyfill implementation class itself (what Hermes would run).
// eslint-disable-next-line @typescript-eslint/no-var-requires
const PolyfillPluralRules = require('intl-pluralrules/plural-rules');

const inst = i18next.createInstance();

beforeAll(async () => {
  await inst.init({
    lng: 'en',
    fallbackLng: 'en',
    resources: {
      en: { translation: en },
      ar: { translation: ar },
    },
    interpolation: { escapeValue: false },
  });
});

describe('polyfill class resolves Arabic plural categories (Hermes path)', () => {
  it('ar cardinal categories: zero/one/two/few/many/other', () => {
    const pr = new PolyfillPluralRules('ar');
    expect(pr.select(0)).toBe('zero');
    expect(pr.select(1)).toBe('one');
    expect(pr.select(2)).toBe('two');
    expect(pr.select(3)).toBe('few');
    expect(pr.select(10)).toBe('few');
    expect(pr.select(11)).toBe('many');
    expect(pr.select(99)).toBe('many');
    expect(pr.select(100)).toBe('other');
  });

  it('en cardinal categories: one/other', () => {
    const pr = new PolyfillPluralRules('en');
    expect(pr.select(1)).toBe('one');
    expect(pr.select(2)).toBe('other');
  });
});

describe('home.savings.count — plural forms (MB-i18n-rtl-07)', () => {
  it('EN count 1 is singular (never "Across 1 decisions")', async () => {
    await inst.changeLanguage('en');
    const out = inst.t('home.savings.count', { count: 1 });
    expect(out).not.toMatch(/1 decisions/);
    expect(out).toMatch(/decision\b/);
  });

  it('EN count 5 is plural', async () => {
    await inst.changeLanguage('en');
    expect(inst.t('home.savings.count', { count: 5 })).toMatch(/5 decisions/);
  });

  it('AR resolves distinct forms for 0 / 1 / 2 / few / many', async () => {
    await inst.changeLanguage('ar');
    const outs = [0, 1, 2, 5, 15].map((count) =>
      inst.t('home.savings.count', { count })
    );
    // No bare-key fallback...
    for (const o of outs) expect(o).not.toBe('home.savings.count');
    // ...and the five categories produce five DISTINCT strings. Arabic
    // singular and dual are grammatical (قرار واحد / قرارين) — they carry
    // NO numeral, which is what separates real plural forms from the old
    // single template interpolating {{count}}.
    expect(new Set(outs).size).toBe(5);
    expect(outs[1]).not.toContain('1');
    expect(outs[2]).not.toContain('2');
    expect(outs[3]).toContain('5');
    expect(outs[4]).toContain('15');
  });
});

describe('history.hero.count — plural forms (MB-i18n-rtl-07)', () => {
  it('EN count 1 is singular', async () => {
    await inst.changeLanguage('en');
    const out = inst.t('history.hero.count', { count: 1 });
    expect(out).not.toMatch(/1 decisions/);
    expect(out).toMatch(/decision\b/);
  });

  it('AR resolves distinct forms for 0 / 1 / 2 / few / many', async () => {
    await inst.changeLanguage('ar');
    const outs = [0, 1, 2, 4, 20].map((count) =>
      inst.t('history.hero.count', { count })
    );
    for (const o of outs) expect(o).not.toBe('history.hero.count');
    expect(new Set(outs).size).toBe(5);
    // Singular and dual are grammatical — no interpolated numeral.
    expect(outs[1]).not.toContain('1');
    expect(outs[2]).not.toContain('2');
  });
});

describe('polyfill is wired into app startup', () => {
  it("src/i18n/index.ts imports 'intl-pluralrules' before init", () => {
    const src = fs.readFileSync(
      path.resolve(__dirname, '../../src/i18n/index.ts'),
      'utf8'
    );
    expect(src).toMatch(/import\s+'intl-pluralrules'/);
  });

  it('package.json declares the dependency', () => {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    const pkg = require('../../package.json');
    expect(pkg.dependencies['intl-pluralrules']).toBeDefined();
  });
});
