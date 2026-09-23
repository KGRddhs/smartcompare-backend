/**
 * W3-14 R2 — settings-surface error copy + the seconds-aware rate-limit sentence.
 *
 * Three contracts, all on REAL modules / REAL catalogs (nothing mocked):
 *
 *  1. `settingsErrorKey(code, fallbackKey)` (new, `services/errorCopy.ts`):
 *     RATE_LIMITED -> 'common.errors.rateLimited', ACCOUNT_LOCKED ->
 *     'common.errors.locked', EVERYTHING else (incl. null / undefined / '')
 *     -> the caller's fallback key. Total by construction. `friendlyErrorKey`
 *     is untouched (pinned by errorCopy.a11.test.ts).
 *
 *  2. Every key it can emit, plus the six `home.errors.rateLimited_*` plural
 *     siblings, exists in BOTH catalogs, non-empty, and clears the copy
 *     policy's scary vocabulary — read from `src/i18n/.copy-policy.json` at
 *     runtime, EN compared case-insensitively after stripping `{{...}}`
 *     exactly as copy-policy.test.ts does (FABLE ruling R-7).
 *
 *  3. A REAL i18next instance with the app's init options
 *     (`src/i18n/index.ts`) resolves `home.errors.rateLimited` with a count to
 *     a sentence carrying the seconds, and WITHOUT a count (field absent /
 *     older backend) to today's BASE sentence. FABLE ruling R-6: the base key
 *     is REQUIRED (siblings without a base render the raw key), and ar 11 and
 *     61 are both `many`, so ">= 4 distinct" is at its boundary — two extra
 *     inequalities stop a 2-form catalog passing.
 *
 * This file is the anti-tautology anchor for R3's count-aware `t` mock
 * (FABLE ruling R-16): R3 proves the call site passes `{ count }`; this file
 * proves real i18next turns that into the right sentence.
 */
import i18next from 'i18next';
import * as fs from 'fs';
import * as path from 'path';
import en from '../src/i18n/en.json';
import ar from '../src/i18n/ar.json';
import * as errorCopy from '../src/services/errorCopy';

const EN = en as Record<string, string>;
const AR = ar as Record<string, string>;

const policy = JSON.parse(
  fs.readFileSync(path.resolve(__dirname, '../src/i18n/.copy-policy.json'), 'utf8'),
) as { scary_vocab_en: string[]; scary_vocab_ar: string[] };

// copy-policy.test.ts:91-93 — placeholders are never user-visible.
const visibleCopy = (v: string) => v.replace(/\{\{[^}]+\}\}/g, '');

const settingsErrorKey = (errorCopy as any).settingsErrorKey as
  | ((code: string | null | undefined, fallbackKey: string) => string)
  | undefined;

const PLURAL_SUFFIXES = ['zero', 'one', 'two', 'few', 'many', 'other'];
const RATE_PLURAL_KEYS = PLURAL_SUFFIXES.map((s) => `home.errors.rateLimited_${s}`);
const NEW_COMMON_KEYS = ['common.errors.rateLimited', 'common.errors.locked'];

describe('W3-14 R2 — settingsErrorKey (total code -> key map)', () => {
  it('is exported from services/errorCopy', () => {
    expect(typeof settingsErrorKey).toBe('function');
  });

  it('RATE_LIMITED -> common.errors.rateLimited', () => {
    expect(settingsErrorKey!('RATE_LIMITED', 'x')).toBe('common.errors.rateLimited');
  });

  it('ACCOUNT_LOCKED -> common.errors.locked', () => {
    expect(settingsErrorKey!('ACCOUNT_LOCKED', 'x')).toBe('common.errors.locked');
  });

  it.each([
    ['null', null],
    ['undefined', undefined],
    ['empty string', ''],
    ['VALIDATION_ERROR', 'VALIDATION_ERROR'],
    ['BAD_REQUEST', 'BAD_REQUEST'],
    ['NOT_FOUND', 'NOT_FOUND'],
    ['TIMEOUT', 'TIMEOUT'],
    ['USAGE_LIMIT', 'USAGE_LIMIT'],
    ['INTERNAL_ERROR', 'INTERNAL_ERROR'],
  ])('%s -> the caller fallback key, verbatim', (_label, code) => {
    expect(settingsErrorKey!(code as any, 'x')).toBe('x');
    expect(settingsErrorKey!(code as any, 'profile.aiSharing.errorSave')).toBe(
      'profile.aiSharing.errorSave',
    );
  });

  it('friendlyErrorKey is untouched: RATE_LIMITED still maps to the Home key', () => {
    expect(errorCopy.friendlyErrorKey('RATE_LIMITED')).toBe('home.errors.rateLimited');
    expect(errorCopy.friendlyErrorKey('ACCOUNT_LOCKED')).toBe('home.errors.comparison');
  });
});

