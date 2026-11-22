/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * INC-C1 OTA-BATCH RED -- last checked (INC_C1_UNIT_SPEC_V2.md section 7.2,
 * rows D1-D7, H4, X1 and the pins D5, P1(a)(b); gate rulings F1, F3, F4).
 *
 * The contract this file fixes for GREEN:
 *  - requestContext.CLIENT_CAPABILITIES deep-equals ['price_size', 'price_asof'];
 *    the built X-Client-Capabilities is exactly 'price_size,price_asof' and
 *    never names vision_anthropic (D1, spec 2.2.1).
 *  - The 'fresh' and 'stale' provenance lines read "Last checked ...": days =
 *    the calendar days between the local start of the as-of day and the local
 *    start of the day of Date.now(), clamped at 0; 0 -> checkedToday, 1 ->
 *    checkedYesterday, >= 2 -> checkedDaysAgo with count and the ASCII figure
 *    (the NoStore forms when the price has no store), plurals by the real
 *    i18next rules (D2, D3, D4, D6, D7). The testIDs results-product-asof-<i>
 *    and -lastseen-<i> stay; 'listed', 'staleNoDate' and the honest line keep
 *    their bytes (D5, P1).
 *  - results.partial.note carries the section 6 row 1 words: no tap promise
 *    (H4).
 *  - A converted_usd price shows the converted label once (the caption); the
 *    price line is the bare amount and the size label wraps the bare amount
 *    (X1).
 *
 * Harness: the INC-C1a sizeLabel.c1a pattern (child components mocked, the
 * REAL ResultsContent and makeProps) with the REAL i18next: an instance set up
 * as in i18n/referralExpiryPlurals.w414, its language changed before each
 * render, so the plural forms are the shipped rules. Clock (F4): Date.now is
 * spied to NOW = 2025-07-15 12:00 local and every as_of is built from local
 * date parts, so a helper that reads the device clock fails. F1: existing
 * exports only, no new path mocked, every base failure is an expect assertion.
 * Arabic from the section 6 code points; this source stays ASCII.
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import enCatalog from '../../src/i18n/en.json';
import arCatalog from '../../src/i18n/ar.json';

import { ResultsContent } from '../../src/components/results/ResultsContent';
import { formatAsOfDate } from '../../src/services/fieldStatusView';

const EN = enCatalog as unknown as Record<string, string>;
const AR = arCatalog as unknown as Record<string, string>;

let mockLang: 'en' | 'ar' = 'en';

jest.mock('react-native-reanimated', () => {
  const real = jest.requireActual('react-native-reanimated');
  const entering = { duration: () => entering, delay: () => entering };
  return {
    __esModule: true,
    ...real,
    default: real.default ?? real,
    FadeIn: entering,
    FadeInDown: entering,
  };
});

// The real i18next over the real catalogs (referralExpiryPlurals.w414 setup).
jest.mock('react-i18next', () => {
  const i18next = require('i18next');
  const en = require('../../src/i18n/en.json');
  const ar = require('../../src/i18n/ar.json');
  const inst = i18next.createInstance();
  inst.init({
    lng: 'en',
    fallbackLng: 'en',
    resources: { en: { translation: en }, ar: { translation: ar } },
    interpolation: { escapeValue: false },
    initAsync: false,
    initImmediate: false,
  });
  const t = inst.t.bind(inst);
  return {
    __esModule: true,
    __inst: inst,
    useTranslation: () => ({
      t,
      i18n: {
        get language() {
          return mockLang;
        },
      },
    }),
  };
});

