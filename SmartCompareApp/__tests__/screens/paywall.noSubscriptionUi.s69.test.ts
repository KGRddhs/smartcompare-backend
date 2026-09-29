/**
 * S69 U2 — T2: static fence — no subscription UI is reachable anywhere.
 *
 * Spec: docs/investigations/2026-09-29-session-69-state/U2_HONEST_LIMIT_SHEET_SPEC.md
 * (§2 R1-R6, §3 T2) as corrected by the spec review:
 *   - item 14: the source scan (a) covers ONLY the sheet file and
 *     PaywallBanner.tsx; ProfileScreen.tsx legitimately carries Alert.alert and
 *     the MonthStrip "BHD saved", so it gets only the (b) checks.
 *   - item 7 / Q7: (c) is a POSITIVE allowlist of the surviving paywall.* keys,
 *     identical in en.json and ar.json; every other paywall.* key (incl. the
 *     R6 families the spec missed: title, subtitle, title_part1/accent, trust,
 *     features.*) is gone, and profile.upgrade is gone (item 9).
 *   - item 1 / Q1: the Paywall route params gain `error?` / `code?` (the 429
 *     envelope the app really receives), and App.tsx keeps the `Paywall` route.
 *   - items 5, 12, 17 / Q3, Q8, Q9, Q10: honest copy — no "tomorrow" (the reset
 *     is 00:00 UTC), no premium/unlimited/friend-code promise on the banner, no
 *     Arabic diacritics, no Arabic-Indic digits, no noun–number agreement error
 *     after {{limit}}.
 *
 * Reads files only; no render, no network.
 */
import * as fs from 'fs';
import * as path from 'path';

import en from '../../src/i18n/en.json';
import ar from '../../src/i18n/ar.json';
import copyPolicy from '../../src/i18n/.copy-policy.json';

const ROOT = path.join(__dirname, '..', '..');
const read = (rel: string) => fs.readFileSync(path.join(ROOT, rel), 'utf8');

const EN = en as Record<string, string>;
const AR = ar as Record<string, string>;

const SHEET = 'src/screens/PaywallScreen.tsx';
const BANNER = 'src/components/PaywallBanner.tsx';
const PROFILE = 'src/screens/ProfileScreen.tsx';

/** The ONLY paywall.* keys that may survive (spec-review Q7). */
const PAYWALL_ALLOW = [
  'paywall.dailyLimit',
  'paywall.monthlyLimit',
  'paywall.usageMessage',
  'paywall.limit.title',
  'paywall.limit.today',
  'paywall.limit.remaining',
  'paywall.limit.resets_daily',
  'paywall.limit.resets_monthly',
  'paywall.limit.resets_unknown',
].sort();

/** R6 + spec-review item 11: families that must be gone from BOTH catalogs. */
const DELETED_PREFIXES = [
  'paywall.title',
  'paywall.subtitle',
  'paywall.title_part1',
  'paywall.title_accent',
  'paywall.trust',
  'paywall.cta',
  'paywall.features.',
  'paywall.plan.',
  'paywall.socialProof.',
  'paywall.timeline.',
  'paywall.coming_soon_',
  'paywall.subscribe',
  'paywall.payment',
  'paywall.restore',
  'paywall.social',
  'paywall.premium.',
  'paywall.free.',
];

const BANNER_KEYS = [
  'home.compare.paywall_banner_title',
  'home.compare.paywall_banner_body',
  'home.compare.paywall_banner_cta',
];

const paywallKeys = (cat: Record<string, string>) =>
  Object.keys(cat)
    .filter((k) => k.startsWith('paywall.'))
    .sort();

