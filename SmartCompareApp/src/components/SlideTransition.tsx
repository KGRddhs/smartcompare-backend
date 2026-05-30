/**
 * SlideTransition — Bundle E S0.4.
 *
 * Wraps an onboarding step's content in an Animated.View that slides in
 * from the side when `step` changes. Direction mirrors based on
 * I18nManager.isRTL: LTR slides in from right (+width), RTL slides in
 * from left (-width). Re-renders with the same `step` value do NOT
 * retrigger the slide — only step changes drive the animation.
 *
 * **Initial mount = visible (translateX:0).** Per F-S2.CRITICAL (task #40)
 * the prior implementation initialized `translateX = startOffset` (e.g.
 * +393px on iPhone) which left first-mount content fully offscreen.
 * The early-return guard `prevStepRef.current === step` fires on initial
 * effect run (ref initialized to the same step value), so the
 * `withTiming(0)` slide-in never ran. Result: every fresh-session entry
 * (Google sign-in, Apple sign-in, fresh device) landed on a blank
 * Step01 with only the warm-wash bg + chrome visible. Fix: initial
 * shared-value is 0 (settled at destination), and the useEffect drives
 * the slide-in only on actual step CHANGES — animating from offscreen
 * INTO place when the user advances/retreats.
 *
 * Contract: __tests__/primitives/SlideTransition.test.tsx
 *   - testID forwarded to the animated wrapper
 *   - data-direction='ltr' OR 'rtl' prop exposed for direction assertion
 *   - same-step re-render keeps the same direction prop (no retrigger)
 *   - F-S2.CRITICAL: initial mount renders with translateX:0 (visible);
 *     animation only fires when `step` changes from prior render
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

  // F-S2.CRITICAL (task #40): initial translateX = 0 (settled at
  // destination, content visible on first mount). Slide-in animation
  // is driven by the useEffect below ONLY when `step` changes from
  // the prior render — first mount is already at the destination so
  // no animation runs on entry. Prior implementation initialized
  // this to `startOffset` (+/-width) which left first-mount content
  // offscreen indefinitely because the same-step early-return guard
  // fires on initial effect run (ref initialized to the same step).
  const translateX = useSharedValue(0);
  const prevStepRef = useRef(step);

  useEffect(() => {
    if (prevStepRef.current === step) {
      // Same step — do not retrigger (the contract). On initial
      // mount this fires because prevStepRef was initialized to the
      // same `step`; we're already at translateX=0 so no animation
      // is needed and the content stays visible.
      return;
    }
    prevStepRef.current = step;
    // Step CHANGED — snap to offscreen first, then animate IN to 0.
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
      // data-* prop forwards through to the host node so the test scaffold
      // can target it via `node.props['data-direction']`. RN doesn't strip
      // unknown View props.
      {...({ 'data-direction': direction } as Record<string, string>)}
    >
      {children}
    </Animated.View>
  );
}
