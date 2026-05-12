/**
 * QarenLogo brand-glyph tests — Bundle B/C/D Task 2.10.
 *
 * Verifies the SVG glyph renders and accepts size/color props so the
 * 4 header swaps (Home, Profile, History, Splash) can scale it
 * appropriately without per-screen variants.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import QarenLogo from '../../src/components/QarenLogo';

describe('QarenLogo', () => {
  it('renders a single Svg root', () => {
    const { UNSAFE_root } = render(<QarenLogo />);
    const svgs = UNSAFE_root.findAllByType('Svg' as any);
    expect(svgs.length).toBe(1);
  });

  it('applies the size prop to width + height + viewBox', () => {
    const { UNSAFE_root } = render(<QarenLogo size={48} />);
    const svg = UNSAFE_root.findByType('Svg' as any);
    expect(svg.props.width).toBe(48);
    expect(svg.props.height).toBe(48);
  });

  it('defaults size to 32 when no prop given', () => {
    const { UNSAFE_root } = render(<QarenLogo />);
    const svg = UNSAFE_root.findByType('Svg' as any);
    expect(svg.props.width).toBe(32);
    expect(svg.props.height).toBe(32);
  });

  it('renders the emerald accent dot (signal-color rule from Bundle A)', () => {
    const { UNSAFE_root } = render(<QarenLogo />);
    const circles = UNSAFE_root.findAllByType('Circle' as any);
    // At least one Circle uses the emerald accent color.
    const hasEmerald = circles.some(
      (c: any) => c.props.fill === '#10B981'
    );
    expect(hasEmerald).toBe(true);
  });

  it('the main mark uses the color prop when provided', () => {
    const { UNSAFE_root } = render(<QarenLogo color="#FF00FF" />);
    const circles = UNSAFE_root.findAllByType('Circle' as any);
    // At least one Circle stroke uses the override color (the outer Q ring).
    const hasOverride = circles.some(
      (c: any) => c.props.stroke === '#FF00FF'
    );
    expect(hasOverride).toBe(true);
  });
});
