/**
 * S81-11 RED -- launchSurfaces (spec 2.2, C4 / C5; rulings R-S11-3, R-S11-19,
 * R-S11-27, R-S11-34).
 *
 * The new pure leaf src/services/launchSurfaces.ts holds the per-session
 * reading of the cached /app/version body (categories_live + surfaces) and
 * the ONE send rule (categoryToSend). It is fed ONLY from
 * appVersionService.checkForcedUpdate (R-S11-19: P9 replaced). The
 * category_coming_soon_tap EVENT is OUT of this unit (R-S11-27): the module
 * exports no event-name constant.
 *
 * A missing module is read through loadOptional and ASSERTED (never a top
 * level import), so every RED row fails at base on an assertion.
 */

import * as fs from 'fs';
import * as path from 'path';

let mockNativeVersion: string | null | undefined = '1.0.0';
jest.mock('expo-application', () => ({
  get nativeApplicationVersion() {
    return mockNativeVersion;
  },
  applicationId: 'com.qaren.test',
}));

function loadOptional(rel: string): any {
  try {
    // eslint-disable-next-line @typescript-eslint/no-var-requires
    return require(rel);
  } catch {
    return null;
  }
}

const SRC = path.resolve(__dirname, '../../src');

function readSrc(rel: string): string {
  return fs.readFileSync(path.join(SRC, rel), 'utf8').replace(/\r\n/g, '\n');
}

function walk(dir: string, out: string[] = []): string[] {
  for (const name of fs.readdirSync(dir)) {
    const full = path.join(dir, name);
    const st = fs.statSync(full);
    if (st.isDirectory()) {
      if (name === 'i18n' || name === '__tests__') continue;
      walk(full, out);
    } else if (/\.(ts|tsx|js)$/.test(name)) {
      out.push(full);
    }
  }
  return out;
}

const mockFetch = jest.fn();
(global as any).fetch = mockFetch;

function jsonResponse(body: unknown, ok = true) {
  return { ok, status: ok ? 200 : 500, json: async () => body };
}

/** The five base keys of version_routes.get_version_info(). */
function baseBody(extra: Record<string, unknown> = {}) {
  return {
    min_version: '1.0.0',
    latest_version: '1.0.0',
    force_update: false,
    update_url_ios: '',
    update_url_android: '',
    ...extra,
  };
}

const ABSENT = { categoriesLive: null, surfaces: { skincare: false, makeup: false } };

function mod(): any {
  return loadOptional('../../src/services/launchSurfaces');
}

beforeEach(() => {
  mockFetch.mockReset();
  mockNativeVersion = '1.0.0';
  mod()?.__resetLaunchSurfaces?.();
});