jest.mock('../../src/components/results/TopMatchBadge', () => ({
  TopMatchBadge: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-top-match-badge'} />;
  },
}));
jest.mock('../../src/components/results/DimensionBars', () => ({
  DimensionBars: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-dim-bars'} />;
  },
}));
jest.mock('../../src/components/results/FactualVerdict', () => ({
  FactualVerdict: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-factual-verdict'} />;
  },
}));
jest.mock('../../src/components/results/ConfidencePills', () => ({
  ConfidencePills: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-confidence-pills'} />;
  },
}));
jest.mock('../../src/components/results/ConfidenceDetailsSheet', () => ({
  ConfidenceDetailsSheet: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-confidence-sheet'} />;
  },
}));
jest.mock('../../src/components/results/PersonalizationChip', () => ({
  PersonalizationChip: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-personalization-chip'} />;
  },
}));
jest.mock('../../src/components/hero/RevealBurst', () => ({
  RevealBurst: () => {
    const { View } = require('react-native');
    return <View testID="mock-reveal-burst" />;
  },
}));
jest.mock('../../src/components/FeedbackCard', () => ({
  __esModule: true,
  default: () => {
    const { View } = require('react-native');
    return <View testID="mock-feedback-card" />;
  },
}));
jest.mock('../../src/components/results/ResultsAccordion', () => ({
  ResultsAccordion: (props: any) => {
    const { View } = require('react-native');
    return <View testID={props.testID ?? 'mock-accordion'} />;
  },
}));

const I18N = (require('react-i18next') as any).__inst;

// ------------------------------------------------------------------ strings --

const u = (...cps: number[]) => String.fromCodePoint(...cps);