describe('T2 — no subscription UI in the sheet / banner sources (R1, item 14)', () => {
  it('T2-a the sheet and the banner sources carry no Alert, price, trial, restore or social proof', () => {
    const FORBIDDEN: RegExp[] = [
      /Alert\.alert/,
      /BHD/,
      /trial/i,
      /Restore/i,
      /socialProof/,
      /Trusted by/i,
      /coming[_ ]soon/i,
      /5,000/,
    ];
    const hits: string[] = [];
    for (const rel of [SHEET, BANNER]) {
      const src = read(rel);
      for (const re of FORBIDDEN) if (re.test(src)) hits.push(`${rel}: ${re}`);
    }
    expect(hits).toEqual([]);
  });

  it('T2-a2 the sheet never navigates to an unregistered "Home" route and is ~200 lines, not 786', () => {
    const src = read(SHEET);
    expect(src).not.toMatch(/navigate\(\s*['"]Home['"]/);
    expect(src).not.toMatch(/common\.cancel/);
    const lines = src.split(/\r?\n/).length;
    expect(lines).toBeLessThanOrEqual(250);
  });
});

describe('T2 — Profile (R4, item 9)', () => {
  it('T2-b ProfileScreen has no Paywall navigation, no profile.upgrade key and no upgrade row', () => {
    const src = read(PROFILE);
    // Any 'Paywall' string literal: catches navigate('Paywall'), the object
    // form navigate({ name: 'Paywall' }) and a route-name constant alike.
    expect(src).not.toMatch(/['"`]Paywall['"`]/);
    expect(src).not.toMatch(/profile\.upgrade/);
    expect(src).not.toMatch(/profile-row-upgrade/);
  });
});

describe('T2 — catalogs (R6, items 10, 11; Q7)', () => {
  it('T2-c1 en.json paywall.* keys are EXACTLY the allowlist', () => {
    expect(paywallKeys(EN)).toEqual(PAYWALL_ALLOW);
  });

  it('T2-c2 ar.json paywall.* keys are EXACTLY the allowlist', () => {
    expect(paywallKeys(AR)).toEqual(PAYWALL_ALLOW);
  });

  it('T2-c3 no deleted family survives in either catalog, and profile.upgrade is gone from both', () => {
    const survivors: string[] = [];
    for (const [name, cat] of [['en', EN], ['ar', AR]] as const) {
      for (const k of Object.keys(cat)) {
        if (DELETED_PREFIXES.some((p) => (p.endsWith('.') || p.endsWith('_') ? k.startsWith(p) : k === p))) {
          survivors.push(`${name}:${k}`);
        }
      }
      if ('profile.upgrade' in cat) survivors.push(`${name}:profile.upgrade`);
    }
    expect(survivors).toEqual([]);
  });

  it('T2-c4 interpolation contract: counts keys carry their placeholders in BOTH languages, no plural suffix', () => {
    const need: Record<string, string[]> = {
      'paywall.usageMessage': ['{{used}}', '{{limit}}'],
      'paywall.limit.today': ['{{used}}', '{{limit}}'],
      'paywall.limit.remaining': ['{{remaining}}'],
    };
    const missing: string[] = [];
    for (const [key, ph] of Object.entries(need)) {
      for (const [name, cat] of [['en', EN], ['ar', AR]] as const) {
        const v = cat[key];
        if (typeof v !== 'string') {
          missing.push(`${name}:${key} absent`);
          continue;
        }
        for (const p of ph) if (!v.includes(p)) missing.push(`${name}:${key} lacks ${p}`);
      }
    }
    expect(missing).toEqual([]);
    expect(PAYWALL_ALLOW.filter((k) => /_(zero|one|two|few|many|other)$/.test(k))).toEqual([]);
  });
});

describe('T2 — honest copy (items 5, 12, 17; Q3, Q8, Q9, Q10)', () => {
  const EN_DISHONEST = [
    /BHD/,
    /trial/i,
    /premium/i,
    /subscri/i,
    /upgrade/i,
    /unlimited/i,
    /coming soon/i,
    /friend code/i,
    /invite/i,
    /referral/i,
    /tomorrow/i,
    /\bfailed\b/i,
  ];
  const AR_DISHONEST = [/د\.ب/, /تجرب/, /مميز/, /اشتراك/, /غير محدود/, /رمز صديق/, /دعوة/, /قريبا/, /غدا/];
  const DIACRITICS = /[ً-ْ]/;
  const ARABIC_INDIC = /[٠-٩٪]/;

  it('T2-e1 EN values of the surviving paywall keys and the banner: present, no promise, no scary word, no "tomorrow"', () => {
    const hits: string[] = [];
    for (const key of [...PAYWALL_ALLOW, ...BANNER_KEYS]) {
      const v = EN[key];
      if (typeof v !== 'string' || v.trim() === '') {
        hits.push(`${key}: absent`);
        continue;
      }
      for (const re of EN_DISHONEST) if (re.test(v)) hits.push(`${key}: ${re} in "${v}"`);
      for (const w of copyPolicy.scary_vocab_en) {
        if (v.toLowerCase().includes(w.toLowerCase())) hits.push(`${key}: scary "${w}"`);
      }
    }
    expect(hits).toEqual([]);
  });

  it('T2-e2 AR values of the surviving paywall keys and the banner: present, MSA, no diacritics, ASCII digits, no banned term', () => {
    const hits: string[] = [];
    const arTerms = [...copyPolicy.banned_ar.map((b) => b.pattern), ...copyPolicy.scary_vocab_ar];
    for (const key of [...PAYWALL_ALLOW, ...BANNER_KEYS]) {
      const v = AR[key];
      if (typeof v !== 'string' || v.trim() === '') {
        hits.push(`${key}: absent`);
        continue;
      }
      if (DIACRITICS.test(v)) hits.push(`${key}: diacritics`);
      if (ARABIC_INDIC.test(v)) hits.push(`${key}: Arabic-Indic digit or percent`);
      for (const re of AR_DISHONEST) if (re.test(v)) hits.push(`${key}: ${re}`);
      for (const term of arTerms) if (new RegExp(term).test(v)) hits.push(`${key}: banned "${term}"`);
    }
    expect(hits).toEqual([]);
  });

  it('T2-e3 AR counts copy avoids the noun–number agreement error right after {{limit}} / {{remaining}}', () => {
    const offenders = ['paywall.usageMessage', 'paywall.limit.today', 'paywall.limit.remaining'].filter((k) => {
      const v = AR[k];
      return typeof v !== 'string' || /\{\{(limit|remaining)\}\}\s*مقارن/.test(v);
    });
    expect(offenders).toEqual([]);
  });

  it('T2-f the PaywallBanner no longer promises unlimited / premium / a friend code, and its CTA is not "See options"', () => {
    const body = EN['home.compare.paywall_banner_body'];
    const cta = EN['home.compare.paywall_banner_cta'];
    expect(body).not.toMatch(/unlimited|premium|friend code|upgrade/i);
    expect(cta).not.toBe('See options');
    expect(AR['home.compare.paywall_banner_body']).not.toMatch(/غير محدود|مميز|رمز صديق|اشتراك/);
    expect(AR['home.compare.paywall_banner_cta']).not.toBe('عرض الخيارات');
  });
});

describe('T2 — route contract (R2; items 1, 7)', () => {
  it('T2-d App.tsx keeps the Paywall route on PaywallScreen, and its params accept the real 429 envelope (error / code)', () => {
    const app = read('App.tsx');
    expect(app).toMatch(/name="Paywall"[\s\S]{0,80}component=\{PaywallScreen\}/);
    const types = read('src/types/types.ts');
    const m = types.match(/Paywall:\s*\{([\s\S]*?)\}\s*\|\s*undefined;/);
    expect(m).not.toBeNull();
    const block = (m as RegExpMatchArray)[1];
    expect(block).toMatch(/initialUsage\?:/);
    expect(block).toMatch(/\berror\?:\s*string/);
    expect(block).toMatch(/\bcode\?:\s*string/);
  });
});
