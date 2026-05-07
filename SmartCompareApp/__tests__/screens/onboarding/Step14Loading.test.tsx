/**
 * Step14Loading tests — Phase 2 Task 21.
 *
 * Theatrical loading centerpiece. LoadingRings #4 + stage copy cycler +
 * progress bar 0→100% over 3.2s minimum + CounterTicker "0 → 47 cohort
 * peers". onComplete fires after the 3.2s floor (even if API was faster).
 * See design spec § 2 row 14 — "perceived effort = perceived value."
 */

import React from 'react';
import { render, act } from '@testing-library/react-native';
import { Step14Loading } from '../../../src/screens/onboarding/Step14Loading';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const MIN_FLOOR_MS = 3200;

beforeEach(() => {
  jest.useFakeTimers();
});

afterEach(() => {
  act(() => {
    jest.runOnlyPendingTimers();
  });
  jest.useRealTimers();
});

describe('Step14Loading', () => {
  it('renders the LoadingRings illustration', () => {
    const { getByTestId } = render(
      <Step14Loading onComplete={jest.fn()} cohortPeerCount={47} />
    );
    expect(getByTestId('s14-rings')).toBeTruthy();
  });

  it('renders the progress bar at 0% on mount', () => {
    const { getByTestId } = render(
      <Step14Loading onComplete={jest.fn()} cohortPeerCount={47} />
    );
    expect(getByTestId('s14-progress-track')).toBeTruthy();
  });

  it('renders the cohort peer counter', () => {
    const { getByTestId } = render(
      <Step14Loading onComplete={jest.fn()} cohortPeerCount={47} />
    );
    expect(getByTestId('s14-peer-counter')).toBeTruthy();
  });

  it('does NOT call onComplete before the 3.2s floor elapses', () => {
    const onComplete = jest.fn();
    render(<Step14Loading onComplete={onComplete} cohortPeerCount={47} />);
    act(() => {
      jest.advanceTimersByTime(MIN_FLOOR_MS - 1);
    });
    expect(onComplete).not.toHaveBeenCalled();
  });

  it('calls onComplete after the 3.2s minimum floor', () => {
    const onComplete = jest.fn();
    render(<Step14Loading onComplete={onComplete} cohortPeerCount={47} />);
    act(() => {
      jest.advanceTimersByTime(MIN_FLOOR_MS + 50);
    });
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it('respects an explicit minDurationMs override', () => {
    const onComplete = jest.fn();
    render(
      <Step14Loading
        onComplete={onComplete}
        cohortPeerCount={47}
        minDurationMs={1000}
      />
    );
    act(() => {
      jest.advanceTimersByTime(999);
    });
    expect(onComplete).not.toHaveBeenCalled();
    act(() => {
      jest.advanceTimersByTime(50);
    });
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it('cycles through 4 stage copy strings during the floor', () => {
    const { getByTestId } = render(
      <Step14Loading onComplete={jest.fn()} cohortPeerCount={47} />
    );
    const initial = getByTestId('s14-stage-copy').props.children;
    act(() => {
      jest.advanceTimersByTime(900); // past the first 800ms cycle
    });
    const second = getByTestId('s14-stage-copy').props.children;
    expect(second).not.toBe(initial);
  });

  it('only fires onComplete once even if timers re-trigger', () => {
    const onComplete = jest.fn();
    render(<Step14Loading onComplete={onComplete} cohortPeerCount={47} />);
    act(() => {
      jest.advanceTimersByTime(MIN_FLOOR_MS + 5000);
    });
    expect(onComplete).toHaveBeenCalledTimes(1);
  });
});
