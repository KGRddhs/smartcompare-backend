/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * INC-C1a SIZE-LABEL RED -- rows C1..C7 and P1..P2 (INC_C1A_UNIT_SPEC.md
 * section 4, rulings CR-1..CR-5).
 *
 * The contract this RED round fixes for GREEN (see the RED report):
 *  - requestContext.CLIENT_CAPABILITIES deep-equals ['price_size'], so the
 *    built context headers carry X-Client-Capabilities: price_size exactly
 *    (price_asof is NOT declared in this unit).
 *  - ResultsContent product card (the two cards only, CR-5): a SHOWN price
 *    (amount a finite number, unavailable not true, not replaced by the
 *    S81-11 honest line) with size_ml a finite integer in 1..9999 renders
 *    results.price.withSize with {{price}} = today's whole formatPrice output
 *    (the converted label included, once: CR-4) and {{size}} the size
 *    through the app digit policy. Otherwise today's text, byte for byte.
 *  - Per-ml line (testID results-product-perml-<idx>, style
 *    styles.convertedCaption): only with a valid size_ml AND per_ml a finite
 *    number > 0; {{price}} = formatAmountWithCurrency(per_ml, currency, t,
 *    minorUnit + 1) (CR-3: utils/formatNumber.formatPrice gains an optional
 *    4th fraction-digits parameter; the 3-argument call is unchanged). No
 *    client computation of per ml.
 *  - metadata.pair_price_sizes.mode === 'different_sizes' with BOTH prices
 *    shown: one caption results.price.differentSizes, testID
 *    results-price-different-sizes.
 *  - en.json / ar.json gain exactly results.price.withSize, .perMl,
 *    .differentSizes (Arabic byte-exact from PAGE_DESIGN_V2.md section 6a
 *    table, built here from code points: this source stays pure ASCII).
 *
 * Harness: the S81-11 honestUnknowns suite pattern (plain jest.mock of the
 * installed packages and of the child components; the real ResultsContent;
 * the real en.json / ar.json through a t equal to the component's). New
 * behaviour is read at run time, so every RED row fails on an assertion.
 * Synthetic values only.
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import enCatalog from '../../src/i18n/en.json';
import arCatalog from '../../src/i18n/ar.json';

const EN = enCatalog as Record<string, string>;
const AR = arCatalog as Record<string, string>;

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

jest.mock('react-i18next', () => {
  const en = require('../../src/i18n/en.json') as Record<string, string>;
  const ar = require('../../src/i18n/ar.json') as Record<string, string>;
  const t = (key: string, opts?: Record<string, unknown>) => {
    const cat = mockLang === 'ar' ? ar : en;
    let str = cat[key] ?? ((opts?.defaultValue as string) ?? key);
    if (opts) {
      for (const [k, v] of Object.entries(opts)) {
        if (k === 'defaultValue') continue;
        str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
      }
    }
    return str;
  };
  return {
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

import { ResultsContent } from '../../src/components/results/ResultsContent';
import { formatPrice as formatAmountWithCurrency } from '../../src/utils/formatNumber';

// ------------------------------------------------------------------ strings --

const u = (...cps: number[]) => String.fromCodePoint(...cps);
const MIDDOT = u(0xb7);
const AR_ML = u(0x645, 0x644);
const EN_WITH_SIZE = '{{price}} ' + MIDDOT + ' {{size}} ml';
const AR_WITH_SIZE = '{{price}} ' + MIDDOT + ' {{size}} ' + AR_ML;
const EN_PER_ML = '{{price}} per ml';
const AR_PER_ML = '{{price}} ' + u(0x644, 0x643, 0x644) + ' ' + AR_ML;
const EN_DIFF = 'Different bottle sizes, so we do not compare the prices.';
const AR_DIFF = u(
  0x62d, 0x62c, 0x645, 0x627, 0x20, 0x627, 0x644, 0x639, 0x628, 0x648, 0x62a, 0x64a, 0x646,
  0x20, 0x645, 0x62e, 0x62a, 0x644, 0x641, 0x627, 0x646, 0x60c, 0x20, 0x644, 0x630, 0x627,
  0x20, 0x644, 0x627, 0x20, 0x646, 0x642, 0x627, 0x631, 0x646, 0x20, 0x627, 0x644, 0x633,
  0x639, 0x631, 0x64a, 0x646, 0x2e,
);

const fill = (tpl: string, vars: Record<string, string>) =>
  Object.entries(vars).reduce((s, [k, v]) => s.split(`{{${k}}}`).join(v), tpl);

/** Today's formatted amount, built from the catalog (never from new code). */
const money = (amountText: string, code: string, lang: 'en' | 'ar') => {
  const cat = lang === 'ar' ? AR : EN;
  return `${amountText} ${cat[`currency.${code}`] ?? code}`;
};
const conv = (lang: 'en' | 'ar') => (lang === 'ar' ? AR : EN)['results.convertedUSD'];
const withSize = (price: string, size: string, lang: 'en' | 'ar') =>
  fill(lang === 'ar' ? AR_WITH_SIZE : EN_WITH_SIZE, { price, size });
const perMl = (price: string, lang: 'en' | 'ar') =>
  fill(lang === 'ar' ? AR_PER_ML : EN_PER_ML, { price });

/** A t equal to the component's for the EN catalog. */
const tEn = (key: string, opts?: Record<string, unknown>) => {
  let str = EN[key] ?? ((opts?.defaultValue as string) ?? key);
  if (opts) {
    for (const [k, v] of Object.entries(opts)) {
      if (k === 'defaultValue') continue;
      str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
    }
  }
  return str;
};

// ------------------------------------------------------------------ bodies --

const HOUR = 3600 * 1000;
const DAY = 24 * HOUR;
const NOW = Date.parse('2026-11-16T12:00:00Z');
const iso = (ms: number) => new Date(ms).toISOString();
const HOST = 'store-a.example.com';

function product(name: string, price: any) {
  return { name, brand: 'Brand A', category: 'fragrances', price, pros: ['Long wear'], cons: ['Pricey'] };
}

const shown = (amount: number, extra: Record<string, unknown> = {}) => ({
  amount,
  currency: 'BHD',
  retailer: HOST,
  source_method: 'page_scrape',
  ...extra,
});

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
    comparisonId: 'cmp-c1a',
    isRTL: mockLang === 'ar',
    feedbackSubmitted: false,
    onFeedbackSubmitted: jest.fn(),
    feedbackComparisonId: 'cmp-c1a',
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

const NEW_ID_RE = /perml|different-sizes/;

/** Renders one body and returns the card texts, the testIDs and the tree. */
function show(products: any[], metadata: any = {}, lang: 'en' | 'ar' = 'en') {
  mockLang = lang;
  const r = render(<ResultsContent {...makeProps(products, metadata)} />);
  const card = (i: number) => allText(r.getByTestId(`results-product-card-${i}`).children);
  const ids: string[] = r.UNSAFE_root.findAll((n: any) => typeof n.props?.testID === 'string')
    .map((n: any) => n.props.testID as string)
    .filter((id: string, i: number, a: string[]) => a.indexOf(id) === i);
  const textOf = (id: string) => {
    const n = r.queryByTestId(id);
    return n ? allText(n.children).join('') : null;
  };
  const snap = { card0: card(0), card1: card(1), ids, textOf, r };
  return snap;
}

function strip(products: any[]) {
  return products.map((p) => {
    const price = p.price ? { ...p.price } : p.price;
    if (price) {
      delete price.size_ml;
      delete price.per_ml;
    }
    return { ...p, price };
  });
}

/** Rendering with and without the size keys gives the same cards and ids. */
function expectToday(products: any[], metadata: any, lang: 'en' | 'ar') {
  const a = show(products, metadata, lang);
  const b = show(strip(products), metadata, lang);
  expect(a.card0).toEqual(b.card0);
  expect(a.card1).toEqual(b.card1);
  expect(a.ids.filter((id) => NEW_ID_RE.test(id))).toEqual([]);
  expect(a.ids).toEqual(b.ids);
  a.r.unmount();
  b.r.unmount();
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

// ------------------------------------------------------------------ C rows --

describe('INC-C1a C rows (fail at base)', () => {
  it('C1 capability: CLIENT_CAPABILITIES is exactly [price_size] and the built headers carry X-Client-Capabilities: price_size', async () => {
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
    // INC-C1: price_asof joins price_size; the exact value replaces the not-price_asof check.
    expect(rc.CLIENT_CAPABILITIES).toEqual(['price_size', 'price_asof']);
    const headers = await rc.buildContextHeaders({});
    expect(headers['X-Client-Capabilities']).toBe('price_size,price_asof');
    const config: any = { headers: {} };
    rc.mergeContextHeaders(config, headers);
    expect(config.headers['X-Client-Capabilities']).toBe('price_size,price_asof');
  });

  it('C2 size label EN and AR: BHD 58.11 with size_ml 100 renders "58.110 BHD . 100 ml" (and the as-of line stays)', () => {
    expect(EN['results.price.withSize']).toBe(EN_WITH_SIZE);
    expect(AR['results.price.withSize']).toBe(AR_WITH_SIZE);
    const products = [
      product('Fragrance A', shown(58.11, { size_ml: 100 })),
      product('Fragrance B', shown(9.5, { size_ml: 30 })),
    ];
    for (const lang of ['en', 'ar'] as const) {
      const s = show(products, {}, lang);
      const p0 = money('58.110', 'BHD', lang);
      expect(s.card0).toContain(withSize(p0, '100', lang));
      expect(s.card0).not.toContain(p0);
      expect(s.card1).toContain(withSize(money('9.500', 'BHD', lang), '30', lang));
      s.r.unmount();
    }
    // a price carrying both as_of and size_ml shows both lines
    const dated = [
      product('Fragrance A', shown(58.11, { size_ml: 100, as_of: iso(NOW - 2 * DAY) })),
      product('Fragrance B', shown(9.5)),
    ];
    const d = show(dated, {}, 'en');
    expect(d.card0).toContain(withSize(money('58.110', 'BHD', 'en'), '100', 'en'));
    expect(d.ids).toContain('results-product-asof-0');
    d.r.unmount();
  });

  it('C3 per-ml line: per_ml 0.5811 -> "0.5811 BHD per ml" (minor unit + 1, CR-3); absent / 0 / negative / NaN / string -> no line', () => {
    expect(EN['results.price.perMl']).toBe(EN_PER_ML);
    expect(AR['results.price.perMl']).toBe(AR_PER_ML);
    // CR-3: the formatter takes an optional 4th fraction-digits argument;
    // the 3-argument call keeps today's bytes.
    expect(formatAmountWithCurrency(58.11, 'BHD', tEn)).toBe('58.110 BHD');
    expect((formatAmountWithCurrency as any)(0.5811, 'BHD', tEn, 4)).toBe('0.5811 BHD');

    const body = (per: unknown, size: unknown = 100) => [
      product('Fragrance A', shown(58.11, { size_ml: size, per_ml: per })),
      product('Fragrance B', shown(9.5)),
    ];
    for (const lang of ['en', 'ar'] as const) {
      const s = show(body(0.5811), {}, lang);
      expect(s.textOf('results-product-perml-0')).toBe(perMl(money('0.5811', 'BHD', lang), lang));
      expect(s.ids).not.toContain('results-product-perml-1');
      s.r.unmount();
    }
    // a 2-decimal currency: minor unit + 1 = 3 places
    const sar = show(
      [product('Fragrance A', shown(12.5, { currency: 'SAR', size_ml: 100, per_ml: 0.125 })), product('Fragrance B', shown(9.5))],
      {},
      'en',
    );
    expect(sar.textOf('results-product-perml-0')).toBe(perMl('0.125 SAR', 'en'));
    sar.r.unmount();
    // the per-ml line wears the existing caption style
    const styled = show(
      [product('Fragrance A', shown(58.11, { size_ml: 100, per_ml: 0.5811, source_method: 'converted_usd' })), product('Fragrance B', shown(9.5))],
      {},
      'en',
    );
    const perNode: any = styled.r.queryByTestId('results-product-perml-0');
    const convNode: any = styled.r.queryByTestId('results-product-converted-0');
    expect(perNode).not.toBeNull();
    expect(perNode?.props?.style).toEqual(convNode?.props?.style);
    styled.r.unmount();
    // no per_ml key, or a bad one -> no line (no client computation)
    for (const per of [undefined, null, 0, -0.5, NaN, Infinity, '0.5811']) {
      const s = show(body(per), {}, 'en');
      expect(s.ids).not.toContain('results-product-perml-0');
      expect(s.card0.some((x) => /per ml/.test(x))).toBe(false);
      s.r.unmount();
    }
    // per_ml without a valid size_ml -> no line
    for (const size of [null, 0, 10000]) {
      const s = show(body(0.5811, size), {}, 'en');
      expect(s.ids).not.toContain('results-product-perml-0');
      s.r.unmount();
    }
    const noSizeKey = show(
      [product('Fragrance A', shown(58.11, { per_ml: 0.5811 })), product('Fragrance B', shown(9.5))],
      {},
      'en',
    );
    expect(noSizeKey.ids).not.toContain('results-product-perml-0');
    noSizeKey.r.unmount();
  });

  it('C4 converted price (CR-4): the size label wraps today\'s whole price line; the converted label appears once in it', () => {
    const products = [
      product('Fragrance A', shown(58.11, { source_method: 'converted_usd', size_ml: 100 })),
      product('Fragrance B', shown(9.5)),
    ];
    for (const lang of ['en', 'ar'] as const) {
      const label = conv(lang);
      // INC-C1 (T7-08): the size label wraps the bare amount; the caption is the one label.
      const today = money('58.110', 'BHD', lang);
      const s = show(products, {}, lang);
      const line = withSize(today, '100', lang);
      expect(s.card0).toContain(line);
      expect(line.split(label).length - 1).toBe(0);
      // the caption under the price stays as today: same count of the label
      const base = show(strip(products), {}, lang);
      const count = (texts: string[]) => texts.join('\n').split(label).length - 1;
      expect(count(s.card0)).toBe(count(base.card0));
      expect(count(s.card0)).toBe(1);
      s.r.unmount();
      base.r.unmount();
    }
  });

  it('C5 invalid sizes: 0, -5, 1.5, 10000, "100", null, NaN -> today\'s text exactly (1 and 9999 are labelled)', () => {
    // boundary controls: the valid ends of 1..9999 are labelled
    const one = show([product('Fragrance A', shown(58.11, { size_ml: 1 })), product('Fragrance B', shown(9.5))], {}, 'en');
    expect(one.card0).toContain(withSize(money('58.110', 'BHD', 'en'), '1', 'en'));
    one.r.unmount();
    const top = show([product('Fragrance A', shown(58.11, { size_ml: 9999 })), product('Fragrance B', shown(9.5))], {}, 'en');
    const re = new RegExp('^58\\.110 BHD ' + MIDDOT + ' 9,?999 ml$');
    expect(top.card0.some((x) => re.test(x))).toBe(true);
    top.r.unmount();
    for (const size of [0, -5, 1.5, 10000, '100', null, NaN, Infinity]) {
      for (const lang of ['en', 'ar'] as const) {
        expectToday(
          [product('Fragrance A', shown(58.11, { size_ml: size, per_ml: 0.5811 })), product('Fragrance B', shown(9.5))],
          {},
          lang,
        );
      }
    }
  });

  it('C6 pending and N/A: unavailable true or amount null with size_ml -> today\'s text exactly, no per-ml line', () => {
    // paired control: the same side shown gets the label
    const ctl = show([product('Fragrance A', shown(58.11, { size_ml: 100, per_ml: 0.5811 })), product('Fragrance B', shown(9.5))], {}, 'en');
    expect(ctl.card0).toContain(withSize(money('58.110', 'BHD', 'en'), '100', 'en'));
    expect(ctl.ids).toContain('results-product-perml-0');
    ctl.r.unmount();
    const pending = { amount: null, currency: 'BHD', unavailable: true, reason: 'size_mismatch', size_ml: 100, per_ml: 0.5811 };
    const pendingWithAmount = { amount: 58.11, currency: 'BHD', unavailable: true, size_ml: 100, per_ml: 0.5811 };
    const na = { amount: null, currency: 'BHD', size_ml: 100, per_ml: 0.5811 };
    for (const lang of ['en', 'ar'] as const) {
      for (const p of [pending, pendingWithAmount, na]) {
        expectToday([product('Fragrance A', p), product('Fragrance B', shown(9.5))], {}, lang);
      }
      // an amount replaced by the S81-11 honest line is not a shown price
      expectToday(
        [product('Fragrance A', { amount: 40, currency: 'BHD', estimated: true, source_method: 'estimated', size_ml: 100, per_ml: 0.4 }), product('Fragrance B', shown(9.5))],
        { field_status: [{ price: { state: 'unknown', source: 'estimated', reason: 'estimated' } }, null] },
        lang,
      );
    }
  });

  it('C7 different sizes: mode different_sizes with two shown prices -> the caption once; same_size / unknown / absent / one pending -> none', () => {
    expect(EN['results.price.differentSizes']).toBe(EN_DIFF);
    expect(AR['results.price.differentSizes']).toBe(AR_DIFF);
    const two = [
      product('Fragrance A', shown(58.11, { size_ml: 100, per_ml: 0.5811 })),
      product('Fragrance B', shown(9.5, { size_ml: 30, per_ml: 0.3167 })),
    ];
    const diff = { pair_price_sizes: { mode: 'different_sizes', sizes_ml: [100, 30] } };
    for (const lang of ['en', 'ar'] as const) {
      const s = show(two, diff, lang);
      expect(s.r.queryAllByTestId('results-price-different-sizes')).toHaveLength(1);
      expect(s.textOf('results-price-different-sizes')).toBe(lang === 'ar' ? AR_DIFF : EN_DIFF);
      s.r.unmount();
    }
    const none = (products: any[], md: any) => {
      const s = show(products, md, 'en');
      expect(s.ids).not.toContain('results-price-different-sizes');
      expect(s.card0.concat(s.card1).join('\n')).not.toContain(EN_DIFF);
      s.r.unmount();
    };
    none(two, { pair_price_sizes: { mode: 'same_size', sizes_ml: [100, 100] } });
    none(two, { pair_price_sizes: { mode: 'unknown', sizes_ml: [100, null] } });
    none(two, {});
    none(two, { pair_price_sizes: 'different_sizes' });
    const onePending = [
      product('Fragrance A', shown(58.11, { size_ml: 100 })),
      product('Fragrance B', { amount: null, currency: 'BHD', unavailable: true, reason: 'size_mismatch' }),
    ];
    none(onePending, diff);
    const oneNa = [product('Fragrance A', shown(58.11, { size_ml: 100 })), product('Fragrance B', { amount: null, currency: 'BHD' })];
    none(oneNa, diff);
  });
});

// ------------------------------------------------------------------ P rows --

const P1_BODIES: Record<string, any[]> = {
  shown: [product('Fragrance A', shown(58.11)), product('Fragrance B', shown(9.5, { source_method: 'local_bhd' }))],
  converted: [
    product('Fragrance A', shown(58.11, { source_method: 'converted_usd' })),
    product('Fragrance B', { amount: null, currency: 'BHD', unavailable: true, reason: 'size_mismatch' }),
  ],
  mixed: [product('Fragrance A', { amount: null, currency: 'BHD' }), product('Fragrance B', shown(12.5, { currency: 'SAR' }))],
};

// Recorded at base b0ad2603 (2026-11-16, run s96c-red-base1); Arabic as escapes.
const P1_GOLDEN: Record<string, string[]> = {
  // INC-C1 (T7-08): the converted rows show the bare amount; the caption keeps the one label.
  'converted-ar-0': ['Fragrance A', 'Brand A', '58.110 \u062f.\u0628', '(\u0645\u062d\u0648\u0644 \u0645\u0646 \u0627\u0644\u062f\u0648\u0644\u0627\u0631)'],
  'converted-ar-1': ['Fragrance B', 'Brand A', '\u0644\u0627 \u064a\u0648\u062c\u062f \u0633\u0639\u0631 \u0645\u0624\u0643\u062f \u0628\u0639\u062f.'],
  'converted-en-0': ['Fragrance A', 'Brand A', '58.110 BHD', '(converted from USD)'],
  'converted-en-1': ['Fragrance B', 'Brand A', 'No confirmed price yet.'],
  'mixed-ar-0': ['Fragrance A', 'Brand A', '\u0627\u0644\u0633\u0639\u0631 \u063a\u064a\u0631 \u0645\u062a\u0648\u0641\u0631'],
  'mixed-ar-1': ['Fragrance B', 'Brand A', '12.50 \u0631.\u0633'],
  'mixed-en-0': ['Fragrance A', 'Brand A', 'Price N/A'],
  'mixed-en-1': ['Fragrance B', 'Brand A', '12.50 SAR'],
  'shown-ar-0': ['Fragrance A', 'Brand A', '58.110 \u062f.\u0628'],
  'shown-ar-1': ['Fragrance B', 'Brand A', '9.500 \u062f.\u0628'],
  'shown-en-0': ['Fragrance A', 'Brand A', '58.110 BHD'],
  'shown-en-1': ['Fragrance B', 'Brand A', '9.500 BHD'],
};

describe('INC-C1a P rows (pass at base)', () => {
  it('P1 today\'s body (no new key) renders byte-identical card text on both cards, both languages (golden recorded at base)', () => {
    const got: Record<string, string[]> = {};
    for (const [name, products] of Object.entries(P1_BODIES)) {
      for (const lang of ['en', 'ar'] as const) {
        const s = show(products, {}, lang);
        got[`${name}-${lang}-0`] = s.card0;
        got[`${name}-${lang}-1`] = s.card1;
        expect(s.ids.filter((id) => NEW_ID_RE.test(id))).toEqual([]);
        s.r.unmount();
      }
    }
    expect(got).toEqual(P1_GOLDEN);
  });

  it('P2 i18n parity holds and the as-of provenance line is unchanged when size keys are present', () => {
    const enKeys = Object.keys(EN).sort();
    const arKeys = Object.keys(AR).sort();
    expect(arKeys).toEqual(enKeys);
    const vars = (s: string) => [...s.matchAll(/\{\{(\w+)\}\}/g)].map((m) => m[1]).sort();
    for (const k of enKeys) expect(vars(AR[k])).toEqual(vars(EN[k]));
    for (const lang of ['en', 'ar'] as const) {
      for (const [age, tid] of [
        [2 * DAY, 'results-product-asof-0'],
        [10 * DAY, 'results-product-lastseen-0'],
      ] as const) {
        const dated = shown(58.11, { as_of: iso(NOW - age) });
        const a = show([product('Fragrance A', { ...dated, size_ml: 100, per_ml: 0.5811 }), product('Fragrance B', shown(9.5))], {}, lang);
        const b = show([product('Fragrance A', dated), product('Fragrance B', shown(9.5))], {}, lang);
        expect(a.textOf(tid)).not.toBeNull();
        expect(a.textOf(tid)).toBe(b.textOf(tid));
        a.r.unmount();
        b.r.unmount();
      }
    }
  });
});
