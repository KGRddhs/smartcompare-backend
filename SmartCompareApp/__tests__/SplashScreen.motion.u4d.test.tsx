/**
 * U4d - the JS splash is PINNED, not changed: the mark never moves, fades or
 * remounts after the first frame, and the tagline is the only animation
 * (issue #283, O3).
 *
 * Spec: docs/investigations/2026-10-03-session-71-state/U4D_REVEAL_GLYPH_SPEC.md
 * section 2f and section 5 rows P1-P4, with P1 replaced by P1b (correction C1,
 * ruling UR9) and the file shape of correction C5.
 *
 * All four are PINs: green at base and after GREEN (SplashScreen.tsx stays
 * byte-unchanged, R6).
 *
 * Why a file-local reanimated mock: the repo mock's useSharedValue returns a
 * FRESH { value } on every render, so a value set after mount is invisible
 * after a re-render. This file wraps the repo mock and makes useSharedValue
 * stable (React.useRef), records every object useAnimatedStyle returns (so
 * an animated style attached to the mark path is detectable), and wraps
 * withTiming / withDelay / withSpring / withRepeat / withSequence in jest.fn
 * so the tagline's animation arguments are pinned. The mock is NOT virtual:
 * react-native-reanimated exists (C5).
 *
 * The repo jest window is 390 x 844 (__mocks__/react-native.ts Dimensions),
 * as in SplashScreen.mark.u4c: the mark rect there is left 134.675, top
 * 358.000, size 126.803 (+-0.01). Fake timers only; no wall-clock dependency.
 * Stated limit (L6): these pins prove binding and arguments, not frame timing.
 */
import React from 'react';
import { act, render } from '@testing-library/react-native';
import { Dimensions, I18nManager } from 'react-native';
import SplashScreen from '../src/screens/SplashScreen';

jest.mock('react-native-reanimated', () => {
  const base = jest.requireActual('../__mocks__/react-native-reanimated');
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const ReactInMock = require('react');
  const animatedStyles = new Set<object>();
  return {
    ...base,
    // The spread drops TypeScript's non-enumerable __esModule flag.
    __esModule: true,
    default: base.default,
    __animatedStyles: animatedStyles,
    // Stable across renders (the repo mock returns a fresh object per render).
    useSharedValue: (init: number) => ReactInMock.useRef({ value: init }).current,
    useAnimatedStyle: (updater: () => object) => {
      const s = updater();
      animatedStyles.add(s);
      return s;
    },
    withTiming: jest.fn(base.withTiming),
    withDelay: jest.fn(base.withDelay),
    withSpring: jest.fn(base.withSpring),
    withRepeat: jest.fn(base.withRepeat),
    withSequence: jest.fn(base.withSequence),
  };
});

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) =>
      (({ 'app.name': 'MYEZ', 'splash.tagline': 'Compare smarter' }) as Record<string, string>)[key] ?? key,
  }),
}));

/** The instrumented mock above, read back (typed locally; the real package types do not know __animatedStyles). */
type InstrumentedReanimated = {
  __animatedStyles: Set<object>;
  withTiming: jest.Mock;
  withDelay: jest.Mock;
  withSpring: jest.Mock;
  withRepeat: jest.Mock;
  withSequence: jest.Mock;
};
// eslint-disable-next-line @typescript-eslint/no-require-imports
const R: InstrumentedReanimated = require('react-native-reanimated');

/**
 * Local structural type for a test-renderer node: the repo installs no
 * @types/react-test-renderer, so RNTL's `UNSAFE_root` is typed loosely.
 */
type TestNode = {
  type: unknown;
  props: Record<string, any>;
  parent: TestNode | null;
  findAll: (predicate: (node: TestNode) => boolean) => TestNode[];
};

type Style = Record<string, unknown>;

/** Deep StyleSheet.flatten (the repo mock flattens one array level only). */
function flattenStyle(style: unknown): Style {
  if (Array.isArray(style)) {
    return style.reduce<Style>((acc, s) => ({ ...acc, ...flattenStyle(s) }), {});
  }
  if (style && typeof style === 'object') return { ...(style as Style) };
  return {};
}

/** Every style object a style prop references (so registry membership can be tested). */
function styleObjects(style: unknown, out: object[] = []): object[] {
  if (Array.isArray(style)) style.forEach((s) => styleObjects(s, out));
  else if (style && typeof style === 'object') out.push(style as object);
  return out;
}

/** Asymmetric matcher: a number within +-tol of `expected` (spec: +-0.01). */
function near(expected: number, tol = 0.01) {
  return {
    $$typeof: Symbol.for('jest.asymmetricMatcher'),
    asymmetricMatch: (actual: unknown): boolean => typeof actual === 'number' && Math.abs(actual - expected) <= tol,
    toAsymmetricMatcher: (): string => `${expected} +- ${tol}`,
  };
}

// Spec section 2d / U4c C1, window 390 x 844.
const RECT = {
  position: 'absolute',
  left: near(134.675),
  top: near(358.0),
  width: near(126.803),
  height: near(126.803),
};
// mark.top + mark.size + spacing.lg = 358.000 + 126.803 + 20.
const TAGLINE_TOP = 358.0 + 126.803 + 20;

type PathState =
  | { error: string }
  | { image: TestNode; hosts: string; violations: string[] };

/**
 * The state of every host from the one mark Image up to the root: its type,
 * testID and deep-flattened style (serialised), plus the violations P1b
 * forbids on that path (an animated style object, opacity, transform,
 * entering / exiting / layout / animatedProps).
 */
