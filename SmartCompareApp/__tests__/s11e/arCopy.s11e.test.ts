/**
 * S81-11e AR-COPY RED - the twelve Arabic strings of the first post-approval
 * OTA, re-read by the delegated native read (specs/S81_11E_AR_COPY_REVIEW.md,
 * 1 WRONG + 11 AWKWARD) under RULINGS_S81_11E (R-S11E-7..12).
 *
 * Spec: .qa-s80/S81-11e_UNIT_SPEC.md section 5 (filed as specs/S81_11E_UNIT_SPEC.md).
 *   R1-R12  the twelve AR values equal the EXPECTED table (spec 2.1 verbatim)
 *   R13     one concentration form (no transliteration opening with the "or" word)
 *   R14     the "last online" phrase is gone from lastSeen / lastSeenNoStore
 *   R15     the clock form: the hour word before {{time}} in resets and its siblings
 *   P1-P6   placeholders, table self-check, key sets, diacritics / digits / bidi,
 *           the copy policy (read from src/i18n/.copy-policy.json), the EN table
 *
 * Hermetic: fs.readFileSync + JSON.parse of the catalogs and the policy; no
 * render, no mock, no network. Bytes: ASCII everywhere except the twelve
 * EXPECTED values (raw UTF-8, [NATIVE READ] for the owner); every other Arabic
 * is a code-point escape. Failure messages print keys, never Arabic values.
 */
import * as fs from 'fs';
import * as path from 'path';

type Flat = Record<string, string>;

const I18N_DIR = path.join(__dirname, '..', '..', 'src', 'i18n');
const readJson = (name: string): unknown =>
  JSON.parse(fs.readFileSync(path.join(I18N_DIR, name), 'utf8'));

const AR = readJson('ar.json') as Flat;
const EN = readJson('en.json') as Flat;
const POLICY = readJson('.copy-policy.json') as {
  banned_ar?: { pattern: string; label: string }[];
  scary_vocab_ar?: string[];
};

/** Spec 2.1 verbatim: the new AR value per key. */
const EXPECTED: Flat = {
  'home.errors.categoryNotLive': 'نقارن العطور حاليا، وستتوفر فئات أخرى قريبا.',
  'home.errors.insufficientDataReason.placeholder_identity': 'نحتاج أسماء أوضح لنحدد المنتجين. أضف اسم الماركة واسم العطر.',
  'results.honest.notListed': 'غير مذكور بعد لدى المتاجر التي نتابعها',
  'results.price.lastSeen': '{{store}}، آخر رصد في {{date}}',
  'results.price.lastSeenNoStore': 'آخر رصد في {{date}}',
  'home.errors.comparison': 'لمطابقة أدق، اكتب اسم الماركة واسم العطر.',
  'home.errors.insufficientData': 'البيانات قليلة عن هذين المنتجين — جرب عطرين آخرين واكتب اسم الماركة واسم العطر.',
  'onboarding.s1.quote_3': 'نسخة EDP أم EDT من العطر نفسه؟ اعرف الفرق في الحجم والسعر.',
  'onboarding.s17.tag_echoes_body': 'عندما يقارن متسوقون في عمرك نفس المنتجين.',
  'home.compare.box_a_text': 'المنتج أ · مثال: ديور سوفاج EDP',
  'home.compare.box_b_text': 'المنتج ب · مثال: بلو دو شانيل EDP',
  'home.headerCounter.resets': 'تتجدد الساعة {{time}}',
};

/** Spec 1.3 EN column (EN is unchanged by this unit). */
const EN_TABLE: Flat = {
  'home.errors.categoryNotLive': 'We compare fragrances for now. More categories are coming soon.',
  'home.errors.insufficientDataReason.placeholder_identity': 'We need clearer names to tell which products these are. Add the brand and the fragrance name.',
  'results.honest.notListed': 'Not listed by the stores we can read yet',
  'results.price.lastSeen': '{{store}}, last seen {{date}}',
  'results.price.lastSeenNoStore': 'Last seen {{date}}',
  'home.errors.comparison': 'Sharper match coming up \u2014 add the brand and the fragrance name.',
  'home.errors.insufficientData': 'Thin data on that pair \u2014 swap in two fragrances with the brand and name.',
  'onboarding.s1.quote_3': 'EDP or EDT of the same scent? See how size and price compare.',
  'onboarding.s17.tag_echoes_body': 'When peers your age just compared the same pair.',
  'home.compare.box_a_text': 'Product A \u00b7 e.g. Dior Sauvage EDP',
  'home.compare.box_b_text': 'Product B \u00b7 e.g. Bleu de Chanel EDP',
  'home.headerCounter.resets': 'resets {{time}}',
};

const TWELVE = Object.keys(EXPECTED);

const phSet = (v: string | undefined): string[] =>
  v === undefined ? ['<missing>'] : Array.from(new Set(v.match(/\{\{[^}]+\}\}/g) ?? [])).sort();
const visible = (v: string): string => v.replace(/\{\{[^}]+\}\}/g, '');

const AR_LETTER = '[\\u0600-\\u06FF]';
const wordRe = (w: string, flags = 'u') =>
  new RegExp(`(?<!${AR_LETTER})[\\u0628\\u0644\\u0648]?${w}(?!${AR_LETTER})`, flags);
const BRAND_AR = '\u0645\u064a\u0651\u0632';
const VERB_AR = '\u0642\u0627\u0631\u0646';
const AR_DIACRITICS = /[\u064b-\u0652\u0670]/;
const AR_INDIC_DIGIT = /[\u0660-\u0669\u06f0-\u06f9\u066a]/;
const BIDI_CONTROL = /[\u200e\u200f\u202a-\u202e\u2066-\u2069]/;
const ASCII_DIGIT = /[0-9]/;

