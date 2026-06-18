/**
 * RunnerUpWinsCard — Task #24 tests.
 *
 * The richer structured "Where the runner-up wins" block: lists the dims the
 * runner-up actually leads (from scoring_v2.dimensions) + the key_tradeoff
 * prose. NO raw "+Npt" point math (qualitative delta_text OR the clean label).
 * Hides entirely when there is neither a winning dim nor a key_tradeoff.
 * Gray, symmetric, real dims only.
 */

import React from 'react';
import { render } from '@testing-library/react-native';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      (opts?.defaultValue as string) ?? key,
  }),
}));

import {
  RunnerUpWinsCard,
  runnerUpWinningDims,
} from '../../src/components/results/RunnerUpWinsCard';

const products: any = [
  { name: 'Black Orchid' },
  { name: 'Oud Wood' },
];

// Real-payload-shaped dims: winner (A, index 0) sweeps character+longevity;
// price/reviews/value are no-data placeholders (caption_key:'limited_data').
const SWEEP_DIMS: any = [
  { key: 'price', label: 'Price', score_a: 75, score_b: 75, delta_text: 'Price data unavailable', caption_key: 'limited_data' },
  { key: 'reviews', label: 'Reviews', score_a: 75, score_b: 75, delta_text: 'Limited review data', caption_key: 'limited_data' },
  { key: 'value', label: 'Value', score_a: 75, score_b: 75, delta_text: 'Limited value data', caption_key: 'limited_data' },
  { key: 'character', label: 'Character', score_a: 74.1, score_b: 55.9, delta_text: '+18pt distinctiveness' },
  { key: 'longevity', label: 'Longevity', score_a: 74.1, score_b: 55.9, delta_text: '+18pt longevity' },
];

// Dims where the RUNNER-UP (B, index 1) leads two real dims.
const RUNNER_LEADS_DIMS: any = [
  { key: 'price', label: 'Price', score_a: 75, score_b: 75, delta_text: 'Price data unavailable', caption_key: 'limited_data' },
  { key: 'comfort', label: 'Comfort', score_a: 60, score_b: 82, delta_text: 'More cushioned ride' },
  { key: 'value', label: 'Value', score_a: 70, score_b: 88, delta_text: '+18pt value' },
];

describe('runnerUpWinningDims helper', () => {
  it('returns dims where the runner-up score > winner score, excluding limited_data', () => {
    // winner = index 1 (B); runner-up = A. A leads where score_a > score_b.
    const dims = runnerUpWinningDims(SWEEP_DIMS, 1);
    // A (74.1) > B (55.9) on character + longevity; placeholders excluded.
    expect(dims.map((d) => d.key)).toEqual(['character', 'longevity']);
  });

  it('returns [] when the winner sweeps every real dim', () => {
    // winner = index 0 (A); A wins character+longevity → runner-up B leads none.
    expect(runnerUpWinningDims(SWEEP_DIMS, 0)).toEqual([]);
  });

  it('excludes dims missing a numeric score pair', () => {
    const dims = [
      { key: 'x', label: 'X', winner_index: 1 } as any, // no score_a/b
      { key: 'y', label: 'Y', score_a: 50, score_b: 70 } as any,
    ];
    expect(runnerUpWinningDims(dims, 0).map((d) => d.key)).toEqual(['y']);
  });

  it('tolerates undefined dimensions', () => {
    expect(runnerUpWinningDims(undefined, 0)).toEqual([]);
  });
});

describe('RunnerUpWinsCard render', () => {
  it('HIDES entirely when there is neither a winning dim nor a key_tradeoff', () => {
    // winner sweeps (index 0) → no runner-up dims; no prose.
    const { queryByTestId } = render(
      <RunnerUpWinsCard
        products={products}
        winnerIndex={0}
        dimensions={SWEEP_DIMS}
        keyTradeoff={null}
        testID="ruw"
      />,
    );
    expect(queryByTestId('ruw')).toBeNull();
  });

  it('SWEEP case — renders name + key_tradeoff prose only (no dim rows)', () => {
    const { getByTestId, getByText, queryByTestId } = render(
      <RunnerUpWinsCard
        products={products}
        winnerIndex={0}
        dimensions={SWEEP_DIMS}
        keyTradeoff="Oud Wood offers a sophisticated woody aroma."
        testID="ruw"
      />,
    );
    expect(getByTestId('ruw')).toBeTruthy();
    expect(getByText('Oud Wood')).toBeTruthy(); // runner-up = index 1
    expect(getByText('Oud Wood offers a sophisticated woody aroma.')).toBeTruthy();
    // No dim rows on a sweep.
    expect(queryByTestId('ruw-dims')).toBeNull();
  });

  it('renders a row per dim the runner-up leads', () => {
    // winner = index 0 → runner-up B leads comfort + value.
    const { getByTestId } = render(
      <RunnerUpWinsCard
        products={products}
        winnerIndex={0}
        dimensions={RUNNER_LEADS_DIMS}
        keyTradeoff={null}
        testID="ruw"
      />,
    );
    expect(getByTestId('ruw-dims')).toBeTruthy();
    expect(getByTestId('ruw-dim-comfort')).toBeTruthy();
    expect(getByTestId('ruw-dim-value')).toBeTruthy();
    // Placeholder price dim excluded.
    expect(() => getByTestId('ruw-dim-price')).toThrow();
  });

  it('uses qualitative delta_text but NEVER raw "+Npt" point math (falls back to label)', () => {
    const { getByText, queryByText, queryAllByText } = render(
      <RunnerUpWinsCard
        products={products}
        winnerIndex={0}
        dimensions={RUNNER_LEADS_DIMS}
        keyTradeoff={null}
        testID="ruw"
      />,
    );
    // comfort delta_text "More cushioned ride" is qualitative → shown verbatim.
    expect(getByText('More cushioned ride')).toBeTruthy();
    // value delta_text "+18pt value" is point-math → falls back to the LABEL "Value".
    expect(getByText('Value')).toBeTruthy();
    expect(queryByText('+18pt value')).toBeNull();
    // No "pt" point-math anywhere in the rendered card (queryAll → [] when none).
    expect(queryAllByText(/\d+\s*pt/i)).toHaveLength(0);
  });

  it('is symmetric — works whichever side wins (winnerIndex 1 → runner-up A)', () => {
    const dims: any = [
      { key: 'speed', label: 'Speed', score_a: 90, score_b: 60, delta_text: 'Snappier' },
    ];
    const { getByText } = render(
      <RunnerUpWinsCard
        products={products}
        winnerIndex={1}
        dimensions={dims}
        keyTradeoff={null}
        testID="ruw"
      />,
    );
    // winner = B (index 1) → runner-up = A "Black Orchid"; A leads speed.
    expect(getByText('Black Orchid')).toBeTruthy();
    expect(getByText('Snappier')).toBeTruthy();
  });

  it('renders the eyebrow when visible', () => {
    const { getByText } = render(
      <RunnerUpWinsCard
        products={products}
        winnerIndex={0}
        dimensions={RUNNER_LEADS_DIMS}
        keyTradeoff={null}
        testID="ruw"
      />,
    );
    // i18n stub returns the key.
    expect(getByText('results.runnerUpWins')).toBeTruthy();
  });

  it('hides when key_tradeoff is only whitespace and no winning dims', () => {
    const { queryByTestId } = render(
      <RunnerUpWinsCard
        products={products}
        winnerIndex={0}
        dimensions={SWEEP_DIMS}
        keyTradeoff="   "
        testID="ruw"
      />,
    );
    expect(queryByTestId('ruw')).toBeNull();
  });
});
