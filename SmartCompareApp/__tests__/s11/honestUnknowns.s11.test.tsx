/**
 * S81-11 RED -- D20 honest unknowns (spec 2.2 / 2.3, C10 / C15 / C16 / C17;
 * rulings R-S11-12, R-S11-13, R-S11-14, R-S11-16, R-S11-17, R-S11-18,
 * R-S11-21, R-S11-24, R-S11-25).
 *
 * The contract this RED round fixes for GREEN (named here, see the report):
 *  - src/services/fieldStatusView.ts exports productFieldStatus,
 *    isFieldUnknown, priceProvenance(price, fieldPrice, nowMs, origin?),
 *    sectionNeedsHonestLine, formatAsOfDate(dateIso, lang) and the three
 *    window constants.
 *  - priceProvenance kinds: none | fresh | stale | staleNoDate | unknown |
 *    listed ('listed' = a STORED body with a date, R-S11-13: dateful,
 *    stateless, never replaced by age).
 *  - ResultsContent gains the optional prop resultOrigin ('live' default |
 *    'stored'); ResultsScreen passes 'stored' for the comparison_id entry.
 *  - testIDs results-product-price-honest-<i>, -asof-<i>, -lastseen-<i>,
 *    -listed-<i>, -checked-<i>; results-accordion-honest-<section> and
 *    results-accordion-honest-field-<size|concentration>-<i>.
 *  - keys results.honest.notListed, results.price.asOf / asOfNoStore /
 *    lastSeen / lastSeenNoStore / listedOn / listedOnNoStore / checkedEarlier.
 * Absent field_status / section_status / as_of = today's bytes (P rows).
 */

import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render, fireEvent } from '@testing-library/react-native';
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

const mockAccordionProps: any[] = [];
jest.mock('../../src/components/results/ResultsAccordion', () => ({
  ResultsAccordion: (props: any) => {
    mockAccordionProps.push(props);
    const { View } = require('react-native');
    return <View testID={props.testID ?? 'mock-accordion'} />;
  },
}));

import { ResultsContent } from '../../src/components/results/ResultsContent';
import { formatPrice as formatAmountWithCurrency } from '../../src/utils/formatNumber';

function loadOptional(rel: string): any {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    return require(rel);
  } catch {
    return null;
  }
}

function fsv(): any {
  return loadOptional('../../src/services/fieldStatusView');
}

const HOUR = 3600 * 1000;
const DAY = 24 * HOUR;
const NOW = Date.parse('2026-11-05T12:00:00Z');
const iso = (ms: number) => new Date(ms).toISOString();
const HOST = 'store-a.example.com';

/** A t equal to the component's for the price strings (EN catalog). */
const tEn = (key: string, opts?: Record<string, unknown>) => {
  let str = EN[key] ?? key;
  if (opts) {
    for (const [k, v] of Object.entries(opts)) {
      str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
    }
  }
  return str;
};

function product(name: string, price: any) {
  return { name, brand: 'Brand A', price, pros: ['Long wear'], cons: ['Pricey'] };
}

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
    comparisonId: 'cmp-s11',
    isRTL: false,
    feedbackSubmitted: false,
    onFeedbackSubmitted: jest.fn(),
    feedbackComparisonId: 'cmp-s11',
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

const HONEST_ID_RE = /honest|asof|lastseen|listed|checked/;

function honestIds(rendered: any): string[] {
  return rendered.UNSAFE_root.findAll(
    (n: any) => typeof n.props?.testID === 'string' && HONEST_ID_RE.test(n.props.testID),
  ).map((n: any) => n.props.testID);
}

let nowSpy: jest.SpyInstance;
beforeEach(() => {
  mockLang = 'en';
  mockAccordionProps.length = 0;
  nowSpy = jest.spyOn(Date, 'now').mockReturnValue(NOW);
});
afterEach(() => {
  nowSpy.mockRestore();
});

