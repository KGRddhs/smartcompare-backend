// SmartCompareApp/src/components/LifestylePicker.tsx
//
// Bundle E S2.X3 REWRITE — OptionRow icon-circle pattern. Lifestyle
// multi-select has no onboarding counterpart (cohort-seeded
// inferentially; surfaces here only for explicit editing), so this
// picker adopts the W2 icon-circle rhythm independently rather than
// mirroring a specific Step.
//
// Per memory feedback_compose_vs_rewrite_phrasing.md this is a REWRITE
// (not compose) — the prior layout was a wrapping chip grid. The new
// layout is a vertical OptionRow stack where each row is a multi-select
// toggle (`active` boolean drives Cal-AI black-on-select inversion).
//
// testID `lifestyle-{tag}` + the 11-tag literal list + multi-select
// semantics (add on tap when absent, remove on tap when present) are
// preserved verbatim so existing EditPreferencesFlow contract holds.
//
// Per-tag lucide icon mapping (all verified as lucide-react-native@1.14.0
// exports; new imports enumerated in __mocks__/lucide-react-native.ts):
//   fitness            → HeartPulse  (active body)
//   budget_conscious   → Coins       (frugal)
//   tech_enthusiast    → Cpu         (silicon)
//   eco_conscious      → Leaf        (green)
//   luxury_lover       → Gem         (premium)
//   minimalist         → Minus       (less is more)
//   family_focused     → Heart       (warmth)
//   frequent_traveler  → Plane       (journey)
//   home_cook          → ChefHat     (kitchen)
//   outdoors           → Mountain    (open air)
//   creative           → Palette     (expression)

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import {
  HeartPulse,
  Coins,
  Cpu,
  Leaf,
  Gem,
  Minus,
  Heart,
  Plane,
  ChefHat,
  Mountain,
  Palette,
} from 'lucide-react-native';
import { OptionRow } from './primitives/OptionRow';
import { colors, spacing, typography } from '../theme';

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

type LifestyleTag = (typeof LIFESTYLE_TAGS)[number];

const ICON_SIZE = 20;
const ICON_STROKE = 2;

function lifestyleIcon(tag: LifestyleTag, color: string): React.ReactNode {
  switch (tag) {
    case 'fitness':
      return <HeartPulse size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'budget_conscious':
      return <Coins size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'tech_enthusiast':
      return <Cpu size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'eco_conscious':
      return <Leaf size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'luxury_lover':
      return <Gem size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'minimalist':
      return <Minus size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'family_focused':
      return <Heart size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'frequent_traveler':
      return <Plane size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'home_cook':
      return <ChefHat size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'outdoors':
      return <Mountain size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'creative':
      return <Palette size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
  }
}

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
      <View style={styles.list}>
        {LIFESTYLE_TAGS.map((tag) => {
          const active = value.includes(tag);
          const iconColor = active ? colors.accentDark : colors.text.primary;
          return (
            <OptionRow
              key={tag}
              testID={`lifestyle-${tag}`}
              option={{
                key: tag,
                label: t(`preferences.lifestyle.${tag}`),
                icon: lifestyleIcon(tag, iconColor),
              }}
              active={active}
              onToggle={() => toggle(tag)}
              style="icon-circle"
            />
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
  list: {
    gap: spacing.sm,
  },
});
