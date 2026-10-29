/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * S81-08 CLIENT-FIRST-OTA RED - rows D1..D6: streamComparison (spec section 5
 * as amended by RULINGS_S81_08: R-S08-1 one id per compare attempt shared by
 * the SSE request and its single REST fallback, exposed as compareRequestId;
 * R-S08-4 amended: NO legacy header on the stream; R-S08-9 / C13: a null id
 * leaves the REST config without a headers key, a builder failure never
 * blocks the stream or triggers the REST fallback).
 *
 * The SSE transport is driven over a mocked `expo/fetch` with real frames;
 * the REST compare over a fake axios instance. Plain jest.mock only. Every RED
 * row fails at base on an assertion. Synthetic values; Date.now pre-cutoff.
 */

import { TextEncoder } from 'util';

const nodeCrypto = require('crypto');

const sha = (s: string): string => nodeCrypto.createHash('sha256').update(s, 'utf8').digest('hex');
const NEW = sha('s81-08-new');
const LEG = sha('s81-08-legacy');
const V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const PRE_CUTOFF_MS = Date.UTC(2026, 9, 23, 12, 0, 0);
const USER_A = 'user-a-synthetic';
const CONSENT_KEY = '@qaren_ai_consent_' + USER_A;

jest.mock('../../src/services/certificatePinning', () => ({ setupCertificatePinning: jest.fn() }));

const mockAuth = {
  getToken: jest.fn(async () => 'bearer-synthetic-1'),
  getSavedUser: jest.fn(async () => ({ id: 'user-a-synthetic' })),
};
jest.mock('../../src/services/authService', () => ({
  getToken: (...a: any[]) => (mockAuth.getToken as any)(...a),
  getSavedUser: (...a: any[]) => (mockAuth.getSavedUser as any)(...a),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
}));

jest.mock('axios', () => {
  const instance: any = {
    get: jest.fn(),
    put: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
    interceptors: { request: { use: jest.fn() }, response: { use: jest.fn() } },
  };
  return { create: jest.fn(() => instance), __instance: instance };
});

jest.mock('expo-image-manipulator', () => ({ manipulateAsync: jest.fn(), SaveFormat: { JPEG: 'jpeg' } }));
jest.mock('expo/fetch', () => ({ fetch: jest.fn() }));
jest.mock('../../src/services/sentry', () => ({
  addSseFallbackBreadcrumb: jest.fn(),
  initSentry: jest.fn(),
  scrubString: (s: string) => s,
  scrubBeforeSend: (e: any) => e,
}));

const mockDF = {
  getDeviceFingerprint: jest.fn(),
  legacyDeviceFingerprintHash: jest.fn(),
  legacyFingerprintHeaderActive: jest.fn(
    (nowMs?: number) => (typeof nowMs === 'number' ? nowMs : Date.now()) < Date.UTC(2027, 2, 31, 21, 0, 0),
  ),
  getDeviceIdentity: jest.fn(),
  LEGACY_FINGERPRINT_HEADER_UNTIL_MS: Date.UTC(2027, 2, 31, 21, 0, 0),
  _resetCacheForTests: jest.fn(),
};
jest.mock('../../src/services/deviceFingerprint', () => mockDF);

const mockUuid: { next: () => string } = { next: () => nodeCrypto.randomUUID() };
jest.mock('expo-crypto', () => ({
  randomUUID: () => mockUuid.next(),
  digestStringAsync: jest.fn(async () => 'f'.repeat(64)),
  CryptoDigestAlgorithm: { SHA256: 'SHA256' },
}));

const mockAsync: any = {
  store: {} as Record<string, string>,
  getItem: jest.fn(async (k: string) => (k in mockAsync.store ? mockAsync.store[k] : null)),
  setItem: jest.fn(async (k: string, v: string) => {
    mockAsync.store[k] = v;
  }),
  removeItem: jest.fn(async (k: string) => {
    delete mockAsync.store[k];
  }),
  multiRemove: jest.fn(async () => undefined),
  clear: jest.fn(async () => undefined),
};
jest.mock('@react-native-async-storage/async-storage', () => ({ __esModule: true, default: mockAsync }));
jest.mock('../../src/services/aiConsent', () => jest.requireActual('../../src/services/aiConsent'));

