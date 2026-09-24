/**
 * W3-11bcd — MB-I18N-RTL-05: HomeScreen must never render the backend's
 * English `error` prose to an Arabic user on a `success:false` envelope.
 *
 * Harness = __tests__/HomeScreen.errorCopy.a11.test.tsx (A11) with `t`
 * resolving through the REAL ar.json and `i18n.language = 'ar'`.
 * `friendlyErrorKey` (services/errorCopy) is the real module; only
 * `services/api`'s network surface is mocked.
 *
 * LIVE vs DEFENSIVE (spec FABLE ruling R2):
 *   - The URL path (`HomeScreen.tsx:540`, `handleUrlCompare` → `api.post(
 *     '/api/v1/url/compare')` → the SYNC backend `compare_from_text`, whose
 *     `structured_comparison_service.py:3493-3498` / `:3541-3545` returns
 *     carry "We don't compare this category" and "Could not identify two
 *     products to compare. Try: …") is the LIVE defect. Those tests come
 *     FIRST in this file and are the primary RTL-05 red tests.
 *   - The SSE `onComplete` `success:false` arm (`HomeScreen.tsx:418-434`) is
 *     a DEFENSIVE arm no shipped transport reaches: `api.ts:688-700`
 *     (`dispatchTerminal`) routes a `success:false` terminal payload to
 *     `onError`, and `api.ts:603-618` does the same on the REST fallback
 *     (pinned in __tests__/api.terminalRouting.w311.test.ts). The SSE tests
 *     below drive `handlers.onComplete` DIRECTLY to pin the arm in case that
 *     routing ever changes — they are NOT live-path regression tests.
 */

import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react-native';
import arCatalog from '../src/i18n/ar.json';

const AR = arCatalog as Record<string, string>;
const ASCII_LETTER = /[A-Za-z]/;

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

// Same faithful parseApiError re-implementation as the A11 harness.
jest.mock('../src/services/api', () => ({
  __esModule: true,
  default: {
    post: (...args: any[]) => mockApiPost(...args),
  },
  healthCheck: (...args: any[]) => mockHealthCheck(...args),
  streamComparison: (...args: any[]) => mockStreamComparison(...args),
  parseApiError: (error: any) => {
    const data = error?.response?.data;
    const status = error?.response?.status;
    const rawCode =
      (typeof data?.code === 'string' && data.code) ||
      (typeof data?.detail?.code === 'string' && data.detail.code) ||
      null;
    if (rawCode === 'TIMEOUT' || rawCode === 'STREAM_TIMEOUT' || (status === 503 && !rawCode)) {
      return { message: '', code: 'TIMEOUT' };
    }
    if (data?.error) return { message: data.error, code: rawCode };
    if (data?.detail) {
      return {
        message: typeof data.detail === 'string' ? data.detail : 'Invalid request',
        code: rawCode,
      };
    }
    if (error?.message) return { message: error.message, code: rawCode };
    return { message: 'Something went wrong', code: rawCode };
  },
  trackEvent: (...args: any[]) => mockTrackEvent(...args),
  COMPARE_TIMEOUT_MS: 35000,
}));

jest.mock('../src/services/authService', () => ({
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
}));

jest.mock('../src/services/usageService', () => ({
  isUsageLimitError: () => false,
  getUsageLimitDetail: () => null,
}));

jest.mock('../src/services/referralService', () => ({
  getReferralStatus: (...args: any[]) => mockGetReferralStatus(...args),
}));

jest.mock('../src/hooks/useComparisonCounter', () => ({
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

jest.mock('../src/components/CategorySelector', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () => ReactRequired.createElement('View', { testID: 'mock-category-selector' }),
  };
});

jest.mock('../src/components/QarenLogo', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () => ReactRequired.createElement('View', { testID: 'mock-qaren-logo' }),
  };
});

jest.mock('../src/components/TwoInputShell', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: (props: any) =>
      ReactRequired.createElement('View', { testID: 'mock-two-input-shell', ...props }),
  };
});

jest.mock('../src/components/PaywallBanner', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () => ReactRequired.createElement('View', { testID: 'mock-paywall-banner' }),
  };
});

jest.mock('../src/components/HomeEditorialSections', () => {
  const ReactRequired = require('react');
  return {
    __esModule: true,
    default: () =>
      ReactRequired.createElement('View', { testID: 'mock-home-editorial-sections' }),
  };
});

jest.mock('../src/screens/LoadingScreenVariants', () => {
  const ReactRequired = require('react');
  return {
    LoadingScreenVariants: (props: any) =>
      ReactRequired.createElement('View', { ...props, testID: 'mock-loading-screen-variants' }),
  };
});

