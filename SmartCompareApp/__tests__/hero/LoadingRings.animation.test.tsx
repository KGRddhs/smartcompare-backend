/**
 * B3 — LoadingRings ring-radius driver binding.
 *
 * The pre-B3 component created three UI-thread shared values for the ring
 * radii, drove them with an infinite `withDelay(withRepeat(withTiming(...)))`,
 * and then read them as PLAIN NUMBERS during render (`const r = sv.value`)
 * into plain `react-native-svg` Circles. Mutating a shared value schedules no
 * React render, so the rings only moved when something else re-rendered the
 * component — in practice the counter's own rAF pump, which is bounded by
 * motion.counterTick (2400ms). After that the rings froze mid-loop while the
 * drivers kept looping on the UI thread forever, and on ResultsScreen's
 * loading branch (which has no timer at all) the freeze lasted the whole
 * compare.
 *
 * These pin the BINDING, not the mock. Two axes distinguish bound from
 * unbound:
 *
 *   1. CHANNEL — the radius and the fade must arrive through `animatedProps`
 *      on an animated component. A literal `r=` / `opacity=` on the host node
 *      IS the bug: a one-shot snapshot of the driver taken on the JS thread.
 *   2. DERIVATION — the bound props must be a live function of the driver's
 *      current reading (radius → the 1→0 fade ramp), not baked constants.
 *
 * Under the unbound version `animatedProps` is absent on every ring, so every
 * assertion below except the deliberate structural guard fails.
 */
import React from 'react';
import { render } from '@testing-library/react-native';

/**
 * Extends the shared reanimated mock with a shared value whose reading this
 * suite can pin. Default (`null`) behaves exactly like the shared mock: the
 * value starts at its init and honours writes. Setting `mockRingReading`
 * forces every driver to report that radius at render time, which is how we
 * observe the ring geometry mid-loop without a UI runtime.
 */
let mockRingReading: number | null = null;

jest.mock('react-native-reanimated', () => {
  const real = jest.requireActual('react-native-reanimated');
  return {
    __esModule: true,
    ...real,
    default: real.default ?? real,
    useSharedValue: (init: number) => {
      let stored = init;
      return {
        get value() {
          return mockRingReading === null ? stored : mockRingReading;
        },
        set value(next: number) {
          stored = next;
        },
      };
    },
  };
});

import { LoadingRings } from '../../src/components/hero/LoadingRings';

const RING_BASE_R = 60;
const RING_TARGET_R = 150;

function ringNodes(root: any) {
  return root.findAll(
    (n: any) =>
      typeof n.type === 'string' &&
      typeof n.props?.testID === 'string' &&
      n.props.testID.startsWith('loading-rings-ring-'),
  );
}

afterEach(() => {
  mockRingReading = null;
});

describe('LoadingRings — ring radii are bound to render (B3)', () => {
  it('feeds radius + fade through animatedProps, never as render-time literals', () => {
    const { UNSAFE_root } = render(<LoadingRings />);
    const rings = ringNodes(UNSAFE_root);
    expect(rings.length).toBe(3);

    rings.forEach((ring: any) => {
      expect(ring.props.animatedProps).toBeDefined();
      // A literal r / opacity on the host node is the exact shape of the
      // defect — the JS thread sampling the driver once per render.
      expect(ring.props.r).toBeUndefined();
      expect(ring.props.opacity).toBeUndefined();

      // Drivers start at the base radius, fully opaque.
      expect(ring.props.animatedProps.r).toBeCloseTo(RING_BASE_R, 6);
      expect(ring.props.animatedProps.opacity).toBeCloseTo(1, 6);
    });
  });

  it('derives radius + fade from the driver mid-loop, not from constants', () => {
    // Halfway through the expansion: r is the driver reading and the ring is
    // half faded. Under the pre-B3 render-time read this geometry could only
    // ever reach the screen on a React re-render.
    mockRingReading = (RING_BASE_R + RING_TARGET_R) / 2;
    const { UNSAFE_root } = render(<LoadingRings />);

    ringNodes(UNSAFE_root).forEach((ring: any) => {
      expect(ring.props.r).toBeUndefined();
      expect(ring.props.animatedProps.r).toBeCloseTo(105, 6);
      expect(ring.props.animatedProps.opacity).toBeCloseTo(0.5, 6);
    });
  });

  it('fades the ring fully out at the end of the expansion', () => {
    mockRingReading = RING_TARGET_R;
    const { UNSAFE_root } = render(<LoadingRings />);

    ringNodes(UNSAFE_root).forEach((ring: any) => {
      expect(ring.props.animatedProps.r).toBeCloseTo(RING_TARGET_R, 6);
      expect(ring.props.animatedProps.opacity).toBeCloseTo(0, 6);
    });
  });

  it('keeps the reduced-motion path on the static base ring (animated={false})', () => {
    // Contract guard: animated={false} never drives the radii, so the rings
    // must still paint the pre-B3 static circle — r=60 at full opacity — for
    // the two consumers that mount it that way.
    const { UNSAFE_root } = render(
      <LoadingRings counterTarget={2074} animated={false} />,
    );

    ringNodes(UNSAFE_root).forEach((ring: any) => {
      expect(ring.props.animatedProps.r).toBeCloseTo(RING_BASE_R, 6);
      expect(ring.props.animatedProps.opacity).toBeCloseTo(1, 6);
    });
  });

  it('keeps centre + stroke static on the host node (structural contract)', () => {
    const { UNSAFE_root } = render(<LoadingRings />);
    ringNodes(UNSAFE_root).forEach((ring: any) => {
      expect(ring.props.cx).toBe(160);
      expect(ring.props.cy).toBe(160);
      expect(ring.props.fill).toBe('none');
      expect(ring.props.stroke).toBe('#10B981');
      expect(ring.props.strokeWidth).toBe(2.5);
    });
  });
});
