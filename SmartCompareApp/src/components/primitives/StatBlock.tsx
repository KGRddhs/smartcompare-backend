/**
 * StatBlock — Bundle E S0.3 primitive.
 *
 * Stacked label + value tile used in the Step15Reveal stat grid
 * (Top priority / Budget / Peers in Capital / GCC cohort) and on
 * ProfileScreen MonthStrip.
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/OnboardingReadyScreen.jsx
 * lines 14–29 (StatBlock function definition).
 *
 * Contract: __tests__/primitives/StatBlock.test.tsx
 *   - Renders label (muted uppercase eyebrow) + value (bold primary)
 *   - Numeric value renders with thousands separator allowed (2,074 ok)
 *   - accent=true switches value color to emerald
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing, radii } from '../../theme';

interface Props {
  label: string;
  value: string | number;
  accent?: boolean;
  testID?: string;
}

function formatValue(value: string | number): string {
  if (typeof value === 'number') {
    return value.toLocaleString('en-US');
  }
  return value;
}

export function StatBlock({ label, value, accent, testID }: Props) {
  return (
    <View style={styles.tile} testID={testID}>
      {/* F-S2.hotfix2 (task #39): allow the eyebrow label to wrap to 2
          lines + adjustsFontSizeToFit so long Step15 labels like
          "PEERS IN MUHARRAQ" / "PEERS IN NORTHERN" / "PEERS IN SOUTHERN"
          don't truncate to "PEERS IN MUHARR…". Ahmed's W4 device walk
          caught the clip on Bahrain governorate substitutions. The
          0.85 minimumFontScale gives ~9.4px floor — still legible at
          11px nominal, never drops below caption tier. */}
      <Text
        style={styles.label}
        numberOfLines={2}
        adjustsFontSizeToFit
        minimumFontScale={0.85}
      >
        {label}
      </Text>
      <Text style={[styles.value, accent ? styles.valueAccent : null]} numberOfLines={1}>
        {formatValue(value)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  tile: {
    flex: 1,
    minWidth: 0,
    padding: 14,
    borderRadius: radii.card,
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  label: {
    fontSize: 11,
    fontWeight: '500',
    lineHeight: 11 * 1.3,
    color: colors.text.secondary,
    letterSpacing: 0.4,
    textTransform: 'uppercase',
  },
  value: {
    fontSize: 18,
    fontWeight: '700',
    lineHeight: 18 * 1.2,
    color: colors.text.primary,
    marginTop: spacing.xs + 2,
  },
  valueAccent: {
    color: colors.accent,
  },
});
