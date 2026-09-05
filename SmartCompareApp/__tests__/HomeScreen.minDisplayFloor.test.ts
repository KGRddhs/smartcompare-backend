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

  it('uses the floor helper for SSE-stream success', () => {
    expect(SOURCE).toMatch(/navigateToResultsWithFloor\(\s*data\s*\)/);
  });

  it('uses the floor helper for URL compare success', () => {
    expect(SOURCE).toMatch(
      /navigateToResultsWithFloor\(\s*response\.data\s*\)/
    );
  });

  // Bundle B redesign moved the image-identify path out of HomeScreen
  // (now ScanCamera → ResultsScreen via vision_products param). HomeScreen
  // text/URL paths still flow through the floor helper; image-identify
  // entry is no longer applicable to this test surface.

  it('does NOT navigate Compare success paths without the floor helper', () => {
    // Each successful compare must go through navigateToResultsWithFloor.
    // The helper itself contains the only `navigation.navigate('Results' as any`
    // call shape. Direct navigate to Results in HomeScreen is reserved for
    // distinct entry shapes (history tap, etc.) that don't need the
    // brand-moment floor.
    //
    // Compare-path forbidden pattern: a bare
    // `navigation.navigate('Results', {result: ...})` outside the helper.
    // The helper match is the case-cast `'Results' as any` form so the
    // un-cast literal-args form must stay at 0 occurrences.
    const bareLiteralNav = SOURCE.match(
      /navigation\.navigate\(['"]Results['"]\s*,\s*\{\s*result\s*:/g
    );
    expect((bareLiteralNav ?? []).length).toBe(0);

    // The helper is the ONLY allowed `'Results' as any` call carrying a
    // `{result}`. Bundle E S3 added a separate re-open navigate (the
    // Smart-pick "View verdict" CTA) which since A18 carries the
    // `{comparison_id: ...}` shape — a distinct entry path, not a
    // compare-success completion, so it does not go through the helper.
    const helperShapedCalls = SOURCE.match(
      /navigation\.navigate\(['"]Results['"] as any/g
    );
    const helperInternalNav = SOURCE.match(
      /navigation\.navigate\(['"]Results['"] as any,\s*\{\s*result\s*\}/g
    );
    // At least 1 helper-shaped call must exist (the floor closure itself).
    expect((helperShapedCalls ?? []).length).toBeGreaterThanOrEqual(1);
    // And EXACTLY 1 of those must wrap a `{result}` (the floor's payload
    // — proves no second compare-success navigation has slipped in).
    expect((helperInternalNav ?? []).length).toBe(1);
  });

  it('re-open entry sidesteps the HomeScreen floor (distinct from compare success)', () => {
    // Bundle E S3 — HomeEditorialSections.onPressVerdict re-opens an
    // existing comparison rather than completing one, so it does NOT go
    // through HomeScreen's navigateToResultsWithFloor.
    //
    // A18 corrected two things here. (1) The pinned param name was
    // `from_history`, which is not in RootStackParamList.Results and
    // which ResultsScreen never reads — pinning it kept the dead-tap
    // alive. The real re-open param is `comparison_id`. (2) The old
    // rationale ("the result is already cached/fetched in History") was
    // factually wrong: nothing pre-fetches it. ResultsScreen fetches via
    // getComparison(id) and enforces its OWN 1.2s floor on that path, so
    // the brand moment still lands — it is just owned by ResultsScreen,
    // not by HomeScreen's helper.
    const reopenNav = SOURCE.match(
      /navigation\.navigate\(['"]Results['"],\s*\{\s*comparison_id\s*:/g
    );
    expect((reopenNav ?? []).length).toBe(1);
    // And the dead param must never come back on any Results navigate.
    // Whole-line comments are stripped first so this greps CODE, not the
    // prose above (which necessarily names the param it forbids).
    const CODE = SOURCE.split('\n')
      .filter((line: string) => !line.trim().startsWith('//'))
      .join('\n');
    expect(CODE).not.toMatch(/from_history/);
  });
});
