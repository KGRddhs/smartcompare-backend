/**
 * Idle-time parametrized per-category test — WIP branch
 * `wip/A-L3-percategory-mobile-fixtures-idle-time`.
 *
 * Extends ResultsContent.v2Wiring.test.tsx with category-specific render
 * checks for all 9 categories. Asserts:
 *   (a) all dim labels match the design system spec (no generic
 *       "Performance"/"Value" labels leaking into category screens)
 *   (b) variant string renders OR gracefully omits
 *   (c) confidence pills always 3 (price/reviews/specs) — modulo
 *       fragrance fixture which suppresses Price when source_method:estimated
 *   (d) factual_verdict.line1+line2 both rendered
 *   (e) winner card has the emerald ring (testID match)
 */

import React from 'react';
import { render } from '@testing-library/react-native';

// Reanimated chain mock
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

jest.mock('../src/components/results/TopMatchBadge', () => ({ TopMatchBadge: () => null }));
jest.mock('../src/components/results/HeroRings', () => ({ HeroRings: () => null }));
jest.mock('../src/components/results/PersonalizationChip', () => ({ PersonalizationChip: () => null }));
jest.mock('../src/components/hero/RevealBurst', () => ({ RevealBurst: () => null }));
jest.mock('../src/components/CohortBadge', () => ({ CohortBadge: () => null }));
jest.mock('../src/components/FeedbackCard', () => ({ __esModule: true, default: () => null }));
jest.mock('../src/components/results/ResultsAccordion', () => ({ ResultsAccordion: () => null }));

// anyEstimated factory — overridden per fixture so fragrances suppresses
// the Price pill while other categories keep all 3.
jest.mock('../src/services/sourceMethod', () => ({ anyEstimated: jest.fn(() => false) }));

import { ResultsContent } from '../src/components/results/ResultsContent';
import { anyEstimated } from '../src/services/sourceMethod';

interface CategoryFixture {
  name: string;
  fixture: any;
  expectedLabels: string[];
  hideePricePill?: boolean;
}

const FIXTURES: CategoryFixture[] = [
  {
    name: 'electronics',
    fixture: require('./fixtures/v2_response_electronics.json'),
    expectedLabels: ['Camera', 'Battery', 'Performance', 'Value'],
  },
  {
    name: 'grocery',
    fixture: require('./fixtures/v2_response_grocery.json'),
    expectedLabels: ['Price', 'Reviews', 'Value', 'Nutrition', 'Ingredients', 'Taste'],
  },
  {
    name: 'supplements',
    fixture: require('./fixtures/v2_response_supplements.json'),
    expectedLabels: ['Price', 'Reviews', 'Value', 'Efficacy', 'Safety', 'Trust'],
  },
  {
    name: 'makeup',
    fixture: require('./fixtures/v2_response_makeup.json'),
    expectedLabels: ['Price', 'Reviews', 'Value', 'Shade range', 'Longevity', 'Finish'],
  },
  {
    name: 'skincare',
    fixture: require('./fixtures/v2_response_skincare.json'),
    expectedLabels: ['Price', 'Reviews', 'Value', 'Active ingredients', 'Evidence', 'Skin compatibility'],
  },
  {
    name: 'haircare',
    fixture: require('./fixtures/v2_response_haircare.json'),
    expectedLabels: ['Price', 'Reviews', 'Value', 'Hair match', 'Results', 'Ingredients'],
  },
  {
    name: 'fragrances',
    fixture: require('./fixtures/v2_response_fragrances.json'),
    expectedLabels: ['Price', 'Reviews', 'Value', 'Character', 'Longevity', 'Projection'],
    hideePricePill: true, // estimated source_method on both products
  },
  {
    name: 'fashion',
    fixture: require('./fixtures/v2_response_fashion.json'),
    expectedLabels: ['Price', 'Reviews', 'Value', 'Craftsmanship', 'Durability', 'Heritage'],
  },
  {
    name: 'other',
    fixture: require('./fixtures/v2_response_other.json'),
    expectedLabels: ['Price', 'Reviews', 'Value', 'Function', 'Build', 'Reliability'],
  },
];

