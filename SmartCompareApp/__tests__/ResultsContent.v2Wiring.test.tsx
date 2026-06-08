/**
 * Lane A-L3 (Sprint A) — Tasks L3.1, L3.5, L3.6.
 *
 * v2-wiring contract for ResultsContent — proves the new backend fields
 * (variant, scoring_v2.factual_verdict.line1+line2, scoring_v2.dimensions
 * with category-specific keys, scoring_v2.confidence_legs + confidence_details)
 * actually surface to pixels. Tests develop against the fixture
 * __tests__/fixtures/v2_response_electronics.json so the mobile lane can
 * close ahead of L1's backend changes.
 *
 * Heavy-child stubs mirror ResultsContent.imageUrl.test.tsx so this suite
 * stays focused on the wiring under test (NOT on child internals — those
 * have their own dedicated tests: DimensionBars.bundle-c.test.tsx,
 * ConfidencePills.test.tsx, FactualVerdict.test.tsx, etc.).
 */

import React from 'react';
import { fireEvent, render } from '@testing-library/react-native';
import fixture from './fixtures/v2_response_electronics.json';

// Reanimated chain mock — FadeIn.duration().delay() returns same chainable
// reference so JSX `entering={FadeIn.duration(400)}` does not throw.
jest.mock('react-native-reanimated', () => {
  const real = jest.requireActual('react-native-reanimated');
  const entering = { duration: () => entering, delay: () => entering };
  return {
    __esModule: true,
    ...real,
    default: real.default ?? real,
    FadeIn: entering,
    FadeInDown: entering,
  };
});

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      let str = (opts?.defaultValue as string) ?? key;
      if (opts) {
        for (const [k, v] of Object.entries(opts)) {
          if (k === 'defaultValue') continue;
          str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
        }
      }
      return str;
    },
  }),
}));

// Heavy children we don't exercise — stub to nothing.
jest.mock('../src/components/results/TopMatchBadge', () => ({ TopMatchBadge: () => null }));
jest.mock('../src/components/results/HeroRings', () => ({ HeroRings: () => null }));
jest.mock('../src/components/results/PersonalizationChip', () => ({ PersonalizationChip: () => null }));
jest.mock('../src/components/hero/RevealBurst', () => ({ RevealBurst: () => null }));
jest.mock('../src/components/CohortBadge', () => ({ CohortBadge: () => null }));
jest.mock('../src/components/FeedbackCard', () => ({ __esModule: true, default: () => null }));
jest.mock('../src/components/results/ResultsAccordion', () => ({ ResultsAccordion: () => null }));
jest.mock('../src/services/sourceMethod', () => ({ anyEstimated: jest.fn(() => false) }));

// Real renders for the units under test (DimensionBars, ConfidencePills,
// ConfidenceDetailsSheet, FactualVerdict, ProductImage) — those carry the
// wiring assertions for this file.

import { ResultsContent } from '../src/components/results/ResultsContent';

function makeProps(overrides: Record<string, any> = {}): any {
  const products = (fixture as any).overview.products;
  return {
    result: fixture as any,
    products,
    winnerIndex: 0 as 0 | 1,
    scoring_v2: (fixture as any).scoring_v2,
    comparisonId: 'cmp_v2_wiring',
    cohortPeerCount: 0,
    cohortGovernorate: '',
    isRTL: false,
    feedbackSubmitted: false,
    onFeedbackSubmitted: () => {},
    feedbackComparisonId: undefined,
    sheetLeg: null,
    onPillPress: jest.fn(),
    onCloseSheet: jest.fn(),
    winnerScaleAnimStyle: {} as any,
    winnerRevealed: false,
    onBack: jest.fn(),
    onShare: jest.fn(),
    ...overrides,
  };
}

