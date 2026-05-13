/**
 * TopMatchBadge — Bundle E Phase 3 Task 3.4.
 *
 * Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 3 + § Decision 5.
 *
 * One-word pill above the higher-scoring hero ring. Emerald background,
 * white text, no icon. Copy comes from i18n key `results.topMatch` only —
 * never hardcoded. Banned vocabulary ("Best Pick", "Winner", "Excellent",
 * etc.) is enforced at the catalog level by copy-policy.test.ts and at the
 * render level by the TopMatchBadge.test.tsx negative-assertion sweep.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';

import { colors, spacing, radii, typography } from '../../theme';

export interface TopMatchBadgeProps {
  testID?: string;
}

export function TopMatchBadge({ testID = 'top-match-badge' }: TopMatchBadgeProps) {
  const { t } = useTranslation();
  return (
    <View style={styles.pill} testID={testID}>
      <Text style={styles.label}>{t('results.topMatch', { defaultValue: 'Top match' })}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    alignSelf: 'flex-start',
    backgroundColor: colors.accent,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radii.chip,
  },
  label: {
    ...typography.body,
    color: colors.text.onInverse,
    fontWeight: '600',
    fontSize: 14,
    lineHeight: 18,
    letterSpacing: 0.2,
  },
});

export default TopMatchBadge;
