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

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

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
  // § Decision 2 invariant — fail loud on zero scores. A score of 0
  // means the backend leaked a dimension where one product had no data,
  // which would paint a misleading empty bar. Render a contract-violation
  // node instead so the regression is visible in dev + jest.
  //
  // Bundle C — `score_a | score_b` widened to `number | null` (spec § 2h);
  // silent-omission filter lands in B.5.2. Until then, null is treated as
  // zero so the existing contract-violation node fires for stale clients.
  const hasZero = dimensions.some(
    (d) => (d.score_a ?? 0) <= 0 || (d.score_b ?? 0) <= 0,
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

  return (
    <View style={styles.container} testID={testID}>
      {dimensions.map((d) => (
        <DimensionRow
          key={d.key}
          dimension={d}
          winnerIndex={winnerIndex}
          testID={`${testID}-row-${d.key}`}
        />
      ))}
    </View>
  );
}

interface DimensionRowProps {
  dimension: Dimension;
  winnerIndex: 0 | 1;
  testID: string;
}

function DimensionRow({ dimension, winnerIndex, testID }: DimensionRowProps) {
  const { label, delta_text, confidence } = dimension;
  // Bundle C — `score_a | score_b` typed `number | null` (spec § 2h).
  // Pre-B.5.2 narrowing: coerce null to 0; the parent contract-violation
  // node already short-circuits before reaching here when scores are 0.
  const score_a = dimension.score_a ?? 0;
  const score_b = dimension.score_b ?? 0;
  const isLow = confidence === 'low';
  const rowOpacity = isLow ? LOW_CONFIDENCE_OPACITY : 1;
  const prefix = isLow ? LOW_CONFIDENCE_PREFIX : undefined;

  // Per-row winner: whichever score is higher inside THIS dimension —
  // not the overall comparison winner. Emerald paints that side's bar
  // fill; the other side gets neutral gray. Ties go to overall winner.
  const aWins = score_a > score_b || (score_a === score_b && winnerIndex === 0);
  const fillA = aWins ? colors.accent : colors.text.secondary;
  const fillB = aWins ? colors.text.secondary : colors.accent;

  return (
    <View style={[styles.row, { opacity: rowOpacity }]} testID={testID}>
      <View style={styles.labelRow}>
        <Text style={styles.label}>{label}</Text>
        <Text style={styles.delta}>{delta_text}</Text>
      </View>
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
    </View>
  );
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
