/**
 * Step04Country — Bundle E S2.W1 rewrite.
 *
 * REWRITE not compose — JSX OnboardingExtras.jsx s4 layout differs from
 * the prior bespoke flag-card grid: it uses OptionRow icon-circle (flag
 * emoji glyph + label + governorate sub line) and an emerald-accentWord
 * headline ("Where do you `shop`?") with a thin subtitle. Memory pin:
 * feedback_compose_vs_rewrite_phrasing.md.
 *
 * 6 GCC countries. If country===BH, conditional governorate sub-question
 * slides in (verbatim Capital/Muharraq/Northern/Southern keys for
 * cohort_priors.json exact-case match per CLAUDE.md cohort rules).
 *
 * Backend writes via PUT /api/v1/auth/demographics. Cohort key #1 + the
 * GCC-native positioning moment.
 *
 * testIDs preserved from the Phase 2 contract:
 *   - country-BH / -SA / -AE / -KW / -QA / -OM forwarded to each OptionRow
 *   - gov-Capital / -Muharraq / -Northern / -Southern on the gov chips
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import { OptionRow } from '../../components/primitives/OptionRow';
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
  // Per JSX, BH renders a governorate hint as the sub-line. Other GCC
  // countries get no sub for now (their region pickers don't exist yet).
  subKey?: string;
}

const COUNTRIES: CountryRow[] = [
  // BH leads — design choice (cohort #1, GCC-native positioning); the
  // governorate sub-line previews the conditional sub-question.
  {
    code: 'BH',
    flag: '🇧🇭',
    labelKey: 'onboarding.s4.bahrain',
    subKey: 'onboarding.s4.bh_sub',
  },
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
      {/* Headline — emerald-accentWord on "shop" per JSX OnbHeadline.
          Three nested Text spans so the middle word inherits the accent
          color without breaking the line as a whole. */}
      <Text style={styles.headline}>
        {t('onboarding.s4.title_before', { defaultValue: 'Where do you ' })}
        <Text style={styles.headlineAccent}>
          {t('onboarding.s4.title_accent', { defaultValue: 'shop' })}
        </Text>
        {t('onboarding.s4.title_after', { defaultValue: '?' })}
      </Text>

      <Text style={styles.subtitle}>
        {t('onboarding.s4.subtitle', {
          defaultValue:
            'Currency, retailers, and peer cohort all calibrate to your region.',
        })}
      </Text>

      <View style={styles.list}>
        {COUNTRIES.map((c) => {
          const selected = country === c.code;
          return (
            <OptionRow
              key={c.code}
              testID={`country-${c.code}`}
              option={{
                key: c.code,
                label: t(c.labelKey),
                icon: c.flag,
                // BH preview hint mirrors the governorate set from the
                // conditional sub-question below — sets expectation
                // BEFORE the user taps so the second-question reveal
                // feels continuous, not a surprise.
                sub: c.subKey
                  ? t(c.subKey, {
                      defaultValue: 'Capital, Muharraq, Northern, Southern',
                    })
                  : undefined,
              }}
              active={selected}
              onToggle={() => onChangeCountry(c.code)}
              style="icon-circle"
            />
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
                    style={[
                      styles.govChipText,
                      selected && styles.govChipTextSelected,
                    ]}
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
  // Headline + accent word — emerald accentWord on "shop" per
  // OnbHeadline JSX. Display typography for the surrounding text; the
  // accent span inherits sizing and only overrides color.
  headline: {
    ...typography.display,
    color: colors.text.primary,
    marginBottom: spacing.sm,
  },
  headlineAccent: {
    color: colors.accent,
  },
  subtitle: {
    ...typography.body,
    color: colors.text.secondary,
    marginBottom: spacing.xl,
  },
  list: {
    gap: spacing.sm,
  },
  // BH governorate sub-question chips. Unchanged from prior
  // implementation since this surface still wants a horizontal chip row
  // (no OptionRow rhythm needed — these are tiny picker-style targets
  // that fit better as chips per the JSX OnbGovChip pattern).
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
