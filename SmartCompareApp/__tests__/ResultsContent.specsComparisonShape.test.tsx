/**
 * Lane A-L3 fix-commit — `fix(L3): specs_comparison defensive shape`.
 *
 * L2 cross-QA verdict (2026-06-08) flagged a cross-lane contract
 * mismatch: L1's response_builder emits `specs.specs_comparison` as a
 * DICT with keys `{rows, product_0_advantages, product_1_advantages,
 * similar}`, but ResultsAccordion expected a flat ARRAY of rows. The
 * earlier per-row emerald-winner tests passed against the array-shape
 * fixture but would have rendered zero emerald cells in production.
 *
 * Fix: ResultsContent.tsx now reads BOTH shapes defensively. This test
 * parametrizes the per-row winner emerald assertion over the array-
 * shape fixture (`v2_response_electronics.json`) AND the live-shape
 * fixture (`v2_response_electronics_live_shape.json`) so future schema
 * drift in either direction trips a loud failure.
 */

import React from 'react';
import { fireEvent, render } from '@testing-library/react-native';

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

// Heavy children stubbed — they don't gate the emerald-cell render path
// (which lives entirely inside ResultsAccordion).
jest.mock('../src/components/results/TopMatchBadge', () => ({ TopMatchBadge: () => null }));
jest.mock('../src/components/results/HeroRings', () => ({ HeroRings: () => null }));
jest.mock('../src/components/results/PersonalizationChip', () => ({ PersonalizationChip: () => null }));
jest.mock('../src/components/hero/RevealBurst', () => ({ RevealBurst: () => null }));
jest.mock('../src/components/CohortBadge', () => ({ CohortBadge: () => null }));
jest.mock('../src/components/FeedbackCard', () => ({ __esModule: true, default: () => null }));
jest.mock('../src/services/sourceMethod', () => ({ anyEstimated: jest.fn(() => false), isConvertedUsd: jest.fn((p: any) => p?.source_method === 'converted_usd') }));

import { ResultsContent } from '../src/components/results/ResultsContent';
import { colors } from '../src/theme';

function flattenStyle(style: any) {
  const arr = Array.isArray(style) ? style : [style];
  return Object.assign({}, ...arr.filter(Boolean));
}

const FIXTURES: Array<{ shape: string; fixture: any }> = [
  {
    shape: 'array (legacy fixture / pre-L1.9)',
    fixture: require('./fixtures/v2_response_electronics.json'),
  },
  {
    shape: 'dict-with-rows (L1 production emit)',
    fixture: require('./fixtures/v2_response_electronics_live_shape.json'),
  },
];

function makeProps(fixture: any, overrides: Record<string, any> = {}) {
  const products = fixture.overview.products;
  return {
    result: fixture,
    products,
    winnerIndex: 0 as 0 | 1,
    scoring_v2: fixture.scoring_v2,
    comparisonId: 'cmp_spec_shape',
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

/**
 * Pulls the rows[] from either shape so the test can iterate them
 * without caring which shape the fixture uses. This mirrors the
 * production defensive-read in ResultsContent.tsx.
 */
function rowsOf(fixture: any): Array<any> {
  const raw = fixture.specs.specs_comparison;
  if (Array.isArray(raw)) return raw;
  if (Array.isArray(raw?.rows)) return raw.rows;
  return [];
}

describe.each(FIXTURES)(
  'ResultsContent specs_comparison shape — $shape',
  ({ shape, fixture }) => {
    // Ensure the fixture is actually in the shape this row tests.
    it('fixture is in the expected shape (sanity pin)', () => {
      const raw = fixture.specs.specs_comparison;
      if (shape.startsWith('array')) {
        expect(Array.isArray(raw)).toBe(true);
      } else {
        expect(Array.isArray(raw)).toBe(false);
        expect(Array.isArray(raw.rows)).toBe(true);
      }
    });

    it('renders accordion specs body when the user taps the specs toggle', () => {
      const { getByTestId } = render(<ResultsContent {...makeProps(fixture)} />);
      const toggle = getByTestId('results-specs-toggle');
      fireEvent.press(toggle);
      expect(getByTestId('results-accordion-body-specs')).toBeTruthy();
    });

    it('paints emerald on the WINNER cell of every winner row', () => {
      const { getByTestId } = render(<ResultsContent {...makeProps(fixture)} />);
      fireEvent.press(getByTestId('results-specs-toggle'));

      const rows = rowsOf(fixture);
      const winnerRows = rows.filter((r) => r.winner === 0 || r.winner === 1);
      expect(winnerRows.length).toBeGreaterThan(0); // sanity: fixture has rows

      for (const row of winnerRows) {
        const winnerCell = getByTestId(
          `results-content-accordion-inner-specs-cell-${row.field}-${row.winner}`
        );
        const loserCell = getByTestId(
          `results-content-accordion-inner-specs-cell-${row.field}-${
            row.winner === 0 ? 1 : 0
          }`
        );
        expect(flattenStyle(winnerCell.props.style).color).toBe(colors.accent);
        expect(flattenStyle(loserCell.props.style).color).not.toBe(colors.accent);
      }
    });

    it('does NOT paint emerald on tie rows (winner === null)', () => {
      const { getByTestId, queryByTestId } = render(
        <ResultsContent {...makeProps(fixture)} />
      );
      fireEvent.press(getByTestId('results-specs-toggle'));

      const NA = new Set(['n/a', 'na', 'null', 'none', 'unknown', '']);
      const tieRows = rowsOf(fixture)
        .filter((r) => r.winner === null)
        .filter((r) => {
          const v0 = String(r.p0_value ?? '').toLowerCase().trim();
          const v1 = String(r.p1_value ?? '').toLowerCase().trim();
          return !NA.has(v0) && !NA.has(v1);
        });

      for (const row of tieRows) {
        const cell0 = queryByTestId(
          `results-content-accordion-inner-specs-cell-${row.field}-0`
        );
        const cell1 = queryByTestId(
          `results-content-accordion-inner-specs-cell-${row.field}-1`
        );
        if (!cell0 || !cell1) continue;
        expect(flattenStyle(cell0.props.style).color).not.toBe(colors.accent);
        expect(flattenStyle(cell1.props.style).color).not.toBe(colors.accent);
      }
    });
  }
);

describe('ResultsContent specs_comparison shape — edge cases', () => {
  it('renders gracefully when specs_comparison is undefined (legacy data)', () => {
    const legacy = JSON.parse(JSON.stringify(require('./fixtures/v2_response_electronics.json')));
    delete legacy.specs.specs_comparison;
    const { getByTestId, queryByTestId } = render(
      <ResultsContent {...makeProps(legacy)} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    expect(getByTestId('results-accordion-body-specs')).toBeTruthy();
    // No row should paint emerald since winnerByField map is empty.
    const cell = queryByTestId('results-content-accordion-inner-specs-cell-display-0');
    if (cell) {
      expect(flattenStyle(cell.props.style).color).not.toBe(colors.accent);
    }
  });

  it('renders gracefully when specs_comparison is a dict with no rows key', () => {
    // Hypothetical schema variant — partial dict with only the legacy
    // advantages arrays, no `rows` key. Defensive read returns undefined.
    const partial = JSON.parse(JSON.stringify(require('./fixtures/v2_response_electronics.json')));
    partial.specs.specs_comparison = {
      product_0_advantages: ['A1'],
      product_1_advantages: ['B1'],
    };
    const { getByTestId } = render(<ResultsContent {...makeProps(partial)} />);
    fireEvent.press(getByTestId('results-specs-toggle'));
    expect(getByTestId('results-accordion-body-specs')).toBeTruthy();
  });
});
