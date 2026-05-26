/**
 * LoadingScreen Bundle E — variants + 3.2s min-display floor.
 *
 * Frontend lands LoadingScreenVariants.tsx during S2 (plan § S2.x). The
 * file exports two variants:
 *   - ConcentricVariant (uses LoadingRings hero + StageChecklist + TipCard)
 *   - StreamingCardsVariant (two product-shape ghost cards, field-by-field
 *     reveal w/ shimmer overlay)
 *
 * Mode "onboarding" ALWAYS uses ConcentricVariant (Step14 theatrical moment).
 * Mode "comparison" picks one of the two randomly on mount (useMemo).
 *
 * 3.2s min display floor: onboarding mode MUST hold the loader on screen
 * for at least 3,200ms before calling `onDone`, even if the underlying
 * promise resolved instantly. (Bundle D 1.F.3 + plan S2.x).
 */
import React from 'react';
import { render, act } from '@testing-library/react-native';
import { LoadingScreenVariants } from '../src/screens/LoadingScreenVariants';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string, opts?: any) => opts?.defaultValue ?? k }),
}));
jest.mock('../src/hooks/useLanguage', () => ({
  useLanguage: () => ({ isRTL: false, language: 'en' }),
}));

describe('LoadingScreenVariants — Bundle E', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders ConcentricVariant without warnings', () => {
    expect(() =>
      render(<LoadingScreenVariants variant="concentric" mode="comparison" />),
    ).not.toThrow();
  });

  it('renders StreamingCardsVariant without warnings', () => {
    expect(() =>
      render(<LoadingScreenVariants variant="streaming" mode="comparison" />),
    ).not.toThrow();
  });

  it('onboarding mode FORCES ConcentricVariant regardless of variant prop', () => {
    // Even if `variant="streaming"` is passed, mode="onboarding" overrides
    // to concentric (Step14 theatrical moment).
    const { getByTestId, queryByTestId } = render(
      <LoadingScreenVariants variant="streaming" mode="onboarding" />,
    );
    expect(getByTestId('loading-concentric')).toBeTruthy();
    expect(queryByTestId('loading-streaming')).toBeNull();
  });

  it('onboarding mode enforces 3.2s min display floor before firing onDone', () => {
    const onDone = jest.fn();
    render(
      <LoadingScreenVariants
        variant="concentric"
        mode="onboarding"
        // Simulate an instant-resolve promise — done IMMEDIATELY ready.
        ready={true}
        onDone={onDone}
      />,
    );

    // Advance time just under 3.2s — onDone must NOT have fired yet.
    act(() => { jest.advanceTimersByTime(3199); });
    expect(onDone).not.toHaveBeenCalled();

    // Advance past the floor — onDone fires.
    act(() => { jest.advanceTimersByTime(2); });
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('comparison mode does NOT enforce the 3.2s floor (fires as soon as ready)', () => {
    const onDone = jest.fn();
    render(
      <LoadingScreenVariants
        variant="concentric"
        mode="comparison"
        ready={true}
        onDone={onDone}
      />,
    );
    // Comparison mode is not the theatrical "advisor ready" moment — it
    // releases as soon as the backend finishes. Allow a tiny tick for the
    // useEffect to flush.
    act(() => { jest.advanceTimersByTime(50); });
    expect(onDone).toHaveBeenCalled();
  });

  it('comparison mode picks ONE variant via useMemo (stable across re-renders)', () => {
    // The variant rotation invariant: pick at mount, hold across re-renders
    // until unmount. Asserted by testID stability across re-renders.
    const { getByTestId, queryByTestId, rerender } = render(
      <LoadingScreenVariants mode="comparison" />,
    );
    const pickedConcentric = !!queryByTestId('loading-concentric');
    const pickedStreaming = !!queryByTestId('loading-streaming');
    // Exactly one must be picked.
    expect(pickedConcentric !== pickedStreaming).toBe(true);

    // Re-render with the same props — useMemo holds, same testID stays.
    rerender(<LoadingScreenVariants mode="comparison" />);
    if (pickedConcentric) expect(getByTestId('loading-concentric')).toBeTruthy();
    else expect(getByTestId('loading-streaming')).toBeTruthy();
  });
});
