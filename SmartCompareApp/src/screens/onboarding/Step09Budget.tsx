/**
 * Step09Budget — Phase 2 Task 15.
 *
 * 3 budget tier cards with BHD ranges. Aligns with backend
 * `_get_price_tier()`: budget(<11), mid(11-57), premium(57-189).
 * See design spec § 2 row 9.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, typography, radii } from '../../theme';
import { OnboardingBudget } from './types';

interface Props {
  value?: OnboardingBudget;
  onChange: (b: OnboardingBudget) => void;
}

interface BudgetRow {
  value: OnboardingBudget;
  labelKey: string;
  rangeKey: string;
}

const BUDGETS: BudgetRow[] = [
  { value: 'budget', labelKey: 'onboarding.s9.budget', rangeKey: 'onboarding.s9.budget_range' },
  { value: 'mid', labelKey: 'onboarding.s9.mid', rangeKey: 'onboarding.s9.mid_range' },
  { value: 'premium', labelKey: 'onboarding.s9.premium', rangeKey: 'onboarding.s9.premium_range' },
];

export function Step09Budget({ value, onChange }: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('onboarding.s9.title')}</Text>

      <View style={styles.list}>
        {BUDGETS.map((b) => {
          const selected = value === b.value;
          return (
            <TouchableOpacity
              key={b.value}
              testID={`budget-${b.value}`}
              onPress={() => onChange(b.value)}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              style={[styles.card, selected && styles.cardSelected]}
            >
              <Text style={[styles.cardLabel, selected && styles.cardLabelSelected]}>
                {t(b.labelKey)}
              </Text>
              <Text style={styles.cardRange}>{t(b.rangeKey)}</Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.xl,
  },
  title: {
    ...typography.display,
    color: colors.text.primary,
    marginBottom: spacing.xl,
  },
  list: {
    gap: spacing.sm,
  },
  card: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    paddingVertical: spacing.lg,
    paddingHorizontal: spacing.lg,
    borderWidth: 2,
    borderColor: 'transparent',
  },
  cardSelected: {
    backgroundColor: colors.bg.primary,
    borderColor: colors.cta.primary,
  },
  cardLabel: {
    ...typography.title,
    color: colors.text.primary,
    marginBottom: spacing.xs,
  },
  cardLabelSelected: {
    color: colors.text.primary,
  },
  cardRange: {
    ...typography.caption,
    color: colors.text.secondary,
  },
});
