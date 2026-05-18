// SmartCompareApp/src/components/BudgetPicker.tsx
//
// Stateless 1-of-5 budget tier cards (Bundle C spec § 3a + 3c).
// Backend `_detect_price_tier()` mirror — 5 semantic tiers anchored
// per-category server-side (PRICE_TIERS_BY_CATEGORY).
//
// Editorial restraint: premium / luxury / top_tier get a hairline
// editorial-dark accent + heavier font weight on top_tier. NO gaudy
// gold, NO border glow, NO icon — pure typography + restraint per
// design § 3c.
//
// `BudgetValue` mirrors the project-wide literal in `src/types`; the
// local re-export here is for backwards-compat with existing call sites.

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';

import { colors, spacing, typography, radii } from '../theme';
import type { BudgetValue } from '../types';
export type { BudgetValue };

interface Tier {
  value: BudgetValue;
  labelKey: string;
  rangeKey: string;
  editorial: boolean;
  heavy: boolean;
}

const BUDGETS: Tier[] = [
  { value: 'budget',   labelKey: 'onboarding.s9.budget',   rangeKey: 'onboarding.s9.budget_range',   editorial: false, heavy: false },
  { value: 'mid',      labelKey: 'onboarding.s9.mid',      rangeKey: 'onboarding.s9.mid_range',      editorial: false, heavy: false },
  { value: 'premium',  labelKey: 'onboarding.s9.premium',  rangeKey: 'onboarding.s9.premium_range',  editorial: true,  heavy: false },
  { value: 'luxury',   labelKey: 'onboarding.s9.luxury',   rangeKey: 'onboarding.s9.luxury_range',   editorial: true,  heavy: false },
  { value: 'top_tier', labelKey: 'onboarding.s9.top_tier', rangeKey: 'onboarding.s9.top_tier_range', editorial: true,  heavy: true  },
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
            style={[
              styles.card,
              b.editorial && styles.cardEditorial,
              selected && styles.cardSelected,
            ]}
          >
            <Text
              testID={`budget-${b.value}-label`}
              style={[styles.cardLabel, b.heavy && styles.cardLabelHeavy]}
            >
              {t(b.labelKey)}
            </Text>
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
    borderLeftWidth: 2,
    borderColor: 'transparent',
    marginBottom: spacing.sm,
  },
  // Bundle C § 3c — premium / luxury / top_tier: subtle dark hairline on
  // the leading edge only. Stays editorial; never reads as a state border.
  cardEditorial: {
    borderLeftWidth: 3,
    borderLeftColor: colors.editorialDark,
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
  // Bundle C § 3c — top_tier reads with a heavier label weight. Spec
  // calls for "Geist Display Medium"; until a display-weight asset is
  // added to assets/fonts/, we use Geist-Bold (the heaviest variant
  // already bundled). Flag in B.9 cleanup if a display weight is added.
  cardLabelHeavy: {
    fontFamily: 'Geist-Bold',
    fontWeight: '700',
  },
  cardRange: {
    ...typography.caption,
    color: colors.text.secondary,
  },
});
