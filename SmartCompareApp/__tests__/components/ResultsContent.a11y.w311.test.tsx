/**
 * W3-11bcd — MB-I18N-RTL-09 (b): the Results header's screen-reader labels
 * go through the catalog.
 *
 * Measured at base b63a8368: `ResultsContent.tsx:208`
 * `accessibilityLabel="Back"` and `:224` `accessibilityLabel="Share"` —
 * VoiceOver/TalkBack read English to an Arabic user. The fix uses
 * `t('results.a11y.back')` / `t('results.a11y.share')` (new keys, both
 * catalogs). Under the echo-`t` mock a translated label renders as its key.
 *
 * Harness = __tests__/components/ResultsContent.render.test.tsx.
 */

import React from 'react';
import { render } from '@testing-library/react-native';

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

jest.mock('../../src/components/results/TopMatchBadge', () => ({
  TopMatchBadge: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-top-match-badge'} />;
  },
}));
jest.mock('../../src/components/results/DimensionBars', () => ({
  DimensionBars: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-dim-bars'} />;
  },
}));
jest.mock('../../src/components/results/FactualVerdict', () => ({
  FactualVerdict: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-factual-verdict'} />;
  },
}));
jest.mock('../../src/components/results/ConfidencePills', () => ({
  ConfidencePills: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-confidence-pills'} />;
  },
}));
jest.mock('../../src/components/results/ConfidenceDetailsSheet', () => ({
  ConfidenceDetailsSheet: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-confidence-sheet'} />;
  },
}));
jest.mock('../../src/components/results/PersonalizationChip', () => ({
  PersonalizationChip: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-personalization-chip'} />;
  },
}));
jest.mock('../../src/components/hero/RevealBurst', () => ({
  RevealBurst: () => {
    const { View } = require('react-native');
    return <View testID="mock-reveal-burst" />;
  },
}));
jest.mock('../../src/components/CohortBadge', () => ({
  CohortBadge: () => null,
}));
jest.mock('../../src/components/FeedbackCard', () => ({
  __esModule: true,
  default: () => {
    const { View } = require('react-native');
    return <View testID="mock-feedback-card" />;
  },
}));
jest.mock('../../src/components/results/ResultsAccordion', () => ({
  ResultsAccordion: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-accordion'} />;
  },
}));
jest.mock('../../src/services/sourceMethod', () => ({
  anyEstimated: jest.fn(() => false),
  isConvertedUsd: jest.fn((p: any) => p?.source_method === 'converted_usd'),
}));

import { ResultsContent } from '../../src/components/results/ResultsContent';

const mockProducts: any = [
  {
    name: 'iPhone 15',
    brand: 'Apple',
    price: { amount: 329, currency: 'BHD', retailer: 'Sharaf DG' },
    pros: ['Faster CPU'],
    cons: ['Higher price'],
  },
  {
    name: 'Galaxy S24',
    brand: 'Samsung',
    price: { amount: 299, currency: 'BHD', retailer: 'Sharaf DG' },
    pros: ['Better camera'],
    cons: ['Slower updates'],
  },
];

const baseProps: any = {
  result: {
    overview: {
      winner: { product_index: 1, name: 'Galaxy S24', reason: 'r', key_tradeoff: 'k' },
      products: mockProducts,
    },
    comparison: {},
    recommendation: 'Galaxy S24 wins',
    metadata: { query: 'iphone-15-vs-galaxy-s24', elapsed_seconds: 14 },
  },
  products: mockProducts,
  winnerIndex: 1 as 0 | 1,
  scoring_v2: {
    overall_score: { product_a: 72, product_b: 81 },
    dimensions: [{ dim: 'camera', winner_index: 1, leftPct: 38, rightPct: 62 }],
    confidence_legs: { price: 'high', reviews: 'medium', specs: 'high' },
    factual_verdict: { line1: 'l1', line2: 'l2' },
    personalization: { applied_shifts: [] },
    comparison_quality: 'normal',
    confidence_details: {},
  },
  comparisonId: 'cmp-123',
  cohortPeerCount: 0,
  cohortGovernorate: null,
  isRTL: false,
  feedbackSubmitted: false,
  onFeedbackSubmitted: jest.fn(),
  feedbackComparisonId: 'cmp-123',
  sheetLeg: null,
  onPillPress: jest.fn(),
  onCloseSheet: jest.fn(),
  winnerRevealed: true,
  winnerScaleAnimStyle: { transform: [{ scale: 1 }] },
  onBack: jest.fn(),
  onShare: jest.fn(),
};

describe('W3-11 RTL-09 (b) — Results header a11y labels are catalog keys', () => {
  it('the back button label is t("results.a11y.back"), not the English literal', () => {
    const { getByLabelText, queryByLabelText } = render(<ResultsContent {...baseProps} />);
    expect(getByLabelText('results.a11y.back')).toBeTruthy();
    expect(queryByLabelText('Back')).toBeNull();
  });

  it('the share button label is t("results.a11y.share"), not the English literal', () => {
    const { getByLabelText, queryByLabelText } = render(<ResultsContent {...baseProps} />);
    expect(getByLabelText('results.a11y.share')).toBeTruthy();
    expect(queryByLabelText('Share')).toBeNull();
  });
});
