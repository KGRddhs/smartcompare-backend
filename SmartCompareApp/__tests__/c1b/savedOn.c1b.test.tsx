/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * INC-C1b RED -- T7-11 "Saved on <date>" on a result re-opened from History
 * (INC_C1B_UNIT_SPEC_V2.md section 3 and 10.2: rows S1-S3, pins P-S1, P-S2;
 * ruling RU-9).
 *
 * The contract this file fixes for GREEN:
 *  - getComparison adds saved_at = wrapper.comparison.created_at when it is a
 *    string that Date.parse reads (Number.isFinite), with or without an id;
 *    comparison_id keeps its rule; no saved_at key otherwise; the 404 contract
 *    stands (S1, P-S1).
 *  - ResultsContent with resultOrigin 'stored' and a readable result.saved_at
 *    renders testID results-saved-on = t('results.savedOn', { date }), the
 *    date as month (short), day and year, gregorian, ASCII digits, as the
 *    first child of the scroll content (after the header, before
 *    results-content-hero-pair). A live result, a missing origin, a missing or
 *    unreadable saved_at: no such line (S2, P-S2).
 *  - ResultsScreen opened with route.params.comparison_id passes the stored
 *    origin and the loaded body, so the line shows on a History re-open (S3).
 *
 * Harness: getComparison through the REAL api.ts (jest.requireActual) with
 * axios mocked (the api.getComparison.comparisonId.m18 pattern);
 * ResultsContent with the INC-C1 lastChecked harness (child components
 * mocked by their existing paths, the real i18next over the real catalogs);
 * ResultsScreen with services/api mocked and fake timers (the
 * ResultsScreen.historyFloor.a17 pattern). Dates at 12:00Z, so CI (UTC) and
 * the box (UTC+3) agree. F1: no new symbol is imported; every base failure is
 * an expect assertion. Arabic is built from code points; this source stays
 * ASCII. Synthetic values only.
 */

import React from 'react';
import { act, render } from '@testing-library/react-native';

import { ResultsContent } from '../../src/components/results/ResultsContent';
import ResultsScreen from '../../src/screens/ResultsScreen';

let mockLang: 'en' | 'ar' = 'en';
const mockGetComparison = jest.fn();

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

