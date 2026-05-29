/**
 * LoadingScreenVariants — Bundle E S2.W3 flesh-out.
 *
 * Exports two variants per design doc § S2.x:
 *   - ConcentricVariant: LoadingRings hero + StageChecklist (4 stages) +
 *     LoadingTipsCarousel (factoid rotator) — the theatrical "advisor
 *     coming together" treatment used by Step14 onboarding (mode=
 *     "onboarding") AND by comparison-mode results loading (50/50 split).
 *   - StreamingCardsVariant: two product-shape ghost cards with
 *     field-by-field reveal (photo → name → price → stars → top-match
 *     badge) + shimmer. KEPT AS A LEAN STUB this commit — the F-S2.X2
 *     task (#32) ships the full StreamingCardsVariant + comparison-mode
 *     rotation behavior. Mode "onboarding" stays concentric here.
 *
 * Min-display floor:
 *   - mode="onboarding" enforces 3,200ms minimum (DEFAULT_MIN_DISPLAY_MS)
 *     even if `ready=true` — the brand moment lands cleanly.
 *   - mode="comparison" fires onDone as soon as `ready=true` flips
 *     (no floor — backend can resolve faster).
 *
 * The `stages` prop is passed through to the inner StageChecklist; the
 * `tips` prop into LoadingTipsCarousel. Step14 passes the
 * region/priorities/peers/calibrate stages matching Step13 so the
 * perceived continuity holds across the build-out → theatrical-load
 * transition.
 */
import React, { useEffect, useMemo, useRef } from 'react';
import { View, StyleSheet, Text } from 'react-native';
import { LoadingRings } from '../components/hero/LoadingRings';
import { StageChecklist, Stage } from '../components/StageChecklist';
import { LoadingTipsCarousel } from '../components/LoadingTipsCarousel';
import { CounterTicker } from '../components/CounterTicker';
import { colors, spacing, typography } from '../theme';

interface Props {
  variant?: 'concentric' | 'streaming';
  mode: 'onboarding' | 'comparison';
  /**
   * When `ready=true` AND mode is "comparison", onDone fires on the next
   * tick. When mode is "onboarding", onDone fires after `minDisplayMs`
   * regardless of `ready` (theatrical floor).
   */
  ready?: boolean;
  onDone?: () => void;
  /** Minimum on-screen duration in onboarding mode (ms). */
  minDisplayMs?: number;
  /** Stage rows for the ConcentricVariant's StageChecklist. */
  stages?: Stage[];
  /** Tip rotator copy. Empty array → tips block omitted. */
  tips?: string[];
  /** Per-tip rotation interval (default 3,200ms per JSX spec). */
  tipIntervalMs?: number;
  /** Cohort-peer copy under the rings (e.g. "47 peers in Capital"). */
  cohortFooter?: string;
  /**
   * Y.B Bundle D rhythm preservation: numeric counter chip below the
   * LoadingRings hero ("0 → 2,074" type beat) — the animation Ahmed
   * explicitly liked on the Bundle D loading screen. Omit to skip the
   * chip entirely. CounterTicker animates 0 → target over 2.4s per the
   * Bundle D motion language.
   */
  counterTarget?: number;
  /** CounterTicker duration override (default 2,400ms per Bundle D feel). */
  counterDurationMs?: number;
  /**
   * Y.B Bundle D rhythm preservation: caption below the counter chip
   * (e.g. "Loading your comparison" for comparison-mode, "Building
   * your shopping advisor" for onboarding-mode). Renders only when
   * supplied — null/undefined → caption block omitted.
   */
  caption?: string;
  testID?: string;
}

const DEFAULT_MIN_DISPLAY_MS = 3200;
const DEFAULT_TIP_INTERVAL_MS = 3200;
const DEFAULT_COUNTER_DURATION_MS = 2400;

