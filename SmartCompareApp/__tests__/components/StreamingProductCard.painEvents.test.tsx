/**
 * StreamingProductCard pain-workflow instrumentation — Bundle B B.1 (F3.5).
 *
 * The card emits three pain-workflow signals via an optional `onSignal`
 * callback (the parent threads it to trackEvent -> POST /events):
 *   - spec_expand    : user taps "+N more" to reveal specs past the 3-row preview
 *   - result_abandon : card unmounts before reaching the 'verdict' stage
 *   - screenshot     : expo-screen-capture addScreenshotListener fires while mounted
 *
 * Instrumentation is opt-in: with NO onSignal prop the card is a pure render
 * (the existing StreamingProductCard.test.tsx suite proves that path stays
 * green). These tests cover the instrumented path.
 *
 * Sync-render pattern (CLAUDE.md): plain render() + fireEvent, no act() wrap.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import * as ScreenCapture from 'expo-screen-capture';
import { StreamingProductCard } from '../../src/components/StreamingProductCard';

describe('StreamingProductCard pain-workflow signals', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  // --- spec_expand ---

  it('renders a "+N more" affordance when specs exceed the 3-row preview', () => {
    const onSignal = jest.fn();
    const { getByTestId } = render(
      <StreamingProductCard
        testID="card"
        stage="specs"
        onSignal={onSignal}
        product={{
          name: 'iPhone 15',
          specs: { a: '1', b: '2', c: '3', d: '4', e: '5' },
        }}
      />
    );
    expect(getByTestId('card-spec-expand')).toBeTruthy();
  });

  it('does NOT render the expand affordance when specs fit in 3 rows', () => {
    const onSignal = jest.fn();
    const { queryByTestId } = render(
      <StreamingProductCard
        testID="card"
        stage="specs"
        onSignal={onSignal}
        product={{ name: 'iPhone 15', specs: { a: '1', b: '2' } }}
      />
    );
    expect(queryByTestId('card-spec-expand')).toBeNull();
  });

  it('fires spec_expand once and removes the affordance after the first tap', () => {
    const onSignal = jest.fn();
    const { getByTestId, queryByTestId } = render(
      <StreamingProductCard
        testID="card"
        stage="specs"
        onSignal={onSignal}
        product={{
          name: 'iPhone 15',
          specs: { a: '1', b: '2', c: '3', d: '4' },
        }}
      />
    );
    fireEvent.press(getByTestId('card-spec-expand'));
    // The affordance disappears once expanded — this IS the once-guarantee
    // (no second tap is possible), and the signal fired exactly once.
    expect(queryByTestId('card-spec-expand')).toBeNull();
    const expandCalls = onSignal.mock.calls.filter((c) => c[0] === 'spec_expand');
    expect(expandCalls).toHaveLength(1);
  });

  it('expanding reveals the remaining specs', () => {
    const onSignal = jest.fn();
    const { getByTestId, queryByText } = render(
      <StreamingProductCard
        testID="card"
        stage="specs"
        onSignal={onSignal}
        product={{
          name: 'iPhone 15',
          specs: { a: '1', b: '2', c: '3', dee: 'visible-after-expand' },
        }}
      />
    );
    // 4th spec hidden before expand
    expect(queryByText('visible-after-expand')).toBeNull();
    fireEvent.press(getByTestId('card-spec-expand'));
    expect(queryByText('visible-after-expand')).toBeTruthy();
  });

  it('does NOT render the expand affordance without onSignal (pure-render path)', () => {
    const { queryByTestId } = render(
      <StreamingProductCard
        testID="card"
        stage="specs"
        product={{
          name: 'iPhone 15',
          specs: { a: '1', b: '2', c: '3', d: '4', e: '5' },
        }}
      />
    );
    expect(queryByTestId('card-spec-expand')).toBeNull();
  });

  // --- result_abandon ---

  it('fires result_abandon when unmounted before the verdict stage', () => {
    const onSignal = jest.fn();
    const { unmount } = render(
      <StreamingProductCard
        testID="card"
        stage="prices"
        onSignal={onSignal}
        product={{ name: 'iPhone 15' }}
      />
    );
    unmount();
    expect(onSignal).toHaveBeenCalledWith('result_abandon');
  });

  it('does NOT fire result_abandon when unmounted at the verdict stage', () => {
    const onSignal = jest.fn();
    const { unmount } = render(
      <StreamingProductCard
        testID="card"
        stage="verdict"
        onSignal={onSignal}
        product={{ name: 'iPhone 15' }}
      />
    );
    unmount();
    const abandonCalls = onSignal.mock.calls.filter((c) => c[0] === 'result_abandon');
    expect(abandonCalls).toHaveLength(0);
  });

  it('does NOT fire result_abandon when no onSignal is provided', () => {
    // Pure-render path must not crash on unmount (no effect registered).
    const { unmount } = render(
      <StreamingProductCard testID="card" stage="prices" product={{ name: 'X' }} />
    );
    expect(() => unmount()).not.toThrow();
  });

  // --- screenshot ---

  it('fires screenshot when the screen-capture listener triggers', () => {
    let captured: (() => void) | null = null;
    jest
      .spyOn(ScreenCapture, 'addScreenshotListener')
      .mockImplementation((listener: () => void) => {
        captured = listener;
        return { remove: () => {} } as any;
      });

    const onSignal = jest.fn();
    render(
      <StreamingProductCard
        testID="card"
        stage="reviews"
        onSignal={onSignal}
        product={{ name: 'iPhone 15' }}
      />
    );
    // Simulate the OS screenshot event.
    expect(captured).not.toBeNull();
    captured!();
    expect(onSignal).toHaveBeenCalledWith('screenshot');
  });

  it('removes the screenshot listener on unmount', () => {
    const remove = jest.fn();
    jest
      .spyOn(ScreenCapture, 'addScreenshotListener')
      .mockReturnValue({ remove } as any);

    const onSignal = jest.fn();
    const { unmount } = render(
      <StreamingProductCard
        testID="card"
        stage="reviews"
        onSignal={onSignal}
        product={{ name: 'iPhone 15' }}
      />
    );
    unmount();
    expect(remove).toHaveBeenCalled();
  });

  it('does NOT register a screenshot listener without onSignal', () => {
    const spy = jest.spyOn(ScreenCapture, 'addScreenshotListener');
    render(
      <StreamingProductCard testID="card" stage="reviews" product={{ name: 'X' }} />
    );
    expect(spy).not.toHaveBeenCalled();
  });
});
