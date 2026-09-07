/**
 * A16 — CounterTicker's UI→JS commit guard.
 *
 * The ticker animates a shared value on the UI thread and mirrors it into
 * React state through `useAnimatedReaction` + `runOnJS`. The reaction body
 * runs once per FRAME (~60/s; ~72 frames for the 1.2s quiz ticker), so an
 * unconditional `runOnJS(setDisplay)(Math.round(current))` pays a boundary
 * crossing and a setState for every frame even though only a change in the
 * ROUNDED value can change the single Text node it renders. The guard commits
 * one crossing per distinct integer instead.
 *
 * Why this file exists separately from CounterTicker.test.tsx: the shared
 * reanimated mock (`__mocks__/react-native-reanimated.ts:48`) stubs
 * `useAnimatedReaction` as a bare no-op, so the reaction NEVER fires in jest —
 * the six assertions in the sibling suite pass entirely off the synchronous
 * `setDisplay(clampedTarget)` floor in the effect and are green with or
 * without this guard. To make the on-device path observable we extend the
 * shared mock two ways, and only two: capture the reaction body so a test can
 * step it frame by frame, and record each `runOnJS`-wrapped call so the
 * crossings can be counted. Everything else forwards to the shared mock.
 *
 * These pin the guard, not the mock: with the `previous` check stripped from
 * CounterTicker, `commits every frame regardless of the rounded value` is what
 * happens, and the first two tests below fail (4 crossings instead of 2).
 */

import React from 'react';
import { render, act } from '@testing-library/react-native';

type ReactionBody = (current: number, previous: number | null) => void;

const mockReactionBodies: ReactionBody[] = [];
const mockCrossings: number[] = [];

jest.mock('react-native-reanimated', () => {
  const real = jest.requireActual('react-native-reanimated');
  return {
    __esModule: true,
    ...real,
    default: real.default ?? real,
    useAnimatedReaction: (_prepare: () => number, react: ReactionBody) => {
      mockReactionBodies.push(react);
    },
    runOnJS:
      (fn: (value: number) => void) =>
      (value: number) => {
        mockCrossings.push(value);
        return fn(value);
      },
  };
});

import { CounterTicker } from '../../src/components/CounterTicker';

/** The reaction body registered by the most recent render. */
function latestReaction(): ReactionBody {
  const body = mockReactionBodies[mockReactionBodies.length - 1];
  expect(typeof body).toBe('function');
  return body;
}

/** Feed the reaction a run of frames, threading `previous` as Reanimated does. */
function playFrames(react: ReactionBody, frames: number[]) {
  act(() => {
    frames.forEach((current, i) => {
      react(current, i === 0 ? null : frames[i - 1]);
    });
  });
}

beforeEach(() => {
  mockReactionBodies.length = 0;
  mockCrossings.length = 0;
});

describe('CounterTicker — per-frame commit guard (A16)', () => {
  it('crosses to JS once per distinct integer, not once per frame', () => {
    render(<CounterTicker target={100} duration={1200} testID="counter" />);
    const react = latestReaction();
    mockCrossings.length = 0;

    // Four frames spanning a single integer step: 10 → 10 → 10 → 11.
    playFrames(react, [10.1, 10.2, 10.4, 10.6]);

    expect(mockCrossings).toEqual([10, 11]);
  });

  it('holds the crossing count to the number of integers the tick passes', () => {
    render(<CounterTicker target={3} duration={800} testID="counter" />);
    const react = latestReaction();
    mockCrossings.length = 0;

    // 16 frames easing 0 → 3. Only four integers are ever displayed.
    const frames = Array.from({ length: 16 }, (_, i) => (i * 3) / 15);
    playFrames(react, frames);

    expect(frames.length).toBe(16);
    expect(mockCrossings.length).toBeLessThanOrEqual(4);
    expect(mockCrossings).toEqual([0, 1, 2, 3]);
  });

  it('still commits on the reaction first run, when previous is null', () => {
    render(<CounterTicker target={50} duration={400} testID="counter" />);
    const react = latestReaction();
    mockCrossings.length = 0;

    // A registration run whose rounded value equals what is already shown
    // must not be suppressed by an accidental "same as displayed" guard —
    // Reanimated hands us null, and null carries no previous reading.
    playFrames(react, [50]);

    expect(mockCrossings).toEqual([50]);
  });

  it('leaves the final displayed value at the target', () => {
    const { getByTestId } = render(
      <CounterTicker target={78} duration={1200} testID="counter" />
    );
    const react = latestReaction();

    playFrames(react, [77.2, 77.6, 77.9, 78]);

    // Last integer the guard let through is the target, and the Text node
    // agrees — the end-state contract the sibling suite asserts still holds.
    expect(mockCrossings[mockCrossings.length - 1]).toBe(78);
    expect(getByTestId('counter').props.children).toBe('78');
  });
});
