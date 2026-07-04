// SmartCompareApp/src/components/PrioritiesPicker.tsx
//
// Bundle E S2.X3 REWRITE — OptionRow icon-circle pattern matching
// Step08Priorities onboarding rhythm. Replaces the prior Bundle A
// chip-flex-grid layout so the EditPreferencesFlow visually inherits
// the same Cal-AI-Lite black-on-select row inversion + lucide glyphs
// shipped in Bundle E W2.
//
// Per memory feedback_compose_vs_rewrite_phrasing.md this is a REWRITE
// (not compose) — the prior layout was a wrapping chip grid; the new
// layout is a vertical OptionRow stack. The 8 canonical priority keys
// + MAX_SELECTIONS=3 silent cap + `priority-{key}` testID contract are
// preserved verbatim so PrioritiesPicker stays drop-in compatible with
// EditPreferencesFlow + any other call site.
//
// Per-priority icon mapping is intentionally identical to Step08:
//   price → DollarSign, quality → Award, brand_reputation → ShieldCheck,
//   durability → Hammer, latest_features → Sparkles,
//   ease_of_use → MousePointerClick, eco_friendly → Leaf,
//   health_safety → HeartPulse.
// Visual parity across onboarding + edit is the whole point of S2.X3.

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
import { OptionRow } from './primitives/OptionRow';
import { colors, spacing, typography } from '../theme';
import { toCanonicalPriorities } from '../utils/priorities';

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
  testIDPrefix?: string;
}

export default function PrioritiesPicker({
  value,
  onChange,
  testIDPrefix = 'priority',
}: Props) {
  const { t } = useTranslation();

  // Normalize cohort-seeded priorities to canonical display keys so they
  // render as selected rows here instead of sitting INVISIBLE while still
  // consuming the 3-selection cap (which made priorities un-choosable for
  // demographics-seeded users — device bug 2026-07-04).
  const selected = toCanonicalPriorities(value);

  const toggle = (key: string) => {
    if (selected.includes(key)) {
      onChange(selected.filter((k) => k !== key));
      return;
    }
    // Silent cap per Build Principle #4: engaging, never scary. No
    // shake / haptic / toast on overflow — extra taps are simply no-ops.
    if (selected.length >= MAX_SELECTIONS) return;
    onChange([...selected, key]);
  };

  return (
    <View>
      <Text style={styles.helper}>
        {t('preferences.priorities.helper', { defaultValue: 'Pick up to 3' })}
      </Text>
      <View style={styles.list}>
        {PRIORITIES.map((p) => {
          const active = selected.includes(p);
          const iconColor = active ? colors.accentDark : colors.text.primary;
          return (
            <OptionRow
              key={p}
              testID={`${testIDPrefix}-${p}`}
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
  helper: {
    ...typography.body,
    color: colors.text.secondary,
    marginBottom: spacing.lg,
  },
  list: {
    gap: spacing.sm,
  },
});
