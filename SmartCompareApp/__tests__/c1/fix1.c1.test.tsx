/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * INC-C1 fix round 1 (relay ruling ORCH-C1-B) -- rows E1 and E2 with their
 * pins, RED first in this new file; the frozen c1 files stay as they are.
 *
 * The contract this file fixes:
 *  - E1 (adversary 2, A2-1): the dated price caption ("<store>, last checked
 *    ...", testIDs results-product-asof-<i> and results-product-lastseen-<i>)
 *    may wrap: numberOfLines 2 on that Text only, EN and AR, with and without
 *    a store. Its text (so its word order), its style and its other props
 *    stay as today. Pin: the listed line (results-product-listed-<i>) and
 *    every other caption of the price block keep today's value (checked 1,
 *    per-ml 1, converted 1, the honest line 2, the different-sizes line
 *    unset), and the caption style is today's.
 *  - E2 (adversary 1, F3): Home's unmount cleanup aborts an in-flight link
 *    compare without bumping the compare run, so its CanceledError reaches
 *    the link catch. There it ends with NO alert: error.name CanceledError or
 *    error.code ERR_CANCELED, each on its own (the cancel services/api
 *    runRestCompare drops). The same holds for a cancel that reaches the catch
 *    while Home is still mounted, and the catch still drops the loader
 *    (nothing else in the catch changes). Pin: while Home is mounted a real
 *    refusal keeps today's alert (the link title with Cancel and Type the
 *    names; TIMEOUT's two arguments), and the Cancel button stays silent.
 *
 * Harness: one module registry. ResultsContent as lastChecked.c1 renders it
 * (child components mocked, the real i18next over the real catalogs, Date.now
 * spied to NOW, every as_of built from local date parts). HomeScreen with the
 * cameraLink.c1 mocks (one services/api mock whose parseApiError is the a11
 * copy plus the reason read; useFocusEffect as a runner per subscriber); its t
 * is the same real i18next, set to EN. Every row renders one tree at a time
 * and presses only inside the latest render (RNTL 13.3.3 drops an event on an
 * element outside it). F1: existing exports and paths only, no new symbol, no
 * new mocked path; every base failure is an expect assertion. ASCII source.
 */

import React from 'react';
import { render, fireEvent, act, waitFor } from '@testing-library/react-native';
import enCatalog from '../../src/i18n/en.json';
import arCatalog from '../../src/i18n/ar.json';

import HomeScreen from '../../src/screens/HomeScreen';
import { ResultsContent } from '../../src/components/results/ResultsContent';
import { formatAsOfDate } from '../../src/services/fieldStatusView';
import { colors } from '../../src/theme';

const EN = enCatalog as unknown as Record<string, string>;
const AR = arCatalog as unknown as Record<string, string>;

let mockLang: 'en' | 'ar' = 'en';
const mockFocus = new Set<() => void>();

// ------------------------------------------------- the lastChecked.c1 mocks --

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

// The real i18next over the real catalogs (referralExpiryPlurals.w414 setup),
// for ResultsContent and HomeScreen alike.
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

// --------------------------------------------------- the cameraLink.c1 mocks --

// A focus runner per useFocusEffect subscriber: run on mount, run again by a
// focus event, dropped (with its cleanup) on unmount.
jest.mock('@react-navigation/native', () => {
  const ReactRequired = require('react');
  return {
    useFocusEffect: (cb: any) => {
      const latest = ReactRequired.useRef(cb);
      latest.current = cb;
      ReactRequired.useEffect(() => {
        let cleanup: any = latest.current();
        const runner = () => {
          if (typeof cleanup === 'function') cleanup();
          cleanup = latest.current();
        };
        mockFocus.add(runner);
        return () => {
          mockFocus.delete(runner);
          if (typeof cleanup === 'function') cleanup();
        };
      }, []);
    },
  };
});

jest.mock('expo-camera', () => {
  const ReactRequired = require('react');
  return {
    CameraView: () => ReactRequired.createElement('CameraView'),
    useCameraPermissions: () => [{ granted: true }, jest.fn()],
  };
});

jest.mock('expo-image-picker', () => ({
  launchImageLibraryAsync: jest.fn().mockResolvedValue({ canceled: true }),
  MediaTypeOptions: { Images: 'Images' },
}));

