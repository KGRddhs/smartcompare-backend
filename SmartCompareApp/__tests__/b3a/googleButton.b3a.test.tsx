/**
 * S79 B3-A item 6 -- the Google button, offlineAccess, Google sign-out /
 * revoke (spec C6, rows R39-R48; rulings A4, A6, A7, A12 (MR7, MR8), A16).
 *
 * Screens render against a mocked authService; the service rows load the
 * REAL module with jest.requireActual (its api / google-signin / sentry
 * dependencies resolve to this file's mocks).
 */
/* eslint-disable @typescript-eslint/no-require-imports */

import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';
import { TERMS_VERSION } from '../../src/services/consent';

jest.mock('react-native-reanimated', () => {
  const RealReact = require('react');
  const passthrough = ({ children, ...props }: any) => RealReact.createElement('mock-Animated-View', props, children);
  return {
    __esModule: true,
    default: { View: passthrough, Text: passthrough },
    FadeIn: { duration: () => ({ delay: () => ({}) }), delay: () => ({}) },
    FadeInDown: { duration: () => ({ delay: () => ({}) }), delay: () => ({}) },
    useSharedValue: (init: any) => ({ value: init }),
    useAnimatedStyle: (fn: any) => fn(),
    withTiming: (v: any) => v,
    withRepeat: (a: any) => a,
    withDelay: (_: any, a: any) => a,
    withSequence: (...a: any[]) => a[a.length - 1],
    runOnJS: (fn: any) => fn,
    Easing: { inOut: () => (t: number) => t, out: () => (t: number) => t, ease: (t: number) => t, cubic: (t: number) => t },
  };
});

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en', changeLanguage: jest.fn() },
  }),
}));

jest.mock('expo-screen-capture', () => ({ usePreventScreenCapture: jest.fn() }));

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

const mockGs = {
  configure: jest.fn(),
  hasPlayServices: jest.fn().mockResolvedValue(true),
  signIn: jest.fn(),
  hasPreviousSignIn: jest.fn(() => true),
  signOut: jest.fn(() => Promise.resolve(null)),
  revokeAccess: jest.fn(() => Promise.resolve(null)) as any,
};
// `virtual: true` like the four older Google suites (b4, w3-3, w3-16, a8): jest resolves a
// virtual and a non-virtual mock of the same installed module to different module ids, and
// the shared per-worker resolver cache then hands the SECOND file in a worker the other
// file's resolution (measured 2026-10-18: either file fails when it runs second).
jest.mock('@react-native-google-signin/google-signin', () => ({ GoogleSignin: mockGs }), { virtual: true });

jest.mock('@sentry/react-native', () => ({
  addBreadcrumb: jest.fn(),
  captureMessage: jest.fn(),
  captureException: jest.fn(),
  init: jest.fn(),
}));

jest.mock('../../src/services/deviceFingerprint', () => ({
  getDeviceFingerprint: jest.fn().mockResolvedValue('f'.repeat(64)),
}));

const mockPost = jest.fn();
const mockApiDelete = jest.fn();
jest.mock('../../src/services/api', () => ({
  __esModule: true,
  default: {
    post: (...a: any[]) => mockPost(...a),
    delete: (...a: any[]) => mockApiDelete(...a),
    get: jest.fn(),
    put: jest.fn(),
  },
  API_BASE_URL: 'https://test.invalid',
  getInFlightRefresh: () => null,
  getOrStartRefresh: jest.fn(() => Promise.resolve(null)),
  parseApiError: (err: any) => ({ message: err?.message ?? 'error', code: null }),
  updateProfile: jest.fn(),
}));

const mockRevoke = jest.fn();
const mockClearSession = jest.fn();
jest.mock('../../src/services/authService', () => ({
  login: jest.fn(),
  register: jest.fn(),
  requestPasswordReset: jest.fn(),
  signInWithGoogle: jest.fn(),
  signInWithApple: jest.fn(),
  isAppleSignInAvailable: jest.fn().mockResolvedValue(true),
  getSavedUser: jest.fn().mockResolvedValue({ id: 'u1', display_name: 'K', email: 'k@example.com' }),
  clearSession: (...a: any[]) => mockClearSession(...a),
  updateSavedUserDisplayName: jest.fn(),
  getToken: jest.fn().mockResolvedValue(null),
  refreshSession: jest.fn(),
  revokeGoogleAccessBestEffort: (...a: any[]) => mockRevoke(...a),
}));

const mockFetch = jest.fn();
(global as any).fetch = mockFetch;

