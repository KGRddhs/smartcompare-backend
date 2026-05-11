// SmartCompareApp/src/components/LifestylePicker.tsx
//
// Multi-select chip grid of 11 lifestyle tags. New for Bundle A §2 — the
// existing onboarding doesn't surface lifestyle picking; it gets seeded
// inferentially from cohort priors and only surfaces here for explicit
// editing.

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, typography, radii } from '../theme';

const LIFESTYLE_TAGS = [
  'fitness',
  'budget_conscious',
  'tech_enthusiast',
  'eco_conscious',
  'luxury_lover',
  'minimalist',
  'family_focused',
  'frequent_traveler',
  'home_cook',
  'outdoors',
  'creative',
] as const;

interface Props {
  value: string[];
  onChange: (next: string[]) => void;
}

export default function LifestylePicker({ value, onChange }: Props) {
  const { t } = useTranslation();

  const toggle = (key: string) => {
    if (value.includes(key)) {
      onChange(value.filter((k) => k !== key));
    } else {
      onChange([...value, key]);
    }
  };

  return (
    <View>
      <Text style={styles.helper}>
        {t('preferences.lifestyle.helper', { defaultValue: 'Pick any that fit' })}
      </Text>
      <View style={styles.chipRow}>
        {LIFESTYLE_TAGS.map((tag) => {
          const selected = value.includes(tag);
          return (
            <TouchableOpacity
              key={tag}
              testID={`lifestyle-${tag}`}
              onPress={() => toggle(tag)}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              style={[styles.chip, selected && styles.chipSelected]}
            >
              <Text style={[styles.chipText, selected && styles.chipTextSelected]}>
                {t(`preferences.lifestyle.${tag}`)}
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
