/**
 * A9 — the force-update gate as a hook, so App.tsx gains one line and the
 * whole behaviour stays testable without rendering the root tree.
 *
 * CONTRACT
 * Returns `null` on the first render and stays `null` forever unless the
 * backend affirmatively says this install is below `APP_MIN_VERSION` while
 * `APP_FORCE_UPDATE` is on. A non-null value means "show the blocking
 * screen".
 *
 * WHY IT NEVER TOUCHES BOOT
 * Nothing awaits it: the effect fires the check and returns immediately,
 * so the splash gate, auth and first paint are unaffected. The consumer
 * renders the blocking screen only AFTER the splash has been released, so
 * even a fast answer cannot delay startup — the worst case is a screen
 * swap on an app the user could not have used anyway.
 *
 * WHY NOT `InteractionManager.runAfterInteractions` (the B5 pattern used
 * for Home's consumer-less boot calls): that queue can be postponed
 * indefinitely by a looping animation. Deferring a *telemetry ping* that
 * way is free; deferring an *incident lever* means it may never fire. A
 * single small JSON GET does not block the JS thread, so it is fired
 * directly and simply given a deadline.
 */
import { useEffect, useState } from 'react';
import { checkForcedUpdate, type ForcedUpdateGate } from '../services/appVersionService';

export function useForcedUpdateGate(): ForcedUpdateGate | null {
  const [gate, setGate] = useState<ForcedUpdateGate | null>(null);

  useEffect(() => {
    let cancelled = false;

    checkForcedUpdate()
      .then((result) => {
        // The cancelled latch keeps a late answer from setting state on an
        // unmounted tree; the `result` guard keeps the app ungated on
        // every fail-open path.
        if (!cancelled && result) setGate(result);
      })
      .catch(() => {
        // checkForcedUpdate is written not to reject. This catch exists so
        // that if it ever does, the failure is inert rather than an
        // unhandled rejection — a version check must never gate the app.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return gate;
}
