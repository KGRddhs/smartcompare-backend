import React from 'react';
import { render } from '@testing-library/react-native';
import ScannerReticle from '../../src/components/ScannerReticle';

describe('ScannerReticle', () => {
  it('renders SVG with at least 4 corner-bracket Path elements', () => {
    const { UNSAFE_root } = render(<ScannerReticle />);
    const paths = UNSAFE_root.findAllByType('Path' as any);
    expect(paths.length).toBeGreaterThanOrEqual(4);
  });

  it('renders one Svg root', () => {
    const { UNSAFE_root } = render(<ScannerReticle />);
    const svgs = UNSAFE_root.findAllByType('Svg' as any);
    expect(svgs.length).toBe(1);
  });

  it('uses pointerEvents=none so taps pass through to camera below', () => {
    const { UNSAFE_root } = render(<ScannerReticle />);
    const overlay = UNSAFE_root.findByProps({ pointerEvents: 'none' });
    expect(overlay).toBeTruthy();
  });
});
