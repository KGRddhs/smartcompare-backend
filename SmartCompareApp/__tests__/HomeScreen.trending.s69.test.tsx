/**
 * S69 U6 T5 — a trending tap starts THAT comparison; no invented counts (RT-7).
 *
 * Spec R5 + review corrections 18-19 and open question E:
 *   - HomeScreen.tsx:1010-1012 ignored the tapped query and only switched to
 *     type mode. The editorial callback becomes `onPressTrending(a, b, tag?)`
 *     carrying the names the row already derives (HomeEditorialSections.tsx:
 *     363-376 — pre-split a/b, else a case-insensitive " vs " split of
 *     `query`), and HomeScreen prefills both inputs and runs the same
 *     `handleTextCompare(a, b)` the shell's Compare button runs (so the
 *     canCompare -> Paywall gate still applies).
 *   - The hand-written `count` / `view_count` (data/trending_curated.json) is
 *     no longer rendered.
 *   - The section title reads "Popular comparisons" / «مقارنات شائعة» in the
 *     real catalogs (key choice left to the green: reuse home.trending.title
 *     with new text or add a new key — both satisfy this).
 *
 * Harness: HomeScreen.bundleE.s3.integration.test.tsx (boundary mocks,
 * mocked TwoInputShell + HomeEditorialSections); the real TrendingNearYou is
 * reached through jest.requireActual. The i18n mock resolves keys against
 * the REAL en.json / ar.json so copy is asserted as a user would read it.
 */

import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react-native';

jest.mock('@react-navigation/native', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
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
  // eslint-disable-next-line @typescript-eslint/no-require-imports
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

const mockStreamComparison = jest.fn();
const mockGetHomeTrending = jest.fn();

jest.mock('../src/services/api', () => ({
  __esModule: true,
  default: { post: jest.fn(), get: jest.fn() },
  healthCheck: jest.fn().mockResolvedValue(true),
  streamComparison: (...args: any[]) => mockStreamComparison(...args),
  parseApiError: (e: any) => ({ message: e?.message || 'error', code: undefined }),
  trackEvent: jest.fn(),
  COMPARE_TIMEOUT_MS: 35000,
  getHomeTrending: (...args: any[]) => mockGetHomeTrending(...args),
  getHomeSmartPick: jest.fn().mockResolvedValue({ smart_pick: null, empty_state: true }),
  getHomeQuickCategories: jest.fn().mockResolvedValue({ categories: [] }),
  getHomeSavings: jest.fn().mockResolvedValue({ savings: null }),
}));

jest.mock('../src/services/authService', () => ({
  getSavedUser: jest.fn().mockResolvedValue({ id: 'u1', email: 'k@example.com' }),
}));

jest.mock('../src/services/usageService', () => ({
  isUsageLimitError: () => false,
  getUsageLimitDetail: () => null,
}));

jest.mock('../src/services/referralService', () => ({
  getReferralStatus: jest.fn().mockResolvedValue({ monthly_bonus_comparisons: 0 }),
}));

// The editorial sections only render while canCompare is true
// (HomeScreen.tsx:992), so the Paywall gate is covered by the shared
// handleTextCompare path rather than by a tap here.
jest.mock('../src/hooks/useComparisonCounter', () => ({
  useComparisonCounter: () => ({
    used: 1,
    total: 3,
    canCompare: true,
    increment: jest.fn(),
  }),
}));

jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn().mockResolvedValue(null),
  setItem: jest.fn().mockResolvedValue(undefined),
}));

jest.mock('../src/components/CategorySelector', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () => ReactRequired.createElement('View', { testID: 'mock-category-selector' }),
  };
});

jest.mock('../src/components/QarenLogo', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () => ReactRequired.createElement('View', { testID: 'mock-qaren-logo' }),
  };
});

jest.mock('../src/components/TwoInputShell', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: (props: any) =>
      ReactRequired.createElement('View', { testID: 'mock-two-input-shell', ...props }),
  };
});

jest.mock('../src/components/PaywallBanner', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () => ReactRequired.createElement('View', { testID: 'mock-paywall-banner' }),
  };
});

jest.mock('../src/components/HomeEditorialSections', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: ({ onPickCategory, onPressTrending, onPressVerdict }: any) =>
      ReactRequired.createElement('View', {
        testID: 'mock-home-editorial-sections',
        onPickCategory,
        onPressTrending,
        onPressVerdict,
      }),
  };
});

jest.mock('../src/icons', () => ({
  ScanIcon: () => null,
  LinkIcon: () => null,
  TypeIcon: () => null,
}));

let mockLang: 'en' | 'ar' = 'en';
jest.mock('react-i18next', () => {
   
  const catalogs: Record<string, Record<string, string>> = {
    en: require('../src/i18n/en.json'),
    ar: require('../src/i18n/ar.json'),
  };
   
  const t = (key: string, opts?: any) => {
    const cat = catalogs[mockLang];
    const fallback = typeof opts === 'string' ? opts : opts?.defaultValue;
    let str: string = cat[key] ?? fallback ?? key;
    if (opts && typeof opts === 'object') {
      for (const [k, v] of Object.entries(opts)) {
        if (k === 'defaultValue') continue;
        str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
      }
    }
    return str;
  };
  return { useTranslation: () => ({ t, i18n: { language: mockLang } }) };
});

