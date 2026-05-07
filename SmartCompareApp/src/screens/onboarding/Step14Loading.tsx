/**
 * Step14Loading — Phase 2 Task 21. CENTERPIECE.
 *
 * Theatrical loading screen — perceived effort = perceived value. Even if
 * the backend is faster, we hold for `minDurationMs` (3.2s default per
 * design § 2 row 14) so the brand moment lands.
 *
 * Composition:
 *  - LoadingRings illustration #4 (big Q + 3 emerald glow rings expanding)
 *  - Cycling stage-copy text ("388 GCC shoppers helped train this" → ...)
 *  - ProgressBar with variableEasing — 4-segment fast/slow/fast/snap
 *  - CounterTicker "0 → cohortPeerCount" cohort peers
 *  - onComplete fires ONCE after the floor elapses
 *
 * Per § 4g audit: confident verbs only — *crafting, calibrating, tuning*.
 * No "generating" / "processing" / "waiting".
 *
 * Per build principle 5: NO exit ramps during loading. No Cancel button,
 * no "keep waiting?" modal — the back arrow on the orchestrator is the
 * only natural escape.
 */

import React, { useEffect, useRef, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';
import { LoadingRings } from '../../components/illustrations/LoadingRings';
import { ProgressBar } from '../../components/ProgressBar';
import { CounterTicker } from '../../components/CounterTicker';
import { colors, spacing, typography } from '../../theme';

const DEFAULT_MIN_DURATION_MS = 3200;
const STAGE_INTERVAL_MS = 800;
const STAGE_KEYS = [
  'onboarding.s14.stage_1',
  'onboarding.s14.stage_2',
  'onboarding.s14.stage_3',
  'onboarding.s14.stage_4',
] as const;

interface Props {
  /** Fires exactly once after `minDurationMs` elapses. */
  onComplete: () => void;
  /** Cohort peer count to tick up to (e.g. "47 peers"). */
  cohortPeerCount: number;
  /** Override the floor (default 3200ms per design spec). */
  minDurationMs?: number;
}

export function Step14Loading({
  onComplete,
  cohortPeerCount,
  minDurationMs = DEFAULT_MIN_DURATION_MS,
}: Props) {
  const { t } = useTranslation();
  const [stageIdx, setStageIdx] = useState(0);
  const [progress, setProgress] = useState(0);
  const completedRef = useRef(false);

  // Stage cycler — rotate every STAGE_INTERVAL_MS, stop at the last stage.
  useEffect(() => {
    const id = setInterval(() => {
      setStageIdx((prev) => (prev < STAGE_KEYS.length - 1 ? prev + 1 : prev));
    }, STAGE_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  // Progress driver — reaches 100% at the floor. We let ProgressBar's
  // variableEasing animate the visual; this just sets the target.
  useEffect(() => {
    setProgress(0);
    const tick = setTimeout(() => setProgress(1), 50);
    return () => clearTimeout(tick);
  }, []);

  // The 3.2s floor — fires onComplete exactly once.
  useEffect(() => {
    const id = setTimeout(() => {
      if (!completedRef.current) {
        completedRef.current = true;
        onComplete();
      }
    }, minDurationMs);
    return () => clearTimeout(id);
  }, [minDurationMs, onComplete]);

  const stageCopy = t(STAGE_KEYS[stageIdx]);

  return (
    <View style={styles.container}>
      <View style={styles.heroBlock}>
        <LoadingRings size={240} testID="s14-rings" />

        <Text style={styles.stageCopy} testID="s14-stage-copy">
          {stageCopy}
        </Text>

        <View style={styles.progressWrap}>
          <ProgressBar progress={progress} variableEasing testID="s14-progress" />
        </View>

        <View style={styles.peerWrap}>
          <CounterTicker
            target={cohortPeerCount}
            duration={1800}
            suffix={` ${t('onboarding.s14.peer_label', { defaultValue: 'cohort peers' })}`}
            style={styles.peerCounter}
            testID="s14-peer-counter"
          />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.lg,
  },
  heroBlock: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stageCopy: {
    ...typography.title,
    color: colors.text.primary,
    textAlign: 'center',
    marginTop: spacing.xl,
    paddingHorizontal: spacing.lg,
    minHeight: 56, // reserve space so the text swap doesn't shift layout
  },
  progressWrap: {
    width: '100%',
    marginTop: spacing.xl,
    paddingHorizontal: spacing.lg,
  },
  peerWrap: {
    marginTop: spacing.xl,
  },
  peerCounter: {
    ...typography.body,
    color: colors.text.secondary,
    textAlign: 'center',
  },
});
