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
import { ShieldCheck, Zap, Sparkles } from 'lucide-react-native';
import { OptionRow } from '../../components/primitives/OptionRow';
import { colors, spacing, typography } from '../../theme';
import { OnboardingBrandAttitude } from './types';

interface Props {
  value?: OnboardingBrandAttitude;
  onChange: (b: OnboardingBrandAttitude) => void;
}

// F-S2.W2.hotfix (task #38): per-attitude lucide-react-native icons
// inside the icon-circle slot. Ahmed's W2 device walk caught the
// empty circles on Step10 — my W2 ship shipped OptionRow icon-circle
// rows with NO `icon` field (label+sub only). The icon mapping
// matches the brand-attitude semantics:
//   - brand_loyal    → ShieldCheck (trust + name protection)
//   - function_first → Zap (function-first power)
//   - best_of_both   → Sparkles (balance / nuanced pick)
// All 3 verified as lucide-react-native@1.14.0 exports.
const ICON_SIZE = 20;
const ICON_STROKE = 2;
function attitudeIcon(key: OnboardingBrandAttitude, color: string): React.ReactNode {
  switch (key) {
    case 'brand_loyal':
      return <ShieldCheck size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'function_first':
      return <Zap size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'best_of_both':
      return <Sparkles size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    // trust_known_brands is cohort-derived (NOT user-pickable here)
    // per qaren-cohort skill rule — fall through to empty so the
    // type-narrowed switch stays exhaustive without rendering a
    // glyph if the value somehow leaks in.
    case 'trust_known_brands':
    default:
      return null;
  }
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
        {ATTITUDES.map((a) => {
          const active = value === a.value;
          // Active row's circle bg flips to accentLight; icon glyph
          // adopts accentDark to maintain stroke contrast — same
          // contract as Step08Priorities lucide glyphs.
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