// eslint-disable-next-line @typescript-eslint/no-require-imports
const HomeScreen = require('../src/screens/HomeScreen').default;

const { TrendingNearYou } = jest.requireActual('../src/components/HomeEditorialSections');

const TRENDING = {
  region: 'bahrain',
  trending: [
    { tag: 'Electronics', a: 'iPhone 15', b: 'Galaxy S24', count: 1247, query: 'iPhone 15 vs Galaxy S24' },
    { tag: 'Fragrances', a: '', b: '', count: 983, view_count: 983, query: 'Dior Sauvage VS Bleu de Chanel' },
  ],
};

/** Every string rendered anywhere in the tree. */
function allText(screen: any): string[] {
  const out: string[] = [];
  const walk = (node: any) => {
    if (node == null) return;
    if (typeof node === 'string' || typeof node === 'number') {
      out.push(String(node));
      return;
    }
    if (Array.isArray(node)) {
      node.forEach(walk);
      return;
    }
    walk(node.children);
  };
  walk(screen.toJSON());
  return out;
}

beforeEach(() => {
  jest.clearAllMocks();
  mockLang = 'en';
  mockGetHomeTrending.mockResolvedValue(TRENDING);
  mockStreamComparison.mockReturnValue({ subscribe: jest.fn(), abort: jest.fn() });
});

describe('S69 U6 T5 \u2014 TrendingNearYou', () => {
  it('T5.1 tapping a card reports the pair (a, b), not the composed query string', async () => {
    const onPressTrending = jest.fn();
    const screen = render(<TrendingNearYou onPressTrending={onPressTrending} />);
    const items = await screen.findAllByTestId('home-trending-item');

    fireEvent.press(items[0]);
    expect(onPressTrending).toHaveBeenCalledTimes(1);
    expect(onPressTrending.mock.calls[0][0]).toBe('iPhone 15');
    expect(onPressTrending.mock.calls[0][1]).toBe('Galaxy S24');
  });

  it('T5.2 a legacy query-only row is split on " vs " case-insensitively and trimmed', async () => {
    const onPressTrending = jest.fn();
    const screen = render(<TrendingNearYou onPressTrending={onPressTrending} />);
    const items = await screen.findAllByTestId('home-trending-item');

    fireEvent.press(items[1]);
    expect(onPressTrending.mock.calls[0][0]).toBe('Dior Sauvage');
    expect(onPressTrending.mock.calls[0][1]).toBe('Bleu de Chanel');
  });

  it('T5.3 no view count is rendered', async () => {
    const screen = render(<TrendingNearYou onPressTrending={jest.fn()} />);
    await screen.findAllByTestId('home-trending-item');

    const texts = allText(screen);
    expect(texts.join(' ')).not.toMatch(/1,?247|983/);
    // No bare number anywhere in the section.
    expect(texts.filter((s) => /^\s*[\d,.\u0660-\u0669]+\s*$/.test(s))).toEqual([]);
  });

  it('T5.4 the section title is "Popular comparisons" (EN) and \u00ab\u0645\u0642\u0627\u0631\u0646\u0627\u062a \u0634\u0627\u0626\u0639\u0629\u00bb (AR), not "Trending in"', async () => {
    const enScreen = render(<TrendingNearYou onPressTrending={jest.fn()} />);
    await enScreen.findAllByTestId('home-trending-item');
    expect(enScreen.getByText('Popular comparisons')).toBeTruthy();
    expect(allText(enScreen).join(' ')).not.toMatch(/Trending in/);
    enScreen.unmount();

    mockLang = 'ar';
    const arScreen = render(<TrendingNearYou onPressTrending={jest.fn()} />);
    await arScreen.findAllByTestId('home-trending-item');
    expect(arScreen.getByText('\u0645\u0642\u0627\u0631\u0646\u0627\u062a \u0634\u0627\u0626\u0639\u0629')).toBeTruthy();
  });
});

describe('S69 U6 T5 \u2014 HomeScreen runs the tapped comparison', () => {
  function renderHome() {
    const navigation = { navigate: jest.fn(), goBack: jest.fn() };
    const screen = render(<HomeScreen navigation={navigation as any} />);
    return { navigation, screen };
  }

  it('T5.5 a trending tap prefills both inputs and starts the compare with (a, b) through the Compare path', async () => {
    const { screen } = renderHome();
    const editorial = screen.getByTestId('mock-home-editorial-sections');

    editorial.props.onPressTrending('iPhone 15', 'Galaxy S24', 'Electronics');

    await waitFor(() =>
      expect(mockStreamComparison).toHaveBeenCalledWith(
        { product_a: 'iPhone 15', product_b: 'Galaxy S24' },
        expect.any(Object),
      ),
    );
    const shell = screen.getByTestId('mock-two-input-shell');
    expect(shell.props.initialA).toBe('iPhone 15');
    expect(shell.props.initialB).toBe('Galaxy S24');
  });
});
