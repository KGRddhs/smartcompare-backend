/**
 * S69 U-R — brand rename Qaren -> MYEZ (ميّز): catalog fence (T1).
 *
 * Spec: docs/investigations/2026-09-29-session-69-state/UR_RENAME_MYEZ_SPEC.md §3 T1,
 * as corrected by its spec review (C1-C4, C10 and the per-key table).
 *
 * Why the fence is per-key and not a blind "no قارن anywhere":
 *   - «قارن» is BOTH the old brand AND the imperative verb "compare!". Of the
 *     108 substring hits in ar.json at base e3f87b8b, 24 are the brand, 10 are
 *     the verb (EN "Compare…"), and 74 are other words that merely contain the
 *     root (مقارنة, المقارنات, نقارن, يقارن …). A substring replace would turn
 *     «مقارنة» into «مميّزة» and «المقارنات» into «المميّزات» ("the features").
 *   - JavaScript's \b does not treat Arabic letters as word characters, so the
 *     Arabic word boundary is written out with explicit lookarounds.
 *   - The key NAME `referrals.landing.openQaren` is a code identifier used by
 *     ReferralLandingScreen and two suites; only its VALUE changes.
 *
 * Brand forms (ruling R-A): Latin "MYEZ" (capitals); Arabic «ميّز» with the
 * shadda = U+0645 U+064A U+0651 U+0632.
 */
import en from '../../src/i18n/en.json';
import ar from '../../src/i18n/ar.json';
import policy from '../../src/i18n/.copy-policy.json';

type Flat = Record<string, string>;

function flatten(obj: unknown, prefix = '', out: Flat = {}): Flat {
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v !== null && typeof v === 'object') flatten(v, key, out);
    else out[key] = String(v);
  }
  return out;
}

const EN = flatten(en);
const AR = flatten(ar);

const MYEZ_AR = 'ميّز'; // ميّز
const OLD_AR = 'قارن'; // قارن
const AR_LETTER = '[\\u0600-\\u06FF]';
// Standalone word, optionally carrying one attached proclitic (ب / ل / و):
// «بقارن» in referrals.landing.network is the brand after ب.
const wordRe = (w: string, flags = 'u') =>
  new RegExp(`(?<!${AR_LETTER})[\\u0628\\u0644\\u0648]?${w}(?!${AR_LETTER})`, flags);
const OLD_AR_WORD = wordRe(OLD_AR);
const MYEZ_AR_WORD = wordRe(MYEZ_AR);

// Addresses / schemes stay on qaren (ruling R-B / D14). At base no catalog
// value carries one; stripping keeps the fence honest if one is ever added.
const ADDRESS_RE =
  /qaren:\/\/\S*|[\w.+-]*@qaren\.app|(?:https?:\/\/)?(?:[\w-]+\.)*qaren\.app(?:\/[\w/.%-]*)?/gi;
const stripAddresses = (s: string) => s.replace(ADDRESS_RE, ' ');

const countMatches = (s: string, re: RegExp) =>
  (s.match(new RegExp(re.source, re.flags.includes('g') ? re.flags : `${re.flags}g`)) ?? []).length;

/** The 24 Arabic brand keys + the one Latin-in-AR key (review table). */
const BRAND_KEYS = [
  'app.name',
  'home.savings.count_zero',
  'home.savings.count_one',
  'home.savings.count_two',
  'home.savings.count_few',
  'home.savings.count_many',
  'home.savings.count_other',
  'loading.tip.cross_checks',
  'profile.styleProfile.basedOn',
  'profile.aiSharing.subtitle',
  'referrals.share.maxReached',
  'referrals.landing.unavailable',
  'referrals.landing.network',
  'referrals.landing.openQaren',
  'referrals.quiz.signupCtaSoft',
  'referrals.status.subtitle',
  'referrals.status.gifted',
  'onboarding.s5.privacy_anon_body',
  'home.permission.body',
  'home.compare.unavailable_body',
  'results.tips.retailers',
  'referrals.share.messageWithLink',
  'update.required.title',
  'update.required.body',
  'update.required.manual',
].sort();

/** «قارن» as the verb "compare!" — EN has no brand here; these stay. */
const VERB_KEYS = [
  'app.tagline',
  'splash.tagline',
  'home.hero',
  'home.compare.cta',
  'home.camera.compareCta',
  'home.capture.compareCta',
  'home.limit.max_body',
  'history.recompare',
  'onboarding.s1.title',
  'onboarding.s15.cta',
].sort();

