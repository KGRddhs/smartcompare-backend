/**
 * CohortBullet — Bundle E S0.3 primitive.
 *
 * Used at Step12CohortProof as 3 bullets below the PeerLattice hero.
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/OnboardingCohortScreen.jsx
 * lines 22–39 (CohortBullet function): 24px emerald-tint circle with a
 * checkmark glyph + bullet text on the right.
 *
 * The `icon` prop is currently semantic-only (used as a hint for tests +
 * a11y); all bullets render the same checkmark glyph per the JSX. If a
 * future design adds icon variation we can fork a lucide-backed render.
 *
 * Contract: __tests__/primitives/CohortBullet.test.tsx
 *   - Renders text
 *   - accent=true → root style contains an emerald color value somewhere
 *   - testID forwarded to the root container so tests can target it
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Polyline } from 'react-native-svg';
import { colors, spacing } from '../../theme';

interface Props {
  icon: string;
  text: string;
  accent?: boolean;
  testID?: string;
}

const CIRCLE_SIZE = 24;

export function CohortBullet({ icon: _icon, text, accent, testID }: Props) {
  return (
    <View
      style={[styles.row, accent ? styles.rowAccent : null]}
      testID={testID}
      accessibilityRole="text"
    >
      <View style={styles.circle}>
        <Svg width={13} height={13} viewBox="0 0 24 24">
          <Polyline
            points="20 6 9 17 4 12"
            fill="none"
            stroke={colors.accentDark}
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </Svg>
      </View>
      <Text style={styles.text}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.md,
  },
  // accent=true highlights the bullet (used sparingly — e.g. the "Picks
  // rooted in your region" bullet on Step12). Emerald color is the
  // load-bearing signal — text color flip is enough; we keep the bullet
  // text style the same.
  rowAccent: {
    borderColor: colors.accent,
    backgroundColor: colors.accentLight,
    paddingVertical: spacing.xs,
    paddingHorizontal: spacing.md,
    borderRadius: 12,
    borderWidth: 1,
  },
  circle: {
    width: CIRCLE_SIZE,
    height: CIRCLE_SIZE,
    borderRadius: CIRCLE_SIZE / 2,
    backgroundColor: colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 1,
    flexShrink: 0,
  },
  text: {
    flex: 1,
    fontSize: 15,
    fontWeight: '500',
    lineHeight: 15 * 1.5,
    color: colors.text.primary,
  },
});
