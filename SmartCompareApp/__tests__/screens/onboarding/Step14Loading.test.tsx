/**
 * Step14Loading tests — Bundle E S2.W3 REWRITE contract.
 *
 * The Phase 2 LoadingRings + stage-copy ticker + ProgressBar layout
 * was replaced with the ConcentricVariant composition delegated via
 * LoadingScreenVariants. Step14 is now a thin wrapper that feeds the
 * 4 region/priorities/peers/calibrate stages + 4 factoid tips + cohort
 * footer into the shared loader surface.
 *
 * The 3.2s minimum-display floor moves to LoadingScreenVariants
 * (mode="onboarding" + minDisplayMs); Step14 inherits it via prop
 * pass-through. The minDurationMs Step14 prop is honored as the
 * floor override.
 *
 * Contract pinned:
 *   - testID="s14-loading-root" forwarded to LoadingScreenVariants
 *   - LoadingRings hero rendered via testID="loading-rings" inside the
 *     ConcentricVariant
 *   - StageChecklist 4-stage card rendered via testID="loading-stage-card"
 *     containing stage-{region,priorities,peers,calibrate}-icon
 *   - LoadingTipsCarousel rendered via testID="loading-tips" — 4 tips
 *   - cohort footer via testID="loading-cohort-footer" shows the count
 *   - onComplete fires exactly once after minDurationMs floor
 *   - Floor honored even if backend resolves "instantly"
 */

import React from 'react';
import { render, act } from '@testing-library/react-native';

const impactAsyncMock = jest.fn().mockResolvedValue(undefined);
jest.mock('expo-haptics', () => ({
  impactAsync: (style: string) => impactAsyncMock(style),
  ImpactFeedbackStyle: { Light: 'light', Medium: 'medium', Heavy: 'heavy' },
  __esModule: true,
}));

import { Step14Loading } from '../../../src/screens/onboarding/Step14Loading';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      const dv = opts?.defaultValue as string | undefined;
      if (dv && opts && (opts.governorate || opts.count != null)) {
        return dv
          .replace(/{{governorate}}/g, String(opts.governorate ?? ''))
          .replace(/{{count}}/g, String(opts.count ?? ''));
      }
      return key;
    },
  }),
}));

const MIN_FLOOR_MS = 3200;

beforeEach(() => {
  impactAsyncMock.mockClear();
  jest.useFakeTimers();
});

afterEach(() => {
  act(() => {
    jest.runOnlyPendingTimers();
  });
  jest.useRealTimers();
});

describe('Step14Loading (S2.W3 REWRITE)', () => {
  it('renders the loading root + inner ConcentricVariant scaffolding', () => {
    const { getByTestId } = render(
      <Step14Loading onComplete={jest.fn()} cohortPeerCount={47} />,
    );
    expect(getByTestId('s14-loading-root')).toBeTruthy();
    expect(getByTestId('loading-concentric')).toBeTruthy();
    expect(getByTestId('loading-rings')).toBeTruthy();
  });

  // Step14 onboarding mode intentionally omits the cohort footer line.
  // The counter chip + "cohort peers refining your match" caption per
  // design doc § 3.2 already convey the cohort beat — duplicating
  // "N cohort peers helped train this" right below would be redundant.
  // The cohortFooter prop on LoadingScreenVariants stays available for
  // other callers (comparison-mode results loading).
  it('omits the legacy cohort footer line (cohort beat carried by counter + caption)', () => {
    const { queryByTestId } = render(
      <Step14Loading onComplete={jest.fn()} cohortPeerCount={123} />,
    );
    expect(queryByTestId('loading-cohort-footer')).toBeNull();
  });

  it('renders the StageChecklist card with the 4 expected stage rows', () => {
    const { getByTestId } = render(
      <Step14Loading onComplete={jest.fn()} cohortPeerCount={47} />,
    );
    expect(getByTestId('loading-stage-card')).toBeTruthy();
    expect(getByTestId('stage-region-icon')).toBeTruthy();
    expect(getByTestId('stage-priorities-icon')).toBeTruthy();
    expect(getByTestId('stage-peers-icon')).toBeTruthy();
    expect(getByTestId('stage-calibrate-icon')).toBeTruthy();
  });

  it('renders the LoadingTipsCarousel host', () => {
    const { getByTestId } = render(
      <Step14Loading onComplete={jest.fn()} cohortPeerCount={47} />,
    );
    expect(getByTestId('loading-tips')).toBeTruthy();
  });

  // Y.B Bundle D rhythm preservation (design doc § 3.2 LoadingRings spec
  // + dispatcher Step14 aesthetic note 2026-05-29): counter chip ticks
  // 0 → cohortPeerCount over 2.4s with the i18n caption
  // "cohort peers refining your match" rendered below. Step14 wires
  // counterTarget to the supplied cohortPeerCount + falls back to
  // 2,074 when cohortPeerCount is missing/zero so the brand beat lands
  // even on cold-start.
  it('renders the counter chip with the cohort peer count as the ticking target (Y.B)', () => {
    const { getByTestId } = render(
      <Step14Loading onComplete={jest.fn()} cohortPeerCount={47} />,
    );
    expect(getByTestId('loading-counter-chip')).toBeTruthy();
    expect(getByTestId('loading-counter')).toBeTruthy();
    // CounterTicker commits the final integer on mount (safety floor)
    // for jest envs that no-op reanimated's useAnimatedReaction. The
    // supplied cohortPeerCount becomes the counter target verbatim.
    expect(getByTestId('loading-counter').props.children).toBe('47');
  });

  it('falls back to 2,074 counter target when cohortPeerCount is zero', () => {
    const { getByTestId } = render(
      <Step14Loading onComplete={jest.fn()} cohortPeerCount={0} />,
    );
    // COUNTER_FALLBACK_TARGET kicks in so the brand beat still lands
    // even when the cohort match comes back empty (cold-start).
    expect(getByTestId('loading-counter').props.children).toBe('2074');
  });

  it('renders the caption with the loading.cohort.caption i18n key (Y.B)', () => {
    const { getByTestId } = render(
      <Step14Loading onComplete={jest.fn()} cohortPeerCount={47} />,
    );
    expect(getByTestId('loading-caption')).toBeTruthy();
    // Mock t() pass-through for keys without interpolation tokens
    // returns the literal key string — design doc § 3.2 caption key.
    const text = getByTestId('loading-caption').props.children as string;
    expect(text).toBe('loading.cohort.caption');
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

  it('respects an explicit minDurationMs override (override flows to LoadingScreenVariants)', () => {
    const onComplete = jest.fn();
    render(
      <Step14Loading
        onComplete={onComplete}
        cohortPeerCount={47}
        minDurationMs={1000}
      />,
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

  it('fires onComplete exactly once even if timers continue past the floor', () => {
    const onComplete = jest.fn();
    render(<Step14Loading onComplete={onComplete} cohortPeerCount={47} />);
    act(() => {
      jest.advanceTimersByTime(MIN_FLOOR_MS + 5000);
    });
    expect(onComplete).toHaveBeenCalledTimes(1);
  });
});