describe('S81-11 E1r -- priceProvenance truth table (the owner staleness rule)', () => {
  const pp = (price: any, fieldPrice: any, origin?: string) =>
    fsv()?.priceProvenance?.(price, fieldPrice, NOW, origin);

  it('the module exports the documented API and constants', () => {
    const m = fsv();
    expect(m).not.toBeNull();
    for (const fn of [
      'productFieldStatus',
      'isFieldUnknown',
      'priceProvenance',
      'sectionNeedsHonestLine',
      'formatAsOfDate',
    ]) {
      expect(typeof m?.[fn]).toBe('function');
    }
    expect(m?.HONEST_PRICE_FRESH_HOURS_CONVERTED).toBe(24);
    expect(m?.HONEST_PRICE_FRESH_DAYS_GENUINE).toBe(7);
    expect(m?.HONEST_PRICE_MAX_AGE_DAYS).toBe(30);
  });

  it('converted: 23 h fresh, 25 h stale; genuine: 6 d fresh, 8 d stale, 31 d unknown', () => {
    const conv = (age: number) =>
      pp({ amount: 10, currency: 'BHD', source_method: 'converted_usd', retailer: HOST, as_of: iso(NOW - age) }, null);
    const gen = (age: number) =>
      pp({ amount: 10, currency: 'BHD', source_method: 'page_scrape', retailer: HOST, as_of: iso(NOW - age) }, null);
    expect(conv(23 * HOUR)?.kind).toBe('fresh');
    expect(conv(25 * HOUR)?.kind).toBe('stale');
    expect(gen(6 * DAY)?.kind).toBe('fresh');
    expect(gen(8 * DAY)?.kind).toBe('stale');
    expect(gen(29 * DAY)?.kind).toBe('stale');
    expect(gen(31 * DAY)?.kind).toBe('unknown');
    expect(gen(6 * DAY)).toEqual({ kind: 'fresh', store: HOST, dateIso: iso(NOW - 6 * DAY) });
  });

  it('R-S11-12: an estimate under field_status unknown/estimated is the honest line; absent field_status = none', () => {
    const est = { amount: 40, currency: 'BHD', estimated: true, source_method: 'estimated', as_of: iso(NOW - DAY) };
    expect(pp(est, { state: 'unknown', source: 'estimated', reason: 'estimated' })?.kind).toBe('unknown');
    expect(pp(est, null)?.kind).toBe('none');
    expect(pp({ amount: 40, currency: 'BHD', estimated: true }, undefined)?.kind).toBe('none');
  });

  it('unavailable / no amount: unknown only under field_status unknown, else none', () => {
    expect(pp({ amount: null, unavailable: true }, { state: 'unknown', reason: 'no_price' })?.kind).toBe('unknown');
    expect(pp({ amount: null, unavailable: true }, null)?.kind).toBe('none');
    expect(pp({ amount: null }, { state: 'unknown', reason: 'no_price' })?.kind).toBe('unknown');
    expect(pp({ amount: null }, null)?.kind).toBe('none');
    expect(pp(undefined, { state: 'unknown', reason: 'no_price' })?.kind).toBe('unknown');
    expect(pp(undefined, null)?.kind).toBe('none');
  });

  it('dates: no as_of anywhere -> none; field_status as_of used; price.as_of preferred; future -> fresh; unparsable -> none', () => {
    const base = { amount: 10, currency: 'BHD', source_method: 'page_scrape', retailer: HOST };
    expect(pp(base, null)?.kind).toBe('none');
    expect(pp(base, { state: 'fresh', as_of: iso(NOW - 2 * DAY) })).toEqual({
      kind: 'fresh',
      store: HOST,
      dateIso: iso(NOW - 2 * DAY),
    });
    expect(
      pp({ ...base, as_of: iso(NOW - 2 * DAY) }, { state: 'fresh', as_of: iso(NOW - 20 * DAY) })?.kind,
    ).toBe('fresh');
    expect(pp({ ...base, as_of: iso(NOW + 3 * DAY) }, null)?.kind).toBe('fresh');
    expect(pp({ ...base, as_of: 'not-a-date' }, null)?.kind).toBe('none');
  });

  it('R-S11-14: the store is price.retailer as-is (a host included), else null', () => {
    const base = { amount: 10, currency: 'BHD', source_method: 'page_scrape', as_of: iso(NOW - DAY) };
    expect(pp({ ...base, retailer: HOST }, null)?.store).toBe(HOST);
    expect(pp({ ...base, retailer: 'Store A' }, null)?.store).toBe('Store A');
    expect(pp({ ...base, retailer: '   ' }, null)?.store).toBeNull();
    expect(pp({ ...base, url: 'https://store-a.example.com/p/1' }, null)?.store).toBeNull();
  });

  it('R-S11-18: field_status stale with as_of null -> the dateless stale marker', () => {
    const base = { amount: 10, currency: 'BHD', source_method: 'page_scrape', retailer: HOST };
    expect(pp(base, { state: 'stale', source: 'served_from_cache', as_of: null })?.kind).toBe('staleNoDate');
  });

  it('R-S11-13: a STORED body with a date is listed (never aged out); without a date none', () => {
    const base = { amount: 10, currency: 'BHD', source_method: 'page_scrape', retailer: HOST };
    expect(pp({ ...base, as_of: iso(NOW - 40 * DAY) }, null, 'stored')).toEqual({
      kind: 'listed',
      store: HOST,
      dateIso: iso(NOW - 40 * DAY),
    });
    expect(pp({ ...base, as_of: iso(NOW - 2 * DAY) }, null, 'stored')?.kind).toBe('listed');
    expect(pp(base, null, 'stored')?.kind).toBe('none');
    expect(pp({ ...base, as_of: iso(NOW - 40 * DAY) }, null, 'live')?.kind).toBe('unknown');
  });
});

