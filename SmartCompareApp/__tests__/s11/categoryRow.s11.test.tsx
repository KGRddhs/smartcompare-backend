/**
 * S81-11 RED -- the category row re-cut and the send gate (spec 2.3 / 2.5,
 * C6 / C7 / C11; rulings R-S11-2, R-S11-3, R-S11-23, R-S11-27, R-S11-34).
 *
 * HomeScreen renders the REAL CategorySelector; the launch store is the
 * REAL src/services/launchSurfaces (loaded optionally: at base it does not
 * exist, and every row that needs it asserts its presence first). The
 * network surface of services/api is mocked with recorders (streamComparison
 * options, the url/compare body, trackEvent) and global fetch is a recorder
 * (a compare must issue ZERO /app/version requests, R-S11-19).
 */

import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react-native';
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

const mockHealthCheck = jest.fn();
const mockStreamComparison = jest.fn();
const mockApiPost = jest.fn();
const mockTrackEvent = jest.fn();
const mockGetSavedUser = jest.fn();
const mockGetReferralStatus = jest.fn();

jest.mock('../../src/services/api', () => ({
  __esModule: true,
  default: {
    post: (...args: any[]) => mockApiPost(...args),
  },
  healthCheck: (...args: any[]) => mockHealthCheck(...args),
  streamComparison: (...args: any[]) => mockStreamComparison(...args),
  parseApiError: (error: any) => {
    const data = error?.response?.data;
    const code = (typeof data?.code === 'string' && data.code) || null;
    return { message: '', code };
  },
  trackEvent: (...args: any[]) => mockTrackEvent(...args),
  COMPARE_TIMEOUT_MS: 35000,
  API_BASE_URL: 'https://api.example.test',
}));

jest.mock('../../src/services/authService', () => ({
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
}));

