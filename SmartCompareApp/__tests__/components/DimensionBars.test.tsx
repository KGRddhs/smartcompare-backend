/**
 * DimensionBars — Bundle E Phase 3 Task 3.2 RED scaffold.
 *
 * Plan: docs/plans/2026-05-13-results-quality-overhaul.md
 * Design: docs/plans/2026-05-13-results-quality-overhaul-design.md § Decision 3
 * + § Decision 2 (dimensions[] contract).
 *
 * Renders one row per backend `dimensions[]` entry (3-6 rows). Each row
 * shows two horizontal bars (one per product) plus the label and score
 * numbers. Emerald for the higher score in a row, neutral gray for the
 * lower — **never orange**. Low-confidence rows render at opacity 0.6
 * with a "≈" prefix on the score number.
 *
 * **Invariant: a dimension is never emitted if either product lacks the
 * data** (design § Decision 2: "No empty bars. Ever."). Backend enforces
 * this in `scoring_v2`; frontend should reject score=0 defensively as a
 * contract breach so a stale client never paints a misleading empty bar.
 *
 * BLOCKED ON: backend Task 1.6 — scoring_v2 SSE shape with
 * `dimensions[]` array of `{key, label, score_a, score_b, delta_text,
 * confidence, is_core}`. Component path: `src/components/results/
 * DimensionBars.tsx` (to be created).
 */

import React from 'react';
import { render } from '@testing-library/react-native';

import { DimensionBars } from '../../src/components/results/DimensionBars';

import { colors } from '../../src/theme';

type Dimension = {
  key: string;
  label: string;
  score_a: number;
  score_b: number;
  delta_text: string;
  confidence: 'high' | 'medium' | 'low';
  is_core: boolean;
};

const DIMENSIONS_HIGH: Dimension[] = [
  { key: 'price', label: 'Price', score_a: 88, score_b: 72, delta_text: 'BHD 30 less', confidence: 'high', is_core: true },
  { key: 'reviews', label: 'Reviews', score_a: 82, score_b: 78, delta_text: '0.2★ higher', confidence: 'high', is_core: true },
  { key: 'value', label: 'Value', score_a: 90, score_b: 76, delta_text: 'Better ratio of features to cost', confidence: 'high', is_core: true },
  { key: 'build_quality', label: 'Build', score_a: 80, score_b: 88, delta_text: 'PBT keycaps, metal frame', confidence: 'medium', is_core: false },
];

describe('DimensionBars — Bundle E Phase 3 § Decision 3', () => {
  it('renders one row per dimension supplied by the backend', () => {
    const { getAllByTestId } = render(
      <DimensionBars dimensions={DIMENSIONS_HIGH} winnerIndex={0} testID="bars" />,
    );
    const rows = getAllByTestId(/^bars-row-[^-]+$/);
    expect(rows).toHaveLength(DIMENSIONS_HIGH.length);
    // Each row's testID encodes the dimension key for reliable selection
    // downstream — assert the keys match the data exactly.
    const rowIds = rows.map((r) => r.props.testID);
    for (const d of DIMENSIONS_HIGH) {
      expect(rowIds).toContain(`bars-row-${d.key}`);
    }
  });

  it('throws (or returns a contract-error node) when a dimension has score 0', () => {
    // Backend `scoring_v2` guarantees no zero-score dimensions
    // (design § Decision 2 — "A dimension is never emitted if either
    // product lacks the data."). A stale client receiving a malformed
    // payload with score=0 must NOT paint an empty bar — it must fail
    // loud so the regression is visible. Implementation may either
    // throw at render time or render an error node carrying
    // `data-contract-violation="true"` — we accept either.
    const bad: Dimension[] = [
      { ...DIMENSIONS_HIGH[0], score_a: 0 },
    ];
    let threw = false;
    let violationNode: any = null;
    try {
      const { queryByTestId } = render(
        <DimensionBars dimensions={bad} winnerIndex={0} testID="bars" />,
      );
      violationNode = queryByTestId('bars-contract-violation');
    } catch {
      threw = true;
    }
    expect(threw || violationNode !== null).toBe(true);
  });

  it('applies 0.6 opacity and a "≈" prefix on low-confidence rows', () => {
    const lowConf: Dimension[] = [
      { ...DIMENSIONS_HIGH[0], confidence: 'low' },
      DIMENSIONS_HIGH[1], // high confidence — control
    ];
    const { getByTestId } = render(
      <DimensionBars dimensions={lowConf} winnerIndex={0} testID="bars" />,
    );
    const lowRow = getByTestId('bars-row-price');
    // Opacity 0.6 may live on the row View's style or on the
    // foreground bar's style — flatten and search.
    const flat = Array.isArray(lowRow.props.style)
      ? Object.assign({}, ...lowRow.props.style)
      : (lowRow.props.style ?? {});
    expect(flat.opacity).toBeCloseTo(0.6, 2);
    // The "≈" prefix sits on the score-number text inside this row.
    const scoreText = getByTestId('bars-row-price-score-a');
    expect(scoreText.props['data-score-prefix']).toBe('≈');
    // Control row has no prefix.
    const controlScoreText = getByTestId('bars-row-reviews-score-a');
    expect(controlScoreText.props['data-score-prefix']).toBeUndefined();
    // Banned colors sweep on bar fill — same contract as HeroRings:
    // emerald for the higher score, neutral gray for the lower, never
    // destructive red or warning orange.
    const fill = getByTestId('bars-row-price-fill-a');
    const fillStyle = Array.isArray(fill.props.style)
      ? Object.assign({}, ...fill.props.style)
      : (fill.props.style ?? {});
    const bg = String(fillStyle.backgroundColor ?? '').toLowerCase();
    expect(bg).not.toContain(colors.warning.toLowerCase());
    expect(bg).not.toContain(colors.destructive.toLowerCase());
    expect(bg).not.toContain('#f59');
    expect(bg).not.toContain('#ef44');
  });
});

/**
 * RED→GREEN trajectory:
 *
 *  1. Pre-Phase-3: `src/components/results/DimensionBars.tsx` not
 *     present. All 3 tests fail at import.
 *  2. Phase 3 Task 3.2 lands the component reading the new
 *     `dimensions[]` array. All 3 assertions pass.
 *  3. The zero-score contract guard catches a regression that would
 *     surface "empty bar with 0 score" in production — the original
 *     anti-pattern called out in design § Decision 2.
 */
