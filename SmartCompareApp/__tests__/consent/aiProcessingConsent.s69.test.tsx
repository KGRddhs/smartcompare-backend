/**
 * S69 U3 T1 — one-time AI-processing consent before any byte leaves the
 * device (App Review guideline 5.1.2(i)).
 *
 * Spec: docs/investigations/2026-09-29-session-69-state/U3_AI_CONSENT_SPEC.md
 * R1 (the sheet), R2 (camera / photo-picker pre-sheet), R3 (as ruled by the
 * spec review: client-only persistence), R5 is T2. R4 (the Profile toggle,
 * D3) is OUT OF SCOPE, so the sheet must not mention any opt-out.
 *
 * Contract pinned here (what the green must provide):
 *   - src/services/aiConsent.ts exporting AI_CONSENT_VERSION.
 *   - AsyncStorage key `@qaren_ai_consent_<userId>` (userId from
 *     getSavedUser()), value JSON `{version: AI_CONSENT_VERSION, at: <ISO>}`.
 *     A null userId shows the sheet, dispatches only after Agree, and
 *     persists nothing.
 *   - The sheet renders testID `ai-consent-sheet` with the buttons
 *     `ai-consent-agree`, `ai-consent-not-now` and the Privacy link
 *     `ai-consent-privacy-link` (closes the sheet, drops the pending action,
 *     then navigates to Legal { doc: 'privacy' }).
 *   - Copy keys aiConsent.{title, body, link, agree, notNow} in en.json AND
 *     ar.json; `aiConsent.body` names MYEZ / ميّز and joins BRAND_KEYS in
 *     __tests__/i18n/brand.myez.s69.test.ts.
 *
 * Dispatch-point map (spec review): the gate sits
 *   - in handleTextCompare AFTER the !canCompare -> Paywall check and BEFORE
 *     saveRecentSearch / setLoading / trackEvent / streamComparison
 *     (covers the Type-mode Compare button and a Popular-comparisons tap);
 *   - in handleUrlCompare AFTER the !canCompare check and BEFORE trackEvent /
 *     api.post('/api/v1/url/compare');
 *   - before navigate('ScanCamera') (the scan CTA and both preview rows),
 *     before requestPermission() (the permission pad — R2) and before
 *     ImagePicker.launchImageLibraryAsync (the gallery fallback — R2).
 *   The camera identify request is made by Results from `vision_products`,
 *   reachable only through those Home entries, so gating them gates it.
 *
 * Modal harness: the shared react-native mock unmounts a Modal whose
 * `visible` is false and never calls `onDismiss`. The spec review (point 11)
 * lets the green run the pending action from `onDismiss` (iOS presentation
 * clash), so this file wraps Modal to fire `onDismiss` on a visible
 * true -> false transition, the way iOS does. A green that dispatches
 * directly is unaffected.
 *
 * aiConsent module: the review recommends a global "granted" jest.mock in
 * __tests__/setup.ts. This file maps the module back to the real
 * implementation with a plain per-file factory override of the global grant in
 * setup.ts (at base the module did not exist yet, hence the red).
 */

import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// This suite exercises the REAL gate: the factory below overrides the global
// grant registered in __tests__/setup.ts for THIS file's module registry only.
// Never pass `{ virtual: true }` here: the module exists, and a virtual mock of
// an existing path leaks the real module into every later test file in the
// same jest worker (reproduced 2026-09-29 with --runInBand: 23 Home tests red).
jest.mock('../../src/services/aiConsent', () => jest.requireActual('../../src/services/aiConsent'));

jest.mock('react-native', () => {
  const RN = jest.requireActual('react-native');
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const ReactRequired = require('react');
  const Modal = (props: any) => {
    const wasVisible = ReactRequired.useRef(props.visible !== false);
    ReactRequired.useEffect(() => {
      const nowVisible = props.visible !== false;
      if (wasVisible.current && !nowVisible && typeof props.onDismiss === 'function') {
        props.onDismiss();
      }
      wasVisible.current = nowVisible;
    }, [props.visible]);
    if (props.visible === false) return null;
    return ReactRequired.createElement('Modal', props, props.children);
  };
  return { ...RN, Modal };
});

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

let mockPermission: { granted: boolean } = { granted: true };
const mockRequestPermission = jest.fn();
jest.mock('expo-camera', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const ReactRequired = require('react');
  return {
    CameraView: () => ReactRequired.createElement('CameraView'),
    useCameraPermissions: () => [mockPermission, mockRequestPermission],
  };
});

