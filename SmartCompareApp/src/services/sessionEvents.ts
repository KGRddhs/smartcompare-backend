/**
 * M18 MB-flows-02 — session-invalidation event channel.
 *
 * `isAuthenticated` in App.tsx was previously flipped false ONLY by the
 * user-initiated handleLogout, so a session cleared from non-UI code
 * (the 401 interceptor's failed refresh in api.ts) left the app
 * rendering MainTabs with no token and no route back to Auth.
 *
 * This is a dependency-free pub/sub so api.ts (which must not import
 * App.tsx) can tell the root navigator "this session is dead". App.tsx
 * subscribes once on mount and downgrades to the Auth stack.
 *
 * NOT emitted from clearSession() itself: handleLogout calls
 * clearSession, and emitting there would re-enter the logout path
 * (listener -> logout -> clearSession -> emit -> listener ...).
 * Emission sites are exactly the non-UI session-death points:
 * api.ts/performRefresh (mid-session 401) and, since A3,
 * authService/runBootRefresh (the boot refresh, which now runs in the
 * background instead of blocking the splash).
 */

type SessionInvalidListener = () => void;

const listeners = new Set<SessionInvalidListener>();

/**
 * Subscribe to session-invalidation. Returns an unsubscribe function.
 */
export function onSessionInvalid(listener: SessionInvalidListener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/**
 * Notify all subscribers that the stored session is dead (cleared or
 * unrecoverable). A throwing listener never blocks the others.
 */
export function emitSessionInvalid(): void {
  for (const listener of Array.from(listeners)) {
    try {
      listener();
    } catch {
      // Listener errors are the listener's problem — the remaining
      // subscribers must still hear that the session died.
    }
  }
}

/** Test-only: drop all listeners. */
export function __resetSessionListeners(): void {
  listeners.clear();
}
