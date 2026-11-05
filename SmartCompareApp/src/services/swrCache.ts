/**
 * S81-G6 CL2 CLIENT-SPEED -- an in-memory stale-while-revalidate cache, per
 * signed-in user.
 *
 * A leaf: no imports, nothing persisted (an app restart starts empty). The
 * owning user is set by ONE App.tsx effect keyed on user?.id; any change of
 * user (sign-out included) drops every entry, and with no user every read
 * misses and every focus refetches (the A12 behaviour). History is the only
 * reader (Home is NOT cached: its focus refetch feeds the quota pill).
 */

export const SWR_FOCUS_THROTTLE_MS = 30000;

type SwrEntry = { data: unknown; fetchedAt: number };

let swrUserId: string | null = null;
const swrEntries = new Map<string, SwrEntry>();

/** Set the owning user; a different id (null included) clears the cache. */
export function setSwrUser(userId: string | null): void {
  const next = userId ?? null;
  if (next === swrUserId) return;
  swrUserId = next;
  swrEntries.clear();
}

/** The cached entry for key, or undefined (always undefined with no user). */
export function swrRead<T>(key: string): { data: T; fetchedAt: number } | undefined {
  if (swrUserId === null) return undefined;
  const entry = swrEntries.get(key);
  if (!entry) return undefined;
  return { data: entry.data as T, fetchedAt: entry.fetchedAt };
}

/** Stamp key with data fetched at now (a no-op with no user). */
export function swrWrite<T>(key: string, data: T, now: number = Date.now()): void {
  if (swrUserId === null) return;
  swrEntries.set(key, { data, fetchedAt: now });
}

/** True with no user, no entry, or an entry at least the throttle old. */
export function shouldRefetchOnFocus(key: string, now: number = Date.now()): boolean {
  if (swrUserId === null) return true;
  const entry = swrEntries.get(key);
  if (!entry) return true;
  return now - entry.fetchedAt >= SWR_FOCUS_THROTTLE_MS;
}

/** Drop every entry whose key starts with prefix. */
export function invalidateSwrPrefix(prefix: string): void {
  Array.from(swrEntries.keys()).forEach((key) => {
    if (key.startsWith(prefix)) swrEntries.delete(key);
  });
}

/** Drop every entry and the owning user (a test seam). */
export function clearSwrCache(): void {
  swrEntries.clear();
  swrUserId = null;
}