const mockLaunchImageLibrary = jest.fn();
jest.mock('expo-image-picker', () => ({
  launchImageLibraryAsync: (...args: any[]) => mockLaunchImageLibrary(...args),
  MediaTypeOptions: { Images: 'Images' },
}));

jest.mock('expo-haptics', () => ({
  impactAsync: jest.fn().mockResolvedValue(undefined),
  notificationAsync: jest.fn().mockResolvedValue(undefined),
  ImpactFeedbackStyle: { Light: 'Light' },
  NotificationFeedbackType: { Success: 'Success' },
}));

const mockStreamComparison = jest.fn();
const mockApiPost = jest.fn();
const mockTrackEvent = jest.fn();
const mockIdentifyFromImages = jest.fn();

jest.mock('../../src/services/api', () => ({
  __esModule: true,
  default: { post: (...args: any[]) => mockApiPost(...args), get: jest.fn() },
  healthCheck: jest.fn().mockResolvedValue(true),
  streamComparison: (...args: any[]) => mockStreamComparison(...args),
  identifyFromImages: (...args: any[]) => mockIdentifyFromImages(...args),
  parseApiError: (e: any) => ({ message: e?.message || 'error', code: undefined }),
  trackEvent: (...args: any[]) => mockTrackEvent(...args),
  COMPARE_TIMEOUT_MS: 35000,
  getHomeTrending: jest.fn().mockResolvedValue({ region: 'bahrain', trending: [] }),
  getHomeSmartPick: jest.fn().mockResolvedValue({ smart_pick: null, empty_state: true }),
  getHomeQuickCategories: jest.fn().mockResolvedValue({ categories: [] }),
  getHomeSavings: jest.fn().mockResolvedValue({ savings: null }),
}));

const mockGetSavedUser = jest.fn();
jest.mock('../../src/services/authService', () => ({
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
}));

jest.mock('../../src/services/usageService', () => ({
  isUsageLimitError: () => false,
  getUsageLimitDetail: () => null,
}));

jest.mock('../../src/services/referralService', () => ({
  getReferralStatus: jest.fn().mockResolvedValue({ monthly_bonus_comparisons: 0 }),
}));

jest.mock('../../src/hooks/useComparisonCounter', () => ({
  useComparisonCounter: () => ({
    used: 1,
    total: 3,
    canCompare: true,
    increment: jest.fn().mockResolvedValue(2),
  }),
}));

jest.mock('../../src/components/CategorySelector', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () => ReactRequired.createElement('View', { testID: 'mock-category-selector' }),
  };
});

jest.mock('../../src/components/QarenLogo', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () => ReactRequired.createElement('View', { testID: 'mock-qaren-logo' }),
  };
});

jest.mock('../../src/components/TwoInputShell', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: (props: any) =>
      ReactRequired.createElement('View', { testID: 'mock-two-input-shell', ...props }),
  };
});

jest.mock('../../src/components/PaywallBanner', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () => ReactRequired.createElement('View', { testID: 'mock-paywall-banner' }),
  };
});

