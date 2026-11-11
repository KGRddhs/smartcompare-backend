/**
 * S81-11 GATE ROWS (final round, RULINGS_REBASE_S81_11 RB-S11-2): the four
 * rows that pin behaviours the correctness adversary proved unpinned
 * (S81_11_ADV1_correctness.md m1: O3, O10, O11, O14, O18). Test-only; every
 * row is green at HEAD and was proven RED on a byte copy of the source file
 * carrying the adversary's edit, restored and sha256-compared.
 *
 *  G11-GR1 (O3)  a Link compare answered HTTP 200 success:false with a
 *                top-level INSUFFICIENT_DATA reason renders the per-reason
 *                sentence (friendlyErrorKey(code, response.data.reason)).
 *  G11-GR2 (O10) under field_status price unknown the converted-from-USD
 *                caption is NOT rendered beside the honest line.
 *  G11-GR3 (O11, O18) the dateless stale marker (results.price.checkedEarlier,
 *                testID -checked-) renders ONLY for a LIVE body whose
 *                field_status price state is stale with as_of null; a STORED
 *                body renders the amount with no marker; fresh / unknown
 *                entries never render it.
 *  G11-GR4 (O14) the coming-soon toast announces through
 *                AccessibilityInfo.announceForAccessibility on iOS only; on
 *                Android the toast's accessibilityLiveRegion carries it.
 */

import React from 'react';
import { render, waitFor, act } from '@testing-library/react-native';
import enCatalog from '../../src/i18n/en.json';

const EN = enCatalog as Record<string, string>;

