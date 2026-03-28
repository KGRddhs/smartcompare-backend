import { colors, spacing, radii, typography, shadows, arabicLineHeightMultiplier } from '../src/theme';

describe('Theme tokens', () => {
  it('has all required color groups', () => {
    expect(colors.bg.primary).toBe('#FFFFFF');
    expect(colors.bg.secondary).toBe('#F8F8FA');
    expect(colors.text.primary).toBe('#1A1A1E');
    expect(colors.text.secondary).toBe('#6B7280');
    expect(colors.text.placeholder).toBe('#9CA3AF');
    expect(colors.accent).toBe('#10B981');
    expect(colors.accentLight).toBe('#ECFDF5');
    expect(colors.destructive).toBe('#EF4444');
    expect(colors.warning).toBe('#F59E0B');
    expect(colors.border.light).toBe('#E5E7EB');
    expect(colors.border.medium).toBe('#D1D5DB');
  });

  it('has all spacing values', () => {
    expect(spacing.xs).toBe(4);
    expect(spacing.sm).toBe(8);
    expect(spacing.md).toBe(12);
    expect(spacing.base).toBe(16);
    expect(spacing.lg).toBe(20);
    expect(spacing.xl).toBe(24);
    expect(spacing['2xl']).toBe(32);
    expect(spacing['3xl']).toBe(48);
  });

  it('has all radii values', () => {
    expect(radii.card).toBe(16);
    expect(radii.button).toBe(12);
    expect(radii.chip).toBe(999);
    expect(radii.input).toBe(12);
  });

  it('has all typography presets with fontSize, fontWeight, lineHeight', () => {
    for (const key of ['display', 'title', 'body', 'caption', 'small'] as const) {
      const preset = typography[key];
      expect(preset.fontSize).toBeGreaterThan(0);
      expect(preset.fontWeight).toBeDefined();
      expect(preset.lineHeight).toBe(preset.fontSize * 1.5);
    }
  });

  it('has correct Arabic line-height multiplier', () => {
    expect(arabicLineHeightMultiplier).toBeCloseTo(1.7 / 1.5, 5);
  });

  it('has card shadow with required properties', () => {
    expect(shadows.card.shadowColor).toBe('#000');
    expect(shadows.card.shadowOffset).toEqual({ width: 0, height: 1 });
    expect(shadows.card.shadowOpacity).toBe(0.08);
    expect(shadows.card.shadowRadius).toBe(3);
    expect(shadows.card.elevation).toBe(2);
  });
});
