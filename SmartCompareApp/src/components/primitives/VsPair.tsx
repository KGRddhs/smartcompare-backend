/**
 * VsPair — Bundle E S0.3 primitive.
 *
 * Two ProductBlocks side-by-side with a center, absolute-positioned emerald
 * "VS" pill between them. Used across HistoryRowV2, SmartPickCard
 * (HomeScreen), MarqueeCard items (ProfileScreen RecentDecisions /
 * HistoryScreen HeroStats), PaywallScreen HeroVisual, and Results hero
 * card pair.
 *
 * winner='left' applies the winner outline to the left block, 'right'
 * to the right block, null to neither.
 *
 * Contract: __tests__/primitives/VsPair.test.tsx
 *   - testID="vs-pair-pill" exposes the emerald VS pill
 *   - testID="vs-pair-block-left" / "-right" expose each block
 *   - winning block carries accessibilityState.selected=true
 */
import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { ProductBlock, ProductBlockData } from './ProductBlock';
import { colors, spacing, radii } from '../../theme';

interface Props {
  left: ProductBlockData;
  right: ProductBlockData;
  winner: 'left' | 'right' | null;
  testID?: string;
}

export function VsPair({ left, right, winner, testID }: Props) {
  return (
    <View style={styles.row} testID={testID}>
      <ProductBlock
        product={left}
        winner={winner === 'left'}
        showTopMatch={winner === 'left'}
        testID="vs-pair-block-left"
      />
      <View style={styles.pillWrap} pointerEvents="none">
        <View style={styles.pill} testID="vs-pair-pill">
          <Text style={styles.pillText}>VS</Text>
        </View>
      </View>
      <ProductBlock
        product={right}
        winner={winner === 'right'}
        showTopMatch={winner === 'right'}
        testID="vs-pair-block-right"
      />
    </View>
  );
}

const PILL_SIZE = 32;

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'stretch',
    gap: spacing.md,
    position: 'relative',
  },
  pillWrap: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pill: {
    width: PILL_SIZE,
    height: PILL_SIZE,
    borderRadius: radii.chip,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pillText: {
    fontSize: 11,
    fontWeight: '700',
    lineHeight: 11,
    letterSpacing: 0.5,
    color: colors.text.onInverse,
  },
});
