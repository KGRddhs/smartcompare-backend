/**
 * LoadingRings — hero illustration #4 (the centerpiece).
 *
 * Used on Onboarding screen 14 (theatrical 3.2s loading) per design
 * Section 5b. Larger dramatic version of #3:
 *   - Big Q-logo at center (~40% of viewbox)
 *   - 3 emerald rings expanding outward continuously, ~2s each, fading
 *     as they expand
 *   - Gentle scale-pulse on the logo
 *   - Rings staggered every 700ms
 *
 * The animation runs continuously while the screen is mounted; the
 * onComplete handler on the parent screen fires when the 3.2s
 * minimum has elapsed AND the API result has arrived.
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
  testID?: string;
}

const VIEWBOX = 320;
const CENTER = VIEWBOX / 2;
const RING_BASE_R = 60;
const RING_TARGET_R = 150;
const RING_DURATION_MS = 2000;
const RING_STAGGER_MS = 700;
const RING_COUNT = 3;

export function LoadingRings({ size = 320, testID }: Props) {
  // One radius driver per ring; each repeats forever.
  const ring0 = useSharedValue(RING_BASE_R);
  const ring1 = useSharedValue(RING_BASE_R);
  const ring2 = useSharedValue(RING_BASE_R);

  useEffect(() => {
    const drive = (sv: { value: number }, delayMs: number) => {
      sv.value = withDelay(
        delayMs,
        withRepeat(
          withTiming(RING_TARGET_R, {
            duration: RING_DURATION_MS,
            easing: Easing.out(Easing.cubic),
          }),
          -1,
          false
        )
      );
    };
    drive(ring0, 0);
    drive(ring1, RING_STAGGER_MS);
    drive(ring2, RING_STAGGER_MS * 2);
  }, [ring0, ring1, ring2]);

  return (
    <View style={[styles.root, { width: size, height: size }]} testID={testID}>
      <Svg width={size} height={size} viewBox={`0 0 ${VIEWBOX} ${VIEWBOX}`}>
        {[ring0, ring1, ring2].map((sv, i) => {
          const r = sv.value;
          // Opacity fades 1 → 0 as the ring expands from base to target.
          const progress = (r - RING_BASE_R) / (RING_TARGET_R - RING_BASE_R);
          const opacity = Math.max(0, 1 - progress);
          return (
            <Circle
              key={`ring-${i}`}
              testID={`loading-rings-ring-${i}`}
              cx={CENTER}
              cy={CENTER}
              r={r}
              fill="none"
              stroke={colors.accent}
              strokeWidth={2.5}
              opacity={opacity}
            />
          );
        })}
      </Svg>
      <View style={styles.center} pointerEvents="none" testID="loading-rings-logo">
        <QaranIcon size={Math.round(size * 0.4)} />
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