describe('S81-11 B9 -- parseLaunchSurfaces truth table', () => {
  it('the module exists with its documented API', () => {
    const m = mod();
    expect(m).not.toBeNull();
    for (const fn of [
      'parseLaunchSurfaces',
      'recordLaunchSurfaces',
      'getLaunchSurfaces',
      'subscribeLaunchSurfaces',
      'useLaunchSurfaces',
      'categoryToSend',
      '__resetLaunchSurfaces',
    ]) {
      expect(typeof m?.[fn]).toBe('function');
    }
    expect(m?.ABSENT_LAUNCH_SURFACES).toEqual(ABSENT);
  });

  it('categories_live: only an array of strings is accepted (lower-cased, trimmed)', () => {
    const m = mod();
    expect(typeof m?.parseLaunchSurfaces).toBe('function');
    if (!m) return;
    expect(m.parseLaunchSurfaces(baseBody()).categoriesLive).toBeNull();
    expect(m.parseLaunchSurfaces(baseBody({ categories_live: null })).categoriesLive).toBeNull();
    expect(m.parseLaunchSurfaces(baseBody({ categories_live: 'fragrances' })).categoriesLive).toBeNull();
    expect(m.parseLaunchSurfaces(baseBody({ categories_live: [1] })).categoriesLive).toBeNull();
    expect(m.parseLaunchSurfaces(baseBody({ categories_live: {} })).categoriesLive).toBeNull();
    expect(
      m.parseLaunchSurfaces(baseBody({ categories_live: ['fragrances', 2] })).categoriesLive,
    ).toBeNull();
    expect(
      m.parseLaunchSurfaces(baseBody({ categories_live: ['Fragrances '] })).categoriesLive,
    ).toEqual(['fragrances']);
    expect(m.parseLaunchSurfaces(baseBody({ categories_live: [] })).categoriesLive).toEqual([]);
  });

  it('surfaces: a chip is true ONLY for the boolean true; unknown keys ignored', () => {
    const m = mod();
    expect(typeof m?.parseLaunchSurfaces).toBe('function');
    if (!m) return;
    const s = (v: unknown) => m.parseLaunchSurfaces(baseBody({ surfaces: v })).surfaces;
    expect(s(undefined)).toEqual({ skincare: false, makeup: false });
    expect(s(null)).toEqual({ skincare: false, makeup: false });
    expect(s([])).toEqual({ skincare: false, makeup: false });
    expect(s('skincare')).toEqual({ skincare: false, makeup: false });
    expect(s({})).toEqual({ skincare: false, makeup: false });
    expect(s({ skincare: 'true', makeup: 1 })).toEqual({ skincare: false, makeup: false });
    expect(s({ skincare: { on: true } })).toEqual({ skincare: false, makeup: false });
    const both = s({ skincare: true, fashion: true });
    expect(both).toEqual({ skincare: true, makeup: false });
    expect(Object.keys(both).sort()).toEqual(['makeup', 'skincare']);
    expect(s({ skincare: true, makeup: true })).toEqual({ skincare: true, makeup: true });
  });

  it('a non-object payload is ABSENT', () => {
    const m = mod();
    expect(typeof m?.parseLaunchSurfaces).toBe('function');
    if (!m) return;
    for (const p of [undefined, null, 'x', 3, [], [baseBody()]]) {
      expect(m.parseLaunchSurfaces(p)).toEqual(ABSENT);
    }
  });

  it('recordLaunchSurfaces never throws, stores and notifies subscribers', () => {
    const m = mod();
    expect(typeof m?.recordLaunchSurfaces).toBe('function');
    if (!m) return;
    const seen: any[] = [];
    const unsub = m.subscribeLaunchSurfaces((v: any) => seen.push(v));
    expect(() => m.recordLaunchSurfaces(undefined)).not.toThrow();
    const hostile: any = {};
    Object.defineProperty(hostile, 'categories_live', {
      get() {
        throw new Error('boom');
      },
    });
    expect(() => m.recordLaunchSurfaces(hostile)).not.toThrow();
    m.recordLaunchSurfaces(baseBody({ categories_live: ['fragrances'], surfaces: { makeup: true } }));
    expect(m.getLaunchSurfaces()).toEqual({
      categoriesLive: ['fragrances'],
      surfaces: { skincare: false, makeup: true },
    });
    expect(seen.length).toBeGreaterThanOrEqual(1);
    expect(seen[seen.length - 1]).toEqual(m.getLaunchSurfaces());
    unsub();
    m.__resetLaunchSurfaces();
    expect(m.getLaunchSurfaces()).toEqual(ABSENT);
  });

  it('R-S11-27: no event-name constant is exported (the event ships with SF1)', () => {
    const m = mod();
    expect(m).not.toBeNull();
    expect(m?.CATEGORY_COMING_SOON_EVENT).toBeUndefined();
    expect(Object.values(m ?? { x: 'category_coming_soon_tap' })).not.toContain(
      'category_coming_soon_tap',
    );
  });
});

describe('S81-11 B8 -- categoryToSend (R-S11-3 / R-S11-34)', () => {
  it('fragrances ONLY when selected AND categories_live carries it', () => {
    const m = mod();
    expect(typeof m?.categoryToSend).toBe('function');
    if (!m) return;
    const live = { categoriesLive: ['fragrances'], surfaces: { skincare: false, makeup: false } };
    expect(m.categoryToSend('fragrances', live)).toBe('fragrances');
    expect(m.categoryToSend(null, live)).toBeUndefined();
    expect(m.categoryToSend('skincare', live)).toBeUndefined();
    expect(m.categoryToSend('electronics', live)).toBeUndefined();
    expect(m.categoryToSend('fragrances', ABSENT)).toBeUndefined();
    expect(
      m.categoryToSend('fragrances', { categoriesLive: [], surfaces: ABSENT.surfaces }),
    ).toBeUndefined();
    expect(
      m.categoryToSend('skincare', {
        categoriesLive: ['fragrances', 'skincare'],
        surfaces: ABSENT.surfaces,
      }),
    ).toBeUndefined();
  });
});

