/**
 * #105 — tapping a confidence pill on a LIVE-shape payload opens the
 * "What we know" sheet instead of throwing.
 *
 * The backend ships `scoring_v2.confidence_details` as nested dicts
 * (response_builder._confidence_legs_and_details at b073918); the old
 * client called `.map` on that dict mid-render, so every real tap threw a
 * TypeError. The hand-written string-array fixtures kept this invisible —
 * this suite renders through ResultsContent with the live-shape fixture
 * (now carrying the real dict shape) and a set sheetLeg.
 *
 * Scaffolding copied verbatim from ResultsContent.v2Wiring.test.tsx
 * (reanimated chain mock, per-file react-i18next mock with defaultValue
 * support, heavy-child stubs, makeProps).
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import fixture from './fixtures/v2_response_electronics_live_shape.json';

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
jest.mock('../src/components/results/PersonalizationChip', () => ({ PersonalizationChip: () => null }));
jest.mock('../src/components/hero/RevealBurst', () => ({ RevealBurst: () => null }));
jest.mock('../src/components/CohortBadge', () => ({ CohortBadge: () => null }));
jest.mock('../src/components/FeedbackCard', () => ({ __esModule: true, default: () => null }));
jest.mock('../src/components/results/ResultsAccordion', () => ({ ResultsAccordion: () => null }));
jest.mock('../src/services/sourceMethod', () => ({ anyEstimated: jest.fn(() => false), isConvertedUsd: jest.fn((p: any) => p?.source_method === 'converted_usd') }));

import { ResultsContent } from '../src/components/results/ResultsContent';

function makeProps(overrides: Record<string, any> = {}): any {
  const products = (fixture as any).overview.products;
  return {
    result: fixture as any,
    products,
    winnerIndex: 0 as 0 | 1,
    scoring_v2: (fixture as any).scoring_v2,
    comparisonId: 'cmp_confidence_sheet',
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

describe('#105 — confidence sheet renders the live dict shape', () => {
  it('sanity pin — the live-shape fixture carries DICT confidence_details', () => {
    const details = (fixture as any).scoring_v2.confidence_details;
    for (const leg of ['price', 'reviews', 'specs']) {
      expect(Array.isArray(details[leg])).toBe(false);
      expect(typeof details[leg]).toBe('object');
    }
  });

  it.each(['price', 'reviews', 'specs'] as const)(
    'opening the sheet for the %s leg on a live-shape payload renders fact lines',
    (leg) => {
      const { getByTestId } = render(
        <ResultsContent {...makeProps({ sheetLeg: leg })} />
      );
      expect(getByTestId('results-v2-confidence-sheet')).toBeTruthy();
      expect(getByTestId(`results-v2-confidence-sheet-${leg}-fact-0`)).toBeTruthy();
    },
  );

  it('a payload with NO confidence_details still opens an empty sheet without throwing', () => {
    const scoringV2 = {
      ...(fixture as any).scoring_v2,
      confidence_details: undefined,
    };
    const { getByTestId, queryByTestId } = render(
      <ResultsContent {...makeProps({ sheetLeg: 'price', scoring_v2: scoringV2 })} />
    );
    expect(getByTestId('results-v2-confidence-sheet')).toBeTruthy();
    expect(queryByTestId('results-v2-confidence-sheet-price-fact-0')).toBeNull();
  });
});
