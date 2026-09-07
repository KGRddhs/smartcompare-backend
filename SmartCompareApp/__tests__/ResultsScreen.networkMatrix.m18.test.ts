/**
 * M18 mobile-network unit — screen wiring pins (source-level).
 *
 * Behavioral coverage of the matrix itself lives in
 * api.networkMatrix.m18.test.ts (classifyLoadFailure / parseApiError /
 * identifyFromImages / SSE watchdog are all real-function tested there).
 * This file pins the WIRING at the source level — the established
 * ResultsScreen convention (see ResultsScreen.timeout.test.tsx § 2: a full
 * render needs the whole Reanimated surface + 9 service mocks).
 *
 * Pins:
 *  - MB-flows-05: BOTH ResultsScreen catches route through
 *    classifyLoadFailure; the camera catch can no longer set
 *    'vision_failed' (reserved for an actual action==='error' identify
 *    response in the try block).
 *  - MB-perf-03: compare-class endpoints carry a per-call
 *    COMPARE_TIMEOUT_MS instead of riding the global 120s axios timeout;
 *    identifyFromImages carries an AbortController + IDENTIFY_TIMEOUT_MS.
 *  - MB-contract-02 (+ A11): HomeScreen's terminal onError fallback never
 *    renders a raw transport string on EITHER compare path — both end on
 *    `t(friendlyErrorKey(parsed.code))`, and no Alert takes `.message`.
 */

import * as fs from 'fs';
import * as path from 'path';

const SRC = (rel: string) => fs.readFileSync(path.resolve(__dirname, rel), 'utf8');

const RESULTS = SRC('../src/screens/ResultsScreen.tsx');
const HOME = SRC('../src/screens/HomeScreen.tsx');
const API = SRC('../src/services/api.ts');

describe('ResultsScreen — MB-flows-05 classification wiring (source)', () => {
  it('imports the explicit matrix', () => {
    expect(RESULTS).toMatch(/from '\.\.\/services\/failureClassification'/);
  });

  it('routes BOTH the history and camera catches through classifyLoadFailure', () => {
    const calls = RESULTS.match(/classifyLoadFailure\(/g) || [];
    expect(calls.length).toBeGreaterThanOrEqual(2);
  });

  it("the camera catch never claims the photos were bad: setLoadError('vision_failed') appears exactly once (the action==='error' try branch)", () => {
    const occurrences = RESULTS.match(/setLoadError\('vision_failed'\)/g) || [];
    expect(occurrences.length).toBe(1);
  });

  it('keeps the not_found and retryable timeout states wired', () => {
    expect(RESULTS).toMatch(/setLoadError\('not_found'\)/);
    expect(RESULTS).toMatch(/setLoadError\('timeout'\)/);
    expect(RESULTS).toMatch(/handleRetry/);
  });
});

describe('api.ts — MB-perf-03 per-call deadlines (source)', () => {
  it('declares the three deadline constants', () => {
    expect(API).toMatch(/export const COMPARE_TIMEOUT_MS/);
    expect(API).toMatch(/export const IDENTIFY_TIMEOUT_MS/);
    expect(API).toMatch(/export const STREAM_WATCHDOG_MS/);
  });

  it('the REST compare, pair compare and history detail fetch all carry COMPARE_TIMEOUT_MS', () => {
    const uses = API.match(/timeout: COMPARE_TIMEOUT_MS/g) || [];
    expect(uses.length).toBeGreaterThanOrEqual(3);
  });

  it('identifyFromImages wires an AbortController + IDENTIFY_TIMEOUT_MS into the fetch', () => {
    const identifyBlock = API.slice(
      API.indexOf('export async function identifyFromImages'),
      API.indexOf('export async function getComparisonHistory')
    );
    expect(identifyBlock).toMatch(/AbortController/);
    expect(identifyBlock).toMatch(/IDENTIFY_TIMEOUT_MS/);
    expect(identifyBlock).toMatch(/signal/);
  });

  it('the SSE error event preserves code and layer (MB-contract-02)', () => {
    const errorCase = API.slice(API.indexOf("case 'error':"));
    expect(errorCase).toMatch(/parsed\.code/);
    expect(errorCase).toMatch(/layer: parsed\.layer/);
  });
});

describe('HomeScreen — MB-perf-03/MB-contract-02 (source)', () => {
  it('the URL compare carries the per-call COMPARE_TIMEOUT_MS', () => {
    expect(HOME).toMatch(/COMPARE_TIMEOUT_MS/);
  });

  it('the terminal onError fallback never renders a raw transport string', () => {
    // MB-contract-02 originally pinned the guarded ternary
    // `parsed.code ? t('home.errors.comparison') : parsed.message` — which
    // still rendered the raw axios string on the CODELESS arm (a Railway edge
    // 502 has no `{success, error, code}` envelope, so parseApiError falls
    // through to `error?.message` = "Request failed with status code 502",
    // carrying the forbidden token "failed"). A11 replaced the ternary with a
    // TOTAL code->key map, so no arm can reach a raw string. Pin the stronger
    // property the ternary was only approximating.
    expect(HOME).toMatch(/from '\.\.\/services\/errorCopy'/);
    const terminalFallbacks =
      HOME.match(/Alert\.alert\(\s*t\('common\.error'\),\s*t\(friendlyErrorKey\(parsed\.code\)\)\s*\)/g) || [];
    // Both compare paths (text stream + URL) end on the same coded copy.
    expect(terminalFallbacks.length).toBe(2);
  });

  it('no HomeScreen alert can render parseApiError().message or error.message', () => {
    // The regression this guards: reintroducing `parsed.message` (or
    // `error.message`) as Alert copy on EITHER compare path.
    const alertArgs = HOME.match(/Alert\.alert\([\s\S]*?\);/g) || [];
    expect(alertArgs.length).toBeGreaterThan(0);
    const leaky = alertArgs.filter((call) =>
      /(parsed|error|err)\??\.message/.test(call)
    );
    expect(leaky).toEqual([]);
  });
});
