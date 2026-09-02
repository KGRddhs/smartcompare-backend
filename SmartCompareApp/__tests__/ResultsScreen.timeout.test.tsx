/**
 * Genuine-BH bundle — WS6 graceful timeout / partial handling (D1/D2/D3).
 *
 * The Tom Ford fragrance "couldn't load" bug was a 30s hard-cap TIMEOUT
 * mis-surfaced as a 400 + scary "couldn't finish…/Try again" copy. This
 * suite locks the FE half of the fix:
 *
 *  1. `parseApiError` (REAL function, behaviorally tested) normalizes the
 *     new 503/TIMEOUT envelope into a stable `code:'TIMEOUT'` with an
 *     EMPTY `message`, so callers substitute friendly copy by code and the
 *     backend's (possibly scary) `error` string can never reach the UI.
 *  2. The timeout/partial render wiring is verified at the SOURCE level —
 *     the established ResultsScreen convention (see
 *     ResultsScreen.redesign.test.tsx / .no_estimated_copy.test.tsx),
 *     because a full render needs the whole Reanimated entering-animation
 *     surface + 9 service mocks. Source assertions are exactly what the
 *     plan's grep-style acceptance prescribes.
 *  3. A forbidden-vocab guard over the NEW i18n keys (EN scary_vocab +
 *     AR scary_vocab + provenance vocabulary) — the no-scary-copy contract
 *     (Build Principle #4) + feedback_no_estimated_word_in_ui.
 *
 * Mocks mirror api.demographics.test.ts (the precedent for importing a
 * pure helper out of src/services/api.ts without the network surface).
 */

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

jest.mock('../src/services/certificatePinning', () => ({
  setupCertificatePinning: jest.fn(),
}));

jest.mock('../src/services/authService', () => ({
  getToken: jest.fn().mockResolvedValue('fake-jwt'),
  refreshSession: jest.fn(),
  clearSession: jest.fn(),
}));

jest.mock('expo-image-manipulator', () => ({
  manipulateAsync: jest.fn(),
  SaveFormat: { JPEG: 'jpeg' },
}));

import * as fs from 'fs';
import * as path from 'path';
import { parseApiError } from '../src/services/api';

// ---------------------------------------------------------------------------
// 1. parseApiError — the load-bearing normalization (real function)
// ---------------------------------------------------------------------------

