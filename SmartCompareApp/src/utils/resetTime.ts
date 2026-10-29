/**
 * S81-08 CLIENT-FIRST-OTA: the exact local reset time of the free comparisons
 * (spec 2.7 as amended by RULINGS_S81_08 R-S08-2 / R-S08-8 / R-S08-10 /
 * R-S08-14 and GATE_S81_08 GC-2 / GC-5). Pure functions: no I/O, no clock of
 * their own (the caller passes `nowMs`).
 *
 * - resolveResetAt: the reset instant carried by a /usage/status body or a
 *   USAGE_LIMIT 429 detail, read in this order (R-S08-14 / GC-2):
 *   retry_after_seconds, then retry_after (whole seconds, 1..172800, counted
 *   from now), then resets_at (an ISO instant strictly after now and at most
 *   48 h ahead). Anything else is ignored, so the screen keeps today's copy.
 * - formatResetClock: HH:MM on the 24-hour clock in ASCII digits, rounded to
 *   the nearest minute, in the device's local time unless an offset is given.
 * - sheetResetClock: the limit sheet's rule (R-S08-2 / R-S08-8 / GC-5): the
 *   daily state shows a resolved time always; the open and unknown states only
 *   when the status names a daily axis (`counted_scope` on /usage/status,
 *   `scope` on the 429 detail); the monthly state never. The fetched
 *   /usage/status decides first, like the sheet's state. A relative reset of
 *   the 429 detail is counted from the FIRST time that detail object is
 *   resolved (RULINGS_FIX1_S81_08 F1-4), so a re-render (the /usage/status
 *   fetch landing) never shifts the shown minute; this per-object anchor is
 *   the module's only state.
 */

const MAX_AHEAD_MS = 48 * 60 * 60 * 1000;
const MAX_RETRY_SECONDS = 172800;
const MINUTE_MS = 60 * 1000;

/** The counted axes a reset time may be shown for (R-S08-2). */
export const DAILY_SCOPES: readonly string[] = ['daily', 'device_daily'];

/** The reset fields a /usage/status body or a USAGE_LIMIT 429 detail may carry. */
export interface ResetSource {
  resets_at?: unknown;
  retry_after_seconds?: unknown;
  retry_after?: unknown;
}

function wholeSeconds(value: unknown): number | null {
  return typeof value === 'number' && Number.isInteger(value) && value > 0 && value <= MAX_RETRY_SECONDS
    ? value
    : null;
}

/** The reset instant, or null when nothing usable is present. */
export function resolveResetAt(src: ResetSource | null | undefined, nowMs: number): Date | null {
  if (!src || typeof src !== 'object' || !Number.isFinite(nowMs)) return null;
  const relative = wholeSeconds(src.retry_after_seconds) ?? wholeSeconds(src.retry_after);
  if (relative !== null) return new Date(nowMs + relative * 1000);
  if (typeof src.resets_at === 'string') {
    const at = Date.parse(src.resets_at);
    if (Number.isFinite(at) && at > nowMs && at <= nowMs + MAX_AHEAD_MS) return new Date(at);
  }
  return null;
}

/**
 * `HH:MM` (24-hour, zero-padded, ASCII digits) of `at` rounded to the nearest
 * minute, shifted by `offsetMinutes` (default: the device's own offset at that
 * minute, i.e. the device-local clock).
 */
export function formatResetClock(at: Date, offsetMinutes?: number): string {
  const rounded = Math.round(at.getTime() / MINUTE_MS) * MINUTE_MS;
  const offset =
    typeof offsetMinutes === 'number' && Number.isFinite(offsetMinutes)
      ? offsetMinutes
      : -new Date(rounded).getTimezoneOffset();
  const shifted = new Date(rounded + offset * MINUTE_MS);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(shifted.getUTCHours())}:${pad(shifted.getUTCMinutes())}`;
}

// F1-4: the first nowMs a 429 detail object was resolved at (weakly keyed, so
// a new 429 gets a new anchor and nothing is kept alive).
const initialAnchors = new WeakMap<object, number>();

function anchoredNow(src: unknown, nowMs: number): number {
  if (!src || typeof src !== 'object' || !Number.isFinite(nowMs)) return nowMs;
  const seen = initialAnchors.get(src);
  if (seen !== undefined) return seen;
  initialAnchors.set(src, nowMs);
  return nowMs;
}

/** True for a scope that names a daily axis. */
export function isDailyScope(scope: unknown): boolean {
  return typeof scope === 'string' && DAILY_SCOPES.includes(scope);
}

/**
 * The limit sheet's reset clock for its state `kind`, or null for today's
 * copy. `fetched` is the /usage/status body (it decides first); `initial` is
 * the USAGE_LIMIT 429 detail the caller passed to the sheet.
 */
export function sheetResetClock(
  kind: string,
  fetched: (ResetSource & { counted_scope?: unknown }) | null | undefined,
  initial: (ResetSource & { scope?: unknown }) | null | undefined,
  nowMs: number,
): string | null {
  if (kind === 'monthly') return null;
  const fromFetched = resolveResetAt(fetched, nowMs);
  const at = fromFetched ?? resolveResetAt(initial, anchoredNow(initial, nowMs));
  if (at === null) return null;
  if (kind !== 'daily') {
    const scope = fromFetched ? fetched?.counted_scope : initial?.scope;
    if (!isDailyScope(scope)) return null;
  }
  return formatResetClock(at);
}
