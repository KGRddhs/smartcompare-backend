/**
 * Step10BrandAttitude — Bundle E S2.W2 REWRITE.
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/OnboardingScreen.jsx
 * Cal-AI-Lite OptionRow icon-circle rhythm. No dedicated JSX file exists
 * for s10 — design doc § 3.1 says all multi-option onboarding steps
 * inherit the OnboardingScreen.jsx OptionRow pattern (icon-circle row +
 * black-on-select Cal-AI inversion).
 *
 * Per memory feedback_compose_vs_rewrite_phrasing.md this is a REWRITE
 * (not compose) — the prior Bundle D layout was a bespoke card with no
 * OptionRow shared rhythm. Visual harmony with Step04 + Step08 + Step11
 * comes from a single primitive surface.
 *
 * 3 brand attitudes: brand_loyal / function_first / best_of_both.
 * `trust_known_brands` is cohort-derived (NOT user-pickable here) per
 * qaren-cohort skill rule. Final personalization key fed to scoring
 * ±30% cap.
 *
 * Test contract preserved (Step10BrandAttitude.test.tsx — 3 tests):
 *   - testID="brand-{brand_loyal|function_first|best_of_both}" forwarded
 *     to each OptionRow root
 *   - onChange(value) fires on row press
 *   - accessibilityState.selected mirrors active state
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { OptionRow } from '../../components/primitives/OptionRow';
import { colors, spacing, typography } from '../../theme';
import { OnboardingBrandAttitude } from './types';

interface Props {
  value?: OnboardingBrandAttitude;
  onChange: (b: OnboardingBrandAttitude) => void;
}

const ATTITUDES: {
  value: OnboardingBrandAttitude;
  labelKey: string;
  subKey: string;
}[] = [
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
        {ATTITUDES.map((a) => (
          <OptionRow
            key={a.value}
            testID={`brand-${a.value}`}
            option={{ key: a.value, label: t(a.labelKey), sub: t(a.subKey) }}
            active={value === a.value}
            onToggle={() => onChange(a.value)}
            style="icon-circle"
          />
        ))}
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
});
