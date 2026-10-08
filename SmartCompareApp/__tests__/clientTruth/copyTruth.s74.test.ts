/**
 * S74 CLIENT-TRUTH - reviewer-path copy truth (decisions COPY=A, N388=B) and
 * the #239-class plural fix.
 *
 * Spec CLIENT_TRUTH_SPEC.md section 2 (C7, C8, C9, C10) + section 8 rows
 * CT-C1..CT-C4, amended by FABLE_RULINGS_CLIENT_TRUTH.md CT3 (the push
 * pre-prompt drops the bonus-expiry promise), CT4 (signupCtaSoft carries no
 * comparison count), CT14 (reviews.count and specs.citations get the same
 * {count} plural fix) and CT17 (the no-digit class covers the Arabic-Indic
 * ranges).
 *
 * At main dfbda511: the avatar hint says "Photo upload coming soon" (no upload
 * feature exists), the pending price says "Pricing lands in an upcoming
 * update." (no app update brings it), onboarding s12 says "388 GCC
 * shoppers ...", the confidence sheet says "Checked across 1 retail sources.",
 * the pre-prompt promises a bonus-expiry push no sender implements, and the
 * invitee CTA says "5 comparisons" (free tier: 3 a day / 10 a month).
 *
 * Each node collects the EN and the AR problems together so a red run shows
 * both languages. The plural nodes use the REAL i18next (createInstance, real
 * catalogs; the pattern of __tests__/i18n/referralExpiryPlurals.w414.test.ts)
 * against the real toConfidenceLines adapter. Pure ASCII: Arabic is written
 * as \u escapes.
 */
import * as fs from 'fs';
import * as path from 'path';
import { createInstance } from 'i18next';
import en from '../../src/i18n/en.json';
import ar from '../../src/i18n/ar.json';
import { toConfidenceLines } from '../../src/components/results/confidenceDetailsLines';

const EN = en as unknown as Record<string, string>;
const AR = ar as unknown as Record<string, string>;

/** ASCII digits plus the Arabic-Indic and extended Arabic-Indic ranges (ruling CT17). */
const ANY_DIGIT = /[0-9\u0660-\u0669\u06f0-\u06f9]/;

const SIX = ['_zero', '_one', '_two', '_few', '_many', '_other'];

/** A catalog form with its {{count}} filled (undefined stays undefined). */
function fillCount(value: string | undefined, n: number): string | undefined {
  return typeof value === 'string' ? value.replace(/\{\{count\}\}/g, String(n)) : value;
}

function realT(lng: 'en' | 'ar') {
  const inst = createInstance();
  inst.init({
    lng,
    fallbackLng: 'en',
    resources: { en: { translation: en }, ar: { translation: ar } },
    interpolation: { escapeValue: false },
    initAsync: false,
    initImmediate: false,
  } as any);
  return inst.t.bind(inst) as unknown as (key: string, params?: Record<string, unknown>) => string;
}

/** The six-form house convention: every form present, the bare base key gone. */
function familyProblems(base: string): string[] {
  const problems: string[] = [];
  for (const [lang, cat] of [
    ['EN', EN],
    ['AR', AR],
  ] as const) {
    const missing = SIX.filter((s) => typeof cat[`${base}${s}`] !== 'string');
    if (missing.length) problems.push(`${lang} lacks ${missing.join(',')}`);
    if (cat[base] !== undefined) problems.push(`${lang} still has the base key`);
  }
  return problems;
}

