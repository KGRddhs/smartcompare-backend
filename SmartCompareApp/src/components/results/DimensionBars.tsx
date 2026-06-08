/**
 * DimensionBars — Bundle E Phase 3 Task 3.3.
 *
 * Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 3
 * + § Decision 2 (dimensions[] contract).
 *
 * One row per backend `dimensions[]` entry (3-6 rows). Each row shows:
 *   - left:  product-A bar (emerald if A wins this dim, gray if B wins)
 *   - label: the dimension label (typography.body, Inter Medium)
 *   - right: product-B bar (mirrored)
 *   - score numbers in tabular figures
 *   - delta_text underneath (caption, secondary color)
 *
 * Color contract per § Decision 3: the bar fill is **emerald for the
 * higher score**, **neutral gray for the lower** — never orange or red.
 *
 * Confidence handling per § Decision 3 line 195:
 *   - `low` rows render at row-level opacity 0.6 + "≈" prefix on the
 *     score number. No banner, no scary copy.
 *   - `high` / `medium` rows render at full opacity, no prefix.
 *
 * Zero-score contract violation per § Decision 2: backend never emits a
 * dimension where either product lacks data. A stale client receiving
 * score=0 must NOT paint an empty bar — render an error node so the
 * regression is loud and visible.
 */

import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTranslation } from 'react-i18next';
import * as Haptics from 'expo-haptics';
import { ChevronDown, ChevronUp } from 'lucide-react-native';

import { colors, spacing, typography } from '../../theme';
import type { Dimension } from '../../types';

interface DimensionBarsProps {
  dimensions: Dimension[];
  winnerIndex: 0 | 1;
  testID?: string;
}

const BAR_TRACK_HEIGHT = 6;
const LOW_CONFIDENCE_OPACITY = 0.6;
const LOW_CONFIDENCE_PREFIX = '\u2248'; // ≈

export function DimensionBars({
  dimensions,
  winnerIndex,
  testID = 'bars',
}: DimensionBarsProps) {
  // Bundle C § 2b — last-resort "Limited data" visible row. Backend
  // flags `data_insufficient: true` only when the dim can't be silently
  // omitted (single-dim scenarios). Most missing dims hit § 2h silent
  // omission instead and never reach this state.
  const insufficientDims = dimensions.filter((d) => d.data_insufficient === true);

  // Bundle C — silent omission per spec § 2h. Dims with `null` on either
  // side (and NOT flagged data_insufficient) disappear from the rendered
  // tree entirely. Done at component entry so the downstream contract-
  // violation check + DimensionRow logic see only renderable rows.
  const renderableDims = dimensions.filter(
    (d) => !d.data_insufficient && d.score_a != null && d.score_b != null,
  );

  // § Decision 2 invariant — fail loud on ACTUAL zero scores. A score of
  // 0 means the backend leaked a dimension where one product had no
  // data, which would paint a misleading empty bar. Bundle C separates
  // `null` (silent omission per § 2h, filtered out above) from `0`
  // (contract violation per § 6d, still trips this guard).
  const hasZero = renderableDims.some(
    (d) => (d.score_a as number) <= 0 || (d.score_b as number) <= 0,
  );
  if (hasZero) {
    return (
      <View
        style={styles.violation}
        testID={`${testID}-contract-violation`}
        {...({ 'data-contract-violation': 'true' } as any)}
      >
        {/* Dev-facing contract-violation surface; never shown in
            production because backend never emits zero-score dims. */}
        {/* eslint-disable-next-line i18next/no-literal-string */}
        <Text style={styles.violationText}>Dimension scored 0 — backend contract breach.</Text>
      </View>
    );
  }

  // Bundle C § 6b — hero card shows top 4 dims by default; remaining
  // dims hide behind a "See full breakdown" expand row that toggles
  // visibility inline. ≤4 renderable dims → expand row never appears.
  const HERO_CAP = 4;
  const showExpandRow = renderableDims.length > HERO_CAP;

  return (
    <View style={styles.container} testID={testID}>
      <HeroExpand
        renderableDims={renderableDims}
        winnerIndex={winnerIndex}
        heroCap={HERO_CAP}
        showExpandRow={showExpandRow}
        testID={testID}
      />
      {insufficientDims.map((d) => (
        <InsufficientRow
          key={d.key}
          dimension={d}
          testID={`${testID}-row-${d.key}-insufficient`}
        />
      ))}
    </View>
  );
}

interface HeroExpandProps {
  renderableDims: Dimension[];
  winnerIndex: 0 | 1;
  heroCap: number;
  showExpandRow: boolean;
  testID: string;
}