// ResultsScreen's import graph (ResultsScreen.historyFloor.a17 boundary mocks).
jest.mock('../../src/services/api', () => ({
  getComparison: (...args: any[]) => mockGetComparison(...args),
  identifyFromImages: jest.fn(),
  trackEvents: jest.fn().mockResolvedValue(undefined),
  submitFeedback: jest.fn().mockResolvedValue(undefined),
  shareComparison: jest.fn(),
  putDemographics: jest.fn().mockResolvedValue(undefined),
  parseApiError: jest.fn(() => ({ code: 'INTERNAL_ERROR', message: '' })),
}));
// The REAL api.ts (loaded with jest.requireActual below) talks to this axios.
jest.mock('axios', () => {
  const instance = {
    get: jest.fn(),
    put: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  };
  return { create: jest.fn(() => instance), __instance: instance };
});
jest.mock('../../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));
jest.mock('../../src/services/authService', () => ({
  getToken: jest.fn().mockResolvedValue('synthetic'),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
  getSavedUser: jest.fn().mockResolvedValue(null),
  onSessionInvalid: jest.fn(() => () => undefined),
}));
jest.mock('../../src/services/demographicsTrigger', () => ({
  loadDemographicsState: jest.fn().mockResolvedValue({}),
  shouldShowDemographicsPrompt: jest.fn().mockReturnValue(false),
  recordDismissal: jest.fn().mockResolvedValue(undefined),
  recordSubmission: jest.fn().mockResolvedValue(undefined),
}));
jest.mock('expo-localization', () => ({
  locale: 'en-US',
  getLocales: () => [{ languageCode: 'en', regionCode: 'BH' }],
}));
jest.mock('../../src/hooks/useLanguage', () => ({
  useLanguage: () => ({ isRTL: false, language: 'en', setLanguage: jest.fn() }),
}));
jest.mock('../../src/lib/performance/wallTimeInstrumentation', () => ({
  getWallTimeTracker: () => ({ mark: jest.fn(), report: jest.fn(), reset: jest.fn(), start: jest.fn() }),
}));

const I18N = (require('react-i18next') as any).__inst;

/** The real services/api module, loaded once on first use. */
let realApiModule: { getComparison: (id: string) => Promise<any> } | null = null;
const realApi = () => {
  if (!realApiModule) {
    realApiModule = jest.requireActual('../../src/services/api') as { getComparison: (id: string) => Promise<any> };
  }
  return realApiModule as { getComparison: (id: string) => Promise<any> };
};
const axiosGet = (): jest.Mock => (require('axios') as any).__instance.get;

// ------------------------------------------------------------------ data --

const u = (...cps: number[]) => String.fromCodePoint(...cps);
const ROW_ID = '3f2b8c1d-9a4e-4f6b-8c2d-1e5a7b9c0d2f';
// The server's created_at shape (six fraction digits, +00:00), at 12:00Z.
const CREATED_AT = '2026-11-22T12:00:00.000000+00:00';
// Section 9 row 1, the words before {{date}}.
const AR_SAVED_ON_PREFIX = u(0x645, 0x62d, 0x641, 0x648, 0x638, 0x629, 0x20, 0x628, 0x62a, 0x627, 0x631, 0x64a, 0x62e, 0x20);
const INDIC_DIGIT = new RegExp('[' + u(0x660) + '-' + u(0x669) + u(0x6f0) + '-' + u(0x6f9) + ']');

const fullBody = () => ({
  success: true,
  products: [{ name: 'Fragrance A' }, { name: 'Fragrance B' }],
  metadata: { query: 'Fragrance A vs Fragrance B', region: 'bahrain' },
});

const price = (amount: number) => ({
  amount,
  currency: 'BHD',
  retailer: 'store-a.example.com',
  source_method: 'page_scrape',
});
const product = (name: string, amount: number) => ({
  name,
  brand: 'Brand A',
  category: 'fragrances',
  price: price(amount),
  pros: ['Long wear'],
  cons: ['Pricey'],
});

/** A v2 body as the comparisons row stores it (render-light: no scoring_v2). */
const storedBody = () => {
  const products = [product('Fragrance A', 58.11), product('Fragrance B', 9.5)];
  return {
    success: true,
    overview: {
      winner: { product_index: 0, name: 'Fragrance A', reason: 'Fits the brief.' },
      products,
    },
    comparison: { winner_index: 0 },
    recommendation: 'Fits the brief.',
    metadata: { query: 'Fragrance A vs Fragrance B', region: 'bahrain' },
  };
};

function contentProps(lang: 'en' | 'ar', opts: { origin?: 'live' | 'stored'; savedAt?: unknown }): any {
  const body: any = storedBody();
  if (opts.savedAt !== undefined) body.saved_at = opts.savedAt;
  return {
    result: body,
    products: body.overview.products,
    winnerIndex: 0 as 0 | 1,
    scoring_v2: null,
    comparisonId: ROW_ID,
    ...(opts.origin ? { resultOrigin: opts.origin } : {}),
    isRTL: lang === 'ar',
    feedbackSubmitted: false,
    onFeedbackSubmitted: jest.fn(),
    feedbackComparisonId: ROW_ID,
    sheetLeg: null,
    onPillPress: jest.fn(),
    onCloseSheet: jest.fn(),
    winnerRevealed: true,
    winnerScaleAnimStyle: { transform: [{ scale: 1 }] },
    onBack: jest.fn(),
    onShare: jest.fn(),
  };
}

// ------------------------------------------------------------------ reads --

type Rendered = ReturnType<typeof render>;

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
const has = (r: Rendered, id: string) => r.queryByTestId(id) !== null;
const textOf = (r: Rendered, id: string): string | null => {
  const n = r.queryByTestId(id);
  return n ? allText(n.children).join('') : null;
};
/** Every testID in document order (first occurrence). */
const testIds = (r: Rendered): string[] =>
  r.UNSAFE_root.findAll((n: any) => typeof n.props?.testID === 'string')
    .map((n: any) => n.props.testID as string)
    .filter((id: string, i: number, a: string[]) => a.indexOf(id) === i);

function show(props: any, lang: 'en' | 'ar'): Rendered {
  mockLang = lang;
  I18N.changeLanguage(lang);
  // Harness check (passes at base): the real i18next now speaks this language.
  expect(I18N.language).toBe(lang);
  return render(<ResultsContent {...props} />);
}

const navigation = () => ({ goBack: jest.fn(), navigate: jest.fn(), setOptions: jest.fn() }) as any;

/** Drain queued microtasks inside act (the screen's dynamic import and awaits). */
const flush = async () => {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
};

beforeEach(() => {
  mockLang = 'en';
  mockGetComparison.mockReset();
});
afterEach(() => {
  mockLang = 'en';
});

// ------------------------------------------------------------------ rows --

describe('INC-C1b T7-11 rows (fail at base)', () => {
  it('S1 getComparison adds saved_at = comparison.created_at (a string Date.parse reads), with or without an id', async () => {
    const get = axiosGet();
    get.mockReset();
    get.mockResolvedValueOnce({
      data: { success: true, comparison: { id: ROW_ID, full_response: fullBody(), created_at: CREATED_AT } },
    });
    const withId = await realApi().getComparison(ROW_ID);
    get.mockResolvedValueOnce({
      data: { success: true, comparison: { full_response: fullBody(), created_at: CREATED_AT } },
    });
    const noId = await realApi().getComparison(ROW_ID);
    expect({
      withId: { savedAt: withId.saved_at ?? null, comparisonId: withId.comparison_id ?? null },
      noId: { savedAt: noId.saved_at ?? null, hasComparisonId: 'comparison_id' in noId },
    }).toEqual({
      withId: { savedAt: CREATED_AT, comparisonId: ROW_ID },
      noId: { savedAt: CREATED_AT, hasComparisonId: false },
    });
  });

  it('S2 a stored result with saved_at reads "Saved on <date>" above the product pair (EN, AR)', () => {
    const en = show(contentProps('en', { origin: 'stored', savedAt: CREATED_AT }), 'en');
    const enText = textOf(en, 'results-saved-on');
    const ids = testIds(en);
    const at = ids.indexOf('results-saved-on');
    const placed = at > ids.indexOf('results-content-header') && at < ids.indexOf('results-content-hero-pair');
    en.unmount();

    const ar = show(contentProps('ar', { origin: 'stored', savedAt: CREATED_AT }), 'ar');
    const arText = textOf(ar, 'results-saved-on');
    ar.unmount();
    const a = arText ?? '';
    expect({
      en: enText,
      placed,
      ar: {
        present: arText !== null,
        prefix: a.startsWith(AR_SAVED_ON_PREFIX),
        day: a.includes('22'),
        year: a.includes('2026'),
        indicDigit: INDIC_DIGIT.test(a),
        latinLetter: /[A-Za-z]/.test(a),
      },
    }).toEqual({
      en: 'Saved on Nov 22, 2026',
      placed: true,
      ar: { present: true, prefix: true, day: true, year: true, indicDigit: false, latinLetter: false },
    });
  });

  it('S3 a History re-open (route.params.comparison_id) shows the saved-on line once the stored body loads', async () => {
    jest.useFakeTimers();
    try {
      mockGetComparison.mockResolvedValue({ ...storedBody(), comparison_id: ROW_ID, saved_at: CREATED_AT });
      mockLang = 'en';
      I18N.changeLanguage('en');
      const r = render(
        <ResultsScreen route={{ params: { comparison_id: ROW_ID } } as any} navigation={navigation()} />,
      );
      // Harness: the screen mounted into the History loading state.
      const loading = has(r, 'results-loading-state');
      for (let i = 0; i < 8; i++) await flush();
      expect({
        loading,
        fetched: mockGetComparison.mock.calls.map((c: any[]) => c[0]),
        content: has(r, 'results-content'),
        savedOn: has(r, 'results-saved-on'),
      }).toEqual({ loading: true, fetched: [ROW_ID], content: true, savedOn: true });
      r.unmount();
    } finally {
      jest.useRealTimers();
    }
  });
});

describe('INC-C1b T7-11 pins (pass at base)', () => {
  it('P-S1 no saved_at without a created_at string Date.parse reads (with or without an id); comparison_id keeps its rule; the 404 contract stands', async () => {
    const get = axiosGet();
    get.mockReset();
    const cases: { name: string; comparison: Record<string, unknown> }[] = [
      { name: 'id, no created_at', comparison: { id: ROW_ID } },
      { name: 'id, numeric created_at', comparison: { id: ROW_ID, created_at: 1763812800 } },
      { name: 'id, unreadable created_at', comparison: { id: ROW_ID, created_at: 'not-a-date' } },
      { name: 'no id, no created_at', comparison: {} },
      { name: 'no id, numeric created_at', comparison: { created_at: 1763812800 } },
      { name: 'no id, unreadable created_at', comparison: { created_at: 'not-a-date' } },
    ];
    const got: unknown[] = [];
    for (const c of cases) {
      get.mockResolvedValueOnce({
        data: { success: true, comparison: { ...c.comparison, full_response: fullBody() } },
      });
      const payload = await realApi().getComparison(ROW_ID);
      got.push({
        name: c.name,
        hasSavedAt: 'saved_at' in payload,
        comparisonId: payload.comparison_id ?? null,
        products: Array.isArray(payload.products) ? payload.products.length : null,
      });
    }
    expect(got).toEqual(
      cases.map((c) => ({
        name: c.name,
        hasSavedAt: false,
        comparisonId: 'id' in c.comparison ? ROW_ID : null,
        products: 2,
      })),
    );
    get.mockResolvedValueOnce({
      data: { success: true, comparison: { id: ROW_ID, full_response: null, created_at: CREATED_AT } },
    });
    await expect(realApi().getComparison(ROW_ID)).rejects.toMatchObject({ response: { status: 404 } });
  });

  it('P-S2 no saved-on line on a live result, without an origin, or on a stored result without a readable saved_at', () => {
    const cases: Record<string, { origin?: 'live' | 'stored'; savedAt?: unknown }> = {
      live: { origin: 'live', savedAt: CREATED_AT },
      noOrigin: { savedAt: CREATED_AT },
      storedWithout: { origin: 'stored' },
      storedUnreadable: { origin: 'stored', savedAt: 'not-a-date' },
    };
    const got: Record<string, unknown> = {};
    const want: Record<string, unknown> = {};
    for (const [name, opts] of Object.entries(cases)) {
      const r = show(contentProps('en', opts), 'en');
      got[name] = { content: has(r, 'results-content'), savedOn: has(r, 'results-saved-on') };
      want[name] = { content: true, savedOn: false };
      r.unmount();
    }
    expect(got).toEqual(want);
  });
});
