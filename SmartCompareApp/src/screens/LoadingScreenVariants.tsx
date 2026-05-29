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
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { View, StyleSheet, Text } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { LoadingRings } from '../components/hero/LoadingRings';
import { StageChecklist, Stage } from '../components/StageChecklist';
import { LoadingTipsCarousel } from '../components/LoadingTipsCarousel';
// CounterTicker import dropped per F-S2.W3.hotfix — LoadingRings hosts
// the single counter chip now. The external duplicate chip + its
// CounterTicker invocation are gone.
import { colors, spacing, typography, radii } from '../theme';
import { motion } from '../theme/motion';

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
        // F-S2.X2 (task #32) — StreamingCardsVariant fleshed out.
        // Two product-shape ghost cards side-by-side with field-by-
        // field reveal (photo → name → price → stars → top-match
        // badge), shimmer overlay on PENDING fields, and an emerald
        // accentLight winner indicator on the right card at final
        // stage. Mode="onboarding" never reaches this branch per
        // the useMemo override above (forced concentric for the
        // Step14 theatrical moment).
        <StreamingCardsVariant testID="loading-streaming" />
      )}
    </View>
  );
}

// F-S2.X2: 5 reveal stages, staggered ~400ms per dispatcher kickoff
// spec. The index drives BOTH cards in lockstep; the right (winner)
// card flips its accent at the final stage so the "Top match" beat
// lands as a finishing flourish.
const REVEAL_STAGES = ['photo', 'name', 'price', 'stars', 'badge'] as const;
type RevealStage = (typeof REVEAL_STAGES)[number];
const REVEAL_STAGE_MS = 400;

// Shimmer travels left → right across the pending field. 60px sweep
// inside the field width gives a clean "glint" effect at the 1.4s
// motion.shimmer cadence without bleeding past the field edges.
const SHIMMER_TRANSLATE_PX = 60;

interface StreamingCardsVariantProps {
  testID?: string;
}

function StreamingCardsVariant({ testID }: StreamingCardsVariantProps) {
  // revealIndex advances 0 → REVEAL_STAGES.length, holding at the
  // top so the final state stays mounted while the loader awaits
  // onDone (which is owned by the outer LoadingScreenVariants).
  const [revealIndex, setRevealIndex] = useState(0);

  useEffect(() => {
    if (revealIndex >= REVEAL_STAGES.length) return;
    const id = setTimeout(
      () => setRevealIndex((prev) => prev + 1),
      REVEAL_STAGE_MS,
    );
    return () => clearTimeout(id);
  }, [revealIndex]);

  return (
    <View style={streamingStyles.row} testID={testID}>
      <StreamingCard
        revealIndex={revealIndex}
        isWinner={false}
        testID="loading-streaming-card-a"
      />
      <StreamingCard
        revealIndex={revealIndex}
        isWinner
        testID="loading-streaming-card-b"
      />
    </View>
  );
}

interface StreamingCardProps {
  revealIndex: number;
  isWinner: boolean;
  testID?: string;
}

function StreamingCard({ revealIndex, isWinner, testID }: StreamingCardProps) {
  const revealedThrough = (stage: RevealStage): boolean =>
    revealIndex > REVEAL_STAGES.indexOf(stage);

  const cardRevealed = revealedThrough('badge');
  // Winner accent flips on at the final stage so the result moment
  // stays "earned" rather than handed-out at mount.
  const accentActive = isWinner && cardRevealed;

  return (
    <View
      style={[
        streamingStyles.card,
        accentActive ? streamingStyles.cardWinner : null,
      ]}
      testID={testID}
    >
      <GhostField
        revealed={revealedThrough('photo')}
        style={streamingStyles.photo}
        testID={`${testID}-photo`}
      />
      <GhostField
        revealed={revealedThrough('name')}
        style={streamingStyles.name}
        testID={`${testID}-name`}
      />
      <GhostField
        revealed={revealedThrough('price')}
        style={streamingStyles.price}
        testID={`${testID}-price`}
      />
      <GhostField
        revealed={revealedThrough('stars')}
        style={streamingStyles.stars}
        testID={`${testID}-stars`}
      />
      {isWinner && revealedThrough('stars') ? (
        <View
          style={streamingStyles.badge}
          testID={`${testID}-badge`}
        >
          <Text style={streamingStyles.badgeText}>Top match</Text>
        </View>
      ) : null}
    </View>
  );
}