jest.mock('../src/icons', () => ({
  ScanIcon: () => null,
  LinkIcon: () => null,
  TypeIcon: () => null,
}));

// `t` resolves through the REAL ARABIC catalog, so every assertion below is
// about the sentence an Arabic user would actually read.
jest.mock('react-i18next', () => {
  const catalog = require('../src/i18n/ar.json') as Record<string, string>;
  return {
    useTranslation: () => ({
      t: (key: string, opts?: any) => {
        if (catalog[key] !== undefined) return catalog[key];
        if (opts && typeof opts === 'object' && 'defaultValue' in opts) return opts.defaultValue;
        return key;
      },
      i18n: { language: 'ar' },
    }),
  };
});

import HomeScreen from '../src/screens/HomeScreen';

function makeProps(overrides: any = {}) {
  return {
    navigation: { navigate: jest.fn(), goBack: jest.fn() },
    ...overrides,
  };
}

// The two envelopes the backend really emits (sync path
// structured_comparison_service.py:3493-3498 and :3541-3545).
const CATEGORY_BLOCK = {
  success: false,
  code: 'CONTENT_UNAVAILABLE',
  error: "We don't compare this category",
  layer: 'query_prefilter',
};
const IDENTIFY_FAIL = {
  success: false,
  error: "Could not identify two products to compare. Try: 'iPhone 15 vs Galaxy S24'",
  parsed: {},
};

beforeEach(() => {
  jest.clearAllMocks();
  mockHealthCheck.mockResolvedValue(true);
  mockGetSavedUser.mockResolvedValue({ id: 'u1', email: 'k@example.com' });
  mockGetReferralStatus.mockResolvedValue({
    monthly_bonus_comparisons: 1,
    bonus_referrer_name: 'Sara',
    bonus_expires_at: null,
  });
});

/** Mount, switch to text mode, submit a pair, return the SSE handlers. */
async function submitTextCompare(rendered: any) {
  let handlers: any = null;
  mockStreamComparison.mockReturnValue({
    subscribe: (h: any) => {
      handlers = h;
    },
    abort: jest.fn(),
  });
  fireEvent.press(rendered.getByTestId('home-mode-type'));
  const shell = await waitFor(() => rendered.getByTestId('mock-two-input-shell'));
  await act(async () => {
    shell.props.onSubmit('iPhone 15', 'Galaxy S24');
  });
  return handlers;
}

async function submitUrlCompare(rendered: any) {
  fireEvent.press(rendered.getByTestId('home-mode-link'));
  const shell = await waitFor(() => rendered.getByTestId('mock-two-input-shell'));
  await act(async () => {
    shell.props.onSubmit('https://noon.com/a', 'https://amazon.com/b');
  });
}

