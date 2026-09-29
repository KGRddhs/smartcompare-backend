/**
 * S69 U3 T2 — Step05Trust tells the truth about what reaches OpenAI (R5, PM-3).
 *
 * Spec: docs/investigations/2026-09-29-session-69-state/U3_AI_CONSENT_SPEC.md R5,
 * as corrected by its spec review (point 8 + the Step05Trust copy proposal).
 *
 * Measured at base f40a44d3:
 *   - privacy_never_body promises "Your budget … never shared", while the
 *     budget tier is in the verdict system prompt
 *     (app/services/extraction_service.py:1943 "Budget level: {budget}",
 *     appended at :2561 via _build_preferences_prompt).
 *   - the subtitle counts "Three" off-limits items (en.json:562, ar.json:559);
 *     with the budget gone only two remain (name, email).
 *   - privacy_anon_body says "Your queries help MYEZ get smarter. We strip your
 *     name, email, and identity first." — a data-use claim, and false for
 *     MYEZ's own storage (comparisons are saved with user_id). The rewording
 *     states what is sent to OpenAI (product names + the preferences above) and
 *     that name / email / account are not: no OpenAI request carries a
 *     user / safety_identifier / metadata field and no prompt module reads
 *     email, display_name or user_id.
 *   - the Step05Trust.tsx defaultValues mirror the old copy and must move with
 *     the catalogs (the i18n mock returns keys, so the defaults are read by
 *     rendering with a t() that returns them).
 *
 * The Profile AI-sharing toggle (R4) is out of scope, so no copy here may
 * promise an opt-out.
 */

import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render } from '@testing-library/react-native';

let mockMode: 'default' | 'en' | 'ar' = 'default';
jest.mock('react-i18next', () => {
  const catalogs: Record<string, Record<string, string>> = {
    en: require('../../src/i18n/en.json'),
    ar: require('../../src/i18n/ar.json'),
  };
  const t = (key: string, opts?: any) => {
    const fallback = typeof opts === 'string' ? opts : opts?.defaultValue;
    if (mockMode === 'default') return fallback ?? key;
    return catalogs[mockMode][key] ?? fallback ?? key;
  };
  return { useTranslation: () => ({ t, i18n: { language: mockMode === 'ar' ? 'ar' : 'en' } }) };
});

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { Step05Trust } = require('../../src/screens/onboarding/Step05Trust');
const EN: Record<string, string> = require('../../src/i18n/en.json');
const AR: Record<string, string> = require('../../src/i18n/ar.json');

const SRC = fs.readFileSync(
  path.join(__dirname, '..', '..', 'src', 'screens', 'onboarding', 'Step05Trust.tsx'),
  'utf8',
);

const BRAND_AR = 'ميّز'; // ميّز
const AR_DIACRITICS = /[ً-ْٰ]/;
// «ميزانية» (budget) — covers ميزانيتك / الميزانية
const AR_BUDGET = 'ميزاني';
// «ثلاث» (three)
const AR_THREE = 'ثلاث';
const OPT_OUT_EN = /opt[\s-]?out|turn (it )?off|switch (it )?off|toggle|disable|settings/i;

/** Every string rendered under a node. */
function textOf(node: any): string {
  const out: string[] = [];
  const walk = (n: any) => {
    if (n == null) return;
    if (typeof n === 'string' || typeof n === 'number') {
      out.push(String(n));
      return;
    }
    if (Array.isArray(n)) {
      n.forEach(walk);
      return;
    }
    walk(n.children);
  };
  walk(node);
  return out.join(' ');
}

function renderRows(mode: 'default' | 'en' | 'ar') {
  mockMode = mode;
  const screen = render(<Step05Trust onNext={jest.fn()} />);
  return {
    screen,
    use: textOf(screen.getByTestId('trust-row-use')),
    anon: textOf(screen.getByTestId('trust-row-anon')),
    never: textOf(screen.getByTestId('trust-row-never')),
    all: textOf(screen.toJSON()),
  };
}

