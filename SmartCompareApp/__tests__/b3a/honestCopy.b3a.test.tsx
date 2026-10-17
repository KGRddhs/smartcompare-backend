/**
 * S79 B3-A item 4 -- honest copy (spec C4, rows R26-R32; rulings A8, A12
 * (MR10), A13).
 *
 * The copy contract is the fixture __tests__/fixtures/b3a_copy.json (every
 * EN / AR string; this source stays ASCII, Arabic only appears as \u escapes
 * in patterns). Failure messages print keys, never Arabic values.
 */
/* eslint-disable @typescript-eslint/no-require-imports */

import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render } from '@testing-library/react-native';
import { createInstance } from 'i18next';

const APP = path.resolve(__dirname, '../..');
const EN: Record<string, string> = require('../../src/i18n/en.json');
const AR: Record<string, string> = require('../../src/i18n/ar.json');
const FX = require('../fixtures/b3a_copy.json') as {
  changed_keys: string[];
  new_keys: string[];
  learning_keys: string[];
  brand_keys: string[];
  en: Record<string, string>;
  ar: Record<string, string>;
};
const POLICY = require('../../src/i18n/.copy-policy.json') as {
  banned_en?: { pattern: string; label: string }[];
  banned_ar?: { pattern: string; label: string }[];
  scary_vocab_en?: string[];
  scary_vocab_ar?: string[];
};

const ALL_KEYS = [...FX.changed_keys, ...FX.new_keys, ...FX.learning_keys];

const AR_LETTER = '[\\u0600-\\u06FF]';
const BRAND_AR = 'ميّز';
const VERB_AR = 'قارن';
const wordRe = (w: string, flags = 'u') =>
  new RegExp(`(?<!${AR_LETTER})[\\u0628\\u0644\\u0648]?${w}(?!${AR_LETTER})`, flags);
const AR_DIACRITICS = /[ً-ْٰ]/;

let mockLang: 'en' | 'ar' = 'en';
function realT(lng: 'en' | 'ar') {
  const inst = createInstance();
  inst.init({
    lng,
    fallbackLng: 'en',
    resources: { en: { translation: EN }, ar: { translation: AR } },
    interpolation: { escapeValue: false },
    initAsync: false,
    initImmediate: false,
  } as any);
  return inst.t.bind(inst) as unknown as (key: string, params?: Record<string, unknown>) => string;
}

jest.mock('react-i18next', () => ({
  useTranslation: () => {
    const { createInstance: ci } = require('i18next');
    const en = require('../../src/i18n/en.json');
    const ar = require('../../src/i18n/ar.json');
    const inst = ci();
    inst.init({
      lng: mockLang,
      fallbackLng: 'en',
      resources: { en: { translation: en }, ar: { translation: ar } },
      interpolation: { escapeValue: false },
      initAsync: false,
      initImmediate: false,
    });
    return { t: inst.t.bind(inst), i18n: { language: mockLang } };
  },
}));

const mockSmartPick = jest.fn();
jest.mock('../../src/services/api', () => ({
  getHomeSmartPick: () => mockSmartPick(),
  getHomeQuickCategories: () => Promise.resolve({ categories: [] }),
  getHomeSavings: () => Promise.resolve({ savings: null }),
  getHomeTrending: () => Promise.resolve({ items: [] }),
}));

function basePick(overrides: Record<string, any> = {}) {
  return {
    comparison_id: 'cmp_1',
    winner_name: 'Galaxy S24',
    runner_up_name: 'iPhone 15',
    winner_price_bhd: 12.345,
    runner_up_price_bhd: 8.5,
    reason_key: 'home.smart_pick.reason.fallback',
    reason_params: {},
    category: 'electronics',
    updated_at: '3d ago',
    winner_sub: null,
    runner_up_sub: null,
    verdict_short: null,
    winner_image_url: null,
    runner_up_image_url: null,
    ...overrides,
  };
}

/**
 * The options object literal of a t() call, given the index right after its
 * key argument: `, { ... }` with balanced braces (string literals skipped),
 * or null when the call has no object second argument.
 */
function optionsAfter(src: string, from: number): string | null {
  let j = from;
  while (j < src.length && /\s/.test(src[j])) j += 1;
  if (src[j] !== ',') return null;
  j += 1;
  while (j < src.length && /\s/.test(src[j])) j += 1;
  if (src[j] !== '{') return null;
  let depth = 0;
  let quote: string | null = null;
  for (let e = j; e < src.length; e += 1) {
    const c = src[e];
    if (quote) {
      if (c === '\\') e += 1;
      else if (c === quote) quote = null;
      continue;
    }
    if (c === "'" || c === '"' || c === '`') quote = c;
    else if (c === '{') depth += 1;
    else if (c === '}') {
      depth -= 1;
      if (depth === 0) return src.slice(j, e + 1);
    }
  }
  return null;
}

