/**
 * Four corner brackets centered on screen with a subtle pulse loop.
 * Spec: docs/plans/2026-05-12-bundle-bcd-consolidated-design.md § 4.6
 */
import React, { useEffect } from 'react';
import { Dimensions, StyleSheet, View } from 'react-native';
import Svg, { Path } from 'react-native-svg';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';

const VIEWPORT_WIDTH = Dimensions.get('window').width;
const SIZE = Math.min(VIEWPORT_WIDTH * 0.7, 280);
const BRACKET = 30;
const STROKE = 3;
const COLOR = '#FFFFFF';

export default function ScannerReticle() {
  const pulse = useSharedValue(1);

  useEffect(() => {
    pulse.value = withRepeat(withTiming(1.04, { duration: 1200 }), -1, true);
  }, [pulse]);

  const animStyle = useAnimatedStyle(() => ({
    transform: [{ scale: pulse.value }],
  }));

  return (
    <View style={styles.overlay} pointerEvents="none">
      <Animated.View style={animStyle}>
        <Svg width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`}>
          <Path
            d={`M 0 ${BRACKET} L 0 0 L ${BRACKET} 0`}
            stroke={COLOR}
            strokeWidth={STROKE}
            fill="none"
          />
          <Path
            d={`M ${SIZE - BRACKET} 0 L ${SIZE} 0 L ${SIZE} ${BRACKET}`}
            stroke={COLOR}
            strokeWidth={STROKE}
            fill="none"
          />
          <Path
            d={`M ${SIZE} ${SIZE - BRACKET} L ${SIZE} ${SIZE} L ${SIZE - BRACKET} ${SIZE}`}
            stroke={COLOR}
            strokeWidth={STROKE}
            fill="none"
          />
          <Path
            d={`M ${BRACKET} ${SIZE} L 0 ${SIZE} L 0 ${SIZE - BRACKET}`}
            stroke={COLOR}
            strokeWidth={STROKE}
            fill="none"
          />
        </Svg>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
