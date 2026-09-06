/**
 * A10 — PhoneMockup glow-pulse binding.
 *
 * The pre-A10 component drove `glowOpacity` with an INFINITE
 * `withRepeat(withSequence(...))` whose only consumer was
 * `opacity={glowOpacity.value}` — a plain read during render on a plain
 * (non-animated) `Rect`. Mutating a shared value does not schedule a React
 * render, so that read was a one-shot snapshot at mount: the ring painted at
 * a flat 0.4 forever while the driver ticked on the UI thread every frame
 * driving nothing. The sting: the production `animated` path rendered DIMMER
 * (0.4) than the reduced-motion path (0.7).
 *
 * These pin the binding, not the mock: the glow's opacity must arrive through
 * `animatedProps` on an animated component, never as a render-time literal.
 * Under the unbound version `animatedProps` is absent and `opacity` is a
 * literal prop, so both assertions flip.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { PhoneMockup } from '../../src/components/hero/PhoneMockup';

function glowNode(root: any) {
  return root.findAll(
    (n: any) =>
      typeof n.type === 'string' && n.props?.testID === 'phone-mockup-glow',
  )[0];
}

describe('PhoneMockup — glow pulse is bound to render (A10)', () => {
  it('feeds the ring opacity through animatedProps, not a render-time read', () => {
    const { UNSAFE_root } = render(<PhoneMockup />);
    const glow = glowNode(UNSAFE_root);

    expect(glow).toBeDefined();
    expect(glow.props.animatedProps).toBeDefined();
    // No literal opacity may survive on the host node — that is the exact
    // shape of the bug: a static snapshot of the driver.
    expect(glow.props.opacity).toBeUndefined();
    // Pulse floor is where the driver starts when animated.
    expect(glow.props.animatedProps.opacity).toBeCloseTo(0.4, 6);
  });

  it('holds the ring at the reduced-motion value when animated={false}', () => {
    const { UNSAFE_root } = render(<PhoneMockup animated={false} />);
    const glow = glowNode(UNSAFE_root);

    expect(glow.props.animatedProps.opacity).toBeCloseTo(0.7, 6);
    expect(glow.props.opacity).toBeUndefined();
  });

  it('keeps the ring stroke-only and static-stroked (structural contract)', () => {
    const { UNSAFE_root } = render(<PhoneMockup />);
    const glow = glowNode(UNSAFE_root);
    expect(glow.props.fill).toBe('none');
    expect(glow.props.stroke).toBe('#10B981');
    expect(glow.props.strokeWidth).toBe(4);
  });
});
