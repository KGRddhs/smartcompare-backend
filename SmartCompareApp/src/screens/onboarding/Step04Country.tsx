/**
 * Step04Country — Phase 2 Task 14.
 *
 * 6 GCC flag cards. If country===BH, conditional second question slides in:
 * "Which area?" (Capital / Muharraq / Northern / Southern). See design spec
 * § 2 row 4. Cohort key #1 + GCC-native positioning.
 *
 * Backend writes to `users.demographics_profile.country` and `.governorate`
 * via PUT /api/v1/auth/demographics. Values must match cohort_priors.json
 * exact case ('Capital', not 'capital') per CLAUDE.md cohort match rules.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { colors, spacing, typography, radii } from '../../theme';
import { OnboardingCountry, OnboardingGovernorate } from './types';

interface Props {
  country?: OnboardingCountry;
  governorate?: OnboardingGovernorate;
  onChangeCountry: (c: OnboardingCountry) => void;
  onChangeGovernorate: (g: OnboardingGovernorate) => void;
}

interface CountryRow {
  code: OnboardingCountry;
  flag: string;
  labelKey: string;
}

const COUNTRIES: CountryRow[] = [
  { code: 'BH', flag: '🇧🇭', labelKey: 'onboarding.s4.bahrain' },
  { code: 'SA', flag: '🇸🇦', labelKey: 'onboarding.s4.saudi_arabia' },
  { code: 'AE', flag: '🇦🇪', labelKey: 'onboarding.s4.uae' },
  { code: 'KW', flag: '🇰🇼', labelKey: 'onboarding.s4.kuwait' },
  { code: 'QA', flag: '🇶🇦', labelKey: 'onboarding.s4.qatar' },
  { code: 'OM', flag: '🇴🇲', labelKey: 'onboarding.s4.oman' },
];

const GOVERNORATES: OnboardingGovernorate[] = [
  'Capital',
  'Muharraq',
  'Northern',
  'Southern',
];

export function Step04Country({
  country,
  governorate,
  onChangeCountry,
  onChangeGovernorate,
}: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('onboarding.s4.title')}</Text>

      <View style={styles.list}>
        {COUNTRIES.map((c) => {
          const selected = country === c.code;
          return (
            <TouchableOpacity
              key={c.code}
              testID={`country-${c.code}`}
              onPress={() => onChangeCountry(c.code)}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              style={[styles.card, selected && styles.cardSelected]}
            >
              <Text style={styles.flag}>{c.flag}</Text>
              <Text style={[styles.cardLabel, selected && styles.cardLabelSelected]}>
                {t(c.labelKey)}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {country === 'BH' ? (
        <View style={styles.subQuestion}>
          <Text style={styles.subTitle}>{t('onboarding.s4.gov_title')}</Text>
          <View style={styles.govRow}>
            {GOVERNORATES.map((g) => {
              const selected = governorate === g;
              return (
                <TouchableOpacity
                  key={g}
                  testID={`gov-${g}`}
                  onPress={() => onChangeGovernorate(g)}
                  accessibilityRole="button"
                  accessibilityState={{ selected }}
                  style={[styles.govChip, selected && styles.govChipSelected]}
                >
                  <Text
                    style={[styles.govChipText, selected && styles.govChipTextSelected]}
                  >
                    {t(`onboarding.s4.gov_${g.toLowerCase()}`)}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>
        </View>
      ) : null}
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
    flexDirection: 'row',
    alignItems: 'center',
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
  flag: {
    fontSize: 28,
    // marginEnd auto-flips with writing direction so the gap stays
    // between the flag and its country label under both LTR and RTL.
    marginEnd: spacing.md,
  },
  cardLabel: {
    ...typography.title,
    color: colors.text.primary,
  },
  cardLabelSelected: {
    color: colors.text.primary,
  },
  subQuestion: {
    marginTop: spacing.xl,
  },
  subTitle: {
    ...typography.title,
    color: colors.text.primary,
    marginBottom: spacing.md,
  },
  govRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  govChip: {
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    borderRadius: radii.chip,
    borderWidth: 1,
    borderColor: colors.border.medium,
    backgroundColor: colors.bg.primary,
  },
  govChipSelected: {
    backgroundColor: colors.cta.primary,
    borderColor: colors.cta.primary,
  },
  govChipText: {
    ...typography.body,
    color: colors.text.primary,
  },
  govChipTextSelected: {
    color: colors.cta.onPrimary,
  },
});