/** The defaultValue literal passed for `key` in Step05Trust.tsx. */
function defaultValueIn(src: string, key: string): string {
  const at = src.indexOf(`'${key}'`);
  if (at < 0) return '';
  const tail = src.slice(at, at + 600);
  const m = /defaultValue:\s*(?:\n\s*)?(['"])((?:\\.|(?!\1).)*)\1/.exec(tail);
  return m ? m[2].replace(/\\'/g, "'").replace(/\\"/g, '"') : '';
}

beforeEach(() => {
  mockMode = 'default';
});

describe('S69 U3 T2 — the budget promise is gone', () => {
  it('T2.1 EN privacy_never_body no longer lists the budget', () => {
    expect(EN['onboarding.s5.privacy_never_body']).toBeTruthy();
    expect(EN['onboarding.s5.privacy_never_body']).not.toMatch(/budget/i);
    expect(EN['onboarding.s5.privacy_never_body']).toMatch(/name/i);
    expect(EN['onboarding.s5.privacy_never_body']).toMatch(/email/i);
  });

  it('T2.2 AR privacy_never_body no longer lists the budget («ميزانيتك»)', () => {
    expect(AR['onboarding.s5.privacy_never_body']).toBeTruthy();
    expect(AR['onboarding.s5.privacy_never_body']).not.toContain(AR_BUDGET);
  });

  it('T2.3 the Step05Trust.tsx defaultValue for privacy_never_body no longer lists the budget', () => {
    const dv = defaultValueIn(SRC, 'onboarding.s5.privacy_never_body');
    expect(dv.length).toBeGreaterThan(0);
    expect(dv).not.toMatch(/budget/i);
  });

  it('T2.4 the subtitle no longer counts "Three" off-limits items (EN, AR, defaultValue)', () => {
    expect(EN['onboarding.s5.subtitle']).not.toMatch(/\bthree\b/i);
    expect(AR['onboarding.s5.subtitle']).not.toContain(AR_THREE);
    const dv = defaultValueIn(SRC, 'onboarding.s5.subtitle');
    expect(dv.length).toBeGreaterThan(0);
    expect(dv).not.toMatch(/\bthree\b/i);
  });

  it('T2.5 no rendered row (EN or AR) promises the budget is never shared', () => {
    const en = renderRows('en');
    expect(en.never).not.toMatch(/budget/i);
    en.screen.unmount();
    const ar = renderRows('ar');
    expect(ar.never).not.toContain(AR_BUDGET);
  });
});

describe('S69 U3 T2 — the reworded data-use claim is present and true', () => {
  it('T2.6 EN privacy_anon_body names OpenAI and MYEZ, and drops "get smarter" / "strip … first"', () => {
    const s = EN['onboarding.s5.privacy_anon_body'] ?? '';
    expect(s).toMatch(/OpenAI/);
    expect(s).toMatch(/\bMYEZ\b/);
    expect(s).toMatch(/product name/i);
    expect(s).toMatch(/\bname\b/i);
    expect(s).toMatch(/\bemail\b/i);
    expect(s).not.toMatch(/smarter/i);
    expect(s).not.toMatch(/\bstrip/i);
    expect(s).not.toMatch(/Qaren/i);
    expect(s).not.toMatch(OPT_OUT_EN);
  });

  it('T2.7 AR privacy_anon_body names OpenAI and ميّز, and drops «ننزع» (we strip) / «التحسّن» (get smarter)', () => {
    const s = AR['onboarding.s5.privacy_anon_body'] ?? '';
    expect(s).toMatch(/OpenAI/);
    expect(s).toContain(BRAND_AR);
    expect(s).not.toContain('ننزع'); // ننزع
    expect(s).not.toContain('التحس'); // التحس…
  });

  it('T2.8 the rendered fallback copy (defaultValues) carries the reworded claim and no budget promise', () => {
    const d = renderRows('default');
    expect(d.anon).toMatch(/OpenAI/);
    expect(d.anon).not.toMatch(/smarter/i);
    expect(d.never).not.toMatch(/budget/i);
    expect(d.all).not.toMatch(/\bThree\b/);
  });

  it('T2.9 each changed defaultValue equals its en.json value (subtitle, anon, never)', () => {
    for (const key of [
      'onboarding.s5.subtitle',
      'onboarding.s5.privacy_anon_body',
      'onboarding.s5.privacy_never_body',
    ]) {
      expect({ key, dv: defaultValueIn(SRC, key) }).toEqual({ key, dv: EN[key] });
    }
    // ...and the reworded copy is what they now say.
    expect(defaultValueIn(SRC, 'onboarding.s5.privacy_anon_body')).toMatch(/OpenAI/);
  });

  it('T2.10 the rewritten Arabic strings carry no diacritics other than the brand token', () => {
    for (const key of [
      'onboarding.s5.subtitle',
      'onboarding.s5.privacy_anon_body',
      'onboarding.s5.privacy_never_body',
    ]) {
      const v = (AR[key] ?? '').split(BRAND_AR).join('');
      expect({ key, diacritic: AR_DIACRITICS.test(v) }).toEqual({ key, diacritic: false });
    }
  });
});

// Item 4 (the two SOUND adversaries): the body under this heading now states
// what reaches OpenAI, so the old heading "What's anonymized" (AR «ما يُجهَّل»,
// with diacritics) no longer described it.
const HEAD_EN = 'What reaches OpenAI';
const HEAD_AR = 'ما يصل إلى OpenAI';
// «يجهل» — the root of «يُجهَّل» (anonymized), compared with diacritics removed
const AR_ANONYMIZED = 'يجهل';
const stripDiacritics = (s: string) => s.replace(/[ً-ْٰ]/g, '');

describe('S69 U3 T2 — the heading over the rewritten body names what it describes', () => {
  it('T2.11 privacy_anon_head is "What reaches OpenAI" (EN) and «ما يصل إلى OpenAI» (AR); the defaultValue equals EN', () => {
    expect(EN['onboarding.s5.privacy_anon_head']).toBe(HEAD_EN);
    expect(AR['onboarding.s5.privacy_anon_head']).toBe(HEAD_AR);
    expect(defaultValueIn(SRC, 'onboarding.s5.privacy_anon_head')).toBe(HEAD_EN);
  });

  it('T2.12 the rendered anon row carries the new heading (fallback, EN, AR) and no "anonymized" / «يُجهَّل»', () => {
    const d = renderRows('default');
    expect(d.anon).toContain(HEAD_EN);
    expect(d.anon).not.toMatch(/anonymi[sz]/i);
    d.screen.unmount();
    const en = renderRows('en');
    expect(en.anon).toContain(HEAD_EN);
    expect(en.anon).not.toMatch(/anonymi[sz]/i);
    en.screen.unmount();
    const ar = renderRows('ar');
    expect(ar.anon).toContain(HEAD_AR);
    expect(stripDiacritics(ar.anon)).not.toContain(AR_ANONYMIZED);
  });

  it('T2.13 the Arabic heading carries no diacritics', () => {
    const v = AR['onboarding.s5.privacy_anon_head'] ?? '';
    expect(v.length).toBeGreaterThan(0);
    expect(AR_DIACRITICS.test(v)).toBe(false);
  });
});