jest.mock('../../src/components/HomeEditorialSections', () => {
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

jest.mock('../../src/icons', () => ({
  ScanIcon: () => null,
  LinkIcon: () => null,
  TypeIcon: () => null,
}));

let mockLang: 'en' | 'ar' = 'en';
jest.mock('react-i18next', () => {
  const catalogs: Record<string, Record<string, string>> = {
    en: require('../../src/i18n/en.json'),
    ar: require('../../src/i18n/ar.json'),
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
const HomeScreen = require('../../src/screens/HomeScreen').default;
const EN: Record<string, string> = require('../../src/i18n/en.json');
const AR: Record<string, string> = require('../../src/i18n/ar.json');

const USER_ID = 'u1';
const CONSENT_KEY = `@qaren_ai_consent_${USER_ID}`;
const CONSENT_PREFIX = '@qaren_ai_consent_';
const STORE: Record<string, string> = (AsyncStorage as any)._store;
// HomeScreen.tsx RECENT_SEARCHES_KEY — the key saveRecentSearch() writes.
// Item 5 / adversary mutant M8: "nothing before consent" includes this local
// write, so moving saveRecentSearch in front of withAiConsent must redden.
// T1.2 is the positive control (the key IS written once the user agrees).
const RECENT_SEARCHES_KEY = '@qaren_recent_searches';

/** The real module (red at base: the file does not exist yet). */
function consentVersion(): unknown {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const mod = require('../../src/services/aiConsent');
  return mod.AI_CONSENT_VERSION;
}

function olderVersionThan(current: unknown): unknown {
  return typeof current === 'number' ? current - 1 : '0';
}

async function flush(times = 4) {
  for (let i = 0; i < times; i += 1) {
    await act(async () => {
      await new Promise((r) => setTimeout(r, 0));
    });
  }
}

function makeNavigation() {
  const navigation: any = { navigate: jest.fn(), goBack: jest.fn() };
  navigation.getParent = () => navigation;
  return navigation;
}

async function renderHome() {
  const navigation = makeNavigation();
  const screen = render(<HomeScreen navigation={navigation} />);
  await flush();
  return { navigation, screen };
}

const sheet = (screen: any) => screen.queryByTestId('ai-consent-sheet');

/** Every string rendered under a node. */
function textUnder(node: any): string {
  const out: string[] = [];
  const walk = (n: any) => {
    if (n == null) return;
    if (typeof n === 'string' || typeof n === 'number') {
      out.push(String(n));
      return;
    }
    if (Array.isArray(n)) {
      n.forEach(walk);
      return;
    }
    walk(n.children);
  };
  walk(node);
  return out.join(' ');
}

async function switchMode(screen: any, testID: 'home-mode-type' | 'home-mode-link') {
  fireEvent.press(screen.getByTestId(testID));
  await flush(1);
}

async function submitText(screen: any, a = 'iPhone 15', b = 'Galaxy S24') {
  await switchMode(screen, 'home-mode-type');
  const shell = screen.getByTestId('mock-two-input-shell');
  await act(async () => {
    shell.props.onSubmit(a, b);
  });
  await flush();
}

async function submitLink(
  screen: any,
  a = 'https://example.com/a',
  b = 'https://example.com/b',
) {
  await switchMode(screen, 'home-mode-link');
  const shell = screen.getByTestId('mock-two-input-shell');
  await act(async () => {
    shell.props.onSubmit(a, b);
  });
  await flush();
}

async function press(screen: any, testID: string) {
  await act(async () => {
    fireEvent.press(screen.getByTestId(testID));
  });
  await flush();
}

const submitEvents = () =>
  mockTrackEvent.mock.calls.filter(([name]) => name === 'compare_entry_submit');

// Only the URL and body are exposed: the third argument carries an AbortSignal,
// which jest's diff printer cannot serialise.
const urlComparePosts = () =>
  mockApiPost.mock.calls
    .filter(([url]) => url === '/api/v1/url/compare')
    .map(([url, body]) => [url, body]);

beforeEach(async () => {
  jest.clearAllMocks();
  await (AsyncStorage as any).clear();
  mockLang = 'en';
  mockPermission = { granted: true };
  mockGetSavedUser.mockResolvedValue({ id: USER_ID, email: 'k@example.com' });
  mockStreamComparison.mockReturnValue({ subscribe: jest.fn(), abort: jest.fn() });
  mockApiPost.mockResolvedValue({ data: { success: false, code: 'TIMEOUT' } });
  mockLaunchImageLibrary.mockResolvedValue({ canceled: true });
  mockRequestPermission.mockResolvedValue({ granted: true });
});

// ---------------------------------------------------------------------------
// Text compare (Type mode) — the first compare without consent
// ---------------------------------------------------------------------------

describe('S69 U3 T1 — text compare is gated by the AI consent sheet', () => {
  it('T1.1 the first compare shows the sheet and does NOT call the compare API, the loader or the submit event', async () => {
    const { screen } = await renderHome();
    await submitText(screen);

    expect(mockStreamComparison).not.toHaveBeenCalled();
    expect(submitEvents()).toEqual([]);
    expect(screen.queryByTestId('home-loading-screen')).toBeNull();
    expect(sheet(screen)).not.toBeNull();
    // Nothing before consent — not even the local recent-search write.
    expect(STORE[RECENT_SEARCHES_KEY]).toBeUndefined();
  });

  it('T1.2 "Agree" persists {version: AI_CONSENT_VERSION, at: ISO} under @qaren_ai_consent_<userId> and dispatches the pending compare', async () => {
    const { screen } = await renderHome();
    await submitText(screen);
    expect(mockStreamComparison).not.toHaveBeenCalled();

    await press(screen, 'ai-consent-agree');

    await waitFor(() =>
      expect(mockStreamComparison).toHaveBeenCalledWith(
        { product_a: 'iPhone 15', product_b: 'Galaxy S24' },
        expect.any(Object),
      ),
    );
    expect(mockStreamComparison).toHaveBeenCalledTimes(1);
    expect(sheet(screen)).toBeNull();
    // Positive control for the recent-search assertions in T1.1 / T1.4.
    expect(JSON.parse(STORE[RECENT_SEARCHES_KEY] ?? 'null')).toEqual(['iPhone 15 vs Galaxy S24']);

    const raw = STORE[CONSENT_KEY];
    expect(typeof raw).toBe('string');
    const stored = JSON.parse(raw);
    expect(stored.version).toEqual(consentVersion());
    expect(typeof stored.at).toBe('string');
    expect(Number.isNaN(Date.parse(stored.at))).toBe(false);
    expect(new Date(stored.at).toISOString()).toBe(stored.at);
  });

  it('T1.3 after "Agree" the next compare dispatches without the sheet', async () => {
    const { screen } = await renderHome();
    await submitText(screen);
    expect(mockStreamComparison).not.toHaveBeenCalled();
    expect(sheet(screen)).not.toBeNull();
    await press(screen, 'ai-consent-agree');
    await waitFor(() => expect(mockStreamComparison).toHaveBeenCalledTimes(1));

    await act(async () => {
      screen.getByTestId('mock-two-input-shell').props.onSubmit('Pixel 9', 'iPhone 16');
    });
    await flush();

    expect(sheet(screen)).toBeNull();
    expect(mockStreamComparison).toHaveBeenCalledTimes(2);
    expect(mockStreamComparison.mock.calls[1][0]).toEqual({
      product_a: 'Pixel 9',
      product_b: 'iPhone 16',
    });
  });

  it('T1.4 "Not now" dispatches nothing, persists nothing, and the sheet asks again on the next attempt', async () => {
    const { screen } = await renderHome();
    await submitText(screen);
    expect(mockStreamComparison).not.toHaveBeenCalled();

    await press(screen, 'ai-consent-not-now');

    expect(sheet(screen)).toBeNull();
    expect(mockStreamComparison).not.toHaveBeenCalled();
    expect(screen.queryByTestId('home-loading-screen')).toBeNull();
    expect(Object.keys(STORE).filter((k) => k.startsWith(CONSENT_PREFIX))).toEqual([]);
    expect(STORE[RECENT_SEARCHES_KEY]).toBeUndefined();

    await act(async () => {
      screen.getByTestId('mock-two-input-shell').props.onSubmit('iPhone 15', 'Galaxy S24');
    });
    await flush();

    expect(mockStreamComparison).not.toHaveBeenCalled();
    expect(sheet(screen)).not.toBeNull();
    expect(STORE[RECENT_SEARCHES_KEY]).toBeUndefined();
  });

  it('T1.5 a stored consent of the CURRENT version skips the sheet and dispatches at once', async () => {
    STORE[CONSENT_KEY] = JSON.stringify({
      version: consentVersion(),
      at: '2026-09-30T00:00:00.000Z',
    });
    const { screen } = await renderHome();
    await submitText(screen);

    expect(sheet(screen)).toBeNull();
    expect(mockStreamComparison).toHaveBeenCalledTimes(1);
  });

  it('T1.6 a stored consent of an OLDER version asks again and dispatches nothing', async () => {
    let current: unknown;
    try {
      current = consentVersion();
    } catch {
      current = '1';
    }
    STORE[CONSENT_KEY] = JSON.stringify({
      version: olderVersionThan(current),
      at: '2026-01-01T00:00:00.000Z',
    });
    const { screen } = await renderHome();
    await submitText(screen);

    expect(mockStreamComparison).not.toHaveBeenCalled();
    expect(sheet(screen)).not.toBeNull();
  });

  it('T1.7 consent is per account: another user\'s stored consent does not cover this user', async () => {
    STORE[`${CONSENT_PREFIX}someone-else`] = JSON.stringify({
      version: '1',
      at: '2026-09-30T00:00:00.000Z',
    });
    const { screen } = await renderHome();
    await submitText(screen);

    expect(mockStreamComparison).not.toHaveBeenCalled();
    expect(sheet(screen)).not.toBeNull();
  });

  it('T1.8 with no saved user (userId null) the sheet shows, "Agree" dispatches, and nothing is persisted', async () => {
    mockGetSavedUser.mockResolvedValue(null);
    const { screen } = await renderHome();
    await submitText(screen);

    expect(mockStreamComparison).not.toHaveBeenCalled();
    expect(sheet(screen)).not.toBeNull();

    await press(screen, 'ai-consent-agree');
    await waitFor(() => expect(mockStreamComparison).toHaveBeenCalledTimes(1));
    expect(Object.keys(STORE).filter((k) => k.startsWith(CONSENT_PREFIX))).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Popular comparisons (#269) — runs through handleTextCompare
// ---------------------------------------------------------------------------

describe('S69 U3 T1 — a Popular-comparisons tap is gated', () => {
  it('T1.9 the tap prefills both inputs, shows the sheet and dispatches nothing; "Not now" keeps the prefill', async () => {
    const { screen } = await renderHome();
    await act(async () => {
      screen
        .getByTestId('mock-home-editorial-sections')
        .props.onPressTrending('iPhone 15', 'Galaxy S24', 'Electronics');
    });
    await flush();

    expect(mockStreamComparison).not.toHaveBeenCalled();
    expect(sheet(screen)).not.toBeNull();

    await press(screen, 'ai-consent-not-now');
    expect(mockStreamComparison).not.toHaveBeenCalled();
    const shell = screen.getByTestId('mock-two-input-shell');
    expect(shell.props.initialA).toBe('iPhone 15');
    expect(shell.props.initialB).toBe('Galaxy S24');
  });

  it('T1.10 "Agree" on a trending tap runs THAT pair', async () => {
    const { screen } = await renderHome();
    await act(async () => {
      screen
        .getByTestId('mock-home-editorial-sections')
        .props.onPressTrending('Dior Sauvage', 'Bleu de Chanel', 'Fragrances');
    });
    await flush();
    expect(mockStreamComparison).not.toHaveBeenCalled();

    await press(screen, 'ai-consent-agree');
    await waitFor(() =>
      expect(mockStreamComparison).toHaveBeenCalledWith(
        { product_a: 'Dior Sauvage', product_b: 'Bleu de Chanel' },
        expect.any(Object),
      ),
    );
  });
});

// ---------------------------------------------------------------------------
// Link mode — POST /api/v1/url/compare (spec review correction 1)
// ---------------------------------------------------------------------------

describe('S69 U3 T1 — Link mode is gated', () => {
  it('T1.11 the first link compare shows the sheet and does NOT post /api/v1/url/compare or fire the submit event', async () => {
    const { screen } = await renderHome();
    await submitLink(screen);

    expect(urlComparePosts()).toEqual([]);
    expect(submitEvents()).toEqual([]);
    expect(screen.queryByTestId('home-loading-screen')).toBeNull();
    expect(sheet(screen)).not.toBeNull();
  });

  it('T1.12 "Agree" posts the pending link pair; "Not now" posts nothing', async () => {
    const first = await renderHome();
    await submitLink(first.screen);
    expect(urlComparePosts()).toEqual([]);
    expect(sheet(first.screen)).not.toBeNull();
    await press(first.screen, 'ai-consent-not-now');
    expect(urlComparePosts()).toEqual([]);
    first.screen.unmount();

    const second = await renderHome();
    await submitLink(second.screen, 'https://shop.example/x', 'https://shop.example/y');
    expect(urlComparePosts()).toEqual([]);
    await press(second.screen, 'ai-consent-agree');
    await waitFor(() => expect(urlComparePosts()).toHaveLength(1));
    const [, body] = urlComparePosts()[0];
    expect(body).toEqual(
      expect.objectContaining({ url1: 'https://shop.example/x', url2: 'https://shop.example/y' }),
    );
  });
});

// ---------------------------------------------------------------------------
// Camera / photo picker (R2) — consent precedes the permission prompt and
// every route to the photo identify request
// ---------------------------------------------------------------------------

describe('S69 U3 T1 — camera and photo-picker paths are gated (R2)', () => {
  it('T1.13 permission not granted: "Turn on camera" shows the sheet BEFORE the OS permission request; "Agree" then requests it', async () => {
    mockPermission = { granted: false };
    const { screen } = await renderHome();
    await act(async () => {
      fireEvent.press(screen.getByText(EN['home.permission.cta']));
    });
    await flush();

    expect(mockRequestPermission).not.toHaveBeenCalled();
    expect(sheet(screen)).not.toBeNull();

    await press(screen, 'ai-consent-agree');
    await waitFor(() => expect(mockRequestPermission).toHaveBeenCalledTimes(1));
  });

  it('T1.14 permission not granted: "Not now" on the pad never shows the OS permission prompt', async () => {
    mockPermission = { granted: false };
    const { screen } = await renderHome();
    await act(async () => {
      fireEvent.press(screen.getByText(EN['home.permission.cta']));
    });
    await flush();
    expect(mockRequestPermission).not.toHaveBeenCalled();
    expect(sheet(screen)).not.toBeNull();

    await press(screen, 'ai-consent-not-now');
    expect(mockRequestPermission).not.toHaveBeenCalled();
    expect(sheet(screen)).toBeNull();
  });

  it('T1.15 the gallery fallback shows the sheet BEFORE opening the photo picker; "Agree" opens it and two photos reach Results', async () => {
    mockPermission = { granted: false };
    mockLaunchImageLibrary.mockResolvedValue({
      canceled: false,
      assets: [{ uri: 'file:///a.jpg' }, { uri: 'file:///b.jpg' }],
    });
    const { screen, navigation } = await renderHome();
    await act(async () => {
      fireEvent.press(screen.getByText(EN['home.permission.gallery_link']));
    });
    await flush();

    expect(mockLaunchImageLibrary).not.toHaveBeenCalled();
    expect(navigation.navigate).not.toHaveBeenCalledWith('Results', expect.anything());
    expect(sheet(screen)).not.toBeNull();

    await press(screen, 'ai-consent-agree');
    await waitFor(() => expect(mockLaunchImageLibrary).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(navigation.navigate).toHaveBeenCalledWith('Results', {
        vision_products: ['file:///a.jpg', 'file:///b.jpg'],
      }),
    );
  });

  it('T1.16 permission granted: the "Open camera" CTA shows the sheet instead of navigating to ScanCamera; "Agree" navigates', async () => {
    const { screen, navigation } = await renderHome();
    await press(screen, 'home-compare-cta');

    expect(navigation.navigate).not.toHaveBeenCalledWith('ScanCamera');
    expect(sheet(screen)).not.toBeNull();

    await press(screen, 'ai-consent-agree');
    await waitFor(() => expect(navigation.navigate).toHaveBeenCalledWith('ScanCamera'));
  });

  it('T1.17 permission granted: both scan preview rows are gated; "Not now" never reaches ScanCamera', async () => {
    const { screen, navigation } = await renderHome();
    for (const row of ['home-scan-preview-row-a', 'home-scan-preview-row-b']) {
      await press(screen, row);
      expect(navigation.navigate).not.toHaveBeenCalledWith('ScanCamera');
      expect(sheet(screen)).not.toBeNull();
      await press(screen, 'ai-consent-not-now');
      expect(sheet(screen)).toBeNull();
    }
    expect(navigation.navigate).not.toHaveBeenCalledWith('ScanCamera');
    expect(mockIdentifyFromImages).not.toHaveBeenCalled();
  });

  it('T1.18 consent given on the camera path also covers a later text compare (one consent, every path)', async () => {
    const { screen, navigation } = await renderHome();
    await press(screen, 'home-compare-cta');
    expect(navigation.navigate).not.toHaveBeenCalledWith('ScanCamera');
    await press(screen, 'ai-consent-agree');
    await waitFor(() => expect(navigation.navigate).toHaveBeenCalledWith('ScanCamera'));

    await submitText(screen);
    expect(sheet(screen)).toBeNull();
    expect(mockStreamComparison).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// The sheet itself
// ---------------------------------------------------------------------------

describe('S69 U3 T1 — the sheet names OpenAI and links the Privacy Policy', () => {
  it('T1.19 the rendered sheet names OpenAI and MYEZ in English and OpenAI and ميّز in Arabic', async () => {
    const en = await renderHome();
    await submitText(en.screen);
    expect(mockStreamComparison).not.toHaveBeenCalled();
    const enSheet = sheet(en.screen);
    expect(enSheet).not.toBeNull();
    const enText = textUnder(enSheet);
    expect(enText).toMatch(/OpenAI/);
    expect(enText).toMatch(/\bMYEZ\b/);
    expect(enText).not.toMatch(/Qaren/);
    en.screen.unmount();

    mockLang = 'ar';
    const ar = await renderHome();
    await submitText(ar.screen);
    const arSheet = sheet(ar.screen);
    expect(arSheet).not.toBeNull();
    const arText = textUnder(arSheet);
    expect(arText).toMatch(/OpenAI/);
    expect(arText).toContain('ميّز');
  });

  it('T1.20 the Privacy link closes the sheet, drops the pending compare and opens Legal { doc: "privacy" }', async () => {
    const { screen, navigation } = await renderHome();
    await submitText(screen);
    expect(mockStreamComparison).not.toHaveBeenCalled();
    expect(sheet(screen)).not.toBeNull();

    await press(screen, 'ai-consent-privacy-link');

    expect(sheet(screen)).toBeNull();
    expect(navigation.navigate).toHaveBeenCalledWith('Legal', { doc: 'privacy' });
    expect(mockStreamComparison).not.toHaveBeenCalled();
    expect(Object.keys(STORE).filter((k) => k.startsWith(CONSENT_PREFIX))).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// Catalogs: keys, copy policy, brand fence, truthfulness, no opt-out
// ---------------------------------------------------------------------------

describe('S69 U3 T1 — aiConsent.* copy in both catalogs', () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const fs = require('fs');
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const path = require('path');
  const policy = require('../../src/i18n/.copy-policy.json');

  const KEYS = [
    'aiConsent.title',
    'aiConsent.body',
    'aiConsent.link',
    'aiConsent.agree',
    'aiConsent.notNow',
  ];
  const BRAND_AR = 'ميّز'; // ميّز
  const AR_LETTER = '[\\u0600-\\u06FF]';
  const MYEZ_AR_WORD = new RegExp(
    `(?<!${AR_LETTER})[\\u0628\\u0644\\u0648]?${BRAND_AR}(?!${AR_LETTER})`,
    'u',
  );
  const OLD_AR_WORD = new RegExp(
    `(?<!${AR_LETTER})[\\u0628\\u0644\\u0648]?\\u0642\\u0627\\u0631\\u0646(?!${AR_LETTER})`,
    'u',
  );
  const AR_DIACRITICS = /[ً-ْٰ]/;
  const OPT_OUT_EN = /opt[\s-]?out|turn (it )?off|switch (it )?off|toggle|disable|settings|you can stop/i;
  // «إيقاف» (turn off), «إلغاء الاشتراك» (unsubscribe), «الإعدادات» (settings), «تعطيل» (disable)
  const OPT_OUT_AR = /إيقاف|إلغاء|الإعدادات|تعطيل/;

  it('T1.21 every aiConsent key exists, non-empty, in en.json AND ar.json, and the Arabic is not the English', () => {
    for (const k of KEYS) {
      expect({ k, en: typeof EN[k] === 'string' && EN[k].trim().length > 0 }).toEqual({ k, en: true });
      expect({ k, ar: typeof AR[k] === 'string' && AR[k].trim().length > 0 }).toEqual({ k, ar: true });
      expect({ k, same: AR[k] === EN[k] }).toEqual({ k, same: false });
    }
  });

  it('T1.22 the body tells the truth: OpenAI, MYEZ, names/links/photos, preferences, and that name + email are not sent (EN + AR)', () => {
    const enBody = EN['aiConsent.body'] ?? '';
    expect(enBody).toMatch(/OpenAI/);
    expect(enBody).toMatch(/\bMYEZ\b/);
    expect(enBody).toMatch(/product name/i);
    expect(enBody).toMatch(/link/i);
    expect(enBody).toMatch(/photo/i);
    expect(enBody).toMatch(/preference/i);
    expect(enBody).toMatch(/\bname\b/i);
    expect(enBody).toMatch(/\bemail\b/i);
    expect(EN['aiConsent.title'] ?? '').toMatch(/\bAI\b/);

    const arBody = AR['aiConsent.body'] ?? '';
    expect(arBody).toMatch(/OpenAI/);
    expect(MYEZ_AR_WORD.test(arBody)).toBe(true);
    // «تفضيل» — preferences
    expect(arBody).toContain('تفضيل');
    // «الذكاء الاصطناعي» — AI
    expect(AR['aiConsent.title'] ?? '').toContain(
      'الذكاء الاصطناعي',
    );
  });

  it('T1.23 no opt-out is promised anywhere in the sheet copy (the Profile toggle routes nothing, #266)', () => {
    for (const k of KEYS) {
      expect({ k, en: OPT_OUT_EN.test(EN[k] ?? 'MISSING opt-out') }).toEqual({ k, en: false });
      expect({ k, ar: OPT_OUT_AR.test(AR[k] ?? 'إيقاف') }).toEqual({ k, ar: false });
    }
  });

  it('T1.24 copy policy: no scary or banned vocabulary; Arabic has no diacritics except the brand token', () => {
    const missing = KEYS.filter((k) => EN[k] === undefined || AR[k] === undefined);
    expect(missing).toEqual([]);
    for (const k of KEYS) {
      const en = EN[k] ?? '';
      const ar = AR[k] ?? '';
      expect({ k, couldnt: /couldn['’]t/i.test(en) }).toEqual({ k, couldnt: false });
      expect({ k, failed: /\bfailed\b/i.test(en) }).toEqual({ k, failed: false });
      expect({ k, tryAgain: /try again/i.test(en) }).toEqual({ k, tryAgain: false });
      for (const w of policy.scary_vocab_en as string[]) {
        expect({ k, w, hit: en.toLowerCase().includes(w.toLowerCase()) }).toEqual({ k, w, hit: false });
      }
      for (const b of policy.banned_en as { pattern: string }[]) {
        expect({ k, b: b.pattern, hit: new RegExp(b.pattern).test(en) }).toEqual({
          k,
          b: b.pattern,
          hit: false,
        });
      }
      for (const w of policy.scary_vocab_ar as string[]) {
        expect({ k, w, hit: ar.includes(w) }).toEqual({ k, w, hit: false });
      }
      for (const b of policy.banned_ar as { pattern: string }[]) {
        expect({ k, b: b.pattern, hit: ar.includes(b.pattern) }).toEqual({ k, b: b.pattern, hit: false });
      }
      expect({ k, diacritic: AR_DIACRITICS.test(ar.split(BRAND_AR).join('')) }).toEqual({
        k,
        diacritic: false,
      });
    }
  });

  it('T1.25 brand fence: MYEZ / ميّز only, never Qaren / standalone قارن, and every aiConsent key naming the app is in BRAND_KEYS', () => {
    const brandSrc: string = fs.readFileSync(
      path.join(__dirname, '..', 'i18n', 'brand.myez.s69.test.ts'),
      'utf8',
    );
    const block = /const BRAND_KEYS = \[([\s\S]*?)\]\.sort\(\)/.exec(brandSrc);
    expect(block).not.toBeNull();
    const brandKeys = new Set(
      Array.from((block as RegExpExecArray)[1].matchAll(/'([^']+)'/g)).map((m) => m[1]),
    );

    const naming = KEYS.filter((k) => /\bMYEZ\b/.test(EN[k] ?? '') || MYEZ_AR_WORD.test(AR[k] ?? ''));
    expect(naming).toContain('aiConsent.body');
    for (const k of naming) {
      expect({ k, en: /\bMYEZ\b/.test(EN[k] ?? ''), ar: MYEZ_AR_WORD.test(AR[k] ?? '') }).toEqual({
        k,
        en: true,
        ar: true,
      });
      expect({ k, inBrandKeys: brandKeys.has(k) }).toEqual({ k, inBrandKeys: true });
    }
    for (const k of KEYS) {
      expect({ k, qaren: /Qaren/i.test(EN[k] ?? '') || /Qaren/i.test(AR[k] ?? '') }).toEqual({
        k,
        qaren: false,
      });
      expect({ k, oldAr: OLD_AR_WORD.test(AR[k] ?? '') }).toEqual({ k, oldAr: false });
    }
  });

  it('T1.26 the body says the preferences are the ones on the profile, incl. suggested ones, and the photos are taken or picked (EN + AR)', () => {
    // PUT /auth/demographics seeds priorities / budget / brand_attitude from
    // the cohort (change_source 'cohort_default'), and the verdict prompt
    // sends them, so "the preferences you set" was not true for every user.
    const enBody = EN['aiConsent.body'] ?? '';
    expect(enBody).toMatch(/preferences on your profile/i);
    expect(enBody).toMatch(/suggested from your onboarding answers/i);
    expect(enBody).toMatch(/photos you take or pick/i);
    expect(enBody).not.toMatch(/preferences you set/i);
    expect(enBody).not.toMatch(/photos you enter/i);
    expect(enBody).toMatch(/Your name, email and account details are not sent/);

    const arBody = AR['aiConsent.body'] ?? '';
    // «ملفك الشخصي» (your profile), «مقترحة» (suggested), «إجاباتك» (your answers)
    expect(arBody).toContain('ملفك الشخصي');
    expect(arBody).toContain('مقترحة');
    expect(arBody).toContain('إجاباتك');
    // «الصور التي تلتقطها أو تختارها» (the photos you take or pick), never «تدخلها» (you enter)
    expect(arBody).toContain('الصور التي تلتقطها أو تختارها');
    expect(arBody).not.toContain('تدخلها');
    // «لا يرسل اسمك أو بريدك الإلكتروني أو بيانات حسابك» (your name, email and account details are not sent)
    expect(arBody).toContain('لا يرسل اسمك أو بريدك الإلكتروني أو بيانات حسابك');
  });
});
