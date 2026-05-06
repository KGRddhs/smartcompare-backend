/**
 * QaranIcon test — Phase 1 Task 4. The Q-as-magnifier brand mark.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { QaranIcon } from '../../src/icons/QaranIcon';
import { flipForRTL } from '../../src/icons';

describe('QaranIcon', () => {
  it('renders an Svg root with default 24px size', () => {
    const { UNSAFE_root } = render(<QaranIcon />);
    // First child is the Svg element from react-native-svg.
    const svg = UNSAFE_root.findByType('Svg' as any);
    expect(svg.props.width).toBe(24);
    expect(svg.props.height).toBe(24);
  });

  it('accepts custom size prop', () => {
    const { UNSAFE_root } = render(<QaranIcon size={48} />);
    const svg = UNSAFE_root.findByType('Svg' as any);
    expect(svg.props.width).toBe(48);
    expect(svg.props.height).toBe(48);
  });

  it('uses default black #0A0A0B color', () => {
    const { UNSAFE_root } = render(<QaranIcon />);
    const circles = UNSAFE_root.findAllByType('Circle' as any);
    expect(circles[0].props.stroke).toBe('#0A0A0B');
  });

  it('respects color prop override', () => {
    const { UNSAFE_root } = render(<QaranIcon color="#10B981" />);
    const circles = UNSAFE_root.findAllByType('Circle' as any);
    // Ring stroke + tail-dot fill should both honor the override.
    expect(circles[0].props.stroke).toBe('#10B981');
    expect(circles[circles.length - 1].props.fill).toBe('#10B981');
  });
});

describe('flipForRTL helper', () => {
  it('returns no transform when LTR', () => {
    expect(flipForRTL(false)).toEqual({ transform: [] });
  });

  it('returns scaleX(-1) when RTL', () => {
    expect(flipForRTL(true)).toEqual({ transform: [{ scaleX: -1 }] });
  });
});
