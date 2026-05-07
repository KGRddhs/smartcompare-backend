/**
 * LoadingTipsCarousel tests — Phase 3 Task 29.
 *
 * Rotates a list of tips every `intervalMs` (default 4000). Used on the
 * Results loading screen after the 8s wait threshold per design § 3.
 * Pure presentational — the parent decides when to mount.
 */

import React from 'react';
import { render, act } from '@testing-library/react-native';
import { LoadingTipsCarousel } from '../../src/components/LoadingTipsCarousel';

const TIPS = [
  'Tip one — first message',
  'Tip two — second message',
  'Tip three — third message',
];

beforeEach(() => {
  jest.useFakeTimers();
});

afterEach(() => {
  act(() => {
    jest.runOnlyPendingTimers();
  });
  jest.useRealTimers();
});

describe('LoadingTipsCarousel', () => {
  it('renders the first tip on mount', () => {
    const { getByTestId } = render(
      <LoadingTipsCarousel tips={TIPS} testID="tips" />
    );
    expect(getByTestId('tips').props.children).toBe(TIPS[0]);
  });

  it('rotates to the next tip after the interval', () => {
    const { getByTestId } = render(
      <LoadingTipsCarousel tips={TIPS} intervalMs={4000} testID="tips" />
    );
    expect(getByTestId('tips').props.children).toBe(TIPS[0]);
    act(() => {
      jest.advanceTimersByTime(4000);
    });
    expect(getByTestId('tips').props.children).toBe(TIPS[1]);
  });

  it('wraps around to the first tip after the last', () => {
    const { getByTestId } = render(
      <LoadingTipsCarousel tips={TIPS} intervalMs={4000} testID="tips" />
    );
    act(() => {
      jest.advanceTimersByTime(4000 * 3);
    });
    expect(getByTestId('tips').props.children).toBe(TIPS[0]);
  });

  it('uses 4000ms as default interval', () => {
    const { getByTestId } = render(
      <LoadingTipsCarousel tips={TIPS} testID="tips" />
    );
    act(() => {
      jest.advanceTimersByTime(3999);
    });
    expect(getByTestId('tips').props.children).toBe(TIPS[0]);
    act(() => {
      jest.advanceTimersByTime(2);
    });
    expect(getByTestId('tips').props.children).toBe(TIPS[1]);
  });

  it('renders nothing when given an empty tips array', () => {
    const { queryByTestId } = render(
      <LoadingTipsCarousel tips={[]} testID="tips" />
    );
    expect(queryByTestId('tips')).toBeNull();
  });

  it('renders the single tip without rotation when given exactly one', () => {
    const { getByTestId } = render(
      <LoadingTipsCarousel tips={['only one']} intervalMs={1000} testID="tips" />
    );
    expect(getByTestId('tips').props.children).toBe('only one');
    act(() => {
      jest.advanceTimersByTime(5000);
    });
    expect(getByTestId('tips').props.children).toBe('only one');
  });

  it('cleans up its interval on unmount', () => {
    const { unmount } = render(
      <LoadingTipsCarousel tips={TIPS} intervalMs={4000} testID="tips" />
    );
    unmount();
    // Advancing timers after unmount must not throw
    expect(() => {
      act(() => {
        jest.advanceTimersByTime(8000);
      });
    }).not.toThrow();
  });
});
