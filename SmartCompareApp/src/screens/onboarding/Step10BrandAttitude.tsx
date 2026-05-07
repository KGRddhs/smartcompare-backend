/**
 * Step10BrandAttitude — Phase 2 Task 15.
 *
 * 3 brand attitude cards: brand_loyal / function_first / best_of_both.
 * (`trust_known_brands` is a cohort-derived value, not a user-pickable
 * option here.) Final personalization key. See design spec § 2 row 10.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, typography, radii } from '../../theme';
import { OnboardingBrandAttitude } from './types';

interface Props {
  value?: OnboardingBrandAttitude;
  onChange: (b: OnboardingBrandAttitude) => void;
}

const ATTITUDES: { value: OnboardingBrandAttitude; labelKey: string; subKey: string }[] = [
  { value: 'brand_loyal',    labelKey: 'onboarding.s10.brand_loyal',    subKey: 'onboarding.s10.brand_loyal_sub' },
  { value: 'function_first', labelKey: 'onboarding.s10.function_first', subKey: 'onboarding.s10.function_first_sub' },
  { value: 'best_of_both',   labelKey: 'onboarding.s10.best_of_both',   subKey: 'onboarding.s10.best_of_both_sub' },
];

export function Step10BrandAttitude({ value, onChange }: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('onboarding.s10.title')}</Text>

      <View style={styles.list}>
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
              <Text style={[styles.cardLabel, selected && styles.cardLabelSelected]}>
                {t(a.labelKey)}
              </Text>
              <Text style={styles.cardSub}>{t(a.subKey)}</Text>
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
  cardSub: {
    ...typography.caption,
    color: colors.text.secondary,
  },
});
