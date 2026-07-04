/**
 * Frag-content-quality WS-A Task A6 — FE score-internals guard (defense-in-depth).
 *
 * The backend (WS-A: strip_score_internals at the response_builder chokepoint +
 * the deterministic-partial-verdict fix) is canonical and already scrubs raw
 * internal scores/point-margins out of every user-facing verdict surface. This
 * suite pins the FE backstop that fails a FUTURE regression loud-but-clean: if
 * a score-internal phrase ever reaches `overview.winner.reason` (verdictBody)
 * or `overview.winner.key_tradeoff` (the RunnerUpWinsCard prose), the FE drops
 * that line rather than render the leak.
 *
 * Confirmed live leak strings (fresh nocache 2026-06-21, catfix follow-up):
 *   "wins with a 10.7-point higher overall score", "Strong presentation score
 *   of 100", "Scores 87/100 overall", "leads on the overall score by 4 points".
 */

import React from 'react';
import { render } from '@testing-library/react-native';

import { SCORE_INTERNALS_RE } from '../src/components/results/_deltaText';

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
jest.mock('../src/components/hero/RevealBurst', () => ({ RevealBurst: () => null }));
jest.mock('../src/components/CohortBadge', () => ({ CohortBadge: () => null }));
jest.mock('../src/components/FeedbackCard', () => ({ __esModule: true, default: () => null }));
jest.mock('../src/components/results/ResultsAccordion', () => ({
  ResultsAccordion: () => null,
}));
jest.mock('../src/services/sourceMethod', () => ({ anyEstimated: jest.fn(() => false), isConvertedUsd: jest.fn((p: any) => p?.source_method === 'converted_usd') }));

import { ResultsContent } from '../src/components/results/ResultsContent';

const products: any = [
  { name: 'Oud Wood', brand: 'Tom Ford', price: { amount: 146.64, currency: 'BHD' } },
  { name: 'Oud Voyager', brand: 'Tom Ford', price: { amount: 120, currency: 'BHD' } },
];

// No scoring_v2.factual_verdict → ResultsContent falls back to rendering the
// raw `overview.winner.reason` (verdictBody) so we can test the guard on it.
const scoringNoFactual: any = {
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

function makeProps(overrides: any = {}): any {
  return {
    result: {
      overview: {
        winner: {
          product_index: 0,
          name: 'Oud Wood',
          reason: overrides.reason ?? 'Longer-lasting on skin with a warmer drydown.',
          key_tradeoff: overrides.keyTradeoff ?? 'Voyager is fresher for daytime wear.',
        },
        products,
      },
      recommendation: 'Oud Wood is the stronger overall pick',
    },
    products,
    winnerIndex: 0 as 0 | 1,
    scoring_v2: scoringNoFactual,
    comparisonId: 'cmp-score-guard',
    cohortPeerCount: 0,
    cohortGovernorate: '',
    isRTL: false,
    feedbackSubmitted: false,
    onFeedbackSubmitted: jest.fn(),
    feedbackComparisonId: 'cmp-score-guard',
    sheetLeg: null,
    onPillPress: jest.fn(),
    onCloseSheet: jest.fn(),
    winnerRevealed: true,
    winnerScaleAnimStyle: { transform: [{ scale: 1 }] },
    onBack: jest.fn(),
    onShare: jest.fn(),
  };
}

describe('SCORE_INTERNALS_RE — shared guard regex', () => {
  it('matches known score-internal leak phrases', () => {
    for (const leak of [
      'wins with a 10.7-point higher overall score',
      'leads on the overall score by 4 points',
      'Strong presentation score of 100',
      'Scores 87/100 overall',
    ]) {
      expect(SCORE_INTERNALS_RE.test(leak)).toBe(true);
    }
  });

  it('does NOT match clean qualitative prose', () => {
    for (const clean of [
      'Longer-lasting on skin with a warmer drydown.',
      'Voyager is fresher for daytime wear.',
      'Stronger projection and a richer base.',
    ]) {
      expect(SCORE_INTERNALS_RE.test(clean)).toBe(false);
    }
  });
});

describe('ResultsContent — A6 score-internals guard (defense-in-depth)', () => {
  it('does NOT render a verdictBody that leaks score internals', () => {
    const { queryByText } = render(
      <ResultsContent
        {...makeProps({ reason: 'wins with a 10.7-point higher overall score' })}
      />,
    );
    expect(queryByText('wins with a 10.7-point higher overall score')).toBeNull();
  });

  it('does NOT render a key_tradeoff prose that leaks score internals', () => {
    const { queryByText, queryByTestId } = render(
      <ResultsContent {...makeProps({ keyTradeoff: 'scores 87/100' })} />,
    );
    // The leaking prose is dropped (not rendered).
    expect(queryByText('scores 87/100')).toBeNull();
    // And the runner-up prose node is gone (prose was the only thing that
    // matched here; dims for this fixture are raw-shaped → no rows).
    expect(queryByTestId('results-content-runner-up-wins-prose')).toBeNull();
  });

  it('renders a clean qualitative verdictBody + key_tradeoff normally', () => {
    const { getByText } = render(<ResultsContent {...makeProps()} />);
    expect(getByText('Longer-lasting on skin with a warmer drydown.')).toBeTruthy();
    expect(getByText('Voyager is fresher for daytime wear.')).toBeTruthy();
  });
});
