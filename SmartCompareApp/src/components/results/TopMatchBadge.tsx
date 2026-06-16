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
import { Star } from 'lucide-react-native';

import { colors, spacing, radii } from '../../theme';

export interface TopMatchBadgeProps {
  testID?: string;
}

export function TopMatchBadge({ testID = 'top-match-badge' }: TopMatchBadgeProps) {
  const { t } = useTranslation();
  return (
    <View style={styles.pill} testID={testID}>
      {/* Phase 4.4 — leading ★ per the "UI Kit — Mobile Results" mockup
          (emerald-tinted pill, uppercase label). */}
      <Star size={13} color={colors.accentDark} fill={colors.accentDark} />
      <Text style={styles.label}>{t('results.topMatch', { defaultValue: 'Top match' })}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: 6,
    backgroundColor: colors.accentLight,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radii.chip,
  },
  label: {
    color: colors.accentDark,
    fontWeight: '600',
    fontSize: 11,
    lineHeight: 11 * 1.4,
    letterSpacing: 1.1,
    textTransform: 'uppercase',
  },
});

export default TopMatchBadge;
