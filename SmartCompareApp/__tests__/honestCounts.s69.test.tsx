/**
 * S69 U6 T6 — honest counts (App Review guideline 2.3.1), client half.
 *
 * Spec R6 + review corrections 20-25 and open question F:
 *   (a) `register.benefits.daily` says "5 comparisons per day" (EN + AR) while
 *       the backend free tier is daily 3 / monthly 10 / lifetime_free 3
 *       (app/services/usage_service.py:138-143). The benefits block states
 *       the true daily AND monthly numbers (correction 24: "3 per day" alone
 *       implies ~90 a month) and is retitled "Your account includes".
 *       The backend twin tests/test_register_benefits_parity_s69.py fences the
 *       catalog value against TIER_LIMITS itself.
 *   (b) hard-coded social-proof counts reachable in onboarding go away —
 *       an explicit denylist, not the spec's `/\d[\d,]*\+/` regex, which
 *       misses 388 / 2,074 / 47 / 73% and flags the legitimate "25+
 *       retailers", "500+ BHD", "5+ peers" (correction 22):
 *         - Step15Reveal "2,000+" / "15,000+" tiles and DEFAULT_MATCH_PCT 92
 *           (rendered because nothing passes matchQuality — correction 21);
 *         - Step14Loading COUNTER_FALLBACK_TARGET 2074 and its "2,074" /
 *           "73%" defaultValues; OnboardingFlow's hard-coded
 *           cohortPeerCount={47};
 *         - catalog keys onboarding.s14.tip_2 ("2,074"), onboarding.s14.tip_1
 *           and onboarding.s13.factoid ("73%"); onboarding.s14.stage_1 has no
 *           reader (Step14Loading uses s13.stage_*) and is deleted.
 *       388 stays (it equals data/cohort_priors.json total_responses —
 *       open question F).
 *   (c) the dead `formatUsageMessage` (0 callers, still says "(Premium)") is
 *       deleted from src/services/usageService.ts.
 */

import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render } from '@testing-library/react-native';

jest.mock('expo-haptics', () => ({
  impactAsync: jest.fn().mockResolvedValue(undefined),
  ImpactFeedbackStyle: { Light: 'light', Medium: 'medium', Heavy: 'heavy' },
  __esModule: true,
}));

jest.mock('react-i18next', () => {
   
  const cat: Record<string, string> = require('../src/i18n/en.json');
   
  const t = (key: string, opts?: any) => {
    let str: string = cat[key] ?? opts?.defaultValue ?? key;
    if (opts && typeof opts === 'object') {
      for (const [k, v] of Object.entries(opts)) {
        if (k === 'defaultValue') continue;
        str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
      }
    }
    return str;
  };
  return { useTranslation: () => ({ t, i18n: { language: 'en' } }) };
});

 
const en: Record<string, string> = require('../src/i18n/en.json');
 
const ar: Record<string, string> = require('../src/i18n/ar.json');

const SRC = path.resolve(__dirname, '../src');
const read = (rel: string) => fs.readFileSync(path.join(SRC, rel), 'utf8');

/** Integers written in a catalog value (Western or Arabic-Indic digits). */
function integersIn(value: string): number[] {
  const western = value.replace(/[\u0660-\u0669]/g, (d) => String(d.charCodeAt(0) - 0x0660));
  return (western.match(/\d+/g) ?? []).map(Number);
}

function benefitIntegers(cat: Record<string, string>): number[] {
  return Object.keys(cat)
    .filter((k) => k.startsWith('register.benefits.'))
    .flatMap((k) => integersIn(cat[k]));
}

/** Every string rendered anywhere in a tree. */
function allText(screen: any): string {
  const out: string[] = [];
  const walk = (node: any) => {
    if (node == null) return;
    if (typeof node === 'string' || typeof node === 'number') {
      out.push(String(node));
      return;
    }
    if (Array.isArray(node)) {
      node.forEach(walk);
      return;
    }
    walk(node.children);
  };
  walk(screen.toJSON());
  return out.join(' | ');
}

