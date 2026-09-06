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
import { useTranslation } from 'react-i18next';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { LoadingRings } from '../components/hero/LoadingRings';
import { StageChecklist, Stage, StageStatus } from '../components/StageChecklist';
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
// A2 — the derived comparison checklist is PACED TO THE REAL COMPARE,
// not to a decorative 900ms metronome.
//
// It used to advance on a flat `STAGE_CYCLE_MS = 900` interval, so all
// five emerald checkmarks — including "Cross-checking 25+ retailers" and
// "Locking in your top match" — read DONE at t=4.5s while a cold compare
// runs ~25-31s on prod. The loader stays mounted the whole time (see the
// freeze note below), so the user then stared at a finished checklist for
// another ~20-26 seconds. That is a claim the app cannot back: it says
// the retailers have been checked when the request has not returned.
//
// Cumulative offsets (NOT a flat cadence) at which each stage lands its
// check — the first two go fast so the list visibly moves the moment it
// mounts, then the stages that genuinely dominate wall time stretch:
//
//   cursor 1 @  1.2s   "Understanding your query" done
//   cursor 2 @  4.2s   "Reading specs" done
//   cursor 3 @ 12.0s   "Cross-checking 25+ retailers" done
//   cursor 4 @ 19.5s   "Analyzing reviews" done
//   cursor 5 @ 26.0s   "Locking in your top match" done  <- the freeze
//
// 26s sits inside the 35s COMPARE_TIMEOUT_MS ceiling (api.ts) and past
// the measured 24.5-31.5s cold envelope, so the last check no longer
// lands before the work plausibly could. A FAST compare unmounts the
// loader mid-walk, which is honest (work finished early) and already
// safe — the effect clears its own timers on unmount.
const DEFAULT_COMPARISON_STAGE_DONE_AT_MS = [1200, 4200, 12000, 19500, 26000];
// Offset for a stage index past the end of the table. The schedule and
// DEFAULT_COMPARISON_STAGE_KEYS are the same length today; this exists so
// that if a sixth default stage is ever added and the schedule is not
// extended with it, that stage still lands a check instead of sitting
// `active` forever — a stall is the same class of lie A2 exists to fix,
// just in the other direction.
const STAGE_SCHEDULE_TAIL_STEP_MS = 6500;

function stageDoneAtMs(index: number): number {
  const table = DEFAULT_COMPARISON_STAGE_DONE_AT_MS;
  if (index < table.length) return table[index];
  return (
    table[table.length - 1] +
    (index - table.length + 1) * STAGE_SCHEDULE_TAIL_STEP_MS
  );
}

// A2 — the caption escalates on elapsed time so a long wait is narrated
// instead of sitting on one static string for half a minute. `onStatus`
// (the real SSE progress feed) is unreachable in the shipped client
// while ENABLE_EXPO_FETCH_SSE is false, so there is nothing else moving
// on this screen once the checklist freezes.
const CAPTION_ESCALATE_1_MS = 8000;
const CAPTION_ESCALATE_2_MS = 18000;
const CAPTION_ESCALATION_KEYS = [
  'loading.caption.still_checking',
  'loading.caption.almost_there',
];
// Wave 2: default comparison-mode factoid card rotates every ~5s. The
// LoadingTipsCarousel uses cross-fade internally so the rotation is
// gentle (not a hard cut) — per "no scary copy / no jitter" rule.
const COMPARISON_TIP_INTERVAL_MS = 5000;

// Default comparison-mode i18n keys. Caller can override via the
// `stages` / `tips` props (Step14 onboarding does this; HomeScreen
// relies on the defaults).
const DEFAULT_COMPARISON_STAGE_KEYS = [
  { id: '0', key: 'loading.stage.understanding' },
  { id: '1', key: 'loading.stage.reading_specs' },
  { id: '2', key: 'loading.stage.cross_checking' },
  { id: '3', key: 'loading.stage.analyzing_reviews' },
  { id: '4', key: 'loading.stage.locking_match' },
];

const DEFAULT_COMPARISON_TIP_KEYS = [
  'loading.tip.peer_prioritize',
  'loading.tip.cross_checks',
  'loading.tip.work_for_you',
  'loading.tip.save_offline',
];

