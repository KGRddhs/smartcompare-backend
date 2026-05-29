/**
 * Step11Attribution — Bundle E S2.W2 REWRITE.
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/OnboardingScreen.jsx
 * Cal-AI-Lite OptionRow icon-circle rhythm. No dedicated JSX file exists
 * for s11 — design doc § 3.1 says all multi-option onboarding steps
 * inherit the OnboardingScreen.jsx OptionRow pattern.
 *
 * Per memory feedback_compose_vs_rewrite_phrasing.md this is a REWRITE
 * (not compose) — visual harmony with Step04 + Step08 + Step10 comes
 * from a single primitive surface.
 *
 * 6 stacked sources: friend / instagram / tiktok / app_store / google /
 * other. Values MUST match POST /api/v1/auth/attribution Pydantic enum
 * exactly (`Literal['friend','instagram','tiktok','app_store','google',
 * 'other']`) per CLAUDE.md attribution endpoint contract.
 *
 * Test contract preserved (Step11Attribution.test.tsx — 4 tests):
 *   - testID="attr-{friend|instagram|tiktok|app_store|google|other}"
 *     forwarded to each OptionRow root
 *   - onChange(value) fires with the snake_case backend value
 *   - accessibilityState.selected mirrors active state
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { OptionRow } from '../../components/primitives/OptionRow';
import { colors, spacing, typography } from '../../theme';
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
        {SOURCES.map((s) => (
          <OptionRow
            key={s.value}
            testID={`attr-${s.value}`}
            option={{ key: s.value, label: t(s.labelKey) }}
            active={value === s.value}
            onToggle={() => onChange(s.value)}
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
