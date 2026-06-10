/**
 * ResultsLoadingView — full-screen dramatized comparison loading.
 *
 * Phase 3 Task 28. Replaces the small inline loading overlay with the
 * design § 3 layout: query echo, variable-easing progress bar, 5-row
 * stage checklist (✓ done / ⟳ active / ○ pending) with cohort + region
 * context copy, ghost product cards that fill stage-by-stage, and a
 * tips carousel that fades in after 8s of waiting.
 *
 * Pure presentational. The parent (HomeScreen for now; potentially
 * ResultsScreen post-Task-30) owns the SSE subscription and passes
 * `reachedStage` + per-product `products[]` snapshots in.
 *
 * Min-display floor (1.2s for cache hits per design § 3) is the
 * parent's responsibility — they delay navigation to the success
 * view, not gate this component's render.
 */

import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ScrollView } from 'react-native';
import { useTranslation } from 'react-i18next';
import { ProgressBar } from './ProgressBar';
import { StageChecklist, Stage } from './StageChecklist';
import {
  StreamingProductCard,
  StreamingProductLike,
  StreamingStage,
} from './StreamingProductCard';
import { LoadingTipsCarousel } from './LoadingTipsCarousel';
import { trackEvent } from '../services/api';
import { colors, spacing, typography } from '../theme';

const STAGE_ORDER: StreamingStage[] = [
  'init',
  'specs',
  'prices',
  'reviews',
  'verdict',
];

const STAGE_LABEL_KEYS: Record<StreamingStage, string> = {
  init: 'results.stage.init',
  title: 'results.stage.init',
  specs: 'results.stage.specs',
  prices: 'results.stage.prices',
  reviews: 'results.stage.reviews',
  verdict: 'results.stage.verdict',
};

const STAGE_DEFAULTS: Record<StreamingStage, string> = {
  init: 'Understanding your query',
  title: 'Understanding your query',
  specs: 'Reading specs',
  prices: 'Cross-checking retailers',
  reviews: 'Analyzing reviews',
  verdict: 'Locking in your winner',
};

interface Props {
  /** The user's query, echoed at the top for instant trust. */
  query: string;
  /** Names for each ghost card (the cards themselves accept partial product). */
  productNames: string[];
  /** SSE reach so far. Drives stage status + ghost-card fill. */
  reachedStage: StreamingStage;
  /** Per-product partial-shape snapshots; index-aligned with productNames. */
  products?: StreamingProductLike[];
  /** Override the 8000ms tips-carousel reveal delay. Used by tests. */
  tipsAfterMs?: number;
  /** 5 tips per design § 3 — parent injects locale-resolved strings. */
  tips?: string[];
  /**
   * Comparison id for pain-workflow events, when known. During streaming this
   * is usually undefined (the row isn't saved yet) — events still record with
   * a null comparison_id and the stage in event_data. B.1 F3.5.
   */
  comparisonId?: string;
  /**
   * Opt out of pain-workflow instrumentation (e.g. tests that don't want the
   * /events network call). Defaults to on — the cards only emit on real user
   * actions (expand tap / screenshot / abandon-before-verdict).
   */
  trackPainEvents?: boolean;
}

const DEFAULT_TIPS_AFTER_MS = 8000;

