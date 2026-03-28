import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, radii, typography } from '../theme';

interface ComparisonCounterProps {
  used: number;
  total: number;
}

export function ComparisonCounter({ used, total }: ComparisonCounterProps) {
  const { t } = useTranslation();
  if (used === 0) return null;

  const isWarning = used >= total - 1; // Last free or exhausted

  return (
    <View style={[styles.pill, isWarning && styles.pillWarning]}>
      <Text style={[styles.text, isWarning && styles.textWarning]}>
        {t('home.freeCounter', { used, total })}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.md,
    borderRadius: radii.chip,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
    alignSelf: 'flex-start',
  },
  pillWarning: {
    backgroundColor: colors.accentLight,
    borderColor: colors.accent,
  },
  text: {
    ...typography.small,
    color: colors.text.secondary,
  },
  textWarning: {
    color: colors.accent,
    fontWeight: '600',
  },
});
