import { colors, typography, radii, spacing } from '../../src/theme';

describe('theme tokens — Phase 1 black/emerald hybrid', () => {
  it('cta.primary is now black, not emerald', () => {
    expect(colors.cta.primary).toBe('#0A0A0B');
  });

  it('cta.onPrimary is white', () => {
    expect(colors.cta.onPrimary).toBe('#FFFFFF');
  });

  it('text.primary is deep black matching the logo', () => {
    expect(colors.text.primary).toBe('#0A0A0B');
  });

  it('text.onInverse is white for use on black surfaces', () => {
    expect(colors.text.onInverse).toBe('#FFFFFF');
  });

  it('bg.inverse is the black surface for hero/onboarding moments', () => {
    expect(colors.bg.inverse).toBe('#0A0A0B');
  });

  it('exposes accentGlow rgba for winner reveal', () => {
    expect(colors.accentGlow).toMatch(/rgba\(16,\s*185,\s*129,\s*0?\.20?\)/);
  });

  it('exposes accentDark for pressed/active states', () => {
    expect(colors.accentDark).toBe('#059669');
  });

  it('preserves accentLight winner card tint', () => {
    expect(colors.accentLight).toBe('#ECFDF5');
  });

  it('preserves accent emerald base (no breaking change)', () => {
    expect(colors.accent).toBe('#10B981');
  });

  it('typography.hero is 36pt Bold with -0.02em tracking', () => {
    expect(typography.hero.fontSize).toBe(36);
    expect(typography.hero.fontWeight).toBe('700');
    expect(typography.hero.letterSpacing).toBeCloseTo(-0.72, 2); // 36 * -0.02
  });

  it('typography.display has -0.01em tracking', () => {
    expect(typography.display.fontSize).toBe(28);
    expect(typography.display.fontWeight).toBe('700');
    expect(typography.display.letterSpacing).toBeCloseTo(-0.28, 2); // 28 * -0.01
  });

  it('typography.bodyEmphasis is 16pt SemiBold', () => {
    expect(typography.bodyEmphasis.fontSize).toBe(16);
    expect(typography.bodyEmphasis.fontWeight).toBe('600');
  });

  it('typography.eyebrow is 11pt SemiBold UPPERCASE +0.10em tracking', () => {
    expect(typography.eyebrow.fontSize).toBe(11);
    expect(typography.eyebrow.fontWeight).toBe('600');
    expect(typography.eyebrow.textTransform).toBe('uppercase');
    expect(typography.eyebrow.letterSpacing).toBeCloseTo(1.1, 2); // 11 * 0.10
  });

  it('radii.hero is 24', () => {
    expect(radii.hero).toBe(24);
  });

  it('preserves existing spacing scale', () => {
    expect(spacing.xs).toBe(4);
    expect(spacing['3xl']).toBe(48);
  });
});
