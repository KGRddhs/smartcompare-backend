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

// ---------------------------------------------------------------------
// #105 — the backend ships `confidence_details` as nested DICTS
// (response_builder._confidence_legs_and_details at b073918), not string
// arrays. The sheet must render the live dict shape via the
// toConfidenceLines adapter and degrade gracefully on anything else.
// ---------------------------------------------------------------------

test('#105 — renders live dict shape for price leg without throwing', () => {
  const { getByTestId } = render(
    <ConfidenceDetailsSheet
      visible
      leg="price"
      details={
        {
          price: {
            sources_count: 3,
            method: 'retailer_verified',
            method_p0: 'page_scrape_jsonld',
            method_p1: 'converted_usd',
            freshness: 'live',
          },
        } as any
      }
      onClose={() => {}}
    />,
  );
  expect(getByTestId('confidence-sheet-price-fact-0')).toBeTruthy();
});

test.each([
  [
    'reviews',
    { reviews: { review_count: 1200, source: 'Google Shopping', verified: true } },
  ],
  ['specs', { specs: { verified_pct: 60, citation_count: 9 } }],
])('#105 — renders live dict shape for %s leg', (leg, details) => {
  const { getByTestId } = render(
    <ConfidenceDetailsSheet
      visible
      leg={leg as any}
      details={details as any}
      onClose={() => {}}
    />,
  );
  expect(getByTestId(`confidence-sheet-${leg}-fact-0`)).toBeTruthy();
});

test.each([
  ['empty object', {}],
  ['null leg value', { price: null, reviews: null, specs: null }],
  ['undefined leg value', { price: undefined, reviews: undefined, specs: undefined }],
  ['empty leg dict', { price: {}, reviews: {}, specs: {} }],
  ['string leg value', { price: 'oops', reviews: 'oops', specs: 'oops' }],
  ['number leg value', { price: 7, reviews: 7, specs: 7 }],
])('#105 — does not throw on %s details (all three legs)', (_label, details) => {
  for (const leg of ['price', 'reviews', 'specs'] as const) {
    const { queryByTestId, unmount } = render(
      <ConfidenceDetailsSheet
        visible
        leg={leg}
        details={details as any}
        onClose={() => {}}
      />,
    );
    // Honest empty sheet — no fact lines, but no throw either.
    expect(queryByTestId(`confidence-sheet-${leg}-fact-0`)).toBeNull();
    unmount();
  }
});

test('#105 — composed lines leak no backend internals (rule #2)', () => {
  const { getByTestId } = render(
    <ConfidenceDetailsSheet
      visible
      leg="price"
      details={
        {
          price: {
            sources_count: 3,
            method: 'retailer_verified',
            method_p0: 'page_scrape_jsonld',
            method_p1: 'converted_usd',
            freshness: 'live',
          },
        } as any
      }
      onClose={() => {}}
    />,
  );
  // Every rendered fact line — walk indices until the testID runs out.
  for (let idx = 0; ; idx++) {
    let fact;
    try {
      fact = getByTestId(`confidence-sheet-price-fact-${idx}`);
    } catch {
      expect(idx).toBeGreaterThan(0); // at least one line composed
      break;
    }
    const factText = String(fact.props.children ?? '');
    // The existing rule-#2 guard regex, extended over the composed lines.
    expect(factText).not.toMatch(/\d+%|coefficient|threshold|cap of \d|multiplier/i);
    // Internal source_method enums must be mapped or omitted, never raw.
    expect(factText).not.toContain('page_scrape_jsonld');
    expect(factText).not.toContain('converted_usd');
    expect(factText).not.toContain('shopify_json');
    expect(factText).not.toContain('retailer_verified');
    // The mock catalog must actually translate — a raw key string here
    // means the composed line proves nothing.
    expect(factText).not.toMatch(/^results\.confidence\./);
  }
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
