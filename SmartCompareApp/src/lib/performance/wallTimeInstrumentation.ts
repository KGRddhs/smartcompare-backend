/**
 * Lane A-L3 Task L3.7 — Frontend wall-time instrumentation.
 *
 * Sprint A goal: diagnose the 88s frontend wall-time gap surfaced during
 * Bundle D/E device walkthroughs. Backend already exposes per-stage
 * timings via `metadata.stage_timings_ms` when `DEBUG_STAGE_TIMINGS=true`
 * on Railway — those measure server-side. This module measures the
 * *client* path so the gap can be triaged from the user's tap-to-tappable
 * window, not just the API wall.
 *
 * Five stages, emitted as Sentry tags on the *current* scope so the
 * `comparison_wall_time` info-level event picks them up at report() time:
 *   ttfb                 — first SSE byte received (or non-stream fallback firing)
 *   first_card_visible   — first product card animates into view
 *   all_cards_visible    — both product cards have animated in
 *   ready_celebration    — the 3-part celebration fires post-verdict
 *   user_tappable        — accordions become tappable (UX "interactive")
 *
 * Each `mark(stage)` ALSO calls Sentry.setTag synchronously so a partial
 * journey (e.g. user backed out before user_tappable) still surfaces in
 * the most-recent error breadcrumb. Final `report()` captures an info
 * event aggregating ALL milestones to a single Sentry message that can
 * be filtered by tag in the dashboard.
 *
 * IMPORTANT: this module is intentionally light — zero dependencies
 * beyond `@sentry/react-native` (already in the app). When Sentry is
 * not initialized (test, dev w/o DSN), `setTag` / `captureMessage` are
 * no-op cheap calls that don't throw.
 */
import * as Sentry from '@sentry/react-native';

export type WallTimeStage =
  | 'ttfb'
  | 'first_card_visible'
  | 'all_cards_visible'
  | 'ready_celebration'
  | 'user_tappable';

const STAGES: WallTimeStage[] = [
  'ttfb',
  'first_card_visible',
  'all_cards_visible',
  'ready_celebration',
  'user_tappable',
];

export class WallTimeTracker {
  private startTime: number = 0;
  private milestones: Record<string, number> = {};
  private started: boolean = false;

  /** Reset state + capture t=0. Call when the user taps Compare. */
  start() {
    this.startTime = Date.now();
    this.milestones = {};
    this.started = true;
    try {
      Sentry.setTag('wall_time.started_at', String(this.startTime));
    } catch {
      // Sentry not initialized — silent no-op.
    }
  }

  /**
   * Mark a stage transition. Each stage records `Date.now() - startTime`
   * milliseconds and pushes a Sentry tag named `wall_time.{stage}_ms`.
   * Idempotent — re-calling for the same stage updates the recorded
   * milestone (useful when SSE delivers `specs` twice during settle).
   */
  mark(stage: WallTimeStage) {
    if (!this.started) {
      // Without start() we have no t=0; record 0 so the tag exists but
      // future readers see the missing-start signal.
      this.startTime = Date.now();
      this.started = true;
    }
    const elapsed = Date.now() - this.startTime;
    this.milestones[stage] = elapsed;
    try {
      Sentry.setTag(`wall_time.${stage}_ms`, String(elapsed));
    } catch {
      // Sentry not initialized — silent no-op.
    }
  }

  /** Return a shallow copy of the recorded milestones. Pure read. */
  snapshot(): Record<string, number> {
    return { ...this.milestones };
  }

  /**
   * Submit an aggregate `comparison_wall_time` info event. Includes ALL
   * stage milestones as tags so the event can be filtered/grouped in
   * the Sentry dashboard. Call once per comparison (e.g. when
   * user_tappable lands OR on screen unmount, whichever comes first).
   */
  report() {
    if (!this.started) return;
    const tags: Record<string, string> = {};
    for (const stage of STAGES) {
      if (this.milestones[stage] != null) {
        tags[`wall_time.${stage}_ms`] = String(this.milestones[stage]);
      }
    }
    try {
      Sentry.captureMessage('comparison_wall_time', {
        level: 'info',
        tags,
      });
    } catch {
      // Sentry not initialized — silent no-op.
    }
  }
}

/** Convenience singleton — most call sites only need one tracker per
 *  screen instance. ResultsScreen can use this, or callers may
 *  instantiate their own when running concurrent comparisons (rare). */
let _singleton: WallTimeTracker | null = null;
export function getWallTimeTracker(): WallTimeTracker {
  if (!_singleton) _singleton = new WallTimeTracker();
  return _singleton;
}

/** Test-only reset — drops the singleton so a fresh tracker instantiates
 *  on the next `getWallTimeTracker()` call. Not exported for production use. */
export function __resetWallTimeTrackerForTests() {
  _singleton = null;
}
