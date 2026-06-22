/**
 * _deltaText — shared dimension delta-text guard (frag-content-quality WS-B Task B3).
 *
 * Single source of truth for the FE defense-in-depth against raw point-math
 * leaking into dimension delta captions. The backend (WS-B) is canonical and
 * emits qualitative `delta_text` (e.g. "Longer-lasting"); these guards fail
 * a future regression loud-but-clean rather than render an internal 0-100
 * "+Npt" unit that is shown nowhere else in the UI.
 *
 * Imported by RunnerUpWinsCard.tsx and DimensionBars.tsx so both share ONE
 * regex + helper (no drift).
 */

// Raw point-math the UI must NOT surface: "+18pt", "18 pt", "-5pts",
// "10.7-point higher", "4 points". Broadened from RunnerUpWinsCard's original
// `/\d+\s*pts?\b/i` to also catch the spelled-out "point"/"points" form,
// decimals (e.g. "10.7 point"), and the hyphen-joined "N-point" form (a
// confirmed live verdict leak: "10.7-point higher overall score").
export const POINT_MATH_RE = /\b\d+(?:\.\d+)?[-\s]*(?:pt|pts|point|points)\b/i;

/**
 * Broader score-internals guard (frag-content-quality WS-A Task A6) — catches
 * raw internal-scoring leaks in verdict prose / runner-up key_tradeoff:
 *   - "10.7-point" / "4 points"      (point margins; superset of POINT_MATH_RE)
 *   - "score of 100"
 *   - "87/100"
 *   - "overall score"
 * The backend (WS-A `strip_score_internals` at the response_builder chokepoint)
 * is canonical and already scrubs these; this FE guard fails a future
 * regression loud-but-clean by DROPPING the offending line rather than
 * rendering an internal-only score artifact (no `/100`, no "N points", no
 * "overall score" is ever a user-facing surface).
 */
export const SCORE_INTERNALS_RE =
  /\b\d+(?:\.\d+)?[-\s]?(?:point|pt)s?\b|\bscore of \d+|\b\d+\/100\b|\boverall score\b/i;

/**
 * Safe delta caption for a dimension. Returns `deltaText` unchanged when it is
 * qualitative; when it matches raw point-math, falls back to the dimension
 * `label` (the bar magnitude already carries the signal) — or `''` when no
 * usable label is supplied.
 */
export function safeDelta(deltaText: string | null | undefined, label?: string | null): string {
  const delta = (deltaText ?? '').trim();
  if (delta.length > 0 && !POINT_MATH_RE.test(delta)) return delta;
  return (label ?? '').trim();
}
