/**
 * DimensionBar — Bundle E S0.3 primitive.
 *
 * Two-color comparative bar used on ResultsScreen per dimension (e.g.
 * "Battery", "Camera"). Left vs right proportions are the relative
 * normalized dimension scores (0–1 each, do not need to sum to 1).
 * The winning side renders emerald; the losing side renders the muted
 * secondary text color. A 2px white gap separates the two segments.
 *
 * Contract: __tests__/primitives/DimensionBar.test.tsx
 *   - testID="dim-bar-left" / "dim-bar-right" / "dim-bar-gap"
 *   - winner='left'  → left  segment #10B981, right not
 *   - winner='right' → right segment #10B981, left  not
 *   - winner=null    → neither segment #10B981 (tie)
 */
import React from 'react';
import { View, StyleSheet } from 'react-native';
import { colors } from '../../theme';

interface Props {
  left: number;
  right: number;
  winner: 'left' | 'right' | null;
  testID?: string;
  /**
   * Optional per-segment testID overrides. Default to the primitive's own
   * `dim-bar-left` / `dim-bar-right` / `dim-bar-gap` contract (consumed by
   * `__tests__/primitives/DimensionBar.test.tsx`). Composite consumers
   * (e.g. DimensionBars) pass row-scoped IDs so multiple bars on one
   * screen each carry a unique hook (`bars-row-{key}-fill-a`).
   */
  leftTestID?: string;
  rightTestID?: string;
  gapTestID?: string;
}

const TRACK_HEIGHT = 8;
const GAP_WIDTH = 2;

export function DimensionBar({
  left,
  right,
  winner,
  testID,
  leftTestID = 'dim-bar-left',
  rightTestID = 'dim-bar-right',
  gapTestID = 'dim-bar-gap',
}: Props) {
  const total = left + right || 1;
  const leftPct = (left / total) * 100;
  const rightPct = (right / total) * 100;

  const leftColor = winner === 'left' ? colors.accent : colors.text.secondary;
  const rightColor = winner === 'right' ? colors.accent : colors.text.secondary;

  return (
    <View style={styles.track} testID={testID}>
      <View
        style={[styles.segment, { flexBasis: `${leftPct}%`, backgroundColor: leftColor }]}
        testID={leftTestID}
      />
      <View style={styles.gap} testID={gapTestID} />
      <View
        style={[styles.segment, { flexBasis: `${rightPct}%`, backgroundColor: rightColor }]}
        testID={rightTestID}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  track: {
    flexDirection: 'row',
    height: TRACK_HEIGHT,
    width: '100%',
    borderRadius: TRACK_HEIGHT / 2,
    overflow: 'hidden',
    backgroundColor: 'transparent',
  },
  segment: {
    height: TRACK_HEIGHT,
    flexGrow: 0,
    flexShrink: 1,
    borderRadius: TRACK_HEIGHT / 2,
  },
  gap: {
    width: GAP_WIDTH,
    height: TRACK_HEIGHT,
    backgroundColor: colors.bg.primary,
  },
});
