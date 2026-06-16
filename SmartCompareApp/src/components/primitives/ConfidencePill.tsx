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
  label: React.ReactNode;
  level: Level;
  testID?: string;
  /**
   * Per-pill dot testID. Defaults to the primitive's `confidence-pill-dot`
   * contract (consumed by `__tests__/primitives/ConfidencePill.test.tsx`).
   * Composite rows with multiple pills pass a unique hook so each dot is
   * individually queryable.
   */
  dotTestID?: string;
}

const DOT_COLOR: Record<Level, string> = {
  high: colors.accent, // emerald #10B981
  medium: colors.warning, // amber #F59E0B
  low: colors.text.secondary, // muted gray
};

export function ConfidencePill({ label, level, testID, dotTestID = 'confidence-pill-dot' }: Props) {
  return (
    <View style={styles.pill} testID={testID}>
      <View
        style={[styles.dot, { backgroundColor: DOT_COLOR[level] }]}
        testID={dotTestID}
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
    borderWidth: 1,
    borderColor: colors.border.light,
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