describe('S81-11 B10 -- checkForcedUpdate feeds the store (C5)', () => {
  it('a body carrying categories_live is recorded; the gate decision is unchanged', async () => {
    const m = mod();
    expect(m).not.toBeNull();
    const { checkForcedUpdate } = require('../../src/services/appVersionService');
    mockFetch.mockResolvedValue(jsonResponse(baseBody({ categories_live: ['fragrances'] })));
    await expect(checkForcedUpdate()).resolves.toBeNull();
    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(m?.getLaunchSurfaces?.().categoriesLive).toEqual(['fragrances']);
  });

  it('a rejecting fetch / non-OK / non-JSON body leaves the store ABSENT', async () => {
    const m = mod();
    expect(m).not.toBeNull();
    const { checkForcedUpdate } = require('../../src/services/appVersionService');
    mockFetch.mockRejectedValueOnce(new Error('offline'));
    await expect(checkForcedUpdate()).resolves.toBeNull();
    mockFetch.mockResolvedValueOnce(jsonResponse(baseBody({ categories_live: ['fragrances'] }), false));
    await expect(checkForcedUpdate()).resolves.toBeNull();
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => {
        throw new SyntaxError('bad json');
      },
    });
    await expect(checkForcedUpdate()).resolves.toBeNull();
    expect(m?.getLaunchSurfaces?.()).toEqual(ABSENT);
  });

  it('Expo Go (no native version): no fetch AND the store stays ABSENT', async () => {
    const m = mod();
    expect(m).not.toBeNull();
    mockNativeVersion = null;
    const { checkForcedUpdate } = require('../../src/services/appVersionService');
    await expect(checkForcedUpdate()).resolves.toBeNull();
    expect(mockFetch).not.toHaveBeenCalled();
    expect(m?.getLaunchSurfaces?.()).toEqual(ABSENT);
  });

  it('a forced-update body still blocks (the record call never changes the decision)', async () => {
    const { checkForcedUpdate } = require('../../src/services/appVersionService');
    mockNativeVersion = '1.0.0';
    mockFetch.mockResolvedValue(
      jsonResponse(
        baseBody({
          force_update: true,
          min_version: '2.0.0',
          update_url_ios: 'https://apps.apple.com/app/id1',
          update_url_android: 'https://play.google.com/store/apps/details?id=x',
          categories_live: ['fragrances'],
        }),
      ),
    );
    const gate = await checkForcedUpdate();
    expect(gate).not.toBeNull();
    expect(gate?.minVersion).toBe('2.0.0');
  });
});

describe('S81-11 R-S11-19 -- the store is fed only from checkForcedUpdate', () => {
  it('appVersionService records the parsed payload after the json parse, inside the try', () => {
    const src = readSrc('services/appVersionService.ts');
    expect(src).toMatch(
      /const payload = await response\.json\(\);\s*\n\s*recordLaunchSurfaces\(payload\);/,
    );
    // The Expo Go early return still precedes any fetch.
    const early = src.indexOf('if (currentVersion === null) return null;');
    const fetchAt = src.indexOf('fetchWithDeadline(');
    const recordAt = src.indexOf('recordLaunchSurfaces(payload)');
    expect(early).toBeGreaterThan(-1);
    expect(recordAt).toBeGreaterThan(fetchAt);
    expect(fetchAt).toBeGreaterThan(early);
  });

  it('no other src file calls recordLaunchSurfaces, and launchSurfaces does no network', () => {
    const callers = walk(SRC)
      .filter((f) => !f.endsWith(path.join('services', 'launchSurfaces.ts')))
      .filter((f) => /recordLaunchSurfaces\(/.test(fs.readFileSync(f, 'utf8')))
      .map((f) => path.relative(SRC, f).replace(/\\/g, '/'));
    expect(callers).toEqual(['services/appVersionService.ts']);
    expect(fs.existsSync(path.join(SRC, 'services/launchSurfaces.ts'))).toBe(true);
    const leaf = fs.existsSync(path.join(SRC, 'services/launchSurfaces.ts'))
      ? readSrc('services/launchSurfaces.ts')
      : 'fetch(';
    expect(leaf).not.toMatch(/\bfetch\(|axios|AsyncStorage|from '\.\/api'/);
  });
});