describe('W3-11 RTL-05 — URL compare success:false (HomeScreen.tsx:540) — the LIVE defect', () => {
  it('(c) CONTENT_UNAVAILABLE: the content-block alert in Arabic, never the backend English, and the block event fires', async () => {
    mockApiPost.mockResolvedValueOnce({ data: CATEGORY_BLOCK });
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    const rendered = render(<HomeScreen {...makeProps()} />);
    await submitUrlCompare(rendered);

    await waitFor(() => expect(alertSpy).toHaveBeenCalled());
    expect(alertSpy).toHaveBeenCalledTimes(1);
    const [title, body] = alertSpy.mock.calls[0] as [string, string];
    expect(body).not.toMatch(ASCII_LETTER);
    expect(body).toBe(AR['home.compare.unavailable_body']);
    expect(title).toBe(AR['home.compare.unavailable_title']);
    expect(body).not.toBe("We don't compare this category");
    // Same content-block path the onError branch already uses (:452-455).
    expect(mockTrackEvent).toHaveBeenCalledWith('compare_entry_content_block', {
      mode: 'url',
      layer: 'query_prefilter',
    });
    alertSpy.mockRestore();
  });

  it('(c2) CODELESS identify failure: catalog copy, never "Could not identify … Try: …"', async () => {
    // The sync path's codeless return (:3541-3545) reaches this same arm.
    // Without this case a fix that kept `response.data.error ||` on the
    // non-CONTENT_UNAVAILABLE branch would still pass (c) while shipping the
    // copy-contract-forbidden "Could not" sentence to Arabic users.
    mockApiPost.mockResolvedValueOnce({ data: IDENTIFY_FAIL });
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    const rendered = render(<HomeScreen {...makeProps()} />);
    await submitUrlCompare(rendered);

    await waitFor(() => expect(alertSpy).toHaveBeenCalled());
    const body = String(alertSpy.mock.calls[0][1]);
    expect(body).toBe(AR['home.errors.comparison']);
    expect(body).not.toMatch(ASCII_LETTER);
    expect(body).not.toMatch(/Could not/);
    alertSpy.mockRestore();
  });

  it.each([
    ['TIMEOUT', 'home.errors.timeout'],
    ['STREAM_TIMEOUT', 'home.errors.timeout'],
    ['INSUFFICIENT_DATA', 'home.errors.insufficientData'],
  ])(
    '(c3) code %s on the URL arm renders AR[%s], never the backend prose',
    async (code, key) => {
      // The URL arm branches on CODE like the catch branch: timeouts keep the
      // soft timeout copy, INSUFFICIENT_DATA gets its own guidance through
      // friendlyErrorKey. Removing only the `isTimeout ?` ternary is an
      // EQUIVALENT mutant (friendlyErrorKey maps TIMEOUT/STREAM_TIMEOUT to
      // the same key, errorCopy.ts); what this pins is that no code-keyed
      // envelope on this arm collapses onto the generic nudge or the prose.
      mockApiPost.mockResolvedValueOnce({
        data: { success: false, code, error: 'Comparison timed out, please retry later' },
      });
      const RN = require('react-native');
      const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
      const rendered = render(<HomeScreen {...makeProps()} />);
      await submitUrlCompare(rendered);

      await waitFor(() => expect(alertSpy).toHaveBeenCalled());
      const body = String(alertSpy.mock.calls[0][1]);
      expect(AR[key]).toEqual(expect.any(String));
      expect(body).toBe(AR[key]);
      expect(body).not.toMatch(ASCII_LETTER);
      alertSpy.mockRestore();
    },
  );
});

describe('W3-11 RTL-05 — SSE onComplete success:false (HomeScreen.tsx:418-434) — DEFENSIVE-ARM pins', () => {
  // DEFENSIVE-ARM PIN: api.ts:688-700 (`dispatchTerminal`) sends every
  // success:false terminal payload to onError, so no shipped transport calls
  // onComplete with success:false today. These drive the arm directly so it
  // cannot leak prose if that routing ever changes.

  it('(a) CONTENT_UNAVAILABLE → the content-block alert in Arabic', async () => {
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    const rendered = render(<HomeScreen {...makeProps()} />);
    const handlers = await submitTextCompare(rendered);

    await act(async () => {
      await handlers.onComplete(CATEGORY_BLOCK);
    });

    expect(alertSpy).toHaveBeenCalledTimes(1);
    const [title, body] = alertSpy.mock.calls[0] as [string, string];
    expect(body).not.toMatch(ASCII_LETTER);
    expect(body).toBe(AR['home.compare.unavailable_body']);
    expect(title).toBe(AR['home.compare.unavailable_title']);
    // The envelope's `layer` reaches the content-block event (same shape as
    // the URL arm and the onError branch).
    expect(mockTrackEvent).toHaveBeenCalledWith('compare_entry_content_block', {
      mode: 'text',
      layer: 'query_prefilter',
    });
    alertSpy.mockRestore();
  });

  it('(b) CODELESS identify failure → home.errors.comparison, never "Could not"', async () => {
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    const rendered = render(<HomeScreen {...makeProps()} />);
    const handlers = await submitTextCompare(rendered);

    await act(async () => {
      await handlers.onComplete(IDENTIFY_FAIL);
    });

    const body = String(alertSpy.mock.calls[0][1]);
    expect(body).toBe(AR['home.errors.comparison']);
    expect(body).not.toMatch(ASCII_LETTER);
    expect(body).not.toMatch(/Could not/);
    alertSpy.mockRestore();
  });

  it('(d) STREAM_TIMEOUT keeps the soft timeout copy (D2 branch regression pin)', async () => {
    // Regression pin for the existing D2 timeout branch — passes at base by
    // design; it stops the (a)/(b) fix from swallowing the timeout copy.
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    const rendered = render(<HomeScreen {...makeProps()} />);
    const handlers = await submitTextCompare(rendered);

    await act(async () => {
      await handlers.onComplete({ success: false, code: 'STREAM_TIMEOUT', error: 'stream timeout' });
    });

    expect(alertSpy.mock.calls[0][1]).toBe(AR['home.errors.timeout']);
    alertSpy.mockRestore();
  });
});
