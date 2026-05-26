/**
 * ConfidencePill — Bundle E S0.3 primitive.
 *
 * Used on ResultsScreen below the verdict to communicate signal strength
 * (high / medium / low). Dot color is the load-bearing visual signal;
 * label is the human-readable explanation.
 *
 * Contract: __tests__/primitives/ConfidencePill.test.tsx
 *   - level='high'   → emerald dot (#10B981)
 *   - level='medium' → amber dot
 *   - level='low'    → muted gray dot
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing, radii } from '../../theme';

type Level = 'high' | 'medium' | 'low';

interface Props {
  label: string;
  level: Level;
  testID?: string;
}

const DOT_COLOR: Record<Level, string> = {
  high: colors.accent, // emerald #10B981
  medium: colors.warning, // amber #F59E0B
  low: colors.text.secondary, // muted gray
};

export function ConfidencePill({ label, level, testID }: Props) {
  return (
    <View style={styles.pill} testID={testID}>
      <View
        style={[styles.dot, { backgroundColor: DOT_COLOR[level] }]}
        testID="confidence-pill-dot"
      />
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.md,
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.chip,
    alignSelf: 'flex-start',
    gap: spacing.sm,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  label: {
    fontSize: 13,
    fontWeight: '500',
    color: colors.text.primary,
  },
});
