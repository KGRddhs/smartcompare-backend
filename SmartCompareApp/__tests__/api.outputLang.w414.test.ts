/**
 * W4-14 Part A5 — the text compare requests carry `lang=ar` when the app language
 * is Arabic, and NOTHING otherwise (omit-when-unset), read PER CALL from the default
 * `i18next` instance (the one src/i18n/index.ts initialises).
 *
 * The only live compare call is `streamComparison` (HomeScreen): REST
 * `GET /api/v1/text/compare` by default (ENABLE_EXPO_FETCH_SSE off), SSE
 * `/text/compare/stream` over expo/fetch when the feature override is ON.
 * `compareTextPair` has 0 callers: it is covered only by PIN 21 as recorded
 * dead-path coverage (no lang, in any language). `/image/identify` is W4-14b.
 *
 * Mocks follow api.streamComparison.noBodyFallback / .expoFetch. jest gives each
 * test FILE its own module registry, so the default i18next language cannot leak
 * across suites; it is reset between the tests of THIS file (afterEach).
 *
 * RED = fails at the unit base 3985eaac (no request carries a language);
 * PIN = green there and must stay green.
 */
import i18next from 'i18next';

jest.mock('../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));

jest.mock('../src/services/authService', () => ({
  getToken: jest.fn().mockResolvedValue('fake-jwt'),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
}));

jest.mock('axios', () => {
  const instance = {
    get: jest.fn(),
    put: jest.fn(),
    post: jest.fn(),
    delete: jest.fn(),
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  };
  return { create: jest.fn(() => instance), __instance: instance };
});

jest.mock('expo-image-manipulator', () => ({
  manipulateAsync: jest.fn(),
  SaveFormat: { JPEG: 'jpeg' },
}));

jest.mock('expo/fetch', () => ({ fetch: jest.fn() }));

jest.mock('../src/services/sentry', () => ({
  addSseFallbackBreadcrumb: jest.fn(),
  initSentry: jest.fn(),
  scrubString: (s: string) => s,
  scrubBeforeSend: (e: any) => e,
}));

if (typeof (global as any).TextDecoder === 'undefined') {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  (global as any).TextDecoder = require('util').TextDecoder;
}

const axiosInstance = (require('axios') as any).__instance;
const expoFetchMock = (require('expo/fetch') as any).fetch as jest.Mock;

async function flush(times = 25): Promise<void> {
  for (let i = 0; i < times; i++) {
    // eslint-disable-next-line no-await-in-loop
    await new Promise((r) => setImmediate(r));
  }
}

function completeStream() {
  const encoder = new TextEncoder();
  const chunks = [encoder.encode(`event: complete\ndata: ${JSON.stringify({ success: true })}\n\n`)];
  let i = 0;
  const reader = {
    read: jest.fn().mockImplementation(() =>
      Promise.resolve(i < chunks.length ? { done: false, value: chunks[i++] } : { done: true, value: undefined }),
    ),
  };
  return { ok: true, body: { getReader: () => reader } };
}

async function setLanguage(lng: string | null): Promise<void> {
  if (!i18next.isInitialized) {
    await i18next.init({ lng: lng ?? 'en', resources: {}, initAsync: false } as any);
  }
  if (lng) await i18next.changeLanguage(lng);
}

function setSse(on: boolean | null) {
  const features = require('../src/config/features');
  features._setExpoFetchSseForTests?.(on);
}

/** Run one REST compare through streamComparison; return the axios params. */
async function restParams(input: any): Promise<Record<string, any>> {
  axiosInstance.get.mockReset();
  axiosInstance.get.mockResolvedValue({ data: { success: true } });
  setSse(false);
  const { streamComparison } = require('../src/services/api');
  streamComparison(input).subscribe({ onComplete: jest.fn(), onError: jest.fn() });
  await flush();
  const call = axiosInstance.get.mock.calls.find((c: any[]) => String(c[0]).includes('/api/v1/text/compare'));
  expect(call).toBeDefined();
  return call[1].params;
}

/** Run one SSE compare through streamComparison; return the parsed URL query. */
async function sseQuery(input: any): Promise<URLSearchParams> {
  expoFetchMock.mockReset();
  expoFetchMock.mockResolvedValue(completeStream());
  setSse(true);
  const { streamComparison } = require('../src/services/api');
  streamComparison(input).subscribe({ onComplete: jest.fn(), onError: jest.fn() });
  await flush();
  expect(expoFetchMock).toHaveBeenCalledTimes(1);
  const url = String(expoFetchMock.mock.calls[0][0]);
  expect(url).toContain('/api/v1/text/compare/stream?');
  return new URLSearchParams(url.split('?')[1]);
}

const PAIR = { product_a: 'Lattafa Yara', product_b: 'Lattafa Fakhar' };

describe('W4-14 lang on the compare requests', () => {
  let originalFetch: any;

  beforeEach(() => {
    originalFetch = (global as any).fetch;
    (global as any).fetch = jest.fn();
  });

  afterEach(async () => {
    (global as any).fetch = originalFetch;
    setSse(null);
    if (i18next.isInitialized) await i18next.changeLanguage('en');
  });

  it("RED 18: REST compare (GET /api/v1/text/compare, pair shape) sends lang='ar' when the app language is ar", async () => {
    await setLanguage('ar');
    const params = await restParams(PAIR);
    expect(params.lang).toBe('ar');
  });

  it("RED 19: the SSE compare URL carries lang=ar (feature override ON)", async () => {
    await setLanguage('ar');
    const q = await sseQuery(PAIR);
    expect(q.get('lang')).toBe('ar');
  });

  it("RED 20: REST compare with a string query (q shape) also sends lang='ar' (ar-BH counts as ar)", async () => {
    await setLanguage('ar-BH');
    const params = await restParams('Lattafa Yara vs Lattafa Fakhar');
    expect(params.q).toBe('Lattafa Yara vs Lattafa Fakhar');
    expect(params.lang).toBe('ar');
  });

  it("RED 20b: an upper-case language ('AR', 'Ar' - i18next keeps a one-subtag code's case) still sends lang='ar' on REST and SSE", async () => {
    for (const lng of ['AR', 'Ar']) {
      await setLanguage(lng);
      // Non-vacuous: the instance really carries the upper-case code.
      expect(i18next.language).toBe(lng);
      const params = await restParams(PAIR);
      expect(params.lang).toBe('ar');
      const q = await sseQuery(PAIR);
      expect(q.get('lang')).toBe('ar');
    }
  });

  it('RED 21b (M19): the language is read PER CALL - ar, en, ar across three calls on one imported api module', async () => {
    await setLanguage('ar');
    const first = await restParams(PAIR);
    await setLanguage('en');
    const second = await restParams(PAIR);
    await setLanguage('ar');
    const third = await restParams(PAIR);
    expect([first.lang, 'lang' in second, third.lang]).toEqual(['ar', false, 'ar']);
  });

  it("PIN 21: with language 'en' (or 'en-US') the REST params, the SSE query and the compareTextPair body carry NO lang key (deep-equal to HEAD)", async () => {
    for (const lng of ['en', 'en-US']) {
      // eslint-disable-next-line no-await-in-loop
      await setLanguage(lng);
      // eslint-disable-next-line no-await-in-loop
      const pair = await restParams(PAIR);
      expect(pair).toEqual({ product_a: 'Lattafa Yara', product_b: 'Lattafa Fakhar', region: 'bahrain' });
      // eslint-disable-next-line no-await-in-loop
      const str = await restParams('A vs B');
      expect(str).toEqual({ q: 'A vs B', region: 'bahrain' });
      // eslint-disable-next-line no-await-in-loop
      const q = await sseQuery(PAIR);
      expect(Array.from(q.keys()).sort()).toEqual(['product_a', 'product_b', 'region']);
      axiosInstance.post.mockReset();
      axiosInstance.post.mockResolvedValue({ data: { success: true } });
      const { compareTextPair } = require('../src/services/api');
      // eslint-disable-next-line no-await-in-loop
      await compareTextPair('A', 'B');
      expect(axiosInstance.post.mock.calls[0][1]).toEqual({ product_a: 'A', product_b: 'B', region: 'bahrain' });
    }
  });
});
