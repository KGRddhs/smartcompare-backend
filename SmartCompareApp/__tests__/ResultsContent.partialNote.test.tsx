/**
 * Frag-content-quality WS-F Task F2 (FE-8) — partial-result affordance.
 *
 * Fragrance compares routinely hit the 30s STREAM_HARD_CAP and come back with
 * `metadata.partial === true` (a best-available assembly, NOT an error). When
 * that happens the Results page should carry a calm one-liner so the compare
 * reads as "still settling," never broken or scary.
 *
 * The copy already exists at `results.partial.note` (en.json:736 / ar.json:733
 * — "Prices are still settling — tap to refresh in a moment.") and is
 * copy-policy clean (no couldn't / try again / Failed to / تعذر / فشل). This
 * suite pins:
 *   - metadata.partial === true  → the localized note renders
 *   - metadata.partial false / absent / no metadata → the note does NOT render
 *
 * The i18n mock below is a key passthrough: `t('results.partial.note')` returns
 * the literal key, so we assert against the key string.
 */

import React from 'react';
import { render } from '@testing-library/react-native';

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

// i18n passthrough — `t(key)` returns the key.
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

jest.mock('../src/components/results/DimensionBars', () => ({
  DimensionBars: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-dim-bars'} />;
  },
}));
jest.mock('../src/components/results/ConfidencePills', () => ({
  ConfidencePills: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-confidence-pills'} />;
  },
}));
jest.mock('../src/components/results/ConfidenceDetailsSheet', () => ({
  ConfidenceDetailsSheet: () => null,
}));
jest.mock('../src/components/results/PersonalizationChip', () => ({
  PersonalizationChip: () => null,
}));
jest.mock('../src/components/results/TopMatchBadge', () => ({
  TopMatchBadge: () => null,
}));
jest.mock('../src/components/results/RunnerUpWinsCard', () => ({
  RunnerUpWinsCard: () => null,
}));
jest.mock('../src/components/hero/RevealBurst', () => ({ RevealBurst: () => null }));
jest.mock('../src/components/CohortBadge', () => ({ CohortBadge: () => null }));
jest.mock('../src/components/FeedbackCard', () => ({ __esModule: true, default: () => null }));
jest.mock('../src/components/results/ResultsAccordion', () => ({
  ResultsAccordion: () => null,
}));
jest.mock('../src/services/sourceMethod', () => ({ anyEstimated: jest.fn(() => false) }));

import { ResultsContent } from '../src/components/results/ResultsContent';

const PARTIAL_NOTE_KEY = 'results.partial.note';

const products: any = [
  { name: 'Oud Wood', brand: 'Tom Ford', price: { amount: 146.64, currency: 'BHD' } },
  { name: 'Oud Voyager', brand: 'Tom Ford', price: { amount: 120, currency: 'BHD' } },
];

const scoring: any = {
  factual_verdict: { line1: 'Oud Wood is longer-lasting.', line2: 'Both wear warm.' },
  dimensions: [
    { dim: 'longevity', winner_index: 0 },
    { dim: 'sillage', winner_index: 0 },
    { dim: 'projection', winner_index: 1 },
  ],
  confidence_legs: { price: 'high', reviews: 'medium', specs: 'high' },
  personalization: { applied_shifts: [] },
  comparison_quality: 'normal',
  confidence_details: {},
};

function makeProps(metadata?: any): any {
  return {
    result: {
      overview: {
        winner: {
          product_index: 0,
          name: 'Oud Wood',
          reason: 'Longer-lasting on skin with a warmer drydown.',
          key_tradeoff: 'Voyager is fresher for daytime wear.',
        },
        products,
      },
      recommendation: 'Oud Wood is the stronger overall pick',
      ...(metadata === undefined ? {} : { metadata }),
    },
    products,
    winnerIndex: 0 as 0 | 1,
    scoring_v2: scoring,
    comparisonId: 'cmp-partial-note',
    cohortPeerCount: 0,
    cohortGovernorate: '',
    isRTL: false,
    feedbackSubmitted: false,
    onFeedbackSubmitted: jest.fn(),
    feedbackComparisonId: 'cmp-partial-note',
    sheetLeg: null,
    onPillPress: jest.fn(),
    onCloseSheet: jest.fn(),
    winnerRevealed: true,
    winnerScaleAnimStyle: { transform: [{ scale: 1 }] },
    onBack: jest.fn(),
    onShare: jest.fn(),
  };
}

describe('ResultsContent — F2 partial-result affordance (results.partial.note)', () => {
  it('renders the partial note when metadata.partial === true', () => {
    const { getByText, getByTestId } = render(
      <ResultsContent {...makeProps({ partial: true, code: 'TIMEOUT' })} />,
    );
    expect(getByText(PARTIAL_NOTE_KEY)).toBeTruthy();
    expect(getByTestId('results-content-partial-note')).toBeTruthy();
  });

  it('does NOT render the partial note when metadata.partial is false', () => {
    const { queryByText, queryByTestId } = render(
      <ResultsContent {...makeProps({ partial: false })} />,
    );
    expect(queryByText(PARTIAL_NOTE_KEY)).toBeNull();
    expect(queryByTestId('results-content-partial-note')).toBeNull();
  });

  it('does NOT render the partial note when metadata.partial is absent', () => {
    const { queryByText, queryByTestId } = render(
      <ResultsContent {...makeProps({ query: 'x', region: 'bahrain' })} />,
    );
    expect(queryByText(PARTIAL_NOTE_KEY)).toBeNull();
    expect(queryByTestId('results-content-partial-note')).toBeNull();
  });

  it('does NOT render the partial note when there is no metadata at all', () => {
    const { queryByText, queryByTestId } = render(
      <ResultsContent {...makeProps(undefined)} />,
    );
    expect(queryByText(PARTIAL_NOTE_KEY)).toBeNull();
    expect(queryByTestId('results-content-partial-note')).toBeNull();
  });
});
