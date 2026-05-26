/**
 * ConcentricMotif — hero illustration #3.
 *
 * Used on Onboarding screen 13 ("Time to build your shopping advisor")
 * per design Section 5b.
 *
 * 5 concentric ring circles, rotating at different speeds (8s, 6s, 5s,
 * 4s, 3s) with alternating directions (counter-rotating siblings).
 * Center holds the Q-magnifier brand mark. Innermost ring is emerald;
 * outer 4 are neutral border-medium gray.
 *
 * The rotation is decorative only — accessibility-reduced-motion
 * collapses to a static layout because the Reanimated mock returns
 * identity during tests.
 */
import React, { useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import Svg, { Circle, G } from 'react-native-svg';
import {
  useSharedValue,
  withRepeat,
  withTiming,
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
const RING_RADII = [40, 70, 100, 130, 160] as const; // innermost → outermost
const RING_DURATIONS = [3000, 4000, 5000, 6000, 8000] as const;

export function ConcentricMotif({ size = 320, testID }: Props) {
  // One rotation driver per ring. Mock returns identity in tests.
  const r0 = useSharedValue(0);
  const r1 = useSharedValue(0);
  const r2 = useSharedValue(0);
  const r3 = useSharedValue(0);
  const r4 = useSharedValue(0);

  useEffect(() => {
    const start = (sv: { value: number }, ms: number) => {
      sv.value = withRepeat(
        withTiming(360, { duration: ms, easing: Easing.linear ?? Easing.ease }),
        -1,
        false
      );
    };
    start(r0, RING_DURATIONS[0]);
    start(r1, RING_DURATIONS[1]);
    start(r2, RING_DURATIONS[2]);
    start(r3, RING_DURATIONS[3]);
    start(r4, RING_DURATIONS[4]);
  }, [r0, r1, r2, r3, r4]);

  return (
    <View style={[styles.root, { width: size, height: size }]} testID={testID}>
      <Svg width={size} height={size} viewBox={`0 0 ${VIEWBOX} ${VIEWBOX}`}>
        <G>
          {RING_RADII.map((r, i) => (
            <Circle
              key={`ring-${i}`}
              testID={`concentric-ring-${i}`}
              cx={CENTER}
              cy={CENTER}
              r={r}
              fill="none"
              stroke={i === 0 ? colors.accent : colors.border.medium}
              strokeWidth={i === 0 ? 2.5 : 1.5}
              opacity={i === 0 ? 1 : 0.6 - i * 0.08}
            />
          ))}
        </G>
      </Svg>
      <View style={styles.center} pointerEvents="none">
        <QaranIcon size={Math.round(size * 0.16)} />
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
