/**
 * CounterTicker — animated number display, 0 → target over `duration` ms.
 *
 * Phase 2 Task 10. Used for "388 GCC shoppers", BHD prices on Results, and
 * cohort peer counts. See design spec Section 1 motion language ("Counter
 * tick" row: 800ms ease-out).
 *
 * Why we don't render a Reanimated.Text directly: the animated value is a
 * float that we want to render as an integer (no flickery decimals). We
 * drive a `useSharedValue`, listen with `useAnimatedReaction`, and commit
 * the rounded integer to React state. On JS-mock land (jest), the reaction
 * fires once with the final value — tests assert end-state. On-device, the
 * 60fps reaction interpolates and the displayed integer ticks naturally.
 */

import React, { useEffect, useState } from 'react';
import { Text, TextStyle } from 'react-native';
import {
  useSharedValue,
  useAnimatedReaction,
  withTiming,
  Easing,
  runOnJS,
} from 'react-native-reanimated';

interface CounterTickerProps {
  /** Final value to count up to. Negative inputs clamp to 0. */
  target: number;
  /** Animation duration in ms. Default 800 per design spec. */
  duration?: number;
  /** String prepended to the number, e.g. "$" or "≈". */
  prefix?: string;
  /** String appended, e.g. " BHD" or " peers". */
  suffix?: string;
  /** Text style override (font, color, size). */
  style?: TextStyle;
  /** Test hook. */
  testID?: string;
}

export function CounterTicker({
  target,
  duration = 800,
  prefix = '',
  suffix = '',
  style,
  testID,
}: CounterTickerProps) {
  const clampedTarget = Math.max(0, Math.round(target));
  const [display, setDisplay] = useState<number>(clampedTarget);
  const progress = useSharedValue<number>(0);

  useEffect(() => {
    progress.value = 0;
    progress.value = withTiming(clampedTarget, {
      duration,
      easing: Easing.out(Easing.cubic),
    });
    // Reanimated's useAnimatedReaction (below) drives the on-device tick from
    // 0 to clampedTarget. The setDisplay here is the safety floor: if the
    // reaction never fires (some test environments stub it as no-op), we
    // still commit the final value so the visible number stays correct.
    setDisplay(clampedTarget);
  }, [clampedTarget, duration, progress]);

  useAnimatedReaction(
    () => progress.value,
    (current) => {
      runOnJS(setDisplay)(Math.round(current));
    },
    [clampedTarget]
  );

  return (
    <Text style={style} testID={testID}>{`${prefix}${display}${suffix}`}</Text>
  );
}
