/**
 * Bundle C — Value/Price delta hero + value-match captions
 * (Plan B.5.5–B.5.8, spec § 4b + 4c + 4d).
 *
 * Value + Price rows promote `delta_text` to hero typography (centered,
 * title-weight, emerald when winning). Score numbers shrink to caption
 * beside the bars. Other dims keep the existing inline-right caption.
 *
 * Cross-tier handling (§ 4c): when `is_cross_tier === true`, the delta
 * hero reads "Different tier — held to higher bar" with neutral coloring.
 *
 * Value-match captions (§ 4d): per-row caption beneath the value bars
 * surfaces tier mismatches without an info banner.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { StyleSheet } from 'react-native';

import { DimensionBars } from '../../src/components/results/DimensionBars';
import { colors, typography } from '../../src/theme';
import type { Dimension } from '../../src/types';

test('value row promotes delta_text to hero typography, emerald winner styling', () => {
  const dims: Dimension[] = [
    { key: 'value', label: 'Value', score_a: 88, score_b: 78, delta_text: '40% less' },
  ];
  const { getByTestId } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  const delta = getByTestId('bars-row-value-delta-hero');
  const flat = StyleSheet.flatten(delta.props.style);
  // Emerald winner color since product_a wins this row.
  expect(flat.color).toBe(colors.accent);
  // Hero typography ≥ title.fontSize (no shrinkage).
  expect(flat.fontSize).toBeGreaterThanOrEqual(typography.title.fontSize);
});

test('price row also promotes delta_text to hero typography', () => {
  const dims: Dimension[] = [
    { key: 'price', label: 'Price', score_a: 80, score_b: 90, delta_text: 'BHD 3.76 less' },
  ];
  const { getByTestId } = render(
    <DimensionBars dimensions={dims} winnerIndex={1} testID="bars" />,
  );
  expect(getByTestId('bars-row-price-delta-hero')).toBeTruthy();
});

test('non-value/non-price rows keep inline caption (no delta-hero testID)', () => {
  const dims: Dimension[] = [
    { key: 'reviews', label: 'Reviews', score_a: 88, score_b: 80, delta_text: '0.5★ higher' },
  ];
  const { queryByTestId } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  expect(queryByTestId('bars-row-reviews-delta-hero')).toBeNull();
});

test('cross-tier value row reads "Different tier — held to higher bar", neutral color', () => {
  const dims: Dimension[] = [
    { key: 'value', label: 'Value', score_a: 80, score_b: 75, delta_text: 'Stronger value', is_cross_tier: true },
  ];
  const { getByText, getByTestId } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  expect(getByText('results.value.different_tier')).toBeTruthy();
  const delta = getByTestId('bars-row-value-delta-hero');
  const flat = StyleSheet.flatten(delta.props.style);
  // Cross-tier — winner emerald suppressed; uses primary text color.
  expect(flat.color).toBe(colors.text.primary);
});

test('value row renders "above your usual range" caption when product is above_range', () => {
  const dims: Dimension[] = [
    { key: 'value', label: 'Value', score_a: 80, score_b: 75, delta_text: 'Stronger value',
      value_match_a: 'above_range', value_match_b: 'in_range' },
  ];
  const { getByText } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  expect(getByText('results.valueMatch.above_range')).toBeTruthy();
});

test('value row is SILENT on in_range / in_range (spec § 4d)', () => {
  const dims: Dimension[] = [
    { key: 'value', label: 'Value', score_a: 80, score_b: 78, delta_text: '5% less',
      value_match_a: 'in_range', value_match_b: 'in_range' },
  ];
  const { queryByText } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  expect(queryByText('results.valueMatch.above_range')).toBeNull();
  expect(queryByText('results.valueMatch.below_range')).toBeNull();
  expect(queryByText('results.valueMatch.cheaper_of_two')).toBeNull();
});

test('value row renders "cheaper of the two" when BOTH products are below_range (spec § 4e case 2)', () => {
  const dims: Dimension[] = [
    { key: 'value', label: 'Value', score_a: 80, score_b: 75, delta_text: '20% less',
      value_match_a: 'below_range', value_match_b: 'below_range' },
  ];
  const { getByText } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  expect(getByText('results.valueMatch.cheaper_of_two')).toBeTruthy();
});

test('PRICE row does NOT render value-match captions (only value row does)', () => {
  const dims: Dimension[] = [
    { key: 'price', label: 'Price', score_a: 80, score_b: 72, delta_text: '10% less',
      value_match_a: 'above_range', value_match_b: 'in_range' },
  ];
  const { queryByText } = render(
    <DimensionBars dimensions={dims} winnerIndex={0} testID="bars" />,
  );
  // value-match copy only attaches to the value row per spec § 4d wording.
  expect(queryByText('results.valueMatch.above_range')).toBeNull();
});