jest.mock('../../src/services/usageService', () => ({
  isUsageLimitError: () => false,
  getUsageLimitDetail: () => null,
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

const mockEditorialProps: any[] = [];
jest.mock('../../src/components/HomeEditorialSections', () => {
  const ReactRequired = require('react');
  const actual = jest.requireActual('../../src/components/HomeEditorialSections');
  return {
    __esModule: true,
    ...actual,
    default: (props: any) => {
      mockEditorialProps.push(props);
      return ReactRequired.createElement('View', { testID: 'mock-home-editorial-sections' });
    },
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
      if (k === 'defaultValue') continue;
      out = out.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
    }
    return out;
  };
  const t = (key: string, opts?: any) => {
    if (catalog[key] !== undefined) return interp(catalog[key], opts);
    if (opts && typeof opts === 'object' && 'defaultValue' in opts) {
      return interp(opts.defaultValue, opts);
    }
    return key;
  };
  return { useTranslation: () => ({ t, i18n: { language: 'en' } }) };
});

import HomeScreen from '../../src/screens/HomeScreen';

function loadOptional(rel: string): any {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    return require(rel);
  } catch {
    return null;
  }
}

function launch(): any {
  return loadOptional('../../src/services/launchSurfaces');
}

const ALL_CHIPS = [
  'electronics',
  'grocery',
  'supplements',
  'makeup',
  'skincare',
  'haircare',
  'fragrances',
  'fashion',
  'other',
];

const mockFetch = jest.fn();

function makeProps() {
  return { navigation: { navigate: jest.fn(), goBack: jest.fn() } };
}

function chipIds(rendered: any): string[] {
  return ALL_CHIPS.filter((c) => rendered.queryByTestId(`category-chip-${c}`) !== null);
}

async function submitText(rendered: any) {
  mockStreamComparison.mockReturnValue({ subscribe: jest.fn(), abort: jest.fn() });
  fireEvent.press(rendered.getByTestId('home-mode-type'));
  const shell = await waitFor(() => rendered.getByTestId('mock-two-input-shell'));
  await act(async () => {
    shell.props.onSubmit('Dior Sauvage EDP', 'Bleu de Chanel EDP');
  });
}

async function submitUrl(rendered: any) {
  mockApiPost.mockResolvedValue({ data: { success: false, code: 'INSUFFICIENT_DATA' } });
  const RN = require('react-native');
  const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
  fireEvent.press(rendered.getByTestId('home-mode-link'));
  const shell = await waitFor(() => rendered.getByTestId('mock-two-input-shell'));
  await act(async () => {
    shell.props.onSubmit('https://store-a.example.com/p/1', 'https://store-a.example.com/p/2');
  });
  await waitFor(() => expect(mockApiPost).toHaveBeenCalled());
  alertSpy.mockRestore();
}

/** The full version body: the five base keys plus the two new keys. */
function versionBody(extra: Record<string, unknown>) {
  return {
    min_version: '1.0.0',
    latest_version: '1.0.0',
    force_update: false,
    update_url_ios: '',
    update_url_android: '',
    ...extra,
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  mockEditorialProps.length = 0;
  (global as any).fetch = mockFetch;
  mockFetch.mockReset();
  mockHealthCheck.mockResolvedValue(true);
  mockGetSavedUser.mockResolvedValue({ id: 'u1', email: 'user-a@example.com' });
  mockGetReferralStatus.mockResolvedValue({
    monthly_bonus_comparisons: 0,
    bonus_referrer_name: null,
    bonus_expires_at: null,
  });
  launch()?.__resetLaunchSurfaces?.();
});

afterEach(() => {
  jest.useRealTimers();
});

describe('S81-11 B1 -- ABSENT surfaces: one Fragrances chip + the fragrance-only line', () => {
  it('renders exactly category-chip-fragrances and home-fragrance-only-line; no nudge', async () => {
    const rendered = render(<HomeScreen {...(makeProps() as any)} />);
    await waitFor(() => rendered.getByTestId('home-mode-type'));
    expect(chipIds(rendered)).toEqual(['fragrances']);
    const line = rendered.queryByTestId('home-fragrance-only-line');
    expect(line).not.toBeNull();
    expect(line?.props.children).toBe(EN['home.categories.fragrancesOnly'] ?? '<missing key>');
    expect(rendered.queryByTestId('home-category-nudge')).toBeNull();
  });

  it('the line stays when the Fragrances chip is selected (both row states)', async () => {
    const rendered = render(<HomeScreen {...(makeProps() as any)} />);
    await waitFor(() => rendered.getByTestId('home-mode-type'));
    expect(rendered.queryByTestId('category-chip-fragrances')).not.toBeNull();
    fireEvent.press(rendered.getByTestId('category-chip-fragrances'));
    expect(rendered.queryByTestId('home-fragrance-only-line')).not.toBeNull();
    expect(rendered.queryByTestId('home-category-nudge')).toBeNull();
  });
});

describe('S81-11 B2 / B3 / B4 -- coming-soon chips only under surfaces', () => {
  it('B2: surfaces {skincare, makeup} -> chips fragrances, skincare, makeup in order, both badged', async () => {
    const m = launch();
    expect(m).not.toBeNull();
    m?.recordLaunchSurfaces?.(versionBody({ surfaces: { skincare: true, makeup: true } }));
    const rendered = render(<HomeScreen {...(makeProps() as any)} />);
    await waitFor(() => rendered.getByTestId('home-mode-type'));
    const order = rendered
      .UNSAFE_root.findAll((n: any) =>
        typeof n.props?.testID === 'string' && /^category-chip-[a-z]+$/.test(n.props.testID),
      )
      .map((n: any) => n.props.testID)
      .filter((id: string, i: number, arr: string[]) => arr.indexOf(id) === i);
    expect(order).toEqual([
      'category-chip-fragrances',
      'category-chip-skincare',
      'category-chip-makeup',
    ]);
    expect(rendered.queryByTestId('category-chip-skincare-soon')).not.toBeNull();
    expect(rendered.queryByTestId('category-chip-makeup-soon')).not.toBeNull();
    expect(rendered.queryByTestId('category-chip-fragrances-soon')).toBeNull();
    const soon = rendered.getByTestId('category-chip-skincare');
    expect(soon.props.accessibilityState).toEqual(
      expect.objectContaining({ disabled: false, selected: false }),
    );
    expect(String(soon.props.accessibilityHint ?? '')).not.toBe('');
  });

  it('B3: a coming-soon tap -> the toast (+ iOS announcement), no event, no navigate, no compare', async () => {
    const m = launch();
    expect(m).not.toBeNull();
    m?.recordLaunchSurfaces?.(versionBody({ surfaces: { skincare: true } }));
    const RN = require('react-native');
    const announce = jest.fn();
    const prevA11y = RN.AccessibilityInfo;
    const prevOS = RN.Platform.OS;
    RN.AccessibilityInfo = { ...(prevA11y || {}), announceForAccessibility: announce };
    RN.Platform.OS = 'ios';
    const props = makeProps();
    const rendered = render(<HomeScreen {...(props as any)} />);
    await waitFor(() => rendered.getByTestId('home-mode-type'));
    expect(rendered.queryByTestId('category-chip-skincare')).not.toBeNull();
    // The user's Fragrances pick must survive a coming-soon tap.
    fireEvent.press(rendered.getByTestId('category-chip-fragrances'));
    expect(rendered.getByTestId('category-chip-fragrances').props.accessibilityState).toEqual(
      expect.objectContaining({ selected: true }),
    );
    jest.useFakeTimers();
    fireEvent.press(rendered.getByTestId('category-chip-skincare'));
    expect(rendered.getByTestId('category-chip-fragrances').props.accessibilityState).toEqual(
      expect.objectContaining({ selected: true }),
    );
    const toast = rendered.queryByTestId('home-coming-soon-toast');
    expect(toast).not.toBeNull();
    const expected = (EN['home.categories.comingSoonToast'] ?? '<missing>').replace(
      '{{category}}',
      EN['home.categories.skincare'],
    );
    expect(toast?.props.children).toBe(expected);
    expect(announce).toHaveBeenCalledWith(expected);
    expect(
      mockTrackEvent.mock.calls.filter((c) => c[0] === 'category_coming_soon_tap'),
    ).toHaveLength(0);
    expect(props.navigation.navigate).not.toHaveBeenCalled();
    expect(mockStreamComparison).not.toHaveBeenCalled();
    // The tap never selects the inert chip.
    expect(rendered.getByTestId('category-chip-skincare').props.accessibilityState).toEqual(
      expect.objectContaining({ selected: false }),
    );
    await act(async () => {
      jest.advanceTimersByTime(2600);
    });
    expect(rendered.queryByTestId('home-coming-soon-toast')).toBeNull();
    RN.AccessibilityInfo = prevA11y;
    RN.Platform.OS = prevOS;
  });

  it('B4: invalid surfaces render no soon chip and a fragrance tap queues no coming-soon event', async () => {
    const m = launch();
    expect(m).not.toBeNull();
    m?.recordLaunchSurfaces?.(
      versionBody({ surfaces: { skincare: 'true', makeup: 1, fashion: true } }),
    );
    const rendered = render(<HomeScreen {...(makeProps() as any)} />);
    await waitFor(() => rendered.getByTestId('home-mode-type'));
    expect(chipIds(rendered)).toEqual(['fragrances']);
    expect(rendered.queryByTestId('home-coming-soon-toast')).toBeNull();
    fireEvent.press(rendered.getByTestId('category-chip-fragrances'));
    expect(
      mockTrackEvent.mock.calls.filter((c) => c[0] === 'category_coming_soon_tap'),
    ).toHaveLength(0);
  });
});

describe('S81-11 B5 -- QUICK_CATS is the one fragrances tile', () => {
  it('QuickCategories renders exactly home-quick-cat-fragrances', () => {
    const { QuickCategories } = jest.requireActual(
      '../../src/components/HomeEditorialSections',
    );
    const onPick = jest.fn();
    const rendered = render(<QuickCategories onPickCategory={onPick} />);
    const ids = rendered.UNSAFE_root.findAll(
      (n: any) => typeof n.props?.testID === 'string' && n.props.testID.startsWith('home-quick-cat-'),
    )
      .map((n: any) => n.props.testID)
      .filter((id: string, i: number, arr: string[]) => arr.indexOf(id) === i);
    expect(ids).toEqual(['home-quick-cat-fragrances']);
    fireEvent.press(rendered.getByTestId('home-quick-cat-fragrances'));
    expect(onPick).toHaveBeenCalledWith('fragrances');
  });
});

describe('S81-11 B6 / B7 / B8 -- selected_category gated on categories_live (R-S11-3)', () => {
  it('B6: chip selected + ABSENT version body -> no selected_category on text or link', async () => {
    const rendered = render(<HomeScreen {...(makeProps() as any)} />);
    await waitFor(() => rendered.getByTestId('home-mode-type'));
    fireEvent.press(rendered.getByTestId('category-chip-fragrances'));
    await submitText(rendered);
    expect(mockStreamComparison).toHaveBeenCalledTimes(1);
    expect(mockStreamComparison.mock.calls[0][1]).toEqual({});
    const r2 = render(<HomeScreen {...(makeProps() as any)} />);
    await waitFor(() => r2.getByTestId('home-mode-link'));
    fireEvent.press(r2.getByTestId('category-chip-fragrances'));
    await submitUrl(r2);
    expect(mockApiPost.mock.calls[0][1]).not.toHaveProperty('selected_category');
  });

  it('B7: chip selected + categories_live [fragrances] -> fragrances on text and link', async () => {
    const m = launch();
    expect(m).not.toBeNull();
    m?.recordLaunchSurfaces?.(versionBody({ categories_live: ['fragrances'] }));
    const rendered = render(<HomeScreen {...(makeProps() as any)} />);
    await waitFor(() => rendered.getByTestId('home-mode-type'));
    fireEvent.press(rendered.getByTestId('category-chip-fragrances'));
    await submitText(rendered);
    expect(mockStreamComparison.mock.calls[0][1]).toEqual({ selected_category: 'fragrances' });
    const r2 = render(<HomeScreen {...(makeProps() as any)} />);
    await waitFor(() => r2.getByTestId('home-mode-link'));
    fireEvent.press(r2.getByTestId('category-chip-fragrances'));
    await submitUrl(r2);
    expect(mockApiPost.mock.calls[0][1]).toEqual(
      expect.objectContaining({ selected_category: 'fragrances' }),
    );
    // R-S11-19: a compare reads the store synchronously: zero /app/version requests.
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('B8: chip NOT selected + categories_live [fragrances] -> no selected_category', async () => {
    const m = launch();
    expect(m).not.toBeNull();
    m?.recordLaunchSurfaces?.(versionBody({ categories_live: ['fragrances'] }));
    const rendered = render(<HomeScreen {...(makeProps() as any)} />);
    await waitFor(() => rendered.getByTestId('home-mode-type'));
    await submitText(rendered);
    expect(mockStreamComparison.mock.calls[0][1]).toEqual({});
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('B8b: a QUICK_CATS pick sets the chip but still sends only through the gate', async () => {
    const rendered = render(<HomeScreen {...(makeProps() as any)} />);
    await waitFor(() => rendered.getByTestId('home-mode-type'));
    const last = mockEditorialProps[mockEditorialProps.length - 1];
    expect(typeof last?.onPickCategory).toBe('function');
    await act(async () => {
      last.onPickCategory('fragrances');
    });
    const shell = await waitFor(() => rendered.getByTestId('mock-two-input-shell'));
    mockStreamComparison.mockReturnValue({ subscribe: jest.fn(), abort: jest.fn() });
    await act(async () => {
      shell.props.onSubmit('Dior Sauvage EDP', 'Bleu de Chanel EDP');
    });
    expect(mockStreamComparison.mock.calls[0][1]).toEqual({});
  });
});
