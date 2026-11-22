/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * INC-C1b RED -- B-b client part: a dimension the server did not crown is
 * never painted or listed as a win (INC_C1B_UNIT_SPEC_V2.md section 5.3 and
 * 10.3: rows B1-B5, pins P-B1, P-B2, P-B3; ruling RU-2).
 *
 * The contract this file fixes for GREEN:
 *  - DimensionBars: an explicit `winner: null` paints NO side (no accent on
 *    either fill; the value / price hero delta in text.primary). The bar
 *    PROPORTIONS STAY AS DRAWN (left / right = the scores): no forced equal
 *    halves. `winner` 0 or 1 keeps today's paint; a dim without the key
 *    (rows saved before F2.4) keeps today's score rule, ties going to the
 *    overall winner.
 *  - RunnerUpWinsCard / runnerUpWinningDims: a dim with `winner: null` is not
 *    a runner-up row; with `winner` 0 or 1 it is listed only when it equals
 *    the runner-up; without the key, today's `score[runnerUp] > score[winner]`.
 *
 * Data: the owner's phone test of 22 Nov 2026, "Imagination men" against
 * "Creed Aventus" (spec section 5.1: the scores measured on the screens;
 * Projection, Versatility and Presentation one-sided with the 50 sentinel and
 * `winner: null`; Character and Longevity `winner: 0`; overall winner Creed
 * Aventus, index 1).
 *
 * Harness: DimensionBars and RunnerUpWinsCard real; ResultsContent with the
 * INC-C1a sizeLabel harness minus its DimensionBars mock (child components
 * mocked by their existing paths); colors from src/theme. F1: existing
 * exports only (runnerUpWinningDims), every base failure is an expect
 * assertion, synthetic values apart from the case's names and scores.
 */

import React from 'react';
import { fireEvent, render } from '@testing-library/react-native';

import { DimensionBars } from '../../src/components/results/DimensionBars';
import {
  RunnerUpWinsCard,
  runnerUpWinningDims,
} from '../../src/components/results/RunnerUpWinsCard';
import { ResultsContent } from '../../src/components/results/ResultsContent';
import { colors } from '../../src/theme';

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
    i18n: { language: 'en' },
  }),
}));

