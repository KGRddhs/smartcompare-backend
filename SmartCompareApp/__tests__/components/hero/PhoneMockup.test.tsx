/**
 * PhoneMockup test — Phase 2 Task 18 (illustration #1).
 * Onboarding screen 3 (value prop: "Stop guessing. Start knowing.").
 *
 * Per design Section 5b: phone mockup at 3/4 angle showing real Qaren
 * Results UI with two product cards + emerald winner badge + glow ring
 * around winner. Production: Figma → SVG export.
 *
 * NOTE: this commit ships a hand-coded SVG placeholder per team-lead
 * direction (no Figma file provided yet). Marked for designer
 * review at hand-off time.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { PhoneMockup } from '../../../src/components/hero/PhoneMockup';

describe('PhoneMockup (placeholder)', () => {
  it('renders an Svg root', () => {
    const { UNSAFE_root } = render(<PhoneMockup />);
    expect(UNSAFE_root.findAllByType('Svg' as any).length).toBeGreaterThan(0);
  });

  it('renders the phone frame (outer rounded rect)', () => {
    const { UNSAFE_root } = render(<PhoneMockup />);
    const frame = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' && n.props?.testID === 'phone-mockup-frame'
    );
    expect(frame.length).toBeGreaterThan(0);
  });

  it('renders two product cards in the screen area', () => {
    const { UNSAFE_root } = render(<PhoneMockup />);
    const cards = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' &&
        typeof n.props?.testID === 'string' &&
        n.props.testID.startsWith('phone-mockup-product-')
    );
    expect(cards.length).toBe(2);
  });

  it('renders the winner badge in emerald', () => {
    const { UNSAFE_root } = render(<PhoneMockup />);
    const badge = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' && n.props?.testID === 'phone-mockup-winner-badge'
    );
    expect(badge.length).toBeGreaterThan(0);
    expect(badge[0].props.fill).toBe('#10B981');
  });

  it('renders the emerald glow ring around the winner', () => {
    const { UNSAFE_root } = render(<PhoneMockup />);
    const glow = UNSAFE_root.findAll(
      (n: any) =>
        typeof n.type === 'string' && n.props?.testID === 'phone-mockup-glow'
    );
    expect(glow.length).toBeGreaterThan(0);
  });

  it('respects size prop', () => {
    const { UNSAFE_root } = render(<PhoneMockup size={400} />);
    const svgs = UNSAFE_root.findAllByType('Svg' as any);
    expect(svgs[0].props.width).toBe(400);
  });
});