export function ResultsLoadingView({
  query,
  productNames,
  reachedStage,
  products,
  tipsAfterMs = DEFAULT_TIPS_AFTER_MS,
  tips,
  comparisonId,
  trackPainEvents = true,
}: Props) {
  const { t } = useTranslation();
  const [showTips, setShowTips] = useState(false);

  // Pain-workflow signal sink — threaded to every ghost card. Records the
  // current SSE stage as context; comparison_id is usually null at loading
  // time (the row isn't persisted yet). trackEvent is fire-and-forget and
  // swallows errors, so this never affects the loading UX. B.1 F3.5.
  const onPainSignal = trackPainEvents
    ? (signal: 'spec_expand' | 'result_abandon' | 'screenshot') => {
        trackEvent(signal, { stage: reachedStage }, comparisonId);
      }
    : undefined;

  useEffect(() => {
    const id = setTimeout(() => setShowTips(true), tipsAfterMs);
    return () => clearTimeout(id);
  }, [tipsAfterMs]);

  const stages: Stage[] = STAGE_ORDER.map((s) => ({
    id: s,
    label: t(STAGE_LABEL_KEYS[s], { defaultValue: STAGE_DEFAULTS[s] }),
    status: stageStatus(s, reachedStage),
  }));

  // Progress: number of completed stages / total. ProgressBar's
  // variableEasing handles the fast/slow/fast/snap segmentation.
  const completedCount = STAGE_ORDER.filter(
    (s) => stageStatus(s, reachedStage) === 'done'
  ).length;
  const progress = completedCount / STAGE_ORDER.length;

  const fallbackTips = [
    t('results.tips.retailers', {
      defaultValue: 'Qaren cross-checks 25+ retailers — never just one.',
    }),
    t('results.tips.work_for_you', {
      defaultValue: 'We work for you — never paid by sellers.',
    }),
    t('results.tips.save_offline', {
      defaultValue: 'Save any comparison to revisit later — even offline.',
    }),
  ];

  return (
    <View testID="results-loading" style={styles.container}>
      <ScrollView contentContainerStyle={styles.body} showsVerticalScrollIndicator={false}>
        <Text style={styles.queryEcho} numberOfLines={2}>
          {query}
        </Text>

        <View style={styles.progressWrap}>
          <ProgressBar progress={progress} variableEasing testID="results-progress" />
        </View>

        <View style={styles.checklistWrap}>
          <StageChecklist stages={stages} />
        </View>

        <View style={styles.cardsRow}>
          {productNames.map((name, idx) => (
            <View
              key={`${idx}-${name}`}
              testID={`ghost-card-${idx}`}
              style={styles.cardCol}
            >
              <StreamingProductCard
                stage={reachedStage}
                product={products?.[idx] ?? { name }}
                testID={`ghost-card-${idx}-card`}
                onSignal={onPainSignal}
              />
            </View>
          ))}
        </View>

        {showTips ? (
          <View style={styles.tipsWrap}>
            <LoadingTipsCarousel
              tips={tips && tips.length > 0 ? tips : fallbackTips}
              testID="loading-tips"
            />
          </View>
        ) : null}
      </ScrollView>
    </View>
  );
}

function stageStatus(
  stage: StreamingStage,
  reached: StreamingStage
): 'done' | 'active' | 'pending' {
  const stageIdx = STAGE_ORDER.indexOf(normalizeStage(stage));
  const reachedIdx = STAGE_ORDER.indexOf(normalizeStage(reached));
  if (reachedIdx < 0 || stageIdx < 0) return 'pending';
  if (stageIdx < reachedIdx) return 'done';
  if (stageIdx === reachedIdx) return reached === 'verdict' ? 'done' : 'active';
  return 'pending';
}

/** Treat the streaming-only 'title' stage as 'init' for stage-list display. */
function normalizeStage(s: StreamingStage): StreamingStage {
  return s === 'title' ? 'init' : s;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.bg.primary,
  },
  body: {
    paddingHorizontal: spacing.xl,
    paddingTop: spacing.xl,
    paddingBottom: spacing['2xl'],
    gap: spacing.xl,
  },
  queryEcho: {
    ...typography.title,
    color: colors.text.primary,
  },
  progressWrap: {
    paddingVertical: spacing.sm,
  },
  checklistWrap: {
    backgroundColor: colors.bg.secondary,
    borderRadius: spacing.base,
    padding: spacing.md,
  },
  cardsRow: {
    flexDirection: 'row',
    gap: spacing.md,
  },
  cardCol: {
    flex: 1,
  },
  tipsWrap: {
    marginTop: spacing.md,
    paddingHorizontal: spacing.md,
  },
});
