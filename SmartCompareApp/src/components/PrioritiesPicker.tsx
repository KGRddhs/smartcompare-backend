// SmartCompareApp/src/components/PrioritiesPicker.tsx
//
// Stateless 1-of-3-from-8 priority chips. Body-only (no page title) so it
// can be reused from both the onboarding Step08 host and the Bundle A
// EditPreferencesFlow.

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, typography, radii } from '../theme';

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
  testIDPrefix?: string;
}

export default function PrioritiesPicker({ value, onChange, testIDPrefix = 'priority' }: Props) {
  const { t } = useTranslation();

  const toggle = (key: string) => {
    if (value.includes(key)) {
      onChange(value.filter((k) => k !== key));
      return;
    }
    if (value.length >= MAX_SELECTIONS) return;
    onChange([...value, key]);
  };

  return (
    <View>
      <Text style={styles.helper}>
        {t('preferences.priorities.helper', { defaultValue: 'Pick up to 3' })}
      </Text>
      <View style={styles.chipRow}>
        {PRIORITIES.map((p) => {
          const selected = value.includes(p);
          return (
            <TouchableOpacity
              key={p}
              testID={`${testIDPrefix}-${p}`}
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
  helper: {
    ...typography.body,
    color: colors.text.secondary,
    marginBottom: spacing.lg,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  chip: {
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderRadius: radii.chip,
    borderWidth: 1,
    borderColor: colors.border.medium,
    backgroundColor: colors.bg.primary,
    marginEnd: spacing.sm,
    marginBottom: spacing.sm,
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
