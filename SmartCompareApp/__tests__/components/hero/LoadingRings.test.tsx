/**
 * LoadingRings test — Phase 2 Task 17 (illustration #4 — centerpiece).
 * Onboarding screen 14 (theatrical 3.2s loading).
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { LoadingRings } from '../../../src/components/hero/LoadingRings';

describe('LoadingRings', () => {
  it('renders an Svg root', () => {
    const { UNSAFE_root } = render(<LoadingRings />);
    expect(UNSAFE_root.findAllByType('Svg' as any).length).toBeGreaterThan(0);
  });

  it('F1 the central brand mark is ONE host Image sized 0.22 of the rings (320 -> 70, 240 -> 53, 120 -> 26)', () => {
    // U4c (spec 2026-10-03-session-71-state/U4C_INAPP_MARK_SPEC.md §5 F1):
    // QarenLogo is now the bundled MYEZ mark PNG, a single RN Image, at
    // Math.round(size * 0.22) inside the static `loading-rings-logo` centre.
    const flatten = (style: unknown): Record<string, unknown> =>
      Array.isArray(style)
        ? style.reduce<Record<string, unknown>>((acc, s) => ({ ...acc, ...flatten(s) }), {})
        : style && typeof style === 'object'
          ? { ...(style as Record<string, unknown>) }
          : {};
    const cases: [number, number][] = [
      [320, 70],
      [240, 53],
      [120, 26],
    ];
    const got = cases.map(([size]) => {
      const { UNSAFE_root, unmount } = render(<LoadingRings size={size} />);
      const centre = UNSAFE_root.findAll(
        (n: any) =>
          typeof n.type === 'string' && n.props?.testID === 'loading-rings-logo'
      );
      const images = centre.length === 1 ? centre[0].findAll((n: any) => n.type === 'Image') : [];
      const svgs = centre.length === 1 ? centre[0].findAll((n: any) => n.type === 'Svg') : [];
      const style = images.length === 1 ? flatten(images[0].props.style) : {};
      unmount();
      return {
        size,
        centres: centre.length,
        images: images.length,
        svgs: svgs.length,
        width: style.width,
        height: style.height,
      };
    });
    expect(got).toEqual(
      cases.map(([size, px]) => ({ size, centres: 1, images: 1, svgs: 0, width: px, height: px }))
    );
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