/** Non-ASCII escaped, so a failure message never prints Arabic. */
const esc = (v: string) => v.replace(/[^ -~]/g, (c) => '\\u' + c.charCodeAt(0).toString(16).padStart(4, '0'));

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
  return out.join('');
}

async function renderPick(lang: 'en' | 'ar', overrides: Record<string, any>) {
  mockLang = lang;
  mockSmartPick.mockResolvedValue({ smart_pick: basePick(overrides), empty_state: false });
  const { SmartPickCard } = require('../../src/components/HomeEditorialSections');
  const screen = render(<SmartPickCard />);
  await screen.findByTestId('home-smart-pick');
  return screen;
}

function testIdOrder(json: any): string[] {
  const out: string[] = [];
  const walk = (n: any) => {
    if (n == null || typeof n !== 'object') return;
    if (Array.isArray(n)) {
      n.forEach(walk);
      return;
    }
    if (n.props && typeof n.props.testID === 'string') out.push(n.props.testID);
    walk(n.children);
  };
  walk(json);
  return out;
}

beforeEach(() => {
  mockLang = 'en';
  mockSmartPick.mockReset();
});

describe('B3-A honest copy (C4)', () => {
  it('r26 the 12 changed values (and the A13 learning values) equal the fixture in EN and AR', () => {
    const bad: string[] = [];
    for (const k of [...FX.changed_keys, ...FX.learning_keys]) {
      if (EN[k] !== FX.en[k]) bad.push(`en:${k}`);
      if (AR[k] !== FX.ar[k]) bad.push(`ar:${k}`);
    }
    expect(bad).toEqual([]);
  });

  it('r27 the 5 new keys exist in both catalogs with the fixture values; key sets stay equal', () => {
    const bad: string[] = [];
    for (const k of FX.new_keys) {
      if (EN[k] !== FX.en[k]) bad.push(`en:${k}`);
      if (AR[k] !== FX.ar[k]) bad.push(`ar:${k}`);
    }
    expect(bad).toEqual([]);
    const enKeys = Object.keys(EN).sort();
    const arKeys = Object.keys(AR).sort();
    expect(enKeys.filter((k) => !(k in AR))).toEqual([]);
    expect(arKeys.filter((k) => !(k in EN))).toEqual([]);
  });

  it('r28 no dishonest claim remains in any EN / AR value', () => {
    const bad: string[] = [];
    for (const [k, v] of Object.entries(EN)) {
      if (typeof v !== 'string') continue;
      if (/25\+/.test(v)) bad.push(`en 25+:${k}`);
      if (/even offline/i.test(v)) bad.push(`en offline:${k}`);
      if (/calibrate to your region/i.test(v)) bad.push(`en calibrate:${k}`);
      if (/credits are waiting/i.test(v)) bad.push(`en credits:${k}`);
    }
    if (/people like you\.?$/i.test(EN['onboarding.s1.subtitle'] ?? '')) bad.push('en people-like-you');
    for (const k of ['onboarding.s1.quote_1', 'onboarding.s1.quote_2', 'onboarding.s1.quote_3']) {
      if (/^Picked /.test(EN[k] ?? '')) bad.push(`en picked:${k}`);
    }
    // AR: "25 (+) stores" / "stores 25" (Western or Arabic-Indic digits, MR10)
    // and "even without internet".
    const AR_25_STORE = /(?:25|٢٥)\+?\s*\+?\s*مت(?:ا)?جر|مت(?:ا)?جر\S*\s*\+?(?:25|٢٥)/u;
    const AR_OFFLINE = /حتى\s+(?:بدون|دون)\s+ا?ل?إنترنت/u;
    for (const [k, v] of Object.entries(AR)) {
      if (typeof v !== 'string') continue;
      if (AR_25_STORE.test(v)) bad.push(`ar 25-store:${k}`);
      if (/(?:25|٢٥)\+/u.test(v)) bad.push(`ar 25+:${k}`);
      if (AR_OFFLINE.test(v)) bad.push(`ar offline:${k}`);
    }
    expect(bad).toEqual([]);
  });

  it('r28b [PIN] the loader keeps the reworded keys in its default rotation (keys kept, values changed; closes M20)', () => {
    const src = fs.readFileSync(path.join(APP, 'src/screens/LoadingScreenVariants.tsx'), 'utf8').replace(/\r\n/g, '\n');
    const block = (name: string) => {
      const m = src.match(new RegExp(`const ${name} = \\[([\\s\\S]*?)\\]`));
      expect({ name, found: m !== null }).toEqual({ name, found: true });
      return Array.from((m as RegExpMatchArray)[1].matchAll(/'([^']+)'/g)).map((x) => x[1]);
    };
    expect(block('DEFAULT_COMPARISON_TIP_KEYS')).toEqual(
      expect.arrayContaining(['loading.tip.cross_checks', 'loading.tip.save_offline']),
    );
    expect(block('DEFAULT_COMPARISON_STAGE_KEYS')).toEqual(expect.arrayContaining(['loading.stage.cross_checking']));
  });

  it('r28c (A13) no learning or credits claim remains on the A13 keys (EN)', () => {
    const bad: string[] = [];
    for (const k of FX.learning_keys) {
      const v = EN[k] ?? '';
      if (/train/i.test(v)) bad.push(`train:${k}`);
      if (/refin/i.test(v)) bad.push(`refine:${k}`);
      if (/real buys/i.test(v)) bad.push(`real-buys:${k}`);
      if (/credit/i.test(v)) bad.push(`credit:${k}`);
      if (/cohort peers/i.test(v)) bad.push(`cohort-peers:${k}`);
    }
    expect(bad).toEqual([]);
  });

  it('r29 stale defaultValue literals are gone (each equals the new EN value, or there is none)', () => {
    // (a) the named files (fix round FA6 adds Step14Loading and Step15Reveal).
    const files: Record<string, string[]> = {
      'src/screens/onboarding/Step04Country.tsx': ['onboarding.s4.subtitle'],
      'src/screens/LoginScreen.tsx': ['auth.welcomeBackSub'],
      'src/screens/onboarding/Step01Welcome.tsx': [
        'onboarding.s1.quote_1',
        'onboarding.s1.quote_2',
        'onboarding.s1.quote_3',
      ],
      'src/screens/onboarding/Step14Loading.tsx': ['loading.cohort.caption'],
      'src/screens/onboarding/Step15Reveal.tsx': ['onboarding.s15.subtitle'],
    };
    const bad: string[] = [];
    for (const [rel, keys] of Object.entries(files)) {
      const src = fs.readFileSync(path.join(APP, rel), 'utf8').replace(/\r\n/g, '\n');
      for (const k of keys) {
        let from = 0;
        for (;;) {
          const idx = src.indexOf(`'${k}'`, from);
          if (idx === -1) break;
          from = idx + 1;
          const end = src.indexOf('})', idx);
          const call = src.slice(idx, end === -1 ? idx + 400 : end);
          const m = call.match(/defaultValue:\s*(['"`])((?:\\.|(?!\1)[\s\S])*)\1/);
          if (m && m[2] !== FX.en[k]) bad.push(`${rel}:${k}`);
        }
      }
    }
    expect(bad).toEqual([]);

    // (b) fix round FA6: every t('<key>' ...) call in src/**/*.ts(x) for a
    // fixture key (changed, new or learning) that carries a defaultValue
    // carries the fixture EN value.
    const srcFiles: string[] = [];
    const walk = (dir: string) => {
      for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
        const p = path.join(dir, ent.name);
        if (ent.isDirectory()) walk(p);
        else if (/\.tsx?$/.test(ent.name)) srcFiles.push(path.relative(APP, p).split(path.sep).join('/'));
      }
    };
    walk(path.join(APP, 'src'));
    expect(Object.keys(files).filter((f) => !srcFiles.includes(f))).toEqual([]);
    const escRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const badAll: string[] = [];
    for (const rel of srcFiles) {
      const src = fs.readFileSync(path.join(APP, rel), 'utf8').replace(/\r\n/g, '\n');
      for (const k of ALL_KEYS) {
        const re = new RegExp(`\\bt\\(\\s*(['"])${escRe(k)}\\1`, 'g');
        let hit: RegExpExecArray | null;
        while ((hit = re.exec(src)) !== null) {
          const opts = optionsAfter(src, hit.index + hit[0].length);
          if (opts === null) continue;
          const m = opts.match(/defaultValue:\s*(['"`])((?:\\.|(?!\1)[\s\S])*)\1/);
          if (m && m[2] !== FX.en[k]) badAll.push(`${rel}:${k}`);
        }
      }
    }
    expect(badAll).toEqual([]);
  });

  it('r30 the welcome screen labels the quotes as examples, above the first quote', () => {
    mockLang = 'en';
    const { Step01Welcome } = require('../../src/screens/onboarding/Step01Welcome');
    const screen = render(<Step01Welcome onNext={jest.fn()} />);
    const label = screen.queryByTestId('welcome-examples-label');
    expect(label).not.toBeNull();
    expect(textOf(label)).toBe(FX.en['onboarding.s1.examples_label']);
    const order = testIdOrder(screen.toJSON());
    expect(order.indexOf('welcome-examples-label')).toBeGreaterThanOrEqual(0);
    expect(order.indexOf('welcome-examples-label')).toBeLessThan(order.indexOf('welcome-quote-1'));
  });

  it('r31 [PIN] new and changed values respect the copy and brand fences', () => {
    const bad: string[] = [];
    const bannedEn = (POLICY.banned_en ?? []).map((b) => new RegExp(b.pattern, 'i'));
    const bannedAr = (POLICY.banned_ar ?? []).map((b) => new RegExp(b.pattern, ''));
    const scaryEn = (POLICY.scary_vocab_en ?? []).map((w) => w.toLowerCase());
    const scaryAr = POLICY.scary_vocab_ar ?? [];
    const visible = (v: string) => v.replace(/\{\{[^}]+\}\}/g, '');
    for (const k of ALL_KEYS) {
      const en = visible(FX.en[k] ?? '');
      const ar = visible(FX.ar[k] ?? '');
      if (!en || !ar) bad.push(`missing:${k}`);
      bannedEn.forEach((re, i) => re.test(en) && bad.push(`banned_en#${i}:${k}`));
      bannedAr.forEach((re, i) => re.test(ar) && bad.push(`banned_ar#${i}:${k}`));
      scaryEn.forEach((w) => en.toLowerCase().includes(w) && bad.push(`scary_en:${k}`));
      scaryAr.forEach((w) => ar.includes(w) && bad.push(`scary_ar:${k}`));
      const myez = (en.match(/MYEZ/g) ?? []).length;
      const brand = (ar.match(wordRe(BRAND_AR, 'gu')) ?? []).length;
      const want = FX.brand_keys.includes(k) ? 1 : 0;
      if (myez !== want) bad.push(`myez=${myez}:${k}`);
      if (brand !== want) bad.push(`brand_ar=${brand}:${k}`);
      if (wordRe(VERB_AR).test(ar)) bad.push(`verb_ar:${k}`);
    }
    expect(bad).toEqual([]);
  });

  it('r31b (A8 / MR11) new and changed AR values carry no harakat, shadda or tanween outside the brand', () => {
    const bad: string[] = [];
    for (const k of ALL_KEYS) {
      const stripped = (FX.ar[k] ?? '').split(BRAND_AR).join('');
      if (AR_DIACRITICS.test(stripped)) bad.push(`fixture:${k}`);
      const live = (AR[k] ?? '').split(BRAND_AR).join('');
      if (AR_DIACRITICS.test(live)) bad.push(`catalog:${k}`);
    }
    expect(bad).toEqual([]);
  });

  it('r32 the tailored-pick card shows localised category and time labels (EN)', async () => {
    const t = realT('en');
    let s = await renderPick('en', { category: 'electronics', updated_at: 'Older' });
    expect(textOf(s.getByTestId('home-smart-pick-category'))).toBe(t('home.categories.electronics').toUpperCase());
    expect(textOf(s.getByTestId('home-smart-pick-updated'))).toBe(FX.en['home.smart_pick.updated_older']);
    s.unmount();

    s = await renderPick('en', { category: 'other', updated_at: '3d ago' });
    expect(s.queryByTestId('home-smart-pick-category')).toBeNull();
    expect(textOf(s.getByTestId('home-smart-pick-updated'))).toBe(t('time.daysAgo', { count: 3 }));
    s.unmount();

    s = await renderPick('en', { category: 'gadgets', updated_at: 'Just now' });
    expect(s.queryByTestId('home-smart-pick-category')).toBeNull();
    expect(textOf(s.getByTestId('home-smart-pick-updated'))).toBe(t('time.justNow'));
    s.unmount();

    s = await renderPick('en', { category: 'electronics', updated_at: 'Recently' });
    expect(s.queryByTestId('home-smart-pick-updated')).toBeNull();
    s.unmount();
  });

  it('r32 the tailored-pick card shows localised category and time labels (AR)', async () => {
    const t = realT('ar');
    let s = await renderPick('ar', { category: 'electronics', updated_at: 'Older' });
    expect(esc(textOf(s.getByTestId('home-smart-pick-category')))).toBe(esc(t('home.categories.electronics').toUpperCase()));
    expect(esc(textOf(s.getByTestId('home-smart-pick-updated')))).toBe(esc(FX.ar['home.smart_pick.updated_older']));
    s.unmount();
    s = await renderPick('ar', { category: 'electronics', updated_at: '3d ago' });
    expect(esc(textOf(s.getByTestId('home-smart-pick-updated')))).toBe(esc(t('time.daysAgo', { count: 3 })));
    s.unmount();
  });
});