jest.mock('../../src/components/results/TopMatchBadge', () => ({
  TopMatchBadge: ({ testID }: any) => {
    const { View } = require('react-native');
    return <View testID={testID ?? 'mock-top-match-badge'} />;
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
jest.mock('../../src/components/FeedbackCard', () => ({
  __esModule: true,
  default: () => {
    const { View } = require('react-native');
    return <View testID="mock-feedback-card" />;
  },
}));
jest.mock('../../src/components/results/ResultsAccordion', () => ({
  ResultsAccordion: (props: any) => {
    const { View } = require('react-native');
    return <View testID={props.testID ?? 'mock-accordion'} />;
  },
}));

// ------------------------------------------------------------------ data --

type Rendered = ReturnType<typeof render>;

/** One scoring_v2 dimension; `winner` undefined leaves the key out (pre-F2.4 rows). */
function dim(
  key: string,
  label: string,
  a: number,
  b: number,
  delta: string,
  winner?: 0 | 1 | null,
  extra: Record<string, unknown> = {},
): any {
  return {
    key,
    label,
    score_a: a,
    score_b: b,
    delta_text: delta,
    confidence: 'medium',
    ...(winner === undefined ? {} : { winner }),
    ...extra,
  };
}

const placeholder = (key: string, label: string) =>
  dim(key, label, 75, 75, `Limited ${key} data`, null, { caption_key: 'limited_data', confidence: 'low' });

// The case, spec section 5.1 (A = Imagination men, B = Creed Aventus).
const CHARACTER = dim('character', 'Character', 72.9, 57.2, 'More distinctive', 0);
const LONGEVITY = dim('longevity', 'Longevity', 72.9, 69.5, '8h vs 8h', 0);
const PROJECTION = dim('projection', 'Projection', 50, 88, 'Heavy vs Heavy projection', null);
const VERSATILITY = dim('versatility', 'Versatility', 50, 60, 'More versatile', null);
const PRESENTATION = dim('presentation', 'Presentation', 50, 100, 'Better presented', null);
const CASE_DIMS = [
  placeholder('price', 'Price'),
  placeholder('reviews', 'Reviews'),
  placeholder('value', 'Value'),
  CHARACTER,
  LONGEVITY,
  PROJECTION,
  VERSATILITY,
  PRESENTATION,
];

const CASE_PRODUCTS: any[] = [
  {
    name: 'Imagination men',
    brand: '',
    category: 'fragrances',
    price: { amount: null, currency: 'BHD', unavailable: true },
    pros: [],
    cons: [],
  },
  {
    name: 'Creed Aventus',
    brand: 'Creed',
    category: 'fragrances',
    price: { amount: 166.73, currency: 'BHD', retailer: 'store-a.example.com', source_method: 'page_scrape' },
    pros: [],
    cons: [],
  },
];

function caseProps(): any {
  return {
    result: {
      overview: {
        winner: { product_index: 1, name: 'Creed Aventus', reason: 'Fits the brief.' },
        products: CASE_PRODUCTS,
      },
      comparison: {},
      recommendation: 'Fits the brief.',
      metadata: { query: 'Imagination men vs Creed Aventus' },
    },
    products: CASE_PRODUCTS,
    winnerIndex: 1 as 0 | 1,
    scoring_v2: { dimensions: CASE_DIMS },
    comparisonId: 'cmp-c1b',
    isRTL: false,
    feedbackSubmitted: false,
    onFeedbackSubmitted: jest.fn(),
    feedbackComparisonId: 'cmp-c1b',
    sheetLeg: null,
    onPillPress: jest.fn(),
    onCloseSheet: jest.fn(),
    winnerRevealed: true,
    winnerScaleAnimStyle: { transform: [{ scale: 1 }] },
    onBack: jest.fn(),
    onShare: jest.fn(),
  };
}

// ------------------------------------------------------------------ reads --

const flat = (style: unknown): Record<string, any> => {
  const arr = Array.isArray(style) ? style : [style];
  return Object.assign({}, ...arr.filter(Boolean));
};
const share = (v: unknown) => Math.round(parseFloat(String(v)) * 10) / 10;
/** One bar: whether each fill carries the accent, and the share each draws (one decimal). */
const bar = (r: Rendered, rowId: string) => {
  const a = r.queryByTestId(`${rowId}-fill-a`);
  const b = r.queryByTestId(`${rowId}-fill-b`);
  if (!a || !b) return null;
  const fa = flat(a.props.style);
  const fb = flat(b.props.style);
  return {
    aAccent: fa.backgroundColor === colors.accent,
    bAccent: fb.backgroundColor === colors.accent,
    aShare: share(fa.flexBasis),
    bShare: share(fb.flexBasis),
  };
};
const has = (r: Rendered, id: string) => r.queryByTestId(id) !== null;
const keys = (dims: any[]) => dims.map((d: any) => d.key);

// ------------------------------------------------------------------ rows --

describe('INC-C1b B-b client rows (fail at base)', () => {
  it('B1 the runner-up list follows the server winner: null is never a row; 0 / 1 only when it is the runner-up', () => {
    const dims = [
      dim('longevity', 'Longevity', 71.5, 70.0, '8h vs 8h', null),
      dim('character', 'Character', 72.9, 57.2, 'More distinctive', 0),
    ];
    const r = render(
      <RunnerUpWinsCard products={CASE_PRODUCTS} winnerIndex={1} dimensions={dims} keyTradeoff={null} />,
    );
    // Winner A overall, runner-up B: a dim the server gave to A is not B's row,
    // a dim the server gave to B is, whatever the raw scores say.
    const givenToA = [dim('value', 'Value', 70, 80, 'Better value', 0)];
    const givenToB = [dim('value', 'Value', 80, 70, 'Better value', 1)];
    expect({
      list: keys(runnerUpWinningDims(dims, 1)),
      longevityRow: has(r, 'runner-up-wins-dim-longevity'),
      characterRow: has(r, 'runner-up-wins-dim-character'),
      givenToA: keys(runnerUpWinningDims(givenToA, 0)),
      givenToB: keys(runnerUpWinningDims(givenToB, 0)),
    }).toEqual({
      list: ['character'],
      longevityRow: false,
      characterRow: true,
      givenToA: [],
      givenToB: ['value'],
    });
  });

  it('B2 projection 50 vs 88 with winner null: no accent on either fill, the shares stay 36.2 / 63.8', () => {
    const r = render(<DimensionBars dimensions={[PROJECTION]} winnerIndex={1} testID="bars" />);
    expect(bar(r, 'bars-row-projection')).toEqual({
      aAccent: false,
      bAccent: false,
      aShare: 36.2,
      bShare: 63.8,
    });
  });

  it('B3 a tie (71.2 vs 71.2) with winner null is not painted on the overall winner side', () => {
    const r = render(
      <DimensionBars
        dimensions={[dim('longevity', 'Longevity', 71.2, 71.2, '8h vs 8h', null)]}
        winnerIndex={1}
        testID="bars"
      />,
    );
    expect(bar(r, 'bars-row-longevity')).toEqual({
      aAccent: false,
      bAccent: false,
      aShare: 50,
      bShare: 50,
    });
  });

  it('B4 the case on the Results screen: Projection, Versatility and Presentation carry no accent and keep their shares', () => {
    const r = render(<ResultsContent {...caseProps()} />);
    // Five renderable dims (price and value drop on the pended price, the
    // placeholders drop): the fifth sits behind the expand row.
    fireEvent.press(r.getByTestId('results-v2-bars-expand-row'));
    expect({
      projection: bar(r, 'results-v2-bars-row-projection'),
      versatility: bar(r, 'results-v2-bars-row-versatility'),
      presentation: bar(r, 'results-v2-bars-row-presentation'),
    }).toEqual({
      projection: { aAccent: false, bAccent: false, aShare: 36.2, bShare: 63.8 },
      versatility: { aAccent: false, bAccent: false, aShare: 45.5, bShare: 54.5 },
      presentation: { aAccent: false, bAccent: false, aShare: 33.3, bShare: 66.7 },
    });
  });

  it('B5 value 82 vs 70 with winner null: the hero delta is text.primary and neither fill is the accent', () => {
    const r = render(
      <DimensionBars
        dimensions={[dim('value', 'Value', 82, 70, 'BHD 2 less', null)]}
        winnerIndex={0}
        testID="bars"
      />,
    );
    const hero = r.queryByTestId('bars-row-value-delta-hero');
    expect({
      heroColor: hero ? flat(hero.props.style).color : null,
      bar: bar(r, 'bars-row-value'),
    }).toEqual({
      heroColor: colors.text.primary,
      bar: { aAccent: false, bAccent: false, aShare: 53.9, bShare: 46.1 },
    });
  });
});

describe('INC-C1b B-b client pins (pass at base)', () => {
  it('P-B1 an explicit winner keeps the paint and the shares; the case longevity (winner 0) still paints A and is still a runner-up row', () => {
    const r = render(
      <DimensionBars dimensions={[CHARACTER, LONGEVITY]} winnerIndex={1} testID="bars" />,
    );
    expect({
      character: bar(r, 'bars-row-character'),
      longevity: bar(r, 'bars-row-longevity'),
      runnerUp: keys(runnerUpWinningDims([LONGEVITY], 1)),
    }).toEqual({
      character: { aAccent: true, bAccent: false, aShare: 56.0, bShare: 44.0 },
      longevity: { aAccent: true, bAccent: false, aShare: 51.2, bShare: 48.8 },
      runnerUp: ['longevity'],
    });
  });

  it('P-B2 no winner key (rows saved before F2.4): the score rule, ties to the overall winner; the runner-up list is today\'s', () => {
    const dims = [dim('battery', 'Battery', 80, 70, 'Lasts longer'), dim('display', 'Display', 75, 75, 'Same panel')];
    const r1 = render(<DimensionBars dimensions={dims} winnerIndex={1} testID="w1" />);
    const r0 = render(<DimensionBars dimensions={dims} winnerIndex={0} testID="w0" />);
    const leads = [
      dim('price', 'Price', 75, 75, 'Price data unavailable', undefined, { caption_key: 'limited_data' }),
      dim('comfort', 'Comfort', 60, 82, 'More cushioned ride'),
      dim('value', 'Value', 70, 88, 'Better value'),
    ];
    expect({
      battery1: bar(r1, 'w1-row-battery'),
      display1: bar(r1, 'w1-row-display'),
      display0: bar(r0, 'w0-row-display'),
      list: keys(runnerUpWinningDims(leads, 0)),
    }).toEqual({
      battery1: { aAccent: true, bAccent: false, aShare: 53.3, bShare: 46.7 },
      display1: { aAccent: false, bAccent: true, aShare: 50, bShare: 50 },
      display0: { aAccent: true, bAccent: false, aShare: 50, bShare: 50 },
      list: ['comfort', 'value'],
    });
  });

  it('P-B3 winner null keeps the proportional shares (no forced equal halves)', () => {
    const r = render(
      <DimensionBars dimensions={[PROJECTION, VERSATILITY, PRESENTATION]} winnerIndex={1} testID="bars" />,
    );
    const shares = (id: string) => {
      const b = bar(r, id);
      return b ? [b.aShare, b.bShare] : null;
    };
    expect({
      projection: shares('bars-row-projection'),
      versatility: shares('bars-row-versatility'),
      presentation: shares('bars-row-presentation'),
    }).toEqual({
      projection: [36.2, 63.8],
      versatility: [45.5, 54.5],
      presentation: [33.3, 66.7],
    });
  });
});
