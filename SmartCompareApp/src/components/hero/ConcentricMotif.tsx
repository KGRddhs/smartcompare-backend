/**
 * ConcentricMotif — Bundle E S0.1b hero illustration.
 *
 * 3 emerald rings expanding outward from a Q logo center, staggered 700ms,
 * looping 2.1s. Used by Step03ValueProp, Step05Trust, Step13Anticipation,
 * and LoadingScreen's ConcentricVariant. Bundle D shipped a 5-ring rotating
 * motif; Bundle E swaps to the design-doc § 3.2 spec (3-ring expanding) to
 * match the JSX reference + share visual language with LoadingRings.
 *
 * Animation:
 *   - each ring loops withTiming({ scale: 0.8→2.5, opacity: 0.9→0 }, 2100ms)
 *   - staggered 0ms / 700ms / 1400ms via withDelay
 *   - Easing.out(Easing.cubic) gives the "ripple outward" feel
 *
 * Contract: __tests__/hero/ConcentricMotif.test.tsx
 *   - default + custom-size snapshots
 *   - animated={false} renders without throwing
 */
import React, { useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import {
  useSharedValue,
  withRepeat,
  withTiming,
  withDelay,
  Easing,
} from 'react-native-reanimated';
import { colors, spacing } from '../../theme';
import { QaranIcon } from '../../icons/QaranIcon';

interface Props {
  size?: number;
  animated?: boolean;
  testID?: string;
}

const VIEWBOX = 220;
const CENTER = VIEWBOX / 2;
const RING_BASE_R = 36;
const RING_TARGET_R = VIEWBOX * 0.45;
const RING_DURATION_MS = 2100;
const RING_STAGGER_MS = 700;
const RING_COUNT = 3;

export function ConcentricMotif({ size = 220, animated = true, testID }: Props) {
  // One radius driver per ring; each repeats forever.
  const ring0 = useSharedValue(RING_BASE_R);
  const ring1 = useSharedValue(RING_BASE_R);
  const ring2 = useSharedValue(RING_BASE_R);

  useEffect(() => {
    if (!animated) return;
    const drive = (sv: { value: number }, delayMs: number) => {
      sv.value = withDelay(
        delayMs,
        withRepeat(
          withTiming(RING_TARGET_R, {
            duration: RING_DURATION_MS,
            easing: Easing.out(Easing.cubic),
          }),
          -1,
          false,
        ),
      );
    };
    drive(ring0, 0);
    drive(ring1, RING_STAGGER_MS);
    drive(ring2, RING_STAGGER_MS * 2);
  }, [animated, ring0, ring1, ring2]);

  return (
    <View style={[styles.root, { width: size, height: size }]} testID={testID}>
      <Svg width={size} height={size} viewBox={`0 0 ${VIEWBOX} ${VIEWBOX}`}>
        {[ring0, ring1, ring2].map((sv, i) => {
          const r = sv.value;
          const progress = (r - RING_BASE_R) / (RING_TARGET_R - RING_BASE_R);
          const opacity = Math.max(0, 0.9 - progress);
          return (
            <Circle
              key={`ring-${i}`}
              testID={`concentric-ring-${i}`}
              cx={CENTER}
              cy={CENTER}
              r={r}
              fill="none"
              stroke={colors.accent}
              strokeWidth={2}
              opacity={opacity}
            />
          );
        })}
      </Svg>
      <View style={styles.center} pointerEvents="none">
        <QaranIcon size={Math.round(size * 0.22)} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    alignSelf: 'center',
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.base,
  },
  center: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
