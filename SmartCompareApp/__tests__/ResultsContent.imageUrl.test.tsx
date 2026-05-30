/**
 * Bundle E S3 A4 Wave 2 — ResultsContent image_url integration.
 *
 * A2 left a placeholder `<View testID="results-product-image-slot-{idx}">`
 * with a Smartphone glyph. A4 swaps that for `<ProductImage>` so the slot
 * actually consumes `product.image_url` (A3's contract: string | null).
 *
 * Mock pattern mirrors __tests__/components/ResultsContent.render.test.tsx
 * (A2's reference suite) — same Reanimated FadeIn + child stubs.
 *
 * Contract:
 *   - `image_url: "https://..."`  → renders <Image source.uri = that URL>
 *   - `image_url: null`           → renders placeholder
 *   - `image_url: undefined`      → renders placeholder
 *   - <Image> onError fires       → renders placeholder
 *   - aspectRatio: 1 (square tile per JSX:52)
 */

import React from 'react';
import { fireEvent, render } from '@testing-library/react-native';

// Local Reanimated mock — extends shared mock with FadeIn/FadeInDown
// chain (`.duration().delay()` returns the same object so chaining works).
jest.mock('react-native-reanimated', () => {
  const real = jest.requireActual('react-native-reanimated');
  const entering = {
    duration: () => entering,
    delay: () => entering,
  };
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

// Heavy children stubs — keep render path light. Image-rendering is what
// we exercise; deep child rendering is covered by ResultsContent.render.test.tsx.
jest.mock('../src/components/results/TopMatchBadge', () => ({
  TopMatchBadge: () => null,
}));
jest.mock('../src/components/results/HeroRings', () => ({ HeroRings: () => null }));
jest.mock('../src/components/results/DimensionBars', () => ({ DimensionBars: () => null }));
jest.mock('../src/components/results/FactualVerdict', () => ({ FactualVerdict: () => null }));
jest.mock('../src/components/results/ConfidencePills', () => ({ ConfidencePills: () => null }));
jest.mock('../src/components/results/ConfidenceDetailsSheet', () => ({
  ConfidenceDetailsSheet: () => null,
}));
jest.mock('../src/components/results/PersonalizationChip', () => ({
  PersonalizationChip: () => null,
}));
jest.mock('../src/components/hero/RevealBurst', () => ({ RevealBurst: () => null }));
jest.mock('../src/components/CohortBadge', () => ({ CohortBadge: () => null }));
jest.mock('../src/components/FeedbackCard', () => ({ __esModule: true, default: () => null }));
jest.mock('../src/components/results/ResultsAccordion', () => ({ ResultsAccordion: () => null }));
jest.mock('../src/services/sourceMethod', () => ({ anyEstimated: jest.fn(() => false) }));

import { ResultsContent } from '../src/components/results/ResultsContent';

function makeProduct(overrides: Record<string, any> = {}): any {
  return {
    brand: 'Apple',
    name: 'iPhone 15',
    price: { amount: 329, currency: 'BHD' },
    pros: [],
    cons: [],
    ...overrides,
  };
}

function makeProps(products: any[]): any {
  return {
    result: {
      overview: { winner: { product_index: 0, name: products[0].name }, products },
      comparison: {},
      metadata: {},
    } as any,
    products,
    winnerIndex: 0 as 0 | 1,
    scoring_v2: undefined,
    comparisonId: 'cmp_test',
    cohortPeerCount: 0,
    cohortGovernorate: '',
    isRTL: false,
    feedbackSubmitted: false,
    onFeedbackSubmitted: () => {},
    feedbackComparisonId: undefined,
    sheetLeg: null,
    onPillPress: () => {},
    onSheetClose: () => {},
    onCloseSheet: () => {},
    onShare: () => {},
    onBack: () => {},
    winnerScaleSV: { value: 1 } as any,
    runnerScaleSV: { value: 1 } as any,
    winnerOpacitySV: { value: 1 } as any,
    winnerScaleAnimStyle: {} as any,
    winnerRevealed: false,
    revealBurstReady: false,
    onRevealBurstComplete: () => {},
    anyEstimatedFlag: false,
  };
}

describe('ResultsContent — image_url slot wires to <ProductImage>', () => {
  it('renders <Image> for both products when both image_urls present', () => {
    const products = [
      makeProduct({ image_url: 'https://cdn.example.com/iphone15.jpg' }),
      makeProduct({
        name: 'Galaxy S24',
        brand: 'Samsung',
        image_url: 'https://cdn.example.com/galaxy24.jpg',
      }),
    ];
    const { getByTestId, queryByTestId } = render(
      <ResultsContent {...makeProps(products)} />
    );
    expect(getByTestId('results-product-image-slot-0-img').props.source).toEqual({
      uri: 'https://cdn.example.com/iphone15.jpg',
    });
    expect(getByTestId('results-product-image-slot-1-img').props.source).toEqual({
      uri: 'https://cdn.example.com/galaxy24.jpg',
    });
    expect(queryByTestId('results-product-image-slot-0-placeholder')).toBeNull();
    expect(queryByTestId('results-product-image-slot-1-placeholder')).toBeNull();
  });

  it('renders placeholder when product.image_url is null', () => {
    const products = [
      makeProduct({ image_url: null }),
      makeProduct({ name: 'Galaxy S24', image_url: null }),
    ];
    const { getByTestId, queryByTestId } = render(
      <ResultsContent {...makeProps(products)} />
    );
    expect(getByTestId('results-product-image-slot-0-placeholder')).toBeTruthy();
    expect(getByTestId('results-product-image-slot-1-placeholder')).toBeTruthy();
    expect(queryByTestId('results-product-image-slot-0-img')).toBeNull();
    expect(queryByTestId('results-product-image-slot-1-img')).toBeNull();
  });

  it('renders placeholder when product.image_url is undefined (legacy data)', () => {
    const products = [makeProduct(), makeProduct({ name: 'Galaxy S24' })];
    const { getByTestId, queryByTestId } = render(
      <ResultsContent {...makeProps(products)} />
    );
    expect(getByTestId('results-product-image-slot-0-placeholder')).toBeTruthy();
    expect(getByTestId('results-product-image-slot-1-placeholder')).toBeTruthy();
    expect(queryByTestId('results-product-image-slot-0-img')).toBeNull();
  });

  it('mixed state — first product has URL, second is null → image + placeholder', () => {
    const products = [
      makeProduct({ image_url: 'https://cdn.example.com/iphone15.jpg' }),
      makeProduct({ name: 'Galaxy S24', image_url: null }),
    ];
    const { getByTestId, queryByTestId } = render(
      <ResultsContent {...makeProps(products)} />
    );
    expect(getByTestId('results-product-image-slot-0-img')).toBeTruthy();
    expect(getByTestId('results-product-image-slot-1-placeholder')).toBeTruthy();
    expect(queryByTestId('results-product-image-slot-1-img')).toBeNull();
    expect(queryByTestId('results-product-image-slot-0-placeholder')).toBeNull();
  });

  it('swaps to placeholder when <Image> onError fires (broken URL)', () => {
    const products = [
      makeProduct({ image_url: 'https://cdn.example.com/404.jpg' }),
      makeProduct({ name: 'Galaxy S24', image_url: null }),
    ];
    const { getByTestId, queryByTestId } = render(
      <ResultsContent {...makeProps(products)} />
    );
    const img = getByTestId('results-product-image-slot-0-img');
    expect(img).toBeTruthy();
    fireEvent(img, 'error');
    expect(queryByTestId('results-product-image-slot-0-img')).toBeNull();
    expect(getByTestId('results-product-image-slot-0-placeholder')).toBeTruthy();
  });

  it('image slot keeps the JSX-spec aspectRatio: 1 (square tile)', () => {
    const products = [
      makeProduct({ image_url: 'https://cdn.example.com/iphone15.jpg' }),
      makeProduct({ name: 'Galaxy S24', image_url: null }),
    ];
    const { getByTestId } = render(<ResultsContent {...makeProps(products)} />);
    const img = getByTestId('results-product-image-slot-0-img');
    const styleArr = Array.isArray(img.props.style) ? img.props.style : [img.props.style];
    const flat = Object.assign({}, ...styleArr.filter(Boolean));
    expect(flat.aspectRatio).toBe(1);
  });
});
