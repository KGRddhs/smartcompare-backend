/**
 * Bundle E S3 Hot-Fix Wave 2 R3 — Gate B [IMPORTANT] #2.
 *
 * Wave 2 R1 implemented StageChecklist cycling with `Math.min(cursor + 1,
 * count) but capped via modulo cycle (cursor > count → 0). Gate B
 * flagged the snap-back: at wall floors 14-25s the user sees the cycle
 * loop 2-4 times, all 5 emerald checkmarks vanishing back to pending.
 *
 * R3 contract: cursor advances 0..count, then FREEZES at count. The
 * loader stays mounted until navigateToResultsWithFloor resolves; the
 * frozen all-done state IS the correct UX — work is locked in.
 *
 * Tests pin:
 *   - cursor advances on the per-stage schedule
 *   - at cursor=count, all stages render `done` (full emerald)
 *   - on subsequent ticks past cursor=count, status STAYS done (no wrap)
 *
 * A2 (2026-09-05) retargeted the cadence from a flat 900ms metronome to
 * the per-stage schedule in LoadingScreenVariants
 * (DEFAULT_COMPARISON_STAGE_DONE_AT_MS) — the flat cadence claimed all five
 * checks DONE at 4.5s while a cold compare runs ~25-31s. The FREEZE
 * contract this file exists to protect is UNCHANGED and every assertion
 * below still asserts it: the cursor still advances monotonically to
 * `count` and still holds there, and the no-wrap assertions were widened
 * (not weakened) to cover the longer schedule. Only the clock the walk is
 * driven on moved. Do NOT "simplify" this back toward a modulo cycle —
 * that is the R3/Gate B bug, and re-pacing was chosen precisely because it
 * fixes the honesty problem WITHOUT reintroducing it.
 */

import React from 'react';
import { render, act } from '@testing-library/react-native';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: any) => {
      if (opts && typeof opts === 'object' && 'defaultValue' in opts) {
        return opts.defaultValue;
      }
      return key;
    },
  }),
}));

jest.mock('../src/components/hero/LoadingRings', () => {
  const ReactRequired = require('react');
  return {
    LoadingRings: (props: any) =>
      ReactRequired.createElement('View', {
        testID: 'mock-loading-rings',
        ...props,
      }),
  };
});

import { LoadingScreenVariants } from '../src/screens/LoadingScreenVariants';

const STAGE_COUNT = 5;
// Cumulative wall-clock offsets at which each cursor value is reached,
// mirroring DEFAULT_COMPARISON_STAGE_DONE_AT_MS in the component.
const STAGE_DONE_AT_MS = [1200, 4200, 12000, 19500, 26000];
const ALL_DONE_AT_MS = STAGE_DONE_AT_MS[STAGE_DONE_AT_MS.length - 1];

describe('LoadingScreenVariants — Wave 2 R3 freeze-at-complete (no wrap-back)', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  it('after every stage walks to done, status stays done on subsequent ticks (no wrap to pending)', () => {
    const { getByTestId } = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        testID="lsv-r3"
      />,
    );

    // Walk through all 5 stages. At the final scheduled offset every
    // stage must be done.
    act(() => {
      jest.advanceTimersByTime(ALL_DONE_AT_MS);
    });
    for (let i = 0; i < STAGE_COUNT; i++) {
      expect(getByTestId(`stage-${i}-icon`).props.accessibilityLabel).toBe(
        'done',
      );
    }

    // CRITICAL: advance far past the schedule — a slow compare can sit
    // here well past 26s. Status MUST stay all-done; no pending
    // wrap-back.
    act(() => {
      jest.advanceTimersByTime(ALL_DONE_AT_MS * 3); // ~78s additional
    });
    for (let i = 0; i < STAGE_COUNT; i++) {
      expect(getByTestId(`stage-${i}-icon`).props.accessibilityLabel).toBe(
        'done',
      );
    }
  });

  it('stages still walk pending → active → done one at a time before the freeze', () => {
    const { getByTestId } = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        testID="lsv-r3"
      />,
    );

    // tick 0: stage 0 active, rest pending
    expect(getByTestId('stage-0-icon').props.accessibilityLabel).toBe('active');
    expect(getByTestId('stage-1-icon').props.accessibilityLabel).toBe('pending');
    expect(getByTestId('stage-4-icon').props.accessibilityLabel).toBe('pending');

    // cursor=1
    act(() => {
      jest.advanceTimersByTime(STAGE_DONE_AT_MS[0]);
    });
    expect(getByTestId('stage-0-icon').props.accessibilityLabel).toBe('done');
    expect(getByTestId('stage-1-icon').props.accessibilityLabel).toBe('active');
    expect(getByTestId('stage-2-icon').props.accessibilityLabel).toBe('pending');

    // cursor=4 (last stage active, prior all done)
    act(() => {
      jest.advanceTimersByTime(STAGE_DONE_AT_MS[3] - STAGE_DONE_AT_MS[0]);
    });
    expect(getByTestId('stage-3-icon').props.accessibilityLabel).toBe('done');
    expect(getByTestId('stage-4-icon').props.accessibilityLabel).toBe('active');

    // cursor=5 (count) → all done. This is the freeze point.
    act(() => {
      jest.advanceTimersByTime(STAGE_DONE_AT_MS[4] - STAGE_DONE_AT_MS[3]);
    });
    for (let i = 0; i < STAGE_COUNT; i++) {
      expect(getByTestId(`stage-${i}-icon`).props.accessibilityLabel).toBe(
        'done',
      );
    }
  });

  it('after a long wait stage-0 is still done (regression pin: NO loop back to active)', () => {
    const { getByTestId } = render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        testID="lsv-r3"
      />,
    );
    // ~130s — five times the full schedule, well past any realistic wall
    // floor. The prior modulo cycle would have wrapped many times by now.
    act(() => {
      jest.advanceTimersByTime(ALL_DONE_AT_MS * 5);
    });
    // The previous behavior: at any wrap point, stage-0 briefly returned
    // to 'active' or 'pending'. Freeze contract: stays done.
    expect(getByTestId('stage-0-icon').props.accessibilityLabel).toBe('done');
  });
});
