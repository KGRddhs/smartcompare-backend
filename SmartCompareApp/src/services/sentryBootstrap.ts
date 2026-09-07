/**
 * W3-12 — side-effect-only Sentry bootstrap.
 *
 * WHY THIS MODULE EXISTS. `initSentry()` used to be a statement in App.tsx's
 * module BODY, which reads like the first thing the app does but is not: a
 * module body runs only after its entire import graph has been evaluated.
 * App.tsx imports `authService`, which imports `services/api`, whose module
 * body calls `setupCertificatePinning()` — and on failure that path raises
 * `Sentry.captureMessage('[SECURITY] Certificate pinning init failed …')`,
 * the one alarm that says a release fleet is running unpinned, into a Sentry
 * that did not exist yet. The same window swallowed any boot crash in any
 * module App.tsx imports.
 *
 * Both module systems evaluate dependencies in source order, so importing
 * this module FIRST in `index.ts` — ahead of `./App` — runs this body before
 * App's graph is touched.
 *
 * INVARIANT (pinned by `__tests__/bootSentryOrder.w312.test.ts`): this module
 * imports ONLY `./sentry`. If it ever reaches `services/api`, even
 * transitively, it recreates the exact problem it exists to solve. Do not add
 * imports here.
 */
import { initSentry } from './sentry';

initSentry();