describe('S69 U-R T1 — catalog brand fence (MYEZ / ميّز)', () => {
  it('app.name is exactly "MYEZ" (en) and «ميّز» (ar), pinned by codepoint', () => {
    expect(EN['app.name']).toBe('MYEZ');
    expect(Array.from(AR['app.name'] ?? '').map((c) => c.codePointAt(0)!.toString(16))).toEqual([
      '645',
      '64a',
      '651',
      '632',
    ]);
  });

  it('no en or ar value contains Latin "Qaren" outside an address/scheme', () => {
    const offenders = [
      ...Object.entries(EN)
        .filter(([, v]) => /Qaren/.test(stripAddresses(v)))
        .map(([k]) => `en:${k}`),
      ...Object.entries(AR)
        .filter(([, v]) => /Qaren/.test(stripAddresses(v)))
        .map(([k]) => `ar:${k}`),
    ];
    expect(offenders).toEqual([]);
  });

  it('standalone Arabic «قارن» survives ONLY on the 10 verb keys (the brand uses are gone)', () => {
    // The 10 verb keys still read as the verb: no MYEZ / ميّز leaked into "Compare…".
    for (const k of VERB_KEYS) {
      expect({ k, en: /MYEZ/.test(EN[k]), ar: AR[k].includes(MYEZ_AR) }).toEqual({
        k,
        en: false,
        ar: false,
      });
    }
    const hits = Object.entries(AR)
      .filter(([, v]) => OLD_AR_WORD.test(stripAddresses(v)))
      .map(([k]) => k)
      .sort();
    expect(hits).toEqual(VERB_KEYS);
  });

  it('the en values carrying MYEZ are exactly the 25 brand keys', () => {
    const keys = Object.keys(EN)
      .filter((k) => /\bMYEZ\b/.test(EN[k]))
      .sort();
    expect(keys).toEqual(BRAND_KEYS);
  });

  it('the ar values carrying standalone «ميّز» are exactly the same 25 brand keys (parity both ways)', () => {
    const keys = Object.keys(AR)
      .filter((k) => MYEZ_AR_WORD.test(AR[k]))
      .sort();
    expect(keys).toEqual(BRAND_KEYS);
  });

  it('the proclitic form is written «بميّز» in referrals.landing.network', () => {
    expect(AR['referrals.landing.network']).toContain(`ب${MYEZ_AR}`);
    expect(AR['referrals.landing.network']).not.toContain(OLD_AR);
  });

  it('no blind replace: the other words containing قارن (مقارنة, المقارنات, يقارن …) are intact and ميّز never sits inside a former مقارنة', () => {
    // Structural, not an absolute count: catalog edits by other units (U2 removed
    // paywall keys carrying المقارنات) must not redden this fence.
    const all = Object.values(AR).join('\n');
    const standalone = countMatches(all, OLD_AR_WORD);
    const total = countMatches(all, new RegExp(OLD_AR, 'u'));
    expect(standalone).toBe(VERB_KEYS.length);
    expect(total - standalone).toBeGreaterThanOrEqual(40); // the embedded forms survive
    for (const word of ['مقارنة', 'المقارنات', 'يقارن']) {
      expect({ word, present: all.includes(word) }).toEqual({ word, present: true });
    }
    // ميّز embedded in a longer word may appear ONLY in the pre-existing premium
    // label «مميّز» (onboarding.s9.premium) — never inside a former مقارنة.
    const embeddedMyez = Object.entries(AR)
      .filter(([, v]) => v.includes(MYEZ_AR) && !MYEZ_AR_WORD.test(v))
      .map(([k]) => k)
      .sort();
    expect(embeddedMyez).toEqual(['onboarding.s9.premium']);
    expect(AR['onboarding.s9.premium']).toBe(`م${MYEZ_AR}`);
    expect(countMatches(all, MYEZ_AR_WORD)).toBe(BRAND_KEYS.length);
  });

  it('the key name referrals.landing.openQaren is kept in both catalogs (value only changes)', () => {
    // Full key parity (W3-11 invariant): the rename adds or removes no key.
    expect(Object.keys(AR).sort()).toEqual(Object.keys(EN).sort());
    expect(Object.prototype.hasOwnProperty.call(EN, 'referrals.landing.openQaren')).toBe(true);
    expect(Object.prototype.hasOwnProperty.call(AR, 'referrals.landing.openQaren')).toBe(true);
    expect(EN['referrals.landing.openQaren']).toBe('Open MYEZ');
  });

  it('every renamed value carries the brand and none of the copy-policy banned vocabulary', () => {
    const doc = policy as {
      banned_en?: { pattern: string; label: string }[];
      banned_ar?: { pattern: string; label: string }[];
      scary_vocab_en?: string[];
      scary_vocab_ar?: string[];
    };
    const bad: string[] = [];
    for (const k of BRAND_KEYS) {
      for (const b of doc.banned_en ?? []) if (new RegExp(b.pattern, 'i').test(EN[k])) bad.push(`en:${k}:${b.label}`);
      for (const b of doc.banned_ar ?? []) if (new RegExp(b.pattern).test(AR[k])) bad.push(`ar:${k}:${b.label}`);
      for (const w of doc.scary_vocab_en ?? [])
        if (EN[k].toLowerCase().includes(w.toLowerCase())) bad.push(`en:${k}:${w}`);
      for (const w of doc.scary_vocab_ar ?? []) if (AR[k].includes(w)) bad.push(`ar:${k}:${w}`);
    }
    expect(bad).toEqual([]);
    const unbranded = BRAND_KEYS.filter((k) => !/\bMYEZ\b/.test(EN[k]) || !MYEZ_AR_WORD.test(AR[k]));
    expect(unbranded).toEqual([]);
  });
});
