/**
 * HeroRings — Bundle E Phase 3 Task 3.2.
 *
 * Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 3.
 *
 * Two SVG radial rings side by side. Each shows the calibrated overall
 * score (70-95 range per § Decision 4). Top-match ring strokes emerald
 * (`colors.accent`), runner-up strokes neutral gray
 * (`colors.text.secondary`). Orange + red are banned anywhere on the
 * ring — design § 3 calls them "psychological poison on a score."
 *
 * Geometry: diameter 88px / stroke 8px / radius 44 on phone width.
 * Animation: Reanimated worklet fills the foreground arc 0 → score over
 * 600ms ease-out, fired after the ~3.2s loading sequence settles. The
 * fill uses `strokeDasharray` + animated `strokeDashoffset` on a single
 * foreground circle per ring (cheaper than path morphing, runs on the
 * UI thread).
 *
 * No adjective labels ("Great" / "Excellent") — number stands alone,
 * with "/100" in smaller weight below per design line 175.
 */

import React, { useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import Animated, {
  useSharedValue,
  useAnimatedProps,
  withTiming,
  Easing,
} from 'react-native-reanimated';

import { colors, spacing, typography } from '../../theme';

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

const SIZE = 88;
const STROKE = 8;
const RADIUS = (SIZE - STROKE) / 2; // 40, but design pins to 44 — set explicitly below
const RING_RADIUS = 44;
const CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;
const FILL_DURATION_MS = 600;

interface HeroRingsProps {
  scoreA: number;
  scoreB: number;
  labelA?: string;
  labelB?: string;
  winnerIndex: 0 | 1;
  testID?: string;
}

interface RingProps {
  score: number;
  isWinner: boolean;
  label?: string;
  testID?: string;
}

function Ring({ score, isWinner, label, testID }: RingProps) {
  const progress = useSharedValue(0);

  useEffect(() => {
    // Worklet-native fill animation. The shared value drives
    // strokeDashoffset via useAnimatedProps, which runs entirely on the
    // UI thread — no JS-bridge frames during the 600ms fill.
    progress.value = withTiming(score / 100, {
      duration: FILL_DURATION_MS,
      easing: Easing.out(Easing.ease),
    });
  }, [score, progress]);

  const animatedProps = useAnimatedProps(() => ({
    strokeDashoffset: CIRCUMFERENCE * (1 - progress.value),
  }));

  // Strict color contract per design § 3 — emerald for the winner ring,
  // neutral gray for the runner-up. NEVER colors.warning (orange) or
  // colors.destructive (red).
  const fgStroke = isWinner ? colors.accent : colors.text.secondary;
  const trackStroke = colors.border.light;

  return (
    <View style={styles.ringWrapper} testID={testID}>
      <Svg width={SIZE} height={SIZE}>
        {/* Background track — neutral, always visible. */}
        <Circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RING_RADIUS}
          stroke={trackStroke}
          strokeWidth={STROKE}
          fill="none"
        />
        {/* Foreground arc — animated fill 0 → score/100. The dasharray
            equals the circumference so the offset can be cleanly
            interpolated between full (0%) and zero (100%). Rotated -90°
            via transform so the arc starts at 12 o'clock. */}
        <AnimatedCircle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RING_RADIUS}
          stroke={fgStroke}
          strokeWidth={STROKE}
          fill="none"
          strokeDasharray={CIRCUMFERENCE}
          strokeLinecap="round"
          animatedProps={animatedProps}
          // SVG rotation pivot must match the ring center.
          transform={`rotate(-90 ${SIZE / 2} ${SIZE / 2})`}
        />
      </Svg>
      <View style={styles.centerOverlay} pointerEvents="none">
        <Text style={styles.scoreNumber}>{score}</Text>
        <Text style={styles.scoreSuffix}>/100</Text>
      </View>
      {label ? (
        <Text style={styles.productLabel} numberOfLines={2}>
          {label}
        </Text>
      ) : null}
    </View>
  );
}

export function HeroRings({
  scoreA,
  scoreB,
  labelA,
  labelB,
  winnerIndex,
  testID = 'hero-rings',
}: HeroRingsProps) {
  return (
    <View
      style={styles.container}
      testID={testID}
      // Expose calibrated inputs as host-node props so jest/runtime
      // probes can verify the worklet got the right values without
      // mocking through every Reanimated layer.
      {...({
        'data-score-a': scoreA,
        'data-score-b': scoreB,
        'data-winner-index': winnerIndex,
      } as any)}
    >
      <Ring
        score={scoreA}
        isWinner={winnerIndex === 0}
        label={labelA}
        testID={`${testID}-a`}
      />
      <View style={styles.vsGap}>
        <Text style={styles.vsText}>vs</Text>
      </View>
      <Ring
        score={scoreB}
        isWinner={winnerIndex === 1}
        label={labelB}
        testID={`${testID}-b`}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.lg,
    paddingVertical: spacing.lg,
  },
  ringWrapper: {
    alignItems: 'center',
    width: SIZE + spacing.sm * 2,
  },
  centerOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: SIZE,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scoreNumber: {
    ...typography.title,
    fontSize: 26,
    fontWeight: '700',
    color: colors.text.primary,
    lineHeight: 28,
  },
  scoreSuffix: {
    ...typography.small,
    fontSize: 10,
    color: colors.text.secondary,
    marginTop: 2,
  },
  productLabel: {
    ...typography.caption,
    color: colors.text.primary,
    marginTop: spacing.sm,
    textAlign: 'center',
    fontWeight: '600',
  },
  vsGap: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  vsText: {
    ...typography.caption,
    color: colors.text.secondary,
    fontWeight: '500',
  },
});

// Silence the unused-RADIUS warning — the const documents the geometry
// derivation even though we use the explicit RING_RADIUS pinned to the
// design spec.
void RADIUS;
