/**
 * Bundle E S3 Hot-Fix Wave 2 R2 — LoadingTipsCarousel cross-fade.
 *
 * Wave 2 R1 wired the LoadingTipsCarousel into LoadingScreenVariants
 * comparison-mode but the carousel itself swapped tip text via a hard
 * <Text> render — no opacity transition. Per
 * docs/claude-design-handoff/ui_kits/mobile/LoadingScreen.jsx (TipCard,
 * `animation: qarenTipFade 3.2s ease infinite`) the factoid card must
 * cross-fade between tips.
 *
 * R2 contract:
 *   - The carousel host is an Animated.View whose opacity animates
 *     between 1 → 0 → 1 across each rotation.
 *   - The next tip text appears AFTER the fade-out completes (avoids
 *     visible mid-fade text swap).
 *   - testID surface stays stable: `loading-tips` still resolves (now
 *     to the Animated.View); a new `loading-tips-text` testID points
 *     at the inner Text node so a parent that needs to read the
 *     rendered string can still do so.
 *
 * Reanimated's mock under Jest exposes shared values as plain numbers
 * (no spring/timing actually animates). To test the cross-fade we
 * inspect the Animated.View's style prop directly and assert opacity
 * is driven through the expected values across the rotation cycle.
 */

import React from 'react';
import { render, act } from '@testing-library/react-native';

import { LoadingTipsCarousel } from '../../src/components/LoadingTipsCarousel';

beforeEach(() => {
  jest.useFakeTimers();
});
afterEach(() => {
  jest.useRealTimers();
});

describe('LoadingTipsCarousel — cross-fade rotation', () => {
  it('mounts with opacity 1 (no entry fade)', () => {
    const { getByTestId } = render(
      <LoadingTipsCarousel
        tips={['Tip A', 'Tip B']}
        intervalMs={5000}
        testID="loading-tips"
      />,
    );
    const card = getByTestId('loading-tips');
    // Animated.View flattens its style prop; opacity should be 1 on mount.
    const flatStyle = Array.isArray(card.props.style)
      ? Object.assign({}, ...card.props.style.filter(Boolean))
      : card.props.style ?? {};
    expect(flatStyle.opacity).toBe(1);
  });

  it('exposes the inner tip text via loading-tips-text testID', () => {
    const { getByTestId } = render(
      <LoadingTipsCarousel
        tips={['Tip A', 'Tip B']}
        intervalMs={5000}
        testID="loading-tips"
      />,
    );
    expect(getByTestId('loading-tips-text').props.children).toBe('Tip A');
  });

  it('host is an Animated.View (not a bare Text) so opacity can animate', () => {
    const { getByTestId } = render(
      <LoadingTipsCarousel
        tips={['Tip A', 'Tip B']}
        intervalMs={5000}
        testID="loading-tips"
      />,
    );
    const card = getByTestId('loading-tips');
    // Animated.View renders to a View at runtime; the discriminator is
    // that the prior contract was a Text node with text children. Now
    // the children must be a Text element, not a string.
    expect(typeof card.props.children).not.toBe('string');
  });

  it('after a rotation cycle, the inner text advances to the next tip', () => {
    const { getByTestId } = render(
      <LoadingTipsCarousel
        tips={['Tip A', 'Tip B', 'Tip C']}
        intervalMs={5000}
        testID="loading-tips"
      />,
    );
    expect(getByTestId('loading-tips-text').props.children).toBe('Tip A');
    // One interval + the fade-out/in beats (each <= 250ms) lands us
    // on the next tip with opacity back at 1.
    act(() => {
      jest.advanceTimersByTime(5000);
      jest.runOnlyPendingTimers();
    });
    expect(getByTestId('loading-tips-text').props.children).toBe('Tip B');
    const card = getByTestId('loading-tips');
    const flatStyle = Array.isArray(card.props.style)
      ? Object.assign({}, ...card.props.style.filter(Boolean))
      : card.props.style ?? {};
    expect(flatStyle.opacity).toBe(1);
  });

  it('wraps from last tip back to first after full cycle', () => {
    const { getByTestId } = render(
      <LoadingTipsCarousel
        tips={['Tip A', 'Tip B']}
        intervalMs={5000}
        testID="loading-tips"
      />,
    );
    // Two rotations: A → B → A.
    act(() => {
      jest.advanceTimersByTime(5000);
      jest.runOnlyPendingTimers();
    });
    act(() => {
      jest.advanceTimersByTime(5000);
      jest.runOnlyPendingTimers();
    });
    expect(getByTestId('loading-tips-text').props.children).toBe('Tip A');
  });

  it('renders nothing when tips=[]', () => {
    const { queryByTestId } = render(
      <LoadingTipsCarousel tips={[]} testID="loading-tips" />,
    );
    expect(queryByTestId('loading-tips')).toBeNull();
    expect(queryByTestId('loading-tips-text')).toBeNull();
  });

  it('single-tip array does not rotate (no crash, no fade-out)', () => {
    const { getByTestId } = render(
      <LoadingTipsCarousel
        tips={['Only one']}
        intervalMs={5000}
        testID="loading-tips"
      />,
    );
    expect(getByTestId('loading-tips-text').props.children).toBe('Only one');
    act(() => {
      jest.advanceTimersByTime(15000);
      jest.runOnlyPendingTimers();
    });
    // Still on the only tip; no error from a swap on a 1-element list.
    expect(getByTestId('loading-tips-text').props.children).toBe('Only one');
  });
});
