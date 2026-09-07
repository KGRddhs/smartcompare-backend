/**
 * A9 — dotted-numeric version comparison.
 *
 * WHY THIS IS ITS OWN PURE MODULE
 * It is the decision core of the force-update gate. A comparator bug here
 * does not degrade a feature — it locks every install behind an
 * unskippable screen, recoverable only by an env rollback or another OTA.
 * So it lives apart from anything that touches the network or React, and
 * it is exhaustively tested (`__tests__/versionCompare.a9.test.ts`).
 *
 * THE CLASSIC TRAP
 * A naive string/lexicographic compare orders "1.10.0" BELOW "1.9.0"
 * ('1' < '9' at the second segment), so the very first minor release past
 * .9 would read as "below minimum" for everyone. Segments are compared as
 * NUMBERS, left to right.
 *
 * PARSING IS DELIBERATELY NARROW
 * Only `[v]N(.N)*` with 1–4 numeric segments parses. Pre-release and build
 * metadata ("1.2.3-beta", "1.2.3+ci") are NOT ordered — semver's
 * pre-release precedence rules are subtle and getting them wrong here is
 * expensive, so anything outside the narrow grammar returns `null` and
 * every caller treats `null` as "cannot decide". For the update gate,
 * "cannot decide" means "do not block", which is the safe direction.
 */

/** Segments beyond this are refused (`1.2.3.4` is the widest real shape). */
export const MAX_VERSION_SEGMENTS = 4;

/**
 * Parse a version string into numeric segments.
 *
 * Accepts an optional leading `v`/`V` and surrounding whitespace. Returns
 * `null` for anything else, including empty strings, non-strings, negative
 * or non-integer segments, empty segments (`1..2`), more than
 * {@link MAX_VERSION_SEGMENTS} segments, and segments too large to hold
 * exactly as a JS number.
 */
export function parseVersion(value: unknown): number[] | null {
  if (typeof value !== 'string') return null;

  let body = value.trim();
  if (body === '') return null;
  if (body[0] === 'v' || body[0] === 'V') body = body.slice(1);
  if (body === '') return null;

  const parts = body.split('.');
  if (parts.length > MAX_VERSION_SEGMENTS) return null;

  const segments: number[] = [];
  for (const part of parts) {
    // Digits only: rejects '', '-1', '1a', '1e3', ' 1' (inner whitespace)
    // and every other shape that Number() would silently coerce.
    if (!/^[0-9]+$/.test(part)) return null;
    const n = Number(part);
    // A 20-digit segment parses to an imprecise float; refusing it is
    // better than comparing two values that are both 1e20.
    if (!Number.isSafeInteger(n)) return null;
    segments.push(n);
  }
  return segments;
}

/**
 * Compare two versions.
 *
 * Returns `-1` when `a` is older than `b`, `1` when newer, `0` when equal,
 * and `null` when either side is unparseable. Missing trailing segments
 * count as 0, so "1.2" and "1.2.0" are equal.
 */
export function compareVersions(a: unknown, b: unknown): number | null {
  const left = parseVersion(a);
  const right = parseVersion(b);
  if (left === null || right === null) return null;

  const length = Math.max(left.length, right.length);
  for (let i = 0; i < length; i += 1) {
    const l = i < left.length ? left[i] : 0;
    const r = i < right.length ? right[i] : 0;
    if (l < r) return -1;
    if (l > r) return 1;
  }
  return 0;
}

/**
 * True ONLY when `current` is parseable, `min` is parseable, and `current`
 * is strictly older than `min`.
 *
 * Every other outcome — either side unparseable, equal, or newer — is
 * `false`. The gate that consumes this can therefore never block on a
 * version it did not actually understand.
 */
export function isBelowMinVersion(current: unknown, min: unknown): boolean {
  return compareVersions(current, min) === -1;
}
