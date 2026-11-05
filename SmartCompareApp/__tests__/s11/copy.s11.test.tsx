/**
 * S81-11 RED -- the catalog rows (spec 3 KEYS table + C18, as amended by
 * rulings R-S11-11, R-S11-13, R-S11-18, R-S11-22, R-S11-30, R-S11-32,
 * R-S11-33, R-S11-36) and the Home savings banner (A6, C7).
 *
 * The deletion set is the spec's 23 MINUS the six home.savings.count_* keys
 * (R-S11-11): 17 keys. The ADD set is the spec's 12 PLUS the ruling keys
 * results.price.listedOn / listedOnNoStore (R-S11-13) and
 * results.price.checkedEarlier (R-S11-18): 15 keys. Leaf count per catalog:
 * 1,013 - 17 + 15 = 1,011, parity 0.
 * The A5 sweep applies to string literals and catalog values only, never
 * comments (R-S11-15 / RC9).
 */

import React from 'react';
import * as fs from 'fs';
import * as path from 'path';
import { render, waitFor, act } from '@testing-library/react-native';

jest.mock('react-native-reanimated', () => {
  const real = jest.requireActual('react-native-reanimated');
  return { __esModule: true, ...real, default: real.default ?? real };
});

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      let str = (opts?.defaultValue as string) ?? key;
      if (opts) {
        for (const [k, v] of Object.entries(opts)) {
          if (k === 'defaultValue') continue;
          str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
        }
      }
      return str;
    },
  }),
}));

const mockGetHomeSavings = jest.fn();
jest.mock('../../src/services/api', () => ({
  getHomeSmartPick: () => Promise.resolve(null),
  getHomeQuickCategories: () => Promise.resolve({ categories: [] }),
  getHomeSavings: () => mockGetHomeSavings(),
  getHomeTrending: () => Promise.resolve({ items: [] }),
  trackEvent: jest.fn(),
}));

const ROOT = path.resolve(__dirname, '../..');
const read = (rel: string) => fs.readFileSync(path.join(ROOT, rel), 'utf8').replace(/\r\n/g, '\n');
const EN = JSON.parse(read('src/i18n/en.json')) as Record<string, string>;
const AR = JSON.parse(read('src/i18n/ar.json')) as Record<string, string>;
const POLICY = JSON.parse(read('src/i18n/.copy-policy.json')) as any;

const ADD_EXACT: Record<string, string> = {
  'home.categories.fragrancesOnly': 'Fragrances only for now',
  'home.categories.comingSoon': 'Soon',
  'home.categories.comingSoonToast': '{{category}} is coming soon. Fragrances are ready now.',
  'home.errors.categoryNotLive': 'We compare fragrances for now. More categories are coming soon.',
  'home.errors.insufficientDataReason.same_identity':
    'Those two look like the same product. Pick two different fragrances to compare.',
  'home.errors.insufficientDataReason.placeholder_identity':
    'We need clearer names to tell which products these are. Add the brand and the fragrance name.',
  'home.errors.insufficientDataReason.category_conflict':
    'Those two are different kinds of product. Pick two fragrances to compare.',
  'results.honest.notListed': 'Not listed by the stores we can read yet',
  'results.price.asOf': '{{store}}, as of {{date}}',
  'results.price.asOfNoStore': 'As of {{date}}',
  'results.price.lastSeen': '{{store}}, last seen {{date}}',
  'results.price.lastSeenNoStore': 'Last seen {{date}}',
};

/** Ruling-added keys: presence + placeholders pinned, wording GREEN's. */
const ADD_RULING: Record<string, string[]> = {
  'results.price.listedOn': ['date', 'store'],
  'results.price.listedOnNoStore': ['date'],
  'results.price.checkedEarlier': [],
};

const CHANGE_EXACT: Record<string, string> = {
  'home.hero': 'Compare two fragrances.',
  'home.compare.box_a_text': 'Product A \u00b7 e.g. Dior Sauvage EDP',
  'home.compare.box_b_text': 'Product B \u00b7 e.g. Bleu de Chanel EDP',
  'onboarding.s1.quote_1': 'Sauvage or Bleu de Chanel? See their prices and details side by side.',
  'onboarding.s1.quote_2': 'Two oud perfumes? See which one fits your budget.',
  'onboarding.s1.quote_3': 'EDP or EDT of the same scent? See how size and price compare.',
  'referrals.share.messageWithLink':
    'I overthink every purchase. MYEZ helps me pick between two fragrances. Try it: {{link}} (or use code {{code}} in the app)',
};

