/**
 * Bundle E S3 hotfix — ResultsContent REWRITE order pin.
 *
 * Source of truth:
 *   docs/claude-design-handoff/ui_kits/mobile/ResultsScreen.jsx (lines 286-407)
 *
 * Canonical body element order per the JSX top-down (lines 314-405) —
 *   1. Header (back / TopMatchBadge / share)
 *   2. Hero pair (winner+runner cards with absolute "vs" pill divider)
 *   3. "Why this fits you" verdict (whyWePicked eyebrow + verdict body
 *      + optional runner-up caption + PersonalizationChip subtitle)
 *   4. scoring_v2 hero block (HeroRings or em-dash + DimensionBars +
 *      ConfidenceDetailsSheet) — JSX positions DimensionBars BEFORE
 *      ConfidencePills, so the whole rings/bars block lives here.
 *   5. Confidence pills ("What we know" eyebrow)
 *   6. Cohort badge
 *   7. "Dig deeper" accordion (Reviews + Pros & Cons + Specs)
 *   8. Feedback prompt
 *
 * Prior structure interleaved verdict → confidence → cohort → scoring_v2
 * hero → accordion which did NOT match JSX (JSX has DimensionBars BEFORE
 * confidence pills, and cohort AFTER confidence pills, not before
 * scoring_v2 hero). This file pins the JSX-aligned order so any future
 * reshuffle has to update this list deliberately.
 *
 * The order assertion uses DFS traversal of the rendered tree finding
 * the FIRST occurrence of each pinned testID, then checking the index
 * sequence is strictly monotonic.
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

// Render real children so we test ResultsContent composition, but use a
// tiny shim where heavy children would slow Jest down. Leaves the
// testIDs intact since we only need ORDER not deep content.
jest.mock('../../src/components/results/TopMatchBadge', () => {
  const React = require('react');
  const { View } = require('react-native');
  return {
    TopMatchBadge: (p: any) =>
      React.createElement(View, { testID: p.testID ?? 'mock-top-match' }),
  };
});
jest.mock('../../src/components/results/HeroRings', () => {
  const React = require('react');
  const { View } = require('react-native');
  return {
    HeroRings: (p: any) =>
      React.createElement(View, { testID: p.testID ?? 'results-v2-hero-rings' }),
  };
});
jest.mock('../../src/components/results/DimensionBars', () => {
  const React = require('react');
  const { View } = require('react-native');
  return {
    DimensionBars: (p: any) =>
      React.createElement(View, { testID: p.testID ?? 'results-v2-bars' }),
  };
});
jest.mock('../../src/components/results/FactualVerdict', () => {
  const React = require('react');
  const { View } = require('react-native');
  return {
    FactualVerdict: (p: any) =>
      React.createElement(View, {
        testID: p.testID ?? 'results-content-factual-verdict',
      }),
  };
});
jest.mock('../../src/components/results/ConfidencePills', () => {
  const React = require('react');
  const { View } = require('react-native');
  return {
    ConfidencePills: (p: any) =>
      React.createElement(View, {
        testID: p.testID ?? 'results-content-confidence-pills',
      }),
  };
});
jest.mock('../../src/components/results/ConfidenceDetailsSheet', () => ({
  ConfidenceDetailsSheet: () => null,
}));
jest.mock('../../src/components/results/PersonalizationChip', () => {
  const React = require('react');
  const { View } = require('react-native');
  return {
    PersonalizationChip: (p: any) =>
      React.createElement(View, {
        testID: p.testID ?? 'results-v2-personalization-chip',
      }),
  };
});
jest.mock('../../src/components/hero/RevealBurst', () => ({ RevealBurst: () => null }));
jest.mock('../../src/components/CohortBadge', () => {
  const React = require('react');
  const { View } = require('react-native');
  return {
    CohortBadge: () =>
      React.createElement(View, { testID: 'mock-cohort-badge' }),
  };
});
jest.mock('../../src/components/FeedbackCard', () => {
  const React = require('react');
  const { View } = require('react-native');
  return {
    __esModule: true,
    default: () => React.createElement(View, { testID: 'mock-feedback' }),
  };
});
jest.mock('../../src/components/results/ResultsAccordion', () => {
  const React = require('react');
  const { View } = require('react-native');
  return {
    ResultsAccordion: (p: any) =>
      React.createElement(View, {
        testID: p.testID ?? 'results-content-accordion-inner',
      }),
  };
});
jest.mock('../../src/services/sourceMethod', () => ({
  anyEstimated: jest.fn(() => false),
  isConvertedUsd: jest.fn((p: any) => p?.source_method === 'converted_usd'),
}));

import { ResultsContent } from '../../src/components/results/ResultsContent';

const products: any = [
  {
    brand: 'Apple',
    name: 'iPhone 15',
    price: { amount: 329, currency: 'BHD' },
    image_url: 'https://example.com/iphone.jpg',
  },
  {
    brand: 'Samsung',
    name: 'Galaxy S24',
    price: { amount: 299, currency: 'BHD' },
    image_url: 'https://example.com/galaxy.jpg',
  },
];

const scoring_v2: any = {
  comparison_quality: 'normal',
  overall_score: { product_a: 80, product_b: 92 },
  dimensions: [
    { dim: 'camera', a: 80, b: 92 },
    { dim: 'battery', a: 70, b: 90 },
    { dim: 'price', a: 60, b: 95 },
  ],
  factual_verdict: { line1: 'Galaxy wins on camera.', line2: '' },
  confidence_legs: { price: 'high', reviews: 'medium', specs: 'high' },
  personalization: { applied_shifts: [] },
};

const baseProps: any = {
  result: {
    overview: {
      winner: {
        product_index: 1,
        name: 'Galaxy S24',
        reason: 'Tuned to your priorities.',
        key_tradeoff: 'iPhone keeps the faster CPU.',
      },
      products,
    },
    specs: { products },
    reviews: { products },
  } as any,
  products,
  winnerIndex: 1 as 0 | 1,
  scoring_v2,
  comparisonId: 'cmp-1',
  cohortPeerCount: 2000,
  cohortGovernorate: 'Capital',
  isRTL: false,
  feedbackSubmitted: false,
  onFeedbackSubmitted: () => {},
  feedbackComparisonId: 'cmp-1',
  sheetLeg: null,
  onPillPress: () => {},
  onCloseSheet: () => {},
  winnerRevealed: true,
  winnerScaleAnimStyle: { transform: [{ scale: 1 }] },
  onBack: () => {},
  onShare: () => {},
};

/**
 * Pre-order DFS over the rendered JSON tree. Returns the index at which
 * the first match for each pinned testID is encountered.
 */