export function LoadingScreenVariants({
  variant,
  mode,
  ready,
  onDone,
  minDisplayMs = DEFAULT_MIN_DISPLAY_MS,
  stages,
  tips = [],
  tipIntervalMs = DEFAULT_TIP_INTERVAL_MS,
  cohortFooter,
  counterTarget,
  counterDurationMs = DEFAULT_COUNTER_DURATION_MS,
  caption,
  testID,
}: Props) {
  // Mode "onboarding" always concentric (Step14). Mode "comparison"
  // resolves the variant on first mount via useMemo so re-renders during
  // load do not flip the variant mid-fly.
  const resolvedVariant = useMemo<'concentric' | 'streaming'>(() => {
    if (mode === 'onboarding') return 'concentric';
    if (variant) return variant;
    return Math.random() < 0.5 ? 'concentric' : 'streaming';
  }, [mode, variant]);

  // onDone gate. Fire exactly once — covers both modes.
  const firedRef = useRef(false);

  // Onboarding mode: timer-driven floor. Fires after minDisplayMs.
  useEffect(() => {
    if (mode !== 'onboarding' || !onDone) return;
    const handle = setTimeout(() => {
      if (!firedRef.current) {
        firedRef.current = true;
        onDone();
      }
    }, minDisplayMs);
    return () => clearTimeout(handle);
  }, [mode, onDone, minDisplayMs]);

  // Comparison mode: ready-driven release. Fires on next tick when
  // `ready` flips true so React's render queue settles first.
  useEffect(() => {
    if (mode !== 'comparison' || !onDone || !ready) return;
    const handle = setTimeout(() => {
      if (!firedRef.current) {
        firedRef.current = true;
        onDone();
      }
    }, 0);
    return () => clearTimeout(handle);
  }, [mode, ready, onDone]);

  return (
    <View style={styles.root} testID={testID}>
      {resolvedVariant === 'concentric' ? (
        <View style={styles.concentric} testID="loading-concentric">
          <LoadingRings size={240} testID="loading-rings" />

          {/* Y.B Bundle D rhythm: counter chip "0 → target" below the
              rings — the animation Ahmed explicitly liked. Pill-styled
              emerald chip with the ticking integer at typography.title
              weight. Renders only when counterTarget is supplied. */}
          {counterTarget != null ? (
            <View style={styles.counterChip} testID="loading-counter-chip">
              <CounterTicker
                target={counterTarget}
                duration={counterDurationMs}
                style={styles.counterValue}
                testID="loading-counter"
              />
            </View>
          ) : null}

          {/* Y.B Bundle D rhythm: caption below the counter chip
              ("Loading your comparison" / "Building your shopping
              advisor"). Renders only when caption is supplied. */}
          {caption ? (
            <Text style={styles.caption} testID="loading-caption">
              {caption}
            </Text>
          ) : null}

          {cohortFooter ? (
            <Text style={styles.cohortFooter} testID="loading-cohort-footer">
              {cohortFooter}
            </Text>
          ) : null}

          {stages && stages.length > 0 ? (
            <View style={styles.stageCard} testID="loading-stage-card">
              <StageChecklist stages={stages} />
            </View>
          ) : null}

          {tips.length > 0 ? (
            <LoadingTipsCarousel
              tips={tips}
              intervalMs={tipIntervalMs}
              testID="loading-tips"
              style={styles.tips}
            />
          ) : null}
        </View>
      ) : (
        // StreamingCardsVariant stub kept lean until F-S2.X2 (#32) ships
        // the field-by-field reveal + shimmer. Mode="onboarding" never
        // reaches this branch per the useMemo override above.
        <View testID="loading-streaming" style={styles.streamingStub} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.bg.primary,
  },
  concentric: {
    flex: 1,
    width: '100%',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.xl,
    gap: spacing.xl,
  },
  cohortFooter: {
    ...typography.body,
    color: colors.text.secondary,
    textAlign: 'center',
  },
  // Y.B Bundle D rhythm — neutral pill chip wrapping the CounterTicker
  // per design doc § 3.2 LoadingRings spec (bg.secondary + border.light
  // hairline). Restrained chrome lets the counter beat anchor the
  // moment without competing with the emerald rings above it.
  counterChip: {
    backgroundColor: colors.bg.secondary,
    borderRadius: 999,
    paddingVertical: spacing.xs + 2,
    paddingHorizontal: spacing.base,
    borderWidth: 1,
    borderColor: colors.border.light,
    alignSelf: 'center',
  },
  // Tabular-nums keeps the integer width stable as the ticker counts
  // up — without it the digit shift jitters horizontally on most
  // device fonts. typography.title weight + text.primary.
  counterValue: {
    ...typography.title,
    color: colors.text.primary,
    fontWeight: '700',
    textAlign: 'center',
    fontVariant: ['tabular-nums'],
  },
  // Y.B Bundle D rhythm — caption below counter chip in restrained
  // 13 / text.secondary weight per design doc § 3.2.
  caption: {
    fontSize: 13,
    color: colors.text.secondary,
    textAlign: 'center',
    marginTop: -spacing.md,
  },
  // StageChecklist card matches the Step13 stage card chrome for
  // visual continuity across the Step13 → Step14 transition.
  stageCard: {
    width: '100%',
    backgroundColor: colors.bg.secondary,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: colors.border.light,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  tips: {
    marginTop: spacing.sm,
    paddingHorizontal: spacing.md,
  },
  streamingStub: {
    width: 280,
    height: 200,
    backgroundColor: colors.bg.secondary,
    borderRadius: 16,
  },
});
