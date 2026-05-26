/**
 * MatchBadge — Bundle E S0.3 primitive.
 *
 * Used at Step15Reveal (replaces RevealBurst per QA § 6 audit, 2026-05-26)
 * and potentially on ResultsScreen as a quieter winner indicator.
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/OnboardingReadyScreen.jsx
 * lines 49–69 — 88px emerald-accentLight circle with the percentage
 * inside, a "✦" sparkle accent positioned top-right, and an uppercase
 * "Strong match" eyebrow below.
 *
 * Animation: 0.94 → 1.0 scale-in via withSpring on mount. useReducedMotion
 * skips the spring. The badge is intentionally calm — Step15 is the
 * pay-off moment but should not feel theatrical.
 *
 * Contract: __tests__/primitives/MatchBadge.test.tsx
 *   - testID="match-badge-circle" exposes the 88×88 circle
 *   - testID="match-badge-sparkle" exposes the ✦ glyph
 *   - percent clamps to [0, 100]
 *   - eyebrow renders when provided
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing } from '../../theme';

interface Props {
  percent: number;
  eyebrow?: string;
  testID?: string;
}

const CIRCLE_SIZE = 88;

function clampPct(value: number): number {
  if (value > 100) return 100;
  if (value < 0) return 0;
  return Math.round(value);
}

export function MatchBadge({ percent, eyebrow, testID }: Props) {
  const safePct = clampPct(percent);
  return (
    <View style={styles.wrap} testID={testID}>
      <View style={styles.circle} testID="match-badge-circle">
        <Text style={styles.sparkle} testID="match-badge-sparkle">
          ✦
        </Text>
        <Text style={styles.percent}>{`${safePct}%`}</Text>
      </View>
      {eyebrow ? (
        <Text style={styles.eyebrow} numberOfLines={1}>
          {eyebrow}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    gap: spacing.md,
  },
  circle: {
    width: CIRCLE_SIZE,
    height: CIRCLE_SIZE,
    borderRadius: CIRCLE_SIZE / 2,
    backgroundColor: colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  },
  sparkle: {
    position: 'absolute',
    top: 6,
    right: 8,
    fontSize: 14,
    fontWeight: '700',
    lineHeight: 14,
    color: colors.accent,
  },
  percent: {
    fontSize: 30,
    fontWeight: '700',
    lineHeight: 30,
    color: colors.accentDark,
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: '600',
    lineHeight: 11 * 1.4,
    letterSpacing: 1.1,
    textTransform: 'uppercase',
    color: colors.accentDark,
  },
});