// Section 6 rows 1-17 of the unit spec: EN literal, AR from the code points.
const ROW: Record<number, { key: string; en: string; ar: string }> = {
  1: {
    key: 'results.partial.note',
    en: 'Some details did not arrive in time, so a few may be missing.',
    ar: u(
      0x644, 0x645, 0x20, 0x62a, 0x635, 0x644, 0x20, 0x628, 0x639, 0x636, 0x20, 0x627,
      0x644, 0x62a, 0x641, 0x627, 0x635, 0x64a, 0x644, 0x20, 0x641, 0x64a, 0x20, 0x627,
      0x644, 0x648, 0x642, 0x62a, 0x20, 0x627, 0x644, 0x645, 0x646, 0x627, 0x633, 0x628,
      0x60c, 0x20, 0x644, 0x630, 0x627, 0x20, 0x642, 0x62f, 0x20, 0x64a, 0x646, 0x642,
      0x635, 0x20, 0x628, 0x639, 0x636, 0x647, 0x627, 0x2e,
    ),
  },
  2: {
    key: 'results.price.checkedToday',
    en: '{{store}}, last checked today',
    ar: '{{store}}' + u(
      0x60c, 0x20, 0x622, 0x62e, 0x631, 0x20, 0x62a, 0x62d, 0x642, 0x642, 0x20, 0x627,
      0x644, 0x64a, 0x648, 0x645,
    ),
  },
  3: {
    key: 'results.price.checkedTodayNoStore',
    en: 'Last checked today',
    ar: u(
      0x622, 0x62e, 0x631, 0x20, 0x62a, 0x62d, 0x642, 0x642, 0x20, 0x627, 0x644, 0x64a,
      0x648, 0x645,
    ),
  },
  4: {
    key: 'results.price.checkedYesterday',
    en: '{{store}}, last checked yesterday',
    ar: '{{store}}' + u(
      0x60c, 0x20, 0x622, 0x62e, 0x631, 0x20, 0x62a, 0x62d, 0x642, 0x642, 0x20, 0x623,
      0x645, 0x633,
    ),
  },
  5: {
    key: 'results.price.checkedYesterdayNoStore',
    en: 'Last checked yesterday',
    ar: u(0x622, 0x62e, 0x631, 0x20, 0x62a, 0x62d, 0x642, 0x642, 0x20, 0x623, 0x645, 0x633),
  },
  6: {
    key: 'results.price.checkedDaysAgo_zero',
    en: '{{store}}, last checked {{days}} days ago',
    ar: '{{store}}' + u(
      0x60c, 0x20, 0x622, 0x62e, 0x631, 0x20, 0x62a, 0x62d, 0x642, 0x642, 0x20, 0x642,
      0x628, 0x644, 0x20,
    ) + '{{days}}' + u(0x20, 0x64a, 0x648, 0x645),
  },
  7: {
    key: 'results.price.checkedDaysAgo_one',
    en: '{{store}}, last checked 1 day ago',
    ar: '{{store}}' + u(
      0x60c, 0x20, 0x622, 0x62e, 0x631, 0x20, 0x62a, 0x62d, 0x642, 0x642, 0x20, 0x642,
      0x628, 0x644, 0x20, 0x64a, 0x648, 0x645, 0x20, 0x648, 0x627, 0x62d, 0x62f,
    ),
  },
  8: {
    key: 'results.price.checkedDaysAgo_two',
    en: '{{store}}, last checked 2 days ago',
    ar: '{{store}}' + u(
      0x60c, 0x20, 0x622, 0x62e, 0x631, 0x20, 0x62a, 0x62d, 0x642, 0x642, 0x20, 0x642,
      0x628, 0x644, 0x20, 0x64a, 0x648, 0x645, 0x64a, 0x646,
    ),
  },
  9: {
    key: 'results.price.checkedDaysAgo_few',
    en: '{{store}}, last checked {{days}} days ago',
    ar: '{{store}}' + u(
      0x60c, 0x20, 0x622, 0x62e, 0x631, 0x20, 0x62a, 0x62d, 0x642, 0x642, 0x20, 0x642,
      0x628, 0x644, 0x20,
    ) + '{{days}}' + u(0x20, 0x623, 0x64a, 0x627, 0x645),
  },
  10: {
    key: 'results.price.checkedDaysAgo_many',
    en: '{{store}}, last checked {{days}} days ago',
    ar: '{{store}}' + u(
      0x60c, 0x20, 0x622, 0x62e, 0x631, 0x20, 0x62a, 0x62d, 0x642, 0x642, 0x20, 0x642,
      0x628, 0x644, 0x20,
    ) + '{{days}}' + u(0x20, 0x64a, 0x648, 0x645, 0x64b, 0x627),
  },
  11: {
    key: 'results.price.checkedDaysAgo_other',
    en: '{{store}}, last checked {{days}} days ago',
    ar: '{{store}}' + u(
      0x60c, 0x20, 0x622, 0x62e, 0x631, 0x20, 0x62a, 0x62d, 0x642, 0x642, 0x20, 0x642,
      0x628, 0x644, 0x20,
    ) + '{{days}}' + u(0x20, 0x64a, 0x648, 0x645),
  },
  12: {
    key: 'results.price.checkedDaysAgoNoStore_zero',
    en: 'Last checked {{days}} days ago',
    ar: u(
      0x622, 0x62e, 0x631, 0x20, 0x62a, 0x62d, 0x642, 0x642, 0x20, 0x642, 0x628, 0x644,
      0x20,
    ) + '{{days}}' + u(0x20, 0x64a, 0x648, 0x645),
  },
  13: {
    key: 'results.price.checkedDaysAgoNoStore_one',
    en: 'Last checked 1 day ago',
    ar: u(
      0x622, 0x62e, 0x631, 0x20, 0x62a, 0x62d, 0x642, 0x642, 0x20, 0x642, 0x628, 0x644,
      0x20, 0x64a, 0x648, 0x645, 0x20, 0x648, 0x627, 0x62d, 0x62f,
    ),
  },
  14: {
    key: 'results.price.checkedDaysAgoNoStore_two',
    en: 'Last checked 2 days ago',
    ar: u(
      0x622, 0x62e, 0x631, 0x20, 0x62a, 0x62d, 0x642, 0x642, 0x20, 0x642, 0x628, 0x644,
      0x20, 0x64a, 0x648, 0x645, 0x64a, 0x646,
    ),
  },
  15: {
    key: 'results.price.checkedDaysAgoNoStore_few',
    en: 'Last checked {{days}} days ago',
    ar: u(
      0x622, 0x62e, 0x631, 0x20, 0x62a, 0x62d, 0x642, 0x642, 0x20, 0x642, 0x628, 0x644,
      0x20,
    ) + '{{days}}' + u(0x20, 0x623, 0x64a, 0x627, 0x645),
  },
  16: {
    key: 'results.price.checkedDaysAgoNoStore_many',
    en: 'Last checked {{days}} days ago',
    ar: u(
      0x622, 0x62e, 0x631, 0x20, 0x62a, 0x62d, 0x642, 0x642, 0x20, 0x642, 0x628, 0x644,
      0x20,
    ) + '{{days}}' + u(0x20, 0x64a, 0x648, 0x645, 0x64b, 0x627),
  },
  17: {
    key: 'results.price.checkedDaysAgoNoStore_other',
    en: 'Last checked {{days}} days ago',
    ar: u(
      0x622, 0x62e, 0x631, 0x20, 0x62a, 0x62d, 0x642, 0x642, 0x20, 0x642, 0x628, 0x644,
      0x20,
    ) + '{{days}}' + u(0x20, 0x64a, 0x648, 0x645),
  },
};
const AR_BHD = u(0x62f, 0x2e, 0x628);
const cat = (lang: 'en' | 'ar') => (lang === 'ar' ? AR : EN);
const fill = (tpl: string, vars: Record<string, string>) =>
  Object.entries(vars).reduce((s, [k, v]) => s.split(`{{${k}}}`).join(v), tpl);