const RN = require('react-native');
const SecureStore = require('expo-secure-store');
const LoginScreen = require('../../src/screens/LoginScreen').default;
const RegisterScreen = require('../../src/screens/RegisterScreen').default;
const { Step16Account } = require('../../src/screens/onboarding/Step16Account');
const EditProfileScreen = require('../../src/screens/EditProfileScreen').default;
const realAuth = () => jest.requireActual('../../src/services/authService');

const GOOGLE_FILLS = ['#34A853', '#4285F4', '#EA4335', '#FBBC05'];

function makeNavigation(): any {
  return { navigate: jest.fn(), goBack: jest.fn(), canGoBack: () => false, getParent: () => ({ navigate: jest.fn() }) };
}

function flat(style: any): Record<string, any> {
  return Object.assign({}, ...([] as any[]).concat(style ?? []).flat(Infinity).filter(Boolean));
}

/** Pre-order list of {testID | 'TextInput'} markers of a JSON tree. */
function order(json: any): string[] {
  const out: string[] = [];
  const walk = (n: any) => {
    if (n == null || typeof n !== 'object') return;
    if (Array.isArray(n)) return n.forEach(walk);
    if (n.type === 'TextInput') out.push('<TextInput>');
    if (n.props && typeof n.props.testID === 'string') out.push(n.props.testID);
    walk(n.children);
  };
  walk(json);
  return out;
}

function findJson(json: any, pred: (n: any) => boolean): any | null {
  let hit: any = null;
  const walk = (n: any) => {
    if (hit || n == null || typeof n !== 'object') return;
    if (Array.isArray(n)) return n.forEach(walk);
    if (pred(n)) {
      hit = n;
      return;
    }
    walk(n.children);
  };
  walk(json);
  return hit;
}

function parentOf(json: any, child: any): any | null {
  return findJson(json, (n) => Array.isArray(n.children) && n.children.includes(child));
}

function allNodes(n: any, out: any[] = []): any[] {
  if (n == null || typeof n !== 'object') return out;
  if (Array.isArray(n)) {
    n.forEach((c) => allNodes(c, out));
    return out;
  }
  out.push(n);
  allNodes(n.children, out);
  return out;
}

const textChildren = (n: any): string =>
  (n.children ?? []).filter((c: any) => typeof c === 'string').join('');

function expectOfficialGlyph(sub: any) {
  const nodes = allNodes(sub);
  const svg = nodes.find((n) => n.type === 'Svg' && n.props?.testID === 'google-glyph');
  expect(svg).toBeTruthy();
  const fills = allNodes(svg)
    .filter((n) => n.type === 'Path')
    .map((n) => String(n.props.fill).toUpperCase())
    .sort();
  expect(fills).toEqual(GOOGLE_FILLS);
  const typedG = nodes.filter((n) => n.type === 'Text' && textChildren(n).trim() === 'G');
  expect(typedG).toHaveLength(0);
}

const originalOS = RN.Platform.OS;
beforeEach(() => {
  jest.clearAllMocks();
  RN.Platform.OS = 'ios';
  mockGs.hasPreviousSignIn.mockImplementation(() => true);
  mockGs.signOut.mockImplementation(() => Promise.resolve(null));
  mockGs.revokeAccess = jest.fn(() => Promise.resolve(null));
  mockPost.mockResolvedValue({ data: { success: true } });
  SecureStore.__reset();
});
afterAll(() => {
  RN.Platform.OS = originalOS;
});

