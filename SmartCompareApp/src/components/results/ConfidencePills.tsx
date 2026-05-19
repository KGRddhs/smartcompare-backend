/**
 * ConfidencePills — Bundle C spec § 5b + § 5c + § 5d.
 *
 * Replaces the legacy single-word confidence banner on the Results screen
 * with a 3-pill horizontal row (💰 Price / ⭐ Reviews / 📋 Specs). Tap
 * opens "What we know" bottom sheet (caller-owned modal state).
 *
 * Color contract:
 *  - strong     → emerald-tinted (uses `colors.accentLight` background +
 *                 `colors.accentDark` text). Confident, not loud.
 *  - acceptable → amber (`colors.warning` at 13% alpha background + warning
 *                 text). Soft middle ground; never reads as warning/error.
 *  - weak       → muted (`colors.bg.secondary` background + secondary text).
 *                 Never red, never destructive — the calibrated-honesty
 *                 anchor (spec § 0) forbids alarmist signal.
 *
 * Suppression rules:
 *  - When `hidePricePill === true` (caller computes via `anyEstimated()`
 *    helper), the Price pill is omitted entirely (§ 5c — price provenance
 *    is silent in the UI; no "estimated" copy anywhere).
 *  - A leg whose confidence is `undefined` is omitted entirely (no
 *    placeholder pill).
 *  - When no legs are present, the component renders `null` (caller may
 *    decide whether to slot in a fallback).
 */
import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';

import { colors, spacing, typography, radii } from '../../theme';

type Level = 'strong' | 'acceptable' | 'weak';
type Leg = 'price' | 'reviews' | 'specs';

interface Props {
  confidence: {
    price?: Level;
    reviews?: Level;
    specs?: Level;
  };
  hidePricePill?: boolean;
  onPillPress: (leg: Leg) => void;
  testID?: string;
}

const PILLS: Array<{ leg: Leg; emoji: string; labelKey: string }> = [
  { leg: 'price',   emoji: '💰', labelKey: 'results.confidence.pill.price' },
  { leg: 'reviews', emoji: '⭐', labelKey: 'results.confidence.pill.reviews' },
  { leg: 'specs',   emoji: '📋', labelKey: 'results.confidence.pill.specs' },
];

export function ConfidencePills({ confidence, hidePricePill, onPillPress, testID = 'confidence-pills' }: Props) {
  const { t } = useTranslation();

  const renderable = PILLS.filter((p) => {
    if (p.leg === 'price' && hidePricePill) return false;
    return confidence[p.leg] !== undefined;
  });

  if (renderable.length === 0) return null;

  return (
    <View style={styles.row} testID={testID}>
      {renderable.map((p) => {
        const level = confidence[p.leg]!;
        const palette = PALETTES[level];
        return (
          <TouchableOpacity
            key={p.leg}
            testID={`${testID}-${p.leg}`}
            accessibilityRole="button"
            onPress={() => onPillPress(p.leg)}
            style={[styles.pill, { backgroundColor: palette.bg }]}
          >
            <Text style={styles.emoji}>{p.emoji}</Text>
            <Text style={[styles.label, { color: palette.fg }]}>
              {t(p.labelKey)}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const PALETTES: Record<Level, { bg: string; fg: string }> = {
  strong:     { bg: colors.accentLight,           fg: colors.accentDark },
  // Amber at low alpha — soft, never alarmist.
  acceptable: { bg: colors.warning + '22',        fg: colors.warning },
  weak:       { bg: colors.bg.secondary,          fg: colors.text.secondary },
};

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: spacing.sm,
    flexWrap: 'wrap',
    paddingVertical: spacing.xs,
  },
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radii.chip,
    gap: spacing.xs,
  },
  emoji: {
    fontSize: 14,
  },
  label: {
    ...typography.caption,
    fontWeight: '600',
  },
});
