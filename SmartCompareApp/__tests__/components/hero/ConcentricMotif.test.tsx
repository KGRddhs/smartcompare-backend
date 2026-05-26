/**
 * ConcentricMotif test — Phase 2 Task 17 (illustration #3).
 * Onboarding screen 13 ("Time to build your shopping advisor").
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { ConcentricMotif } from '../../../src/components/hero/ConcentricMotif';

describe('ConcentricMotif', () => {
  it('renders an Svg root', () => {
    const { UNSAFE_root } = render(<ConcentricMotif />);
    expect(UNSAFE_root.findAllByType('Svg' as any).length).toBeGreaterThan(0);
  });

  it('renders 5 concentric ring circles + 1 center brand mark', () => {
    const { UNSAFE_root } = render(<ConcentricMotif />);
    const rings = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' &&
        typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('concentric-ring-')
    );
    expect(rings.length).toBe(5);
  });

  it('innermost ring uses emerald accent', () => {
    const { UNSAFE_root } = render(<ConcentricMotif />);
    const innermost = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' && n.props?.testID === 'concentric-ring-0'
    );
    expect(innermost[0].props.stroke).toBe('#10B981');
  });

  it('outer rings use neutral border color', () => {
    const { UNSAFE_root } = render(<ConcentricMotif />);
    const outer = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' && n.props?.testID === 'concentric-ring-4'
    );
    expect(outer[0].props.stroke).not.toBe('#10B981');
  });

  it('respects size prop', () => {
    const { UNSAFE_root } = render(<ConcentricMotif size={400} />);
    const svgs = UNSAFE_root.findAllByType('Svg' as any);
    expect(svgs[0].props.width).toBe(400);
    expect(svgs[0].props.height).toBe(400);
  });
});
