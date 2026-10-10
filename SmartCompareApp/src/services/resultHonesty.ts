/**
 * S69 U7 R2 — is this HTTP-200 comparison DEGRADED?
 *
 * When the verdict LLM call fails after Phase-1,
 * `extraction_service.generate_comparison` returns
 * `{"winner_index": 0, "error": "verdict generation unavailable"}` and
 * `response_builder.build_comparison_response` still ships `success: true`,
 * passing that dict through as `result.comparison`. The ONLY signal is a
 * truthy `result.comparison.error` (no metadata flag is set; the template
 * winner reason is also produced on legitimate paths, so the text cannot be
 * used). Same key the backend's own url_extraction_service keys on.
 *
 * A degraded result's winner reason is the template sentence and its
 * pros/cons are empty; scores (scoring_v2, deterministic) and prices are
 * real. Zero imports so screens and their test harnesses can consume it.
 */
export function isDegradedComparison(result: any): boolean {
  const err = result?.comparison?.error;
  return typeof err === 'string' ? err.trim().length > 0 : !!err;
}

/**
 * S74 CLIENT-TRUTH (AR-5, decision MED=A, ruling CT6) — does this comparison
 * concern supplements or over-the-counter medicines? ResultsContent then
 * shows the "not medical advice" line. True when any of:
 *   (a) a category (result.category_used, result.category, a product's
 *       category_profile.category or category) normalises (lowercase, no
 *       spaces / underscores / hyphens) to supplements or a backend synonym
 *       (supplement, vitamin, vitamins — extraction_service.py);
 *   (b) a product identity ("brand name variant", the fields the overview
 *       projection carries) or the raw result.query carries a whole-word
 *       token of PHARMACY_TABLET_TOKENS outside PHARMACY_CONTEXT_ONLY_TOKENS
 *       (ruling Y3: "White Vinegar" is grocery, "Fluke" is not "flu");
 *   (c) the same text carries a dose: a number + mg / mcg / IU, a pack count
 *       may follow ("500mg 24 tablets"). Never ml or g: "Dior Sauvage EDP
 *       100ml" and "256GB" are not doses.
 * No lookbehind in the patterns (Hermes compatibility, cf. sentry.ts).
 */

/** Verbatim mirror of _PHARMACY_TABLET_TOKENS in app/services/extraction_service.py (a jest node pins the equality). */
export const PHARMACY_TABLET_TOKENS: readonly string[] = [
  'effervescent', 'chewable', 'paracetamol', 'ibuprofen', 'panadol', 'adol',
  'brufen', 'pharmacy', 'laxative', 'antacid', 'flu', 'vinegar',
  'glucose', 'dose', 'dosage',
];

/** Backend tokens that are context, not a pharmacy signal, on their own (ruling Y3). */
export const PHARMACY_CONTEXT_ONLY_TOKENS: readonly string[] = [
  'vinegar', 'glucose', 'flu', 'dose', 'dosage', 'pharmacy',
];

const SUPPLEMENT_CATEGORIES = new Set(['supplements', 'supplement', 'vitamin', 'vitamins']);

const PHARMACY_TOKEN_RE = new RegExp(
  `(?:^|[^a-z0-9])(?:${PHARMACY_TABLET_TOKENS.filter(
    (tok) => !PHARMACY_CONTEXT_ONLY_TOKENS.includes(tok),
  ).join('|')})(?![a-z0-9])`,
);

// A unit glued to a letter is a word and glued to a digit a model code
// ("2024 MG5"); a space then a number is a pack count, so still a dose.
const DOSE_RE = /(?:^|[^a-z0-9.,])\d+(?:[.,]\d+)?\s*(?:mg|mcg|iu)(?![a-z]|\d)/;

function normalisedCategory(value: unknown): string {
  return typeof value === 'string' ? value.toLowerCase().replace(/[\s_-]/g, '') : '';
}

export function isSupplementComparison(result: any, products: any): boolean {
  const list: any[] = Array.isArray(products) ? products : [];
  const categories: unknown[] = [result?.category_used, result?.category];
  for (const p of list) {
    categories.push(p?.category_profile?.category, p?.category);
  }
  if (categories.some((c) => SUPPLEMENT_CATEGORIES.has(normalisedCategory(c)))) {
    return true;
  }
  const texts = list.map((p) => `${p?.brand ?? ''} ${p?.name ?? ''} ${p?.variant ?? ''}`);
  if (typeof result?.query === 'string') texts.push(result.query);
  return texts.some((text) => {
    const lower = text.toLowerCase();
    return PHARMACY_TOKEN_RE.test(lower) || DOSE_RE.test(lower);
  });
}