/** Today's formatted amount, built from the catalog (never from new code). */
const money = (amountText: string, code: string, lang: 'en' | 'ar') =>
  `${amountText} ${cat(lang)[`currency.${code}`] ?? code}`;
const count = (texts: string[], needle: string) => texts.join('\n').split(needle).length - 1;
const DIGIT_OR_MINUS = new RegExp(
  '[-0-9' + u(0x660) + '-' + u(0x669) + u(0x6f0) + '-' + u(0x6f9) + ']',
);

// ------------------------------------------------------------------ clock --

const NOW = new Date(2025, 6, 15, 12, 0, 0).getTime();
/** n days before NOW, built from local date parts (F4). */
const asOf = (n: number) => new Date(2025, 6, 15 - n, 12, 0, 0).toISOString();

// ------------------------------------------------------------------ bodies --

const STORE = 'noon.com';
const STORE_B = 'store-b.example.com';

function product(name: string, p: any) {
  return { name, brand: 'Brand A', category: 'fragrances', price: p, pros: ['Long wear'], cons: ['Pricey'] };
}

/** A genuine BHD price at noon.com; n = null leaves as_of out. */
const price = (n: number | null, x: Record<string, unknown> = {}) => ({
  amount: 58.11,
  currency: 'BHD',
  retailer: STORE,
  source_method: 'page_scrape',
  ...(n === null ? {} : { as_of: asOf(n) }),
  ...x,
});

/** The second card: an undated genuine BHD price at another store. */
const other = (x: Record<string, unknown> = {}) => ({
  amount: 9.5,
  currency: 'BHD',
  retailer: STORE_B,
  source_method: 'local_bhd',
  ...x,
});

const pair = (a: any, b: any = other()) => [product('Fragrance A', a), product('Fragrance B', b)];

function makeProps(products: any[], metadata: any, extra: Record<string, unknown> = {}) {
  const result: any = {
    overview: {
      winner: { product_index: 0, name: products[0].name, reason: 'Fits the brief.' },
      products,
    },
    comparison: {},
    recommendation: 'Fits the brief.',
    metadata: { query: 'a-vs-b', ...(metadata ?? {}) },
  };
  return {
    result,
    products,
    winnerIndex: 0 as 0 | 1,
    scoring_v2: null,
    comparisonId: 'cmp-c1',
    isRTL: mockLang === 'ar',
    feedbackSubmitted: false,
    onFeedbackSubmitted: jest.fn(),
    feedbackComparisonId: 'cmp-c1',
    sheetLeg: null,
    onPillPress: jest.fn(),
    onCloseSheet: jest.fn(),
    winnerRevealed: true,
    winnerScaleAnimStyle: { transform: [{ scale: 1 }] },
    onBack: jest.fn(),
    onShare: jest.fn(),
    ...extra,
  } as any;
}

