/**
 * Bundle C — DimensionBars hero + expand (Plan B.5.9 + B.5.10, spec § 6b).
 *
 * Hero shows top 4 dims visible by default. "See full breakdown" expand
 * row reveals the rest inline. ≤4 dims → no expand row. Tapping the
 * expand row toggles visibility + dispatches a haptic light tap.
 */
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';

import { DimensionBars } from '../../src/components/results/DimensionBars';
import type { Dimension } from '../../src/types';

const makeDim = (key: string, label: string, score_a: number, score_b: number): Dimension => ({
  key,
  label,
  score_a,
  score_b,
  delta_text: `${Math.abs(score_a - score_b)}pt`,
});

const SIX_DIMS: Dimension[] = [
  makeDim('price', 'Price', 85, 75),
  makeDim('reviews', 'Reviews', 88, 80),
  makeDim('value', 'Value', 90, 70),
  makeDim('performance', 'Performance', 82, 78),
  makeDim('build', 'Build', 80, 76),
  makeDim('longevity', 'Longevity', 75, 72),
];

test('hero card shows top 4 dims by default (collapsed)', () => {
  const { queryByTestId, getByText } = render(
    <DimensionBars dimensions={SIX_DIMS} winnerIndex={0} testID="bars" />,
  );
  expect(queryByTestId('bars-row-price')).toBeTruthy();
  expect(queryByTestId('bars-row-reviews')).toBeTruthy();
  expect(queryByTestId('bars-row-value')).toBeTruthy();
  expect(queryByTestId('bars-row-performance')).toBeTruthy();
  // bottom 2 hidden behind expand row
  expect(queryByTestId('bars-row-build')).toBeNull();
  expect(queryByTestId('bars-row-longevity')).toBeNull();
  // expand row visible — i18n key returned by mock
  expect(getByText('results.dimensions.see_full_breakdown')).toBeTruthy();
});

test('tapping expand row reveals remaining dims', () => {
  const { getByTestId } = render(
    <DimensionBars dimensions={SIX_DIMS} winnerIndex={0} testID="bars" />,
  );
  fireEvent.press(getByTestId('bars-expand-row'));
  expect(getByTestId('bars-row-build')).toBeTruthy();
  expect(getByTestId('bars-row-longevity')).toBeTruthy();
});

test('expand row absent when ≤4 dims', () => {
  const dims = SIX_DIMS.slice(0, 3);
  const { queryByTestId, queryByText } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  expect(queryByTestId('bars-expand-row')).toBeNull();
  expect(queryByText('results.dimensions.see_full_breakdown')).toBeNull();
});

test('expand row absent when EXACTLY 4 dims', () => {
  const dims = SIX_DIMS.slice(0, 4);
  const { queryByTestId } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  expect(queryByTestId('bars-expand-row')).toBeNull();
});

test('expand row appears when >4 dims AND insufficient rows do not count toward the 4-cap', () => {
  const dims: Dimension[] = [
    ...SIX_DIMS,
    { key: 'durability', label: 'Durability', score_a: null, score_b: null, delta_text: '', data_insufficient: true },
  ];
  const { queryByTestId } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  // 6 renderable + 1 insufficient. Hero shows top 4 of 6; expand reveals rest.
  expect(queryByTestId('bars-expand-row')).toBeTruthy();
  // Insufficient row renders unconditionally (no expand-gate).
  expect(queryByTestId('bars-row-durability-insufficient')).toBeTruthy();
});
