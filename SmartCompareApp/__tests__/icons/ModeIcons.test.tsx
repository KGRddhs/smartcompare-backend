/**
 * ModeIcons tests — Phase 2 follow-up (Task #51).
 *
 * 3 mode icons (Scan / Link / Type) for HomeScreen's 3-equal-chip mode
 * selector per design § 5a row "Mode | 3". Drop-in compatible with the
 * Lucide icons currently used (size + color props, default #0A0A0B).
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import {
  ScanIcon,
  LinkIcon,
  TypeIcon,
} from '../../src/icons/ModeIcons';

const ICONS = [
  ['ScanIcon', ScanIcon],
  ['LinkIcon', LinkIcon],
  ['TypeIcon', TypeIcon],
] as const;

describe.each(ICONS)('%s', (_name, Icon) => {
  it('renders an Svg root with default 24px size', () => {
    const { UNSAFE_root } = render(<Icon />);
    const svg = UNSAFE_root.findByType('Svg' as any);
    expect(svg.props.width).toBe(24);
    expect(svg.props.height).toBe(24);
  });

  it('respects size prop', () => {
    const { UNSAFE_root } = render(<Icon size={32} />);
    const svg = UNSAFE_root.findByType('Svg' as any);
    expect(svg.props.width).toBe(32);
  });

  it('uses default black color #0A0A0B', () => {
    const { UNSAFE_root } = render(<Icon />);
    const svg = UNSAFE_root.findByType('Svg' as any);
    const allChildren = svg.findAllByProps({ fill: '#0A0A0B' });
    expect(allChildren.length).toBeGreaterThan(0);
  });

  it('respects color prop override', () => {
    const { UNSAFE_root } = render(<Icon color="#FFFFFF" />);
    const svg = UNSAFE_root.findByType('Svg' as any);
    const overridden = svg.findAllByProps({ fill: '#FFFFFF' });
    expect(overridden.length).toBeGreaterThan(0);
    const stillDefault = svg.findAllByProps({ fill: '#0A0A0B' });
    expect(stillDefault.length).toBe(0);
  });
});

describe('icons/index re-exports', () => {
  it('exports all 3 mode icons', () => {
    const idx = require('../../src/icons');
    expect(idx.ScanIcon).toBeDefined();
    expect(idx.LinkIcon).toBeDefined();
    expect(idx.TypeIcon).toBeDefined();
  });
});
