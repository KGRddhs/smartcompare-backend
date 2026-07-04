/**
 * Step08Priorities — Bundle E S2.W2 REWRITE.
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/OnboardingScreen.jsx
 * QarenOnboardingScreen (lines 75-168) + OptionRow function (37-73).
 * The JSX shows 8 priority rows with per-priority lucide-style outline
 * SVG icons inside 36px circles, plus the standard Cal-AI-Lite
 * black-on-select row inversion.
 *
 * Per memory feedback_compose_vs_rewrite_phrasing.md this is a REWRITE
 * (not compose) — the prior Bundle D layout was a wrapping
 * TouchableOpacity chip flex-grid with plain text labels. The JSX
 * dictates a vertical stack of icon-circle rows. The S2.W2 OptionRow
 * primitive extension (icon: string | ReactNode, shipped this wave at
 * `c04b3cb`) makes this a clean swap.
 *
 * Anatomy:
 *   1. Title + subtitle (existing copy preserved: "What matters most
 *      when you buy?" + "Pick up to 3").
 *   2. 8 OptionRow rows, each passing a lucide-react-native icon as
 *      `option.icon` (ReactNode) — sized 20px for visual breathing
 *      inside the 36px circle, accentDark stroke when active mirrors
 *      the PrivacyRow pattern.
 *   3. MAX_SELECTIONS=3 silent cap (no scary copy on overflow per
 *      Build Principle #4 — engaging never scary).
 *
 * 8 canonical priority keys preserved VERBATIM (CLAUDE.md cohort match
 * rule + dispatcher W2 task description): price / quality /
 * brand_reputation / durability / latest_features / ease_of_use /
 * eco_friendly / health_safety. Feeds scoring ±30% personalization cap.
 *
 * Per-priority icon mapping (dispatcher's W2 suggestion list, all 8
 * verified as lucide-react-native@1.14.0 exports):
 *   price            → DollarSign
 *   quality          → Award
 *   brand_reputation → ShieldCheck
 *   durability       → Hammer
 *   latest_features  → Sparkles
 *   ease_of_use      → MousePointerClick
 *   eco_friendly     → Leaf
 *   health_safety    → HeartPulse
 *
 * Test contract preserved (Step08Priorities.test.tsx — 6 tests):
 *   - testID="priority-<canonical_key>" forwarded to each OptionRow root
 *   - onChange(next[]) toggles per the existing add/remove/silent-cap
 *     contract
 *   - accessibilityState.selected mirrors per-key membership
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import {
  DollarSign,
  Award,
  ShieldCheck,
  Hammer,
  Sparkles,
  MousePointerClick,
  Leaf,
  HeartPulse,
} from 'lucide-react-native';
import { OptionRow } from '../../components/primitives/OptionRow';
import { colors, spacing, typography } from '../../theme';
import { toCanonicalPriorities } from '../../utils/priorities';

const PRIORITIES = [
  'price',
  'quality',
  'brand_reputation',
  'durability',
  'latest_features',
  'ease_of_use',
  'eco_friendly',
  'health_safety',
] as const;

type PriorityKey = (typeof PRIORITIES)[number];

const MAX_SELECTIONS = 3;
const ICON_SIZE = 20;
const ICON_STROKE = 2;

// Per-priority lucide icon glyph. Color is inherited from each render
// site (active rows use accentDark for emerald signal; inactive rows
// use text.primary for the standard black-on-white circle).
function priorityIcon(key: PriorityKey, color: string): React.ReactNode {
  switch (key) {
    case 'price':
      return <DollarSign size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'quality':
      return <Award size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'brand_reputation':
      return <ShieldCheck size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'durability':
      return <Hammer size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'latest_features':
      return <Sparkles size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'ease_of_use':
      return <MousePointerClick size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'eco_friendly':
      return <Leaf size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
    case 'health_safety':
      return <HeartPulse size={ICON_SIZE} color={color} strokeWidth={ICON_STROKE} />;
  }
}

interface Props {
  value: string[];
  onChange: (priorities: string[]) => void;
}

export function Step08Priorities({ value, onChange }: Props) {
  const { t } = useTranslation();

  // Normalize any cohort-seeded priorities to canonical display keys so
  // they render as selected rows instead of invisibly consuming the cap.
  const selected = toCanonicalPriorities(value);

  const toggle = (key: string) => {
    if (selected.includes(key)) {
      onChange(selected.filter((k) => k !== key));
      return;
    }
    if (selected.length >= MAX_SELECTIONS) {
      // Silent cap per Build Principle #4: engaging, never scary. No
      // tooltip, no shake, no haptic on overflow. Selecting another
      // simply does nothing.
      return;
    }
    onChange([...selected, key]);
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t('onboarding.s8.title')}</Text>
      <Text style={styles.subtitle}>
        {t('onboarding.s8.subtitle', { defaultValue: 'Pick up to 3' })}
      </Text>

      <View style={styles.list}>
        {PRIORITIES.map((p) => {
          const active = selected.includes(p);
          // Active row's circle bg flips to accentLight; icon glyph
          // adopts accentDark to maintain stroke contrast. Inactive
          // rows use text.primary on bg.secondary per OptionRow's
          // default circle styling.
          const iconColor = active ? colors.accentDark : colors.text.primary;
          return (
            <OptionRow
              key={p}
              testID={`priority-${p}`}
              option={{
                key: p,
                label: t(`onboarding.s8.priority_${p}`),
                icon: priorityIcon(p, iconColor),
              }}
              active={active}
              onToggle={() => toggle(p)}
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
    marginBottom: spacing.sm,
  },
  subtitle: {
    ...typography.body,
    color: colors.text.secondary,
    marginBottom: spacing.xl,
  },
  list: {
    gap: spacing.sm,
  },
});