describe('S81-11 field_status / section_status readers', () => {
  it('productFieldStatus: only an array entry that is a plain object', () => {
    const m = fsv();
    expect(typeof m?.productFieldStatus).toBe('function');
    if (!m) return;
    const entry = { price: { state: 'unknown' } };
    expect(m.productFieldStatus({ field_status: [entry, null] }, 0)).toEqual(entry);
    expect(m.productFieldStatus({ field_status: [entry, null] }, 1)).toBeNull();
    expect(m.productFieldStatus({ field_status: [entry] }, 1)).toBeNull();
    expect(m.productFieldStatus({ field_status: { 0: entry } }, 0)).toBeNull();
    expect(m.productFieldStatus({ field_status: [[1], 'x'] }, 0)).toBeNull();
    expect(m.productFieldStatus(undefined, 0)).toBeNull();
    expect(m.isFieldUnknown({ state: 'unknown' })).toBe(true);
    expect(m.isFieldUnknown({ state: 'known' })).toBe(false);
    expect(m.isFieldUnknown('unknown')).toBe(false);
  });

  it('R-S11-21: the section line is for unavailable ONLY', () => {
    const m = fsv();
    expect(typeof m?.sectionNeedsHonestLine).toBe('function');
    if (!m) return;
    const md = { section_status: { specs: 'partial', reviews: 'unavailable', pros_cons: 'available' } };
    expect(m.sectionNeedsHonestLine(md, 'specs')).toBe(false);
    expect(m.sectionNeedsHonestLine(md, 'reviews')).toBe(true);
    expect(m.sectionNeedsHonestLine(md, 'pros_cons')).toBe(false);
    expect(m.sectionNeedsHonestLine({}, 'reviews')).toBe(false);
    expect(m.sectionNeedsHonestLine({ section_status: 'unavailable' }, 'reviews')).toBe(false);
  });
});

