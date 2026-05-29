/**
 * PrivacyRow — Bundle E S2.W1 primitive.
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/OnboardingExtras.jsx
 * PrivacyRow function (lines 154-170). 36px emerald-accentLight circle with an
 * accentDark icon glyph + head (15/600) / body (13/400) pair on the right.
 *
 * First consumer: Step05Trust (3 rows — check / search / X). Future reuse
 * candidate: the eventual Profile → Privacy settings surface in S3+, hence
 * the standalone primitive lift per S0.3 doctrine.
 *
 * Icons are passed as ReactNode so the consumer can supply a lucide-
 * react-native component, an inline Svg, or any other glyph. We keep
 * the primitive icon-agnostic so it doesn't drag a lucide dep on every
 * surface that consumes it (the project already uses lucide-react-native
 * elsewhere, but the primitive itself shouldn't pin the source).
 *
 * Contract: __tests__/primitives/PrivacyRow.test.tsx
 *   - Renders head + body strings
 *   - Icon slot exposed via testID="privacy-row-icon" (caller can target)
 *   - testID forwarded to the row container so test scaffolds can pin
 *     position within a list
 */
import React, { ReactNode } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing } from '../../theme';

interface Props {
  icon: ReactNode;
  head: string;
  body: string;
  testID?: string;
}

const CIRCLE_SIZE = 36;

export function PrivacyRow({ icon, head, body, testID }: Props) {
  return (
    <View style={styles.row} testID={testID} accessibilityRole="text">
      <View style={styles.circle} testID="privacy-row-icon">
        {icon}
      </View>
      <View style={styles.textCol}>
        <Text style={styles.head}>{head}</Text>
        <Text style={styles.body}>{body}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 14,
  },
  circle: {
    width: CIRCLE_SIZE,
    height: CIRCLE_SIZE,
    borderRadius: CIRCLE_SIZE / 2,
    backgroundColor: colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  textCol: {
    flex: 1,
    minWidth: 0,
  },
  head: {
    fontSize: 15,
    fontWeight: '600',
    lineHeight: 15 * 1.3,
    color: colors.text.primary,
  },
  body: {
    fontSize: 13,
    fontWeight: '400',
    lineHeight: 13 * 1.5,
    color: colors.text.secondary,
    marginTop: spacing.xs,
  },
});
