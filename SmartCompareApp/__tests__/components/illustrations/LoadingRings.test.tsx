/**
 * LoadingRings test — Phase 2 Task 17 (illustration #4 — centerpiece).
 * Onboarding screen 14 (theatrical 3.2s loading).
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { LoadingRings } from '../../../src/components/illustrations/LoadingRings';

describe('LoadingRings', () => {
  it('renders an Svg root', () => {
    const { UNSAFE_root } = render(<LoadingRings />);
    expect(UNSAFE_root.findAllByType('Svg' as any).length).toBeGreaterThan(0);
  });

  it('renders the central Q-logo brand mark via QaranIcon', () => {
    const { UNSAFE_root } = render(<LoadingRings />);
    // QaranIcon renders Circle elements; just verify SOMEthing with the
    // brand black or emerald color is present in the central area.
    const centerLogo = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' && n.props?.testID === 'loading-rings-logo'
    );
    expect(centerLogo.length).toBeGreaterThan(0);
  });

  it('renders 3 expanding emerald rings', () => {
    const { UNSAFE_root } = render(<LoadingRings />);
    const rings = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' &&
        typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('loading-rings-ring-')
    );
    expect(rings.length).toBe(3);
  });

  it('all 3 rings use emerald stroke', () => {
    const { UNSAFE_root } = render(<LoadingRings />);
    const rings = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' &&
        typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('loading-rings-ring-')
    );
    rings.forEach((r: any) => expect(r.props.stroke).toBe('#10B981'));
  });

  it('respects size prop', () => {
    const { UNSAFE_root } = render(<LoadingRings size={300} />);
    const svgs = UNSAFE_root.findAllByType('Svg' as any);
    expect(svgs[0].props.width).toBe(300);
  });
});
