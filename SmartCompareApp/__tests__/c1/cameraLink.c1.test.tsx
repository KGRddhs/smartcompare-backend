/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * INC-C1 OTA-BATCH RED -- camera and link (INC_C1_UNIT_SPEC_V2.md section
 * 7.3, rows C1, L1 and the pins C2, L2, P1(c)(d); gate rulings F1, F13).
 *
 * The contract this file fixes for GREEN:
 *  - A THROWN identify failure with HTTP 503 and code LLM_UNAVAILABLE (top
 *    level, or under detail) shows the photo state: container testID
 *    results-photo-unavailable-state, title results.photoUnavailable.title,
 *    body results.photoUnavailable.body, a primary button
 *    results-photo-type-names labelled common.typeNames and a secondary
 *    button results-empty-back labelled common.back (goBack). Type the names
 *    calls navigation.popTo('Main') (never goBack); on the next focus Home
 *    opens in type mode, once: a second focus changes nothing (C1).
 *  - Every other camera answer keeps today's screen: the engine state with
 *    ONE button, the retryable timeout state, the paywall (C2, P1(d)).
 *  - On the LINK path only, STORE_UNREADABLE / NOT_PRODUCT_PAGE /
 *    UNRESOLVED_PRODUCT / BAD_REQUEST / no code (thrown, or a 200 with success
 *    false) raise Alert.alert(home.errors.link.title, <the code's sentence>,
 *    [Cancel (style cancel), Type the names]); Type the names switches Home to
 *    type mode (L1). Every other link answer and the text path keep today's
 *    two-argument alert or navigation (L2, P1(c)).
 *
 * Harness: ONE module registry for ResultsScreen and HomeScreen. One
 * services/api mock (the a11 network surface plus the s69 camera surface;
 * parseApiError = the a11 copy plus api.ts's additive reason read); the
 * camera.engineUnavailable.s69 mocks and the HomeScreen.errorCopy.a11 mocks;
 * usageService keyed on code USAGE_LIMIT; react-i18next = the c1a catalog t
 * over the real en.json / ar.json. useFocusEffect keeps a runner per
 * subscriber in mockFocus (run on mount, dropped on unmount); fireFocus()
 * runs every runner, as a navigation focus event would. The new intent module
 * is reached only through the screens (F1: no import of a new symbol, no
 * jest.mock of a new path; every base failure is an expect assertion).
 * Arabic from the section 6 code points; this source stays ASCII.
 */

import React from 'react';
import { render, fireEvent, act, waitFor } from '@testing-library/react-native';
import enCatalog from '../../src/i18n/en.json';
import arCatalog from '../../src/i18n/ar.json';

import HomeScreen from '../../src/screens/HomeScreen';
import ResultsScreen from '../../src/screens/ResultsScreen';

const EN = enCatalog as unknown as Record<string, string>;
const AR = arCatalog as unknown as Record<string, string>;

let mockLang: 'en' | 'ar' = 'en';
const mockFocus = new Set<() => void>();

// A focus runner per useFocusEffect subscriber: run on mount, run again by
// fireFocus(), dropped (with its cleanup) on unmount.
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

// The c1a catalog t: the real en.json / ar.json, {{var}} filled, no plurals.
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

// ------------------------------------------------------------------ strings --

const u = (...cps: number[]) => String.fromCodePoint(...cps);

// Section 6 rows 18-25 of the unit spec: EN literal, AR from the code points.
const ROW: Record<number, { key: string; en: string; ar: string }> = {
  18: {
    key: 'results.photoUnavailable.title',
    en: 'Photo compare is not available right now',
    ar: u(
      0x627, 0x644, 0x645, 0x642, 0x627, 0x631, 0x646, 0x629, 0x20, 0x628, 0x627, 0x644,
      0x635, 0x648, 0x631, 0x20, 0x63a, 0x64a, 0x631, 0x20, 0x645, 0x62a, 0x627, 0x62d,
      0x629, 0x20, 0x62d, 0x627, 0x644, 0x64a, 0x64b, 0x627,
    ),
  },
  19: {
    key: 'results.photoUnavailable.body',
    en: 'You can type the two names instead.',
    ar: u(
      0x64a, 0x645, 0x643, 0x646, 0x643, 0x20, 0x643, 0x62a, 0x627, 0x628, 0x629, 0x20,
      0x627, 0x633, 0x645, 0x64a, 0x20, 0x627, 0x644, 0x639, 0x637, 0x631, 0x64a, 0x646,
      0x20, 0x628, 0x62f, 0x644, 0x64b, 0x627, 0x20, 0x645, 0x646, 0x20, 0x630, 0x644,
      0x643, 0x2e,
    ),
  },
  20: {
    key: 'common.typeNames',
    en: 'Type the names',
    ar: u(0x627, 0x643, 0x62a, 0x628, 0x20, 0x627, 0x644, 0x623, 0x633, 0x645, 0x627, 0x621),
  },
  21: {
    key: 'home.errors.link.title',
    en: 'Let\'s try another way',
    ar: u(
      0x644, 0x646, 0x62c, 0x631, 0x651, 0x628, 0x20, 0x637, 0x631, 0x64a, 0x642, 0x629,
      0x20, 0x623, 0x62e, 0x631, 0x649,
    ),
  },
  22: {
    key: 'home.errors.link.storeUnreadable',
    en: 'This shop\'s page did not open for us. You can type the two names instead.',
    ar: u(
      0x635, 0x641, 0x62d, 0x629, 0x20, 0x647, 0x630, 0x627, 0x20, 0x627, 0x644, 0x645,
      0x62a, 0x62c, 0x631, 0x20, 0x644, 0x645, 0x20, 0x62a, 0x64f, 0x641, 0x62a, 0x62d,
      0x20, 0x644, 0x62f, 0x64a, 0x646, 0x627, 0x2e, 0x20, 0x64a, 0x645, 0x643, 0x646,
      0x643, 0x20, 0x643, 0x62a, 0x627, 0x628, 0x629, 0x20, 0x627, 0x633, 0x645, 0x64a,
      0x20, 0x627, 0x644, 0x639, 0x637, 0x631, 0x64a, 0x646, 0x20, 0x628, 0x62f, 0x644,
      0x64b, 0x627, 0x20, 0x645, 0x646, 0x20, 0x630, 0x644, 0x643, 0x2e,
    ),
  },
  23: {
    key: 'home.errors.link.notProductPage',
    en: 'That link opens a shop page, not a product. Open the perfume\'s own page and copy its link.',
    ar: u(
      0x647, 0x630, 0x627, 0x20, 0x627, 0x644, 0x631, 0x627, 0x628, 0x637, 0x20, 0x64a,
      0x641, 0x62a, 0x62d, 0x20, 0x635, 0x641, 0x62d, 0x629, 0x20, 0x645, 0x62a, 0x62c,
      0x631, 0x20, 0x648, 0x644, 0x64a, 0x633, 0x20, 0x635, 0x641, 0x62d, 0x629, 0x20,
      0x645, 0x646, 0x62a, 0x62c, 0x2e, 0x20, 0x627, 0x641, 0x62a, 0x62d, 0x20, 0x635,
      0x641, 0x62d, 0x629, 0x20, 0x627, 0x644, 0x639, 0x637, 0x631, 0x20, 0x646, 0x641,
      0x633, 0x647, 0x20, 0x648, 0x627, 0x646, 0x633, 0x62e, 0x20, 0x631, 0x627, 0x628,
      0x637, 0x647, 0x627, 0x2e,
    ),
  },
  24: {
    key: 'home.errors.link.unresolved',
    en: 'We did not find a perfume on that page. Copy the link of the perfume\'s own page.',
    ar: u(
      0x644, 0x645, 0x20, 0x646, 0x62c, 0x62f, 0x20, 0x639, 0x637, 0x631, 0x64b, 0x627,
      0x20, 0x641, 0x64a, 0x20, 0x62a, 0x644, 0x643, 0x20, 0x627, 0x644, 0x635, 0x641,
      0x62d, 0x629, 0x2e, 0x20, 0x627, 0x646, 0x633, 0x62e, 0x20, 0x631, 0x627, 0x628,
      0x637, 0x20, 0x635, 0x641, 0x62d, 0x629, 0x20, 0x627, 0x644, 0x639, 0x637, 0x631,
      0x20, 0x646, 0x641, 0x633, 0x647, 0x2e,
    ),
  },
  25: {
    key: 'home.errors.link.generic',
    en: 'One of those links did not open for us. Paste a link from another shop, or type the two names.',
    ar: u(
      0x623, 0x62d, 0x62f, 0x20, 0x627, 0x644, 0x631, 0x627, 0x628, 0x637, 0x64a, 0x646,
      0x20, 0x644, 0x645, 0x20, 0x64a, 0x64f, 0x641, 0x62a, 0x62d, 0x20, 0x644, 0x62f,
      0x64a, 0x646, 0x627, 0x2e, 0x20, 0x627, 0x644, 0x635, 0x642, 0x20, 0x631, 0x627,
      0x628, 0x637, 0x64b, 0x627, 0x20, 0x645, 0x646, 0x20, 0x645, 0x62a, 0x62c, 0x631,
      0x20, 0x622, 0x62e, 0x631, 0x60c, 0x20, 0x623, 0x648, 0x20, 0x627, 0x643, 0x62a,
      0x628, 0x20, 0x627, 0x633, 0x645, 0x64a, 0x20, 0x627, 0x644, 0x639, 0x637, 0x631,
      0x64a, 0x646, 0x2e,
    ),
  },
};
const cat = (lang: 'en' | 'ar') => (lang === 'ar' ? AR : EN);

/** What a reader of `lang` sees on the new and the existing surfaces. */
function say(lang: 'en' | 'ar') {
  const c = cat(lang);
  return {
    photoTitle: ROW[18][lang],
    photoBody: ROW[19][lang],
    typeNames: ROW[20][lang],
    linkTitle: ROW[21][lang],
    row: (n: number) => ROW[n][lang],
    back: c['common.back'],
    cancel: c['common.cancel'],
    engineTitle: c['home.errors.engineUnavailable.title'],
    engineBody: c['home.errors.engineUnavailable.body'],
  };
}

// Recorded from the base catalogs (d2f49d8b): the alerts and screens render
// these values verbatim through the catalog t above.
const P1C_GOLDEN: Record<string, string[]> = {
  'TIMEOUT 503-en': [
    'Hold on ' + u(0x2014) + ' give it another tap.',
    'Still gathering prices ' + u(0x2014) + ' give it another tap in a moment.',
  ],
  'LLM_UNAVAILABLE 503-en': [
    'One moment ' + u(0x2014) + ' the comparison engine is resting',
    'Comparisons are paused for a moment. Please come back shortly.',
  ],
  'INSUFFICIENT_DATA same_identity-en': [
    'Hold on ' + u(0x2014) + ' give it another tap.',
    'Those two look like the same product. Pick two different fragrances to compare.',
  ],
  'RATE_LIMITED 5 s-en': [
    'Hold on ' + u(0x2014) + ' give it another tap.',
    'Plenty of compares in flight ' + u(0x2014) + ' give it a moment, then tap.',
  ],
  'TIMEOUT 503-ar': [
    u(
      0x644, 0x62d, 0x638, 0x629, 0x20, 0x2014, 0x20, 0x62c, 0x631, 0x651, 0x628, 0x20,
      0x627, 0x644, 0x636, 0x63a, 0x637, 0x20, 0x645, 0x631, 0x651, 0x629, 0x20, 0x62b,
      0x627, 0x646, 0x64a, 0x629, 0x2e,
    ),
    u(
      0x645, 0x627, 0x20, 0x632, 0x644, 0x646, 0x627, 0x20, 0x646, 0x62c, 0x645, 0x639,
      0x20, 0x627, 0x644, 0x623, 0x633, 0x639, 0x627, 0x631, 0x20, 0x2014, 0x20, 0x623,
      0x645, 0x647, 0x644, 0x647, 0x627, 0x20, 0x644, 0x62d, 0x638, 0x629, 0x20, 0x62b,
      0x645, 0x20, 0x627, 0x636, 0x63a, 0x637, 0x20, 0x645, 0x62c, 0x62f, 0x62f, 0x64b,
      0x627, 0x2e,
    ),
  ],
  'LLM_UNAVAILABLE 503-ar': [
    u(
      0x644, 0x62d, 0x638, 0x629, 0x20, 0x648, 0x627, 0x62d, 0x62f, 0x629, 0x20, 0x2014,
      0x20, 0x645, 0x62d, 0x631, 0x643, 0x20, 0x627, 0x644, 0x645, 0x642, 0x627, 0x631,
      0x646, 0x629, 0x20, 0x641, 0x64a, 0x20, 0x627, 0x633, 0x62a, 0x631, 0x627, 0x62d,
      0x629, 0x20, 0x642, 0x635, 0x64a, 0x631, 0x629,
    ),
    u(
      0x627, 0x644, 0x645, 0x642, 0x627, 0x631, 0x646, 0x627, 0x62a, 0x20, 0x645, 0x62a,
      0x648, 0x642, 0x641, 0x629, 0x20, 0x645, 0x624, 0x642, 0x62a, 0x627, 0x2e, 0x20,
      0x64a, 0x631, 0x62c, 0x649, 0x20, 0x627, 0x644, 0x639, 0x648, 0x62f, 0x629, 0x20,
      0x628, 0x639, 0x62f, 0x20, 0x642, 0x644, 0x64a, 0x644, 0x2e,
    ),
  ],
  'INSUFFICIENT_DATA same_identity-ar': [
    u(
      0x644, 0x62d, 0x638, 0x629, 0x20, 0x2014, 0x20, 0x62c, 0x631, 0x651, 0x628, 0x20,
      0x627, 0x644, 0x636, 0x63a, 0x637, 0x20, 0x645, 0x631, 0x651, 0x629, 0x20, 0x62b,
      0x627, 0x646, 0x64a, 0x629, 0x2e,
    ),
    u(
      0x64a, 0x628, 0x62f, 0x648, 0x20, 0x623, 0x646, 0x20, 0x627, 0x644, 0x645, 0x646,
      0x62a, 0x62c, 0x64a, 0x646, 0x20, 0x646, 0x641, 0x633, 0x20, 0x627, 0x644, 0x639,
      0x637, 0x631, 0x2e, 0x20, 0x627, 0x62e, 0x62a, 0x631, 0x20, 0x639, 0x637, 0x631,
      0x64a, 0x646, 0x20, 0x645, 0x62e, 0x62a, 0x644, 0x641, 0x64a, 0x646, 0x20, 0x644,
      0x644, 0x645, 0x642, 0x627, 0x631, 0x646, 0x629, 0x2e,
    ),
  ],
  'RATE_LIMITED 5 s-ar': [
    u(
      0x644, 0x62d, 0x638, 0x629, 0x20, 0x2014, 0x20, 0x62c, 0x631, 0x651, 0x628, 0x20,
      0x627, 0x644, 0x636, 0x63a, 0x637, 0x20, 0x645, 0x631, 0x651, 0x629, 0x20, 0x62b,
      0x627, 0x646, 0x64a, 0x629, 0x2e,
    ),
    u(
      0x639, 0x62f, 0x62f, 0x20, 0x627, 0x644, 0x645, 0x642, 0x627, 0x631, 0x646, 0x627,
      0x62a, 0x20, 0x643, 0x628, 0x64a, 0x631, 0x20, 0x627, 0x644, 0x622, 0x646, 0x20,
      0x2014, 0x20, 0x623, 0x645, 0x647, 0x644, 0x647, 0x627, 0x20, 0x644, 0x62d, 0x638,
      0x629, 0x20, 0x62b, 0x645, 0x20, 0x627, 0x636, 0x63a, 0x637, 0x2e,
    ),
  ],
};

const P1D_GOLDEN: Record<string, { texts: string[]; ids: string[] }> = {
  'thrown-500-en': {
    texts: [
      'One moment ' + u(0x2014) + ' the comparison engine is resting',
      'Comparisons are paused for a moment. Please come back shortly.',
      'Back',
    ],
    ids: ['results-empty-state'],
  },
  '200-failed-llm-en': {
    texts: [
      'One moment ' + u(0x2014) + ' the comparison engine is resting',
      'Comparisons are paused for a moment. Please come back shortly.',
      'Back',
    ],
    ids: ['results-empty-state'],
  },
  '200-failed-nocode-en': {
    texts: [
      'Still gathering prices',
      'We\'re lining up the best local listings ' + u(0x2014) + ' give it another tap in a moment.',
      'Tap to retry',
    ],
    ids: ['results-empty-state', 'results-timeout-state', 'results-timeout-retry'],
  },
  'thrown-500-ar': {
    texts: [
      u(
        0x644, 0x62d, 0x638, 0x629, 0x20, 0x648, 0x627, 0x62d, 0x62f, 0x629, 0x20, 0x2014,
        0x20, 0x645, 0x62d, 0x631, 0x643, 0x20, 0x627, 0x644, 0x645, 0x642, 0x627, 0x631,
        0x646, 0x629, 0x20, 0x641, 0x64a, 0x20, 0x627, 0x633, 0x62a, 0x631, 0x627, 0x62d,
        0x629, 0x20, 0x642, 0x635, 0x64a, 0x631, 0x629,
      ),
      u(
        0x627, 0x644, 0x645, 0x642, 0x627, 0x631, 0x646, 0x627, 0x62a, 0x20, 0x645, 0x62a,
        0x648, 0x642, 0x641, 0x629, 0x20, 0x645, 0x624, 0x642, 0x62a, 0x627, 0x2e, 0x20,
        0x64a, 0x631, 0x62c, 0x649, 0x20, 0x627, 0x644, 0x639, 0x648, 0x62f, 0x629, 0x20,
        0x628, 0x639, 0x62f, 0x20, 0x642, 0x644, 0x64a, 0x644, 0x2e,
      ),
      u(0x631, 0x62c, 0x648, 0x639),
    ],
    ids: ['results-empty-state'],
  },
  '200-failed-llm-ar': {
    texts: [
      u(
        0x644, 0x62d, 0x638, 0x629, 0x20, 0x648, 0x627, 0x62d, 0x62f, 0x629, 0x20, 0x2014,
        0x20, 0x645, 0x62d, 0x631, 0x643, 0x20, 0x627, 0x644, 0x645, 0x642, 0x627, 0x631,
        0x646, 0x629, 0x20, 0x641, 0x64a, 0x20, 0x627, 0x633, 0x62a, 0x631, 0x627, 0x62d,
        0x629, 0x20, 0x642, 0x635, 0x64a, 0x631, 0x629,
      ),
      u(
        0x627, 0x644, 0x645, 0x642, 0x627, 0x631, 0x646, 0x627, 0x62a, 0x20, 0x645, 0x62a,
        0x648, 0x642, 0x641, 0x629, 0x20, 0x645, 0x624, 0x642, 0x62a, 0x627, 0x2e, 0x20,
        0x64a, 0x631, 0x62c, 0x649, 0x20, 0x627, 0x644, 0x639, 0x648, 0x62f, 0x629, 0x20,
        0x628, 0x639, 0x62f, 0x20, 0x642, 0x644, 0x64a, 0x644, 0x2e,
      ),
      u(0x631, 0x62c, 0x648, 0x639),
    ],
    ids: ['results-empty-state'],
  },
  '200-failed-nocode-ar': {
    texts: [
      u(
        0x645, 0x627, 0x20, 0x632, 0x644, 0x646, 0x627, 0x20, 0x646, 0x62c, 0x645, 0x639,
        0x20, 0x627, 0x644, 0x623, 0x633, 0x639, 0x627, 0x631,
      ),
      u(
        0x646, 0x64f, 0x631, 0x62a, 0x651, 0x628, 0x20, 0x623, 0x641, 0x636, 0x644, 0x20,
        0x627, 0x644, 0x639, 0x631, 0x648, 0x636, 0x20, 0x627, 0x644, 0x645, 0x62d, 0x644,
        0x64a, 0x629, 0x20, 0x2014, 0x20, 0x623, 0x645, 0x647, 0x644, 0x647, 0x627, 0x20,
        0x644, 0x62d, 0x638, 0x629, 0x20, 0x62b, 0x645, 0x20, 0x627, 0x636, 0x63a, 0x637,
        0x20, 0x645, 0x62c, 0x62f, 0x62f, 0x64b, 0x627, 0x2e,
      ),
      u(
        0x627, 0x636, 0x63a, 0x637, 0x20, 0x644, 0x625, 0x639, 0x627, 0x62f, 0x629, 0x20,
        0x627, 0x644, 0x645, 0x62d, 0x627, 0x648, 0x644, 0x629,
      ),
    ],
    ids: ['results-empty-state', 'results-timeout-state', 'results-timeout-retry'],
  },
};
const NEW_IDS = ['results-photo-unavailable-state', 'results-photo-type-names', 'results-empty-back'];

/** Rows loop over many renders; bound each one well above jest's 5 s default. */
const ROW_MS = 60000;

// ------------------------------------------------------------------ helpers --

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

const textOf = (rendered: any, id: string) => {
  const n = rendered.queryByTestId(id);
  return n ? allText(n.children).join('') : null;
};

/** The testIDs under a node (itself included), first appearance order. */
const idsUnder = (node: any): string[] =>
  node
    .findAll((n: any) => typeof n.props?.testID === 'string')
    .map((n: any) => n.props.testID as string)
    .filter((id: string, i: number, a: string[]) => a.indexOf(id) === i);

/** Host elements with the button role under a node. */
const buttonsUnder = (node: any): any[] =>
  node.findAll((n: any) => typeof n.type === 'string' && n.props?.accessibilityRole === 'button');

const selected = (rendered: any, id: string) => rendered.getByTestId(id).props.accessibilityState;

/** The axios-SHAPED error identifyFromImages throws on !response.ok. */
const thrownIdentify = (status: number, data: any) =>
  Object.assign(new Error(`Server error ${status}`), { response: { status, data } });

/** An axios rejection exactly as the interceptor hands it to the screen. */
function axiosError(status: number, data: any): any {
  const err: any = new Error(`Request failed with status code ${status}`);
  err.isAxiosError = true;
  err.response = { status, data };
  return err;
}

const makeHomeNavigation = () => ({ navigate: jest.fn(), goBack: jest.fn() });
const makeCameraNavigation = () => ({
  goBack: jest.fn(),
  navigate: jest.fn(),
  setOptions: jest.fn(),
  popTo: jest.fn(),
});

const IDENTIFIED = [
  { brand: 'A', name: 'one' },
  { brand: 'B', name: 'two' },
];

const flush = async () => {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
};

const tick = async (ms: number) => {
  await flush();
  await act(async () => {
    jest.advanceTimersByTime(ms);
  });
  await flush();
};

/** Runs every focus runner, as a navigation focus event does. */
async function fireFocus() {
  await act(async () => {
    mockFocus.forEach((run) => run());
  });
}

async function renderCamera(navigation: any) {
  const rendered = render(
    <ResultsScreen
      route={{ params: { vision_products: ['file://a.jpg', 'file://b.jpg'] } } as any}
      navigation={navigation}
    />,
  );
  // Past the 1.2 s camera floor, so any settled state is on screen.
  await tick(1500);
  return rendered;
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

// ------------------------------------------------------------------ camera --

describe('INC-C1 camera rows (ResultsScreen with HomeScreen, fake timers)', () => {
  beforeEach(() => {
    resetCommon();
    jest.useFakeTimers();
  });
  afterEach(() => {
    jest.useRealTimers();
    mockLang = 'en';
  });

  it('C1 a thrown 503 LLM_UNAVAILABLE shows the photo state; Type the names pops to Main and Home opens in type mode once; Back goes back', async () => {
    const variants: { lang: 'en' | 'ar'; label: string; data: any }[] = [
      {
        lang: 'en',
        label: 'top-level code',
        data: { success: false, error: 'x', code: 'LLM_UNAVAILABLE', request_id: 'r' },
      },
      { lang: 'en', label: 'detail code', data: { detail: { code: 'LLM_UNAVAILABLE', error: 'x' } } },
      {
        lang: 'ar',
        label: 'top-level code',
        data: { success: false, error: 'x', code: 'LLM_UNAVAILABLE', request_id: 'r' },
      },
    ];
    for (const v of variants) {
      mockLang = v.lang;
      const s = say(v.lang);
      const home = render(<HomeScreen navigation={makeHomeNavigation() as any} />);
      await flush();
      // Harness check (passes at base): Home starts in scan mode.
      expect(selected(home, 'home-mode-scan')).toEqual({ selected: true });

      mockIdentifyFromImages.mockReset();
      mockIdentifyFromImages.mockRejectedValue(thrownIdentify(503, v.data));
      const nav = makeCameraNavigation();
      const results = await renderCamera(nav);
      expect(mockIdentifyFromImages).toHaveBeenCalled();

      const state = results.queryByTestId('results-photo-unavailable-state');
      expect({ variant: `${v.lang} ${v.label}`, photoState: state !== null }).toEqual({
        variant: `${v.lang} ${v.label}`,
        photoState: true,
      });
      const stateTexts = allText(state?.children ?? []);
      expect(stateTexts).toContain(s.photoTitle);
      expect(stateTexts).toContain(s.photoBody);
      expect(stateTexts.indexOf(s.photoTitle)).toBeLessThan(stateTexts.indexOf(s.photoBody));
      expect(textOf(results, 'results-photo-type-names')).toBe(s.typeNames);
      expect(textOf(results, 'results-empty-back')).toBe(s.back);
      expect(results.queryByText(s.engineTitle)).toBeNull();
      expect(results.queryByText(s.engineBody)).toBeNull();
      expect(results.queryByTestId('results-timeout-state')).toBeNull();

      // Type the names: back to Main (never goBack), and the intent waits for Home's focus.
      fireEvent.press(results.getByTestId('results-photo-type-names'));
      expect(nav.popTo).toHaveBeenCalledTimes(1);
      expect(nav.popTo).toHaveBeenCalledWith('Main');
      expect(nav.goBack).not.toHaveBeenCalled();
      await fireFocus();
      expect(selected(home, 'home-mode-type')).toEqual({ selected: true });
      expect(selected(home, 'home-mode-scan')).toEqual({ selected: false });
      expect(home.getByTestId('mock-two-input-shell').props.mode).toBe('text');

      // Once: a later focus does not re-apply it (the tab's onPress in act: RNTL 13, as in L1).
      await act(async () => {
        home.getByTestId('home-mode-scan').props.onPress();
      });
      await fireFocus();
      expect(selected(home, 'home-mode-scan')).toEqual({ selected: true });
      expect(selected(home, 'home-mode-type')).toEqual({ selected: false });

      // The secondary button goes back.
      fireEvent.press(results.getByTestId('results-empty-back'));
      expect(nav.goBack).toHaveBeenCalledTimes(1);

      results.unmount();
      home.unmount();
    }
  }, ROW_MS);

  it('C2 pin: every other camera failure keeps today\'s screen (engine state with ONE button, timeout state, paywall)', async () => {
    const s = say('en');
    const engine: [string, () => void][] = [
      [
        'thrown 500 SERVER_ERROR',
        () =>
          mockIdentifyFromImages.mockRejectedValue(
            thrownIdentify(500, { success: false, error: 'x', code: 'SERVER_ERROR', request_id: 'r' }),
          ),
      ],
      [
        'thrown bare 500',
        () => mockIdentifyFromImages.mockRejectedValue(thrownIdentify(500, { error: 'Internal Server Error' })),
      ],
      [
        'thrown 502 {error}',
        () => mockIdentifyFromImages.mockRejectedValue(thrownIdentify(502, { error: '<html>Bad Gateway</html>' })),
      ],
      [
        '200 comparison_failed LLM_UNAVAILABLE',
        () =>
          mockIdentifyFromImages.mockResolvedValue({
            success: false,
            action: 'comparison_failed',
            error: 'x',
            code: 'LLM_UNAVAILABLE',
            products: IDENTIFIED,
          }),
      ],
    ];
    for (const [label, arrange] of engine) {
      mockIdentifyFromImages.mockReset();
      arrange();
      const nav = makeCameraNavigation();
      const r = await renderCamera(nav);
      const root = r.getByTestId('results-empty-state');
      const buttons = buttonsUnder(root);
      expect({
        label,
        title: r.queryByText(s.engineTitle) !== null,
        body: r.queryByText(s.engineBody) !== null,
        buttons: buttons.map((b: any) => allText(b.children).join('')),
        newIds: idsUnder(root).filter((id) => NEW_IDS.includes(id)),
        timeout: r.queryByTestId('results-timeout-state') !== null,
      }).toEqual({ label, title: true, body: true, buttons: [s.back], newIds: [], timeout: false });
      fireEvent.press(buttons[0]);
      expect(nav.goBack).toHaveBeenCalledTimes(1);
      expect(nav.popTo).not.toHaveBeenCalled();
      r.unmount();
    }

    const timeout: [string, any][] = [
      ['thrown bare 503 {}', thrownIdentify(503, {})],
      [
        'the identify watchdog',
        Object.assign(new Error('identify_timeout'), {
          code: 'TIMEOUT',
          response: { status: 503, data: { code: 'TIMEOUT' } },
        }),
      ],
      ['thrown 503 FEATURE_DISABLED', thrownIdentify(503, { success: false, error: 'x', code: 'FEATURE_DISABLED' })],
    ];
    for (const [label, err] of timeout) {
      mockIdentifyFromImages.mockReset();
      mockIdentifyFromImages.mockRejectedValue(err);
      const r = await renderCamera(makeCameraNavigation());
      const root = r.getByTestId('results-empty-state');
      expect({
        label,
        timeout: r.queryByTestId('results-timeout-state') !== null,
        retry: r.queryByTestId('results-timeout-retry') !== null,
        newIds: idsUnder(root).filter((id) => NEW_IDS.includes(id)),
        engine: r.queryByText(s.engineTitle) !== null,
      }).toEqual({ label, timeout: true, retry: true, newIds: [], engine: false });
      r.unmount();
    }

    mockIdentifyFromImages.mockReset();
    const detail = { code: 'USAGE_LIMIT', used: 3 };
    mockIdentifyFromImages.mockRejectedValue(
      Object.assign(new Error('Usage limit reached'), { code: 'USAGE_LIMIT', detail }),
    );
    const nav = makeCameraNavigation();
    const r = await renderCamera(nav);
    expect(nav.navigate).toHaveBeenCalledWith('Paywall', { initialUsage: detail });
    expect(NEW_IDS.filter((id) => r.queryByTestId(id) !== null)).toEqual([]);
    r.unmount();
  }, ROW_MS);

  it('P1(d) pin: the camera 500 and 200 comparison_failed screens keep their texts and testIDs (golden)', async () => {
    const cases: [string, () => void][] = [
      [
        'thrown-500',
        () =>
          mockIdentifyFromImages.mockRejectedValue(
            thrownIdentify(500, { success: false, error: 'x', code: 'SERVER_ERROR', request_id: 'r' }),
          ),
      ],
      [
        '200-failed-llm',
        () =>
          mockIdentifyFromImages.mockResolvedValue({
            success: false,
            action: 'comparison_failed',
            error: 'x',
            code: 'LLM_UNAVAILABLE',
            products: IDENTIFIED,
          }),
      ],
      [
        '200-failed-nocode',
        () =>
          mockIdentifyFromImages.mockResolvedValue({
            success: false,
            action: 'comparison_failed',
            error: 'x',
            products: IDENTIFIED,
          }),
      ],
    ];
    const got: Record<string, { texts: string[]; ids: string[] }> = {};
    for (const lang of ['en', 'ar'] as const) {
      for (const [name, arrange] of cases) {
        mockLang = lang;
        mockIdentifyFromImages.mockReset();
        arrange();
        const r = await renderCamera(makeCameraNavigation());
        const root = r.getByTestId('results-empty-state');
        got[`${name}-${lang}`] = { texts: allText(root.children), ids: idsUnder(root) };
        r.unmount();
      }
    }
    expect(got).toEqual(P1D_GOLDEN);
  }, ROW_MS);
});

// ------------------------------------------------------------------ link --

describe('INC-C1 link rows (HomeScreen, real timers)', () => {
  let alertSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.useRealTimers();
    resetCommon();
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

  /** Mount, switch to type mode, submit a pair, return the stream handlers. */
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
      shell.props.onSubmit('Fragrance A', 'Fragrance B');
    });
    return handlers;
  }

  const LINK_ROWS: [string | null, number][] = [
    ['STORE_UNREADABLE', 22],
    ['NOT_PRODUCT_PAGE', 23],
    ['UNRESOLVED_PRODUCT', 24],
    ['BAD_REQUEST', 25],
    [null, 25],
  ];

  it('L1 link refusals by code on both arms (thrown 400, 200 success:false), codeless too: the link title, the code\'s sentence, Cancel and Type the names; Type the names opens type mode', async () => {
    for (const lang of ['en', 'ar'] as const) {
      const s = say(lang);
      for (const [code, row] of LINK_ROWS) {
        for (const arm of ['thrown', 'success:false'] as const) {
          const label = `${lang} ${code ?? 'codeless'} ${arm}`;
          mockLang = lang;
          alertSpy.mockClear();
          mockApiPost.mockReset();
          if (arm === 'thrown') {
            mockApiPost.mockRejectedValueOnce(
              code
                ? axiosError(400, { success: false, code, error: 'prose', request_id: 'r' })
                : axiosError(400, '<html>x</html>'),
            );
          } else {
            mockApiPost.mockResolvedValueOnce({
              data: code ? { success: false, code, error: 'prose' } : { success: false, error: 'prose' },
            });
          }
          const rendered = render(<HomeScreen navigation={makeHomeNavigation() as any} />);
          await submitUrlCompare(rendered);
          await waitFor(() => expect(alertSpy).toHaveBeenCalled());
          expect({ label, calls: alertSpy.mock.calls }).toEqual({
            label,
            calls: [
              [
                s.linkTitle,
                s.row(row),
                [
                  { text: s.cancel, style: 'cancel' },
                  { text: s.typeNames, onPress: expect.any(Function) },
                ],
              ],
            ],
          });
          const buttons: any[] = alertSpy.mock.calls[0][2];
          await act(async () => {
            buttons[1].onPress();
          });
          expect({ label, type: selected(rendered, 'home-mode-type') }).toEqual({
            label,
            type: { selected: true },
          });
          rendered.unmount();
        }
      }
    }
  }, ROW_MS);

  it('L2 pin: every other link answer and the text path keep today\'s two-argument alert or navigation', async () => {
    const cases: [string, any, string[]][] = [
      [
        'TIMEOUT 503',
        axiosError(503, { success: false, error: 'x', code: 'TIMEOUT', request_id: 'r' }),
        [EN['common.error'], EN['home.errors.timeout']],
      ],
      [
        'CATEGORY_NOT_LIVE 400',
        axiosError(400, { success: false, error: 'x', code: 'CATEGORY_NOT_LIVE', request_id: 'r' }),
        [EN['home.categories.fragrancesOnly'], EN['home.errors.categoryNotLive']],
      ],
      [
        'LLM_UNAVAILABLE 503',
        axiosError(503, { success: false, error: 'x', code: 'LLM_UNAVAILABLE', request_id: 'r' }),
        [EN['home.errors.engineUnavailable.title'], EN['home.errors.engineUnavailable.body']],
      ],
      [
        'RATE_LIMITED 429 + retry_after_seconds 5',
        axiosError(429, {
          success: false,
          error: 'x',
          code: 'RATE_LIMITED',
          retry_after_seconds: 5,
          request_id: 'r',
        }),
        [EN['common.error'], EN['home.errors.rateLimited']],
      ],
      [
        'INSUFFICIENT_DATA 400 + reason same_identity',
        axiosError(400, {
          success: false,
          error: 'x',
          code: 'INSUFFICIENT_DATA',
          reason: 'same_identity',
          request_id: 'r',
        }),
        [EN['common.error'], EN['home.errors.insufficientDataReason.same_identity']],
      ],
      [
        'AUTH_REQUIRED 401',
        axiosError(401, { success: false, error: 'x', code: 'AUTH_REQUIRED', request_id: 'r' }),
        [EN['common.error'], EN['home.errors.comparison']],
      ],
      [
        'codeless edge 502',
        axiosError(502, '<html><body>Bad gateway</body></html>'),
        [EN['home.errors.engineUnavailable.title'], EN['home.errors.engineUnavailable.body']],
      ],
    ];
    for (const [label, err, args] of cases) {
      expect(args.every((x) => typeof x === 'string' && x.length > 0)).toBe(true);
      alertSpy.mockClear();
      mockApiPost.mockReset();
      mockApiPost.mockRejectedValueOnce(err);
      const rendered = render(<HomeScreen navigation={makeHomeNavigation() as any} />);
      await submitUrlCompare(rendered);
      await waitFor(() => expect(alertSpy).toHaveBeenCalled());
      expect({ label, calls: alertSpy.mock.calls }).toEqual({ label, calls: [args] });
      rendered.unmount();
    }

    // USAGE_LIMIT 429 on the link path: the paywall, no alert.
    alertSpy.mockClear();
    mockApiPost.mockReset();
    const usage = { success: false, error: 'x', code: 'USAGE_LIMIT', tier: 'free', request_id: 'r' };
    mockApiPost.mockRejectedValueOnce(axiosError(429, usage));
    const navigation = makeHomeNavigation();
    const paywalled = render(<HomeScreen navigation={navigation as any} />);
    await submitUrlCompare(paywalled);
    await waitFor(() => expect(navigation.navigate).toHaveBeenCalledWith('Paywall', { initialUsage: usage }));
    expect(alertSpy).not.toHaveBeenCalled();
    paywalled.unmount();

    // The text path keeps today's copy for BAD_REQUEST (the link map stays off it).
    alertSpy.mockClear();
    const textRender = render(<HomeScreen navigation={makeHomeNavigation() as any} />);
    const handlers = await submitTextCompare(textRender);
    expect(handlers).not.toBeNull();
    await act(async () => {
      handlers.onError(axiosError(400, { success: false, error: 'x', code: 'BAD_REQUEST', request_id: 'r' }));
    });
    expect(alertSpy.mock.calls).toEqual([[EN['common.error'], EN['home.errors.comparison']]]);
    textRender.unmount();
  }, ROW_MS);

  it('P1(c) pin: the text-path alerts for TIMEOUT 503, LLM_UNAVAILABLE 503, INSUFFICIENT_DATA + reason, RATE_LIMITED + retry_after_seconds (golden)', async () => {
    const cases: [string, any][] = [
      ['TIMEOUT 503', axiosError(503, { success: false, error: 'x', code: 'TIMEOUT', request_id: 'r' })],
      [
        'LLM_UNAVAILABLE 503',
        axiosError(503, { success: false, error: 'x', code: 'LLM_UNAVAILABLE', request_id: 'r' }),
      ],
      [
        'INSUFFICIENT_DATA same_identity',
        axiosError(400, {
          success: false,
          error: 'x',
          code: 'INSUFFICIENT_DATA',
          reason: 'same_identity',
          request_id: 'r',
        }),
      ],
      [
        'RATE_LIMITED 5 s',
        axiosError(429, {
          success: false,
          error: 'x',
          code: 'RATE_LIMITED',
          retry_after_seconds: 5,
          request_id: 'r',
        }),
      ],
    ];
    const got: Record<string, string[]> = {};
    for (const lang of ['en', 'ar'] as const) {
      for (const [name, err] of cases) {
        mockLang = lang;
        alertSpy.mockClear();
        const rendered = render(<HomeScreen navigation={makeHomeNavigation() as any} />);
        const handlers = await submitTextCompare(rendered);
        await act(async () => {
          handlers.onError(err);
        });
        got[`${name}-${lang}`] = alertSpy.mock.calls[0];
        rendered.unmount();
      }
    }
    expect(got).toEqual(P1C_GOLDEN);
  }, ROW_MS);
});
