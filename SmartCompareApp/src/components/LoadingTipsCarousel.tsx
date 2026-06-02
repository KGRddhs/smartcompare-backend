/**
 * LoadingTipsCarousel — rotating helpful-fact ticker.
 *
 * Phase 3 Task 29. Surfaces below the StageChecklist on the Results
 * loading screen. The component is purely presentational — the parent
 * owns the mount gate (Step14 onboarding shows it immediately;
 * comparison mode shows it via the LoadingScreenVariants wrapper).
 *
 * Per § 4g audit: no scary "still loading" framing — these are
 * confidence-building micro-facts. Empty / single-tip arrays are
 * tolerated (no rotation, no crash).
 *
 * Wave 2 R2 (2026-06-02): rotation now cross-fades via a reanimated
 * shared value driving opacity 1 → 0 → 1. The text swap lands at the
 * trough so users never see a hard text change. Matches
 * docs/claude-design-handoff/ui_kits/mobile/LoadingScreen.jsx TipCard
 * which calls for `qarenTipFade ease infinite` opacity rhythm.
 */

import React, { useEffect, useState } from 'react';
import { Text, TextStyle } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';
import { colors, typography } from '../theme';

interface Props {
  /** Tips to rotate through. Empty array → renders nothing. */
  tips: string[];
  /** Rotation interval. Default 4000ms per design § 3. */
  intervalMs?: number;
  /** Style override (font, color, alignment). */
  style?: TextStyle;
  /** Test/parent hook. The host Animated.View carries this testID; the
   *  inner Text node carries `${testID}-text` for callers that want to
   *  read the rendered string directly. */
  testID?: string;
}

const FADE_OUT_MS = 200;
const FADE_IN_MS = 200;

export function LoadingTipsCarousel({
  tips,
  intervalMs = 4000,
  style,
  testID,
}: Props) {
  const [index, setIndex] = useState(0);
  const opacity = useSharedValue(1);

  useEffect(() => {
    if (tips.length <= 1) return;
    const pendingTimers: ReturnType<typeof setTimeout>[] = [];
    const rotate = () => {
      // Fade-out (200ms) → state swap → fade-in (200ms). We orchestrate
      // the swap via setTimeout instead of the withTiming() callback so
      // the rhythm survives reanimated-mock environments where the
      // animation-callback signature is dropped.
      opacity.value = withTiming(0, { duration: FADE_OUT_MS });
      const swapTimer = setTimeout(() => {
        setIndex((prev) => (prev + 1) % tips.length);
        opacity.value = withTiming(1, { duration: FADE_IN_MS });
      }, FADE_OUT_MS);
      pendingTimers.push(swapTimer);
    };
    const intervalId = setInterval(rotate, intervalMs);
    return () => {
      clearInterval(intervalId);
      for (const t of pendingTimers) clearTimeout(t);
    };
  }, [tips, intervalMs, opacity]);

  const animStyle = useAnimatedStyle(() => ({
    opacity: opacity.value,
  }));

  if (tips.length === 0) return null;

  // Clamp index when the tips list shrinks under us (defensive — parent
  // is unlikely to mutate, but cheap to guard).
  const safeIndex = index < tips.length ? index : 0;
  const textTestID = testID ? `${testID}-text` : undefined;

  return (
    <Animated.View testID={testID} style={animStyle}>
      <Text testID={textTestID} style={[styles, style]}>
        {tips[safeIndex]}
      </Text>
    </Animated.View>
  );
}

const styles: TextStyle = {
  ...typography.caption,
  color: colors.text.secondary,
  textAlign: 'center',
};