jest.mock('expo-haptics', () => ({
  impactAsync: jest.fn().mockResolvedValue(undefined),
  notificationAsync: jest.fn().mockResolvedValue(undefined),
  ImpactFeedbackStyle: { Light: 'Light', Medium: 'Medium' },
  NotificationFeedbackType: { Success: 'Success' },
}));

const mockHealthCheck = jest.fn();
const mockStreamComparison = jest.fn();
const mockApiPost = jest.fn();
const mockTrackEvent = jest.fn();
const mockGetSavedUser = jest.fn();
const mockGetReferralStatus = jest.fn();
const mockGetComparison = jest.fn();
const mockIdentifyFromImages = jest.fn();

jest.mock('../../src/services/api', () => ({
  __esModule: true,
  default: {
    post: (...args: any[]) => mockApiPost(...args),
  },
  healthCheck: (...args: any[]) => mockHealthCheck(...args),
  streamComparison: (...args: any[]) => mockStreamComparison(...args),
  trackEvent: (...args: any[]) => mockTrackEvent(...args),
  trackEvents: jest.fn().mockResolvedValue(undefined),
  submitFeedback: jest.fn().mockResolvedValue(undefined),
  getComparison: (...args: any[]) => mockGetComparison(...args),
  identifyFromImages: (...args: any[]) => mockIdentifyFromImages(...args),
  COMPARE_TIMEOUT_MS: 35000,
  // The a11 copy of parseApiError plus api.ts's additive `reason` read
  // (top level first, then under detail, string only).
  parseApiError: (error: any) => {
    const base = (() => {
      const data = error?.response?.data;
      const status = error?.response?.status;
      const rawCode =
        (typeof data?.code === 'string' && data.code) ||
        (typeof data?.detail?.code === 'string' && data.detail.code) ||
        null;
      if (rawCode === 'TIMEOUT' || rawCode === 'STREAM_TIMEOUT' || (status === 503 && !rawCode)) {
        return { message: '', code: 'TIMEOUT' };
      }
      const code = rawCode ?? (status === 502 || status === 504 ? 'GATEWAY_UNAVAILABLE' : null);
      if (data?.error) return { message: data.error, code };
      if (data?.detail) {
        return {
          message: typeof data.detail === 'string' ? data.detail : 'Invalid request',
          code,
        };
      }
      if (error?.message) return { message: error.message, code };
      return { message: 'Something went wrong', code };
    })();
    const d = error?.response?.data;
    const reason =
      (typeof d?.reason === 'string' && d.reason) ||
      (typeof d?.detail?.reason === 'string' && d.detail.reason) ||
      undefined;
    return reason ? { ...base, reason } : base;
  },
}));

jest.mock('../../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));

jest.mock('../../src/services/authService', () => ({
  getToken: jest.fn().mockResolvedValue('fake-jwt'),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
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
  useLanguage: () => ({
    isRTL: false,
    language: 'en',
    setLanguage: jest.fn(),
  }),
}));

jest.mock('../../src/lib/performance/wallTimeInstrumentation', () => ({
  getWallTimeTracker: () => ({
    start: jest.fn(),
    mark: jest.fn(),
    report: jest.fn(),
    reset: jest.fn(),
  }),
}));

// usageService keyed on code USAGE_LIMIT (both server shapes, as the module).
jest.mock('../../src/services/usageService', () => {
  const payload = (error: any) => {
    const data = error?.response?.data;
    if (!data) return null;
    if (data?.detail?.code === 'USAGE_LIMIT') return data.detail;
    if (data?.code === 'USAGE_LIMIT') return data;
    return null;
  };
  return {
    isUsageLimitError: (error: any) => payload(error) !== null,
    getUsageLimitDetail: (error: any) => payload(error),
  };
});

jest.mock('../../src/services/referralService', () => ({
  getReferralStatus: (...args: any[]) => mockGetReferralStatus(...args),
}));

jest.mock('../../src/hooks/useComparisonCounter', () => ({
  useComparisonCounter: () => ({
    used: 1,
    total: 3,
    canCompare: true,
    increment: jest.fn().mockResolvedValue(undefined),
  }),
}));

jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn().mockResolvedValue(null),
  setItem: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('../../src/components/CategorySelector', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () => ReactRequired.createElement('View', { testID: 'mock-category-selector' }),
  };
});

