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
import {
  Users,
  Camera,
  Music,
  ShoppingBag,
  Search,
  MoreHorizontal,
} from 'lucide-react-native';
import { OptionRow } from '../../components/primitives/OptionRow';
import { colors, spacing, typography } from '../../theme';
import { OnboardingAttributionSource } from './types';

interface Props {
  value?: OnboardingAttributionSource;
  onChange: (source: OnboardingAttributionSource) => void;
}

// F-S2.W2.hotfix (task #38): per-source lucide-react-native icons.
// Ahmed's W2 device walk caught empty circles on Step11 — W2 shipped
// label-only OptionRow rows. Icon mapping:
//   - friend    → Users (group of two)
//   - instagram → Camera (Instagram brand glyph removed from
//                 lucide-react-native v1.x; Camera is the semantic
//                 stand-in for a photo-sharing source)
//   - tiktok    → Music (TikTok is a music-video platform; lucide
//                 dropped brand glyphs in v1.x)
//   - app_store → ShoppingBag (app marketplace)
//   - google    → Search (search-driven discovery)
//   - other     → MoreHorizontal (3-dot fallback)
// All 6 verified as lucide-react-native@1.14.0 exports (or aliases:
// MoreHorizontal → Ellipsis).
const ICON_SIZE = 20;
const ICON_STROKE = 2;
function sourceIcon(key: OnboardingAttributionSource, color: string): React.ReactNode {
  switch (key) {
    case 'friend':
      return <Users size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'instagram':
      return <Camera size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'tiktok':
      return <Music size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'app_store':
      return <ShoppingBag size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'google':
      return <Search size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'other':
      return <MoreHorizontal size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
  }
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
          const active = value === s.value;
          const iconColor = active ? colors.accentDark : colors.text.primary;
          return (
            <OptionRow
              key={s.value}
              testID={`attr-${s.value}`}
              option={{
                key: s.value,
                label: t(s.labelKey),
                icon: sourceIcon(s.value, iconColor),
              }}
              active={active}
              onToggle={() => onChange(s.value)}
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