describe('W3-14 R2 — catalog entries exist in both languages and obey the copy policy', () => {
  const REQUIRED = [...NEW_COMMON_KEYS, ...RATE_PLURAL_KEYS, 'home.errors.rateLimited'];

  it.each(REQUIRED)('%s exists, non-empty, in en AND ar', (key) => {
    expect(typeof EN[key]).toBe('string');
    expect(EN[key].trim().length).toBeGreaterThan(0);
    expect(typeof AR[key]).toBe('string');
    expect(AR[key].trim().length).toBeGreaterThan(0);
  });

  it('the policy lists are non-empty (a vacuous scan would pass anything)', () => {
    expect(policy.scary_vocab_en.length).toBeGreaterThan(0);
    expect(policy.scary_vocab_ar.length).toBeGreaterThan(0);
  });

  it.each(REQUIRED)('%s clears scary_vocab_en (case-insensitive) and scary_vocab_ar', (key) => {
    const enVisible = visibleCopy(EN[key] ?? '').toLowerCase();
    for (const term of policy.scary_vocab_en) {
      expect(enVisible).not.toContain(term.toLowerCase());
    }
    const arVisible = visibleCopy(AR[key] ?? '');
    for (const term of policy.scary_vocab_ar) {
      expect(arVisible).not.toContain(term);
    }
  });

  it('en _other carries {{count}} (the seconds reach the sentence)', () => {
    expect(EN['home.errors.rateLimited_other']).toContain('{{count}}');
  });
});

describe('W3-14 R2 — REAL i18next resolves the seconds sentence (app init options)', () => {
  const inst = i18next.createInstance();

  beforeAll(async () => {
    // Exactly src/i18n/index.ts:31-41 minus the react binding.
    await inst.init({
      resources: {
        en: { translation: en },
        ar: { translation: ar },
      },
      lng: 'en',
      fallbackLng: 'en',
      interpolation: { escapeValue: false },
    });
  });

  it('en {count: 61} contains "61" and is NOT the base sentence', async () => {
    await inst.changeLanguage('en');
    const out = inst.t('home.errors.rateLimited', { count: 61 });
    expect(out).toContain('61');
    expect(out).not.toBe(EN['home.errors.rateLimited']);
    expect(out).not.toBe('home.errors.rateLimited');
  });

  it('en {count: 1} is the singular sentence, not the plural one', async () => {
    await inst.changeLanguage('en');
    expect(inst.t('home.errors.rateLimited', { count: 1 })).toBe(
      (EN['home.errors.rateLimited_one'] ?? '<missing _one>').replace('{{count}}', '1'),
    );
    expect(inst.t('home.errors.rateLimited', { count: 1 })).not.toBe(
      inst.t('home.errors.rateLimited', { count: 61 }),
    );
  });

  it('field absent: no opts AND {count: undefined} both render the BASE sentence', async () => {
    await inst.changeLanguage('en');
    expect(inst.t('home.errors.rateLimited')).toBe(EN['home.errors.rateLimited']);
    expect(inst.t('home.errors.rateLimited', { count: undefined })).toBe(
      EN['home.errors.rateLimited'],
    );
  });

  it('ar 1/2/3/11/61 -> >= 4 distinct sentences, no ASCII letters, 1!=2 and 3!=11 (R-6)', async () => {
    await inst.changeLanguage('ar');
    const tAr = (count: number) => inst.t('home.errors.rateLimited', { count });
    const outs = [1, 2, 3, 11, 61].map(tAr);
    for (const o of outs) {
      expect(o).not.toBe('home.errors.rateLimited');
      expect(o).not.toMatch(/[A-Za-z]/);
    }
    expect(new Set(outs).size).toBeGreaterThanOrEqual(4);
    expect(tAr(1)).not.toBe(tAr(2));
    expect(tAr(3)).not.toBe(tAr(11));
    // Base sentence stays reachable in Arabic too (field absent).
    expect(inst.t('home.errors.rateLimited')).toBe(AR['home.errors.rateLimited']);
    await inst.changeLanguage('en');
  });
});
