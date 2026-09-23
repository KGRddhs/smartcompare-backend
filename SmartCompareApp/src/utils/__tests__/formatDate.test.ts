/**
 * W3-11bcd — MB-I18N-RTL-08: relative time goes through the catalog.
 *
 * Measured at base b63a8368: `formatTimeAgo` hard-codes 8 strings
 * (formatDate.ts:28-39) and gives Arabic ONE form for every count —
 * "منذ 1 دقيقة", "منذ 2 دقيقة", "منذ 5 دقيقة", "منذ 15 دقيقة" (the
 * grammatical singular/dual/plural never appear). The fix adds a `t`
 * parameter and the `time.justNow` + `time.{minutes,hours,days}Ago` six-form
 * families (both catalogs), following the `history.hero.count` template.
 *
 * Real i18next instance over the real catalogs; `Date.now` is pinned.
 */
import * as fs from 'fs';
import * as path from 'path';
import { createInstance } from 'i18next';
import en from '../../i18n/en.json';
import ar from '../../i18n/ar.json';
import { formatDate, formatTimeAgo } from '../formatDate';

const AR = ar as Record<string, string>;
const NOW = Date.UTC(2026, 8, 11, 12);
const MIN = 60_000;
const HOUR = 3_600_000;
const DAY = 86_400_000;

const inst = createInstance();
// Catalog lookups go through `tr` rather than a literal-key t call so the
// src-wide referenced-key fence (__tests__/i18n/no-missing-referenced-keys)
// scans product code only, not this test's expectations.
const tr = (key: string, opts?: Record<string, unknown>): string => inst.t(key, opts);

beforeAll(async () => {
  await inst.init({
    lng: 'en',
    fallbackLng: 'en',
    resources: {
      en: { translation: en },
      ar: { translation: ar },
    },
    interpolation: { escapeValue: false },
  });
});

beforeEach(() => {
  jest.spyOn(Date, 'now').mockReturnValue(NOW);
});

afterEach(() => {
  jest.restoreAllMocks();
});

function ago(ms: number): Date {
  return new Date(NOW - ms);
}

describe('RTL-08 (a) — Arabic relative time', () => {
  it('5 minutes ago resolves through time.minutesAgo, not the hard-coded one-form string', async () => {
    await inst.changeLanguage('ar');
    const out = formatTimeAgo(ago(5 * MIN), 'ar', inst.t);
    expect(out).not.toBe('منذ 5 دقيقة');
    const expected = tr('time.minutesAgo', { count: 5 });
    expect(expected).not.toBe('time.minutesAgo');
    expect(out).toBe(expected);
  });

  it('every bucket routes to its catalog key (justNow / minutes / hours / days; >= 7 days stays formatDate)', async () => {
    await inst.changeLanguage('ar');
    expect(tr('time.justNow')).not.toBe('time.justNow');
    expect(formatTimeAgo(ago(10_000), 'ar', inst.t)).toBe(tr('time.justNow'));
    expect(formatTimeAgo(ago(3 * HOUR), 'ar', inst.t)).toBe(tr('time.hoursAgo', { count: 3 }));
    expect(formatTimeAgo(ago(2 * DAY), 'ar', inst.t)).toBe(tr('time.daysAgo', { count: 2 }));
    // Preserved: the >= 7-day fallback is the absolute date.
    expect(formatTimeAgo(ago(20 * DAY), 'ar', inst.t)).toBe(formatDate(ago(20 * DAY), 'ar'));
  });

  const FAMILIES: [string, number[]][] = [
    ['time.minutesAgo', [0, 1, 2, 5, 15, 100]],
    ['time.hoursAgo', [0, 1, 2, 3, 11, 100]],
    ['time.daysAgo', [0, 1, 2, 3, 11, 100]],
  ];

  it.each(FAMILIES)(
    '%s gives six distinct Arabic forms; singular and dual carry no digit',
    async (key, counts) => {
      await inst.changeLanguage('ar');
      const forms = counts.map((count) => tr(key, { count }));
      for (const f of forms) {
        expect(f).not.toBe(key);
        expect(f).not.toMatch(/^time\./);
      }
      expect(new Set(forms).size).toBe(6);
      // counts[1] === 1 and counts[2] === 2: grammatical singular / dual
      // (the history.hero.count convention — "قرار واحد", "قراران").
      expect(forms[1]).not.toMatch(/[0-9٠-٩]/);
      expect(forms[2]).not.toMatch(/[0-9٠-٩]/);
    },
  );

  it('daysAgo with count 1 is the "yesterday" string (time.daysAgo_one)', async () => {
    await inst.changeLanguage('ar');
    const one = tr('time.daysAgo', { count: 1 });
    expect(one).toBe(tr('time.daysAgo_one'));
    expect(one).toBe(AR['profile.recent.yesterday']);
  });
});

describe('RTL-08 (b) — English wording preserved exactly', () => {
  it('3 hours ago is "3h ago", and it comes from the catalog', async () => {
    await inst.changeLanguage('en');
    const out = formatTimeAgo(ago(3 * HOUR), 'en', inst.t);
    expect(out).toBe(tr('time.hoursAgo', { count: 3 }));
    expect(out).toBe('3h ago');
  });

  it('5 minutes ago is "5m ago", and it comes from the catalog', async () => {
    await inst.changeLanguage('en');
    const out = formatTimeAgo(ago(5 * MIN), 'en', inst.t);
    expect(out).toBe(tr('time.minutesAgo', { count: 5 }));
    expect(out).toBe('5m ago');
  });
});

describe('P8 — formatDate.ts can never re-grow hard-coded relative-time copy', () => {
  // src/utils is exempt from i18next/no-literal-string (eslint.config.js),
  // and under mode:'jsx-text-only' the plugin could not see a non-JSX
  // string there anyway (spec R13.2). This source pin is the ONLY fence for
  // the RTL-08 class in this file — do not weaken it.
  const SRC = fs.readFileSync(path.resolve(__dirname, '../formatDate.ts'), 'utf8');

  it('contains no Arabic-script character', () => {
    expect(SRC.match(/[؀-ۿ]/g) ?? []).toEqual([]);
  });

  it("contains none of 'just now' | 'm ago' | 'h ago' | 'd ago'", () => {
    const found = ['just now', 'm ago', 'h ago', 'd ago'].filter((lit) => SRC.includes(lit));
    expect(found).toEqual([]);
  });
});