/** The transliteration opening with the two-letter "or" word (alef-hamza waw, space, dal waw). */
const OR_FORM = '\u0623\u0648 \u062f\u0648';
/** The "last online" phrase. */
const LAST_ONLINE = '\u0622\u062e\u0631 \u0638\u0647\u0648\u0631';
/** The hour word + space + {{time}}. */
const CLOCK_FORM = '\u0627\u0644\u0633\u0627\u0639\u0629 {{time}}';

describe('S81-11e AR-COPY RED rows (fail at base on the old values)', () => {
  it.each(TWELVE)('R1-R12 the AR value of %s equals the EXPECTED table', (k) => {
    expect({ k, matches: AR[k] === EXPECTED[k] }).toEqual({ k, matches: true });
  });

  it('R13 one concentration form in quote_3 and both compare boxes', () => {
    const want: Record<string, string[]> = {
      'onboarding.s1.quote_3': ['EDP', 'EDT'],
      'home.compare.box_a_text': ['EDP'],
      'home.compare.box_b_text': ['EDP'],
    };
    const got = Object.keys(want).map((k) => {
      const v = AR[k] ?? '';
      return { k, orForm: v.includes(OR_FORM), tokens: ['EDP', 'EDT'].filter((t) => v.includes(t)) };
    });
    expect(got).toEqual(Object.keys(want).map((k) => ({ k, orForm: false, tokens: want[k] })));
  });

  it('R14 the "last online" phrase is gone from lastSeen and lastSeenNoStore', () => {
    const ks = ['results.price.lastSeen', 'results.price.lastSeenNoStore'];
    expect(ks.map((k) => ({ k, lastOnline: (AR[k] ?? '').includes(LAST_ONLINE) }))).toEqual(
      ks.map((k) => ({ k, lastOnline: false }))
    );
  });

  it('R15 the clock form: the hour word before {{time}} in resets and both siblings', () => {
    const ks = ['home.headerCounter.resets', 'home.headerCounter.a11yResets', 'paywall.limit.resets_at'];
    expect(ks.map((k) => ({ k, clock: (AR[k] ?? '').includes(CLOCK_FORM) }))).toEqual(
      ks.map((k) => ({ k, clock: true }))
    );
  });
});

describe('S81-11e AR-COPY PIN rows (green at base)', () => {
  it.each(TWELVE)('P1 the AR placeholder set of %s equals EN', (k) => {
    expect({ k, ph: phSet(AR[k]) }).toEqual({ k, ph: phSet(EN[k]) });
  });

  it.each(TWELVE)('P2 the EXPECTED placeholder set of %s equals EN (table self-check)', (k) => {
    expect({ k, ph: phSet(EXPECTED[k]) }).toEqual({ k, ph: phSet(EN[k]) });
  });

  it('P3 the twelve keys exist in both catalogs and the key sets are equal (1,011 each)', () => {
    const arKeys = Object.keys(AR).sort();
    const enKeys = Object.keys(EN).sort();
    expect(TWELVE.length).toBe(12);
    expect(TWELVE.filter((k) => !(k in AR)).map((k) => `ar:${k}`)).toEqual([]);
    expect(TWELVE.filter((k) => !(k in EN)).map((k) => `en:${k}`)).toEqual([]);
    expect(arKeys.filter((k) => !(k in EN))).toEqual([]);
    expect(enKeys.filter((k) => !(k in AR))).toEqual([]);
    expect({ ar: arKeys.length, en: enKeys.length }).toEqual({ ar: 1011, en: 1011 });
  });

  it('P4 the twelve AR values: no diacritic, no Arabic-Indic digit, no bidi control, no stray ASCII digit', () => {
    const bad: string[] = [];
    for (const k of TWELVE) {
      const v = AR[k] ?? '';
      if (AR_DIACRITICS.test(v.split(BRAND_AR).join(''))) bad.push(`diacritic:${k}`);
      if (AR_INDIC_DIGIT.test(v)) bad.push(`indic_digit:${k}`);
      if (BIDI_CONTROL.test(v)) bad.push(`bidi:${k}`);
      if (ASCII_DIGIT.test(visible(v))) bad.push(`ascii_digit:${k}`);
    }
    expect(bad).toEqual([]);
  });

  it('P5 the twelve AR values pass the copy policy (non-vacuous), carry no standalone verb and no brand word', () => {
    const banned = POLICY.banned_ar ?? [];
    const scary = POLICY.scary_vocab_ar ?? [];
    expect(banned.length).toBeGreaterThanOrEqual(5);
    expect(scary.length).toBeGreaterThanOrEqual(4);
    const bannedRe = banned.map((e) => new RegExp(e.pattern, 'u'));
    const verbRe = wordRe(VERB_AR);
    const bad: string[] = [];
    for (const k of TWELVE) {
      const v = visible(AR[k] ?? '');
      bannedRe.forEach((re, i) => {
        if (re.test(v)) bad.push(`banned_ar[${i}]:${k}`);
      });
      scary.forEach((w, i) => {
        if (v.includes(w)) bad.push(`scary_vocab_ar[${i}]:${k}`);
      });
      if (verbRe.test(v)) bad.push(`verb:${k}`);
      if (v.includes(BRAND_AR) || /MYEZ/.test(v)) bad.push(`brand:${k}`);
    }
    expect(bad).toEqual([]);
  });

  it.each(TWELVE)('P6 the EN value of %s equals the EN table', (k) => {
    expect({ k, en: EN[k] }).toEqual({ k, en: EN_TABLE[k] });
  });
});