function buildTestIdOrder(json: any, pins: string[]): Record<string, number> {
  const order: Record<string, number> = {};
  let counter = 0;
  const visit = (node: any) => {
    if (!node) return;
    counter++;
    const tid = node?.props?.testID;
    if (typeof tid === 'string' && pins.includes(tid) && !(tid in order)) {
      order[tid] = counter;
    }
    const children = Array.isArray(node.children) ? node.children : [];
    for (const c of children) visit(c);
  };
  visit(json);
  return order;
}

describe('ResultsContent — REWRITE element order per ResultsScreen.jsx', () => {
  it('renders all 8 anchor sections in the JSX top-down order', () => {
    const r = render(<ResultsContent {...baseProps} />);
    const json = r.toJSON();
    const pins = [
      'results-content-header',
      'results-content-hero-pair',
      'results-content-why',
      'results-scoring-v2',
      'results-content-confidence',
      'results-cohort-badge-slot',
      'results-content-accordion',
      'results-content-feedback',
    ];
    const order = buildTestIdOrder(json, pins);
    // Every pin found
    for (const p of pins) {
      expect(order[p]).toBeDefined();
    }
    // Strictly increasing
    const indices = pins.map((p) => order[p]);
    for (let i = 1; i < indices.length; i++) {
      expect(indices[i]).toBeGreaterThan(indices[i - 1]);
    }
  });

  it('places scoring_v2 hero BEFORE confidence pills (JSX 348-353 vs 356-365)', () => {
    const r = render(<ResultsContent {...baseProps} />);
    const order = buildTestIdOrder(r.toJSON(), [
      'results-scoring-v2',
      'results-content-confidence',
    ]);
    expect(order['results-scoring-v2']).toBeLessThan(
      order['results-content-confidence']
    );
  });

  it('places cohort badge AFTER confidence pills (JSX 367-377)', () => {
    const r = render(<ResultsContent {...baseProps} />);
    const order = buildTestIdOrder(r.toJSON(), [
      'results-content-confidence',
      'results-cohort-badge-slot',
    ]);
    expect(order['results-content-confidence']).toBeLessThan(
      order['results-cohort-badge-slot']
    );
  });

  it('header sits at the top — before the hero pair (JSX 297-311 vs 316)', () => {
    const r = render(<ResultsContent {...baseProps} />);
    const order = buildTestIdOrder(r.toJSON(), [
      'results-content-header',
      'results-content-hero-pair',
    ]);
    expect(order['results-content-header']).toBeLessThan(
      order['results-content-hero-pair']
    );
  });

  it('feedback prompt is last (JSX 384-404)', () => {
    const r = render(<ResultsContent {...baseProps} />);
    const order = buildTestIdOrder(r.toJSON(), [
      'results-content-accordion',
      'results-content-feedback',
    ]);
    expect(order['results-content-accordion']).toBeLessThan(
      order['results-content-feedback']
    );
  });

  it('the scoring_v2 slot contains the DimensionBars and NO rings card (Phase 2.1 prune)', () => {
    const r = render(<ResultsContent {...baseProps} />);
    const order = buildTestIdOrder(r.toJSON(), [
      'results-scoring-v2',
      'results-v2-bars',
    ]);
    // scoring_v2 wrapper comes first (parent encountered first in DFS)
    expect(order['results-scoring-v2']).toBeDefined();
    expect(order['results-scoring-v2']).toBeLessThan(order['results-v2-bars']);
    // Faithful-results Phase 2.1 — the HeroRings score-rings card is pruned;
    // it must NOT appear in the rendered tree.
    expect(r.queryByTestId('results-v2-hero-rings')).toBeNull();
  });

  it('PersonalizationChip sits under the "Why this fits you" block, before the scoring_v2 hero (Phase 4.4)', () => {
    // Phase 4.4 relocated the chip out of the scoring_v2 hero and under the
    // verdict headline (mockup subline). It must now appear AFTER the "why"
    // block opens and BEFORE the scoring_v2 hero.
    const r = render(<ResultsContent {...baseProps} />);
    const order = buildTestIdOrder(r.toJSON(), [
      'results-content-why',
      'results-v2-personalization-chip',
      'results-scoring-v2',
    ]);
    expect(order['results-content-why']).toBeLessThan(
      order['results-v2-personalization-chip']
    );
    expect(order['results-v2-personalization-chip']).toBeLessThan(
      order['results-scoring-v2']
    );
  });
});
