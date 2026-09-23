/**
 * A11 — backend error `code` -> user-facing i18n key.
 *
 * This is the ONE place that decides which sentence a failed comparison
 * shows. Callers render `t(friendlyErrorKey(parsed.code))` and NEVER
 * `parseApiError(...).message` / `error.message`.
 *
 * WHY THE MESSAGE IS NEVER RENDER INPUT
 * `parseApiError` (services/api.ts) deliberately falls through to
 * `error?.message` whenever the response is not our `{success, error, code}`
 * envelope — a Railway edge 502/504 with an HTML body, an
 * `ERR_BAD_RESPONSE` JSON parse failure, a certificate-pinning/TLS error.
 * That fallback is the raw axios string, "Request failed with status code
 * 502": it leaks transport detail AND carries the forbidden token "failed"
 * (Build Principle #4 / the zero-scary-copy contract, see
 * src/i18n/.copy-policy.json `scary_vocab_en`). It exists as a diagnostic,
 * not as copy.
 *
 * WHY NOT THE BACKEND'S OWN FRIENDLY SENTENCE
 * It is English-only, so an Arabic user would get English copy. The
 * structured `code` is the actual contract — `app/api/text_routes.py`
 * `_surface_comparison_failure` keeps it precisely "so the FE can branch
 * (e.g. show the 'choose different products' copy for INSUFFICIENT_DATA)".
 * Until A11 that contract had no consumer: `grep INSUFFICIENT_DATA` over
 * SmartCompareApp/src returned nothing.
 *
 * TOTALITY IS THE POINT
 * Every input — a recognized code, an unrecognized code, `null`, and
 * `undefined` (a codeless transport failure) — returns a key that exists in
 * both en.json and ar.json. There is no branch on which a caller can fall
 * back to a raw string, which is what made the pre-A11 codeless arm leak.
 */
export function friendlyErrorKey(code: string | null | undefined): string {
  switch (code) {
    case 'INSUFFICIENT_DATA':
      // Both products' Phase 1 specs+price came back None — retyping the
      // same pair will not help, so steer to a different//better-named pair.
      return 'home.errors.insufficientData';
    case 'RATE_LIMITED':
      // The 10/min compare limiter. The generic copy told this user to
      // "try with brand or model", i.e. to retype — actively wrong
      // guidance when the only fix is to wait.
      return 'home.errors.rateLimited';
    case 'TIMEOUT':
    case 'STREAM_TIMEOUT':
      // Genuine-BH bundle (D2). Callers usually branch on TIMEOUT before
      // reaching here; the map stays total so it is correct either way.
      return 'home.errors.timeout';
    default:
      return 'home.errors.comparison';
  }
}

/**
 * W3-14 — the same code -> key contract for the SETTINGS surfaces (Profile
 * toggles, password, EditProfile delete, Results demographics).
 *
 * These surfaces sit behind 1/5/10-minute limiters and the 900 s
 * ACCOUNT_LOCKED lockout, so the two 429 codes get their own neutral
 * sentences (deliberately NOT seconds-interpolated: "give it 900 seconds"
 * is worse than "a moment"); everything else — including `null` /
 * `undefined` / '' (a codeless transport failure or Starlette's bare 404) —
 * returns the caller's own fallback key. Total by construction, so no branch
 * can fall back to rendering `parseApiError(...).message`.
 * `friendlyErrorKey` above is untouched (its compare-surface default is
 * pinned by errorCopy.a11.test.ts).
 */
export function settingsErrorKey(code: string | null | undefined, fallbackKey: string): string {
  switch (code) {
    case 'RATE_LIMITED':
      return 'common.errors.rateLimited';
    case 'ACCOUNT_LOCKED':
      return 'common.errors.locked';
    default:
      return fallbackKey;
  }
}
