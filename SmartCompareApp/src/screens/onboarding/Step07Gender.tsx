/**
 * Step07Gender — Phase 2 Task 14.
 *
 * Cohort key #3 — exact strings ('Male', 'Female') per CLAUDE.md cohort
 * match contract. "Prefer not to say" link clears gender server-side.
 * See § 2 row 7.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, typography, radii } from '../../theme';
import { OnboardingGender } from './types';

interface Props {
  value?: OnboardingGender;
  onChange: (g: OnboardingGender) => void;
  onSkip: () => void;
}

const GENDERS: { value: OnboardingGender; labelKey: string }[] = [
  { value: 'Male', labelKey: 'onboarding.s7.male' },
  { value: 'Female', labelKey: 'onboarding.s7.female' },
];

export function Step07Gender({ value, onChange, onSkip }: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('onboarding.s7.title')}</Text>

      <View style={styles.list}>
        {GENDERS.map((g) => {
          const selected = value === g.value;
          return (
            <TouchableOpacity
              key={g.value}
              testID={`gender-${g.value}`}
              onPress={() => onChange(g.value)}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              style={[styles.card, selected && styles.cardSelected]}
            >
              <Text style={[styles.cardLabel, selected && styles.cardLabelSelected]}>
                {t(g.labelKey)}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      <TouchableOpacity
        testID="gender-prefer-not-to-say"
        onPress={onSkip}
        accessibilityRole="link"
        style={styles.skipWrap}
      >
        <Text style={styles.skipText}>{t('onboarding.s7.prefer_not_to_say')}</Text>
      </TouchableOpacity>
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
  },
  cardLabelSelected: {
    color: colors.text.primary,
  },
  skipWrap: {
    marginTop: spacing.xl,
    alignItems: 'center',
    paddingVertical: spacing.md,
  },
  skipText: {
    ...typography.body,
    color: colors.text.secondary,
  },
});
