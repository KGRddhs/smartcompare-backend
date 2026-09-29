/**
 * S69 U7 R1 — the `success:false` DATA branches of both HomeScreen compare
 * paths pick their alert TITLE by code.
 *
 * HomeScreen has two alert sites that receive a resolved (not thrown)
 * `success: false` payload: the SSE `onComplete` terminal (defensive arm —
 * api.ts dispatchTerminal routes success:false to onError today) and the
 * sync /url/compare 200 envelope. Both choose the title with
 * `friendlyErrorTitleKey(code)`; before this pin, reverting either one to
 * `t('common.error')` ("Hold on — give it another tap.") survived the suite.
 * An LLM_UNAVAILABLE outage must show the engine-unavailable title + body,
 * never the retry-loop title.
 *
 * Harness (mocks, helpers) mirrors HomeScreen.errorCopy.a11.test.tsx: `t`
 * resolves through the REAL en.json and errorCopy is the REAL module.
 */

import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react-native';
import enCatalog from '../src/i18n/en.json';

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

// `services/api` is mocked for its NETWORK surface only. `parseApiError` is
// reimplemented faithfully (envelope `code` + the documented fall-through to
// the raw axios `error.message`) because that fall-through IS the leak the
// screen must never render. `friendlyErrorKey` lives in `services/errorCopy`
// and is deliberately NOT mocked — the real map runs.
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
    // S69 U7 R1 — mirrors api.ts: a codeless 502/504 is GATEWAY_UNAVAILABLE.
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

// `t` resolves through the REAL catalog so the assertions below are about
// user-visible sentences, not key names.
jest.mock('react-i18next', () => {
  const catalog = require('../src/i18n/en.json') as Record<string, string>;
  return {
    useTranslation: () => ({
      t: (key: string, opts?: any) => {
        if (catalog[key] !== undefined) return catalog[key];
        if (opts && typeof opts === 'object' && 'defaultValue' in opts) return opts.defaultValue;
        return key;
      },
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

const ENGINE_OUTAGE = {
  success: false,
  error: 'Still warming up the comparison engine — give it another tap in a moment.',
  code: 'LLM_UNAVAILABLE',
  request_id: 'req-llm',
};

describe('S69 U7 R1 — success:false data branches use the engine-unavailable title', () => {
  it('text path: an SSE complete with success:false + LLM_UNAVAILABLE', async () => {
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    const rendered = render(<HomeScreen {...makeProps()} />);
    const handlers = await submitTextCompare(rendered);

    await act(async () => {
      await handlers.onComplete({ ...ENGINE_OUTAGE });
    });

    expect(alertSpy).toHaveBeenCalledTimes(1);
    const [title, body] = alertSpy.mock.calls[0];
    expect(title).toBe(EN['home.errors.engineUnavailable.title']);
    expect(title).not.toBe(EN['common.error']);
    expect(body).toBe(EN['home.errors.engineUnavailable.body']);
    alertSpy.mockRestore();
  });

  it('URL path: a non-stream 200 with success:false + LLM_UNAVAILABLE', async () => {
    mockApiPost.mockResolvedValueOnce({ data: { ...ENGINE_OUTAGE } });
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    const rendered = render(<HomeScreen {...makeProps()} />);
    await submitUrlCompare(rendered);

    await waitFor(() => expect(alertSpy).toHaveBeenCalled());
    const [title, body] = alertSpy.mock.calls[0];
    expect(title).toBe(EN['home.errors.engineUnavailable.title']);
    expect(title).not.toBe(EN['common.error']);
    expect(body).toBe(EN['home.errors.engineUnavailable.body']);
    alertSpy.mockRestore();
  });

  it('control: a success:false INSUFFICIENT_DATA keeps the shared common.error title', async () => {
    mockApiPost.mockResolvedValueOnce({
      data: { success: false, error: 'Not enough product data', code: 'INSUFFICIENT_DATA' },
    });
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    const rendered = render(<HomeScreen {...makeProps()} />);
    await submitUrlCompare(rendered);

    await waitFor(() => expect(alertSpy).toHaveBeenCalled());
    const [title, body] = alertSpy.mock.calls[0];
    expect(title).toBe(EN['common.error']);
    expect(body).toBe(EN['home.errors.insufficientData']);
    alertSpy.mockRestore();
  });
});
