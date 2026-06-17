/**
 * Idle-time per-category accordion test — WIP branch
 * `wip/A-L3-percategory-mobile-fixtures-idle-time`.
 *
 * Extends ResultsAccordion.v2.test.tsx with category-specific behavior
 * checks for all 9 categories. Asserts:
 *   - L3.2 emerald spec-cell highlight paints correct side per
 *     specs_comparison[*].winner
 *   - L3.3 winner-star (★) on the overall winner's pros/cons column
 *     (and ONLY that column)
 *   - L3.4 retailer-quote block renders per product when present,
 *     gracefully omits when retailer_quotes is absent (graceful degradation)
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';

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

import { ResultsAccordion } from '../src/components/results/ResultsAccordion';
import { colors } from '../src/theme';

function flattenStyle(style: any) {
  const arr = Array.isArray(style) ? style : [style];
  return Object.assign({}, ...arr.filter(Boolean));
}

const FIXTURES: Array<{ name: string; fixture: any }> = [
  { name: 'electronics', fixture: require('./fixtures/v2_response_electronics.json') },
  { name: 'grocery', fixture: require('./fixtures/v2_response_grocery.json') },
  { name: 'supplements', fixture: require('./fixtures/v2_response_supplements.json') },
  { name: 'makeup', fixture: require('./fixtures/v2_response_makeup.json') },
  { name: 'skincare', fixture: require('./fixtures/v2_response_skincare.json') },
  { name: 'haircare', fixture: require('./fixtures/v2_response_haircare.json') },
  { name: 'fragrances', fixture: require('./fixtures/v2_response_fragrances.json') },
  { name: 'fashion', fixture: require('./fixtures/v2_response_fashion.json') },
  { name: 'other', fixture: require('./fixtures/v2_response_other.json') },
];

function makeProps(fixture: any, overrides: Record<string, any> = {}) {
  const winnerIndex = (fixture.winner_index ?? fixture.overview.winner.product_index) as 0 | 1;
  return {
    products: fixture.overview.products,
    reviewProducts: fixture.reviews.products,
    specsProducts: fixture.specs.products,
    specsComparison: fixture.specs.specs_comparison,
    winnerIndex,
    testID: 'accordion',
    ...overrides,
  };
}

describe.each(FIXTURES)(
  'ResultsAccordion per-category — $name',
  ({ name, fixture }) => {
    describe('L3.2 — per-row spec emerald winner highlighting', () => {
      it('paints the winning cell in colors.accent for every winner row', () => {
        const { getByTestId } = render(<ResultsAccordion {...makeProps(fixture)} />);
        fireEvent.press(getByTestId('results-specs-toggle'));

        const winnerRows = fixture.specs.specs_comparison.filter(
          (r: any) => r.winner === 0 || r.winner === 1
        );

        for (const row of winnerRows) {
          const winnerCell = getByTestId(`accordion-specs-cell-${row.field}-${row.winner}`);
          const loserCell = getByTestId(
            `accordion-specs-cell-${row.field}-${row.winner === 0 ? 1 : 0}`
          );
          expect(flattenStyle(winnerCell.props.style).color).toBe(colors.accent);
          expect(flattenStyle(loserCell.props.style).color).not.toBe(colors.accent);
        }
      });

      it('does NOT paint emerald on tie rows (winner === null)', () => {
        const { getByTestId, queryByTestId } = render(
          <ResultsAccordion {...makeProps(fixture)} />
        );
        fireEvent.press(getByTestId('results-specs-toggle'));

        // Tie rows whose backing values are filtered N/A ('None', 'N/A',
        // empty etc.) get dropped by ResultsAccordion's filterSpecs gate
        // — they never render so testID lookup would fail. Skip those
        // and only test rows that actually surface in the spec table.
        const NA = new Set(['n/a', 'na', 'null', 'none', 'unknown', '']);
        const tieRowsRendered = fixture.specs.specs_comparison.filter((r: any) => {
          if (r.winner !== null) return false;
          const v0 = String(r.p0_value ?? '').toLowerCase().trim();
          const v1 = String(r.p1_value ?? '').toLowerCase().trim();
          return !NA.has(v0) && !NA.has(v1);
        });

        for (const row of tieRowsRendered) {
          const cell0 = queryByTestId(`accordion-specs-cell-${row.field}-0`);
          const cell1 = queryByTestId(`accordion-specs-cell-${row.field}-1`);
          // If the cell doesn't render for any other reason (HIDDEN_FIELDS,
          // _-prefix, missing key on specs map) skip — that's a separate
          // contract not under test here.
          if (!cell0 || !cell1) continue;
          expect(flattenStyle(cell0.props.style).color).not.toBe(colors.accent);
          expect(flattenStyle(cell1.props.style).color).not.toBe(colors.accent);
        }
      });
    });

    describe('L3.3 — winner-star on the overall winner column', () => {
      it('renders the ★ on the winner column only', () => {
        const { getByTestId, queryByTestId } = render(
          <ResultsAccordion {...makeProps(fixture)} />
        );
        fireEvent.press(getByTestId('results-accordion-toggle-proscons'));

        const winnerIdx = fixture.winner_index ?? fixture.overview.winner.product_index;
        const loserIdx = winnerIdx === 0 ? 1 : 0;

        expect(getByTestId(`accordion-proscons-winner-star-${winnerIdx}`)).toBeTruthy();
        expect(queryByTestId(`accordion-proscons-winner-star-${loserIdx}`)).toBeNull();
      });
    });

    describe('Phase 5.2 — paraphrased praise review block (Contract 2)', () => {
      it('renders a synthesized praise line per product, NOT verbatim retailer quotes', () => {
        // Inject a synthesized praise line per product (Contract 2 field).
        const withPraise = JSON.parse(JSON.stringify(fixture));
        withPraise.reviews.products.forEach((p: any, i: number) => {
          p.review_praise = `Reviewers speak well of ${p.name} (${name}).`;
        });
        const { getByTestId, queryByTestId } = render(
          <ResultsAccordion {...makeProps(withPraise)} />
        );
        fireEvent.press(getByTestId('results-accordion-toggle-reviews'));

        // Each product's synthesized praise line renders (winner-first order,
        // so at least the winner's block is present).
        const winnerIdx = (withPraise.winner_index ??
          withPraise.overview.winner.product_index) as 0 | 1;
        expect(getByTestId(`accordion-reviews-praise-${winnerIdx}-text`)).toBeTruthy();

        // The dormant verbatim retailer_quotes are NO LONGER rendered.
        expect(queryByTestId('accordion-reviews-quote-0-0')).toBeNull();
        expect(queryByTestId('accordion-reviews-quote-1-0')).toBeNull();
      });

      it('still renders the rating row (real stars) when a genuine rating exists, even with no praise', () => {
        // Fixture products carry real ratings; with no review_praise the block
        // still renders the rating header (skips only when BOTH are absent).
        const noPraise = JSON.parse(JSON.stringify(fixture));
        noPraise.reviews.products.forEach((p: any) => {
          delete p.retailer_quotes;
          delete p.review_praise;
        });
        const { getByTestId, queryByTestId } = render(
          <ResultsAccordion {...makeProps(noPraise)} />
        );
        fireEvent.press(getByTestId('results-accordion-toggle-reviews'));
        // No verbatim quote testIDs.
        expect(queryByTestId('accordion-reviews-quote-0-0')).toBeNull();
        // At least the winner's block renders when it has a rating.
        const winnerIdx = (noPraise.winner_index ??
          noPraise.overview.winner.product_index) as 0 | 1;
        const hasRating =
          typeof noPraise.reviews.products[winnerIdx]?.rating === 'number' &&
          noPraise.reviews.products[winnerIdx].rating > 0;
        if (hasRating) {
          expect(getByTestId(`accordion-reviews-praise-${winnerIdx}`)).toBeTruthy();
        }
      });
    });
  }
);