describe('L3.1 — variant string renders on product card', () => {
  it('renders the variant string for each product card', () => {
    const { getByText } = render(<ResultsContent {...makeProps()} />);
    expect(getByText('128GB \u00b7 Black')).toBeTruthy();
    expect(getByText('128GB \u00b7 Onyx')).toBeTruthy();
  });

  it('renders no variant element when variant missing (legacy data)', () => {
    const productsNoVariant = (fixture as any).overview.products.map((p: any) => ({
      ...p,
      variant: undefined,
    }));
    const { queryByTestId } = render(
      <ResultsContent {...makeProps({ products: productsNoVariant })} />
    );
    expect(queryByTestId('results-product-variant-0')).toBeNull();
    expect(queryByTestId('results-product-variant-1')).toBeNull();
  });

  it('renders no variant element when variant is empty string', () => {
    const productsBlankVariant = (fixture as any).overview.products.map((p: any) => ({
      ...p,
      variant: '',
    }));
    const { queryByTestId } = render(
      <ResultsContent {...makeProps({ products: productsBlankVariant })} />
    );
    expect(queryByTestId('results-product-variant-0')).toBeNull();
    expect(queryByTestId('results-product-variant-1')).toBeNull();
  });
});

describe('L3.6 — DimensionBars use v2 dimensions with category-specific labels', () => {
  it('renders electronics-specific dim labels (not generic Price/Reviews)', () => {
    const { getByText, queryByText } = render(<ResultsContent {...makeProps()} />);
    // From fixture scoring_v2.dimensions — these are electronics-specific.
    expect(getByText('Camera')).toBeTruthy();
    expect(getByText('Battery')).toBeTruthy();
    expect(getByText('Performance')).toBeTruthy();
    // Generic "Reviews" label must NOT appear as a dimension. (The
    // accordion section header is stubbed via ResultsAccordion mock so it
    // can't appear from there either.)
    expect(queryByText(/^Reviews$/)).toBeNull();
  });

  it('FactualVerdict renders both line1 and line2 from scoring_v2', () => {
    const { getByTestId, getByText } = render(<ResultsContent {...makeProps()} />);
    // Verdict carries the full line1 ("BHD 30 less, 0.2★ higher ...") while
    // DimensionBars only emits the "BHD 30 less" fragment as delta_text. We
    // pin verdict via testID and assert the full string is in the tree.
    const verdict = getByTestId('results-content-factual-verdict');
    expect(verdict).toBeTruthy();
    expect(getByText(/0\.2[\u2605]?[\s\S]*higher rating/i)).toBeTruthy();
    expect(getByText(/Galaxy S24 fits/i)).toBeTruthy();
  });
});

describe('L3.5 — ConfidencePills wired to confidence_legs; sheet wired to confidence_details', () => {
  it('renders 3 confidence pills sourced from scoring_v2.confidence_legs', () => {
    const { getByTestId } = render(<ResultsContent {...makeProps()} />);
    // ConfidencePills default testID is `confidence-pills` w/ leg suffix
    // (see ConfidencePills.test.tsx pattern). ResultsContent passes
    // `testID="results-content-confidence-pills"` to override.
    expect(getByTestId('results-content-confidence-pills-price')).toBeTruthy();
    expect(getByTestId('results-content-confidence-pills-reviews')).toBeTruthy();
    expect(getByTestId('results-content-confidence-pills-specs')).toBeTruthy();
  });

  it('opens confidence sheet with details lines when sheetLeg is set', () => {
    const { getByTestId } = render(
      <ResultsContent {...makeProps({ sheetLeg: 'price' })} />
    );
    expect(getByTestId('results-v2-confidence-sheet-price-fact-0')).toBeTruthy();
    expect(getByTestId('results-v2-confidence-sheet-price-fact-1')).toBeTruthy();
  });

  it('invokes onPillPress(leg) when a pill is tapped', () => {
    const onPillPress = jest.fn();
    const { getByTestId } = render(
      <ResultsContent {...makeProps({ onPillPress })} />
    );
    fireEvent.press(getByTestId('results-content-confidence-pills-reviews'));
    expect(onPillPress).toHaveBeenCalledWith('reviews');
  });
});
