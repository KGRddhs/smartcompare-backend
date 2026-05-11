// SmartCompareApp/src/components/BudgetPicker.tsx
//
// Stateless 1-of-3 budget tier cards (matches backend `_get_price_tier()`).

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, typography, radii } from '../theme';

export type BudgetValue = 'budget' | 'mid' | 'premium';

const BUDGETS: { value: BudgetValue; labelKey: string; rangeKey: string }[] = [
  { value: 'budget', labelKey: 'onboarding.s9.budget', rangeKey: 'onboarding.s9.budget_range' },
  { value: 'mid', labelKey: 'onboarding.s9.mid', rangeKey: 'onboarding.s9.mid_range' },
  { value: 'premium', labelKey: 'onboarding.s9.premium', rangeKey: 'onboarding.s9.premium_range' },
];

interface Props {
  value?: BudgetValue;
  onChange: (b: BudgetValue) => void;
}

export default function BudgetPicker({ value, onChange }: Props) {
  const { t } = useTranslation();

  return (
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
            <Text style={styles.cardLabel}>{t(b.labelKey)}</Text>
            <Text style={styles.cardRange}>{t(b.rangeKey)}</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  list: {},
  card: {
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.card,
    paddingVertical: spacing.lg,
    paddingHorizontal: spacing.lg,
    borderWidth: 2,
    borderColor: 'transparent',
    marginBottom: spacing.sm,
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
  cardRange: {
    ...typography.caption,
    color: colors.text.secondary,
  },
});
