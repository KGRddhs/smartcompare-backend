/**
 * Utility icon tests — Phase 1 Task 5.
 *
 * 6 custom utility icons replacing Lucide stand-ins for the most-touched
 * surfaces (header back / close, search bar, bell, settings, plus). The
 * remaining 15 utility lucide icons (Eye, EyeOff, Lock, ChevronRight,
 * ChevronDown, Filter, Trash2, Check, etc.) stay on Lucide for now.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import {
  BackIcon,
  CloseIcon,
  SearchIcon,
  BellIcon,
  SettingsIcon,
  PlusIcon,
} from '../../src/icons/UtilityIcons';

const ICONS = [
  ['BackIcon', BackIcon],
  ['CloseIcon', CloseIcon],
  ['SearchIcon', SearchIcon],
  ['BellIcon', BellIcon],
  ['SettingsIcon', SettingsIcon],
  ['PlusIcon', PlusIcon],
] as const;

describe.each(ICONS)('%s', (name, Icon) => {
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
    // Color shows up either as fill on the Svg root OR on a child Path/etc.
    const allChildren = svg.findAllByProps({ fill: '#0A0A0B' });
    expect(allChildren.length).toBeGreaterThan(0);
  });

  it('respects color prop override', () => {
    const { UNSAFE_root } = render(<Icon color="#10B981" />);
    const svg = UNSAFE_root.findByType('Svg' as any);
    const overridden = svg.findAllByProps({ fill: '#10B981' });
    expect(overridden.length).toBeGreaterThan(0);
    const stillDefault = svg.findAllByProps({ fill: '#0A0A0B' });
    expect(stillDefault.length).toBe(0);
  });
});

describe('icons/index re-exports', () => {
  it('exports all 6 utility icons', () => {
    const idx = require('../../src/icons');
    expect(idx.BackIcon).toBeDefined();
    expect(idx.CloseIcon).toBeDefined();
    expect(idx.SearchIcon).toBeDefined();
    expect(idx.BellIcon).toBeDefined();
    expect(idx.SettingsIcon).toBeDefined();
    expect(idx.PlusIcon).toBeDefined();
  });
});
