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
 *   1b. HTTP 429 that is NOT USAGE_LIMIT (a rate limit — W3-14):
 *      a WAIT, never "No comparison loaded"; sits BELOW row 1
 *      so a metering 429 still routes to the Paywall       -> 'timeout'
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
  if (status === 429) return 'timeout';
  if (status === 404) return 'not_found';
  if (status === 401) return 'auth';
  if (code === 'TIMEOUT' || code === 'STREAM_TIMEOUT') return 'timeout';
  if (status === 503) return 'timeout';
  if (typeof status === 'number' && status >= 500) return 'timeout';
  if (!err?.response) return 'timeout';
  return 'generic';
}

/**
 * S69 U7 R3 — camera-path engine outage.
 *
 * `classifyLoadFailure` above sends any 5xx to 'timeout' ("Still gathering
 * prices" + tap-to-retry). That is right for the History detail fetch and is
 * left untouched, but on the CAMERA path a 5xx from /image/identify is an
 * engine outage (OpenAI 429/insufficient_quota, a dropped connection, the
 * preflight breaker), and tap-to-retry is a loop the user cannot exit while
 * the engine is down. These two predicates are consulted by the camera path
 * only, BEFORE the matrix, and route to the engine-unavailable state (the
 * R1 copy, a back CTA, no retry).
 *
 * Kept identical to errorCopy.ENGINE_UNAVAILABLE_CODES minus the synthetic
 * GATEWAY_UNAVAILABLE (the camera path reads the raw status instead); this
 * module stays zero-import on purpose (see the header).
 */
const CAMERA_ENGINE_OUTAGE_CODES = new Set(['LLM_UNAVAILABLE', 'INTERNAL_ERROR', 'SERVER_ERROR']);

/** A THROWN identify failure that is an engine outage. */
export function isCameraEngineOutage(err: any): boolean {
  const status: unknown = err?.response?.status;
  const code: unknown =
    err?.response?.data?.code ??
    err?.response?.data?.detail?.code ??
    err?.code;
  // The paywall, the identify watchdog and every other timeout keep their
  // own rows in the matrix.
  if (code === 'USAGE_LIMIT' || code === 'TIMEOUT' || code === 'STREAM_TIMEOUT') return false;
  if (typeof code === 'string' && CAMERA_ENGINE_OUTAGE_CODES.has(code)) return true;
  // A bare / otherwise-coded 503 stays the D2 retryable TIMEOUT.
  if (status === 503) return false;
  return typeof status === 'number' && status >= 500;
}

/**
 * A 200 identify RESPONSE that carries an engine outage: either
 * `action: 'comparison_failed'` (ENABLE_CAMERA_FAILURE_ENVELOPE, or the
 * route's exit-6 INTERNAL_ERROR), or — envelope flag OFF — an
 * `action: 'comparison'` whose `success` is false. A comparison_failed
 * without one of these codes (the cold-compare hard-cap) keeps 'timeout'.
 */
export function isCameraEngineOutageResponse(data: any): boolean {
  const code: unknown = data?.code;
  if (typeof code !== 'string' || !CAMERA_ENGINE_OUTAGE_CODES.has(code)) return false;
  if (data?.action === 'comparison_failed') return true;
  return data?.action === 'comparison' && data?.success === false;
}

/**
 * S69 U7 R3 — an UNSUCCESSFUL 200 camera comparison (envelope flag OFF:
 * `action: 'comparison'` + `success: false`) is a load failure, never a
 * result. Map its code to the empty-state kind:
 *   - TIMEOUT / STREAM_TIMEOUT                     -> 'timeout' (tap-to-retry)
 *   - LLM_UNAVAILABLE / INTERNAL_ERROR / SERVER_ERROR -> 'engine_unavailable'
 *   - anything else (INSUFFICIENT_DATA, code-less)  -> 'generic'
 */
export function classifyUnsuccessfulCameraComparison(
  data: any,
): 'timeout' | 'engine_unavailable' | 'generic' {
  const code: unknown = data?.code;
  if (code === 'TIMEOUT' || code === 'STREAM_TIMEOUT') return 'timeout';
  if (typeof code === 'string' && CAMERA_ENGINE_OUTAGE_CODES.has(code)) return 'engine_unavailable';
  return 'generic';
}
