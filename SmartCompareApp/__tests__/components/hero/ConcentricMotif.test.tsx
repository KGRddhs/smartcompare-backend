/**
 * ConcentricMotif structural test — Bundle D legacy + Bundle E spec refresh.
 *
 * Bundle E (2026-05-26) swapped the visual from "5 neutral rotating rings"
 * to "3 emerald rings expanding outward" per design doc § 3.2 and the JSX
 * reference shared with LoadingRings. The structural assertions below are
 * the post-Bundle-E contract; the snapshot in __tests__/hero/ confirms the
 * visual output.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { ConcentricMotif } from '../../../src/components/hero/ConcentricMotif';

describe('ConcentricMotif', () => {
  it('renders an Svg root', () => {
    const { UNSAFE_root } = render(<ConcentricMotif />);
    expect(UNSAFE_root.findAllByType('Svg' as any).length).toBeGreaterThan(0);
  });

  it('renders 3 concentric expanding rings (Bundle E spec)', () => {
    const { UNSAFE_root } = render(<ConcentricMotif />);
    const rings = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' &&
        typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('concentric-ring-'),
    );
    expect(rings.length).toBe(3);
  });

  it('all 3 rings use the emerald accent stroke', () => {
    const { UNSAFE_root } = render(<ConcentricMotif />);
    for (let i = 0; i < 3; i++) {
      const ring = UNSAFE_root.findAll(
        (n: any) =>
          typeof n.type === 'string' && n.props?.testID === `concentric-ring-${i}`,
      );
      expect(ring[0].props.stroke).toBe('#10B981');
    }
  });

  it('respects size prop', () => {
    const { UNSAFE_root } = render(<ConcentricMotif size={400} />);
    const svgs = UNSAFE_root.findAllByType('Svg' as any);
    expect(svgs[0].props.width).toBe(400);
    expect(svgs[0].props.height).toBe(400);
  });
});
