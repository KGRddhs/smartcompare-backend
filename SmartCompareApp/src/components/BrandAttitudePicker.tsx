// SmartCompareApp/src/components/BrandAttitudePicker.tsx
//
// Stateless 1-of-3 brand attitude radio cards. Matches the user-pickable
// subset of VALID_BRAND_ATTITUDE (`trust_known_brands` is cohort-derived
// only and intentionally not exposed here).

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, typography, radii } from '../theme';

export type BrandAttitudeValue = 'brand_loyal' | 'function_first' | 'best_of_both';

const ATTITUDES: { value: BrandAttitudeValue; labelKey: string; subKey: string }[] = [
  { value: 'brand_loyal',    labelKey: 'onboarding.s10.brand_loyal',    subKey: 'onboarding.s10.brand_loyal_sub' },
  { value: 'function_first', labelKey: 'onboarding.s10.function_first', subKey: 'onboarding.s10.function_first_sub' },
  { value: 'best_of_both',   labelKey: 'onboarding.s10.best_of_both',   subKey: 'onboarding.s10.best_of_both_sub' },
];

interface Props {
  value?: BrandAttitudeValue;
  onChange: (b: BrandAttitudeValue) => void;
}

export default function BrandAttitudePicker({ value, onChange }: Props) {
  const { t } = useTranslation();

  return (
    <View>
      {ATTITUDES.map((a) => {
        const selected = value === a.value;
        return (
          <TouchableOpacity
            key={a.value}
            testID={`brand-${a.value}`}
            onPress={() => onChange(a.value)}
            accessibilityRole="button"
            accessibilityState={{ selected }}
            style={[styles.card, selected && styles.cardSelected]}
          >
            <Text style={styles.cardLabel}>{t(a.labelKey)}</Text>
            <Text style={styles.cardSub}>{t(a.subKey)}</Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
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
  cardSub: {
    ...typography.caption,
    color: colors.text.secondary,
  },
});
