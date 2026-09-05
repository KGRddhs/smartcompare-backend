/**
 * A11 — HomeScreen renders CODE-derived copy on BOTH compare paths.
 *
 * The finding: the text path rendered `error.message` where the URL path
 * rendered `parsed.message`. M21 W2 (`1df95b0`) hardened only the CODED arm
 * of the text path — `parsed.code ? t('home.errors.comparison') :
 * error.message || t('home.errors.comparison')` — which left the codeless
 * arm rendering the raw axios string, and left the URL path's
 * `Alert.alert(t('common.error'), parsed.message)` with no code guard at
 * all. Nothing in the suite pinned this screen's alert copy.
 *
 * This is a RUNTIME test, not a source-grep: it drives the real SSE
 * `onError` callback and the real URL `catch`, and asserts on the string
 * that actually reaches `Alert.alert`. `t` resolves through the REAL
 * en.json, and `friendlyErrorKey` is the REAL module (only
 * `services/api`'s network surface is mocked), so a regression to
 * `.message` on either path fails here.
 *
 * Harness mirrors HomeScreen.eS3hf.loaderVisibility.test.tsx.
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

/** An axios rejection exactly as the interceptor hands it to the screen. */
function axiosError(status: number, data: any): any {
  const err: any = new Error(`Request failed with status code ${status}`);
  err.isAxiosError = true;
  err.response = { status, data };
  return err;
}

const INSUFFICIENT_400 = () =>
  axiosError(400, {
    success: false,
    error: 'Not enough product data to compare',
    code: 'INSUFFICIENT_DATA',
    request_id: 'req-1',
  });

// Railway edge 502 with an HTML body: no `error`/`detail` key, so
// parseApiError falls through to the axios string and `code` is null.
const EDGE_502 = () => axiosError(502, '<html><body>Bad gateway</body></html>');

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

describe('A11 — text compare (SSE onError)', () => {
  it('an INSUFFICIENT_DATA 400 shows the dedicated copy, never the axios string', async () => {
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    const rendered = render(<HomeScreen {...makeProps()} />);
    const handlers = await submitTextCompare(rendered);

    await act(async () => {
      handlers.onError(INSUFFICIENT_400());
    });

    expect(alertSpy).toHaveBeenCalledTimes(1);
    const body = alertSpy.mock.calls[0][1];
    expect(body).toBe(EN['home.errors.insufficientData']);
    expect(body).not.toMatch(/Request failed with status code/);
    // Pre-A11 the coded arm collapsed every code onto the generic nudge.
    expect(body).not.toBe(EN['home.errors.comparison']);
    alertSpy.mockRestore();
  });

  it('a CODELESS edge 502 shows catalog copy — the arm that used to leak', async () => {
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    const rendered = render(<HomeScreen {...makeProps()} />);
    const handlers = await submitTextCompare(rendered);

    await act(async () => {
      handlers.onError(EDGE_502());
    });

    const body = alertSpy.mock.calls[0][1];
    // The exact pre-A11 symptom on this arm.
    expect(body).not.toBe('Request failed with status code 502');
    expect(body).not.toMatch(/failed/i);
    expect(body).toBe(EN['home.errors.comparison']);
    alertSpy.mockRestore();
  });

  it('a RATE_LIMITED 429 shows wait guidance, not the retype nudge', async () => {
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    const rendered = render(<HomeScreen {...makeProps()} />);
    const handlers = await submitTextCompare(rendered);

    await act(async () => {
      handlers.onError(
        axiosError(429, {
          success: false,
          error: 'Rate limit exceeded: 10 per 1 minute',
          code: 'RATE_LIMITED',
        }),
      );
    });

    const body = alertSpy.mock.calls[0][1];
    expect(body).toBe(EN['home.errors.rateLimited']);
    expect(body).not.toMatch(/per 1 minute/);
    alertSpy.mockRestore();
  });

  it('TIMEOUT keeps the established soft copy (no regression)', async () => {
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    const rendered = render(<HomeScreen {...makeProps()} />);
    const handlers = await submitTextCompare(rendered);

    await act(async () => {
      handlers.onError(axiosError(503, { success: false, error: 'upstream slow' }));
    });

    expect(alertSpy.mock.calls[0][1]).toBe(EN['home.errors.timeout']);
    alertSpy.mockRestore();
  });
});

describe('A11 — URL compare (catch) now agrees with the text path', () => {
  it('an INSUFFICIENT_DATA 400 shows the same dedicated copy', async () => {
    mockApiPost.mockRejectedValueOnce(INSUFFICIENT_400());
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    const rendered = render(<HomeScreen {...makeProps()} />);
    await submitUrlCompare(rendered);

    await waitFor(() => expect(alertSpy).toHaveBeenCalled());
    const body = alertSpy.mock.calls[0][1];
    expect(body).toBe(EN['home.errors.insufficientData']);
    // Pre-A11 this path rendered `parsed.message` unconditionally, i.e. the
    // backend's English sentence — English copy for an Arabic user.
    expect(body).not.toBe('Not enough product data to compare');
    alertSpy.mockRestore();
  });

  it('a CODELESS edge 502 no longer leaks the raw axios string', async () => {
    mockApiPost.mockRejectedValueOnce(EDGE_502());
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    const rendered = render(<HomeScreen {...makeProps()} />);
    await submitUrlCompare(rendered);

    await waitFor(() => expect(alertSpy).toHaveBeenCalled());
    const body = alertSpy.mock.calls[0][1];
    // This is the residual the finding wrongly called "the correct path":
    // `parsed.message` here WAS "Request failed with status code 502".
    expect(body).not.toBe('Request failed with status code 502');
    expect(body).not.toMatch(/failed/i);
    expect(body).toBe(EN['home.errors.comparison']);
    alertSpy.mockRestore();
  });

  it('both paths resolve the SAME copy for the SAME error (the asymmetry is gone)', async () => {
    const RN = require('react-native');

    const alertSpyText = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    const textRender = render(<HomeScreen {...makeProps()} />);
    const handlers = await submitTextCompare(textRender);
    await act(async () => {
      handlers.onError(INSUFFICIENT_400());
    });
    const textBody = alertSpyText.mock.calls[0][1];
    alertSpyText.mockRestore();

    mockApiPost.mockRejectedValueOnce(INSUFFICIENT_400());
    const alertSpyUrl = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => {});
    const urlRender = render(<HomeScreen {...makeProps()} />);
    await submitUrlCompare(urlRender);
    await waitFor(() => expect(alertSpyUrl).toHaveBeenCalled());
    const urlBody = alertSpyUrl.mock.calls[0][1];
    alertSpyUrl.mockRestore();

    expect(textBody).toBe(urlBody);
  });
});