/** Ruling-reworded keys (wording GREEN's, constraints pinned). */
const CHANGE_RULING = [
  'home.errors.insufficientData',
  'home.errors.comparison',
  'onboarding.s17.tag_echoes_body',
];

const DELETED = [
  'results.cohort_badge',
  'home.savings.eyebrow',
  'home.savings.amount',
  'profile.month.savings',
  'history.hero.savings',
  'home.categories.nudge',
  'home.cat.electronics',
  'home.cat.skincare',
  'home.cat.supplements',
  'home.cat.makeup',
  'loading.tip.peer_prioritize',
  'results.tips.cohort_priority',
  'cohort.trainedBy',
  'onboarding.s14.cohort_footer',
  'profile.styleProfile.basedOn',
  'profile.styleProfile.peersInGovernorate',
  'referrals.share.toast.confirm',
];

const KEPT_COUNT_KEYS = ['zero', 'one', 'two', 'few', 'many', 'other'].map(
  (f) => `home.savings.count_${f}`,
);

const placeholders = (s: string) => (s.match(/\{\{(\w+)\}\}/g) ?? []).map((x) => x.slice(2, -2)).sort();
const NEW_OR_CHANGED = [
  ...Object.keys(ADD_EXACT),
  ...Object.keys(ADD_RULING),
  ...Object.keys(CHANGE_EXACT),
  ...CHANGE_RULING,
];

describe('S81-11 F1 -- ADD / CHANGE / DELETE (both catalogs)', () => {
  it('every spec ADD key exists with its exact EN value and a non-empty AR value', () => {
    for (const [k, v] of Object.entries(ADD_EXACT)) {
      expect({ k, en: EN[k] }).toEqual({ k, en: v });
      expect({ k, ar: typeof AR[k] === 'string' && AR[k].trim().length > 0 }).toEqual({ k, ar: true });
      expect({ k, ph: placeholders(AR[k] ?? '') }).toEqual({ k, ph: placeholders(v) });
    }
  });

  it('every ruling ADD key exists in both catalogs with its placeholder set', () => {
    for (const [k, ph] of Object.entries(ADD_RULING)) {
      expect({ k, en: typeof EN[k] }).toEqual({ k, en: 'string' });
      expect({ k, ar: typeof AR[k] }).toEqual({ k, ar: 'string' });
      expect({ k, ph: placeholders(EN[k] ?? '') }).toEqual({ k, ph: [...ph].sort() });
      expect({ k, ph: placeholders(AR[k] ?? '') }).toEqual({ k, ph: [...ph].sort() });
    }
  });

  it('every CHANGE key carries its new EN value; AR is non-empty and not English', () => {
    for (const [k, v] of Object.entries(CHANGE_EXACT)) {
      expect({ k, en: EN[k] }).toEqual({ k, en: v });
      expect({ k, ar: (AR[k] ?? '') !== (EN[k] ?? '') && (AR[k] ?? '').length > 0 }).toEqual({ k, ar: true });
    }
    // The brand form, {{link}} and {{code}} stay in the share copy.
    expect(AR['referrals.share.messageWithLink']).toMatch(/\{\{link\}\}/);
    expect(AR['referrals.share.messageWithLink']).toMatch(/\{\{code\}\}/);
  });

  it('R-S11-22: insufficientData / comparison are fragrance-neutral (brand and name, no model)', () => {
    for (const k of ['home.errors.insufficientData', 'home.errors.comparison']) {
      expect({ k, model: /\bmodel\b/i.test(EN[k] ?? 'model') }).toEqual({ k, model: false });
      expect(EN[k]).toMatch(/brand/i);
      expect(EN[k]).toMatch(/name/i);
      expect(typeof AR[k]).toBe('string');
    }
  });

  it('R-S11-32: onboarding.s17.tag_echoes_body carries no digit in either catalog', () => {
    const k = 'onboarding.s17.tag_echoes_body';
    expect(typeof EN[k]).toBe('string');
    expect(EN[k]).not.toMatch(/[0-9]/);
    expect(AR[k]).not.toMatch(/[0-9\u0660-\u0669]/);
  });

  it('the 17 deleted keys are absent from both catalogs (R-S11-11 / R-S11-36)', () => {
    expect(DELETED.filter((k) => k in EN)).toEqual([]);
    expect(DELETED.filter((k) => k in AR)).toEqual([]);
  });

  it('PIN R-S11-11: the six home.savings.count_* keys stay in both catalogs', () => {
    for (const k of KEPT_COUNT_KEYS) {
      expect(typeof EN[k]).toBe('string');
      expect(typeof AR[k]).toBe('string');
    }
  });

  it('parity 0 and 1,011 leaves per catalog', () => {
    const e = Object.keys(EN);
    const a = new Set(Object.keys(AR));
    expect(e.filter((k) => !a.has(k))).toEqual([]);
    expect([...a].filter((k) => !(k in EN))).toEqual([]);
    expect(e.length).toBe(1013 - DELETED.length + Object.keys(ADD_EXACT).length + Object.keys(ADD_RULING).length);
  });
});

