/**
 * Bundle C — BudgetPicker 5-tier expansion (Plan B.3.1 – B.3.3)
 *
 * Spec § 3a + 3c — 5 cards, premium/luxury/top_tier get subtle dark accent,
 * top_tier label uses heaviest available font weight (Geist-Bold) per
 * editorial-restraint rule. No gaudy gold, no border glow.
 */
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { StyleSheet } from 'react-native';

import BudgetPicker from '../../src/components/BudgetPicker';
import { colors } from '../../src/theme';

test('renders 5 tier cards', () => {
  const { getByTestId } = render(<BudgetPicker value="mid" onChange={() => {}} />);
  ['budget', 'mid', 'premium', 'luxury', 'top_tier'].forEach((v) => {
    expect(getByTestId(`budget-${v}`)).toBeTruthy();
  });
});

test('snapshot — 5 tier picker with luxury selected', () => {
  const tree = render(<BudgetPicker value="luxury" onChange={() => {}} />).toJSON();
  expect(tree).toMatchSnapshot();
});

test('selected card receives selected accessibility state', () => {
  const { getByTestId } = render(<BudgetPicker value="top_tier" onChange={() => {}} />);
  expect(getByTestId('budget-top_tier').props.accessibilityState.selected).toBe(true);
  expect(getByTestId('budget-budget').props.accessibilityState.selected).toBe(false);
});

test('onChange fires when a card is pressed', () => {
  const onChange = jest.fn();
  const { getByTestId } = render(<BudgetPicker value="mid" onChange={onChange} />);
  fireEvent.press(getByTestId('budget-top_tier'));
  expect(onChange).toHaveBeenCalledWith('top_tier');
});

test('top_tier label uses heaviest available font weight (Geist-Bold or 700)', () => {
  const { getByTestId } = render(<BudgetPicker value="top_tier" onChange={() => {}} />);
  // The label is the first Text inside the card. We pull it via testID convention.
  const card = getByTestId('budget-top_tier-label');
  const flat = StyleSheet.flatten(card.props.style);
  const heavy = flat.fontFamily === 'Geist-Bold' || flat.fontWeight === '700' || flat.fontWeight === 'bold';
  expect(heavy).toBe(true);
});

test('premium / luxury / top_tier cards carry the editorial-dark accent token', () => {
  const { getByTestId } = render(<BudgetPicker value="mid" onChange={() => {}} />);
  // The card root carries an accent prop reflected in resolved style.
  for (const tier of ['premium', 'luxury', 'top_tier']) {
    const card = getByTestId(`budget-${tier}`);
    const flat = StyleSheet.flatten(card.props.style);
    // Editorial-dark accent applied as a left-border or background tint —
    // the exact mechanism varies, but the resolved style MUST mention
    // colors.editorialDark via at least one of: borderLeftColor,
    // borderColor (when not in `cardSelected` state), or backgroundColor.
    const accent = colors.editorialDark;
    const mentioned =
      flat.borderLeftColor === accent ||
      flat.borderColor === accent ||
      flat.backgroundColor === accent ||
      flat.color === accent;
    expect(mentioned).toBe(true);
  }
});

test('budget + mid cards do NOT carry the editorial-dark accent', () => {
  const { getByTestId } = render(<BudgetPicker value="mid" onChange={() => {}} />);
  for (const tier of ['budget', 'mid']) {
    const card = getByTestId(`budget-${tier}`);
    const flat = StyleSheet.flatten(card.props.style);
    const accent = colors.editorialDark;
    const mentioned =
      flat.borderLeftColor === accent ||
      flat.borderColor === accent ||
      flat.backgroundColor === accent;
    expect(mentioned).toBe(false);
  }
});
