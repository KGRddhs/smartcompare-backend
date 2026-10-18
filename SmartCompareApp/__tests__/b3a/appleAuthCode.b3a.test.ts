/**
 * S79 B3-A item 7 -- Apple authorization code on /social-login (spec C7,
 * rows R49-R51; rulings A2 (R51 runs with __DEV__ true) and A18 (the field
 * is `authorization_code`, Apple only, only a non-empty string)).
 *
 * Harness of services/authService.consent.w3-16.test.ts.
 */
/* eslint-disable @typescript-eslint/no-require-imports */

import { TERMS_VERSION } from '../../src/services/consent';

jest.mock('../../src/services/api', () => ({
  __esModule: true,
  default: { post: jest.fn(), get: jest.fn(), put: jest.fn(), delete: jest.fn() },
  API_BASE_URL: 'https://test.invalid',
  getOrStartRefresh: jest.fn(),
  getInFlightRefresh: () => null,
}));

jest.mock('../../src/services/deviceFingerprint', () => ({
  getDeviceFingerprint: jest.fn().mockResolvedValue('f'.repeat(64)),
}));

const mockAppleSignInAsync = jest.fn();
jest.mock(
  'expo-apple-authentication',
  () => ({
    signInAsync: (...args: unknown[]) => mockAppleSignInAsync(...args),
    isAvailableAsync: jest.fn().mockResolvedValue(true),
    AppleAuthenticationScope: { FULL_NAME: 0, EMAIL: 1 },
  })
);

jest.mock('expo-crypto', () => ({
  getRandomBytesAsync: jest.fn().mockResolvedValue(new Uint8Array(32)),
  digestStringAsync: jest.fn().mockResolvedValue('a'.repeat(64)),
  CryptoDigestAlgorithm: { SHA256: 'SHA-256' },
}));

const mockSentry = {
  addBreadcrumb: jest.fn(),
  captureMessage: jest.fn(),
  captureException: jest.fn(),
  init: jest.fn(),
};
jest.mock('@sentry/react-native', () => mockSentry);

const mockFetch = jest.fn();
(global as any).fetch = mockFetch;

const { signInWithApple } = require('../../src/services/authService');

const CONSENT = { terms_accepted: true as const, terms_version: TERMS_VERSION, age_attested: true as const };
const ID_TOKEN = 'header.payload.signature';
const CODE = 'c_test_code';

function sentRaw(): string {
  expect(mockFetch).toHaveBeenCalledTimes(1);
  expect(String(mockFetch.mock.calls[0][0])).toMatch(/\/api\/v1\/auth\/social-login$/);
  return String(mockFetch.mock.calls[0][1].body);
}

beforeEach(() => {
  mockFetch.mockReset();
  mockAppleSignInAsync.mockReset();
  Object.values(mockSentry).forEach((f) => f.mockClear());
  mockFetch.mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ success: true, user: { id: 'u1' }, session: { access_token: 't', refresh_token: 'r' } }),
  });
});

describe('B3-A Apple authorization code (C7)', () => {
  it('r49 Apple sends the authorization code when present', async () => {
    mockAppleSignInAsync.mockResolvedValue({ identityToken: ID_TOKEN, authorizationCode: CODE });
    await signInWithApple(CONSENT);
    const body = JSON.parse(sentRaw());
    expect(typeof body.nonce).toBe('string');
    expect(body).toEqual({
      provider: 'apple',
      id_token: ID_TOKEN,
      nonce: body.nonce,
      authorization_code: CODE,
      ...CONSENT,
    });
  });

  it.each([
    ['undefined', undefined],
    ['null', null],
    ['empty', ''],
    ['non-string', 42],
  ])('r50 [PIN] %s code keeps today\'s bytes', async (_label, code) => {
    mockAppleSignInAsync.mockResolvedValue({ identityToken: ID_TOKEN, authorizationCode: code });
    await signInWithApple(CONSENT);
    const raw = sentRaw();
    const nonce = JSON.parse(raw).nonce;
    expect(raw).toBe(JSON.stringify({ provider: 'apple', id_token: ID_TOKEN, nonce, ...CONSENT }));
  });

  it('r51 [PIN] the code is never logged (console or Sentry), with __DEV__ true', async () => {
    const g = globalThis as any;
    const savedDev = g.__DEV__;
    const spies = [
      jest.spyOn(console, 'log').mockImplementation(() => undefined),
      jest.spyOn(console, 'warn').mockImplementation(() => undefined),
      jest.spyOn(console, 'error').mockImplementation(() => undefined),
    ];
    g.__DEV__ = true;
    try {
      mockAppleSignInAsync.mockResolvedValue({ identityToken: ID_TOKEN, authorizationCode: CODE });
      await signInWithApple(CONSENT);
      const seen: string[] = [];
      const dump = (v: unknown) => {
        try {
          seen.push(typeof v === 'string' ? v : JSON.stringify(v) ?? String(v));
        } catch {
          seen.push(String(v));
        }
      };
      for (const s of spies) s.mock.calls.forEach((args) => args.forEach(dump));
      for (const f of [mockSentry.addBreadcrumb, mockSentry.captureMessage, mockSentry.captureException]) {
        f.mock.calls.forEach((args: unknown[]) => args.forEach(dump));
      }
      // Positive control: the __DEV__ diagnostic line really ran.
      expect(seen.some((s) => s.includes('[APPLE-DIAG]'))).toBe(true);
      expect(seen.filter((s) => s.includes(CODE))).toEqual([]);
    } finally {
      g.__DEV__ = savedDev;
      spies.forEach((s) => s.mockRestore());
    }
  });
});
