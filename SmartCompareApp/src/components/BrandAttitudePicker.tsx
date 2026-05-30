// SmartCompareApp/src/components/BrandAttitudePicker.tsx
//
// Bundle E S2.X3 REWRITE — OptionRow icon-circle pattern matching
// Step10BrandAttitude onboarding rhythm. Replaces the prior Bundle A
// bordered-card layout so EditPreferencesFlow visually inherits the
// W2.hotfix icon-circle treatment (be5cf01).
//
// Per memory feedback_compose_vs_rewrite_phrasing.md this is a REWRITE
// (not compose) — the prior layout was bespoke TouchableOpacity cards.
// The new layout is a vertical OptionRow stack carrying both `label`
// and `sub` (subtitle copy preserved from Bundle A: brand_loyal_sub etc.).
//
// User-pickable subset (3 of 4 — `trust_known_brands` is cohort-derived
// per qaren-cohort skill and stays unexposed). testID `brand-{value}`
// + the 3-enum `BrandAttitudeValue` literal both preserved verbatim.
//
// Per-attitude icon mapping is intentionally identical to Step10:
//   brand_loyal → ShieldCheck (trust + name protection)
//   function_first → Zap (function-first power)
//   best_of_both → Sparkles (balance / nuanced pick)

import React from 'react';
import { View, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { ShieldCheck, Zap, Sparkles } from 'lucide-react-native';
import { OptionRow } from './primitives/OptionRow';
import { colors, spacing } from '../theme';

export type BrandAttitudeValue = 'brand_loyal' | 'function_first' | 'best_of_both';

const ATTITUDES: { value: BrandAttitudeValue; labelKey: string; subKey: string }[] = [
  { value: 'brand_loyal',    labelKey: 'onboarding.s10.brand_loyal',    subKey: 'onboarding.s10.brand_loyal_sub' },
  { value: 'function_first', labelKey: 'onboarding.s10.function_first', subKey: 'onboarding.s10.function_first_sub' },
  { value: 'best_of_both',   labelKey: 'onboarding.s10.best_of_both',   subKey: 'onboarding.s10.best_of_both_sub' },
];

const ICON_SIZE = 20;
const ICON_STROKE = 2;

function attitudeIcon(key: BrandAttitudeValue, color: string): React.ReactNode {
  switch (key) {
    case 'brand_loyal':
      return <ShieldCheck size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'function_first':
      return <Zap size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'best_of_both':
      return <Sparkles size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
  }
}

interface Props {
  value?: BrandAttitudeValue;
  onChange: (b: BrandAttitudeValue) => void;
}

export default function BrandAttitudePicker({ value, onChange }: Props) {
  const { t } = useTranslation();

  return (
    <View style={styles.list}>
      {ATTITUDES.map((a) => {
        const active = value === a.value;
        const iconColor = active ? colors.accentDark : colors.text.primary;
        return (
          <OptionRow
            key={a.value}
            testID={`brand-${a.value}`}
            option={{
              key: a.value,
              label: t(a.labelKey),
              sub: t(a.subKey),
              icon: attitudeIcon(a.value, iconColor),
            }}
            active={active}
            onToggle={() => onChange(a.value)}
            style="icon-circle"
          />
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  list: {
    gap: spacing.sm,
  },
});
