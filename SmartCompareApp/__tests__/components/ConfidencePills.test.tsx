/**
 * Bundle C — ConfidencePills (Plan B.7.1, spec § 5b + § 5c + § 5d).
 *
 * 3-pill horizontal row replaces the legacy single-word confidence
 * banner. Colors: emerald (strong), amber (acceptable), gray-muted (weak).
 * Tap → caller opens "What we know" bottom sheet (component is dumb;
 * tap dispatch flows up via `onPillPress`).
 *
 * § 5c — Price pill HIDDEN when any product has source_method=estimated.
 * § 5d — NO single overall-confidence label; the 3 pills carry the story.
 */
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { StyleSheet } from 'react-native';

import { ConfidencePills } from '../../src/components/results/ConfidencePills';
import { colors } from '../../src/theme';

test('renders 3 pills with translated labels', () => {
  const { getByText } = render(
    <ConfidencePills
      confidence={{ price: 'strong', reviews: 'acceptable', specs: 'weak' }}
      onPillPress={() => {}}
    />,
  );
  // Mock i18n returns the key — labels under results.confidence.pill.* must render.
  expect(getByText('results.confidence.pill.price')).toBeTruthy();
  expect(getByText('results.confidence.pill.reviews')).toBeTruthy();
  expect(getByText('results.confidence.pill.specs')).toBeTruthy();
});

test('strong = emerald, acceptable = amber/warning, weak = muted', () => {
  const { getByTestId } = render(
    <ConfidencePills
      confidence={{ price: 'strong', reviews: 'acceptable', specs: 'weak' }}
      onPillPress={() => {}}
      testID="pills"
    />,
  );
  const strong = StyleSheet.flatten(getByTestId('pills-price').props.style);
  const acceptable = StyleSheet.flatten(getByTestId('pills-reviews').props.style);
  const weak = StyleSheet.flatten(getByTestId('pills-specs').props.style);
  expect(strong.backgroundColor).toBe(colors.accentLight); // emerald-tinted background, accent text
  expect(acceptable.backgroundColor).toBe(colors.warning + '22');
  expect(weak.backgroundColor).toBe(colors.bg.secondary);
});

test('omits Price pill when hidePricePill prop is true (spec § 5c)', () => {
  const { queryByText, getByText } = render(
    <ConfidencePills
      confidence={{ price: 'strong', reviews: 'strong', specs: 'strong' }}
      hidePricePill
      onPillPress={() => {}}
    />,
  );
  expect(queryByText('results.confidence.pill.price')).toBeNull();
  expect(getByText('results.confidence.pill.reviews')).toBeTruthy();
  expect(getByText('results.confidence.pill.specs')).toBeTruthy();
});

test('tapping a pill dispatches onPillPress with the leg name', () => {
  const onPillPress = jest.fn();
  const { getByTestId } = render(
    <ConfidencePills
      confidence={{ price: 'strong', reviews: 'strong', specs: 'strong' }}
      onPillPress={onPillPress}
      testID="pills"
    />,
  );
  fireEvent.press(getByTestId('pills-reviews'));
  expect(onPillPress).toHaveBeenCalledWith('reviews');
  fireEvent.press(getByTestId('pills-specs'));
  expect(onPillPress).toHaveBeenCalledWith('specs');
});

test('omits a pill whose confidence is missing/undefined entirely', () => {
  const { queryByText, getByText } = render(
    <ConfidencePills
      confidence={{ price: 'strong', specs: 'strong' }} // reviews missing
      onPillPress={() => {}}
    />,
  );
  expect(queryByText('results.confidence.pill.reviews')).toBeNull();
  expect(getByText('results.confidence.pill.price')).toBeTruthy();
  expect(getByText('results.confidence.pill.specs')).toBeTruthy();
});

test('renders nothing when no legs are present (all undefined)', () => {
  const tree = render(<ConfidencePills confidence={{}} onPillPress={() => {}} />).toJSON();
  expect(tree).toBeNull();
});

test('NO scary copy, NO provenance words in any rendered pill (spec § 5c + § 5d)', () => {
  const tree = render(
    <ConfidencePills
      confidence={{ price: 'weak', reviews: 'weak', specs: 'weak' }}
      onPillPress={() => {}}
    />,
  ).toJSON();
  const text = JSON.stringify(tree);
  expect(text).not.toMatch(/\b(couldn't|try again|Failed to|estimated|reference price|indicative)\b/i);
  expect(text).not.toMatch(/(تعذر|فشل|تقدير|مُقدَّر)/);
  // § 5d — no single overall confidence word like "High confidence data".
  expect(text).not.toMatch(/High confidence data|Medium confidence data|Low confidence data/i);
});
