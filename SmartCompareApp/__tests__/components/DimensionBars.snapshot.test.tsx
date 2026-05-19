/**
 * Bundle C — DimensionBars snapshot baselines (Plan B.5.11).
 *
 * Pins the visual surface across the three load-bearing states:
 *  - 6 dims collapsed (hero card only)
 *  - 6 dims expanded (all rows visible)
 *  - 2 dims (no expand row)
 */
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';

import { DimensionBars } from '../../src/components/results/DimensionBars';
import type { Dimension } from '../../src/types';

const makeDim = (key: string, label: string, score_a: number, score_b: number, delta_text: string): Dimension => ({
  key, label, score_a, score_b, delta_text,
});

const SIX: Dimension[] = [
  makeDim('price', 'Price', 85, 75, '13% less'),
  makeDim('reviews', 'Reviews', 88, 80, '0.5★ higher'),
  makeDim('value', 'Value', 90, 70, 'Stronger value'),
  makeDim('performance', 'Performance', 82, 78, '4pt'),
  makeDim('build', 'Build', 80, 76, '4pt'),
  makeDim('longevity', 'Longevity', 75, 72, '3pt'),
];

test('snapshot — 6 dims collapsed (hero state)', () => {
  const tree = render(
    <DimensionBars dimensions={SIX} winnerIndex={0} testID="bars" />,
  ).toJSON();
  expect(tree).toMatchSnapshot();
});

test('snapshot — 6 dims expanded (all rows visible)', () => {
  const r = render(<DimensionBars dimensions={SIX} winnerIndex={0} testID="bars" />);
  fireEvent.press(r.getByTestId('bars-expand-row'));
  expect(r.toJSON()).toMatchSnapshot();
});

test('snapshot — 2 dims (no expand row)', () => {
  const dims = SIX.slice(0, 2);
  const tree = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  ).toJSON();
  expect(tree).toMatchSnapshot();
});
