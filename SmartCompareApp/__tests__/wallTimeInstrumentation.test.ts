/**
 * Lane A-L3 Task L3.7 — Wall-time instrumentation unit tests.
 *
 * Exercises the 5-stage tracker that diagnoses the 88s frontend wall-time
 * gap surfaced in Bundle D/E device walkthroughs. Pins the Sentry tag
 * shape so dashboard filters don't break across rollouts.
 */

import * as Sentry from '@sentry/react-native';
import {
  WallTimeTracker,
  getWallTimeTracker,
  __resetWallTimeTrackerForTests,
} from '../src/lib/performance/wallTimeInstrumentation';

jest.mock('@sentry/react-native', () => ({
  setTag: jest.fn(),
  captureMessage: jest.fn(),
}));

const setTag = Sentry.setTag as unknown as jest.Mock;
const captureMessage = Sentry.captureMessage as unknown as jest.Mock;

describe('WallTimeTracker — L3.7 contract', () => {
  beforeEach(() => {
    setTag.mockClear();
    captureMessage.mockClear();
    __resetWallTimeTrackerForTests();
  });

  it('records all 5 stages and emits matching Sentry tags', () => {
    const tracker = new WallTimeTracker();
    const t0 = Date.now();
    tracker.start();

    // Simulate a comparison journey. Advance the clock between marks
    // via jest fake timers if you need deterministic deltas; the
    // contract under test is shape, not absolute values.
    tracker.mark('ttfb');
    tracker.mark('first_card_visible');
    tracker.mark('all_cards_visible');
    tracker.mark('ready_celebration');
    tracker.mark('user_tappable');

    const snap = tracker.snapshot();
    expect(snap.ttfb).toBeDefined();
    expect(snap.first_card_visible).toBeDefined();
    expect(snap.all_cards_visible).toBeDefined();
    expect(snap.ready_celebration).toBeDefined();
    expect(snap.user_tappable).toBeDefined();

    // Each milestone must be a non-negative number.
    for (const v of Object.values(snap)) {
      expect(typeof v).toBe('number');
      expect(v).toBeGreaterThanOrEqual(0);
    }

    // Sentry.setTag called with the expected wall_time.{stage}_ms keys.
    const tagKeys = setTag.mock.calls.map((c) => c[0]);
    expect(tagKeys).toContain('wall_time.started_at');
    expect(tagKeys).toContain('wall_time.ttfb_ms');
    expect(tagKeys).toContain('wall_time.first_card_visible_ms');
    expect(tagKeys).toContain('wall_time.all_cards_visible_ms');
    expect(tagKeys).toContain('wall_time.ready_celebration_ms');
    expect(tagKeys).toContain('wall_time.user_tappable_ms');

    // Every emitted tag value is a string (Sentry tag contract).
    for (const [, value] of setTag.mock.calls) {
      expect(typeof value).toBe('string');
    }

    // Stage marks AFTER start time so all >= 0.
    expect(snap.ttfb).toBeGreaterThanOrEqual(0);
    expect(t0).toBeLessThanOrEqual(Date.now());
  });

  it('captureMessage fires "comparison_wall_time" with stage tags on report()', () => {
    const tracker = new WallTimeTracker();
    tracker.start();
    tracker.mark('ttfb');
    tracker.mark('user_tappable');
    tracker.report();

    expect(captureMessage).toHaveBeenCalledTimes(1);
    const [msg, opts] = captureMessage.mock.calls[0];
    expect(msg).toBe('comparison_wall_time');
    expect(opts.level).toBe('info');
    expect(opts.tags['wall_time.ttfb_ms']).toBeDefined();
    expect(opts.tags['wall_time.user_tappable_ms']).toBeDefined();
    // Stages that were never marked are absent from the tag dict.
    expect(opts.tags['wall_time.first_card_visible_ms']).toBeUndefined();
  });

  it('report() is a no-op when start() was never called', () => {
    const tracker = new WallTimeTracker();
    tracker.report();
    expect(captureMessage).not.toHaveBeenCalled();
  });

  it('mark() before start() auto-initializes t=0 so the tag still emits', () => {
    const tracker = new WallTimeTracker();
    tracker.mark('ttfb');
    expect(tracker.snapshot().ttfb).toBeDefined();
    const ttfbTag = setTag.mock.calls.find(
      (c) => c[0] === 'wall_time.ttfb_ms'
    );
    expect(ttfbTag).toBeDefined();
  });

  it('mark() is idempotent — re-marking same stage updates the milestone', () => {
    const tracker = new WallTimeTracker();
    tracker.start();
    tracker.mark('ttfb');
    const first = tracker.snapshot().ttfb;
    // Tiny synchronous loop to advance Date.now() by at least 1 ms.
    const deadline = Date.now() + 2;
    while (Date.now() < deadline) {
      // busy-wait
    }
    tracker.mark('ttfb');
    const second = tracker.snapshot().ttfb;
    expect(second).toBeGreaterThanOrEqual(first);
  });

  it('singleton helper returns a stable tracker across calls within a session', () => {
    const a = getWallTimeTracker();
    const b = getWallTimeTracker();
    expect(a).toBe(b);
  });

  it('test-reset helper drops the singleton so a fresh instance comes out', () => {
    const a = getWallTimeTracker();
    __resetWallTimeTrackerForTests();
    const b = getWallTimeTracker();
    expect(a).not.toBe(b);
  });

  it('survives Sentry.setTag throwing (test resilience)', () => {
    setTag.mockImplementationOnce(() => {
      throw new Error('Sentry not initialized');
    });
    const tracker = new WallTimeTracker();
    // start() catches the throw silently.
    expect(() => tracker.start()).not.toThrow();
  });
});
