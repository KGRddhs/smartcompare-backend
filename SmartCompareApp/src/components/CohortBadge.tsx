/**
 * CohortBadge — inline social-proof pill on the Results screen.
 *
 * Phase 3 Task 31. "Like 12 shoppers in Capital also picked this." Slides
 * from right (LTR) / left (RTL) on mount with 240ms ease-out + opacity
 * fade per design § 4b. The cohort moat is the differentiator — this
 * badge surfaces it inline, never buried (build principle 6).
 *
 * Renders nothing when peer count is non-positive or the governorate
 * is missing. Defensive — the orchestrator may pass partial cohort
 * data while the SSE stream is still resolving.
 */

import React, { useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { colors, spacing, typography, radii } from '../theme';

interface Props {
  /** Number of cohort peers who also picked the winner. */
  peerCount: number;
  /** User's governorate (Capital / Muharraq / Northern / Southern). */
  governorate: string;
  /** Whether to slide-in from the left (RTL) instead of right (LTR). */
  isRTL?: boolean;
  /** Test/parent hook. */
  testID?: string;
}

const SLIDE_PX = 24;
const SLIDE_DURATION = 240;

export function CohortBadge({ peerCount, governorate, isRTL = false, testID }: Props) {
  const { t } = useTranslation();
  // Slide enters from the trailing side (right under LTR, left under RTL).
  const start = isRTL ? -SLIDE_PX : SLIDE_PX;
  const translateX = useSharedValue(start);
  const opacity = useSharedValue(0);

  useEffect(() => {
    translateX.value = withTiming(0, {
      duration: SLIDE_DURATION,
      easing: Easing.out(Easing.cubic),
    });
    opacity.value = withTiming(1, {
      duration: SLIDE_DURATION,
      easing: Easing.out(Easing.cubic),
    });
  }, [translateX, opacity]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }],
    opacity: opacity.value,
  }));

  if (peerCount <= 0 || !governorate) return null;

  const copy = t('results.cohort_badge', {
    count: peerCount,
    governorate,
    defaultValue: `Like ${peerCount} shoppers in ${governorate}`,
  });

  return (
    <Animated.View
      testID={testID}
      // Dataset props for QA + RTL audit assertions; ignored by RN runtime.
      {...{
        'data-peer-count': peerCount,
        'data-governorate': governorate,
        'data-direction': isRTL ? 'rtl' : 'ltr',
      }}
      accessibilityRole="text"
      accessibilityLabel={copy}
      style={[styles.badge, animatedStyle]}
    >
      <View style={styles.dot} />
      <Text style={styles.copy}>{copy}</Text>
    </Animated.View>
  );
}

const DOT_SIZE = 8;

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: colors.accentLight,
    borderRadius: radii.chip,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
  },
  dot: {
    width: DOT_SIZE,
    height: DOT_SIZE,
    borderRadius: DOT_SIZE / 2,
    backgroundColor: colors.accent,
  },
  copy: {
    ...typography.caption,
    color: colors.text.primary,
    fontWeight: '600',
  },
});