function allText(node: any): string[] {
  const out: string[] = [];
  const walkNode = (n: any) => {
    if (n == null) return;
    if (typeof n === 'string') {
      out.push(n);
      return;
    }
    if (Array.isArray(n)) {
      n.forEach(walkNode);
      return;
    }
    if (n.children) n.children.forEach(walkNode);
  };
  walkNode(node);
  return out;
}

/** Renders one body in one language; returns the card texts, the testIDs and the tree. */
function show(
  products: any[],
  metadata: any = {},
  lang: 'en' | 'ar' = 'en',
  extra: Record<string, unknown> = {},
) {
  mockLang = lang;
  I18N.changeLanguage(lang);
  // Harness check (passes at base): the real i18next now speaks this language.
  expect(I18N.language).toBe(lang);
  const r = render(<ResultsContent {...makeProps(products, metadata, extra)} />);
  const card = (i: number) => allText(r.getByTestId(`results-product-card-${i}`).children);
  const ids: string[] = r.UNSAFE_root.findAll((n: any) => typeof n.props?.testID === 'string')
    .map((n: any) => n.props.testID as string)
    .filter((id: string, i: number, a: string[]) => a.indexOf(id) === i);
  const textOf = (id: string) => {
    const n = r.queryByTestId(id);
    return n ? allText(n.children).join('') : null;
  };
  return { card0: card(0), card1: card(1), ids, textOf, r };
}

let nowSpy: jest.SpyInstance;
beforeEach(() => {
  mockLang = 'en';
  nowSpy = jest.spyOn(Date, 'now').mockReturnValue(NOW);
});
afterEach(() => {
  nowSpy.mockRestore();
  mockLang = 'en';
});

const LANGS = ['en', 'ar'] as const;
/** Rows loop over many renders; bound each one well above jest's 5 s default. */
const ROW_MS = 30000;

// ------------------------------------------------------------------ D, H4, X1 --

