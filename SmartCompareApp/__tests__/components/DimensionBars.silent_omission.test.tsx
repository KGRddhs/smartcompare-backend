/**
 * Bundle C — DimensionBars silent omission (Plan B.5.1 + B.5.2, spec § 2h).
 *
 * Dims with `score_a === null || score_b === null` are silently omitted
 * from the rendered tree — no "—", no muted row, no caption. The user
 * sees a clean-looking 5-card breakdown rather than apologizing for
 * missing signal.
 *
 * The pre-existing zero-score contract-violation node stays as a dev-mode
 * regression catcher (spec § 6d): if backend ever leaks an actual 0
 * score (not null), the violation surface still fires.
 */
import React from 'react';
import { render } from '@testing-library/react-native';

import { DimensionBars } from '../../src/components/results/DimensionBars';
import type { Dimension } from '../../src/types';

const baseDim = (overrides: Partial<Dimension>): Dimension => ({
  key: 'price',
  label: 'Price',
  score_a: 80,
  score_b: 72,
  delta_text: '10% less',
  ...overrides,
});

test('dimensions with score_a=null on either side are silently omitted (spec § 2h)', () => {
  const dims: Dimension[] = [
    baseDim({ key: 'price', label: 'Price', score_a: 80, score_b: 72 }),
    baseDim({ key: 'reviews', label: 'Reviews', score_a: null, score_b: 75, delta_text: '' }),
    baseDim({ key: 'specs', label: 'Specs', score_a: 70, score_b: 80, delta_text: '' }),
  ];
  const { queryByTestId } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  expect(queryByTestId('bars-row-price')).toBeTruthy();
  expect(queryByTestId('bars-row-reviews')).toBeNull(); // silently omitted
  expect(queryByTestId('bars-row-specs')).toBeTruthy();
});

test('dimensions with score_b=null on either side are silently omitted', () => {
  const dims: Dimension[] = [
    baseDim({ key: 'price', score_a: 80, score_b: 72 }),
    baseDim({ key: 'reviews', label: 'Reviews', score_a: 88, score_b: null }),
  ];
  const { queryByTestId } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  expect(queryByTestId('bars-row-price')).toBeTruthy();
  expect(queryByTestId('bars-row-reviews')).toBeNull();
});

test('all-null dimension list renders empty container, NOT contract-violation node', () => {
  const dims: Dimension[] = [
    baseDim({ key: 'price', score_a: null, score_b: null }),
    baseDim({ key: 'reviews', label: 'Reviews', score_a: null, score_b: null }),
  ];
  const { queryByTestId } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  // No rows render
  expect(queryByTestId('bars-row-price')).toBeNull();
  expect(queryByTestId('bars-row-reviews')).toBeNull();
  // Crucially — null scores must NOT trip the zero-score contract
  // violation node (spec § 6d reserves that for actual 0 scores).
  expect(queryByTestId('bars-contract-violation')).toBeNull();
});

test('actual score=0 STILL trips contract-violation node (spec § 6d safety net)', () => {
  const dims: Dimension[] = [
    baseDim({ key: 'price', score_a: 0, score_b: 75 }),
  ];
  const { queryByTestId } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  expect(queryByTestId('bars-contract-violation')).toBeTruthy();
  expect(queryByTestId('bars-row-price')).toBeNull();
});

test('mix of null + populated dims renders only populated ones, no violation', () => {
  const dims: Dimension[] = [
    baseDim({ key: 'price', score_a: 80, score_b: 72 }),
    baseDim({ key: 'reviews', label: 'Reviews', score_a: null, score_b: null }),
    baseDim({ key: 'specs', label: 'Specs', score_a: 70, score_b: 80 }),
  ];
  const { queryByTestId } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  expect(queryByTestId('bars-row-price')).toBeTruthy();
  expect(queryByTestId('bars-row-reviews')).toBeNull();
  expect(queryByTestId('bars-row-specs')).toBeTruthy();
  expect(queryByTestId('bars-contract-violation')).toBeNull();
});
