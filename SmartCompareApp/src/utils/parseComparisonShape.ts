/**
 * Comparison-shape detector + splitter. Spec ref:
 * docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md § 4.1.1.
 *
 * Originally lifted from SearchOverlay.tsx:27 (the regex) and extracted here
 * as part of Bundle B so TwoInputShell can paste-split without depending on
 * the to-be-deleted overlay.
 */

/**
 * Matches a separator that indicates the input is shaped like
 * "X vs Y" / "X and Y" / "X, Y" / "X أو Y" / "X مقابل Y".
 */
export const COMPARISON_PATTERN = /\s(vs|&|and|or|أو|مقابل)\s|,/i;

export function looksLikeTwoProducts(raw: string): boolean {
  return COMPARISON_PATTERN.test(raw);
}

/**
 * Splits the raw string at the FIRST separator match.
 * Returns null if either half is < 2 chars after trim.
 */
export function splitComparisonShape(s: string): [string, string] | null {
  const re = new RegExp(COMPARISON_PATTERN.source, 'i');
  const match = re.exec(s);
  if (!match) return null;
  const cut = match.index;
  const left = s.slice(0, cut).trim();
  const right = s.slice(cut + match[0].length).trim();
  if (left.length < 2 || right.length < 2) return null;
  return [left, right];
}