describe('INC-C1 last-checked rows (fail at base)', () => {
  it('D1 capability: CLIENT_CAPABILITIES is exactly [price_size, price_asof]; the header is price_size,price_asof, never vision_anthropic', async () => {
    let rc: any = null;
    jest.isolateModules(() => {
      jest.doMock('../../src/services/deviceFingerprint', () => ({
        getDeviceFingerprint: async () => null,
      }));
      jest.doMock('../../src/services/authService', () => ({
        getSavedUser: async () => null,
      }));
      rc = require('../../src/services/requestContext');
    });
    expect(rc).not.toBeNull();
    expect(rc.CLIENT_CAPABILITIES).toEqual(['price_size', 'price_asof']);
    const headers = await rc.buildContextHeaders({});
    expect(headers['X-Client-Capabilities']).toBe('price_size,price_asof');
    expect(String(headers['X-Client-Capabilities'])).not.toMatch(/vision_anthropic/);
    const config: any = { headers: {} };
    rc.mergeContextHeaders(config, headers);
    expect(config.headers['X-Client-Capabilities']).toBe('price_size,price_asof');
  }, ROW_MS);

  it('D2 n = 0, 1, 2, 3, 10, 11, 29 days: today, yesterday, N days ago (EN rows 2, 4, 11; AR rows 2, 4, 8, 9, 10)', () => {
    const enRow = (n: number) => (n === 0 ? 2 : n === 1 ? 4 : 11);
    const arRow = (n: number) => (n === 0 ? 2 : n === 1 ? 4 : n === 2 ? 8 : n <= 10 ? 9 : 10);
    for (const lang of LANGS) {
      for (const n of [0, 1, 2, 3, 10, 11, 29]) {
        const s = show(pair(price(n)), {}, lang);
        const tid = n <= 7 ? 'results-product-asof-0' : 'results-product-lastseen-0';
        const row = lang === 'ar' ? arRow(n) : enRow(n);
        expect({ lang, n, text: s.textOf(tid) }).toEqual({
          lang,
          n,
          text: fill(ROW[row][lang], { store: STORE, days: String(n) }),
        });
        s.r.unmount();
      }
    }
  }, ROW_MS);

  it('D3 calendar days, not elapsed time: 23:50 the day before at 00:10 -> yesterday; 00:10 at 23:50 the same day -> today', () => {
    const cases = [
      {
        asOf: new Date(2025, 6, 14, 23, 50, 0).toISOString(),
        now: new Date(2025, 6, 15, 0, 10, 0).getTime(),
        row: 4,
      },
      {
        asOf: new Date(2025, 6, 15, 0, 10, 0).toISOString(),
        now: new Date(2025, 6, 15, 23, 50, 0).getTime(),
        row: 2,
      },
    ];
    for (const lang of LANGS) {
      for (const c of cases) {
        nowSpy.mockReturnValue(c.now);
        const s = show(pair(price(null, { as_of: c.asOf })), {}, lang);
        expect({ lang, asOf: c.asOf, text: s.textOf('results-product-asof-0') }).toEqual({
          lang,
          asOf: c.asOf,
          text: fill(ROW[c.row][lang], { store: STORE }),
        });
        s.r.unmount();
      }
    }
  }, ROW_MS);

  it('D4 (F3) an as_of 4 minutes ahead, across midnight: today, no minus sign and no digit', () => {
    nowSpy.mockReturnValue(new Date(2025, 6, 15, 23, 58, 0).getTime());
    const ahead = new Date(2025, 6, 16, 0, 2, 0).toISOString();
    for (const lang of LANGS) {
      const s = show(pair(price(null, { as_of: ahead })), {}, lang);
      const text = s.textOf('results-product-asof-0');
      expect(text).toBe(fill(ROW[2][lang], { store: STORE }));
      expect(String(text)).not.toMatch(DIGIT_OR_MINUS);
      s.r.unmount();
    }
  }, ROW_MS);

  it('D6 no store: n = 0, 1, 3 -> rows 3, 5, then EN row 17 / AR row 15', () => {
    const cases: [number, number, number][] = [
      [0, 3, 3],
      [1, 5, 5],
      [3, 17, 15],
    ];
    for (const lang of LANGS) {
      for (const [n, enRow, arRow] of cases) {
        const s = show(pair(price(n, { retailer: undefined })), {}, lang);
        expect({ lang, n, text: s.textOf('results-product-asof-0') }).toEqual({
          lang,
          n,
          text: fill(ROW[lang === 'ar' ? arRow : enRow][lang], { days: String(n) }),
        });
        s.r.unmount();
      }
    }
  }, ROW_MS);

  it('D7 the date from field_status (no price.as_of): fresh 2 days ago -> EN row 11 (2), AR row 8', () => {
    const md = { field_status: [{ price: { state: 'fresh', as_of: asOf(2) } }, null] };
    for (const lang of LANGS) {
      const s = show(pair(price(null)), md, lang);
      expect(s.textOf('results-product-asof-0')).toBe(
        fill(ROW[lang === 'ar' ? 8 : 11][lang], { store: STORE, days: '2' }),
      );
      s.r.unmount();
    }
  }, ROW_MS);

  it('H4 partial note: metadata.partial true -> row 1 (EN, AR), no tap promise; the shown price lines as today', () => {
    const md = { partial: true, partial_stage: 'post_gather' };
    for (const lang of LANGS) {
      const s = show(pair(price(null)), md, lang);
      expect(s.card0).toContain(money('58.110', 'BHD', lang));
      expect(s.card1).toContain(money('9.500', 'BHD', lang));
      const note = s.textOf('results-content-partial-note');
      expect(note).toBe(ROW[1][lang]);
      expect(String(note)).not.toMatch(/tap/i);
      expect(String(note)).not.toContain(u(0x627, 0x636, 0x63a, 0x637));
      s.r.unmount();
    }
  }, ROW_MS);

  it('X1 converted price: the label once (the caption), the price line the bare amount; with size_ml 100 the size wraps the bare amount', () => {
    const conv = { amount: 7.14, currency: 'BHD', source_method: 'converted_usd', retailer: STORE };
    for (const lang of LANGS) {
      const label = cat(lang)['results.convertedUSD'];
      expect(typeof label).toBe('string');
      const bare = money('7.140', 'BHD', lang);

      const s = show(pair(conv), {}, lang);
      expect({ lang, labels: count(s.card0, label) }).toEqual({ lang, labels: 1 });
      expect(s.card0).toContain(bare);
      expect(s.textOf('results-product-converted-0')).toBe(label);
      s.r.unmount();

      const z = show(pair({ ...conv, size_ml: 100 }), {}, lang);
      expect(z.card0).toContain(fill(cat(lang)['results.price.withSize'], { price: bare, size: '100' }));
      expect({ lang, labels: count(z.card0, label) }).toEqual({ lang, labels: 1 });
      expect(z.textOf('results-product-converted-0')).toBe(label);
      z.r.unmount();
    }
  }, ROW_MS);
});