jest.mock('@react-navigation/native', () => {
  const ReactRequired = require('react');
  return {
    useFocusEffect: (cb: any) => {
      ReactRequired.useEffect(() => {
        const cleanup = cb();
        return cleanup;
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
  ImpactFeedbackStyle: { Light: 'Light' },
  NotificationFeedbackType: { Success: 'Success' },
}));

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

const mockHealthCheck = jest.fn();
const mockStreamComparison = jest.fn();
const mockApiPost = jest.fn();
const mockApiGet = jest.fn();
const mockTrackEvent = jest.fn();
const mockGetSavedUser = jest.fn();
const mockGetReferralStatus = jest.fn();

jest.mock('../../src/services/api', () => ({
  __esModule: true,
  default: {
    post: (...args: any[]) => mockApiPost(...args),
    get: (...args: any[]) => mockApiGet(...args),
  },
  healthCheck: (...args: any[]) => mockHealthCheck(...args),
  streamComparison: (...args: any[]) => mockStreamComparison(...args),
  parseApiError: (error: any) => {
    const data = error?.response?.data;
    const rawCode =
      (typeof data?.code === 'string' && data.code) ||
      (typeof data?.detail?.code === 'string' && data.detail.code) ||
      null;
    const out: any = { message: '', code: rawCode };
    const reason =
      (typeof data?.reason === 'string' && data.reason) ||
      (typeof data?.detail?.reason === 'string' && data.detail.reason) ||
      undefined;
    if (reason) out.reason = reason;
    return out;
  },
  trackEvent: (...args: any[]) => mockTrackEvent(...args),
  COMPARE_TIMEOUT_MS: 35000,
  API_BASE_URL: 'https://api.example.test',
}));

jest.mock('../../src/services/authService', () => ({
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
}));

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

const mockSelectorProps: any[] = [];
jest.mock('../../src/components/CategorySelector', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: (props: any) => {
      mockSelectorProps.push(props);
      return ReactRequired.createElement('View', { testID: 'mock-category-selector' });
    },
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

jest.mock('react-i18next', () => {
  const catalog = require('../../src/i18n/en.json') as Record<string, string>;
  const interp = (s: string, opts?: any) => {
    if (!opts || typeof opts !== 'object') return s;
    let out = s;
    for (const [k, v] of Object.entries(opts)) {
      if (k === 'defaultValue' || v === undefined) continue;
      out = out.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
    }
    return out;
  };
  const t = (key: string, opts?: any) => {
    if (opts && typeof opts === 'object' && typeof opts.count === 'number') {
      const form = opts.count === 1 ? `${key}_one` : `${key}_other`;
      if (catalog[form] !== undefined) return interp(catalog[form], opts);
    }
    if (catalog[key] !== undefined) return interp(catalog[key], opts);
    if (opts && typeof opts === 'object' && 'defaultValue' in opts) {
      return interp(opts.defaultValue, opts);
    }
    return key;
  };
  return { useTranslation: () => ({ t, i18n: { language: 'en' } }) };
});

// ResultsContent children that are not under test (the honestUnknowns.s11 set).
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

import HomeScreen from '../../src/screens/HomeScreen';
import { ResultsContent } from '../../src/components/results/ResultsContent';
import { priceProvenance } from '../../src/services/fieldStatusView';
import { formatPrice as formatAmountWithCurrency } from '../../src/utils/formatNumber';

const HOUR = 3600 * 1000;
const DAY = 24 * HOUR;
const NOW = Date.parse('2026-11-05T12:00:00Z');
const HOST = 'store-a.example.com';

const tEn = (key: string, opts?: Record<string, unknown>) => {
  let str = EN[key] ?? key;
  if (opts) {
    for (const [k, v] of Object.entries(opts)) {
      str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
    }
  }
  return str;
};

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

function homeProps() {
  return { navigation: { navigate: jest.fn(), goBack: jest.fn() } };
}

function product(name: string, price: any) {
  return { name, brand: 'Brand A', price, pros: ['Long wear'], cons: ['Pricey'] };
}

function resultsProps(products: any[], metadata: any, extra: Record<string, unknown> = {}) {
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
    comparisonId: 'cmp-s11-gr',
    isRTL: false,
    feedbackSubmitted: false,
    onFeedbackSubmitted: jest.fn(),
    feedbackComparisonId: 'cmp-s11-gr',
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

let alertSpy: jest.SpyInstance;

beforeEach(() => {
  jest.clearAllMocks();
  mockSelectorProps.length = 0;
  mockHealthCheck.mockResolvedValue(true);
  mockGetSavedUser.mockResolvedValue({ id: 'u1', email: 'user-a@example.com' });
  mockGetReferralStatus.mockResolvedValue({
    monthly_bonus_comparisons: 0,
    bonus_referrer_name: null,
    bonus_expires_at: null,
  });
  const RN = require('react-native');
  alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
});

afterEach(() => {
  alertSpy.mockRestore();
});

describe('G11-GR1 (O3) -- Link 200 success:false carries the top-level reason', () => {
  async function urlResolveFalse(data: any) {
    mockApiPost.mockResolvedValueOnce({ data });
    const rendered = render(<HomeScreen {...(homeProps() as any)} />);
    const { fireEvent } = require('@testing-library/react-native');
    fireEvent.press(rendered.getByTestId('home-mode-link'));
    const shell = await waitFor(() => rendered.getByTestId('mock-two-input-shell'));
    await act(async () => {
      shell.props.onSubmit('https://store-a.example.com/p/1', 'https://store-a.example.com/p/2');
    });
    await waitFor(() => expect(alertSpy).toHaveBeenCalled());
    rendered.unmount();
  }

  for (const reason of ['same_identity', 'placeholder_identity', 'category_conflict']) {
    it(`G11-GR1: reason ${reason} -> its own sentence, not the generic one`, async () => {
      await urlResolveFalse({ success: false, code: 'INSUFFICIENT_DATA', reason });
      const key = `home.errors.insufficientDataReason.${reason}`;
      expect(typeof EN[key]).toBe('string');
      expect(EN[key]).not.toBe(EN['home.errors.insufficientData']);
      expect(alertSpy).toHaveBeenCalledTimes(1);
      expect(alertSpy.mock.calls[0][1]).toBe(EN[key]);
    });
  }

  it('G11-GR1 control: no reason / no_evidence -> the generic sentence', async () => {
    for (const data of [
      { success: false, code: 'INSUFFICIENT_DATA' },
      { success: false, code: 'INSUFFICIENT_DATA', reason: 'no_evidence' },
    ]) {
      alertSpy.mockClear();
      await urlResolveFalse(data);
      expect(alertSpy.mock.calls[0][1]).toBe(EN['home.errors.insufficientData']);
    }
  });
});

describe('G11-GR2 / G11-GR3 -- the card price lines', () => {
  let nowSpy: jest.SpyInstance;
  beforeEach(() => {
    nowSpy = jest.spyOn(Date, 'now').mockReturnValue(NOW);
  });
  afterEach(() => {
    nowSpy.mockRestore();
  });

  it('G11-GR2 (O10): field_status price unknown on a converted price -> honest line, NO converted caption', () => {
    const products = [
      product('Fragrance A', { amount: null, currency: 'BHD', source_method: 'converted_usd' }),
      product('Fragrance B', { amount: 30, currency: 'BHD', source_method: 'converted_usd' }),
    ];
    const md = {
      field_status: [{ price: { state: 'unknown', source: null, reason: 'no_price' } }, null],
    };
    const rendered = render(<ResultsContent {...resultsProps(products, md)} />);
    expect(rendered.queryByTestId('results-product-price-honest-0')).not.toBeNull();
    expect(rendered.queryByTestId('results-product-converted-0')).toBeNull();
    // Control: the other card (no field_status entry) keeps its caption.
    expect(rendered.queryByTestId('results-product-converted-1')).not.toBeNull();
  });

  it('G11-GR2 (O10): a live converted price older than 30 days -> honest line, NO caption', () => {
    const products = [
      product('Fragrance A', {
        amount: 20,
        currency: 'BHD',
        source_method: 'converted_usd',
        retailer: HOST,
        as_of: new Date(NOW - 31 * DAY).toISOString(),
      }),
      product('Fragrance B', { amount: 30, currency: 'BHD', source_method: 'page_scrape' }),
    ];
    const md = {
      field_status: [{ price: { state: 'unknown', source: 'converted_usd', reason: 'too_old' } }, null],
    };
    const rendered = render(<ResultsContent {...resultsProps(products, md)} />);
    expect(rendered.queryByTestId('results-product-price-honest-0')).not.toBeNull();
    expect(rendered.queryByTestId('results-product-converted-0')).toBeNull();
  });

  const STALE_NO_DATE = {
    state: 'stale',
    source: 'served_from_cache',
    reason: 'served_from_cache',
    as_of: null,
  };
  const priced = () => [
    product('Fragrance A', { amount: 45, currency: 'BHD', retailer: HOST, source_method: 'page_scrape' }),
    product('Fragrance B', { amount: 30, currency: 'BHD', retailer: HOST, source_method: 'page_scrape' }),
  ];

  it('G11-GR3: a LIVE body with a stale / as_of null entry renders the dateless marker', () => {
    for (const extra of [{}, { resultOrigin: 'live' }]) {
      const rendered = render(
        <ResultsContent {...resultsProps(priced(), { field_status: [{ price: STALE_NO_DATE }, null] }, extra)} />,
      );
      const node = rendered.queryByTestId('results-product-checked-0');
      expect(node).not.toBeNull();
      expect(allText(node?.children ?? []).join('')).toBe(EN['results.price.checkedEarlier']);
      rendered.unmount();
    }
  });

  it('G11-GR3 (O11): a STORED body with the same entry renders the amount and NO marker', () => {
    const rendered = render(
      <ResultsContent
        {...resultsProps(priced(), { field_status: [{ price: STALE_NO_DATE }, null] }, { resultOrigin: 'stored' })}
      />,
    );
    expect(rendered.queryByTestId('results-product-checked-0')).toBeNull();
    expect(rendered.queryByText(formatAmountWithCurrency(45, 'BHD', tEn))).not.toBeNull();
    expect(
      priceProvenance({ amount: 45, currency: 'BHD', retailer: HOST }, STALE_NO_DATE, NOW, 'stored').kind,
    ).toBe('none');
  });

  it('G11-GR3 (O18): a fresh or unknown entry with no date never renders the marker (live)', () => {
    for (const state of ['fresh', 'unknown', 'known']) {
      const entry = { state, source: 'page_scrape', reason: null, as_of: null };
      const rendered = render(
        <ResultsContent {...resultsProps(priced(), { field_status: [{ price: entry }, null] })} />,
      );
      expect(rendered.queryByTestId('results-product-checked-0')).toBeNull();
      expect(rendered.queryByText(formatAmountWithCurrency(45, 'BHD', tEn))).not.toBeNull();
      rendered.unmount();
      expect(
        priceProvenance({ amount: 45, currency: 'BHD', retailer: HOST }, entry, NOW, 'live').kind,
      ).not.toBe('staleNoDate');
    }
  });
});

describe('G11-GR4 (O14) -- the coming-soon announcement is iOS-only', () => {
  async function tapComingSoon(os: 'ios' | 'android') {
    const RN = require('react-native');
    const announce = jest.fn();
    const prevA11y = RN.AccessibilityInfo;
    const prevOS = RN.Platform.OS;
    RN.AccessibilityInfo = { ...(prevA11y || {}), announceForAccessibility: announce };
    RN.Platform.OS = os;
    try {
      const rendered = render(<HomeScreen {...(homeProps() as any)} />);
      await waitFor(() => rendered.getByTestId('home-mode-type'));
      const last = mockSelectorProps[mockSelectorProps.length - 1];
      expect(typeof last?.onComingSoon).toBe('function');
      await act(async () => {
        last.onComingSoon('skincare');
      });
      const toastNode = rendered.queryByTestId('home-coming-soon-toast');
      const toast =
        toastNode === null
          ? null
          : { liveRegion: toastNode.props.accessibilityLiveRegion as unknown };
      const expected = tEn('home.categories.comingSoonToast', {
        category: EN['home.categories.skincare'],
      });
      rendered.unmount();
      return { announce, toast, expected };
    } finally {
      RN.AccessibilityInfo = prevA11y;
      RN.Platform.OS = prevOS;
    }
  }

  it('G11-GR4: iOS -> announceForAccessibility(the toast text) once', async () => {
    const { announce, toast, expected } = await tapComingSoon('ios');
    expect(toast).not.toBeNull();
    expect(announce).toHaveBeenCalledTimes(1);
    expect(announce).toHaveBeenCalledWith(expected);
  });

  it('G11-GR4: Android -> NO announce call; the toast carries accessibilityLiveRegion polite', async () => {
    const { announce, toast } = await tapComingSoon('android');
    expect(toast).not.toBeNull();
    expect(toast?.liveRegion).toBe('polite');
    expect(announce).not.toHaveBeenCalled();
  });
});