describe('S81-11 R-S11-24 -- the as-of date is gregorian in both locales', () => {
  it('a known date renders Nov 3 (EN) and the gregorian November (AR), never Hijri', () => {
    const m = fsv();
    expect(typeof m?.formatAsOfDate).toBe('function');
    if (!m) return;
    const d = '2026-11-03T12:00:00Z';
    expect(m.formatAsOfDate(d, 'en')).toBe('Nov 3');
    const ar: string = m.formatAsOfDate(d, 'ar');
    // \u0646\u0648\u0641\u0645\u0628\u0631 = the gregorian month name (November).
    expect(ar).toContain('\u0646\u0648\u0641\u0645\u0628\u0631');
    expect(ar).toMatch(/[3\u0663]/);
    // Hijri month names never appear (Jumada / Rajab family).
    expect(ar).not.toMatch(/\u062c\u0645\u0627\u062f\u0649|\u0631\u062c\u0628/);
  });
});

describe('S81-11 R-S11-24 -- the gregorian calendar is explicit in the source', () => {
  it('fieldStatusView names the gregorian calendar (Node ICU 77 defaults ar-SA to gregory; Hermes may not)', () => {
    const p = path.resolve(__dirname, '../../src/services/fieldStatusView.ts');
    expect(fs.existsSync(p)).toBe(true);
    const src = fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : '';
    expect(src).toMatch(/u-ca-gregory|calendar:\s*'gregory'/);
  });
});

