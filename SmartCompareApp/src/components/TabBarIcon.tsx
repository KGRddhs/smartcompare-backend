/**
 * TabBarIcon — wraps a bottom-tab icon with active-state visuals.
 *
 * Phase 3 Task 32. Per design § 4c:
 * - focused → emerald icon + small emerald dot below + filled state
 * - unfocused → filled black at 60% opacity, no dot
 * - on-device the focused icon scale-bounces 1.0 → 1.15 → 1.0 (spring)
 *
 * The Icon prop is a render function (matches Lucide's API:
 * `({ size, color }) => JSX`), so we can swap to custom TabIcons later
 * without changing this wrapper.
 */

import React, { useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSequence,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { colors } from '../theme';

interface IconProps {
  size: number;
  color: string;
}

interface Props {
  focused: boolean;
  size: number;
  Icon: React.ComponentType<IconProps>;
  testID?: string;
}

const ACTIVE_COLOR = colors.accent;
// Inactive uses a near-black to mirror the design § 4c "filled black 60%"
// without depending on a dynamic opacity wrapper that would also dim the
// dot if we used parent opacity.
const INACTIVE_COLOR = '#0A0A0B99';

const DOT_SIZE = 4;
const SCALE_DURATION = 180;

export function TabBarIcon({ focused, size, Icon, testID }: Props) {
  const scale = useSharedValue(1);

  useEffect(() => {
    if (focused) {
      scale.value = withSequence(
        withTiming(1.15, {
          duration: SCALE_DURATION,
          easing: Easing.out(Easing.cubic),
        }),
        withTiming(1, {
          duration: SCALE_DURATION,
          easing: Easing.out(Easing.cubic),
        })
      );
    } else {
      scale.value = withTiming(1, { duration: SCALE_DURATION });
    }
  }, [focused, scale]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  return (
    <View testID={testID} style={styles.wrap}>
      <Animated.View style={animatedStyle}>
        <Icon size={size} color={focused ? ACTIVE_COLOR : INACTIVE_COLOR} />
      </Animated.View>
      {focused ? (
        <View testID={testID ? `${testID}-dot` : undefined} style={styles.dot} />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 32,
  },
  dot: {
    width: DOT_SIZE,
    height: DOT_SIZE,
    borderRadius: DOT_SIZE / 2,
    backgroundColor: ACTIVE_COLOR,
    marginTop: 2,
  },
});
