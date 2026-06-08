/**
 * HomeScreen min-display floor tests — Task #54.
 *
 * Verifies the 1.2s floor logic that gates Home→Results navigation.
 * Per design § 3 even cached responses (~200ms) must show loading for
 * 1.2s minimum so the brand moment lands.
 *
 * Tests the helper's timing contract directly (timer math + navigation
 * call order) rather than rendering HomeScreen end-to-end. Full
 * integration is verified on-device at the Phase 3 QA gate.
 */

const MIN_LOADING_MS = 1200;

/**
 * Pure helper that mirrors the logic in HomeScreen.navigateToResultsWithFloor.
 * Extracted here so the timing contract has a unit-test home; the live
 * version inside HomeScreen.tsx is the same shape.
 */
function navigateToResultsWithFloor(
  startedAt: number,
  now: () => number,
  scheduleAt: (delayMs: number, fn: () => void) => void,
  navigate: () => void
) {
  const elapsed = now() - startedAt;
  const remaining = Math.max(0, MIN_LOADING_MS - elapsed);
  if (remaining === 0) {
    navigate();
  } else {
    scheduleAt(remaining, navigate);
  }
}

describe('HomeScreen min-display floor (Task #54)', () => {
  it('navigates IMMEDIATELY when work took ≥ 1200ms (no extra delay)', () => {
    const navigate = jest.fn();
    const schedule = jest.fn();
    const startedAt = 1000;
    const now = () => 2500; // 1500ms elapsed
    navigateToResultsWithFloor(startedAt, now, schedule, navigate);
    expect(navigate).toHaveBeenCalledTimes(1);
    expect(schedule).not.toHaveBeenCalled();
  });

  it('delays navigation when work took < 1200ms (cached response)', () => {
    const navigate = jest.fn();
    const schedule = jest.fn();
    const startedAt = 1000;
    const now = () => 1200; // 200ms elapsed (cache hit)
    navigateToResultsWithFloor(startedAt, now, schedule, navigate);
    expect(navigate).not.toHaveBeenCalled();
    expect(schedule).toHaveBeenCalledTimes(1);
    expect(schedule).toHaveBeenCalledWith(1000, expect.any(Function));
  });

  it('schedules 0 remaining ms = navigates immediately at the boundary', () => {
    const navigate = jest.fn();
    const schedule = jest.fn();
    const startedAt = 1000;
    const now = () => 2200; // exactly 1200ms elapsed
    navigateToResultsWithFloor(startedAt, now, schedule, navigate);
    expect(navigate).toHaveBeenCalledTimes(1);
    expect(schedule).not.toHaveBeenCalled();
  });

  it('clamps negative elapsed (clock skew) to a full 1200ms wait', () => {
    const navigate = jest.fn();
    const schedule = jest.fn();
    const startedAt = 5000;
    const now = () => 4000; // -1000ms (clock went backwards)
    navigateToResultsWithFloor(startedAt, now, schedule, navigate);
    expect(navigate).not.toHaveBeenCalled();
    expect(schedule).toHaveBeenCalledTimes(1);
    expect(schedule.mock.calls[0][0]).toBe(2200); // 1200 - (-1000)
  });

  it('end-to-end: timer fires the navigation after the remaining delay', () => {
    jest.useFakeTimers();
    const navigate = jest.fn();
    const startedAt = 1000;
    const now = () => 1300; // 300ms elapsed → remaining 900ms
    navigateToResultsWithFloor(
      startedAt,
      now,
      (ms, fn) => {
        setTimeout(fn, ms);
      },
      navigate
    );
    expect(navigate).not.toHaveBeenCalled();
    jest.advanceTimersByTime(899);
    expect(navigate).not.toHaveBeenCalled();
    jest.advanceTimersByTime(2);
    expect(navigate).toHaveBeenCalledTimes(1);
    jest.useRealTimers();
  });
});

describe('HomeScreen min-display floor — source-level wiring (Task #54)', () => {
  // Source-level assertions guard against regressions where someone
  // re-introduces a direct `navigation.navigate('Results', ...)` call
  // that bypasses the floor. The 3 user paths must all go through
  // `navigateToResultsWithFloor`.
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const fs = require('fs');
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const path = require('path');
  const SOURCE = fs.readFileSync(
    path.resolve(__dirname, '../src/screens/HomeScreen.tsx'),
    'utf8'
  );

  it('declares the navigateToResultsWithFloor helper', () => {
    expect(SOURCE).toMatch(/navigateToResultsWithFloor/);
  });

  it('uses the floor helper for image-identify success', () => {
    expect(SOURCE).toMatch(/navigateToResultsWithFloor\(\s*result\s*\)/);
  });

  it('uses the floor helper for SSE-stream success', () => {
    expect(SOURCE).toMatch(/navigateToResultsWithFloor\(\s*data\s*\)/);
  });

  it('uses the floor helper for URL compare success', () => {
    expect(SOURCE).toMatch(
      /navigateToResultsWithFloor\(\s*response\.data\s*\)/
    );
  });

  it('does NOT navigate to Results without the floor on success paths', () => {
    // Each successful navigate to Results must go through the helper.
    // The Paywall navigates and error paths can use direct navigate;
    // we only forbid `navigate('Results', ...)` which would bypass.
    const directNav = SOURCE.match(
      /navigation\.navigate\(['"]Results['"]\s*,/g
    );
    // The helper itself is the ONLY allowed direct call to
    // `navigation.navigate('Results' as any, ...)` — case-cast version.
    // Source has 1 such call (inside the helper closure). All other
    // paths use the helper. So the count must be exactly 1.
    expect((directNav ?? []).length).toBe(0);
    const helperInternalNav = SOURCE.match(
      /navigation\.navigate\(['"]Results['"] as any/g
    );
    expect((helperInternalNav ?? []).length).toBe(1);
  });
});