describe('B3-A Google button layout (C6)', () => {
  it('r39 Login: Apple, then Google on its own full-width row, then Email, then the fields', async () => {
    const s = render(<LoginScreen navigation={makeNavigation()} onLoginSuccess={jest.fn()} />);
    await s.findByTestId('login-social-apple');
    const json = s.toJSON();
    const wanted = ['login-social-apple', 'login-social-google', 'login-social-email', 'login-email-input'];
    const o = order(json).filter((id) => wanted.includes(id));
    expect(o.filter((id, i) => o.indexOf(id) === i)).toEqual(wanted);
    const g = findJson(json, (n) => n.props?.testID === 'login-social-google');
    const row = parentOf(json, g);
    const rowIds = order(row);
    expect(rowIds.filter((id) => /^login-social-(apple|email)/.test(id))).toEqual([]);
    const st = flat(g.props.style);
    expect(Number(st.minHeight ?? st.height ?? 0)).toBeGreaterThanOrEqual(48);
  });

  it('r40 Google shows the official logo, not a typed G (Login)', async () => {
    const s = render(<LoginScreen navigation={makeNavigation()} onLoginSuccess={jest.fn()} />);
    await s.findByTestId('login-social-apple');
    const g = findJson(s.toJSON(), (n) => n.props?.testID === 'login-social-google');
    expectOfficialGlyph(g);
  });

  it('r41 the Google label cannot be clipped by a fixed line height', async () => {
    const s = render(<LoginScreen navigation={makeNavigation()} onLoginSuccess={jest.fn()} />);
    await s.findByTestId('login-social-apple');
    const g = findJson(s.toJSON(), (n) => n.props?.testID === 'login-social-google');
    const label = allNodes(g).find((n) => n.type === 'Text' && textChildren(n) === 'auth.googleSignIn');
    expect(label).toBeTruthy();
    const st = flat(label.props.style);
    expect(Number(st.fontSize)).toBeGreaterThanOrEqual(15);
    if (st.lineHeight !== undefined) expect(Number(st.lineHeight)).toBeGreaterThanOrEqual(1.2 * Number(st.fontSize));
  });

  it('r42 Register: Apple first, then Google (logo), then the form', async () => {
    const s = render(
      <RegisterScreen navigation={makeNavigation()} route={{ params: undefined }} onRegisterSuccess={jest.fn()} />,
    );
    await s.findByTestId('register-social-apple');
    const json = s.toJSON();
    const wanted = ['register-social-apple', 'register-social-google', '<TextInput>'];
    const o = order(json).filter((id) => wanted.includes(id));
    expect(o.filter((id, i) => o.indexOf(id) === i)).toEqual(wanted);
    const g = findJson(json, (n) => n.props?.testID === 'register-social-google');
    expectOfficialGlyph(g);
  });

  it('r42b (A7 / MR7) a blocked Create Account brings the consent error into view next to the button', async () => {
    const s = render(
      <RegisterScreen navigation={makeNavigation()} route={{ params: undefined }} onRegisterSuccess={jest.fn()} />,
    );
    await s.findByTestId('register-social-apple');
    fireEvent.changeText(s.getByPlaceholderText('auth.email'), 'new@user.bh');
    fireEvent.changeText(s.getByPlaceholderText('auth.password'), 'StrongPass1x');
    fireEvent.changeText(s.getByPlaceholderText('auth.confirmPassword'), 'StrongPass1x');
    await act(async () => {
      fireEvent.press(s.getByText('auth.register'));
    });
    const o = order(s.toJSON());
    const near = o.indexOf('register-submit-consent-error');
    expect(near).toBeGreaterThanOrEqual(0);
    expect(near).toBeGreaterThan(o.lastIndexOf('<TextInput>'));
  });

  it('r43 Step16Account uses the logo', () => {
    const s = render(<Step16Account onSelectMethod={jest.fn()} />);
    const g = findJson(s.toJSON(), (n) => n.props?.testID === 'account-google');
    expectOfficialGlyph(g);
  });
});