describe('S74 CLIENT-TRUTH reviewer-path copy (COPY=A, N388=B)', () => {
  it('CT-C1: editProfile.avatar.placeholder no longer promises a photo upload "soon" (EN and AR)', () => {
    const enValue = EN['editProfile.avatar.placeholder'];
    const arValue = AR['editProfile.avatar.placeholder'];
    const problems: string[] = [];
    if (typeof enValue !== 'string' || /coming soon/i.test(enValue)) problems.push(`EN: ${enValue}`);
    // Old ar:916 "\u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0635\u0648\u0631\u0629 \u0642\u0631\u064a\u0628\u0627\u064b" (photo upload soon).
    if (arValue === '\u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0635\u0648\u0631\u0629 \u0642\u0631\u064a\u0628\u0627\u064b') {
      problems.push('AR: unchanged old ar:916');
    }
    // "soon" (\u0642\u0631\u064a\u0628\u0627).
    if (typeof arValue !== 'string' || /\u0642\u0631\u064a\u0628\u0627/.test(arValue)) problems.push('AR: says "soon"');
    expect(problems).toEqual([]);
  });

  it('CT-C2: results.price.pending no longer promises an app update (EN and AR)', () => {
    const enValue = EN['results.price.pending'];
    const arValue = AR['results.price.pending'];
    const problems: string[] = [];
    if (typeof enValue !== 'string' || /upcoming update|lands/i.test(enValue)) problems.push(`EN: ${enValue}`);
    // Old ar:152 "\u0627\u0644\u0633\u0639\u0631 \u064a\u0635\u0644 \u0641\u064a \u062a\u062d\u062f\u064a\u062b \u0642\u0627\u062f\u0645." (the price arrives in a coming update).
    if (arValue === '\u0627\u0644\u0633\u0639\u0631 \u064a\u0635\u0644 \u0641\u064a \u062a\u062d\u062f\u064a\u062b \u0642\u0627\u062f\u0645.') {
      problems.push('AR: unchanged old ar:152');
    }
    // "update" (\u062a\u062d\u062f\u064a\u062b).
    if (typeof arValue !== 'string' || /\u062a\u062d\u062f\u064a\u062b/.test(arValue)) problems.push('AR: says "update"');
    expect(problems).toEqual([]);
  });

  it('CT-C3 + Y10: onboarding.s12.title carries no number (N388=B; ASCII and Arabic-Indic digits) and no spelled-out count or "train" (EN)', () => {
    const enValue = EN['onboarding.s12.title'];
    const arValue = AR['onboarding.s12.title'];
    expect({
      enIsString: typeof enValue === 'string',
      arIsString: typeof arValue === 'string',
      enHasDigit: ANY_DIGIT.test(String(enValue)),
      arHasDigit: ANY_DIGIT.test(String(arValue)),
      enCountOrTrain: /hundreds|thousands|train/i.test(String(enValue)),
    }).toEqual({
      enIsString: true,
      arIsString: true,
      enHasDigit: false,
      arHasDigit: false,
      enCountOrTrain: false,
    });
  });

  it('CT3: notifications.prePrompt.body no longer promises a bonus-expiry push (EN and AR)', () => {
    const enValue = EN['notifications.prePrompt.body'];
    const arValue = AR['notifications.prePrompt.body'];
    expect({
      enIsString: typeof enValue === 'string',
      arIsString: typeof arValue === 'string',
      enMentionsExpiry: /expir/i.test(String(enValue)),
      // The AR root of "expire / ending" (\u0646\u062a\u0647: \u0627\u0646\u062a\u0647\u0627\u0621, \u062a\u0646\u062a\u0647\u064a, \u0645\u0646\u062a\u0647\u064a)
      // and "validity" (\u0635\u0644\u0627\u062d\u064a).
      arMentionsExpiry: /\u0646\u062a\u0647|\u0635\u0644\u0627\u062d\u064a/.test(String(arValue)),
    }).toEqual({ enIsString: true, arIsString: true, enMentionsExpiry: false, arMentionsExpiry: false });
  });

  it('CT4: referrals.quiz.signupCtaSoft carries no comparison count (EN and AR, ASCII and Arabic-Indic digits)', () => {
    const enValue = EN['referrals.quiz.signupCtaSoft'];
    const arValue = AR['referrals.quiz.signupCtaSoft'];
    expect({
      enIsString: typeof enValue === 'string',
      arIsString: typeof arValue === 'string',
      enHasDigit: ANY_DIGIT.test(String(enValue)),
      arHasDigit: ANY_DIGIT.test(String(arValue)),
    }).toEqual({ enIsString: true, arIsString: true, enHasDigit: false, arHasDigit: false });
  });

  it('CT4: the InviteeQuizScreen signupCtaSoft defaultValues carry no number', () => {
    const src = fs.readFileSync(
      path.resolve(__dirname, '../../src/screens/InviteeQuizScreen.tsx'),
      'utf8',
    );
    const defaults: string[] = [];
    const re = /t\(\s*'referrals\.quiz\.signupCtaSoft'\s*,\s*\{[^}]*?defaultValue:\s*(['"])((?:(?!\1).)*)\1/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(src)) !== null) defaults.push(m[2]);
    // Dropping the defaultValues altogether is also allowed (the catalog wins).
    expect(defaults.filter((d) => ANY_DIGIT.test(d))).toEqual([]);
  });
});

describe('S74 CLIENT-TRUTH confidence-sheet plurals (#239 class; real i18next)', () => {
  it('CT-C4: price.sources is a six-form {count} plural family in both catalogs; 1 -> "1 retail source", 2 -> "2 retail sources"', () => {
    const tEn = realT('en');
    const tAr = realT('ar');
    const base = 'results.confidence.sheet.price.sources';
    expect({
      enCount1: toConfidenceLines('price', { price: { sources_count: 1 } } as any, tEn)[0],
      enCount2: toConfidenceLines('price', { price: { sources_count: 2 } } as any, tEn)[0],
      family: familyProblems(base),
    }).toEqual({
      enCount1: 'Checked across 1 retail source.',
      enCount2: 'Checked across 2 retail sources.',
      family: [],
    });
    expect(toConfidenceLines('price', { price: { sources_count: 1 } } as any, tAr)[0]).toBe(
      fillCount(AR[`${base}_one`], 1),
    );
  });

  it('CT14: reviews.count is a six-form {count} plural family; 1 review reads singular, 2 reviews plural', () => {
    const tEn = realT('en');
    const tAr = realT('ar');
    const base = 'results.confidence.sheet.reviews.count';
    const one = toConfidenceLines('reviews', { reviews: { review_count: 1 } } as any, tEn)[0];
    const two = toConfidenceLines('reviews', { reviews: { review_count: 2 } } as any, tEn)[0];
    const problems = familyProblems(base);
    if (/\breviews\b/i.test(one) || one.includes('{{')) problems.push(`EN count 1 reads "${one}"`);
    if (!/\b2 reviews\b/.test(two)) problems.push(`EN count 2 reads "${two}"`);
    expect(problems).toEqual([]);
    expect(toConfidenceLines('reviews', { reviews: { review_count: 1 } } as any, tAr)[0]).toBe(
      fillCount(AR[`${base}_one`], 1),
    );
  });

  it('CT14: specs.citations is a six-form {count} plural family; 1 citation reads singular, 2 citations plural', () => {
    const tEn = realT('en');
    const tAr = realT('ar');
    const base = 'results.confidence.sheet.specs.citations';
    const one = toConfidenceLines('specs', { specs: { citation_count: 1 } } as any, tEn)[0];
    const two = toConfidenceLines('specs', { specs: { citation_count: 2 } } as any, tEn)[0];
    const problems = familyProblems(base);
    if (/\bcitations\b/i.test(one) || one.includes('{{')) problems.push(`EN count 1 reads "${one}"`);
    if (!/\b2\b/.test(two) || !/\bcitations\b/i.test(two)) problems.push(`EN count 2 reads "${two}"`);
    expect(problems).toEqual([]);
    expect(toConfidenceLines('specs', { specs: { citation_count: 1 } } as any, tAr)[0]).toBe(
      fillCount(AR[`${base}_one`], 1),
    );
  });
});