// ------------------------------------------------------------------ pins --

// Two genuine undated BHD prices: today's card texts (the INC-C1a P1
// 'shown' golden recorded at base b0ad2603; the store is not printed for an
// undated price).
const P1_UNDATED: Record<string, string[]> = {
  'en-0': ['Fragrance A', 'Brand A', '58.110 BHD'],
  'en-1': ['Fragrance B', 'Brand A', '9.500 BHD'],
  'ar-0': ['Fragrance A', 'Brand A', '58.110 ' + AR_BHD],
  'ar-1': ['Fragrance B', 'Brand A', '9.500 ' + AR_BHD],
};

describe('INC-C1 last-checked pins (pass at base)', () => {
  it('D5 pin: 31 d -> the honest line; a stored body -> the listed line (listedOn); live stale without a date -> checkedEarlier', () => {
    for (const lang of LANGS) {
      const a = show(pair(price(31)), {}, lang);
      expect(a.textOf('results-product-price-honest-0')).toBe(cat(lang)['results.honest.notListed']);
      expect(a.ids.filter((id) => /^results-product-(asof|lastseen)-0$/.test(id))).toEqual([]);
      a.r.unmount();

      const b = show(pair(price(2)), {}, lang, { resultOrigin: 'stored' });
      expect(b.textOf('results-product-listed-0')).toBe(
        fill(cat(lang)['results.price.listedOn'], { store: STORE, date: formatAsOfDate(asOf(2), lang) }),
      );
      expect(b.ids.filter((id) => /^results-product-(asof|lastseen)-0$/.test(id))).toEqual([]);
      b.r.unmount();

      const c = show(pair(price(null)), { field_status: [{ price: { state: 'stale', as_of: null } }, null] }, lang);
      expect(c.textOf('results-product-checked-0')).toBe(cat(lang)['results.price.checkedEarlier']);
      c.r.unmount();
    }
  }, ROW_MS);

  it('P1(a)(b) pin: two genuine undated BHD prices keep today\'s cards (golden); a stored body with as_of keeps the listed lines', () => {
    for (const lang of LANGS) {
      const s = show(pair(price(null)), {}, lang);
      expect({ lang, card0: s.card0, card1: s.card1 }).toEqual({
        lang,
        card0: P1_UNDATED[`${lang}-0`],
        card1: P1_UNDATED[`${lang}-1`],
      });
      expect(s.ids.filter((id) => /^results-product-(asof|lastseen|listed|checked)-/.test(id))).toEqual([]);
      s.r.unmount();

      const listedOn = cat(lang)['results.price.listedOn'];
      const st = show(pair(price(2), other({ as_of: asOf(10) })), {}, lang, { resultOrigin: 'stored' });
      expect({ lang, card0: st.card0, card1: st.card1 }).toEqual({
        lang,
        card0: [
          ...P1_UNDATED[`${lang}-0`],
          fill(listedOn, { store: STORE, date: formatAsOfDate(asOf(2), lang) }),
        ],
        card1: [
          ...P1_UNDATED[`${lang}-1`],
          fill(listedOn, { store: STORE_B, date: formatAsOfDate(asOf(10), lang) }),
        ],
      });
      st.r.unmount();
    }
  }, ROW_MS);
});
