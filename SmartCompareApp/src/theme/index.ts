import { StyleSheet } from 'react-native';

export const colors = {
  bg: {
    primary: '#FFFFFF',
    secondary: '#F8F8FA',
    inverse: '#0A0A0B',
  },
  text: {
    primary: '#0A0A0B',
    secondary: '#6B7280',
    placeholder: '#9CA3AF',
    onInverse: '#FFFFFF',
  },
  cta: {
    primary: '#0A0A0B',
    onPrimary: '#FFFFFF',
  },
  accent: '#10B981',
  accentDark: '#059669',
  accentLight: '#ECFDF5',
  accentGlow: 'rgba(16,185,129,0.20)',
  // Bundle C (spec § 3c) — restrained dark accent for premium / luxury /
  // top_tier picker cards. Editorial only — not used for state or CTA.
  // Sits on bg.secondary as a hairline border, never as full fill or glow.
  editorialDark: '#1A1A1A',
  destructive: '#EF4444',
  warning: '#F59E0B',
  border: {
    light: '#E5E7EB',
    medium: '#D1D5DB',
  },
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  base: 16,
  lg: 20,
  xl: 24,
  '2xl': 32,
  '3xl': 48,
} as const;

export const radii = {
  card: 16,
  button: 12,
  chip: 999,
  input: 12,
  hero: 24,
} as const;

export const typography = {
  hero: {
    fontSize: 36,
    fontWeight: '700' as const,
    lineHeight: 36 * 1.2,
    letterSpacing: 36 * -0.02,
  },
  display: {
    fontSize: 28,
    fontWeight: '700' as const,
    lineHeight: 28 * 1.3,
    letterSpacing: 28 * -0.01,
  },
  title: {
    fontSize: 20,
    fontWeight: '600' as const,
    lineHeight: 20 * 1.5,
  },
  body: {
    fontSize: 16,
    fontWeight: '400' as const,
    lineHeight: 16 * 1.5,
  },
  bodyEmphasis: {
    fontSize: 16,
    fontWeight: '600' as const,
    lineHeight: 16 * 1.5,
  },
  caption: {
    fontSize: 13,
    fontWeight: '400' as const,
    lineHeight: 13 * 1.5,
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: '600' as const,
    lineHeight: 11 * 1.4,
    letterSpacing: 11 * 0.10,
    textTransform: 'uppercase' as const,
  },
  small: {
    fontSize: 11,
    fontWeight: '400' as const,
    lineHeight: 11 * 1.5,
  },
} as const;

// Arabic line-height multiplier (1.7x vs 1.5x for English)
export const arabicLineHeightMultiplier = 1.7 / 1.5;

export const shadows = {
  card: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 3,
    elevation: 2,
  },
} as const;
