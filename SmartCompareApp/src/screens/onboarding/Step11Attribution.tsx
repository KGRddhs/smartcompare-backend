/**
 * Step11Attribution — Phase 2 Task 15.
 *
 * 6 stacked cards: Friend / Instagram / TikTok / App Store / Google /
 * Other. Market-research signal. Backend route POST
 * /api/v1/auth/attribution lives in Task 8 (already shipped); the values
 * here MUST match its Pydantic enum exactly. See § 2 row 11.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, typography, radii } from '../../theme';
import { OnboardingAttributionSource } from './types';

interface Props {
  value?: OnboardingAttributionSource;
  onChange: (source: OnboardingAttributionSource) => void;
}

const SOURCES: { value: OnboardingAttributionSource; labelKey: string }[] = [
  { value: 'friend',    labelKey: 'onboarding.s11.friend' },
  { value: 'instagram', labelKey: 'onboarding.s11.instagram' },
  { value: 'tiktok',    labelKey: 'onboarding.s11.tiktok' },
  { value: 'app_store', labelKey: 'onboarding.s11.app_store' },
  { value: 'google',    labelKey: 'onboarding.s11.google' },
  { value: 'other',     labelKey: 'onboarding.s11.other' },
];

export function Step11Attribution({ value, onChange }: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('onboarding.s11.title')}</Text>

      <View style={styles.list}>
        {SOURCES.map((s) => {
          const selected = value === s.value;
          return (
            <TouchableOpacity
              key={s.value}
              testID={`attr-${s.value}`}
              onPress={() => onChange(s.value)}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              style={[styles.card, selected && styles.cardSelected]}
            >
              <Text style={[styles.cardLabel, selected && styles.cardLabelSelected]}>
                {t(s.labelKey)}
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
});
