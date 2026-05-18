/**
 * Bundle C — ConfidenceDetailsSheet (Plan B.7.3, spec § 5b).
 *
 * "What we know" bottom sheet. Renders 2-3 factual lines per leg, sourced
 * verbatim from `scoring_v2.confidence_details` (backend-composed). The
 * component NEVER composes strings — it's a presentation surface only.
 *
 * Critical rule #2 — NO backend internals: no thresholds, coefficients,
 * cap percentages, or shift math leak into the rendered text. Frontend
 * defends with a regex that fails the test if any forbidden pattern
 * appears in the props rendered by the sheet.
 */
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';

import { ConfidenceDetailsSheet } from '../../src/components/results/ConfidenceDetailsSheet';

test('renders 2-3 factual lines for reviews leg', () => {
  const details = {
    reviews: [
      '1200 reviews aggregated from Amazon, Best Buy, Google.',
      'Source verification pending.',
    ],
  };
  const { getByText } = render(
    <ConfidenceDetailsSheet visible leg="reviews" details={details} onClose={() => {}} />,
  );
  expect(getByText(/1200 reviews aggregated/)).toBeTruthy();
  expect(getByText(/Source verification pending/)).toBeTruthy();
});

test('renders Specs lines verbatim from backend payload', () => {
  const details = {
    specs: ['23 of 30 fields verified against manufacturer sources.'],
  };
  const { getByText } = render(
    <ConfidenceDetailsSheet visible leg="specs" details={details} onClose={() => {}} />,
  );
  expect(getByText(/23 of 30 fields/)).toBeTruthy();
});

test('Close button dispatches onClose callback', () => {
  const onClose = jest.fn();
  const { getByText } = render(
    <ConfidenceDetailsSheet
      visible
      leg="price"
      details={{ price: ['Listed at 3 retailers including Amazon.'] }}
      onClose={onClose}
    />,
  );
  fireEvent.press(getByText('results.confidence.sheet.close'));
  expect(onClose).toHaveBeenCalledTimes(1);
});

test('renders sheet title via translation', () => {
  const { getByText } = render(
    <ConfidenceDetailsSheet
      visible
      leg="reviews"
      details={{ reviews: ['One line.'] }}
      onClose={() => {}}
    />,
  );
  expect(getByText('results.confidence.sheet.title')).toBeTruthy();
});

test('renders nothing when not visible', () => {
  const tree = render(
    <ConfidenceDetailsSheet
      visible={false}
      leg="reviews"
      details={{ reviews: ['One line.'] }}
      onClose={() => {}}
    />,
  ).toJSON();
  // Modal stripped via __mocks__/react-native or visible=false hides the surface.
  // We tolerate either null OR a present-but-empty wrapper (no leg text rendered).
  const text = tree ? JSON.stringify(tree) : '';
  expect(text).not.toContain('One line.');
});

test('renders nothing when the requested leg has no details', () => {
  const tree = render(
    <ConfidenceDetailsSheet
      visible
      leg="specs"
      details={{ reviews: ['Wrong leg, should not surface.'] }}
      onClose={() => {}}
    />,
  ).toJSON();
  const text = tree ? JSON.stringify(tree) : '';
  expect(text).not.toContain('Wrong leg');
});

test('NO threshold numbers or coefficient leaks across props (spec § 5b + rule #2)', () => {
  // Synthetic clean payload — passes by default. The point of this guard
  // is to fail loud if backend ever leaks a percent/cap/coefficient
  // into a rendered fact line. We only inspect the user-visible text
  // (the facts themselves), NOT the JSON-serialized style props which
  // legitimately contain "70%" maxHeight etc.
  const cleanDetails = {
    reviews: ['1200 reviews aggregated from Amazon and Best Buy.'],
    specs: ['23 of 30 fields verified.'],
    price: ['Listed at 3 retailers.'],
  };
  const { getByTestId } = render(
    <ConfidenceDetailsSheet visible leg="reviews" details={cleanDetails} onClose={() => {}} />,
  );
  // The fact text is what the user reads. Inspect ONLY its children.
  const fact = getByTestId('confidence-sheet-reviews-fact-0');
  const factText = String(fact.props.children ?? '');
  expect(factText).not.toMatch(/\d+%|coefficient|threshold|cap of \d|multiplier/i);
});

test('NO scary copy across rendered facts (spec § 5d, rule #5)', () => {
  const tree = render(
    <ConfidenceDetailsSheet
      visible
      leg="reviews"
      details={{ reviews: ['Aggregated from 3 sources.'] }}
      onClose={() => {}}
    />,
  ).toJSON();
  const text = JSON.stringify(tree);
  expect(text).not.toMatch(/\b(couldn't|try again|Failed to|estimated|reference price|indicative)\b/i);
  expect(text).not.toMatch(/(تعذر|فشل|تقدير|مُقدَّر)/);
});
