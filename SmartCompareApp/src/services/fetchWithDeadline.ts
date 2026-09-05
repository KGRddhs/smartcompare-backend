/**
 * A8 — bounded raw `fetch`.
 *
 * WHY THIS EXISTS
 * React Native's `fetch` is the whatwg-fetch polyfill over XHR, and RN sets
 * NO default deadline (`XMLHttpRequest.timeout` defaults to 0; Android's
 * OkHttpClientProvider ships 0/0/0 connect/read/write timeouts). A stalled
 * socket therefore never rejects — it simply never settles — so a
 * `try/catch` around a raw `fetch` catches nothing and the caller's loading
 * state stays up forever. Axios callers are unaffected: `api` carries its
 * own `timeout`, and the compare-class calls carry per-request deadlines.
 *
 * WHY `Promise.race` AND NOT ONLY THE SIGNAL
 * `AbortController` alone delegates the outcome to the fetch implementation:
 * the request is cancelled, but the promise only settles if the polyfill
 * actually rejects on abort. Racing an explicit deadline makes the SETTLEMENT
 * deterministic regardless of the transport, while the `abort()` still runs
 * so the socket and its upload buffer are released rather than left in
 * flight. Both halves are load-bearing — the signal frees the resource, the
 * race frees the caller.
 *
 * ERROR SHAPE
 * A deadline expiry rejects with a normalized `{ name: 'TimeoutError',
 * code: 'TIMEOUT' }` error, decided by this module's OWN `timedOut` latch
 * rather than by sniffing the polyfill's `AbortError`. That matters twice
 * over: the polyfill's abort rejection shape differs across RN versions, and
 * a caller-supplied abort must never be mistaken for a deadline. Any other
 * rejection (offline `TypeError`, TLS/certificate-pinning failure, DNS)
 * propagates UNCHANGED so existing diagnostics keep seeing the real error.
 *
 * `services/api.ts` `identifyFromImages` keeps its own inline copy of this
 * pattern (M18 MB-perf-03, the 120s multipart budget). It is deliberately
 * not refactored onto this helper: that path is live on devices and carries
 * its own USAGE_LIMIT/500 branching, so re-plumbing it would be churn on a
 * hot path for no behavioural gain.
 */

/**
 * Deadline for a social sign-in POST to `/api/v1/auth/social-login`.
 *
 * This is one small JSON round-trip (an id_token in, a session out), not the
 * 120s multipart image budget — but it must still tolerate a slow GCC mobile
 * connection, because an over-tight deadline turns a sign-in that WOULD have
 * succeeded into a spurious retry. 25s is comfortably past the backend's own
 * work here while staying far below "the screen is frozen".
 */
export const SOCIAL_LOGIN_TIMEOUT_MS = 25000;

/** Error `code` carried by a deadline expiry. */
export const DEADLINE_ERROR_CODE = 'TIMEOUT';

function deadlineError(timeoutMs: number): Error & { code: string } {
  return Object.assign(new Error(`request_deadline_exceeded_${timeoutMs}ms`), {
    name: 'TimeoutError',
    code: DEADLINE_ERROR_CODE,
  });
}

/**
 * `fetch` with a hard wall-clock deadline.
 *
 * Resolves with the `Response` when the request completes in time. Rejects
 * with a `code: 'TIMEOUT'` error when the deadline expires (and aborts the
 * underlying request), or with the transport's own error otherwise.
 */
export async function fetchWithDeadline(
  input: string,
  init: Record<string, unknown>,
  timeoutMs: number
): Promise<Response> {
  const controller = new AbortController();
  let timedOut = false;
  let timer: ReturnType<typeof setTimeout> | undefined;

  const deadline = new Promise<never>((_resolve, reject) => {
    timer = setTimeout(() => {
      timedOut = true;
      // Release the socket / upload buffer. The race below is what
      // guarantees the CALLER is released, independently of this.
      try {
        controller.abort();
      } catch {
        // An abort that throws must never mask the deadline rejection.
      }
      reject(deadlineError(timeoutMs));
    }, timeoutMs);
  });

  const request = fetch(input, { ...init, signal: controller.signal } as any);
  // The aborted request usually rejects AFTER the race has already settled.
  // Attach a sink so that late rejection is never an unhandled one.
  request.catch(() => {});

  try {
    return await Promise.race([request, deadline]);
  } catch (err: unknown) {
    // A rejection that arrives once the deadline has fired is the abort we
    // caused; report it as the deadline, not as a transport failure.
    if (timedOut) throw deadlineError(timeoutMs);
    throw err;
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}

/** True when `err` is a deadline expiry from `fetchWithDeadline`. */
export function isDeadlineError(err: unknown): boolean {
  return (err as { code?: unknown } | null | undefined)?.code === DEADLINE_ERROR_CODE;
}
