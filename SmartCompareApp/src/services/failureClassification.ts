/**
 * M18 MB-flows-05 — the explicit load-failure classification matrix.
 *
 * ResultsScreen (and any future load-and-render screen) must never guess a
 * failure's meaning from whichever fields happen to exist on the thrown
 * error. Every failure shape the client can produce funnels through this
 * one function, and every branch is pinned in
 * __tests__/api.networkMatrix.m18.test.ts.
 *
 * The matrix (first match wins):
 *   1. USAGE_LIMIT (top-level err.code from the camera raw-fetch tagged
 *      error, or the axios response.data / detail shapes)  -> 'usage_limit'
 *   2. HTTP 404                                            -> 'not_found'
 *   3. HTTP 401 (axios refresh-interceptor territory)      -> 'auth'
 *   4. code TIMEOUT / STREAM_TIMEOUT (any carrier)         -> 'timeout'
 *   5. HTTP 503                                            -> 'timeout'
 *   6. any other 5xx — the BACKEND is down, retryable      -> 'timeout'
 *   7. no `.response` at all — offline TypeError, an axios
 *      deadline (ECONNABORTED), an aborted fetch, or a bare
 *      transport Error: the request never completed, so it
 *      is retryable and is NEVER the user's fault           -> 'timeout'
 *   8. everything else (a real 4xx rejection)              -> 'generic'
 *
 * 'timeout' deliberately reuses the existing soft, retryable loadError
 * state (results.timeout.* copy + tap-to-retry) — per MB-flows-05's fix:
 * offline and 5xx both route to the retry affordance, and 'vision_failed'
 * is reserved for an actual `action === 'error'` identify RESPONSE (a
 * 200 that says vision could not read the photos), never for a thrown
 * transport/server failure.
 *
 * Zero imports on purpose: screens can consume this without dragging the
 * axios/api surface into test harnesses.
 */

export type LoadFailureKind =
  | 'usage_limit'
  | 'not_found'
  | 'auth'
  | 'timeout'
  | 'generic';

export function classifyLoadFailure(err: any): LoadFailureKind {
  const status: unknown = err?.response?.status;
  const code: unknown =
    err?.response?.data?.code ??
    err?.response?.data?.detail?.code ??
    err?.code;

  if (code === 'USAGE_LIMIT') return 'usage_limit';
  if (status === 404) return 'not_found';
  if (status === 401) return 'auth';
  if (code === 'TIMEOUT' || code === 'STREAM_TIMEOUT') return 'timeout';
  if (status === 503) return 'timeout';
  if (typeof status === 'number' && status >= 500) return 'timeout';
  if (!err?.response) return 'timeout';
  return 'generic';
}
