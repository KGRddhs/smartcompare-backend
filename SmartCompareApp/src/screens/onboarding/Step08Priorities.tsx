/**
 * Step08Priorities — Phase 2 Task 15.
 *
 * 1-3 of 8 chips. Personalization signal that feeds scoring ±30% cap.
 * See design spec § 2 row 8 + CLAUDE.md VALID_PRIORITIES (the 8 base
 * keys; cohort-derived enums come from cohort priors not user input).
 *
 * Backend wiring goes through PUT /api/v1/auth/preferences in Task 24.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, typography, radii } from '../../theme';

const PRIORITIES = [
  'price',
  'quality',
  'brand_reputation',
  'durability',
  'latest_features',
  'ease_of_use',
  'eco_friendly',
  'health_safety',
] as const;

const MAX_SELECTIONS = 3;

interface Props {
  value: string[];
  onChange: (priorities: string[]) => void;
}

export function Step08Priorities({ value, onChange }: Props) {
  const { t } = useTranslation();

  const toggle = (key: string) => {
    if (value.includes(key)) {
      onChange(value.filter((k) => k !== key));
      return;
    }
    if (value.length >= MAX_SELECTIONS) {
      // Cap reached — selecting another would orphan the user's intent.
      // Silent block matches the "engaging, never scary" copy contract;
      // the design spec doesn't surface a tooltip here.
      return;
    }
    onChange([...value, key]);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('onboarding.s8.title')}</Text>
      <Text style={styles.subtitle}>
        {t('onboarding.s8.subtitle', { defaultValue: 'Pick up to 3' })}
      </Text>

      <View style={styles.chipRow}>
        {PRIORITIES.map((p) => {
          const selected = value.includes(p);
          return (
            <TouchableOpacity
              key={p}
              testID={`priority-${p}`}
              onPress={() => toggle(p)}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              style={[styles.chip, selected && styles.chipSelected]}
            >
              <Text style={[styles.chipText, selected && styles.chipTextSelected]}>
                {t(`onboarding.s8.priority_${p}`)}
              </Text>
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
    marginBottom: spacing.sm,
  },
  subtitle: {
    ...typography.body,
    color: colors.text.secondary,
    marginBottom: spacing.xl,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  chip: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radii.chip,
    borderWidth: 1,
    borderColor: colors.border.medium,
    backgroundColor: colors.bg.primary,
  },
  chipSelected: {
    backgroundColor: colors.cta.primary,
    borderColor: colors.cta.primary,
  },
  chipText: {
    ...typography.body,
    color: colors.text.primary,
  },
  chipTextSelected: {
    color: colors.cta.onPrimary,
  },
});
