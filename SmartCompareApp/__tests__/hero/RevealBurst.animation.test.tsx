/**
 * A10 — RevealBurst driver binding.
 *
 * The pre-A10 component drove two shared values (`badgeScale`,
 * `particleProgress`) that NOTHING read: the Circles were plain
 * `react-native-svg` nodes hard-coded to their resting position at a flat
 * 0.85 opacity, and the badge View carried no transform. The celebration
 * therefore shipped as a frozen tableau parked over the DimensionBars card.
 *
 * These tests pin the BINDING, not the mock. The reanimated mock evaluates a
 * `useAnimatedProps` / `useAnimatedStyle` updater once at render, so the
 * geometry it produces is a pure function of the shared value's CURRENT
 * reading — which is exactly the axis that distinguishes bound from unbound:
 *
 *   - animated (default) → progress starts at 0 → every particle sits at the
 *     centre at peak opacity, badge scale 0 (the spring's start).
 *   - animated={false}   → progress starts at 1 → every particle sits at its
 *     resting endpoint, faded out, badge scale 1.
 *
 * Under the unbound version BOTH branches render the identical static
 * endpoint and no transform at all, so every assertion below fails.
 */
import React from 'react';
import { StyleSheet } from 'react-native';
import { render } from '@testing-library/react-native';
import { RevealBurst } from '../../src/components/hero/RevealBurst';

const CENTER = 160;

function particleNodes(root: any) {
  return root.findAll(
    (n: any) =>
      typeof n.type === 'string' &&
      typeof n.props?.testID === 'string' &&
      n.props.testID.startsWith('reveal-burst-particle-'),
  );
}

function badgeNode(root: any) {
  return root.findAll(
    (n: any) =>
      typeof n.type === 'string' && n.props?.testID === 'reveal-burst-badge',
  )[0];
}

describe('RevealBurst — particle driver is bound to render (A10)', () => {
  it('emits from the centre at peak opacity while the driver is at 0', () => {
    const { UNSAFE_root } = render(<RevealBurst particleCount={6} />);
    const particles = particleNodes(UNSAFE_root);
    expect(particles.length).toBe(6);

    particles.forEach((p: any) => {
      const bound = p.props.animatedProps;
      // The geometry must arrive through the animated binding, never as a
      // literal prop on the host node.
      expect(bound).toBeDefined();
      expect(p.props.cx).toBeUndefined();
      expect(p.props.cy).toBeUndefined();
      expect(p.props.opacity).toBeUndefined();

      expect(bound.cx).toBeCloseTo(CENTER, 6);
      expect(bound.cy).toBeCloseTo(CENTER, 6);
      expect(bound.opacity).toBeCloseTo(0.85, 6);
    });
  });

  it('rests on the pre-A10 static endpoint, faded out, when the driver is at 1', () => {
    // animated={false} seeds particleProgress at 1 — the end of the burst.
    const { UNSAFE_root } = render(
      <RevealBurst particleCount={6} animated={false} />,
    );
    const particles = particleNodes(UNSAFE_root);

    // Endpoint parity guard: these are the exact coordinates the unbound
    // component rendered (CENTER + cos/sin * distance, + 40 of fall), so the
    // binding changed the PATH and the fade, not where the burst lands.
    expect(particles[0].props.animatedProps.cx).toBeCloseTo(160, 6);
    expect(particles[0].props.animatedProps.cy).toBeCloseTo(106.5, 6);
    expect(particles[1].props.animatedProps.cx).toBeCloseTo(255.26279441628824, 6);
    expect(particles[1].props.animatedProps.cy).toBeCloseTo(145, 6);

    // …and the designed fade-out has run, so the burst does not persist as a
    // static overlay on the DimensionBars card for the life of the screen.
    particles.forEach((p: any) => {
      expect(p.props.animatedProps.opacity).toBeCloseTo(0, 6);
    });
  });

  it('keeps fill + radius static on the host node (structural contract)', () => {
    const { UNSAFE_root } = render(<RevealBurst />);
    particleNodes(UNSAFE_root).forEach((p: any) => {
      expect(p.props.fill).toBe('#10B981');
      expect(p.props.r).toBe(5);
    });
  });
});

describe('RevealBurst — badge spring is bound to render (A10)', () => {
  it('scales the badge from the spring driver (0 at mount when animated)', () => {
    const { UNSAFE_root } = render(<RevealBurst />);
    const flat = StyleSheet.flatten(badgeNode(UNSAFE_root).props.style);
    expect(flat.transform).toEqual([{ scale: 0 }]);
  });

  it('renders the badge at rest scale when animated={false}', () => {
    const { UNSAFE_root } = render(<RevealBurst animated={false} />);
    const flat = StyleSheet.flatten(badgeNode(UNSAFE_root).props.style);
    expect(flat.transform).toEqual([{ scale: 1 }]);
  });
});
