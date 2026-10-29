/**
 * S81-08 CLIENT-FIRST-OTA RED - rows H1..H3: the three new copy keys in both
 * catalogs (spec 2.7 / 3.11 as amended by RULINGS_S81_08 R-S08-2: "the a11y
 * copy never says the bonus refreshes"). Every AR value is [NATIVE READ] for
 * the owner; this file pins structure and the fences only.
 *
 * Pure ASCII: the AR fence patterns are written as code-point escapes (copied
 * from __tests__/screens/paywall.noSubscriptionUi.s69.test.ts T2-e2).
 */

import en from '../../src/i18n/en.json';
import ar from '../../src/i18n/ar.json';
import copyPolicy from '../../src/i18n/.copy-policy.json';

const EN = en as Record<string, string>;
const AR = ar as Record<string, string>;
const POLICY = copyPolicy as any;

const KEYS = ['home.headerCounter.resets', 'home.headerCounter.a11yResets', 'paywall.limit.resets_at'];

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
const AR_DISHONEST = [
  /\u062f\.\u0628/,
  /\u062a\u062c\u0631\u0628/,
  /\u0645\u0645\u064a\u0632/,
  /\u0627\u0634\u062a\u0631\u0627\u0643/,
  /\u063a\u064a\u0631 \u0645\u062d\u062f\u0648\u062f/,
  /\u0631\u0645\u0632 \u0635\u062f\u064a\u0642/,
  /\u062f\u0639\u0648\u0629/,
  /\u0642\u0631\u064a\u0628\u0627/,
  /\u063a\u062f\u0627/,
];
const DIACRITICS = /[\u064b-\u0652]/;
const ARABIC_INDIC = /[\u0660-\u0669\u066a]/;

/** The sentence (EN) or clause (AR) that carries {{time}}. */
function timeClause(v: string): string {
  const parts = v.split(/[.\u060c\u061b]/);
  return parts.find((p) => p.includes('{{time}}')) ?? '';
}

describe('S81-08 H - reset-time copy keys', () => {
  it('H1 the three keys exist in EN and AR with their placeholders', () => {
    const report: string[] = [];
    for (const k of KEYS) {
      for (const [lang, cat] of [
        ['en', EN],
        ['ar', AR],
      ] as const) {
        const v = cat[k];
        if (typeof v !== 'string' || v.trim() === '') {
          report.push(`${lang} ${k}: absent`);
          continue;
        }
        if (!v.includes('{{time}}')) report.push(`${lang} ${k}: no {{time}}`);
        if (k === 'home.headerCounter.a11yResets') {
          for (const ph of ['{{free}}', '{{total}}', '{{bonus}}']) {
            if (!v.includes(ph)) report.push(`${lang} ${k}: no ${ph}`);
          }
        }
      }
    }
    expect(report).toEqual([]);
  });

  it('H2 honest copy: fences, no digits, no today / tomorrow, and the time never attaches to the bonus', () => {
    const hits: string[] = [];
    const bannedEn: RegExp[] = (POLICY.banned_en || []).map((b: any) => new RegExp(b.pattern));
    const bannedAr: RegExp[] = (POLICY.banned_ar || []).map((b: any) => new RegExp(b.pattern));
    for (const k of KEYS) {
      const e = EN[k];
      const a = AR[k];
      if (typeof e !== 'string' || e.trim() === '') hits.push(`en ${k}: absent`);
      if (typeof a !== 'string' || a.trim() === '') hits.push(`ar ${k}: absent`);
      if (typeof e === 'string') {
        const bare = e.replace(/\{\{[a-z]+\}\}/g, '');
        for (const re of [...EN_DISHONEST, ...bannedEn, /today/i]) if (re.test(e)) hits.push(`en ${k}: ${re}`);
        for (const w of POLICY.scary_vocab_en || []) {
          if (e.toLowerCase().includes(String(w).toLowerCase())) hits.push(`en ${k}: scary ${w}`);
        }
        if (/[0-9]/.test(bare)) hits.push(`en ${k}: digit`);
      }
      if (typeof a === 'string') {
        const bare = a.replace(/\{\{[a-z]+\}\}/g, '');
        for (const re of [...AR_DISHONEST, ...bannedAr]) if (re.test(a)) hits.push(`ar ${k}: ${re}`);
        for (const w of POLICY.scary_vocab_ar || []) if (new RegExp(w).test(a)) hits.push(`ar ${k}: scary`);
        if (DIACRITICS.test(a)) hits.push(`ar ${k}: diacritics`);
        if (ARABIC_INDIC.test(a) || /[0-9]/.test(bare)) hits.push(`ar ${k}: digit`);
      }
    }
    // R-S08-2: the clause that carries the time never carries the bonus, and the
    // EN time sentence names what refreshes (no bare "They" / "It" / "These").
    for (const [lang, cat] of [
      ['en', EN],
      ['ar', AR],
    ] as const) {
      const v = cat['home.headerCounter.a11yResets'];
      if (typeof v !== 'string') continue;
      const clause = timeClause(v);
      if (clause.includes('{{bonus}}')) hits.push(`${lang} a11yResets: the time clause carries the bonus`);
      if (lang === 'en' && /^\s*(they|it|these|both)\b/i.test(clause)) {
        hits.push('en a11yResets: the time sentence starts with a pronoun that covers the bonus');
      }
    }
    expect(hits).toEqual([]);
  });

  it('H3 (PIN) the EN and AR key sets stay equal', () => {
    expect(Object.keys(EN).sort()).toEqual(Object.keys(AR).sort());
  });
});