if (typeof (global as any).TextDecoder === 'undefined') {
  (global as any).TextDecoder = require('util').TextDecoder;
}

const api = require('../../src/services/api');
const consent = require('../../src/services/aiConsent');
const features = require('../../src/config/features');
const axiosInstance = (require('axios') as any).__instance;
const expoFetchMock = (require('expo/fetch') as any).fetch as jest.Mock;

function sseFrame(event: string, data: any): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

function makeFetchStream(frames: string[]) {
  const encoder = new TextEncoder();
  const chunks = frames.map((f) => encoder.encode(f));
  let i = 0;
  return {
    ok: true,
    body: {
      getReader: () => ({
        read: () =>
          i < chunks.length
            ? Promise.resolve({ done: false, value: chunks[i++] })
            : Promise.resolve({ done: true, value: undefined }),
      }),
    },
  };
}

async function flush(times = 30): Promise<void> {
  for (let i = 0; i < times; i++) {
    await new Promise((r) => setImmediate(r));
  }
}

function lowerHeaders(h: any): Record<string, string> {
  const out: Record<string, string> = {};
  for (const k of Object.keys(h || {})) {
    if (h[k] !== undefined && h[k] !== null) out[k.toLowerCase()] = String(h[k]);
  }
  return out;
}

const COMPLETE = { success: true, overview: {}, products: [] };

async function runStream(): Promise<{ handle: any; cbs: any }> {
  const cbs = { onComplete: jest.fn(), onError: jest.fn() };
  let handle: any = null;
  let startError: any = null;
  try {
    handle = api.streamComparison({ product_a: 'Alpha One', product_b: 'Beta Two' });
    handle.subscribe(cbs);
  } catch (e) {
    startError = e;
  }
  expect(startError).toBeNull();
  await flush();
  return { handle, cbs };
}

function restCalls(): any[][] {
  return axiosInstance.get.mock.calls.filter((c: any[]) => c[0] === '/api/v1/text/compare');
}

let dateSpy: jest.SpyInstance | null = null;

beforeEach(() => {
  axiosInstance.get.mockReset();
  axiosInstance.get.mockResolvedValue({ data: COMPLETE });
  expoFetchMock.mockReset();
  mockAuth.getSavedUser.mockReset();
  mockAuth.getSavedUser.mockResolvedValue({ id: USER_A });
  mockDF.getDeviceFingerprint.mockReset();
  mockDF.legacyDeviceFingerprintHash.mockReset();
  mockDF.getDeviceIdentity.mockReset();
  mockDF.getDeviceFingerprint.mockResolvedValue(NEW);
  mockDF.legacyDeviceFingerprintHash.mockResolvedValue(LEG);
  mockDF.getDeviceIdentity.mockResolvedValue({ hash: NEW, source: 'securestore' });
  mockUuid.next = () => nodeCrypto.randomUUID();
  mockAsync.store = { [CONSENT_KEY]: JSON.stringify({ version: consent.AI_CONSENT_VERSION, at: '2026-10-23T12:00:00.000Z' }) };
  features._setExpoFetchSseForTests?.(true);
  dateSpy = jest.spyOn(Date, 'now').mockReturnValue(PRE_CUTOFF_MS);
});

afterEach(() => {
  features._setExpoFetchSseForTests?.(null);
  if (dateSpy) dateSpy.mockRestore();
  dateSpy = null;
});

