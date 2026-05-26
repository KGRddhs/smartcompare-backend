/**
 * SlideTransition — Bundle E S0.4.
 *
 * Wraps an onboarding step's content in an Animated.View that slides in
 * from the side when `step` changes. Direction mirrors based on
 * I18nManager.isRTL: LTR slides in from right (+width), RTL slides in
 * from left (-width). Re-renders with the same `step` value do NOT
 * retrigger the slide — only step changes drive the animation.
 *
 * Contract: __tests__/primitives/SlideTransition.test.tsx
 *   - testID forwarded to the animated wrapper
 *   - data-direction='ltr' OR 'rtl' prop exposed for direction assertion
 *   - same-step re-render keeps the same direction prop (no retrigger)
 *
 * The animation duration + easing come from motion.screenTransition
 * (320ms cubic-bezier 0.32,0.72,0,1 — see src/theme/motion.ts).
 */
import React, { useEffect, useRef } from 'react';
import { I18nManager, Dimensions } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
} from 'react-native-reanimated';
import { motion } from '../theme/motion';

interface Props {
  step: number;
  children: React.ReactNode;
  testID?: string;
}

export function SlideTransition({ step, children, testID }: Props) {
  const isRTL = I18nManager.isRTL;
  const direction: 'ltr' | 'rtl' = isRTL ? 'rtl' : 'ltr';
  const width = Dimensions.get('window').width;
  const startOffset = isRTL ? -width : width;

  const translateX = useSharedValue(startOffset);
  const prevStepRef = useRef(step);

  useEffect(() => {
    if (prevStepRef.current === step) {
      // Same step — do not retrigger (the contract).
      return;
    }
    prevStepRef.current = step;
    translateX.value = startOffset;
    translateX.value = withTiming(0, {
      duration: motion.screenTransition.duration,
      easing: motion.screenTransition.easing,
    });
  }, [step, startOffset, translateX]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }],
  }));

  // The data-direction prop is consumed by the test scaffold. It's also
  // a useful debug hook for visual regression sweeps.
  return (
    <Animated.View
      style={[{ flex: 1 }, animatedStyle]}
      testID={testID}
      // @ts-expect-error — data-* props are not strictly typed on
      // Animated.View but RN forwards them to the underlying host node.
      data-direction={direction}
    >
      {children}
    </Animated.View>
  );
}
