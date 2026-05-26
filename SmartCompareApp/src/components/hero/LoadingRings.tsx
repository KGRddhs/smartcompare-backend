/**
 * LoadingRings — Bundle E S0.1b hero illustration.
 *
 * Used on Step14Loading (theatrical 3.2s) and reused by LoadingScreen's
 * ConcentricVariant during comparison loading. Three emerald rings
 * expanding outward (staggered 700ms, 2.1s loop), QarenIcon center, plus
 * a counter chip below ticking 0 → counterTarget over 2.4s ease-out-cubic
 * formatted with thousands separator.
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/LoadingScreen.jsx
 * + design doc § 3.2 LoadingRings.
 *
 * Contract: __tests__/hero/LoadingRings.test.tsx
 *   - default snapshot
 *   - custom counterTarget snapshot
 *   - animated={false} + counterTarget renders FINAL value formatted as
 *     `2,074` (thousands separator); NEVER raw `2074`
 *
 * Animation uses motion.counterTick (2400ms ease-out-cubic) and ring loop
 * staggers via withDelay + withRepeat. useReducedMotion no-ops.
 */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import {
  useSharedValue,
  withRepeat,
  withTiming,
  withDelay,
  Easing,
} from 'react-native-reanimated';
import { colors, spacing, radii } from '../../theme';
import { QaranIcon } from '../../icons/QaranIcon';
import { motion } from '../../theme/motion';

interface Props {
  size?: number;
  counterTarget?: number;
  counterLabel?: string;
  animated?: boolean;
  testID?: string;
}

const VIEWBOX = 320;
const CENTER = VIEWBOX / 2;
const RING_BASE_R = 60;
const RING_TARGET_R = 150;
const RING_DURATION_MS = 2100;
const RING_STAGGER_MS = 700;

function formatThousands(value: number): string {
  return value.toLocaleString('en-US');
}

export function LoadingRings({
  size = 320,
  counterTarget = 2074,
  counterLabel,
  animated = true,
  testID,
}: Props) {
  const ring0 = useSharedValue(RING_BASE_R);
  const ring1 = useSharedValue(RING_BASE_R);
  const ring2 = useSharedValue(RING_BASE_R);

  // Counter rendered as plain RN state (not a worklet) so the displayed
  // value is the source of truth for tests. requestAnimationFrame drives
  // the tick locally; we cap at counterTarget.
  const [counter, setCounter] = useState<number>(animated ? 0 : counterTarget);

  useEffect(() => {
    if (!animated) {
      setCounter(counterTarget);
      return;
    }
    const drive = (sv: { value: number }, delayMs: number) => {
      sv.value = withDelay(
        delayMs,
        withRepeat(
          withTiming(RING_TARGET_R, {
            duration: RING_DURATION_MS,
            easing: Easing.out(Easing.cubic),
          }),
          -1,
          false,
        ),
      );
    };
    drive(ring0, 0);
    drive(ring1, RING_STAGGER_MS);
    drive(ring2, RING_STAGGER_MS * 2);

    const startedAt = Date.now();
    const duration = motion.counterTick.duration;
    // rAF in the RN runtime; fall back to setTimeout in Jest where rAF
    // is not defined. The fallback gives us the test contract (final
    // value reached) even though the cadence is coarser.
    const schedule: (cb: () => void) => unknown =
      typeof requestAnimationFrame === 'function'
        ? requestAnimationFrame
        : (cb) => setTimeout(cb, 16);
    const cancel: (id: any) => void =
      typeof cancelAnimationFrame === 'function'
        ? cancelAnimationFrame
        : clearTimeout;
    let rafId: any;
    const tick = () => {
      const elapsed = Date.now() - startedAt;
      const t = Math.min(1, elapsed / duration);
      // ease-out-cubic
      const eased = 1 - Math.pow(1 - t, 3);
      setCounter(Math.round(eased * counterTarget));
      if (t < 1) {
        rafId = schedule(tick);
      }
    };
    rafId = schedule(tick);
    return () => {
      if (rafId !== undefined) cancel(rafId);
    };
  }, [animated, counterTarget, ring0, ring1, ring2]);

  return (
    <View style={[styles.root, { width: size }]} testID={testID}>
      <View style={[styles.ringWrap, { width: size, height: size }]}>
        <Svg width={size} height={size} viewBox={`0 0 ${VIEWBOX} ${VIEWBOX}`}>
          {[ring0, ring1, ring2].map((sv, i) => {
            const r = sv.value;
            const progress = (r - RING_BASE_R) / (RING_TARGET_R - RING_BASE_R);
            const opacity = Math.max(0, 1 - progress);
            return (
              <Circle
                key={`ring-${i}`}
                testID={`loading-rings-ring-${i}`}
                cx={CENTER}
                cy={CENTER}
                r={r}
                fill="none"
                stroke={colors.accent}
                strokeWidth={2.5}
                opacity={opacity}
              />
            );
          })}
        </Svg>
        <View style={styles.center} pointerEvents="none" testID="loading-rings-logo">
          <QaranIcon size={Math.round(size * 0.4)} />
        </View>
      </View>
      <View style={styles.chip} testID="loading-rings-counter-chip">
        <Text style={styles.chipNumber}>{formatThousands(counter)}</Text>
        {counterLabel ? <Text style={styles.chipLabel}>{counterLabel}</Text> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    alignSelf: 'center',
    alignItems: 'center',
    paddingVertical: spacing.base,
  },
  ringWrap: {
    alignItems: 'center',
    justifyContent: 'center',
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
  chip: {
    marginTop: spacing.lg,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.base,
    backgroundColor: colors.bg.secondary,
    borderRadius: radii.chip,
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: spacing.sm,
    borderWidth: 1,
    borderColor: colors.border.light,
  },
  chipNumber: {
    fontSize: 20,
    fontWeight: '700',
    lineHeight: 20 * 1.2,
    color: colors.accentDark,
    // Tabular nums so the digits don't reflow as the counter ticks.
    fontVariant: ['tabular-nums'],
  },
  chipLabel: {
    fontSize: 12,
    fontWeight: '500',
    lineHeight: 12 * 1.3,
    color: colors.text.secondary,
  },
});