jest.mock('../../src/components/QarenLogo', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () => ReactRequired.createElement('View', { testID: 'mock-qaren-logo' }),
  };
});

jest.mock('../../src/components/TwoInputShell', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: (props: any) =>
      ReactRequired.createElement('View', { testID: 'mock-two-input-shell', ...props }),
  };
});

jest.mock('../../src/components/PaywallBanner', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () => ReactRequired.createElement('View', { testID: 'mock-paywall-banner' }),
  };
});

jest.mock('../../src/components/HomeEditorialSections', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () =>
      ReactRequired.createElement('View', { testID: 'mock-home-editorial-sections' }),
  };
});

jest.mock('../../src/screens/LoadingScreenVariants', () => {
  const ReactRequired = require('react');
  return {
    LoadingScreenVariants: (props: any) =>
      ReactRequired.createElement('View', { ...props, testID: 'mock-loading-screen-variants' }),
  };
});

jest.mock('../../src/icons', () => ({
  ScanIcon: () => null,
  LinkIcon: () => null,
  TypeIcon: () => null,
}));

const I18N = (require('react-i18next') as any).__inst;

// ------------------------------------------------------------------ helpers --

const LANGS = ['en', 'ar'] as const;
/** Rows loop over many renders; bound each one well above jest's 5 s default. */
const E1_MS = 30000;
const E2_MS = 60000;

const cat = (lang: 'en' | 'ar') => (lang === 'ar' ? AR : EN);
const fill = (tpl: string, vars: Record<string, string>) =>
  Object.entries(vars).reduce((s, [k, v]) => s.split(`{{${k}}}`).join(v), tpl);

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

