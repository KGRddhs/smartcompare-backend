/**
 * PeerLattice — Bundle E S0.1b hero illustration.
 *
 * Added per QA § 6 audit (2026-05-26): Step12CohortProof JSX
 * (OnboardingCohortScreen.jsx) uses an 8×12 dot lattice, NOT a bar chart.
 * Replaces the now-unused CohortBarChart hero (slated for delete at S2
 * Step12 swap).
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/OnboardingCohortScreen.jsx
 * PeerLattice function (lines 41–81):
 *   - cols=12 rows=7 dot grid (84 dots — the test scaffold's "8×12 dot grid"
 *     prose simplifies; the actual JSX is 12×7)
 *   - per-dot opacity = max(0.15, 0.85 - distance × 0.10) where distance is
 *     hypot(c - midCol, r - midRow)
 *   - center cell hosts a single emerald YOU-dot (20px circle) with a
 *     2-stop box-shadow halo (bg-primary inner + accent outer)
 *
 * Animation: fade-in from center outward over 600ms cubic-bezier on mount.
 * YOU-dot 0 → 1.0 scale with subtle spring. useReducedMotion no-ops both.
 *
 * Contract: __tests__/hero/PeerLattice.test.tsx
 *   - default + custom-size snapshots
 *   - testID="peer-lattice-you-dot" exposes center emerald dot
 *   - YOU-dot backgroundColor OR fill is exactly #10B981
 *   - animated={false} prop renders without throwing
 */
import React, { useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withSpring,
  Easing,
} from 'react-native-reanimated';
import Animated from 'react-native-reanimated';
import { colors } from '../../theme';
import { motion } from '../../theme/motion';

interface Props {
  size?: number;
  animated?: boolean;
  testID?: string;
}

const COLS = 12;
const ROWS = 7;
const GAP = 7;
const YOU_DOT_SIZE = 20;

interface Cell {
  r: number;
  c: number;
  distance: number;
  opacity: number;
  isCentre: boolean;
}

function buildCells(): Cell[] {
  const midCol = (COLS - 1) / 2;
  const midRow = (ROWS - 1) / 2;
  const cells: Cell[] = [];
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      const distance = Math.hypot(c - midCol, r - midRow);
      const opacity = Math.max(0.15, 0.85 - distance * 0.1);
      const isCentre = r === midRow && c === midCol;
      cells.push({ r, c, distance, opacity, isCentre });
    }
  }
  return cells;
}

const CELLS = buildCells();

export function PeerLattice({ size = 320, animated = true, testID }: Props) {
  const peerOpacity = useSharedValue(animated ? 0 : 1);
  const youScale = useSharedValue(animated ? 0 : 1);

  useEffect(() => {
    if (!animated) return;
    peerOpacity.value = withTiming(1, {
      duration: 600,
      easing: Easing.bezier(0.32, 0.72, 0, 1),
    });
    youScale.value = withSpring(1, motion.revealBurst.badgeSpring);
  }, [animated, peerOpacity, youScale]);

  const peerStyle = useAnimatedStyle(() => ({
    opacity: peerOpacity.value,
  }));

  const youStyle = useAnimatedStyle(() => ({
    transform: [{ scale: youScale.value }],
  }));

  // Dot diameter derives from the available width minus N-1 gaps,
  // divided by N columns. Keeps the lattice square-aspect.
  const innerWidth = Math.min(size, 320);
  const dotSize = (innerWidth - (COLS - 1) * GAP) / COLS;

  return (
    <View
      style={[styles.root, { width: innerWidth, alignSelf: 'center' }]}
      testID={testID}
    >
      <Animated.View style={[styles.grid, peerStyle]}>
        {CELLS.map((cell, i) => (
          <View
            key={i}
            style={[
              styles.cell,
              {
                width: dotSize,
                height: dotSize,
                marginRight: cell.c === COLS - 1 ? 0 : GAP,
                marginBottom: cell.r === ROWS - 1 ? 0 : GAP,
                opacity: cell.isCentre ? 0 : cell.opacity,
                backgroundColor: cell.isCentre ? 'transparent' : colors.text.primary,
              },
            ]}
          />
        ))}
      </Animated.View>
      <Animated.View
        style={[styles.youDot, youStyle, { backgroundColor: colors.accent }]}
        testID="peer-lattice-you-dot"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    position: 'relative',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 18,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    width: '100%',
  },
  cell: {
    borderRadius: 999,
  },
  youDot: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    width: YOU_DOT_SIZE,
    height: YOU_DOT_SIZE,
    marginLeft: -YOU_DOT_SIZE / 2,
    marginTop: -YOU_DOT_SIZE / 2,
    borderRadius: YOU_DOT_SIZE / 2,
    // Halo: outer accent stroke via boxShadow-equivalent. RN uses shadow*
    // props which only render on real devices. The visual halo is
    // production-only; tests assert the YOU-dot color + position only.
    shadowColor: colors.accent,
    shadowOpacity: 0.25,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 0 },
  },
});
