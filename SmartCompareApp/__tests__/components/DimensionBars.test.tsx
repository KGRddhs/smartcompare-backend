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

// ---------------------------------------------------------------------------
// Walk-fix 2026-06-17 — results-screen organization (on-device fragrance walk).
// Grounded in the FRESH real payload (.qa-discovery/_walk_frag.json): when
// prices pend, the backend emits placeholder dims (price/reviews/value) as a
// 75/75 tie with confidence:'low', a "Limited X data" / "...unavailable"
// delta_text, and caption_key:'limited_data'. The real dims (character /
// longevity) carry distinct scores + no caption_key.
//   #1 drop caption_key:'limited_data' dims entirely (no "Limited X data" line)
//   #2 render the two products ONCE as a compact top legend, not per-row
// ---------------------------------------------------------------------------
describe('DimensionBars — walk-fix (limited-data suppression + single legend)', () => {
  // Mirrors the real walk payload's dimension shapes.
  const WALK_DIMS: any[] = [
    { key: 'price', label: 'Price', score_a: 75, score_b: 75, delta_text: 'Price data unavailable', confidence: 'low', caption_key: 'limited_data', is_core: true, winner: null },
    { key: 'reviews', label: 'Reviews', score_a: 75, score_b: 75, delta_text: 'Limited review data', confidence: 'low', caption_key: 'limited_data', is_core: true, winner: null },
    { key: 'value', label: 'Value', score_a: 75, score_b: 75, delta_text: 'Limited value data', confidence: 'low', caption_key: 'limited_data', is_core: true, winner: null },
    { key: 'character', label: 'Character', score_a: 74.1, score_b: 55.9, delta_text: '+18pt distinctiveness', confidence: 'medium', is_core: false, winner: 0 },
    { key: 'longevity', label: 'Longevity', score_a: 74.1, score_b: 55.9, delta_text: '+18pt longevity', confidence: 'medium', is_core: false, winner: 0 },
  ];

  it('drops caption_key:"limited_data" dims (price/reviews/value), keeps the real dims', () => {
    const { queryByTestId, getByTestId } = render(
      <DimensionBars dimensions={WALK_DIMS} winnerIndex={0} testID="bars" />,
    );
    // Placeholder no-data dims are GONE (no row at all).
    expect(queryByTestId('bars-row-price')).toBeNull();
    expect(queryByTestId('bars-row-reviews')).toBeNull();
    expect(queryByTestId('bars-row-value')).toBeNull();
    // Real dims render.
    expect(getByTestId('bars-row-character')).toBeTruthy();
    expect(getByTestId('bars-row-longevity')).toBeTruthy();
  });

  it('never renders the "Limited X data" / "unavailable" placeholder text', () => {
    const { queryByText } = render(
      <DimensionBars dimensions={WALK_DIMS} winnerIndex={0} testID="bars" />,
    );
    expect(queryByText('Limited value data')).toBeNull();
    expect(queryByText('Limited review data')).toBeNull();
    expect(queryByText('Price data unavailable')).toBeNull();
    expect(queryByText(/limited .* data/i)).toBeNull();
  });

  it('renders the two products ONCE in a compact top legend, not repeated per row', () => {
    const { getAllByText, getByTestId } = render(
      <DimensionBars
        dimensions={WALK_DIMS}
        winnerIndex={0}
        productAName="Black Orchid"
        productBName="Oud Wood"
        testID="bars"
      />,
    );
    // The single top legend exists and names each product EXACTLY ONCE
    // (previously the names repeated on every bar row).
    expect(getByTestId('bars-legend')).toBeTruthy();
    expect(getAllByText('Black Orchid')).toHaveLength(1);
    expect(getAllByText('Oud Wood')).toHaveLength(1);
  });

  it('truncates long product names in the legend to one line (no overflow)', () => {
    const longA = 'Tom Ford Black Orchid Eau de Parfum 100 ml';
    const { getByText } = render(
      <DimensionBars
        dimensions={WALK_DIMS}
        winnerIndex={0}
        productAName={longA}
        productBName="Tom Ford Oud Wood Eau de Parfum 100 ml"
        testID="bars"
      />,
    );
    expect(getByText(longA).props.numberOfLines).toBe(1);
  });

  it('omits the top legend when no product names are supplied (legacy callers)', () => {
    const { queryByTestId } = render(
      <DimensionBars dimensions={WALK_DIMS} winnerIndex={0} testID="bars" />,
    );
    expect(queryByTestId('bars-legend')).toBeNull();
  });

  it('a long dimension label is single-line (no horizontal overflow)', () => {
    const { getByText } = render(
      <DimensionBars dimensions={WALK_DIMS} winnerIndex={0} testID="bars" />,
    );
    expect(getByText('Character').props.numberOfLines).toBe(1);
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
