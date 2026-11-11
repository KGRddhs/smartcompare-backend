/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * S81-G6 CL2 CLIENT-SPEED -- rows R16-R21 (spec section 5, RULINGS_S81_G6
 * R-G6-10): src/services/swrCache.ts, the in-memory per-user History cache
 * with the 30 s focus throttle. The module does not exist at base: it is read
 * through loadOptional and asserted. Synthetic ids only (u-a, u-b).
 */

import * as fs from 'fs';
import * as path from 'path';

function loadOptional(rel: string): any {
  try {
    return require(rel);
  } catch {
    return null;
  }
}

const MOD = '../../src/services/swrCache';
const SRC_PATH = path.resolve(__dirname, '../../src/services/swrCache.ts');

const FNS = [
  'setSwrUser',
  'swrRead',
  'swrWrite',
  'shouldRefetchOnFocus',
  'invalidateSwrPrefix',
  'clearSwrCache',
];

const T = 1_700_000_000_000;

function loaded(): any {
  const m = loadOptional(MOD);
  expect(m).not.toBeNull();
  m.clearSwrCache();
  return m;
}

describe('CL2 swrCache leaf (C4)', () => {
  it('R16 exports SWR_FOCUS_THROTTLE_MS = 30000 and the six functions', () => {
    const m = loadOptional(MOD);
    expect(m).not.toBeNull();
    expect(m.SWR_FOCUS_THROTTLE_MS).toBe(30000);
    expect(FNS.filter((name) => typeof m[name] !== 'function')).toEqual([]);
  });

  it('R17 no user: write is a no-op, read is undefined, focus always refetches', () => {
    const m = loaded();
    m.swrWrite('history:', { comparisons: [], total: 0 }, T);
    expect(m.swrRead('history:')).toBeUndefined();
    expect(m.shouldRefetchOnFocus('history:', T + 1)).toBe(true);
    m.setSwrUser(null);
    m.swrWrite('history:', { comparisons: [], total: 0 }, T);
    expect(m.swrRead('history:')).toBeUndefined();
    expect(m.shouldRefetchOnFocus('history:', T + 1)).toBe(true);
  });

  it('R18 throttle: false at T+29999, true at T+30000', () => {
    const m = loaded();
    m.setSwrUser('u-a');
    expect(m.shouldRefetchOnFocus('history:', T)).toBe(true);
    m.swrWrite('history:', { comparisons: [{ id: 'h1' }], total: 1 }, T);
    expect(m.swrRead('history:')).toEqual({
      data: { comparisons: [{ id: 'h1' }], total: 1 },
      fetchedAt: T,
    });
    expect(m.shouldRefetchOnFocus('history:', T + 29999)).toBe(false);
    expect(m.shouldRefetchOnFocus('history:', T + 30000)).toBe(true);
    expect(m.shouldRefetchOnFocus('history:other', T + 1)).toBe(true);
  });

  it('R19 user change: u-a -> u-b clears; u-b -> u-b keeps; -> null clears', () => {
    const m = loaded();
    m.setSwrUser('u-a');
    m.swrWrite('history:', { v: 'a' }, T);
    m.setSwrUser('u-b');
    expect(m.swrRead('history:')).toBeUndefined();
    m.swrWrite('history:', { v: 'b' }, T);
    m.setSwrUser('u-b');
    expect(m.swrRead('history:')).toEqual({ data: { v: 'b' }, fetchedAt: T });
    m.setSwrUser(null);
    expect(m.swrRead('history:')).toBeUndefined();
    m.setSwrUser('u-b');
    expect(m.swrRead('history:')).toBeUndefined();
  });

  it('R20 invalidateSwrPrefix drops history:* only', () => {
    const m = loaded();
    m.setSwrUser('u-a');
    m.swrWrite('history:', { v: 1 }, T);
    m.swrWrite('history:alpha', { v: 2 }, T);
    m.swrWrite('other:x', { v: 3 }, T);
    m.invalidateSwrPrefix('history:');
    expect(m.swrRead('history:')).toBeUndefined();
    expect(m.swrRead('history:alpha')).toBeUndefined();
    expect(m.swrRead('other:x')).toEqual({ data: { v: 3 }, fetchedAt: T });
    expect(m.shouldRefetchOnFocus('history:', T + 1)).toBe(true);
  });

  it('R21 the leaf has no import, no require and no AsyncStorage', () => {
    expect(fs.existsSync(SRC_PATH)).toBe(true);
    const src = fs.readFileSync(SRC_PATH, 'utf8').replace(/\r\n/g, '\n');
    expect(src).not.toMatch(/^\s*import\s/m);
    expect(src).not.toMatch(/\brequire\(/);
    expect(src).not.toMatch(/AsyncStorage/);
  });
});
