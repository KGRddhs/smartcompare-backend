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
