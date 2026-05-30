/**
 * RevealBurst structural test — Bundle D legacy refreshed for Bundle E shape.
 *
 * Bundle E (QA § 6 audit 2026-05-26) repurposed RevealBurst for the
 * ResultsScreen winner-card moment only (Step15Reveal switched to MatchBadge).
 * The visual is now "6-8 emerald particles + scale-bounce badge" rather than
 * "8 burst lines + check glyph". Structural assertions updated accordingly;
 * the snapshot in __tests__/hero/ pins the exact tree.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { RevealBurst } from '../../../src/components/hero/RevealBurst';

describe('RevealBurst', () => {
  it('renders an Svg root', () => {
    const { UNSAFE_root } = render(<RevealBurst />);
    expect(UNSAFE_root.findAllByType('Svg' as any).length).toBeGreaterThan(0);
  });

  it('renders emerald particles emitted from center (default count)', () => {
    const { UNSAFE_root } = render(<RevealBurst />);
    const particles = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' &&
        typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('reveal-burst-particle-'),
    );
    // Default particleCount=6 per Bundle E spec (clamped 6–8 in design intent).
    expect(particles.length).toBe(6);
    particles.forEach((p: any) => expect(p.props.fill).toBe('#10B981'));
  });

  it('renders the Q-badge at center', () => {
    const { UNSAFE_root } = render(<RevealBurst />);
    const badge = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' && n.props?.testID === 'reveal-burst-badge',
    );
    expect(badge.length).toBeGreaterThan(0);
  });

  it('honors custom particleCount', () => {
    const { UNSAFE_root } = render(<RevealBurst particleCount={8} />);
    const particles = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' &&
        typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('reveal-burst-particle-'),
    );
    expect(particles.length).toBe(8);
  });

  it('respects size prop', () => {
    const { UNSAFE_root } = render(<RevealBurst size={280} />);
    const svgs = UNSAFE_root.findAllByType('Svg' as any);
    expect(svgs[0].props.width).toBe(280);
  });
});
