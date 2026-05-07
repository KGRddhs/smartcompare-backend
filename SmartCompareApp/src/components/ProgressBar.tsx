import React, { useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withSequence,
  Easing,
} from 'react-native-reanimated';
import { colors } from '../theme';

interface ProgressBarProps {
  progress: number; // 0-1
  /**
   * When true, animation runs in 4 segments with fast/slow/fast/snap
   * easing per design spec Section 3 ("variable progress easing").
   * Used by Results loading and onboarding screen 14 to make the wait
   * feel intentional. Per-segment timing is verified on-device — unit
   * tests assert end-state width only.
   */
  variableEasing?: boolean;
  testID?: string;
}

const FAST_EASE = Easing.bezier(0, 0.55, 0.45, 1);
const SLOW_EASE = Easing.bezier(0.4, 0, 0.6, 1);
const SNAP_EASE = Easing.bezier(0.55, 0, 0.1, 1);

export function ProgressBar({ progress, variableEasing, testID }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(1, progress));
  const animatedWidth = useSharedValue(clamped);

  useEffect(() => {
    if (variableEasing) {
      animatedWidth.value = withSequence(
        withTiming(Math.min(0.25, clamped), { duration: 600, easing: FAST_EASE }),
        withTiming(Math.min(0.60, clamped), { duration: 1200, easing: SLOW_EASE }),
        withTiming(Math.min(0.90, clamped), { duration: 600, easing: FAST_EASE }),
        withTiming(clamped, { duration: 400, easing: SNAP_EASE })
      );
    } else {
      animatedWidth.value = withTiming(clamped, {
        duration: 600,
        easing: Easing.out(Easing.cubic),
      });
    }
  }, [clamped, variableEasing, animatedWidth]);

  const fillStyle = useAnimatedStyle(() => ({
    width: `${Math.max(0, Math.min(1, animatedWidth.value)) * 100}%`,
  }));

  return (
    <View style={styles.track} testID={testID ? `${testID}-track` : undefined}>
      <Animated.View
        style={[styles.fill, fillStyle]}
        testID={testID ? `${testID}-fill` : undefined}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  track: {
    height: 4,
    backgroundColor: colors.border.light,
    borderRadius: 2,
    overflow: 'hidden',
  },
  fill: {
    height: 4,
    backgroundColor: colors.accent,
    borderRadius: 2,
  },
});
