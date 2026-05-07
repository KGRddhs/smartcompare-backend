/**
 * LoadingTipsCarousel — rotating helpful-fact ticker.
 *
 * Phase 3 Task 29. Surfaces below the StageChecklist on the Results
 * loading screen ONLY after the wait exceeds the 8s threshold per
 * design § 3 ("tips during deep waits"). The component is purely
 * presentational — the parent owns the 8s mount gate.
 *
 * Per § 4g audit: no scary "still loading" framing — these are
 * confidence-building micro-facts ("47 cohort peers in {governorate}
 * helped train this match"). Empty / single-tip arrays are tolerated
 * (no rotation, no crash).
 */

import React, { useEffect, useState } from 'react';
import { Text, TextStyle } from 'react-native';
import { colors, typography } from '../theme';

interface Props {
  /** Tips to rotate through. Empty array → renders nothing. */
  tips: string[];
  /** Rotation interval. Default 4000ms per design § 3. */
  intervalMs?: number;
  /** Style override (font, color, alignment). */
  style?: TextStyle;
  /** Test/parent hook. */
  testID?: string;
}

export function LoadingTipsCarousel({
  tips,
  intervalMs = 4000,
  style,
  testID,
}: Props) {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (tips.length <= 1) return;
    const id = setInterval(() => {
      setIndex((prev) => (prev + 1) % tips.length);
    }, intervalMs);
    return () => clearInterval(id);
  }, [tips, intervalMs]);

  if (tips.length === 0) return null;

  // Clamp index when the tips list shrinks under us (defensive — parent
  // is unlikely to mutate, but cheap to guard).
  const safeIndex = index < tips.length ? index : 0;

  return (
    <Text testID={testID} style={[styles, style]}>
      {tips[safeIndex]}
    </Text>
  );
}

const styles: TextStyle = {
  ...typography.caption,
  color: colors.text.secondary,
  textAlign: 'center',
};