describe('B3-A Google session (C6, service)', () => {
  it('r44 configure no longer asks for offline access; the client ids are unchanged', () => {
    realAuth().configureGoogleSignIn();
    expect(mockGs.configure).toHaveBeenCalledTimes(1);
    const arg = mockGs.configure.mock.calls[0][0];
    expect(arg.offlineAccess).not.toBe(true);
    expect(arg.webClientId).toBe('21336192767-i9prqks93nrdmb9rg7ho2v1md9bgqgsv.apps.googleusercontent.com');
    expect(arg.iosClientId).toBe('21336192767-38hi4t1ac23089iau7jdog1f43oc7rdm.apps.googleusercontent.com');
  });

  async function settle() {
    for (let i = 0; i < 5; i += 1) await new Promise((r) => setTimeout(r, 0));
  }
  async function logoutWithin(ms = 1500): Promise<string> {
    return Promise.race([
      realAuth().logout().then(() => 'done'),
      new Promise<string>((r) => setTimeout(() => r('timeout'), ms)),
    ]);
  }
  const logoutPosts = () => mockPost.mock.calls.filter(([u]) => u === '/api/v1/auth/logout');

  it('r45 logout signs out of Google only when a Google session exists, without delaying logout', async () => {
    await SecureStore.setItemAsync('qaren_token', 'tok-1');
    expect(await logoutWithin()).toBe('done');
    await settle();
    expect(mockGs.signOut).toHaveBeenCalledTimes(1);

    jest.clearAllMocks();
    mockGs.hasPreviousSignIn.mockImplementation(() => false);
    await SecureStore.setItemAsync('qaren_token', 'tok-2');
    expect(await logoutWithin()).toBe('done');
    await settle();
    expect(mockGs.signOut).toHaveBeenCalledTimes(0);

    jest.clearAllMocks();
    mockGs.hasPreviousSignIn.mockImplementation(() => true);
    mockGs.signOut.mockImplementation(() => Promise.reject(new Error('sdk')));
    await SecureStore.setItemAsync('qaren_token', 'tok-3');
    expect(await logoutWithin()).toBe('done');
    await settle();
    expect(logoutPosts()).toHaveLength(1);
    expect(mockGs.signOut).toHaveBeenCalledTimes(1);

    jest.clearAllMocks();
    mockGs.signOut.mockImplementation(() => new Promise(() => undefined));
    await SecureStore.setItemAsync('qaren_token', 'tok-4');
    expect(await logoutWithin()).toBe('done');
    await settle();
    expect(logoutPosts()).toHaveLength(1);
    expect(mockGs.signOut).toHaveBeenCalledTimes(1);
  });

  it('r45b (MR8) the Google sign-out also fires with no stored token and when the server POST rejects', async () => {
    expect(await logoutWithin()).toBe('done');
    await settle();
    expect(logoutPosts()).toHaveLength(0);
    expect(mockGs.signOut).toHaveBeenCalledTimes(1);

    jest.clearAllMocks();
    mockPost.mockRejectedValue(new Error('net'));
    await SecureStore.setItemAsync('qaren_token', 'tok-5');
    expect(await logoutWithin()).toBe('done');
    await settle();
    expect(mockGs.signOut).toHaveBeenCalledTimes(1);
  });

  // Fix round FA2 / FA5: ruling A6 (logout clears the onboarding resume
  // record) pinned on every logout path, and the clear is bounded.
  const RESUME_KEY = '@qaren_onboarding_resume_v1';
  const asyncStorage = () => require('@react-native-async-storage/async-storage').default;
  const plantResume = () =>
    asyncStorage().setItem(
      RESUME_KEY,
      JSON.stringify({ v: 1, step: 3, data: { language: 'ar' }, saved_at: Date.now() }),
    );

  it('r45c (FA2) logout leaves the onboarding resume record null on the token, no-token and POST-rejecting paths', async () => {
    await plantResume();
    await SecureStore.setItemAsync('qaren_token', 'tok-r45c-1');
    expect(await logoutWithin()).toBe('done');
    await settle();
    const afterToken = await asyncStorage().getItem(RESUME_KEY);
    expect(logoutPosts()).toHaveLength(1);

    await plantResume();
    expect(await logoutWithin()).toBe('done');
    await settle();
    const afterNoToken = await asyncStorage().getItem(RESUME_KEY);

    mockPost.mockRejectedValue(new Error('net'));
    await plantResume();
    await SecureStore.setItemAsync('qaren_token', 'tok-r45c-2');
    expect(await logoutWithin()).toBe('done');
    await settle();
    const afterReject = await asyncStorage().getItem(RESUME_KEY);

    expect({ afterToken, afterNoToken, afterReject }).toEqual({
      afterToken: null,
      afterNoToken: null,
      afterReject: null,
    });
  });

  it('r45d (FA5) a never-settling removeItem for the resume key does not hold logout beyond 1 s', async () => {
    const AS = asyncStorage();
    const origRemove = AS.removeItem;
    AS.removeItem = jest.fn((k: string, ...rest: unknown[]) =>
      k === RESUME_KEY ? new Promise(() => undefined) : origRemove.call(AS, k, ...rest),
    );
    jest.useFakeTimers();
    try {
      let settled = false;
      void realAuth()
        .logout()
        .then(() => {
          settled = true;
        });
      await jest.advanceTimersByTimeAsync(1000);
      expect(settled).toBe(true);
      expect(AS.removeItem).toHaveBeenCalledWith(RESUME_KEY);
    } finally {
      jest.useRealTimers();
      AS.removeItem = origRemove;
    }
  });

  it('r46 revokeGoogleAccessBestEffort is bounded and fail-soft', async () => {
    const fn = realAuth().revokeGoogleAccessBestEffort;
    expect(typeof fn).toBe('function');
    await expect(fn()).resolves.toBeUndefined();
    expect(mockGs.revokeAccess).toHaveBeenCalledTimes(1);

    mockGs.revokeAccess = jest.fn(() => Promise.reject(new Error('disconnect')));
    await expect(fn()).resolves.toBeUndefined();

    mockGs.hasPreviousSignIn.mockImplementation(() => false);
    mockGs.revokeAccess = jest.fn(() => Promise.resolve(null));
    await fn();
    expect(mockGs.revokeAccess).toHaveBeenCalledTimes(0);

    mockGs.hasPreviousSignIn.mockImplementation(() => true);
    mockGs.revokeAccess = undefined;
    await expect(fn()).resolves.toBeUndefined();

    jest.useFakeTimers();
    try {
      mockGs.revokeAccess = jest.fn(() => new Promise(() => undefined));
      let settled = false;
      void fn().then(() => {
        settled = true;
      });
      await jest.advanceTimersByTimeAsync(3000);
      expect(settled).toBe(true);
    } finally {
      jest.useRealTimers();
    }
  });

  it('r48 [PIN] Google request body unchanged: provider, id_token and the consent keys only', async () => {
    mockGs.signIn.mockResolvedValue({ data: { idToken: 'header.payload.signature' } });
    mockFetch.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true, user: { id: 'u1' }, session: { access_token: 't', refresh_token: 'r' } }),
    });
    const consent = { terms_accepted: true as const, terms_version: TERMS_VERSION, age_attested: true as const };
    await realAuth().signInWithGoogle(consent);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(Object.keys(body).sort()).toEqual(['age_attested', 'id_token', 'provider', 'terms_accepted', 'terms_version']);
    expect(body.provider).toBe('google');
  });
});

