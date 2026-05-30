/**
 * Step09Budget — Phase 2 Task 15 + Bundle C § 3a / § 3c.
 *
 * 5 budget tier cards with general-guidance BHD ranges (default
 * `other_light` sub-scale per spec § 3e). Per-category re-anchoring
 * happens server-side via PRICE_TIERS_BY_CATEGORY and is invisible
 * to the user — the picker only shows general guidance.
 *
 * Editorial restraint per spec § 3c: premium / luxury / top_tier carry
 * a subtle dark hairline accent; top_tier label uses the heaviest
 * available font weight (Geist-Bold; spec calls for "Geist Display
 * Medium" — see Bundle C deviation note in BudgetPicker.tsx).
 *
 * Bundle E S2.W2 — JSX-DEVIATION NOTE.
 * Step09 intentionally does NOT use the OptionRow primitive that the
 * rest of W2 standardizes on (Step04 / Step08 / Step10 / Step11). Per
 * dispatcher ruling A from W2 kickoff:
 *   - JSX OnboardingScreen.jsx has NO Step09 reference. Bundle C
 *     postdates the Claude-Design JSX kit. JSX-wins doctrine doesn't
 *     fire here because there's no JSX to defer to.
 *   - Bundle C § 3c specifies the editorial-dark left-border hairline
 *     accent on premium / luxury / top_tier rows + Geist-Bold heavy
 *     weight on top_tier — these are deliberate brand-differentiation
 *     signals Ahmed approved at Bundle C ship.
 *   - Folding these into OptionRow would accrete one-screen-only
 *     surface area on a primitive shared with non-budget screens.
 *
 * The bespoke TouchableOpacity card layout therefore stays. Future
 * audits surfacing "why doesn't Step09 use OptionRow?" should land
 * here in git blame and find this note.
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';

import { colors, spacing, typography, radii } from '../../theme';
import { OnboardingBudget } from './types';

interface Props {
  value?: OnboardingBudget;
  onChange: (b: OnboardingBudget) => void;
}

interface BudgetRow {
  value: OnboardingBudget;
  labelKey: string;
  rangeKey: string;
  editorial: boolean;
  heavy: boolean;
}

const BUDGETS: BudgetRow[] = [
  { value: 'budget',   labelKey: 'onboarding.s9.budget',   rangeKey: 'onboarding.s9.budget_range',   editorial: false, heavy: false },
  { value: 'mid',      labelKey: 'onboarding.s9.mid',      rangeKey: 'onboarding.s9.mid_range',      editorial: false, heavy: false },
  { value: 'premium',  labelKey: 'onboarding.s9.premium',  rangeKey: 'onboarding.s9.premium_range',  editorial: true,  heavy: false },
  { value: 'luxury',   labelKey: 'onboarding.s9.luxury',   rangeKey: 'onboarding.s9.luxury_range',   editorial: true,  heavy: false },
  { value: 'top_tier', labelKey: 'onboarding.s9.top_tier', rangeKey: 'onboarding.s9.top_tier_range', editorial: true,  heavy: true  },
];

export function Step09Budget({ value, onChange }: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('onboarding.s9.title')}</Text>

      <View style={styles.list}>
        {BUDGETS.map((b) => {
          const selected = value === b.value;
          return (
            <TouchableOpacity
              key={b.value}
              testID={`budget-${b.value}`}
              onPress={() => onChange(b.value)}
              accessibilityRole="button"
              accessibilityState={{ selected }}
              style={[
                styles.card,
                b.editorial && styles.cardEditorial,
                selected && styles.cardSelected,
              ]}
            >
              <Text
                testID={`budget-${b.value}-label`}
                style={[
                  styles.cardLabel,
                  selected && styles.cardLabelSelected,
                  b.heavy && styles.cardLabelHeavy,
                ]}
              >
                {t(b.labelKey)}
              </Text>
              <Text style={styles.cardRange}>{t(b.rangeKey)}</Text>
            </TouchableOpacity>
          );
        })}
      </View>

      <Text testID="s9-caveat" style={styles.caveat}>
        {t('onboarding.s9.caveat')}
      </Text>
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
    borderLeftWidth: 2,
    borderColor: 'transparent',
  },
  cardEditorial: {
    borderLeftWidth: 3,
    borderLeftColor: colors.editorialDark,
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
  cardLabelHeavy: {
    fontFamily: 'Geist-Bold',
    fontWeight: '700',
  },
  cardRange: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  caveat: {
    ...typography.caption,
    color: colors.text.secondary,
    marginTop: spacing.sm,
    textAlign: 'center',
  },
});
