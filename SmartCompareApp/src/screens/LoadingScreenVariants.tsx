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
// CounterTicker import dropped per F-S2.W3.hotfix — LoadingRings hosts
// the single counter chip now. The external duplicate chip + its
// CounterTicker invocation are gone.
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
   * Y.B Bundle D rhythm preservation: target value for the counter chip
   * inside the LoadingRings hero (ticks 0 → target over motion
   * .counterTick = 2400ms). Per F-S2.W3.hotfix (#37) the external
   * counter chip was de-duplicated — the count now renders inside the
   * LoadingRings hero's built-in chip. LoadingRings defaults to 2074
   * when this prop is omitted.
   */
  counterTarget?: number;
  /**
   * @deprecated F-S2.W3.hotfix — duration is owned by LoadingRings
   * (motion.counterTick = 2400ms) now that the external chip is gone.
   * Kept on the prop interface for back-compat with Step14 wiring
   * but no longer consumed. Will be removed in a follow-up.
   */
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
  // counterDurationMs intentionally accepted-and-unused per
  // F-S2.W3.hotfix deprecation note above; LoadingRings owns the
  // tick duration via motion.counterTick.
  counterDurationMs: _counterDurationMs = DEFAULT_COUNTER_DURATION_MS,
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
          {/* F-S2.W3.hotfix (task #37): pipe counterTarget THROUGH to
              LoadingRings's built-in chip instead of rendering a second
              external chip below it. The hero hosts the single counter
              now — drops the duplicate stack Ahmed flagged ("big
              emerald 2,038 ticking above a separate neutral 46 chip").
              LoadingRings handles tabular-nums + thousands-separator +
              2.4s rAF tick. Default counterTarget = 2074 stays inside
              LoadingRings if Step14 doesn't override. */}
          <LoadingRings
            size={240}
            counterTarget={counterTarget}
            testID="loading-rings"
          />

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
  // F-S2.W3.hotfix: counter chip styles (counterChip + counterValue)
  // removed — LoadingRings hosts the single counter chip with its own
  // styling. The external chip + duplicate CounterTicker invocation
  // are gone per Ahmed's "double counter" report.
  //
  // Y.B Bundle D rhythm — caption below the LoadingRings hero in
  // restrained 13 / text.secondary weight per design doc § 3.2.
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