describe('S81-08 D - stream compare headers and the compare id', () => {
  it('D1 the SSE request carries Accept + Authorization + device + consent + the id, and no legacy header', async () => {
    expoFetchMock.mockResolvedValue(makeFetchStream([sseFrame('complete', COMPLETE)]));
    await runStream();
    expect(expoFetchMock).toHaveBeenCalledTimes(1);
    const h = lowerHeaders(expoFetchMock.mock.calls[0][1].headers);
    expect(h['x-compare-request-id'] ?? '').toMatch(V4);
    expect(h).toEqual({
      accept: 'text/event-stream',
      authorization: 'Bearer bearer-synthetic-1',
      'x-device-fingerprint': NEW,
      'x-ai-consent-version': String(consent.AI_CONSENT_VERSION),
      'x-compare-request-id': h['x-compare-request-id'],
    });
  });

  it('D2 the REST fallback reuses the attempt id; exactly one REST call', async () => {
    expoFetchMock.mockRejectedValue(new Error('stream down'));
    await runStream();
    expect(restCalls()).toHaveLength(1);
    const sseId = lowerHeaders(expoFetchMock.mock.calls[0][1].headers)['x-compare-request-id'];
    const restId = lowerHeaders(restCalls()[0][1]?.headers)['x-compare-request-id'];
    expect(sseId ?? '').toMatch(V4);
    expect(restId).toBe(sseId);
  });

  it('D3 the id is exposed as streamComparison(...).compareRequestId and equals the id sent', async () => {
    expoFetchMock.mockResolvedValue(makeFetchStream([sseFrame('complete', COMPLETE)]));
    const { handle } = await runStream();
    const sent = lowerHeaders(expoFetchMock.mock.calls[0][1].headers)['x-compare-request-id'];
    expect(sent ?? '').toMatch(V4);
    expect(handle.compareRequestId).toBe(sent);
  });

  it('D4 default transport (SSE off): params stay the literal pair and the REST config carries the id', async () => {
    features._setExpoFetchSseForTests?.(false);
    const { handle } = await runStream();
    expect(expoFetchMock).not.toHaveBeenCalled();
    expect(restCalls()).toHaveLength(1);
    const cfg = restCalls()[0][1];
    expect(cfg.params).toEqual({ product_a: 'Alpha One', product_b: 'Beta Two', region: 'bahrain' });
    const id = lowerHeaders(cfg.headers)['x-compare-request-id'];
    expect(id ?? '').toMatch(V4);
    expect(handle.compareRequestId).toBe(id);
  });

  it('D5 one id per attempt: two streamComparison calls send two distinct ids', async () => {
    expoFetchMock.mockImplementation(async () => makeFetchStream([sseFrame('complete', COMPLETE)]));
    await runStream();
    await runStream();
    expect(expoFetchMock).toHaveBeenCalledTimes(2);
    const a = lowerHeaders(expoFetchMock.mock.calls[0][1].headers)['x-compare-request-id'];
    const b = lowerHeaders(expoFetchMock.mock.calls[1][1].headers)['x-compare-request-id'];
    expect(a ?? '').toMatch(V4);
    expect(b ?? '').toMatch(V4);
    expect(a).not.toBe(b);
  });

  it('D6 (PIN, full config) every builder failing: the stream still goes out over expo/fetch and no REST fallback runs', async () => {
    mockDF.getDeviceFingerprint.mockRejectedValue(new Error('device'));
    mockDF.getDeviceIdentity.mockRejectedValue(new Error('device'));
    mockDF.legacyDeviceFingerprintHash.mockRejectedValue(new Error('legacy'));
    mockAuth.getSavedUser.mockRejectedValue(new Error('user'));
    mockUuid.next = () => {
      throw new Error('uuid');
    };
    expoFetchMock.mockResolvedValue(makeFetchStream([sseFrame('complete', COMPLETE)]));
    const { cbs } = await runStream();
    expect(expoFetchMock).toHaveBeenCalledTimes(1);
    expect(lowerHeaders(expoFetchMock.mock.calls[0][1].headers)).toEqual({
      accept: 'text/event-stream',
      authorization: 'Bearer bearer-synthetic-1',
    });
    expect(restCalls()).toHaveLength(0);
    expect(cbs.onComplete).toHaveBeenCalledTimes(1);
    expect(cbs.onError).not.toHaveBeenCalled();
  });
});
