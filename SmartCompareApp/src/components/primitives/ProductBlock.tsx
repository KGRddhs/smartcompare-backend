/**
 * ProductBlock — Bundle E S0.3 primitive.
 *
 * One half of a VsPair (HistoryRowV2, SmartPickCard, PaywallScreen HeroVisual,
 * Results hero card). Renders a product tile + name + sub-line. When
 * `winner=true` the block carries an emerald 2px outline + accentLight bg +
 * an optional uppercase "TOP MATCH" eyebrow above the name.
 *
 * winner state is also exposed via accessibilityState.selected so screen
 * readers announce which product won and tests can target the winning
 * block.
 *
 * Contract is implicit in __tests__/primitives/VsPair.test.tsx — that test
 * targets testID="vs-pair-block-left" / "-right" and reads the
 * accessibilityState.selected flag, both of which VsPair forwards to the
 * underlying ProductBlock.
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { colors, spacing, radii } from '../../theme';

export interface ProductBlockData {
  name: string;
  sub?: string;
}

interface Props {
  product: ProductBlockData;
  winner?: boolean;
  showTopMatch?: boolean;
  testID?: string;
}

export function ProductBlock({ product, winner, showTopMatch, testID }: Props) {
  return (
    <View
      style={[styles.card, winner ? styles.cardWinner : styles.cardBase]}
      testID={testID}
      accessibilityState={{ selected: Boolean(winner) }}
      accessibilityRole="text"
    >
      {showTopMatch ? <Text style={styles.eyebrow}>TOP MATCH</Text> : null}
      <Text style={styles.name} numberOfLines={2}>
        {product.name}
      </Text>
      {product.sub ? (
        <Text style={styles.sub} numberOfLines={1}>
          {product.sub}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    padding: spacing.base,
    borderRadius: radii.card,
    minHeight: 96,
    justifyContent: 'center',
  },
  cardBase: {
    backgroundColor: colors.bg.secondary,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  cardWinner: {
    backgroundColor: colors.accentLight,
    borderWidth: 2,
    borderColor: colors.accent,
  },
  eyebrow: {
    fontSize: 10,
    fontWeight: '700',
    lineHeight: 10 * 1.4,
    letterSpacing: 1,
    textTransform: 'uppercase',
    color: colors.accentDark,
    marginBottom: spacing.xs,
  },
  name: {
    fontSize: 16,
    fontWeight: '600',
    lineHeight: 16 * 1.3,
    color: colors.text.primary,
  },
  sub: {
    fontSize: 13,
    fontWeight: '400',
    lineHeight: 13 * 1.4,
    color: colors.text.secondary,
    marginTop: spacing.xs,
  },
});