describe('S81-11 E2r / E3r -- the card price under field_status / as_of', () => {
  const p1 = product('Fragrance B', { amount: 30, currency: 'BHD', retailer: HOST, source_method: 'page_scrape' });

  it('E2r: price unknown/no_price + amount null -> the honest line in the card-0 price Text (R-S11-17)', () => {
    const products = [product('Fragrance A', { amount: null, currency: 'BHD' }), p1];
    const md = { field_status: [{ price: { state: 'unknown', source: null, reason: 'no_price' } }, null] };
    const rendered = render(<ResultsContent {...makeProps(products, md)} />);
    const node = rendered.queryByTestId('results-product-price-honest-0');
    expect(node).not.toBeNull();
    const txt = allText(node?.children ?? []).join('');
    expect(txt).toBe(EN['results.honest.notListed']);
    expect(txt).not.toMatch(/N\/A|^-$|^0$/);
    expect(rendered.queryByText(EN['results.priceNA'])).toBeNull();
  });

  it('R-S11-12: an estimate under field_status renders the honest line and NO amount', () => {
    const products = [
      product('Fragrance A', { amount: 40, currency: 'BHD', estimated: true, source_method: 'estimated' }),
      p1,
    ];
    const md = {
      field_status: [{ price: { state: 'unknown', source: 'estimated', reason: 'estimated' } }, null],
    };
    const rendered = render(<ResultsContent {...makeProps(products, md)} />);
    expect(rendered.queryByTestId('results-product-price-honest-0')).not.toBeNull();
    expect(rendered.queryByText(formatAmountWithCurrency(40, 'BHD', tEn))).toBeNull();
  });

  it('E3r: 2 d -> "<store>, as of <date>"; 10 d -> last seen; 31 d -> the honest line, no amount', () => {
    const at = (age: number) => [
      product('Fragrance A', {
        amount: 45,
        currency: 'BHD',
        retailer: HOST,
        source_method: 'page_scrape',
        as_of: iso(NOW - age),
      }),
      p1,
    ];
    const m = fsv();
    expect(typeof m?.formatAsOfDate).toBe('function');
    const fmt = (age: number) => m?.formatAsOfDate?.(iso(NOW - age), 'en');

    const r1 = render(<ResultsContent {...makeProps(at(2 * DAY), {})} />);
    const asof = r1.queryByTestId('results-product-asof-0');
    expect(asof).not.toBeNull();
    expect(allText(asof?.children ?? []).join('')).toBe(
      tEn('results.price.asOf', { store: HOST, date: fmt(2 * DAY) }),
    );
    expect(r1.queryByText(formatAmountWithCurrency(45, 'BHD', tEn))).not.toBeNull();
    r1.unmount();

    const r2 = render(<ResultsContent {...makeProps(at(10 * DAY), {})} />);
    const seen = r2.queryByTestId('results-product-lastseen-0');
    expect(seen).not.toBeNull();
    expect(allText(seen?.children ?? []).join('')).toBe(
      tEn('results.price.lastSeen', { store: HOST, date: fmt(10 * DAY) }),
    );
    r2.unmount();

    const r3 = render(<ResultsContent {...makeProps(at(31 * DAY), {})} />);
    expect(r3.queryByTestId('results-product-price-honest-0')).not.toBeNull();
    expect(r3.queryByText(formatAmountWithCurrency(45, 'BHD', tEn))).toBeNull();
  });

  it('R-S11-18: field_status stale with as_of null -> the dateless checked-earlier marker', () => {
    const products = [
      product('Fragrance A', { amount: 45, currency: 'BHD', retailer: HOST, source_method: 'page_scrape' }),
      p1,
    ];
    const md = {
      field_status: [{ price: { state: 'stale', source: 'served_from_cache', reason: 'served_from_cache', as_of: null } }, null],
    };
    const rendered = render(<ResultsContent {...makeProps(products, md)} />);
    const node = rendered.queryByTestId('results-product-checked-0');
    expect(node).not.toBeNull();
    expect(EN['results.price.checkedEarlier']).toBeDefined();
    expect(allText(node?.children ?? []).join('')).toBe(EN['results.price.checkedEarlier']);
    expect(allText(node?.children ?? []).join('')).not.toMatch(/\d/);
    expect(rendered.queryByText(formatAmountWithCurrency(45, 'BHD', tEn))).not.toBeNull();
  });

  it('R-S11-13: a STORED body renders the amount WITH its listed date, never aged out', () => {
    const products = [
      product('Fragrance A', {
        amount: 45,
        currency: 'BHD',
        retailer: HOST,
        source_method: 'page_scrape',
        as_of: iso(NOW - 40 * DAY),
      }),
      p1,
    ];
    const rendered = render(
      <ResultsContent {...makeProps(products, {}, { resultOrigin: 'stored' })} />,
    );
    const node = rendered.queryByTestId('results-product-listed-0');
    expect(node).not.toBeNull();
    expect(EN['results.price.listedOn']).toBeDefined();
    expect(allText(node?.children ?? []).join('')).toBe(
      tEn('results.price.listedOn', {
        store: HOST,
        date: fsv()?.formatAsOfDate?.(iso(NOW - 40 * DAY), 'en'),
      }),
    );
    expect(rendered.queryByText(formatAmountWithCurrency(45, 'BHD', tEn))).not.toBeNull();
    expect(rendered.queryByTestId('results-product-price-honest-0')).toBeNull();
  });

  it('R-S11-25: the narrow RTL card renders the AR honest line with numberOfLines set', () => {
    mockLang = 'ar';
    const products = [product('Fragrance A', { amount: null, currency: 'BHD' }), p1];
    const md = { field_status: [{ price: { state: 'unknown', reason: 'no_price' } }, null] };
    const rendered = render(<ResultsContent {...makeProps(products, md, { isRTL: true })} />);
    const node = rendered.queryByTestId('results-product-price-honest-0');
    expect(node).not.toBeNull();
    expect(typeof AR['results.honest.notListed']).toBe('string');
    expect(allText(node?.children ?? []).join('')).toBe(AR['results.honest.notListed']);
    expect(typeof node?.props.numberOfLines).toBe('number');
    expect(node?.props.numberOfLines).toBeGreaterThanOrEqual(1);
  });

  it('ResultsScreen passes resultOrigin stored for the comparison_id (History) entry', () => {
    const src = fs
      .readFileSync(path.resolve(__dirname, '../../src/screens/ResultsScreen.tsx'), 'utf8')
      .replace(/\r\n/g, '\n');
    expect(src).toMatch(/resultOrigin=\{/);
    expect(src).toMatch(/comparison_id[\s\S]{0,160}'stored'|'stored'[\s\S]{0,160}comparison_id/);
  });
});

describe('S81-11 the honest prop handed to ResultsAccordion (C15)', () => {
  const products = [
    product('Fragrance A', { amount: 45, currency: 'BHD', retailer: HOST }),
    product('Fragrance B', { amount: 30, currency: 'BHD', retailer: HOST }),
  ];

  it('section_status partial / unavailable / available -> sections {specs false, reviews true, pros_cons false}', () => {
    const md = {
      section_status: { specs: 'partial', reviews: 'unavailable', pros_cons: 'available', price: 'available' },
    };
    render(<ResultsContent {...makeProps(products, md)} />);
    const last = mockAccordionProps[mockAccordionProps.length - 1];
    expect(last?.honest).toBeDefined();
    expect(last?.honest?.sections).toEqual({ specs: false, reviews: true, pros_cons: false });
  });

  it('field_status alone -> honest.fields carries the per-product entries', () => {
    const entry = { size: { state: 'unknown' } };
    render(<ResultsContent {...makeProps(products, { field_status: [entry, null] })} />);
    const last = mockAccordionProps[mockAccordionProps.length - 1];
    expect(last?.honest?.fields).toEqual([entry, null]);
  });

  it('PIN P1 (M21): absent metadata -> no honest prop at all', () => {
    render(<ResultsContent {...makeProps(products, {})} />);
    const last = mockAccordionProps[mockAccordionProps.length - 1];
    expect(last).toBeDefined();
    expect(last.honest).toBeUndefined();
  });
});

describe('S81-11 PIN P1 / R-S11-16 -- absent metadata = today, per surface (green at base)', () => {
  const products = [
    product('Fragrance A', { amount: 45, currency: 'BHD', retailer: HOST, source_method: 'page_scrape' }),
    product('Fragrance B', { amount: null, currency: 'BHD' }),
  ];
  const pending = [
    product('Fragrance A', { amount: null, currency: 'BHD', unavailable: true }),
    product('Fragrance B', { amount: 12.5, currency: 'BHD', source_method: 'converted_usd' }),
  ];

  for (const origin of [undefined, 'live', 'stored']) {
    it(`origin ${String(origin)}: the price strings equal today's and no honest testID renders`, () => {
      const extra = origin ? { resultOrigin: origin } : {};
      const r = render(<ResultsContent {...makeProps(products, {}, extra)} />);
      expect(r.queryByText(formatAmountWithCurrency(45, 'BHD', tEn))).not.toBeNull();
      expect(r.queryByText(EN['results.priceNA'])).not.toBeNull();
      expect(honestIds(r)).toEqual([]);
      r.unmount();
      const r2 = render(<ResultsContent {...makeProps(pending, {}, extra)} />);
      expect(r2.queryByText(EN['results.price.pending'])).not.toBeNull();
      expect(
        r2.queryByText(`${formatAmountWithCurrency(12.5, 'BHD', tEn)} ${EN['results.convertedUSD']}`),
      ).not.toBeNull();
      expect(r2.queryByTestId('results-product-converted-1')).not.toBeNull();
      expect(honestIds(r2)).toEqual([]);
    });
  }

  it('a live body with no as_of renders an identical tree for origin live and absent', () => {
    const a = render(<ResultsContent {...makeProps(products, {})} />).toJSON();
    const b = render(<ResultsContent {...makeProps(products, {}, { resultOrigin: 'live' })} />).toJSON();
    expect(JSON.stringify(b)).toBe(JSON.stringify(a));
  });
});

describe('S81-11 E4r / E5r -- ResultsAccordion honest lines (C16)', () => {
  const { ResultsAccordion } = jest.requireActual('../../src/components/results/ResultsAccordion');
  const products: any[] = [
    { name: 'Fragrance A', brand: 'Brand A', pros: ['Long wear'], cons: ['Pricey'], review_count: 0 },
    { name: 'Fragrance B', brand: 'Brand B', pros: ['Fresh'], cons: ['Short'], review_count: 0 },
  ];
  const specsProducts = [
    { name: 'Fragrance A', specs: { concentration: 'EDP', notes_top: 'Bergamot' } },
    { name: 'Fragrance B', specs: { concentration: 'EDT', notes_top: 'Lemon' } },
  ];

  function renderAcc(honest: any) {
    return render(
      <ResultsAccordion
        products={products}
        specsProducts={specsProducts}
        winnerIndex={0}
        honest={honest}
        testID="acc"
      />,
    );
  }

  it('E4r: reviews unavailable -> the section line first in its body; specs partial / proscons available -> none', () => {
    const r = renderAcc({
      sections: { specs: false, reviews: true, pros_cons: false },
      fields: [null, null],
    });
    fireEvent.press(r.getByTestId('results-accordion-toggle-reviews'));
    const body = r.getByTestId('results-accordion-body-reviews');
    const first = (body.children[0] as any)?.props?.testID;
    expect(first).toBe('results-accordion-honest-reviews');
    expect(allText(r.getByTestId('results-accordion-honest-reviews').children).join('')).toBe(
      EN['results.honest.notListed'],
    );
    fireEvent.press(r.getByTestId('results-specs-toggle'));
    expect(r.queryByTestId('results-accordion-honest-specs')).toBeNull();
    fireEvent.press(r.getByTestId('results-accordion-toggle-proscons'));
    expect(r.queryByTestId('results-accordion-honest-proscons')).toBeNull();
  });

  it('E4r-b: specs unavailable -> the section line is the first child of the specs body', () => {
    const r = renderAcc({ sections: { specs: true, reviews: false, pros_cons: false }, fields: [null, null] });
    fireEvent.press(r.getByTestId('results-specs-toggle'));
    const body = r.getByTestId('results-accordion-body-specs');
    expect((body.children[0] as any)?.props?.testID).toBe('results-accordion-honest-specs');
  });

  it('E5r: size unknown + no size/volume row -> the field line; concentration unknown but listed -> none', () => {
    const r = renderAcc({
      sections: { specs: false, reviews: false, pros_cons: false },
      fields: [{ size: { state: 'unknown' }, concentration: { state: 'unknown' } }, null],
    });
    fireEvent.press(r.getByTestId('results-specs-toggle'));
    const row = r.queryByTestId('results-accordion-honest-field-size-0');
    expect(row).not.toBeNull();
    expect(allText(row?.children ?? []).join('')).toContain(EN['results.honest.notListed']);
    expect(r.queryByTestId('results-accordion-honest-field-concentration-0')).toBeNull();
    expect(r.queryByTestId('results-accordion-honest-field-size-1')).toBeNull();
  });

  it('E5r-b: a size unknown WITH a volume row -> no field line', () => {
    const r = render(
      <ResultsAccordion
        products={products}
        specsProducts={[
          { name: 'Fragrance A', specs: { volume: '100 ml', concentration: 'EDP' } },
          { name: 'Fragrance B', specs: { volume: '50 ml', concentration: 'EDT' } },
        ]}
        winnerIndex={0}
        honest={{
          sections: { specs: false, reviews: false, pros_cons: false },
          fields: [{ size: { state: 'unknown' } }, null],
        }}
        testID="acc"
      />,
    );
    fireEvent.press(r.getByTestId('results-specs-toggle'));
    expect(r.queryByTestId('results-accordion-honest-field-size-0')).toBeNull();
  });

  it('PIN: no honest prop -> no honest testID in any open body (today)', () => {
    const r = renderAcc(undefined);
    for (const id of ['results-accordion-toggle-reviews', 'results-specs-toggle', 'results-accordion-toggle-proscons']) {
      fireEvent.press(r.getByTestId(id));
      expect(honestIds(r)).toEqual([]);
    }
  });
});
