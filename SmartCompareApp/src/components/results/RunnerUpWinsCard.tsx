/**
 * RunnerUpWinsCard — Task #24 (approved 2026-06-18).
 *
 * A richer, structured "Where the runner-up wins" block — replaces the
 * one-line caption that used to live inside the "Why this fits you" verdict
 * block. Pairs the design's "Why this fits you" ↔ "Where the runner-up wins"
 * framing (eyebrow `results.runnerUpWins`, already EN+AR).
 *
 * Content (top → bottom):
 *   - eyebrow "Where the runner-up wins" (reuses the verdict-block eyebrow look)
 *   - runner-up product name
 *   - the verdict prompt's `overview.winner.key_tradeoff` prose as the caption
 *   - one row per dimension the RUNNER-UP leads (derived from scoring_v2
 *     dimensions: score[runnerUp] > score[winner], excluding the no-data
 *     `caption_key:'limited_data'` placeholders). Each row shows the QUALITATIVE
 *     delta_text when it isn't raw point-math, otherwise just the clean dim
 *     LABEL — NO "+Npt" (pt is an internal 0-100 unit shown nowhere else; the
 *     dimension bars already carry magnitude visually).
 *
 * Gray, NOT emerald — emerald is the winner-signal color; the runner-up block
 * stays neutral. Real scored dims only (no fabrication). Symmetric (correct
 * whichever side wins). HIDES ENTIRELY when there is neither a winning dim nor
 * a key_tradeoff (no empty card).
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useTranslation } from 'react-i18next';

import { colors, spacing } from '../../theme';
import type { Product, Dimension } from '../../types';
import { safeDelta, SCORE_INTERNALS_RE } from './_deltaText';

export interface RunnerUpWinsCardProps {
  products: Product[];
  winnerIndex: 0 | 1;
  /** scoring_v2.dimensions (may be undefined on legacy/cached payloads). */
  dimensions?: Dimension[];
  /** overview.winner.key_tradeoff — the verdict prompt's runner-up prose. */
  keyTradeoff?: string | null;
  testID?: string;
}

/**
 * Dimensions the runner-up leads — score[runnerUp] strictly greater than
 * score[winner], excluding no-data placeholders and any dim missing a real
 * numeric pair. Exported for direct unit testing of the derivation.
 */
export function runnerUpWinningDims(
  dimensions: Dimension[] | undefined,
  winnerIndex: 0 | 1,
): Dimension[] {
  if (!Array.isArray(dimensions)) return [];
  const runnerUp = winnerIndex === 0 ? 1 : 0;
  return dimensions.filter((d) => {
    if (!d || d.caption_key === 'limited_data') return false;
    const sw = winnerIndex === 0 ? d.score_a : d.score_b;
    const sr = runnerUp === 0 ? d.score_a : d.score_b;
    if (typeof sw !== 'number' || typeof sr !== 'number') return false;
    return sr > sw;
  });
}

/** The label/phrase for a winning dim row: qualitative delta_text when it is
 *  NOT raw point-math, otherwise the clean dim label. Never the "+Npt" form.
 *  Delegates to the shared `safeDelta` guard (single source of truth). */
function dimRowText(d: Dimension): string {
  return safeDelta(d.delta_text, d.label);
}

export function RunnerUpWinsCard({
  products,
  winnerIndex,
  dimensions,
  keyTradeoff,
  testID = 'runner-up-wins',
}: RunnerUpWinsCardProps) {
  const { t } = useTranslation();

  const runnerUpIndex = winnerIndex === 0 ? 1 : 0;
  const runnerUp = products[runnerUpIndex];
  const winningDims = runnerUpWinningDims(dimensions, winnerIndex);
  // A6 defense-in-depth: drop the key_tradeoff prose when it leaks raw score
  // internals ("N-point", "/100", "overall score", "score of N") — render
  // nothing rather than the leak. Backend (WS-A) is canonical; this fails a
  // future regression loud-but-clean (the card self-hides if nothing remains).
  const prose =
    typeof keyTradeoff === 'string' &&
    keyTradeoff.trim().length > 0 &&
    !SCORE_INTERNALS_RE.test(keyTradeoff)
      ? keyTradeoff.trim()
      : null;

  // Hide the whole block when there is nothing real to say — neither a
  // winning dimension nor the key_tradeoff prose (no empty card).
  if (winningDims.length === 0 && !prose) return null;

  return (
    <View style={styles.section} testID={testID}>
      <Text style={styles.eyebrow}>{t('results.runnerUpWins')}</Text>
      {runnerUp?.name ? (
        <Text style={styles.name} numberOfLines={1} testID={`${testID}-name`}>
          {runnerUp.name}
        </Text>
      ) : null}
      {prose ? (
        <Text style={styles.prose} testID={`${testID}-prose`}>
          {prose}
        </Text>
      ) : null}
      {winningDims.length > 0 ? (
        <View style={styles.dimList} testID={`${testID}-dims`}>
          {winningDims.map((d) => (
            <View key={d.key} style={styles.dimRow} testID={`${testID}-dim-${d.key}`}>
              <Text style={styles.dimBullet}>{'+'}</Text>
              <Text style={styles.dimText} numberOfLines={2}>
                {dimRowText(d)}
              </Text>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  // Lean treatment, matching the verdict block (sectionLean) — spacing only,
  // no bordered card. Neutral (gray), never emerald (winner-signal).
  section: {
    marginBottom: spacing.xl,
  },
  eyebrow: {
    fontSize: 11,
    fontWeight: '600',
    color: colors.text.secondary,
    letterSpacing: 1.1,
    textTransform: 'uppercase',
    marginBottom: spacing.sm,
  },
  name: {
    fontSize: 13,
    fontWeight: '600',
    color: colors.text.primary,
    marginBottom: spacing.xs,
  },
  prose: {
    fontSize: 13,
    color: colors.text.secondary,
    lineHeight: 13 * 1.5,
  },
  dimList: {
    marginTop: spacing.sm,
    gap: spacing.xs,
  },
  dimRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.xs,
  },
  // Neutral "+" marker (NOT emerald) — the runner-up's edge, stated plainly.
  dimBullet: {
    fontSize: 13,
    color: colors.text.secondary,
    marginTop: 1,
  },
  dimText: {
    flex: 1,
    fontSize: 13,
    color: colors.text.primary,
    lineHeight: 13 * 1.4,
  },
});

export default RunnerUpWinsCard;
