/**
 * Step06Age — Phase 2 Task 14.
 *
 * Cohort key #2 — must match cohort_priors.json keys exactly per CLAUDE.md
 * cohort match contract: '18-24', '25-34', '35-44', '45-54', '55+'.
 * "Prefer not to say" link clears age_group server-side. See § 2 row 6.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, typography, radii } from '../../theme';
import { OnboardingAgeGroup } from './types';

interface Props {
  value?: OnboardingAgeGroup;
  onChange: (age: OnboardingAgeGroup) => void;
  onSkip: () => void;
}

const AGE_GROUPS: OnboardingAgeGroup[] = ['18-24', '25-34', '35-44', '45-54', '55+'];

export function Step06Age({ value, onChange, onSkip }: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('onboarding.s6.title')}</Text>

      <View style={styles.list}>
        {AGE_GROUPS.map((age) => {
          const selected = value === age;
          return (
            <TouchableOpacity
              key={age}
              testID={`age-${age}`}
              onPress={() => onChange(age)}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              style={[styles.card, selected && styles.cardSelected]}
            >
              <Text style={[styles.cardLabel, selected && styles.cardLabelSelected]}>
                {age}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      <TouchableOpacity
        testID="age-prefer-not-to-say"
        onPress={onSkip}
        accessibilityRole="link"
        style={styles.skipWrap}
      >
        <Text style={styles.skipText}>{t('onboarding.s6.prefer_not_to_say')}</Text>
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
