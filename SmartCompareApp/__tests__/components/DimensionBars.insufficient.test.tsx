/**
 * Bundle C — DimensionBars insufficient-data row (Plan B.5.3 + B.5.4, spec § 2b).
 *
 * Last-resort visible state: when BOTH products lack data on a dim AND
 * the dim cannot be silently omitted (e.g. single-dim scenarios), backend
 * flags `data_insufficient: true`. Renders as label + neutral muted
 * caption "Limited data" — no bar fill, no emerald accent, no scores.
 *
 * Most missing dims should never reach this state (§ 2h silent omission
 * handles them). This row is the rare visible fallback.
 */
import React from 'react';
import { render } from '@testing-library/react-native';

import { DimensionBars } from '../../src/components/results/DimensionBars';
import type { Dimension } from '../../src/types';

test('renders insufficient-data row when data_insufficient=true (spec § 2b)', () => {
  const dims: Dimension[] = [
    {
      key: 'durability',
      label: 'Durability',
      score_a: null,
      score_b: null,
      delta_text: '',
      data_insufficient: true,
    },
  ];
  const { getByTestId, getByText } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  expect(getByTestId('bars-row-durability-insufficient')).toBeTruthy();
  expect(getByText('results.dimensions.limited_data')).toBeTruthy();
});

test('insufficient row has NO bar fill and NO score', () => {
  const dims: Dimension[] = [
    {
      key: 'durability',
      label: 'Durability',
      score_a: null,
      score_b: null,
      delta_text: '',
      data_insufficient: true,
    },
  ];
  const { queryByTestId, getByText } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  // Label still visible
  expect(getByText('Durability')).toBeTruthy();
  // No fill, no score testIDs (those come from regular DimensionRow path)
  expect(queryByTestId('bars-row-durability-fill-a')).toBeNull();
  expect(queryByTestId('bars-row-durability-fill-b')).toBeNull();
  expect(queryByTestId('bars-row-durability-score-a')).toBeNull();
  expect(queryByTestId('bars-row-durability-score-b')).toBeNull();
});

test('dim with both nulls but data_insufficient !== true stays silently omitted (regression check)', () => {
  const dims: Dimension[] = [
    { key: 'price', label: 'Price', score_a: 80, score_b: 72, delta_text: '10% less' },
    { key: 'durability', label: 'Durability', score_a: null, score_b: null, delta_text: '' },
    // ^ no `data_insufficient: true` → silent omission per § 2h (NOT the insufficient row).
  ];
  const { queryByTestId, queryByText } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  expect(queryByTestId('bars-row-price')).toBeTruthy();
  expect(queryByTestId('bars-row-durability')).toBeNull();
  expect(queryByTestId('bars-row-durability-insufficient')).toBeNull();
  expect(queryByText('results.dimensions.limited_data')).toBeNull();
});

test('insufficient row uses muted gray, never emerald or red', () => {
  const dims: Dimension[] = [
    { key: 'durability', label: 'Durability', score_a: null, score_b: null, delta_text: '', data_insufficient: true },
  ];
  const tree = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  ).toJSON();
  const text = JSON.stringify(tree);
  // No emerald accent (no #10B981 or #ECFDF5) in the rendered insufficient row.
  expect(text).not.toContain('#10B981');
  // No destructive red.
  expect(text).not.toContain('#EF4444');
});

test('NO scary copy in insufficient row', () => {
  const dims: Dimension[] = [
    { key: 'durability', label: 'Durability', score_a: null, score_b: null, delta_text: '', data_insufficient: true },
  ];
  const tree = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  ).toJSON();
  const text = JSON.stringify(tree);
  expect(text).not.toMatch(/\b(couldn't|try again|Failed to|missing|unavailable|N\/A)\b/i);
});
