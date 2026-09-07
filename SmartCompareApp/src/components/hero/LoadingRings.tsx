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
 *
 * B3 (mobile checkup, 2026-09-06) — the three ring radii are UI-thread shared
 * values, but the render used to sample them as PLAIN NUMBERS (`const r =
 * sv.value`) into plain `react-native-svg` Circles. Mutating a shared value
 * schedules no React render, so the rings only moved when something else
 * re-rendered the component — in practice the counter's own rAF pump. That
 * pump is bounded by motion.counterTick (2400ms), so the rings ran for ~2.4s,
 * stuttered at whatever cadence the parent re-rendered at, and then FROZE
 * mid-loop while the shared values kept looping on the UI thread forever. On
 * ResultsScreen's loading branch (no timer at all) the freeze was total, for
 * the whole 30s–120s of a compare. Each of those render-time reads was also a
 * BLOCKING synchronous JS→UI-runtime hop (reanimated 4's `makeMutableNative`
 * getter) — 3 per render at display rate, on the app's heaviest screen — and
 * tripped reanimated's "Reading from `value` during component render" warning
 * in dev. The radii now reach the pixels through `useAnimatedProps` on an
 * `Animated.createAnimatedComponent(Circle)`, so the loop runs entirely on the
 * UI thread for the life of the load and the JS thread reads nothing.
 * Geometry is unchanged: a driver at RING_BASE_R still renders r=60/opacity=1,
 * which is exactly what `animated={false}` keeps rendering.
 *
 * Contract: __tests__/hero/LoadingRings.test.tsx (snapshots + counter format)
 *           __tests__/hero/LoadingRings.animation.test.tsx (driver binding)
 */
import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import Animated, {
  useSharedValue,
  useAnimatedProps,
  withRepeat,
  withTiming,
  withDelay,
  Easing,
} from 'react-native-reanimated';
import type { SharedValue } from 'react-native-reanimated';
import { colors, spacing, radii } from '../../theme';
// F-S2.W3.hotfix (task #37): swap center from QaranIcon (magnifier
// mark, reads as "heavy black blob" at 96px with strokeWidth 10) to
// QarenLogo (brand Q-ring with emerald accent dot). The brand mark is
// the intended center per design doc § 3.2 LoadingRings — the
// magnifier is the app-flow glyph for product comparison, NOT the
// loading hero. Reduces visual weight + ships the actual brand cue.
import QarenLogo from '../QarenLogo';
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

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

function formatThousands(value: number): string {
  return value.toLocaleString('en-US');
}

interface RingProps {
  index: number;
  /** UI-thread driver holding this ring's current radius. */
  radius: SharedValue<number>;
}

/**
 * One expanding emerald ring, bound to its UI-thread radius driver.
 *
 * Extracted as its own component ONLY because hooks cannot be called inside
 * the `[ring0, ring1, ring2].map()` that used to render these inline. It
 * renders a single Circle, so the host tree shape is identical to the pre-B3
 * inline map.
 */
function Ring({ index, radius }: RingProps) {
  const animatedProps = useAnimatedProps(() => {
    const r = radius.value;
    // Fade the ring out as it expands: full opacity at the base radius,
    // transparent by the time it reaches the target. Same ramp the pre-B3
    // render-time read computed — it just runs on the UI thread now.
    const progress = (r - RING_BASE_R) / (RING_TARGET_R - RING_BASE_R);
    return { r, opacity: Math.max(0, 1 - progress) };
  });

  return (
    <AnimatedCircle
      testID={`loading-rings-ring-${index}`}
      cx={CENTER}
      cy={CENTER}
      fill="none"
      stroke={colors.accent}
      strokeWidth={2.5}
      animatedProps={animatedProps}
    />
  );
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
          {[ring0, ring1, ring2].map((sv, i) => (
            <Ring key={`ring-${i}`} index={i} radius={sv} />
          ))}
        </Svg>
        <View style={styles.center} pointerEvents="none" testID="loading-rings-logo">
          {/* QarenLogo at 0.22 of the rings size — visually centered
              against the 3-ring stack without bleeding into the inner
              ring's r=60 footprint. Was QaranIcon at 0.4 (96px stroke
              ~10px) which read as a heavy magnifier blob. The
              QarenLogo Q-ring stays light + ships the brand mark. */}
          <QarenLogo size={Math.round(size * 0.22)} />
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