/** A converted price at noon.com (the converted caption shows under it). */
const converted = (x: Record<string, unknown> = {}) => ({
  amount: 7.14,
  currency: 'BHD',
  source_method: 'converted_usd',
  retailer: STORE,
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

/** Renders one ResultsContent body in one language. */
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
  return { r };
}

/** The props a dated or listed caption carries today. */
const CAPTION_PROPS = ['children', 'numberOfLines', 'style', 'testID'];

/**
 * One caption as it renders: its text, its numberOfLines ('absent' when the
 * prop is not set), its style ('caption' when it is the caption style object
 * read off today's converted caption) and its prop names.
 */
function caption(r: any, id: string, captionStyle: unknown) {
  const node = r.queryByTestId(id);
  if (!node) return { id, missing: true };
  const props = node.props as Record<string, unknown>;
  return {
    id,
    text: allText(node.children).join(''),
    numberOfLines: Object.prototype.hasOwnProperty.call(props, 'numberOfLines')
      ? props.numberOfLines
      : 'absent',
    style: props.style === captionStyle ? 'caption' : props.style,
    props: Object.keys(props).sort(),
  };
}

/** The caption style object, read off today's converted caption (X1: one label). */
function captionStyleRef(): unknown {
  const { r } = show(pair(converted()), {}, 'en');
  const node = r.queryByTestId('results-product-converted-0');
  const style = node ? node.props.style : 'no converted caption';
  r.unmount();
  return style;
}

/** The plural form i18next picks for n >= 2 days: EN other; AR two / few / many (CLDR). */
function dayForm(lang: 'en' | 'ar', n: number): string {
  if (lang === 'en') return 'other';
  const m = n % 100;
  if (n === 2) return 'two';
  if (m >= 3 && m <= 10) return 'few';
  if (m >= 11) return 'many';
  return 'other';
}

/** Today's dated line from the catalog (row S1 pins the catalog to the spec table). */
function lastChecked(lang: 'en' | 'ar', store: string | null, n: number): string {
  const c = cat(lang);
  const ns = store ? '' : 'NoStore';
  const key =
    n === 0
      ? `results.price.checkedToday${ns}`
      : n === 1
        ? `results.price.checkedYesterday${ns}`
        : `results.price.checkedDaysAgo${ns}_${dayForm(lang, n)}`;
  const tpl = c[key];
  if (typeof tpl !== 'string') return `missing ${key}`;
  return fill(tpl, store ? { store, days: String(n) } : { days: String(n) });
}

// ------------------------------------------------------------------ E1 --

describe('INC-C1 fix 1, E1: the dated caption wraps to two lines (ResultsContent, real i18next)', () => {
  let nowSpy: jest.SpyInstance;
  beforeEach(() => {
    mockLang = 'en';
    nowSpy = jest.spyOn(Date, 'now').mockReturnValue(NOW);
  });
  afterEach(() => {
    nowSpy.mockRestore();
    mockLang = 'en';
  });

  it('E1 results-product-asof-<i> and -lastseen-<i> take numberOfLines 2, EN and AR, with and without a store; text, word order, style and props as today', () => {
    const ref = captionStyleRef();
    const got: unknown[] = [];
    const want: unknown[] = [];
    for (const lang of LANGS) {
      for (const store of [STORE, null]) {
        // 0-3 days: fresh (asof); 10 and 29 days: stale (lastseen).
        for (const n of [0, 1, 2, 3, 10, 29]) {
          const { r } = show(pair(price(n, store ? {} : { retailer: undefined })), {}, lang);
          const id = `results-product-${n <= 7 ? 'asof' : 'lastseen'}-0`;
          got.push({ lang, store, n, ...caption(r, id, ref) });
          want.push({
            lang,
            store,
            n,
            id,
            text: lastChecked(lang, store, n),
            numberOfLines: 2,
            style: 'caption',
            props: CAPTION_PROPS,
          });
          r.unmount();
        }
      }
      // Both cards dated: card 0 a converted price checked today (its
      // converted caption under it), card 1 a genuine price checked 10 days ago.
      const both = show(pair(converted({ as_of: asOf(0) }), other({ as_of: asOf(10) })), {}, lang);
      for (const [id, host, days] of [
        ['results-product-asof-0', STORE, 0],
        ['results-product-lastseen-1', STORE_B, 10],
      ] as const) {
        got.push({ lang, card: 'both', ...caption(both.r, id, ref) });
        want.push({
          lang,
          card: 'both',
          id,
          text: lastChecked(lang, host, days),
          numberOfLines: 2,
          style: 'caption',
          props: CAPTION_PROPS,
        });
      }
      both.r.unmount();
    }
    expect(got).toEqual(want);
  }, E1_MS);

  it('E1 pin: the caption style is today\'s, and every other caption keeps its numberOfLines (listed 1, checked 1, per-ml 1, converted 1, the honest line 2, the different-sizes line unset)', () => {
    const ref = captionStyleRef();
    expect(ref).toEqual({
      fontSize: 11,
      color: colors.text.secondary,
      lineHeight: 11 * 1.4,
      marginTop: 2,
    });
    const line = (
      id: string,
      text: unknown,
      numberOfLines: unknown,
      style: unknown = 'caption',
      props: string[] = CAPTION_PROPS,
    ) => ({ id, text, numberOfLines, style, props });
    const got: unknown[] = [];
    const want: unknown[] = [];
    for (const lang of LANGS) {
      const c = cat(lang);

      // A stored body, both cards dated: the listed lines, with a store.
      const st = show(pair(price(2), other({ as_of: asOf(10) })), {}, lang, { resultOrigin: 'stored' });
      got.push({ lang, ...caption(st.r, 'results-product-listed-0', ref) });
      want.push({
        lang,
        ...line(
          'results-product-listed-0',
          fill(c['results.price.listedOn'], { store: STORE, date: formatAsOfDate(asOf(2), lang) }),
          1,
        ),
      });
      got.push({ lang, ...caption(st.r, 'results-product-listed-1', ref) });
      want.push({
        lang,
        ...line(
          'results-product-listed-1',
          fill(c['results.price.listedOn'], { store: STORE_B, date: formatAsOfDate(asOf(10), lang) }),
          1,
        ),
      });
      st.r.unmount();

      // A stored body without a store: the listed line, no store.
      const sn = show(pair(price(2, { retailer: undefined })), {}, lang, { resultOrigin: 'stored' });
      got.push({ lang, ...caption(sn.r, 'results-product-listed-0', ref) });
      want.push({
        lang,
        ...line(
          'results-product-listed-0',
          fill(c['results.price.listedOnNoStore'], { date: formatAsOfDate(asOf(2), lang) }),
          1,
        ),
      });
      sn.r.unmount();

      // A live stale price without a date: the checked line.
      const ck = show(pair(price(null)), { field_status: [{ price: { state: 'stale', as_of: null } }, null] }, lang);
      got.push({ lang, ...caption(ck.r, 'results-product-checked-0', ref) });
      want.push({ lang, ...line('results-product-checked-0', c['results.price.checkedEarlier'], 1) });
      ck.r.unmount();

      // A converted price with a bottle size and a per-ml figure: the per-ml
      // and the converted captions.
      const cv = show(pair(converted({ size_ml: 100, per_ml: 0.0714 })), {}, lang);
      got.push({ lang, ...caption(cv.r, 'results-product-perml-0', ref) });
      want.push({ lang, ...line('results-product-perml-0', expect.any(String), 1) });
      got.push({ lang, ...caption(cv.r, 'results-product-converted-0', ref) });
      want.push({ lang, ...line('results-product-converted-0', c['results.convertedUSD'], 1) });
      cv.r.unmount();

      // 31 days: the honest line (its own price style) keeps 2.
      const hn = show(pair(price(31)), {}, lang);
      got.push({ lang, ...caption(hn.r, 'results-product-price-honest-0', ref) });
      want.push({
        lang,
        ...line('results-product-price-honest-0', c['results.honest.notListed'], 2, expect.anything()),
      });
      hn.r.unmount();

      // Two bottle sizes: the different-sizes line sets no numberOfLines.
      const ds = show(
        pair(price(null, { size_ml: 100 }), other({ size_ml: 50 })),
        { pair_price_sizes: { mode: 'different_sizes' } },
        lang,
      );
      got.push({ lang, ...caption(ds.r, 'results-price-different-sizes', ref) });
      want.push({
        lang,
        ...line(
          'results-price-different-sizes',
          c['results.price.differentSizes'],
          'absent',
          'caption',
          ['children', 'style', 'testID'],
        ),
      });
      ds.r.unmount();
    }
    expect(got).toEqual(want);
  }, E1_MS);
});

// ------------------------------------------------------------------ E2 --

/** An axios rejection exactly as the interceptor hands it to the screen. */
function axiosError(status: number, data: any): any {
  const err: any = new Error(`Request failed with status code ${status}`);
  err.isAxiosError = true;
  err.response = { status, data };
  return err;
}

/** The cancel axios 1.x rejects with when a request's signal aborts, and each half of it alone. */
const CANCELS: [string, () => Error][] = [
  [
    'axios CanceledError (name and code)',
    () =>
      Object.assign(new Error('canceled'), {
        name: 'CanceledError',
        code: 'ERR_CANCELED',
        __CANCEL__: true,
      }),
  ],
  ['name CanceledError only', () => Object.assign(new Error('canceled'), { name: 'CanceledError' })],
  ['code ERR_CANCELED only', () => Object.assign(new Error('canceled'), { code: 'ERR_CANCELED' })],
];

/**
 * The link POST stays in flight until its abort signal fires, then rejects
 * with reason(), as axios does for a request whose signal aborts.
 */
function postUntilAborted(reason: () => Error): { signal: any } {
  const seen: { signal: any } = { signal: null };
  mockApiPost.mockImplementation((_url: string, _body: unknown, config: any) => {
    seen.signal = config?.signal ?? null;
    return new Promise<never>((_resolve, reject) => {
      if (seen.signal && typeof seen.signal.addEventListener === 'function') {
        seen.signal.addEventListener('abort', () => reject(reason()), { once: true });
      }
    });
  });
  return seen;
}

const makeHomeNavigation = () => ({ navigate: jest.fn(), goBack: jest.fn() });

/** Lets every pending promise and timer of a compare run out (real timers). */
async function settle() {
  for (let i = 0; i < 3; i += 1) {
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
  }
}

function resetCommon() {
  jest.clearAllMocks();
  mockLang = 'en';
  mockApiPost.mockReset();
  mockIdentifyFromImages.mockReset();
  mockHealthCheck.mockResolvedValue(true);
  mockGetSavedUser.mockResolvedValue({ id: 'u1', email: 'k@example.com' });
  mockGetReferralStatus.mockResolvedValue({
    monthly_bonus_comparisons: 0,
    bonus_referrer_name: null,
    bonus_expires_at: null,
  });
}

describe('INC-C1 fix 1, E2: a cancelled link compare raises no alert (HomeScreen, real timers)', () => {
  let alertSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.useRealTimers();
    resetCommon();
    I18N.changeLanguage('en');
    const RN = require('react-native');
    alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => undefined);
  });
  afterEach(() => {
    alertSpy.mockRestore();
    mockLang = 'en';
  });

  async function submitUrlCompare(rendered: any) {
    fireEvent.press(rendered.getByTestId('home-mode-link'));
    const shell = await waitFor(() => rendered.getByTestId('mock-two-input-shell'));
    await act(async () => {
      shell.props.onSubmit('https://noon.com/a', 'https://store-b.example.com/b');
    });
  }

  const alertsOf = (spy: jest.SpyInstance) => spy.mock.calls.map((c: any[]) => c.slice(0, 2));

  it('E2 a link compare in flight when Home unmounts, rejected with a CanceledError or ERR_CANCELED (each alone too), raises no alert; so does a cancel that reaches the catch while Home is mounted, and the loader still drops', async () => {
    // Harness check (passes at base): Home's t is the real i18next, in EN.
    expect(I18N.language).toBe('en');

    // Harness control (passes at base and after the fix): the same in-flight
    // compare, failed after the unmount by an error that is NOT a cancel,
    // still reaches the catch's alert within the same settle(). So an empty
    // alert list below means the cancel was filtered, not that the catch
    // never ran; and the unmount itself still bumps no compare run.
    {
      alertSpy.mockClear();
      mockApiPost.mockReset();
      const seen = postUntilAborted(() =>
        Object.assign(new Error('socket closed'), { name: 'AxiosError', code: 'ECONNRESET' }),
      );
      const rendered = render(<HomeScreen navigation={makeHomeNavigation() as any} />);
      await submitUrlCompare(rendered);
      expect({ control: 'in flight', aborted: seen.signal?.aborted }).toEqual({
        control: 'in flight',
        aborted: false,
      });
      rendered.unmount();
      expect({ control: 'unmounted', aborted: seen.signal?.aborted }).toEqual({
        control: 'unmounted',
        aborted: true,
      });
      await settle();
      expect({ control: 'alerts', count: alertSpy.mock.calls.length }).toEqual({
        control: 'alerts',
        count: 1,
      });
    }

    const got: unknown[] = [];
    const want: unknown[] = [];
    for (const [label, cancel] of CANCELS) {
      alertSpy.mockClear();
      mockApiPost.mockReset();
      const seen = postUntilAborted(cancel);
      const navigation = makeHomeNavigation();
      const rendered = render(<HomeScreen navigation={navigation as any} />);
      await submitUrlCompare(rendered);
      // Harness (passes at base): the link POST is in flight under the loader,
      // with an abort signal.
      expect(mockApiPost).toHaveBeenCalledTimes(1);
      expect(mockApiPost.mock.calls[0][0]).toBe('/api/v1/url/compare');
      expect({ label, aborted: seen.signal?.aborted }).toEqual({ label, aborted: false });
      expect(rendered.queryByTestId('home-loading-cancel')).not.toBeNull();
      rendered.unmount();
      // Harness: Home's unmount cleanup aborted it (the F3 trigger).
      expect({ label, aborted: seen.signal?.aborted }).toEqual({ label, aborted: true });
      await settle();
      got.push({ label, alerts: alertsOf(alertSpy), navigate: navigation.navigate.mock.calls });
      want.push({ label, alerts: [], navigate: [] });
    }

    // The same filter for a cancel that reaches the catch while Home is still
    // mounted (the run current): no alert, and the catch still drops the
    // loader, as for every other failure.
    alertSpy.mockClear();
    mockApiPost.mockReset();
    mockApiPost.mockRejectedValueOnce(CANCELS[0][1]());
    const mountedNav = makeHomeNavigation();
    const mounted = render(<HomeScreen navigation={mountedNav as any} />);
    await submitUrlCompare(mounted);
    await settle();
    expect(mockApiPost).toHaveBeenCalledTimes(1);
    got.push({
      label: 'a cancel while Home is mounted',
      alerts: alertsOf(alertSpy),
      navigate: mountedNav.navigate.mock.calls,
      loader: mounted.queryByTestId('home-loading-cancel') !== null,
    });
    want.push({ label: 'a cancel while Home is mounted', alerts: [], navigate: [], loader: false });
    mounted.unmount();

    expect(got).toEqual(want);
  }, E2_MS);

  it('E2 pin: while Home is mounted a real refusal keeps today\'s alert (the link title with Cancel and Type the names; TIMEOUT two arguments), and the Cancel button stays silent', async () => {
    expect(I18N.language).toBe('en');
    const title = EN['home.errors.link.title'];
    const generic = EN['home.errors.link.generic'];
    const buttons = [
      { text: EN['common.cancel'], style: 'cancel' },
      { text: EN['common.typeNames'], onPress: expect.any(Function) },
    ];
    const cases: [string, () => void, unknown[]][] = [
      [
        'thrown 400 STORE_UNREADABLE',
        () =>
          mockApiPost.mockRejectedValueOnce(
            axiosError(400, { success: false, code: 'STORE_UNREADABLE', error: 'prose', request_id: 'r' }),
          ),
        [title, EN['home.errors.link.storeUnreadable'], buttons],
      ],
      [
        '200 success:false UNRESOLVED_PRODUCT',
        () =>
          mockApiPost.mockResolvedValueOnce({
            data: { success: false, code: 'UNRESOLVED_PRODUCT', error: 'prose' },
          }),
        [title, EN['home.errors.link.unresolved'], buttons],
      ],
      [
        'thrown 400 codeless (an edge page)',
        () => mockApiPost.mockRejectedValueOnce(axiosError(400, '<html>x</html>')),
        [title, generic, buttons],
      ],
      [
        'an AxiosError ERR_BAD_REQUEST carrying BAD_REQUEST (a code that is not ERR_CANCELED)',
        () =>
          mockApiPost.mockRejectedValueOnce(
            Object.assign(
              axiosError(400, { success: false, code: 'BAD_REQUEST', error: 'prose', request_id: 'r' }),
              { name: 'AxiosError', code: 'ERR_BAD_REQUEST' },
            ),
          ),
        [title, generic, buttons],
      ],
      [
        'an AxiosError ECONNRESET with no response (a transport failure, not a cancel)',
        () =>
          mockApiPost.mockRejectedValueOnce(
            Object.assign(new Error('socket closed'), { name: 'AxiosError', code: 'ECONNRESET' }),
          ),
        [title, generic, buttons],
      ],
      [
        'thrown 503 TIMEOUT',
        () =>
          mockApiPost.mockRejectedValueOnce(
            axiosError(503, { success: false, error: 'x', code: 'TIMEOUT', request_id: 'r' }),
          ),
        [EN['common.error'], EN['home.errors.timeout']],
      ],
    ];
    for (const [label, arrange, args] of cases) {
      expect({
        label,
        strings: args.slice(0, 2).every((x) => typeof x === 'string' && x.length > 0),
      }).toEqual({ label, strings: true });
      alertSpy.mockClear();
      mockApiPost.mockReset();
      arrange();
      const rendered = render(<HomeScreen navigation={makeHomeNavigation() as any} />);
      await submitUrlCompare(rendered);
      await waitFor(() => expect(alertSpy).toHaveBeenCalled());
      expect({ label, calls: alertSpy.mock.calls }).toEqual({ label, calls: [args] });
      rendered.unmount();
    }

    // The Cancel button (A4): the run is dropped at the guard before the
    // catch's cleanup; no alert, and the loader is gone.
    alertSpy.mockClear();
    mockApiPost.mockReset();
    const cancelSeen = postUntilAborted(CANCELS[0][1]);
    const cancelRender = render(<HomeScreen navigation={makeHomeNavigation() as any} />);
    await submitUrlCompare(cancelRender);
    expect(cancelRender.queryByTestId('home-loading-cancel')).not.toBeNull();
    fireEvent.press(cancelRender.getByTestId('home-loading-cancel'));
    expect(cancelSeen.signal?.aborted).toBe(true);
    await settle();
    expect({
      alerts: alertsOf(alertSpy),
      loader: cancelRender.queryByTestId('home-loading-cancel') !== null,
    }).toEqual({ alerts: [], loader: false });
    cancelRender.unmount();
  }, E2_MS);
});