describe('S69 U6 T6 (a) \u2014 the register benefits state the real free tier', () => {
  it.each([
    ['en', en],
    ['ar', ar],
  ])('T6.1 %s register.benefits.daily says 3 a day, not 5', (_lang, cat) => {
    const nums = integersIn(cat['register.benefits.daily'] ?? '');
    expect(nums).toContain(3);
    expect(nums).not.toContain(5);
  });

  it.each([
    ['en', en],
    ['ar', ar],
  ])('T6.2 %s the benefits block also states the monthly 10 (daily alone implies ~90 a month)', (_lang, cat) => {
    const nums = benefitIntegers(cat);
    expect(nums).toContain(10);
    expect(nums).not.toContain(5);
  });

  it('T6.3 the block is retitled "Your account includes" (EN)', () => {
    expect(en['register.benefits.title']).toBe('Your account includes');
    expect(typeof ar['register.benefits.title']).toBe('string');
    expect(ar['register.benefits.title']).not.toBe(
      '\u0627\u0644\u062d\u0633\u0627\u0628 \u0627\u0644\u0645\u062c\u0627\u0646\u064a \u064a\u0634\u0645\u0644',
    ); // «الحساب المجاني يشمل» — the old "Free account includes"
  });
});

describe('S69 U6 T6 (b) \u2014 no invented shopper counts on the onboarding screens', () => {
  it('T6.4 onboarding.s14.stage_1 (no reader) is deleted from both catalogs', () => {
    expect(en['onboarding.s14.stage_1']).toBeUndefined();
    expect(ar['onboarding.s14.stage_1']).toBeUndefined();
    const reader = read('screens/onboarding/Step14Loading.tsx');
    expect(reader).not.toMatch(/s14\.stage_1/);
  });

  it.each([
    ['onboarding.s14.tip_2', /2,?074/],
    ['onboarding.s14.tip_1', /73\s?%|\u0667\u0663/],
    ['onboarding.s13.factoid', /73\s?%|\u0667\u0663/],
  ])('T6.5 %s carries no invented count (EN + AR)', (key, invented) => {
    for (const cat of [en, ar]) {
      if (cat[key] === undefined) continue; // deleting the key is also honest
      expect(cat[key]).not.toMatch(invented);
    }
    // At least one catalog must still be in step with the other.
    expect(en[key] === undefined).toBe(ar[key] === undefined);
  });

  it('T6.6 Step15Reveal has no hard-coded "2,000+" / "15,000+" peer counts and no DEFAULT_MATCH_PCT 92', () => {
    const src = read('screens/onboarding/Step15Reveal.tsx');
    const code = src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(code).not.toMatch(/['"`]2,000\+['"`]/);
    expect(code).not.toMatch(/['"`]15,000\+['"`]/);
    expect(code).not.toMatch(/DEFAULT_MATCH_PCT\s*=\s*92\b/);
  });

  it('T6.7 Step15Reveal rendered without a real matchQuality shows no invented number', () => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { Step15Reveal } = require('../src/screens/onboarding/Step15Reveal');
    const screen = render(
      <Step15Reveal
        onNext={jest.fn()}
        profile={{
          priorities: ['quality', 'durability'],
          budget: 'mid',
          brand_attitude: 'best_of_both',
          country: 'BH',
          governorate: 'Capital',
        }}
      />,
    );
    const text = allText(screen);
    expect(text).not.toMatch(/\b92\b/);
    expect(text).not.toMatch(/15,000|2,000/);
  });

  it('T6.8 Step14Loading has no 2,074 counter fallback and no "2,074" / "73%" default copy', () => {
    const src = read('screens/onboarding/Step14Loading.tsx');
    const code = src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
    expect(code).not.toMatch(/\b2074\b/);
    expect(code).not.toMatch(/2,074/);
    expect(code).not.toMatch(/73%/);
  });

  it('T6.9 OnboardingFlow passes no hard-coded cohortPeerCount literal (was {47})', () => {
    const src = read('screens/onboarding/OnboardingFlow.tsx');
    expect(src).not.toMatch(/cohortPeerCount=\{\s*\d+\s*\}/);
  });
});

describe('S69 U6 T6 (c) \u2014 the dead usage formatter is gone', () => {
  it('T6.10 usageService no longer exports formatUsageMessage and carries no "(Premium)" copy', () => {
    const src = read('services/usageService.ts');
    expect(src).not.toMatch(/formatUsageMessage/);
    expect(src).not.toMatch(/\(Premium\)/);
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const mod = require('../src/services/usageService');
    expect(mod.formatUsageMessage).toBeUndefined();
  });
});