// Walks the active-stage cursor through 0..stages.length, with one
// "all done" hold beat at the end before the cycle restarts so users
// see every checkmark land before the list resets. Pure helper so
// the test can verify timer math independently of the React tree.
function deriveStageStatuses(
  count: number,
  cursor: number,
): StageStatus[] {
  const result: StageStatus[] = [];
  for (let i = 0; i < count; i++) {
    if (i < cursor) result.push('done');
    else if (i === cursor) result.push('active');
    else result.push('pending');
  }
  return result;
}

export function LoadingScreenVariants({
  variant,
  mode,
  ready,
  onDone,
  minDisplayMs = DEFAULT_MIN_DISPLAY_MS,
  stages,
  tips,
  tipIntervalMs,
  cohortFooter,
  counterTarget,
  // counterDurationMs intentionally accepted-and-unused per
  // F-S2.W3.hotfix deprecation note above; LoadingRings owns the
  // tick duration via motion.counterTick.
  counterDurationMs: _counterDurationMs = DEFAULT_COUNTER_DURATION_MS,
  caption,
  testID,
}: Props) {
  const { t } = useTranslation();
  // Mode "onboarding" always concentric (Step14). Mode "comparison"
  // resolves the variant on first mount via useMemo so re-renders during
  // load do not flip the variant mid-fly.
  const resolvedVariant = useMemo<'concentric' | 'streaming'>(() => {
    if (mode === 'onboarding') return 'concentric';
    if (variant) return variant;
    return Math.random() < 0.5 ? 'concentric' : 'streaming';
  }, [mode, variant]);

  // Wave 2: when the caller supplies no stages AND we're in comparison
  // mode, derive a self-walking 5-stage default. Cursor advances 0..count
  // then FREEZES at count (R3 fix per Gate B): on wall floors of 14-25s
  // a modulo loop made all 5 emerald checkmarks vanish back to pending
  // 2-4 times per comparison. The loader stays mounted via
  // navigateToResultsWithFloor until backend resolves, so the frozen
  // all-done state IS the correct UX — work is locked in.
  const shouldDeriveStages = !stages && mode === 'comparison';
  const [stageCursor, setStageCursor] = useState(0);
  const stageCount = DEFAULT_COMPARISON_STAGE_KEYS.length;
  useEffect(() => {
    if (!shouldDeriveStages) return;
    // A2 — one timeout PER STAGE, all armed at mount against the schedule
    // above, instead of a flat repeating interval. Nothing is scheduled
    // past the last offset, so the freeze costs no timer at all (the old
    // interval kept firing into a setState that bailed).
    const ids = Array.from({ length: stageCount }, (_, i) =>
      setTimeout(() => {
        // Freeze at count and never move backwards — no wrap. R3/Gate B:
        // a modulo cycle made all five emerald checkmarks vanish back to
        // pending 2-4x per comparison.
        setStageCursor((prev) => Math.min(Math.max(prev, i + 1), stageCount));
      }, stageDoneAtMs(i)),
    );
    return () => ids.forEach(clearTimeout);
  }, [shouldDeriveStages, stageCount]);

  // A2 — elapsed-time caption escalation. Phase 0 = the caller's caption,
  // 1 at 8s, 2 at 18s. Comparison mode only: the onboarding caption is a
  // 3.2s brand beat with nothing to escalate about.
  const [captionPhase, setCaptionPhase] = useState(0);
  useEffect(() => {
    if (mode !== 'comparison') return;
    const first = setTimeout(() => setCaptionPhase(1), CAPTION_ESCALATE_1_MS);
    const second = setTimeout(() => setCaptionPhase(2), CAPTION_ESCALATE_2_MS);
    return () => {
      clearTimeout(first);
      clearTimeout(second);
    };
  }, [mode]);

  // The escalation is a STAND-IN for the dead progress feed, so it must
  // yield the moment a real one appears: if the caller ever updates the
  // caption prop (an `onStatus` message once ENABLE_EXPO_FETCH_SSE is on,
  // per #118), the caller's live string wins from then on.
  //
  // This is a LATCH, not a per-render equality against the mount value.
  // HomeScreen's caption is `statusMessage || t('results.loading.finding')`
  // and it clears `statusMessage` on completion, so a live feed would
  // return the prop to exactly its mount string — an equality check would
  // read that as "caller went static again" and resume narrating over a
  // feed that is demonstrably alive. Once live, always live, for this mount.
  //
  // Set during render via the documented adjust-state-on-prop-change
  // pattern: React re-runs this component before painting, so the caller's
  // string is never displaced by an escalation string for even one frame.
  const [mountCaption] = useState(caption);
  const [callerFeedIsLive, setCallerFeedIsLive] = useState(false);
  if (!callerFeedIsLive && caption !== mountCaption) {
    setCallerFeedIsLive(true);
  }
  const effectiveCaption = useMemo(() => {
    if (mode !== 'comparison' || !caption) return caption;
    if (callerFeedIsLive || captionPhase === 0) return caption;
    return t(CAPTION_ESCALATION_KEYS[captionPhase - 1], {
      defaultValue: caption,
    });
  }, [mode, caption, callerFeedIsLive, captionPhase, t]);

  // Effective stages — caller override OR derived comparison defaults.
  const effectiveStages = useMemo<Stage[] | undefined>(() => {
    if (stages) return stages;
    if (!shouldDeriveStages) return undefined;
    const statuses = deriveStageStatuses(
      DEFAULT_COMPARISON_STAGE_KEYS.length,
      stageCursor,
    );
    return DEFAULT_COMPARISON_STAGE_KEYS.map((row, i) => ({
      id: row.id,
      label: t(row.key, { defaultValue: row.key }),
      status: statuses[i],
    }));
  }, [stages, shouldDeriveStages, stageCursor, t]);

  // Effective tips — caller override OR derived comparison defaults
  // (translated). Onboarding without an override gets `undefined` so
  // Step14's own ONBOARDING_TIPS sequence is the only path to render.
  const effectiveTips = useMemo<string[] | undefined>(() => {
    if (tips) return tips;
    if (mode !== 'comparison') return undefined;
    return DEFAULT_COMPARISON_TIP_KEYS.map((key) =>
      t(key, { defaultValue: key }),
    );
  }, [tips, mode, t]);

  // Tip rotation interval: caller override OR 5s comparison default OR
  // legacy 3.2s onboarding default.
  const effectiveTipIntervalMs =
    tipIntervalMs ??
    (mode === 'comparison' ? COMPARISON_TIP_INTERVAL_MS : DEFAULT_TIP_INTERVAL_MS);

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
          {effectiveCaption ? (
            <Text style={styles.caption} testID="loading-caption">
              {effectiveCaption}
            </Text>
          ) : null}

          {cohortFooter ? (
            <Text style={styles.cohortFooter} testID="loading-cohort-footer">
              {cohortFooter}
            </Text>
          ) : null}

          {effectiveStages && effectiveStages.length > 0 ? (
            <View style={styles.stageCard} testID="loading-stage-card">
              <StageChecklist stages={effectiveStages} />
            </View>
          ) : null}

          {effectiveTips && effectiveTips.length > 0 ? (
            <LoadingTipsCarousel
              tips={effectiveTips}
              intervalMs={effectiveTipIntervalMs}
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
  // Own hook: StreamingCard is a sibling component, not nested inside
  // LoadingScreenVariants' closure, so it cannot borrow that `t`.
  const { t } = useTranslation();
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
          <Text style={streamingStyles.badgeText}>
            {t('results.topMatch', { defaultValue: 'Top match' })}
          </Text>
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
    // F-S2.hotfix4 #44.1: gap reduced from xl → md so the trailing
    // LoadingTipsCarousel stays visible inside the safe-area on
    // shorter iPhones. With xl gap the cumulative LoadingRings + caption
    // + StageChecklist + tips overflowed center-aligned and the tip
    // factoid clipped mid-sentence (Ahmed's screenshot showed "73% of
    // the GCC shoppers your age prioritize" with the rest cut off).
    gap: spacing.md,
    paddingBottom: spacing.sm,
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
