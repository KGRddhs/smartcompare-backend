/**
 * S69 U7 T1 (spec R1) — an engine outage is never blamed on the user's input.
 *
 * Base (d792f00e): `friendlyErrorKey` (src/services/errorCopy.ts:33-52) sends
 * every code other than INSUFFICIENT_DATA / RATE_LIMITED / TIMEOUT to the
 * default arm `home.errors.comparison` = "Sharper match coming up — try with
 * brand or model." (en.json:117), under the title `common.error` = "Hold on —
 * give it another tap." So during an OpenAI outage the reviewer is told to
 * retype the pair:
 *   - LLM_UNAVAILABLE (coded 503, text_routes.py:399-414)
 *   - INTERNAL_ERROR (coded 400, text_routes.py:418-438)
 *   - SERVER_ERROR (500 from ErrorHandlerMiddleware, error_handler.py:32)
 *   - a Railway edge 502 / 504 with an HTML body — parseApiError returns
 *     code null (api.ts:1010-1040), and null also lands on the default arm.
 *
 * Target contract pinned here (spec R1 + binding review corrections 3/5/6/7
 * and open questions 1-3):
 *   - those five inputs resolve to ONE engine-unavailable body key
 *     `home.errors.engineUnavailable.body` with its own title key
 *     `home.errors.engineUnavailable.title` (new export
 *     `friendlyErrorTitleKey`; every other code keeps `common.error`);
 *   - a BARE 503 (no code) stays TIMEOUT (MB-contract-09 / D2, five pins);
 *   - INSUFFICIENT_DATA / RATE_LIMITED / TIMEOUT unchanged; a codeless
 *     NON-5xx failure keeps `home.errors.comparison`;
 *   - both catalogs carry the new keys, copy-policy clean, no app name, no
 *     provider name, no diacritics in AR, no "brand or model" nudge.
 *
 * Whole chain, no stub in it: axios-shaped error -> real parseApiError ->
 * real friendlyErrorKey -> real en.json / ar.json. Harness mirrors
 * errorCopy.a11.test.ts.
 */

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
  manipulateAsync: jest.fn().mockResolvedValue({ uri: 'file:///manipulated.jpg' }),
  SaveFormat: { JPEG: 'jpeg' },
}));

jest.mock('expo/fetch', () => ({ fetch: jest.fn() }));

jest.mock('../src/services/sentry', () => ({
  addSseFallbackBreadcrumb: jest.fn(),
  initSentry: jest.fn(),
  scrubString: (s: string) => s,
  scrubBeforeSend: (e: any) => e,
}));

import { parseApiError } from '../src/services/api';
import * as errorCopy from '../src/services/errorCopy';
import en from '../src/i18n/en.json';
import ar from '../src/i18n/ar.json';
import policy from '../src/i18n/.copy-policy.json';

const { friendlyErrorKey } = errorCopy;
// New export (does not exist at base). Read off the namespace so a missing
// export is a runtime RED, not a module-load crash that hides the other rows.
const friendlyErrorTitleKey = (code: string | null | undefined): string => {
  const fn = (errorCopy as any).friendlyErrorTitleKey;
  if (typeof fn !== 'function') {
    throw new Error('errorCopy.friendlyErrorTitleKey is not exported');
  }
  return fn(code);
};

const EN = en as Record<string, string>;
const AR = ar as Record<string, string>;

const ENGINE_BODY = 'home.errors.engineUnavailable.body';
const ENGINE_TITLE = 'home.errors.engineUnavailable.title';
const GENERIC_BODY = 'home.errors.comparison';
const GENERIC_TITLE = 'common.error';

function axiosError(status: number, data: any): any {
  const err: any = new Error(`Request failed with status code ${status}`);
  err.isAxiosError = true;
  err.response = { status, data };
  return err;
}

// The five outage shapes, exactly as they reach the client.
const OUTAGES: Array<[string, any]> = [
  [
    'coded 503 LLM_UNAVAILABLE (text_routes.py:399-414)',
    axiosError(503, {
      success: false,
      error: 'Still warming up the comparison engine — give it another tap in a moment.',
      code: 'LLM_UNAVAILABLE',
      request_id: 'req-llm',
    }),
  ],
  [
    'coded 400 INTERNAL_ERROR (text_routes.py:418-438)',
    axiosError(400, {
      success: false,
      error: 'Something went wrong on our side — give it another tap in a moment.',
      code: 'INTERNAL_ERROR',
      request_id: 'req-int',
    }),
  ],
  [
    'coded 500 SERVER_ERROR (ErrorHandlerMiddleware, error_handler.py:32)',
    axiosError(500, {
      success: false,
      error: 'Internal server error',
      code: 'SERVER_ERROR',
      request_id: 'req-500',
    }),
  ],
  ['codeless Railway edge 502 (HTML body)', axiosError(502, '<html><body>Bad gateway</body></html>')],
  ['codeless Railway edge 504 (HTML body)', axiosError(504, '<html><body>Gateway timeout</body></html>')],
];

