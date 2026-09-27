/**
 * W4-14 Part A2 — the `results.dimension.*` catalog family.
 *
 * Every public dimension key the backend can name (49 category dimension keys +
 * the core price/reviews/value, `value` shared = 51) gets a
 * `results.dimension.<key>` entry in BOTH catalogs. The EN value echoes the
 * backend label byte-for-byte, so every English render is unchanged; the Arabic
 * value is the spec's A2 proposal (native review before the OTA). The EN label
 * table below is a literal copy of the backend vocabulary; the backend fence
 * `tests/test_dimension_label_catalog_parity_w414.py` keeps it equal to
 * `scoring_service`. The AR table is the spec's A2 column verbatim (RED 2b).
 *
 * RED = fails at the unit base 3985eaac (the family has 0 keys in either
 * catalog). No PIN rows in this file.
 */
import en from '../../src/i18n/en.json';
import ar from '../../src/i18n/ar.json';

const EN_LABELS: Record<string, string> = {
  actives: 'Active ingredients',
  availability: 'Availability',
  build: 'Build',
  build_quality: 'Build quality',
  character: 'Character',
  cpw: 'Cost per wear',
  craft: 'Craftsmanship',
  dietary: 'Dietary fit',
  dosage: 'Dosage',
  durability: 'Durability',
  ecosystem: 'Ecosystem',
  efficacy: 'Efficacy',
  evidence: 'Evidence',
  feature: 'Features',
  feature_match: 'Feature match',
  finish: 'Finish',
  fit: 'Fit',
  form: 'Form',
  formulation: 'Formulation',
  function: 'Function',
  futureproof: 'Future-proofing',
  hair_match: 'Hair match',
  heritage: 'Heritage',
  ingredient: 'Ingredients',
  ingredient_safety: 'Ingredient safety',
  longevity: 'Longevity',
  multi_value: 'Multi-use value',
  nutrition: 'Nutrition',
  perf_value: 'Performance vs value',
  performance: 'Performance',
  presentation: 'Presentation',
  price: 'Price',
  projection: 'Projection',
  reliability: 'Reliability',
  results: 'Results',
  results_value: 'Results vs value',
  review: 'Reviews',
  reviews: 'Reviews',
  safety: 'Safety',
  scalp: 'Scalp',
  scent: 'Scent',
  sensory: 'Sensory',
  serving_value: 'Serving value',
  shade: 'Shade range',
  skin_compat: 'Skin compatibility',
  style: 'Style',
  taste: 'Taste',
  trust: 'Trust',
  value: 'Value',
  versatility: 'Versatility',
  wear_value: 'Wear value',
};

// The spec's A2 Arabic proposal, verbatim (ruling R10; native review before the OTA).
// A catalog edit must change this table in the same PR (RED 2b is its arbiter).
const AR_LABELS: Record<string, string> = {
  actives: 'المكونات الفعالة',
  availability: 'التوفر',
  build: 'التصنيع',
  build_quality: 'جودة التصنيع',
  character: 'الطابع',
  cpw: 'التكلفة لكل استخدام',
  craft: 'الحرفية',
  dietary: 'الملاءمة الغذائية',
  dosage: 'الجرعة',
  durability: 'المتانة',
  ecosystem: 'المنظومة',
  efficacy: 'الفعالية',
  evidence: 'الأدلة',
  feature: 'المزايا',
  feature_match: 'مطابقة المزايا',
  finish: 'اللمسة النهائية',
  fit: 'المقاس',
  form: 'الشكل',
  formulation: 'التركيبة',
  function: 'الوظيفة',
  futureproof: 'مواكبة المستقبل',
  hair_match: 'ملاءمة الشعر',
  heritage: 'العراقة',
  ingredient: 'المكونات',
  ingredient_safety: 'أمان المكونات',
  longevity: 'الثبات',
  multi_value: 'قيمة الاستخدامات المتعددة',
  nutrition: 'القيمة الغذائية',
  perf_value: 'الأداء مقابل السعر',
  performance: 'الأداء',
  presentation: 'التقديم',
  price: 'السعر',
  projection: 'الانتشار',
  reliability: 'الاعتمادية',
  results: 'النتائج',
  results_value: 'النتائج مقابل السعر',
  review: 'التقييمات',
  reviews: 'التقييمات',
  safety: 'الأمان',
  scalp: 'فروة الرأس',
  scent: 'الرائحة',
  sensory: 'الإحساس عند الاستخدام',
  serving_value: 'قيمة الحصة',
  shade: 'درجات اللون',
  skin_compat: 'ملاءمة البشرة',
  style: 'الطراز',
  taste: 'الطعم',
  trust: 'الموثوقية',
  value: 'القيمة',
  versatility: 'تعدد الاستخدامات',
  wear_value: 'قيمة الاستخدام',
};

const KEYS = Object.keys(EN_LABELS).sort();
const PREFIX = 'results.dimension.';
const enCat = en as Record<string, string>;
const arCat = ar as Record<string, string>;

describe('W4-14 results.dimension.* catalog family', () => {
  it('the literal table is the 51 public keys', () => {
    // Harness guard (not a RED row): the table itself must stay 51 keys.
    expect(KEYS).toHaveLength(51);
  });

  it('RED 1: every public dimension key has results.dimension.<key> in en.json and ar.json', () => {
    const missingEn = KEYS.filter((k) => !(PREFIX + k in enCat));
    const missingAr = KEYS.filter((k) => !(PREFIX + k in arCat));
    expect({ missingEn: missingEn.length, missingAr: missingAr.length }).toEqual({
      missingEn: 0,
      missingAr: 0,
    });
  });

  it('RED 2: the results.dimension family is exactly the 51 keys in both catalogs and no ar value contains an ASCII letter', () => {
    const famEn = Object.keys(enCat).filter((k) => k.startsWith(PREFIX)).sort();
    const famAr = Object.keys(arCat).filter((k) => k.startsWith(PREFIX)).sort();
    // Non-vacuous: the family size is asserted before its contents.
    expect(famEn).toHaveLength(51);
    expect(famAr).toHaveLength(51);
    expect(famEn).toEqual(KEYS.map((k) => PREFIX + k));
    expect(famAr).toEqual(KEYS.map((k) => PREFIX + k));
    const asciiLetter = famAr.filter((k) => /[A-Za-z]/.test(arCat[k]) || !arCat[k].trim());
    expect(asciiLetter).toEqual([]);
  });

  it('RED 2b: ar.json results.dimension.<key> equals the spec A2 Arabic table verbatim (51 rows)', () => {
    // Ruling R10: the 51 AR values are the spec's A2 table verbatim. RED 2 only
    // proves presence and no ASCII; this row pins every value, so a catalog edit
    // (or a swapped word) cannot pass CI without editing AR_LABELS in the same PR.
    expect(Object.keys(AR_LABELS).sort()).toEqual(KEYS);
    const diffs = KEYS.filter((k) => arCat[PREFIX + k] !== AR_LABELS[k]);
    expect(diffs).toEqual([]);
  });

  it('RED 3: en.json results.dimension.<key> equals the backend English label byte-for-byte', () => {
    const diffs = KEYS.filter((k) => enCat[PREFIX + k] !== EN_LABELS[k]);
    expect(diffs).toEqual([]);
  });
});
