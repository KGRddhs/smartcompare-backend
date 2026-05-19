/**
 * Bundle C — Step09Budget 5-tier expansion (Plan B.4.2)
 *
 * Spec § 3a + 3c — onboarding step 9 mirrors BudgetPicker (5 cards) and
 * appends a single-line "Varies by category" caveat below the cards per
 * spec § 3c (picker shows general guidance; per-category re-anchoring
 * is server-side and invisible).
 */
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';

import { Step09Budget } from '../../src/screens/onboarding/Step09Budget';

test('renders 5 tier cards + caveat line', () => {
  const { getByTestId, getByText } = render(
    <Step09Budget value="mid" onChange={() => {}} />,
  );
  ['budget', 'mid', 'premium', 'luxury', 'top_tier'].forEach((v) => {
    expect(getByTestId(`budget-${v}`)).toBeTruthy();
  });
  // Mock i18n returns the key — the caveat key must render.
  expect(getByText('onboarding.s9.caveat')).toBeTruthy();
});

test('snapshot — Step09Budget with top_tier selected', () => {
  const tree = render(
    <Step09Budget value="top_tier" onChange={() => {}} />,
  ).toJSON();
  expect(tree).toMatchSnapshot();
});

test('onChange fires with top_tier when its card is pressed', () => {
  const onChange = jest.fn();
  const { getByTestId } = render(<Step09Budget value="mid" onChange={onChange} />);
  fireEvent.press(getByTestId('budget-top_tier'));
  expect(onChange).toHaveBeenCalledWith('top_tier');
});

test('caveat key is wired below the cards (testID for layout assertion)', () => {
  const { getByTestId } = render(<Step09Budget value="mid" onChange={() => {}} />);
  expect(getByTestId('s9-caveat')).toBeTruthy();
});
