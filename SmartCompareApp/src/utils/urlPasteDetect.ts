/**
 * Cheap URL-shape detector used by TwoInputShell's paste-detection.
 * Spec ref: docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md § 4.1.2.
 *
 * Full URL validation happens later via `new URL()` in TwoInputShell's
 * blur-validator — this helper exists purely to disambiguate "user pasted a
 * link" from "user pasted a comparison phrase" inside onChange.
 */

const URL_SHAPE = /^https?:\/\/[^\s]+$/i;

export function looksLikeUrl(s: string): boolean {
  return URL_SHAPE.test(s.trim());
}