interface GhostFieldProps {
  revealed: boolean;
  style: any;
  testID: string;
}

// Each ghost field is either a shimmering placeholder (pending) or
// a solid tinted block (revealed). The placeholder hosts an
// Animated.View that sweeps a soft highlight via translateX driven
// by motion.shimmer (1.4s linear loop).
function GhostField({ revealed, style, testID }: GhostFieldProps) {
  const sweep = useSharedValue(-SHIMMER_TRANSLATE_PX);

  useEffect(() => {
    if (revealed) return;
    sweep.value = withRepeat(
      withTiming(SHIMMER_TRANSLATE_PX, {
        duration: motion.shimmer.duration,
        easing: Easing.linear,
      }),
      // motion.shimmer.repeat = -1 → infinite per token spec.
      motion.shimmer.repeat,
      false,
    );
  }, [revealed, sweep]);

  const sweepStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: sweep.value }],
  }));

  return (
    <View
      style={[style, revealed ? streamingStyles.fieldRevealed : streamingStyles.fieldPending]}
      testID={revealed ? `${testID}-revealed` : `${testID}-pending`}
    >
      {revealed ? null : (
        <Animated.View
          style={[streamingStyles.shimmer, sweepStyle]}
          testID={`${testID}-shimmer`}
        />
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
});

// F-S2.X2: StreamingCardsVariant styles isolated below so the
// concentric path stays the source of truth at the top of the
// styles block. Layout-collapse rubric (Step12 W1.hotfix lesson):
// the parent `row` uses flexDirection:'row' + gap, each card uses
// flex:1 + minWidth:0 so cards share width equally without
// shrinking children to content.
const PHOTO_HEIGHT = 96;
const NAME_HEIGHT = 14;
const PRICE_HEIGHT = 12;
const STARS_HEIGHT = 12;

const streamingStyles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: spacing.md,
    width: '100%',
    paddingHorizontal: spacing.xl,
    alignItems: 'flex-start',
  },
  card: {
    flex: 1,
    minWidth: 0,
    backgroundColor: colors.bg.primary,
    borderRadius: radii.card,
    borderWidth: 1,
    borderColor: colors.border.light,
    padding: spacing.md,
    gap: spacing.sm,
  },
  // Winner card flips to the accentLight bg + accent border at the
  // final reveal stage. Matches ResultsScreen winner-card chrome so
  // the brand cue is consistent between loading + reveal.
  cardWinner: {
    backgroundColor: colors.accentLight,
    borderColor: colors.accent,
  },
  // GhostField pending state: muted bg + overflow:'hidden' so the
  // shimmer translateX doesn't bleed past the field edge.
  fieldPending: {
    backgroundColor: colors.bg.secondary,
    overflow: 'hidden',
  },
  // GhostField revealed state: slightly stronger tint to signal the
  // field is "done." Real product data isn't loaded here — this is
  // a comparison-loading placeholder, not a streaming result card.
  fieldRevealed: {
    backgroundColor: colors.border.light,
  },
  shimmer: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    width: SHIMMER_TRANSLATE_PX,
    backgroundColor: 'rgba(255,255,255,0.55)',
  },
  photo: {
    width: '100%',
    height: PHOTO_HEIGHT,
    borderRadius: 12,
  },
  name: {
    width: '85%',
    height: NAME_HEIGHT,
    borderRadius: 6,
  },
  price: {
    width: '55%',
    height: PRICE_HEIGHT,
    borderRadius: 6,
  },
  stars: {
    width: '70%',
    height: STARS_HEIGHT,
    borderRadius: 6,
  },
  badge: {
    alignSelf: 'flex-start',
    paddingHorizontal: spacing.sm,
    paddingVertical: 4,
    borderRadius: radii.chip,
    backgroundColor: colors.accent,
    marginTop: spacing.xs,
  },
  badgeText: {
    fontSize: 11,
    fontWeight: '700',
    color: colors.cta.onPrimary,
    letterSpacing: 0.4,
    textTransform: 'uppercase',
  },
});