function HeroExpand({ renderableDims, winnerIndex, heroCap, showExpandRow, testID }: HeroExpandProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const heroDims = renderableDims.slice(0, heroCap);
  const extraDims = renderableDims.slice(heroCap);
  const visibleDims = expanded ? renderableDims : heroDims;

  const onToggle = () => {
    // Haptic only on transition INTO expanded (per CLAUDE.md motion
    // vocabulary — chip:light, never error/heavy intensities).
    if (!expanded) {
      try { Haptics.selectionAsync(); } catch {}
    }
    setExpanded((x) => !x);
  };

  return (
    <>
      {visibleDims.map((d) => (
        <DimensionRow
          key={d.key}
          dimension={d}
          winnerIndex={winnerIndex}
          testID={`${testID}-row-${d.key}`}
        />
      ))}
      {showExpandRow && (
        <TouchableOpacity
          testID={`${testID}-expand-row`}
          onPress={onToggle}
          accessibilityRole="button"
          accessibilityState={{ expanded }}
          style={styles.expandRow}
        >
          <Text style={styles.expandLabel}>
            {t('results.dimensions.see_full_breakdown')}
          </Text>
          {expanded ? (
            <ChevronUp size={16} color={colors.text.secondary} />
          ) : (
            <ChevronDown size={16} color={colors.text.secondary} />
          )}
        </TouchableOpacity>
      )}
    </>
  );
}

interface InsufficientRowProps {
  dimension: Dimension;
  testID: string;
}

function InsufficientRow({ dimension, testID }: InsufficientRowProps) {
  const { t } = useTranslation();
  return (
    <View style={styles.insufficientRow} testID={testID}>
      <Text style={styles.label}>{dimension.label}</Text>
      <Text style={styles.insufficientCaption}>
        {t('results.dimensions.limited_data')}
      </Text>
    </View>
  );
}

interface DimensionRowProps {
  dimension: Dimension;
  winnerIndex: 0 | 1;
  testID: string;
}

function DimensionRow({ dimension, winnerIndex, testID }: DimensionRowProps) {
  const { t } = useTranslation();
  const { key, label, delta_text, confidence } = dimension;
  // Bundle C — `score_a | score_b` typed `number | null` (spec § 2h).
  // Parent filters out null pairs already, but we narrow defensively.
  const score_a = dimension.score_a ?? 0;
  const score_b = dimension.score_b ?? 0;
  const isLow = confidence === 'low';
  const rowOpacity = isLow ? LOW_CONFIDENCE_OPACITY : 1;
  const prefix = isLow ? LOW_CONFIDENCE_PREFIX : undefined;

  // Per-row winner: whichever score is higher inside THIS dimension —
  // not the overall comparison winner. Emerald paints that side's bar
  // fill; the other side gets neutral gray. Ties go to overall winner.
  //
  // Lane A-L3 Task L3.6 — when L1 emits an explicit `winner` index on
  // the dim, prefer it over the score-comparison heuristic. This matches
  // backend's authoritative scoring_v2.dim_winners (e.g. value dim
  // factors in cross-tier framing the FE can't replicate).
  const aWins =
    dimension.winner === 0
      ? true
      : dimension.winner === 1
        ? false
        : score_a > score_b ||
          (score_a === score_b && winnerIndex === 0);
  const fillA = aWins ? colors.accent : colors.text.secondary;
  const fillB = aWins ? colors.text.secondary : colors.accent;

  // Bundle C § 4b — value + price rows promote delta_text to a hero
  // typography slot beneath the label. Other dims keep the existing
  // inline-right caption (incremental migration).
  const isHeroDeltaRow = key === 'value' || key === 'price';
  // § 4c — cross-tier framing suppresses the winner emerald + replaces
  // delta_text with neutral "Different tier — held to higher bar".
  const isCrossTier = dimension.is_cross_tier === true && key === 'value';
  const heroDeltaColor = isCrossTier
    ? colors.text.primary
    : (aWins ? colors.accent : colors.text.primary);
  const heroDeltaText = isCrossTier
    ? t('results.value.different_tier')
    : delta_text;

  // § 4d — per-row caption on the value row ONLY, surfacing tier
  // mismatches without a banner. Silent on in_range/in_range.
  const valueMatchCaptionKey = computeValueMatchCaptionKey(dimension);

  return (
    <View style={[styles.row, { opacity: rowOpacity }]} testID={testID}>
      <View style={styles.labelRow}>
        <Text style={styles.label}>{label}</Text>
        {!isHeroDeltaRow && <Text style={styles.delta}>{delta_text}</Text>}
      </View>
      {isHeroDeltaRow && (
        <Text
          testID={`${testID}-delta-hero`}
          style={[styles.deltaHero, { color: heroDeltaColor }]}
        >
          {heroDeltaText}
        </Text>
      )}
      <View style={styles.barsRow}>
        <BarSide
          score={score_a}
          fillColor={fillA}
          align="left"
          testID={`${testID}-fill-a`}
        />
        <ScoreText
          score={score_a}
          prefix={prefix}
          testID={`${testID}-score-a`}
        />
        <ScoreText
          score={score_b}
          prefix={prefix}
          testID={`${testID}-score-b`}
        />
        <BarSide
          score={score_b}
          fillColor={fillB}
          align="right"
          testID={`${testID}-fill-b`}
        />
      </View>
      {key === 'value' && valueMatchCaptionKey && (
        <Text
          testID={`${testID}-value-match-caption`}
          style={styles.valueMatchCaption}
        >
          {t(valueMatchCaptionKey)}
        </Text>
      )}
    </View>
  );
}