function markPathState(root: TestNode): PathState {
  const images = root.findAll((n) => n.type === 'Image');
  if (images.length !== 1) return { error: `expected 1 Image, got ${images.length}` };
  const hosts: unknown[] = [];
  const violations: string[] = [];
  for (let n: TestNode | null = images[0]; n; n = n.parent) {
    if (typeof n.type !== 'string') continue;
    const style = flattenStyle(n.props.style);
    hosts.push({ type: n.type, testID: n.props.testID ?? null, style });
    const label = `${n.type}${n.props.testID ? `#${n.props.testID}` : ''}`;
    if (styleObjects(n.props.style).some((o) => R.__animatedStyles.has(o))) violations.push(`${label} animated style`);
    if (style.opacity !== undefined) violations.push(`${label} opacity ${JSON.stringify(style.opacity)}`);
    if (style.transform !== undefined) violations.push(`${label} transform`);
    for (const p of ['entering', 'exiting', 'layout', 'animatedProps']) {
      if (n.props[p] !== undefined) violations.push(`${label} ${p}`);
    }
  }
  return { image: images[0], hosts: JSON.stringify(hosts), violations };
}

describe('U4d splash motion pins - only the tagline animates', () => {
  const initialIsRTL = I18nManager.isRTL;

  beforeEach(() => {
    jest.useFakeTimers();
    // C5: P2 reads cumulative mock.calls since this reset.
    jest.clearAllMocks();
    R.__animatedStyles.clear();
  });

  afterEach(() => {
    (I18nManager as { isRTL: boolean }).isRTL = initialIsRTL;
    jest.useRealTimers();
  });

  it('P1b [PIN] the mark path is frozen after the first frame: sampled every 50 ms to 1600 ms, then after ready (no animation, no style change, no remount)', () => {
    expect(Dimensions.get('window')).toMatchObject({ width: 390, height: 844 });
    const onFinish = jest.fn();
    const r = render(<SplashScreen onFinish={onFinish} />);
    const root = r.UNSAFE_root as unknown as TestNode;

    const first = markPathState(root);
    expect('error' in first ? first : { violations: first.violations }).toEqual({ violations: [] });
    // The first-frame rect kept from P1 (the native launch position).
    expect(flattenStyle(r.getByTestId('splash-mark').props.style)).toEqual(RECT);
    if ('error' in first) return;

    const drift: string[] = [];
    const check = (when: string): void => {
      const s = markPathState(root);
      if ('error' in s) {
        drift.push(`${when}: ${s.error}`);
        return;
      }
      if (s.violations.length) drift.push(`${when}: ${s.violations.join(', ')}`);
      if (s.hosts !== first.hosts) drift.push(`${when}: path styles changed`);
      if (s.image !== first.image) drift.push(`${when}: Image remounted`);
    };
    for (let t = 50; t <= 1600; t += 50) {
      act(() => {
        jest.advanceTimersByTime(50);
      });
      check(`${t} ms`);
    }
    r.rerender(<SplashScreen onFinish={onFinish} ready />);
    check('after ready');
    expect(drift).toEqual([]);
  });

  it('P2 [PIN] the only animation in the splash is the tagline: withDelay(200, withTiming(1, { duration: 400 })), nothing else', () => {
    render(<SplashScreen onFinish={jest.fn()} />);
    expect({
      withDelay: R.withDelay.mock.calls,
      withTiming: R.withTiming.mock.calls,
      withSpring: R.withSpring.mock.calls.length,
      withRepeat: R.withRepeat.mock.calls.length,
      withSequence: R.withSequence.mock.calls.length,
    }).toEqual({
      withDelay: [[200, 1]],
      withTiming: [[1, { duration: 400 }]],
      withSpring: 0,
      withRepeat: 0,
      withSequence: 0,
    });
  });

  it('P3 [PIN] the tagline sits 20 pt under the mark, full width, centred, body type, secondary colour; opacity 0, then 1 once a re-render reads the timing', () => {
    expect(Dimensions.get('window')).toMatchObject({ width: 390, height: 844 });
    const r = render(<SplashScreen onFinish={jest.fn()} />);
    const first = flattenStyle(r.getByText('Compare smarter').props.style);
    act(() => {
      jest.advanceTimersByTime(700);
    });
    const later = flattenStyle(r.getByText('Compare smarter').props.style);
    const expected = {
      position: 'absolute',
      left: 0,
      right: 0,
      textAlign: 'center',
      fontSize: 16,
      fontWeight: '400',
      lineHeight: 24,
      color: '#6B7280',
      top: near(TAGLINE_TOP),
    };
    expect({ keys: Object.keys(first).sort(), first, laterOpacity: later.opacity }).toEqual({
      keys: ['color', 'fontSize', 'fontWeight', 'left', 'lineHeight', 'opacity', 'position', 'right', 'textAlign', 'top'],
      first: { ...expected, opacity: 0 },
      laterOpacity: 1,
    });
  });

  it('P4 [PIN] [RTL] the tagline does not move under RTL: left 0 / right 0, same top, no start / end', () => {
    (I18nManager as { isRTL: boolean }).isRTL = true;
    const r = render(<SplashScreen onFinish={jest.fn()} />);
    const s = flattenStyle(r.getByText('Compare smarter').props.style);
    expect({ left: s.left, right: s.right, top: s.top, start: s.start, end: s.end }).toEqual({
      left: 0,
      right: 0,
      top: near(TAGLINE_TOP),
      start: undefined,
      end: undefined,
    });
  });
});