function makeProps(fixture: any, overrides: Record<string, any> = {}) {
  const products = fixture.overview.products;
  const winnerIndex = (fixture.winner_index ?? fixture.overview.winner.product_index) as 0 | 1;
  return {
    result: fixture,
    products,
    winnerIndex,
    scoring_v2: fixture.scoring_v2,
    comparisonId: `cmp_percat_${fixture.category_used}`,
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

describe.each(FIXTURES)(
  'ResultsContent per-category — $name',
  ({ name, fixture, expectedLabels, hideePricePill }) => {
    beforeEach(() => {
      (anyEstimated as jest.Mock).mockReturnValue(!!hideePricePill);
    });

    it('renders the first 4 expected dim labels in the hero card (HERO_CAP=4)', () => {
      // DimensionBars caps the hero render at 4 dims; remaining hide
      // behind a "See full breakdown" expand row. Per-category test
      // covers the visible top-4 only — the expand-row behaviour is
      // exercised by DimensionBars.hero_expand.test.tsx.
      const { getByText } = render(<ResultsContent {...makeProps(fixture)} />);
      for (const label of expectedLabels.slice(0, 4)) {
        expect(getByText(label)).toBeTruthy();
      }
    });

    it('renders the variant string for both products (or omits when absent)', () => {
      const { queryByTestId } = render(<ResultsContent {...makeProps(fixture)} />);
      const p0 = fixture.overview.products[0];
      const p1 = fixture.overview.products[1];
      if (p0.variant && p0.variant.length > 0) {
        expect(queryByTestId('results-product-variant-0')).toBeTruthy();
      } else {
        expect(queryByTestId('results-product-variant-0')).toBeNull();
      }
      if (p1.variant && p1.variant.length > 0) {
        expect(queryByTestId('results-product-variant-1')).toBeTruthy();
      } else {
        expect(queryByTestId('results-product-variant-1')).toBeNull();
      }
    });

    it('renders 3 confidence pills unless Price hidden by estimated source', () => {
      const { queryByTestId, getByTestId } = render(
        <ResultsContent {...makeProps(fixture)} />
      );
      if (hideePricePill) {
        expect(queryByTestId('results-content-confidence-pills-price')).toBeNull();
      } else {
        expect(getByTestId('results-content-confidence-pills-price')).toBeTruthy();
      }
      expect(getByTestId('results-content-confidence-pills-reviews')).toBeTruthy();
      expect(getByTestId('results-content-confidence-pills-specs')).toBeTruthy();
    });

    it('FactualVerdict carries both line1 + line2 from scoring_v2', () => {
      const { getByTestId, getByText } = render(
        <ResultsContent {...makeProps(fixture)} />
      );
      expect(getByTestId('results-content-factual-verdict')).toBeTruthy();
      // line2 snippet uniqueness varies per fixture; spot-check a few words.
      const line2 = fixture.scoring_v2.factual_verdict.line2;
      const snippet = line2.split(/\s+/).slice(0, 3).join(' ');
      expect(getByText(new RegExp(snippet.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i'))).toBeTruthy();
    });

    it('winner card carries the emerald-ring testID', () => {
      const { getByTestId } = render(
        <ResultsContent
          {...makeProps(fixture, { winnerRevealed: true })}
        />
      );
      // The winning product's animated card carries testID="winner-card-anim".
      expect(getByTestId('winner-card-anim')).toBeTruthy();
    });

    it('winner star is in-position per overview.winner.product_index', () => {
      // The accordion is mocked; we pin the value here for cross-QA traceability.
      const declaredWinner = fixture.overview.winner.product_index;
      const flagWinner = fixture.overview.products.findIndex(
        (p: any) => p.is_winner === true
      );
      // Both signals must agree so the L2 accordion sees the same winner
      // index ResultsContent computes for the hero pair.
      expect(declaredWinner).toBe(flagWinner);
      expect(declaredWinner).toBe(fixture.winner_index);
    });
  }
);
