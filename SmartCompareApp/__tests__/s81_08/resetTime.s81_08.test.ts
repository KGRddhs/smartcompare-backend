/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * S81-08 CLIENT-FIRST-OTA RED - rows F1..F6: the pure reset-time helpers in
 * src/utils/resetTime.ts (spec 2.7 as amended by RULINGS_S81_08 R-S08-10:
 * formatResetClock ROUNDS to the nearest minute; and R-S08-14: "the client
 * reads retry_after_seconds, then retry_after, then resets_at (window
 * now..now+48 h)" - the precedence F3 pins).
 *
 * Pure functions, no mocks. The module is read through load(); every row
 * fails at base on an assertion (the module does not exist there).
 */

function load(path: string): any {
  try {
    return require(path);
  } catch {
    return null;
  }
}

const RT = load('../../src/utils/resetTime');
const NOW = Date.UTC(2026, 9, 23, 9, 0, 0);
const H = 3600 * 1000;

function resolve(src: any, now: number = NOW): any {
  return RT && typeof RT.resolveResetAt === 'function' ? RT.resolveResetAt(src, now) : 'MISSING';
}

function fmt(at: Date, offset?: number): any {
  if (!RT || typeof RT.formatResetClock !== 'function') return 'MISSING';
  return offset === undefined ? RT.formatResetClock(at) : RT.formatResetClock(at, offset);
}

function ms(v: any): any {
  return v instanceof Date ? v.getTime() : v;
}

function hhmm(epochMs: number, offsetMinutes: number): string {
  const d = new Date(epochMs + offsetMinutes * 60000);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}`;
}

describe('S81-08 F - resetTime helpers', () => {
  it('F1 the module exports resolveResetAt and formatResetClock', () => {
    expect(RT).not.toBeNull();
    expect(typeof RT?.resolveResetAt).toBe('function');
    expect(typeof RT?.formatResetClock).toBe('function');
  });

  it('F2 resets_at inside the window -> that instant; formatted at a fixed offset', () => {
    const at = NOW + 5 * H;
    const iso = new Date(at).toISOString();
    expect(ms(resolve({ resets_at: iso }))).toBe(at);
    expect(fmt(new Date(at), 180)).toBe(hhmm(at, 180));
  });

  it('F3 precedence (R-S08-14): retry_after_seconds, then retry_after, then resets_at', () => {
    const iso = new Date(NOW + 5 * H).toISOString();
    expect(ms(resolve({ resets_at: iso, retry_after_seconds: 3600, retry_after: 7200 }))).toBe(NOW + 1 * H);
    expect(ms(resolve({ resets_at: iso, retry_after: 7200 }))).toBe(NOW + 2 * H);
    expect(ms(resolve({ resets_at: iso }))).toBe(NOW + 5 * H);
    expect(ms(resolve({ retry_after_seconds: 0, retry_after: 7200 }))).toBe(NOW + 2 * H);
  });

  it('F4 garbage -> null', () => {
    const iso = (t: number) => new Date(t).toISOString();
    const bad: any[] = [
      null,
      undefined,
      {},
      { resets_at: 123 },
      { resets_at: 'x' },
      { resets_at: iso(NOW - 60 * 1000) },
      { resets_at: iso(NOW) },
      { resets_at: iso(NOW + 48 * H + 1000) },
      { retry_after_seconds: 0 },
      { retry_after_seconds: -1 },
      { retry_after_seconds: 1.5 },
      { retry_after_seconds: '60' },
      { retry_after_seconds: true },
      { retry_after_seconds: NaN },
      { retry_after_seconds: Infinity },
      { retry_after_seconds: 172801 },
      { retry_after: 172801 },
    ];
    const got = bad.map((b) => ms(resolve(b)));
    expect(got).toEqual(bad.map(() => null));
    expect(ms(resolve({ resets_at: iso(NOW + 48 * H) }))).toBe(NOW + 48 * H);
    expect(ms(resolve({ retry_after_seconds: 172800 }))).toBe(NOW + 48 * H);
  });

  it('F5 the clock: HH:MM, 24-hour, zero-padded, ASCII digits, rounded to the nearest minute', () => {
    const at = (h: number, m: number, s = 0) => new Date(Date.UTC(2026, 9, 23, h, m, s));
    expect(fmt(at(3, 5), 0)).toBe('03:05');
    expect(fmt(at(15, 0), 0)).toBe('15:00');
    expect(fmt(at(3, 5, 20), 0)).toBe('03:05');
    expect(fmt(at(3, 5, 40), 0)).toBe('03:06');
    expect(fmt(at(23, 59, 55), 0)).toBe('00:00');
    expect(String(fmt(at(9, 7), 0))).toMatch(/^[0-9]{2}:[0-9]{2}$/);
  });

  it('F6 a Riyadh midnight reset reads 00:00 at +03:00 and 01:00 at +04:00', () => {
    const at = new Date('2026-10-24T00:00:00+03:00');
    expect(fmt(at, 180)).toBe('00:00');
    expect(fmt(at, 240)).toBe('01:00');
  });
});