describe('S69 U7 T1 — outage codes resolve to the engine-unavailable copy', () => {
  it.each(OUTAGES)('%s -> engine-unavailable body key, never the brand-or-model nudge', (_label, err) => {
    const key = friendlyErrorKey(parseApiError(err).code);
    expect(key).toBe(ENGINE_BODY);
    expect(key).not.toBe(GENERIC_BODY);
  });

  it.each(OUTAGES)('%s -> engine-unavailable title key, not "give it another tap"', (_label, err) => {
    const title = friendlyErrorTitleKey(parseApiError(err).code);
    expect(title).toBe(ENGINE_TITLE);
    expect(title).not.toBe(GENERIC_TITLE);
  });
});

describe('S69 U7 T1 — the non-outage rows do not move (with the new map in place)', () => {
  it('bare 503 stays TIMEOUT; INSUFFICIENT_DATA / RATE_LIMITED / TIMEOUT / codeless 4xx unchanged', () => {
    // RED anchor: the new title map must exist for this row to run at all.
    expect(friendlyErrorTitleKey('LLM_UNAVAILABLE')).toBe(ENGINE_TITLE);

    // MB-contract-09 / D2: a bare 503 (uvicorn shed, no envelope) is TIMEOUT.
    const bare503 = parseApiError(axiosError(503, { success: false, error: 'x' }));
    expect(bare503.code).toBe('TIMEOUT');
    expect(friendlyErrorKey(bare503.code)).toBe('home.errors.timeout');

    // INSUFFICIENT_DATA IS about the pair — keeps its own copy.
    const insufficient = parseApiError(
      axiosError(400, { success: false, error: 'Not enough product data', code: 'INSUFFICIENT_DATA' }),
    );
    expect(friendlyErrorKey(insufficient.code)).toBe('home.errors.insufficientData');
    expect(friendlyErrorKey('RATE_LIMITED')).toBe('home.errors.rateLimited');
    expect(friendlyErrorKey('TIMEOUT')).toBe('home.errors.timeout');
    expect(friendlyErrorKey('STREAM_TIMEOUT')).toBe('home.errors.timeout');

    // A codeless NON-5xx failure (parser-failure 400, codeless success:false
    // identify — pinned by HomeScreen.arabicAlerts.w311) keeps the generic key.
    const codeless400 = parseApiError(axiosError(400, { detail: 'Could not parse product query' }));
    expect(friendlyErrorKey(codeless400.code)).toBe(GENERIC_BODY);

    // Titles of the untouched rows stay the shared `common.error`.
    for (const code of ['INSUFFICIENT_DATA', 'RATE_LIMITED', 'TIMEOUT', null, undefined, 'WAT']) {
      expect(friendlyErrorTitleKey(code as any)).toBe(GENERIC_TITLE);
    }
  });
});

describe('S69 U7 T1 — both catalogs carry the engine-unavailable keys, copy-policy clean', () => {
  const KEYS = [ENGINE_TITLE, ENGINE_BODY];
  const SCARY_EN = [/couldn['’]t/i, /could not/i, /try again/i, /fail/i, /error occurred/i, /Failed to/];
  const APP_OR_PROVIDER = [/qaren/i, /myez/i, /smartcompare/i, /openai/i, /chatgpt/i, /\bgpt\b/i];
  const AR_DIACRITICS = /[ً-ْٰ]/;

  it.each(KEYS)('%s exists in en.json and ar.json as a real translation', (key) => {
    expect(typeof EN[key]).toBe('string');
    expect(typeof AR[key]).toBe('string');
    expect(EN[key].trim().length).toBeGreaterThan(0);
    expect(AR[key].trim().length).toBeGreaterThan(0);
    expect(AR[key]).not.toBe(EN[key]);
    expect(AR[key]).toMatch(/[؀-ۿ]/);
  });

  it.each(KEYS)('%s obeys the copy contract (no blame, no scary vocab, no names)', (key) => {
    const enStr = EN[key];
    const arStr = AR[key];
    expect(enStr).toBeDefined();
    expect(arStr).toBeDefined();

    // Not the retype nudge — the outage is not the user's input.
    expect(enStr).not.toMatch(/brand or model/i);
    expect(enStr).not.toBe(EN[GENERIC_BODY]);
    expect(arStr).not.toBe(AR[GENERIC_BODY]);
    // "not counted" is false on a 502/504 (the edge can time out after the
    // backend metered and saved the row — review correction 8).
    expect(enStr).not.toMatch(/not (been )?counted/i);

    for (const re of SCARY_EN) expect(enStr).not.toMatch(re);
    for (const word of (policy as any).scary_vocab_en as string[]) {
      expect(enStr.toLowerCase()).not.toContain(word.toLowerCase());
    }
    for (const word of (policy as any).scary_vocab_ar as string[]) {
      expect(arStr).not.toContain(word);
    }
    for (const row of (policy as any).banned_en as Array<{ pattern: string }>) {
      expect(enStr).not.toMatch(new RegExp(row.pattern));
    }
    for (const row of (policy as any).banned_ar as Array<{ pattern: string }>) {
      expect(arStr).not.toMatch(new RegExp(row.pattern));
    }
    // Ruling R-A + unit rule: never names the app or the provider.
    for (const re of APP_OR_PROVIDER) {
      expect(enStr).not.toMatch(re);
      expect(arStr).not.toMatch(re);
    }
    // MSA, no diacritics.
    expect(arStr).not.toMatch(AR_DIACRITICS);
  });
});
