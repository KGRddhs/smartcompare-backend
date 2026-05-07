/**
 * RevealBurst test — Phase 2 Task 17 (illustration #5).
 * Onboarding screen 15 (reveal: "Your shopping advisor is ready").
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { RevealBurst } from '../../../src/components/illustrations/RevealBurst';

describe('RevealBurst', () => {
  it('renders an Svg root', () => {
    const { UNSAFE_root } = render(<RevealBurst />);
    expect(UNSAFE_root.findAllByType('Svg' as any).length).toBeGreaterThan(0);
  });

  it('renders 8 emerald burst lines radiating at 45° intervals', () => {
    const { UNSAFE_root } = render(<RevealBurst />);
    const lines = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' &&
        typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('reveal-burst-line-')
    );
    expect(lines.length).toBe(8);
    lines.forEach((l: any) => expect(l.props.stroke).toBe('#10B981'));
  });

  it('renders the Q-badge at center', () => {
    const { UNSAFE_root } = render(<RevealBurst />);
    const badge = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' && n.props?.testID === 'reveal-burst-badge'
    );
    expect(badge.length).toBeGreaterThan(0);
  });

  it('renders the emerald check ✓ above the badge', () => {
    const { UNSAFE_root } = render(<RevealBurst />);
    const check = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' && n.props?.testID === 'reveal-burst-check'
    );
    expect(check.length).toBeGreaterThan(0);
  });

  it('respects size prop', () => {
    const { UNSAFE_root } = render(<RevealBurst size={280} />);
    // The first Svg is the burst lines container at full size; later
    // Svg(s) are children for the check + Q-icon at smaller scales.
    const svgs = UNSAFE_root.findAllByType('Svg' as any);
    expect(svgs[0].props.width).toBe(280);
  });
});