describe('S81-11 F2 -- the new and changed values obey the copy policy', () => {
  it('no banned / scary pattern; no EN digit outside {{...}}', () => {
    const hits: string[] = [];
    for (const k of NEW_OR_CHANGED) {
      const en = EN[k];
      const ar = AR[k];
      if (typeof en !== 'string' || typeof ar !== 'string') {
        hits.push(`${k}: missing`);
        continue;
      }
      for (const b of POLICY.banned_en ?? []) if (new RegExp(b.pattern, 'i').test(en)) hits.push(`${k}: ${b.label}`);
      for (const b of POLICY.banned_ar ?? []) if (new RegExp(b.pattern).test(ar)) hits.push(`${k}: ar banned`);
      for (const s of POLICY.scary_vocab_en ?? []) if (en.toLowerCase().includes(String(s).toLowerCase())) hits.push(`${k}: ${s}`);
      for (const s of POLICY.scary_vocab_ar ?? []) if (ar.includes(s)) hits.push(`${k}: ar scary`);
      if (/[0-9]/.test(en.replace(/\{\{\w+\}\}/g, ''))) hits.push(`${k}: digit`);
    }
    expect(hits).toEqual([]);
  });
});

describe('S81-11 F3 / A5 -- no electronics / other-category / fabricated copy remains', () => {
  it('no catalog value names iPhone / Galaxy / sunscreen / multivitamin / Compare anything', () => {
    const re = /iPhone|Galaxy|sunscreen|multivitamin|Compare anything/i;
    expect(Object.keys(EN).filter((k) => re.test(EN[k]))).toEqual([]);
    expect(Object.keys(AR).filter((k) => /iPhone|Galaxy/i.test(AR[k]))).toEqual([]);
  });

  it('no catalog value or src string literal says "shopped smarter" or "30 seconds"', () => {
    const re = /shopped smarter|30 seconds/i;
    expect(Object.keys(EN).filter((k) => re.test(EN[k]))).toEqual([]);
    const hits: string[] = [];
    const walk = (dir: string) => {
      for (const name of fs.readdirSync(dir)) {
        const full = path.join(dir, name);
        if (fs.statSync(full).isDirectory()) {
          if (name !== 'i18n') walk(full);
        } else if (/\.(ts|tsx|js)$/.test(name)) {
          const code = fs
            .readFileSync(full, 'utf8')
            .replace(/\/\*[\s\S]*?\*\//g, '')
            .replace(/(^|[^:'"`\\])\/\/[^\n]*/g, '$1');
          const literals = code.match(/'(?:[^'\\\n]|\\.)*'|"(?:[^"\\\n]|\\.)*"|`(?:[^`\\]|\\.)*`/g) ?? [];
          if (literals.some((l) => re.test(l))) hits.push(path.relative(ROOT, full));
        }
      }
    };
    walk(path.join(ROOT, 'src'));
    expect(hits).toEqual([]);
  });
});

describe('S81-11 A6 -- HomeEditorialSections renders no savings banner', () => {
  it('even when getHomeSavings resolves a met threshold', async () => {
    mockGetHomeSavings.mockResolvedValue({ savings_bhd: 40, decisions_count: 5, threshold_met: true });
    const HomeEditorialSections = require('../../src/components/HomeEditorialSections').default;
    const r = render(<HomeEditorialSections onPickCategory={jest.fn()} onPressVerdict={jest.fn()} />);
    await waitFor(() => expect(r.queryByTestId('home-quick-categories')).not.toBeNull());
    for (let i = 0; i < 5; i++) {
      // eslint-disable-next-line no-await-in-loop
      await act(async () => {
        await new Promise((res) => setImmediate(res));
      });
    }
    expect(r.queryByTestId('home-savings-banner')).toBeNull();
    expect(r.queryByText(/shopped smarter/i)).toBeNull();
  });
});
