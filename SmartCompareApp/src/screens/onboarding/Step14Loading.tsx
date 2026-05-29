/**
 * Step14Loading — Bundle E S2.W3 REWRITE.
 *
 * Source of truth: docs/claude-design-handoff/ui_kits/mobile/OnboardingExtras.jsx
 * s13/s14 lineage + design doc § S2.x ConcentricVariant.
 *
 * Per memory feedback_compose_vs_rewrite_phrasing.md this is a REWRITE
 * (not compose) — Step14's prior anatomy (LoadingRings + stage-copy
 * ticker + ProgressBar + CounterTicker) is replaced with the
 * ConcentricVariant composition fed via the shared LoadingScreenVariants
 * surface so the comparison-mode loader (F-S2.X2 task #32) reuses the
 * exact same recipe.
 *
 * New anatomy (delegated to LoadingScreenVariants ConcentricVariant):
 *   1. LoadingRings hero (Q + 3 concentric emerald rings expanding).
 *   2. Cohort footer line — "{cohortPeerCount} cohort peers" so the
 *      counter beat is preserved.
 *   3. StageChecklist (region/priorities/peers/calibrate) — auto-
 *      progressing every STAGE_TICK_MS to match the Step13 cadence.
 *      Stage IDs stay aligned with Step13 for perceived continuity.
 *   4. LoadingTipsCarousel — 4 factoids crossfading every 3.2s per
 *      JSX spec (default tipIntervalMs from LoadingScreenVariants).
 *
 * Theatrical floor: 3,200ms minimum via LoadingScreenVariants
 * mode="onboarding". onComplete maps to LoadingScreenVariants onDone.
 *
 * Governorate substitution: same gcc_fallback discipline as Step13 —
 * null/undefined → "the GCC" per qaren-cohort privacy invariant.
 *
 * NO exit ramps during loading (Build Principle #5). NO Cancel /
 * "keep waiting?" modal — the orchestrator's back arrow is the only
 * natural escape.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { LoadingScreenVariants } from '../LoadingScreenVariants';
import { Stage } from '../../components/StageChecklist';
import { OnboardingGovernorate } from './types';

const DEFAULT_MIN_DURATION_MS = 3200;
const STAGE_TICK_MS = 800;
const TIP_INTERVAL_MS = 3200;
// Y.B Bundle D rhythm: counter chip ticks 0 → target over 2.4s per
// design doc § 3.2 LoadingRings spec + § 3.3 motion.counterTick.
// COUNTER_FALLBACK_TARGET kicks in when cohortPeerCount is null or 0
// (e.g. cold-start with no cohort match yet) so the brand beat still
// lands. 2074 = nominal "trained on N comparisons" figure.
const COUNTER_FALLBACK_TARGET = 2074;
const COUNTER_DURATION_MS = 2400;

const STAGE_IDS = ['region', 'priorities', 'peers', 'calibrate'] as const;

interface Props {
  /** Fires exactly once after `minDurationMs` elapses. */
  onComplete: () => void;
  /** Cohort peer count to surface in the footer copy. */
  cohortPeerCount: number;
  /** Override the floor (default 3200ms per design spec). */
  minDurationMs?: number;
  /** From OnboardingFlow `data.governorate` — falls back to gcc_fallback. */
  governorate?: OnboardingGovernorate;
  /** Per-stage tick override (test hook). */
  stageTickMs?: number;
}

export function Step14Loading({
  onComplete,
  cohortPeerCount,
  minDurationMs = DEFAULT_MIN_DURATION_MS,
  governorate,
  stageTickMs = STAGE_TICK_MS,
}: Props) {
  const { t } = useTranslation();

  // Governorate display — same resolution as Step13 so the perceived
  // continuity between the build-out card and the theatrical load reads
  // as a single moment.
  const governorateDisplay = governorate
    ? t(`onboarding.s4.gov_${governorate.toLowerCase()}`, {
        defaultValue: governorate,
      })
    : t('onboarding.s13.gcc_fallback', { defaultValue: 'the GCC' });

  // Stages auto-progress on a tick clock the same as Step13 (region →
  // priorities → peers → calibrate). The 4 stages should land "done"
  // before the 3.2s floor expires so the moment feels complete.
  const [tick, setTick] = useState(0);
  const complete = tick >= STAGE_IDS.length;

  useEffect(() => {
    if (complete) return;
    const id = setTimeout(() => setTick((prev) => prev + 1), stageTickMs);
    return () => clearTimeout(id);
  }, [tick, complete, stageTickMs]);

  const stages: Stage[] = useMemo(
    () =>
      STAGE_IDS.map((id, index) => {
        let status: Stage['status'] = 'pending';
        if (tick > index) status = 'done';
        else if (tick === index) status = 'active';
        return {
          id,
          status,
          label: t(`onboarding.s13.stage_${id}`, {
            governorate: governorateDisplay,
            defaultValue: defaultStageCopy(id, governorateDisplay),
          }),
        };
      }),
    [tick, t, governorateDisplay],
  );

  // 4 tips lifted from the JSX factoid + the existing s14.stage_* +
  // peer_label copy. Stays 4 to align with the dispatcher spec.
  const tips = useMemo<string[]>(
    () => [
      t('onboarding.s14.tip_1', {
        governorate: governorateDisplay,
        defaultValue: `73% of ${governorateDisplay} shoppers your age prioritize Quality first.`,
      }),
      t('onboarding.s14.tip_2', {
        defaultValue: 'Tuned by 2,074 real GCC purchases.',
      }),
      t('onboarding.s14.tip_3', {
        defaultValue: 'Calibrating across your priorities.',
      }),
      t('onboarding.s14.tip_4', {
        defaultValue: 'Almost there — finalizing your advisor.',
      }),
    ],
    [t, governorateDisplay],
  );

  // Y.B Bundle D rhythm per design doc § 3.2 LoadingRings spec: counter
  // chip "N cohort peers refining your match" with 0 → cohortPeerCount
  // tick over 2.4s. The caption sits below the chip in restrained
  // 13/secondary weight. Both anchor the rhythm Ahmed explicitly
  // bookmarked while the StageChecklist + LoadingTipsCarousel additions
  // ride above as the staged readout.
  const cohortCaption = t('loading.cohort.caption', {
    defaultValue: 'cohort peers refining your match',
  });
  // Counter target falls back to a nominal 2,074 when cohortPeerCount
  // is missing or zero so the brand beat still lands during cold-start.
  const counterTarget =
    cohortPeerCount > 0 ? cohortPeerCount : COUNTER_FALLBACK_TARGET;

  return (
    <LoadingScreenVariants
      mode="onboarding"
      variant="concentric"
      stages={stages}
      tips={tips}
      tipIntervalMs={TIP_INTERVAL_MS}
      // cohortFooter intentionally omitted in Step14 onboarding mode —
      // the counter chip + caption ("cohort peers refining your match")
      // already convey the cohort beat per design doc § 3.2 spec, so
      // duplicating "N cohort peers helped train this" right below
      // would be redundant.
      counterTarget={counterTarget}
      counterDurationMs={COUNTER_DURATION_MS}
      caption={cohortCaption}
      minDisplayMs={minDurationMs}
      onDone={onComplete}
      ready
      testID="s14-loading-root"
    />
  );
}

function defaultStageCopy(
  id: (typeof STAGE_IDS)[number],
  governorate: string,
): string {
  switch (id) {
    case 'region':
      return 'Locking your region';
    case 'priorities':
      return 'Mapping your priorities';
    case 'peers':
      return `Matching to peers in ${governorate}`;
    case 'calibrate':
      return 'Calibrating your advisor';
  }
}
