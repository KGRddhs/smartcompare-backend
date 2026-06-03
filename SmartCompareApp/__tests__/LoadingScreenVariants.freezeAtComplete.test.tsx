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
 *   - cursor advances every STAGE_CYCLE_MS
 *   - at cursor=count, all stages render `done` (full emerald)
 *   - on subsequent ticks past cursor=count, status STAYS done (no wrap)
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
const STAGE_CYCLE_MS = 900;

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

    // Walk through all 5 stages. After STAGE_COUNT ticks every stage
    // must be done.
    act(() => {
      jest.advanceTimersByTime(STAGE_CYCLE_MS * STAGE_COUNT);
    });
    for (let i = 0; i < STAGE_COUNT; i++) {
      expect(getByTestId(`stage-${i}-icon`).props.accessibilityLabel).toBe(
        'done',
      );
    }

    // CRITICAL: advance many more ticks — covers the wall-floor budget
    // of 14-25s plus a buffer. Status MUST stay all-done; no pending
    // wrap-back.
    act(() => {
      jest.advanceTimersByTime(STAGE_CYCLE_MS * 20); // ~18s additional
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

    // tick 1 → cursor=1
    act(() => {
      jest.advanceTimersByTime(STAGE_CYCLE_MS);
    });
    expect(getByTestId('stage-0-icon').props.accessibilityLabel).toBe('done');
    expect(getByTestId('stage-1-icon').props.accessibilityLabel).toBe('active');
    expect(getByTestId('stage-2-icon').props.accessibilityLabel).toBe('pending');

    // tick 4 → cursor=4 (last stage active, prior all done)
    act(() => {
      jest.advanceTimersByTime(STAGE_CYCLE_MS * 3);
    });
    expect(getByTestId('stage-3-icon').props.accessibilityLabel).toBe('done');
    expect(getByTestId('stage-4-icon').props.accessibilityLabel).toBe('active');

    // tick 5 → cursor=5 (count) → all done. This is the freeze point.
    act(() => {
      jest.advanceTimersByTime(STAGE_CYCLE_MS);
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
    // 30 stage cycles (~27s) — well past the realistic 14-25s wall floor.
    // The prior modulo cycle would have wrapped 3-4 times by now.
    act(() => {
      jest.advanceTimersByTime(STAGE_CYCLE_MS * 30);
    });
    // The previous behavior: at any wrap point, stage-0 briefly returned
    // to 'active' or 'pending'. Freeze contract: stays done.
    expect(getByTestId('stage-0-icon').props.accessibilityLabel).toBe('done');
  });
});