describe('parseApiError — D2 timeout normalization', () => {
  it('maps a structured 503 {code:"TIMEOUT"} to code:TIMEOUT with empty message', () => {
    const err = { response: { status: 503, data: { code: 'TIMEOUT', error: "We couldn't finish this comparison in time. Try again." } } };
    const out = parseApiError(err);
    expect(out.code).toBe('TIMEOUT');
    // Empty message — the backend's scary string MUST NOT be forwarded.
    expect(out.message).toBe('');
  });

  it('maps a bare 503 (no specific code) to code:TIMEOUT', () => {
    const err = { response: { status: 503, data: { error: 'Service unavailable' } } };
    const out = parseApiError(err);
    expect(out.code).toBe('TIMEOUT');
    expect(out.message).toBe('');
  });

  it('maps STREAM_TIMEOUT (SSE complete) to code:TIMEOUT', () => {
    const err = { response: { status: 200, data: { success: false, code: 'STREAM_TIMEOUT', error: 'Stream timed out' } } };
    const out = parseApiError(err);
    expect(out.code).toBe('TIMEOUT');
    expect(out.message).toBe('');
  });

  it('reads code from a nested detail.code shape', () => {
    const err = { response: { status: 400, data: { detail: { code: 'TIMEOUT' } } } };
    const out = parseApiError(err);
    expect(out.code).toBe('TIMEOUT');
  });

  it('NEVER forwards the backend error string for a timeout (no scary copy leak)', () => {
    const err = { response: { status: 503, data: { code: 'TIMEOUT', error: "couldn't finish — Try again. Failed to load." } } };
    const out = parseApiError(err);
    expect(out.message).not.toMatch(/couldn't/i);
    expect(out.message).not.toMatch(/try again/i);
    expect(out.message).not.toMatch(/failed to/i);
  });

  it('preserves a non-timeout structured code (e.g. CONTENT_UNAVAILABLE) untouched', () => {
    const err = { response: { status: 422, data: { error: 'Not a product', code: 'CONTENT_UNAVAILABLE' } } };
    const out = parseApiError(err);
    expect(out.code).toBe('CONTENT_UNAVAILABLE');
    expect(out.message).toBe('Not a product');
  });

  it('leaves a plain non-timeout error (no code, no 503) as-is', () => {
    const err = { response: { status: 500, data: { error: 'Boom' } } };
    const out = parseApiError(err);
    expect(out.code).toBeNull();
    expect(out.message).toBe('Boom');
  });

  it('falls back to a generic message + null code with no response', () => {
    const out = parseApiError({});
    expect(out.code).toBeNull();
    expect(out.message).toBe('Something went wrong');
  });
});

// ---------------------------------------------------------------------------
// 2. ResultsScreen / HomeScreen / api.ts wiring — source assertions
// ---------------------------------------------------------------------------

const SRC = (rel: string) =>
  fs.readFileSync(path.resolve(__dirname, rel), 'utf8');

const RESULTS = SRC('../src/screens/ResultsScreen.tsx');
const HOME = SRC('../src/screens/HomeScreen.tsx');
const API = SRC('../src/services/api.ts');

describe('ResultsScreen — timeout state wiring (source)', () => {
  it('declares a "timeout" loadError variant', () => {
    expect(RESULTS).toMatch(/'timeout'/);
  });

  it('maps a 503 / TIMEOUT / STREAM_TIMEOUT response to the timeout state', () => {
    // M18 mobile-network: the status/code inspection moved into the shared
    // explicit matrix (failureClassification.ts) — the 503/TIMEOUT →
    // 'timeout' mapping is now pinned BEHAVIORALLY in
    // api.networkMatrix.m18.test.ts; here we pin that ResultsScreen routes
    // through the matrix and still wires the timeout state.
    const FAILCLASS = SRC('../src/services/failureClassification.ts');
    expect(FAILCLASS).toMatch(/status === 503/);
    expect(RESULTS).toMatch(/classifyLoadFailure\(/);
    expect(RESULTS).toMatch(/setLoadError\('timeout'\)/);
  });

  it('renders the soft timeout copy keys (title + body + retry)', () => {
    expect(RESULTS).toMatch(/results\.timeout\.title/);
    expect(RESULTS).toMatch(/results\.timeout\.body/);
    expect(RESULTS).toMatch(/results\.timeout\.retry/);
  });

  it('wires a tap-to-retry CTA that re-arms the fetch (handleRetry + nonce)', () => {
    expect(RESULTS).toMatch(/handleRetry/);
    expect(RESULTS).toMatch(/retryNonce/);
    expect(RESULTS).toMatch(/testID=\{isTimeout \? 'results-timeout-retry'/);
  });
});

describe('HomeScreen — timeout routes to soft copy (source)', () => {
  it('branches on the TIMEOUT code and shows home.errors.timeout', () => {
    expect(HOME).toMatch(/parsed\.code === 'TIMEOUT'/);
    expect(HOME).toMatch(/home\.errors\.timeout/);
  });

  it('does not surface the raw backend error string for a timeout', () => {
    // The onError TIMEOUT branch must use the i18n key, not error.message.
    const onErrorBlock = HOME.slice(HOME.indexOf("parsed.code === 'TIMEOUT'"));
    expect(onErrorBlock).toMatch(/t\('home\.errors\.timeout'\)/);
  });
});

describe('api.ts — SSE complete + fallback preserve the timeout code (source)', () => {
  it('SSE complete with success:false routes through onError with a 503/code envelope', () => {
    expect(API).toMatch(/parsed\.success === false/);
    expect(API).toMatch(/status: 503/);
  });

  it('non-streaming fallback preserves response.data.code on success:false', () => {
    expect(API).toMatch(/code: response\.data\.code/);
  });
});

// ---------------------------------------------------------------------------
// 3. Forbidden-vocab guard over the NEW i18n keys (EN + AR)
// ---------------------------------------------------------------------------

const EN = JSON.parse(SRC('../src/i18n/en.json'));
const AR = JSON.parse(SRC('../src/i18n/ar.json'));
const COPY_POLICY = JSON.parse(SRC('../src/i18n/.copy-policy.json'));

const NEW_KEYS = [
  'results.timeout.title',
  'results.timeout.body',
  'results.timeout.retry',
  'results.partial.note',
  'home.errors.timeout',
];

describe('WS6 i18n — new timeout keys exist + carry no forbidden vocab', () => {
  it('every new key is present in BOTH en.json and ar.json', () => {
    for (const k of NEW_KEYS) {
      expect(typeof EN[k]).toBe('string');
      expect(EN[k].length).toBeGreaterThan(0);
      expect(typeof AR[k]).toBe('string');
      expect(AR[k].length).toBeGreaterThan(0);
    }
  });

  it('EN copy has zero scary_vocab hits (couldn\'t / try again / Failed to)', () => {
    for (const k of NEW_KEYS) {
      for (const banned of COPY_POLICY.scary_vocab_en as string[]) {
        expect(EN[k].toLowerCase()).not.toContain(banned.toLowerCase());
      }
    }
  });

  it('AR copy has zero scary_vocab hits (تعذر / فشل / تقدير / مُقدَّر)', () => {
    for (const k of NEW_KEYS) {
      for (const banned of COPY_POLICY.scary_vocab_ar as string[]) {
        expect(AR[k]).not.toContain(banned);
      }
    }
  });

  it('EN + AR copy carry no provenance vocabulary (estimated / reference price / indicative)', () => {
    const prov = [/\(estimated\)/i, /\breference price\b/i, /\bindicative\b/i];
    for (const k of NEW_KEYS) {
      for (const p of prov) {
        expect(EN[k]).not.toMatch(p);
        expect(AR[k]).not.toMatch(p);
      }
    }
  });
});

// ---------------------------------------------------------------------------
// 4. converted_usd / genuine JSON-LD price pill labeling (D3)
// ---------------------------------------------------------------------------

import { parseSourceMethod } from '../src/services/sourceMethod';

describe('D3 — price pill labeling never uses the word "estimated"', () => {
  it('converted_usd renders an honest local-listing phrase, not "estimated"', () => {
    const phrase = parseSourceMethod('converted_usd');
    expect(phrase).toBe('Local listing');
    expect(phrase).not.toMatch(/estimated|indicative|reference price/i);
  });

  it('page_scrape_jsonld (genuine BH curl) renders the retailer-page phrase', () => {
    expect(parseSourceMethod('page_scrape_jsonld' as any)).toBe('Retailer page');
  });

  it('shopify_json (genuine BH /products.json) renders the retailer-page phrase, not suppressed', () => {
    // Regression guard: backend emits source_method:"shopify_json" for a real
    // BHD price (price_service.py:1752). It must NOT fall through to null
    // (which would suppress the pill like 'estimated').
    expect(parseSourceMethod('shopify_json' as any)).toBe('Retailer page');
  });

  it('estimated suppresses the pill (returns null) — no provenance copy', () => {
    expect(parseSourceMethod('estimated')).toBeNull();
  });
});