describe('B3-A account deletion revokes Google (C6)', () => {
  async function confirmDelete(props: any) {
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => undefined);
    const s = render(<EditProfileScreen {...props} />);
    fireEvent.press(s.getByTestId('edit-delete-account-row'));
    const buttons = alertSpy.mock.calls[0][2] as any[];
    const destructive = buttons.find((b: any) => b.style === 'destructive');
    await act(async () => {
      await destructive.onPress();
    });
    alertSpy.mockRestore();
    return s;
  }
  const makeProps = (log: string[]) => ({
    navigation: { goBack: jest.fn(), navigate: jest.fn() },
    route: { params: undefined, key: 'EditProfile', name: 'EditProfile' as const },
    onAccountDeleted: jest.fn(() => log.push('deleted')),
  });

  it('r47 a successful DELETE revokes Google after clearSession and before onAccountDeleted; a failed DELETE never does', async () => {
    const log: string[] = [];
    mockApiDelete.mockResolvedValue({ data: { success: true } });
    mockClearSession.mockImplementation(async () => {
      log.push('clear');
    });
    mockRevoke.mockImplementation(() => {
      log.push('revoke');
      return Promise.resolve();
    });
    await confirmDelete(makeProps(log));
    await waitFor(() => expect(log).toContain('deleted'));
    expect(log).toEqual(['clear', 'revoke', 'deleted']);

    jest.clearAllMocks();
    const log2: string[] = [];
    mockApiDelete.mockRejectedValue(new Error('Request failed with status code 502'));
    const props2 = makeProps(log2);
    await confirmDelete(props2);
    expect(mockRevoke).not.toHaveBeenCalled();
    expect(props2.onAccountDeleted).not.toHaveBeenCalled();
  });

  it('r47b [PIN] with the authService mock WITHOUT the export the deletion still completes', async () => {
    const mod = require('../../src/services/authService');
    const saved = mod.revokeGoogleAccessBestEffort;
    delete mod.revokeGoogleAccessBestEffort;
    try {
      const log: string[] = [];
      mockApiDelete.mockResolvedValue({ data: { success: true } });
      mockClearSession.mockResolvedValue(undefined);
      const props = makeProps(log);
      await confirmDelete(props);
      await waitFor(() => expect(props.onAccountDeleted).toHaveBeenCalledTimes(1));
    } finally {
      mod.revokeGoogleAccessBestEffort = saved;
    }
  });

  it('r47c (FA3) a never-settling revoke is not awaited: onAccountDeleted runs once right after clearSession', async () => {
    const log: string[] = [];
    mockApiDelete.mockResolvedValue({ data: { success: true } });
    mockClearSession.mockImplementation(async () => {
      log.push('clear');
    });
    mockRevoke.mockImplementation(() => {
      log.push('revoke');
      return new Promise(() => undefined);
    });
    const props = makeProps(log);
    const alertSpy = jest.spyOn(RN.Alert, 'alert').mockImplementation(() => undefined);
    try {
      const s = render(<EditProfileScreen {...props} />);
      fireEvent.press(s.getByTestId('edit-delete-account-row'));
      const buttons = alertSpy.mock.calls[0][2] as any[];
      const destructive = buttons.find((b: any) => b.style === 'destructive');
      await act(async () => {
        void destructive.onPress();
        for (let i = 0; i < 5; i += 1) await new Promise((r) => setTimeout(r, 0));
      });
    } finally {
      alertSpy.mockRestore();
    }
    expect(props.onAccountDeleted).toHaveBeenCalledTimes(1);
    expect(log).toEqual(['clear', 'revoke', 'deleted']);
  });
});
