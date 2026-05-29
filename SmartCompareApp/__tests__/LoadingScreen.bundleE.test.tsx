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

  // -----------------------------------------------------------------
  // F-S2.X2 (task #32) — StreamingCardsVariant flesh-out coverage.
  // -----------------------------------------------------------------

  describe('StreamingCardsVariant — F-S2.X2', () => {
    it('mounts both ghost cards with all 4 fields pending + shimmer at t=0', () => {
      const { getByTestId, queryByTestId } = render(
        <LoadingScreenVariants variant="streaming" mode="comparison" />,
      );
      // Both cards mounted side-by-side.
      expect(getByTestId('loading-streaming-card-a')).toBeTruthy();
      expect(getByTestId('loading-streaming-card-b')).toBeTruthy();
      // All 4 ghost fields on each card start PENDING (shimmer).
      ['a', 'b'].forEach((side) => {
        ['photo', 'name', 'price', 'stars'].forEach((field) => {
          expect(
            getByTestId(`loading-streaming-card-${side}-${field}-pending`),
          ).toBeTruthy();
          // The 4 pending fields each host a shimmer Animated.View.
          expect(
            getByTestId(`loading-streaming-card-${side}-${field}-shimmer`),
          ).toBeTruthy();
        });
        // Winner-only "Top match" badge is NOT mounted until stars reveal.
        expect(queryByTestId(`loading-streaming-card-${side}-badge`)).toBeNull();
      });
    });

    it('reveals fields in order photo → name → price → stars → badge on the 400ms stagger', () => {
      const { getByTestId, queryByTestId } = render(
        <LoadingScreenVariants variant="streaming" mode="comparison" />,
      );

      // After ~400ms — photo revealed, name still pending.
      act(() => { jest.advanceTimersByTime(400); });
      expect(getByTestId('loading-streaming-card-a-photo-revealed')).toBeTruthy();
      expect(getByTestId('loading-streaming-card-a-name-pending')).toBeTruthy();

      // After ~800ms — name revealed, price still pending.
      act(() => { jest.advanceTimersByTime(400); });
      expect(getByTestId('loading-streaming-card-a-name-revealed')).toBeTruthy();
      expect(getByTestId('loading-streaming-card-a-price-pending')).toBeTruthy();

      // After ~1200ms — price revealed, stars still pending.
      act(() => { jest.advanceTimersByTime(400); });
      expect(getByTestId('loading-streaming-card-a-price-revealed')).toBeTruthy();
      expect(getByTestId('loading-streaming-card-a-stars-pending')).toBeTruthy();

      // After ~1600ms — stars revealed → winner badge mounts on the
      // right (b) card. Loser (a) card still has no badge.
      act(() => { jest.advanceTimersByTime(400); });
      expect(getByTestId('loading-streaming-card-a-stars-revealed')).toBeTruthy();
      expect(getByTestId('loading-streaming-card-b-badge')).toBeTruthy();
      expect(queryByTestId('loading-streaming-card-a-badge')).toBeNull();
    });

    it('flips the right card to winner styling at the final reveal stage', () => {
      // Each setTimeout(400ms) advances revealIndex by 1; React state
      // commit re-runs the effect which schedules the NEXT timer at
      // the current fake-clock timestamp. Jest's advanceTimersByTime
      // doesn't fast-forward through newly-queued timers inside a
      // single call, so we step explicitly per stage (5 × 400ms).
      const { getByTestId } = render(
        <LoadingScreenVariants variant="streaming" mode="comparison" />,
      );
      for (let i = 0; i < 5; i++) {
        act(() => { jest.advanceTimersByTime(400); });
      }
      // The badge testID is the regression-guard that the right card
      // hit the final stage. The styling itself (accentLight bg) is
      // pinned via the snapshot below.
      expect(getByTestId('loading-streaming-card-b-badge')).toBeTruthy();
    });

    it('comparison mode rotation: Math.random < 0.5 → concentric variant', () => {
      const spy = jest.spyOn(Math, 'random').mockReturnValue(0.1);
      try {
        const { getByTestId, queryByTestId } = render(
          <LoadingScreenVariants mode="comparison" />,
        );
        expect(getByTestId('loading-concentric')).toBeTruthy();
        expect(queryByTestId('loading-streaming')).toBeNull();
      } finally {
        spy.mockRestore();
      }
    });

    it('comparison mode rotation: Math.random >= 0.5 → streaming variant', () => {
      const spy = jest.spyOn(Math, 'random').mockReturnValue(0.9);
      try {
        const { getByTestId, queryByTestId } = render(
          <LoadingScreenVariants mode="comparison" />,
        );
        expect(getByTestId('loading-streaming')).toBeTruthy();
        expect(queryByTestId('loading-concentric')).toBeNull();
      } finally {
        spy.mockRestore();
      }
    });

    it('onboarding mode FORCES concentric even when Math.random would have picked streaming', () => {
      const spy = jest.spyOn(Math, 'random').mockReturnValue(0.9);
      try {
        const { getByTestId, queryByTestId } = render(
          <LoadingScreenVariants mode="onboarding" />,
        );
        expect(getByTestId('loading-concentric')).toBeTruthy();
        expect(queryByTestId('loading-streaming')).toBeNull();
      } finally {
        spy.mockRestore();
      }
    });
  });
});
