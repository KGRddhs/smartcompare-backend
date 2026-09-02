/**
 * Localized currency display — M21 W4 rtl-i18n (MB-i18n-rtl-02).
 *
 * The app spoke two languages in one screen: Home/History hero copy
 * localizes the currency ("د.ب" via catalog strings) while the Results
 * price lines interpolated the raw Latin ISO code ("BHD 12.500") into
 * Arabic copy. `localizedCurrency` resolves an ISO code through the
 * `currency.*` catalog family (EN keeps ISO codes; AR gets the Arabic
 * glyphs the rest of the app already uses) and falls back to the raw
 * code for anything uncatalogued.
 */
import i18next from 'i18next';
import * as fs from 'fs';
import * as path from 'path';
import en from '../../i18n/en.json';
import ar from '../../i18n/ar.json';
import { localizedCurrency } from '../currencyDisplay';

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

describe('localizedCurrency', () => {
  it('EN: GCC ISO codes stay Latin ISO (design language unchanged in EN)', async () => {
    await inst.changeLanguage('en');
    expect(localizedCurrency('BHD', inst.t)).toBe('BHD');
    expect(localizedCurrency('SAR', inst.t)).toBe('SAR');
  });

  it('AR: GCC codes resolve to the Arabic glyphs the hero copy already uses', async () => {
    await inst.changeLanguage('ar');
    expect(localizedCurrency('BHD', inst.t)).toBe('د.ب');
    expect(localizedCurrency('SAR', inst.t)).toBe('ر.س');
    expect(localizedCurrency('AED', inst.t)).toBe('د.إ');
    expect(localizedCurrency('KWD', inst.t)).toBe('د.ك');
    expect(localizedCurrency('QAR', inst.t)).toBe('ر.ق');
    expect(localizedCurrency('OMR', inst.t)).toBe('ر.ع');
  });

  it('unknown / missing codes fall back to the raw input', async () => {
    await inst.changeLanguage('ar');
    expect(localizedCurrency('XYZ', inst.t)).toBe('XYZ');
    expect(localizedCurrency('', inst.t)).toBe('');
  });

  it('tolerates a t() that echoes keys (jest react-i18next mock shape)', () => {
    const echoT = ((k: string) => k) as any;
    expect(localizedCurrency('BHD', echoT)).toBe('BHD');
  });
});

describe('localizedCurrency wiring (price render sites)', () => {
  const SRC = path.resolve(__dirname, '../..');
  const SITES = [
    'components/results/ResultsContent.tsx',
    'screens/ResultsScreen.tsx',
    'screens/HistoryScreen.tsx',
  ];
  for (const rel of SITES) {
    it(`${rel} formats price currency via localizedCurrency`, () => {
      const src = fs.readFileSync(path.join(SRC, rel), 'utf8');
      expect(src).toMatch(/localizedCurrency\s*\(/);
    });
  }
});
