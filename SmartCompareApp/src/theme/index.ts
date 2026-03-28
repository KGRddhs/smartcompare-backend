import { StyleSheet } from 'react-native';

export const colors = {
  bg: {
    primary: '#FFFFFF',
    secondary: '#F8F8FA',
  },
  text: {
    primary: '#1A1A1E',
    secondary: '#6B7280',
    placeholder: '#9CA3AF',
  },
  accent: '#10B981',
  accentLight: '#ECFDF5',
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
} as const;

export const typography = {
  display: {
    fontSize: 28,
    fontWeight: '700' as const,
    lineHeight: 28 * 1.5,
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
  caption: {
    fontSize: 13,
    fontWeight: '400' as const,
    lineHeight: 13 * 1.5,
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
