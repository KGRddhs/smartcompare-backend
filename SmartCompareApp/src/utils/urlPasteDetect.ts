/**
 * Cheap URL-shape detector used by TwoInputShell's paste-detection.
 * Spec ref: docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md § 4.1.2.
 *
 * Full URL validation happens later via `new URL()` in TwoInputShell's
 * blur-validator — this helper exists purely to disambiguate "user pasted a
 * link" from "user pasted a comparison phrase" inside onChange.
 *
 * Predicate is the anchored regex VERBATIM from spec § 4.1.2 (no
 * pre-trimming). Leading/trailing whitespace deliberately fails the
 * predicate so the auto-mode-switch stays conservative — a false-negative
 * (user has to tap Link manually) is preferred over a false-positive
 * (unwanted mode change on a whitespace-prefixed paste). Cross-QA
 * finding OQ-FE.
 *
 * NOTE for callers: do NOT pre-trim the input before passing it here.
 * The whole point of the anchored predicate is to be sensitive to the
 * exact paste shape. TwoInputShell's `handleBoxChange` historically
 * passed `next.trim()` — that's being corrected in tandem with this
 * change.
 */

const URL_SHAPE = /^https?:\/\/[^\s]+$/i;

export function looksLikeUrl(s: string): boolean {
  return URL_SHAPE.test(s);
}