// Bundle C § 4d + 4e — pick the right caption key for the VALUE row based
// on per-product `value_match_*` flags. Returns `null` for the silent
// in_range/in_range case. Caller renders only when key !== null.
function computeValueMatchCaptionKey(d: Dimension): string | null {
  const a = d.value_match_a;
  const b = d.value_match_b;
  if (!a && !b) return null;
  if (a === 'in_range' && b === 'in_range') return null;
  // Both below → "cheaper of the two" (spec § 4e case 2).
  if (a === 'below_range' && b === 'below_range') return 'results.valueMatch.cheaper_of_two';
  // Any product above → caption surfaces above-range, with tradeoff
  // variant if backend supplied a key_tradeoff snippet.
  if (a === 'above_range' || b === 'above_range') {
    return d.key_tradeoff
      ? 'results.valueMatch.above_range_with_tradeoff'
      : 'results.valueMatch.above_range';
  }
  // Single product below_range → "within your range" framing.
  if (a === 'below_range' || b === 'below_range') {
    return 'results.valueMatch.below_range';
  }
  return null;
}

interface BarSideProps {
  score: number;
  fillColor: string;
  align: 'left' | 'right';
  testID: string;
}

function BarSide({ score, fillColor, align, testID }: BarSideProps) {
  // Score range is calibrated 70-95 per § Decision 4. Map to bar width
  // proportionally so visual deltas reflect real score deltas without
  // pinning the high end to 100% (which would feel like everyone aces).
  const widthPct = Math.max(10, Math.min(100, score));
  return (
    <View
      style={[
        styles.barTrack,
        align === 'left' ? styles.barLeft : styles.barRight,
      ]}
    >
      <View
        testID={testID}
        style={[
          styles.barFill,
          {
            width: `${widthPct}%`,
            backgroundColor: fillColor,
            alignSelf: align === 'left' ? 'flex-end' : 'flex-start',
          },
        ]}
      />
    </View>
  );
}

interface ScoreTextProps {
  score: number;
  prefix?: string;
  testID: string;
}

function ScoreText({ score, prefix, testID }: ScoreTextProps) {
  return (
    <Text
      style={styles.score}
      testID={testID}
      {...({ 'data-score-prefix': prefix } as any)}
    >
      {prefix ? `${prefix} ${score}` : String(score)}
    </Text>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: spacing.md,
    paddingVertical: spacing.sm,
  },
  row: {
    gap: spacing.xs,
  },
  // Bundle C § 2b — last-resort visible state for truly-missing data.
  // Neutral muted styling — never emerald, never destructive. The
  // caption "Limited data" is the user-facing equivalent of "no signal
  // to score this dim with yet" without apologizing.
  insufficientRow: {
    gap: spacing.xs,
    paddingVertical: spacing.xs,
    opacity: 0.7,
  },
  insufficientCaption: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  labelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'baseline',
  },
  label: {
    ...typography.bodyEmphasis,
    color: colors.text.primary,
  },
  delta: {
    ...typography.caption,
    color: colors.text.secondary,
    flexShrink: 1,
    marginStart: spacing.sm,
    textAlign: 'right',
  },
  // Bundle C § 4b — hero promotion: value + price rows put the delta
  // text center-stage above the bars, title-weight, emerald when winning.
  deltaHero: {
    ...typography.title,
    textAlign: 'center',
    marginVertical: spacing.xs,
  },
  // Bundle C § 4d — per-row caption under the value bars only.
  valueMatchCaption: {
    ...typography.caption,
    color: colors.text.secondary,
    marginTop: spacing.xs,
    textAlign: 'center',
  },
  // Bundle C § 6b — expand row sits under the hero 4 dims.
  expandRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.xs,
    paddingVertical: spacing.sm,
  },
  expandLabel: {
    ...typography.caption,
    color: colors.text.secondary,
  },
  barsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  barTrack: {
    flex: 1,
    height: BAR_TRACK_HEIGHT,
    backgroundColor: colors.border.light,
    borderRadius: BAR_TRACK_HEIGHT / 2,
    overflow: 'hidden',
    flexDirection: 'row',
  },
  barLeft: {
    justifyContent: 'flex-end',
  },
  barRight: {
    justifyContent: 'flex-start',
  },
  barFill: {
    height: BAR_TRACK_HEIGHT,
    borderRadius: BAR_TRACK_HEIGHT / 2,
  },
  score: {
    ...typography.caption,
    fontVariant: ['tabular-nums'],
    color: colors.text.primary,
    minWidth: 28,
    textAlign: 'center',
  },
  violation: {
    padding: spacing.base,
    borderRadius: 8,
    backgroundColor: colors.bg.secondary,
  },
  violationText: {
    ...typography.caption,
    color: colors.text.secondary,
    textAlign: 'center',
  },
});
