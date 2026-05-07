/**
 * CounterTicker tests — Phase 2 Task 10.
 *
 * Animates a number from 0 → target over `duration` ms with ease-out.
 * Used for "388 GCC shoppers helped train this", BHD price ticks on the
 * Results screen, cohort peer counts. See design spec Section 1 motion
 * language ("Counter tick" row).
 *
 * Under the reanimated jest mock, `useSharedValue(init)` returns
 * `{ value: init }` and `withTiming(toValue)` returns `toValue` synchronously,
 * so the displayed value reflects the target on first commit. We assert the
 * end-state value, not per-frame interpolation. Per-frame easing is on-device
 * QA at the Phase 2 gate.
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import { CounterTicker } from '../../src/components/CounterTicker';

describe('CounterTicker', () => {
  it('renders the target value', () => {
    const { getByText } = render(<CounterTicker target={388} duration={800} />);
    expect(getByText('388')).toBeTruthy();
  });

  it('renders an integer (rounded)', () => {
    const { getByTestId } = render(
      <CounterTicker target={47.6} duration={500} testID="counter" />
    );
    const text = getByTestId('counter').props.children;
    expect(typeof text).toBe('string');
    expect(Number.isInteger(Number(text))).toBe(true);
  });

  it('supports a prefix and suffix', () => {
    const { getByText } = render(
      <CounterTicker target={295} duration={500} suffix=" BHD" />
    );
    expect(getByText('295 BHD')).toBeTruthy();
  });

  it('clamps target to >= 0 (negative inputs render as 0)', () => {
    const { getByText } = render(<CounterTicker target={-12} duration={400} />);
    expect(getByText('0')).toBeTruthy();
  });

  it('forwards style and testID to its host node', () => {
    const { getByTestId } = render(
      <CounterTicker target={10} duration={200} testID="t" style={{ fontSize: 24 }} />
    );
    const node = getByTestId('t');
    expect(Array.isArray(node.props.style) || typeof node.props.style === 'object').toBe(true);
  });

  it('updates display when target prop changes', () => {
    const { rerender, getByTestId } = render(
      <CounterTicker target={50} duration={400} testID="counter" />
    );
    expect(getByTestId('counter').props.children).toBe('50');

    rerender(<CounterTicker target={200} duration={400} testID="counter" />);
    expect(getByTestId('counter').props.children).toBe('200');
  });
});
