/**
 * Lane A-L3 (Sprint A) — Tasks L3.2, L3.3, L3.4.
 *
 * ResultsAccordion v2 wiring contract:
 *   - L3.2: per-row emerald winner highlighting in specs table when L1
 *     supplies a `specsComparison` array carrying {field, p0_value, p1_value, winner}.
 *   - L3.3: winner-star (★) prefix on the winning product's name column
 *     in the pros/cons grid.
 *   - L3.4: per-retailer review quote block (3 quotes max — Amazon, Noon, X)
 *     under each product's review_summary when L1 supplies
 *     `reviewProducts[i].retailer_quotes`.
 *
 * Develops against fixture so it can close ahead of L1.
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import fixture from '../fixtures/v2_response_electronics.json';

// Consult the REAL en.json catalog so keys like
// `results.reviews.ratingWithCount` interpolate their actual template
// ("{{rating}} · {{count}} reviews") — this exercises the real i18n string,
// not a passthrough that would leave the bare key.
jest.mock('react-i18next', () => {
  const en = require('../../src/i18n/en.json') as Record<string, string>;
  return {
    useTranslation: () => ({
      t: (key: string, opts?: Record<string, unknown>) => {
        let str = en[key] ?? (opts?.defaultValue as string) ?? key;
        if (opts) {
          for (const [k, v] of Object.entries(opts)) {
            if (k === 'defaultValue') continue;
            str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
          }
        }
        return str;
      },
    }),
  };
});

import { ResultsAccordion } from '../../src/components/results/ResultsAccordion';
import { colors } from '../../src/theme';
import { TouchableOpacity } from 'react-native';

function flattenStyle(style: any) {
  const arr = Array.isArray(style) ? style : [style];
  return Object.assign({}, ...arr.filter(Boolean));
}

function makeProps(overrides: Record<string, any> = {}) {
  const result = fixture as any;
  return {
    products: result.overview.products,
    reviewProducts: result.reviews.products,
    specsProducts: result.specs.products,
    specsComparison: result.specs.specs_comparison,
    winnerIndex: 0 as 0 | 1,
    testID: 'accordion',
    ...overrides,
  };
}

function findRowByLabel(root: any, label: string): any | null {
  // RN test renderer JSON shape: each node has `type`, `props`, `children`.
  // Look for a Text child whose children contain the label, then return the
  // parent row.
  function walk(node: any, parent: any): any | null {
    if (!node) return null;
    if (typeof node === 'string') return null;
    if (node.children) {
      for (const c of node.children) {
        if (
          typeof c === 'object' &&
          c &&
          c.type === 'Text' &&
          Array.isArray(c.children) &&
          c.children.includes(label)
        ) {
          return parent || node;
        }
      }
      for (const c of node.children) {
        const found = walk(c, node);
        if (found) return found;
      }
    }
    return null;
  }
  return walk(root, null);
}

describe('L3.2 — specs table per-row emerald winner highlight', () => {
  it('paints the winning cell in emerald and the loser in default color', () => {
    const { getByTestId, UNSAFE_getByProps } = render(
      <ResultsAccordion {...makeProps()} />
    );
    // Open the specs accordion.
    const toggle = getByTestId('results-specs-toggle');
    // Simulate press.
    const { fireEvent } = require('@testing-library/react-native');
    fireEvent.press(toggle);

    // Each spec row gets `testID="accordion-specs-row-{field}"`. Cell at idx
    // 0 is the spec key (e.g. "display"); idx 1+2 are p0/p1 values.
    // The fixture says the display row has winner=1 (Galaxy S24 wins).
    const displayCellP0 = getByTestId('accordion-specs-cell-display-0');
    const displayCellP1 = getByTestId('accordion-specs-cell-display-1');
    expect(displayCellP0).toBeTruthy();
    expect(displayCellP1).toBeTruthy();
    expect(flattenStyle(displayCellP1.props.style).color).toBe(colors.accent);
    expect(flattenStyle(displayCellP0.props.style).color).not.toBe(colors.accent);

    // Processor row: winner=0 (iPhone A16 wins).
    const procP0 = getByTestId('accordion-specs-cell-processor-0');
    const procP1 = getByTestId('accordion-specs-cell-processor-1');
    expect(flattenStyle(procP0.props.style).color).toBe(colors.accent);
    expect(flattenStyle(procP1.props.style).color).not.toBe(colors.accent);
  });

  it('renders no emerald when specsComparison has winner === null (tie)', () => {
    const { getByTestId } = render(<ResultsAccordion {...makeProps()} />);
    const { fireEvent } = require('@testing-library/react-native');
    fireEvent.press(getByTestId('results-specs-toggle'));
    // storage row tie (both 128GB).
    const a = getByTestId('accordion-specs-cell-storage-0');
    const b = getByTestId('accordion-specs-cell-storage-1');
    expect(flattenStyle(a.props.style).color).not.toBe(colors.accent);
    expect(flattenStyle(b.props.style).color).not.toBe(colors.accent);
  });
});

describe('L3.3 — winner-star (★) on the winning product in pros/cons', () => {
  it('renders a star prefix on the winning product name only', () => {
    const { getByTestId } = render(<ResultsAccordion {...makeProps()} />);
    const { fireEvent } = require('@testing-library/react-native');
    fireEvent.press(getByTestId('results-accordion-toggle-proscons'));
    // Winner is index 0 (iPhone). Star testID on the winning col only.
    expect(getByTestId('accordion-proscons-winner-star-0')).toBeTruthy();
  });

  it('renders no star on the loser column', () => {
    const { queryByTestId } = render(<ResultsAccordion {...makeProps()} />);
    const { fireEvent } = require('@testing-library/react-native');
    fireEvent.press(queryByTestId('results-accordion-toggle-proscons')!);
    expect(queryByTestId('accordion-proscons-winner-star-1')).toBeNull();
  });
});

describe('Phase 5.2 — paraphrased praise review block (Contract 2)', () => {
  const allTextIn = (node: any): string => {
    if (!node) return '';
    if (typeof node === 'string') return node;
    if (Array.isArray(node)) return node.map(allTextIn).join(' ');
    if (node.props?.children !== undefined) return allTextIn(node.props.children);
    return '';
  };

  function withPraise() {
    return (fixture as any).reviews.products.map((p: any, i: number) => ({
      ...p,
      review_praise:
        i === 0
          ? 'Owners praise the bright display and dependable battery life.'
          : 'Reviewers highlight the standout camera and smooth performance.',
      rating_count: p.review_count,
    }));
  }

  it('renders one synthesized praise line per product (no verbatim quotes, no source pills)', () => {
    const { getByTestId, getByText } = render(
      <ResultsAccordion {...makeProps({ reviewProducts: withPraise() })} />
    );
    const { fireEvent } = require('@testing-library/react-native');
    fireEvent.press(getByTestId('results-accordion-toggle-reviews'));

    // Praise line testIDs (winner-first: winnerIndex 0 → product 0 first).
    expect(getByTestId('accordion-reviews-praise-0-text')).toBeTruthy();
    expect(getByTestId('accordion-reviews-praise-1-text')).toBeTruthy();
    expect(
      getByText('Owners praise the bright display and dependable battery life.')
    ).toBeTruthy();
    expect(
      getByText('Reviewers highlight the standout camera and smooth performance.')
    ).toBeTruthy();
  });

  it('NO LONGER renders the dormant retailer_quotes (Contract 2)', () => {
    // Fixture products carry retailer_quotes; the new surface must NOT render
    // them as per-source verbatim quote cards.
    const { queryByTestId, getByTestId } = render(
      <ResultsAccordion {...makeProps({ reviewProducts: withPraise() })} />
    );
    const { fireEvent } = require('@testing-library/react-native');
    fireEvent.press(getByTestId('results-accordion-toggle-reviews'));
    expect(queryByTestId('accordion-reviews-quote-0-0')).toBeNull();
    expect(queryByTestId('accordion-reviews-quote-0-1')).toBeNull();
    expect(queryByTestId('accordion-reviews-quote-1-0')).toBeNull();
  });

  it('does not surface any source-domain text in the praise block', () => {
    const withDomain = (fixture as any).reviews.products.map((p: any, i: number) => ({
      ...p,
      // praise is synthesized prose; even if a domain were present in raw data
      // it must not be rendered as a citation.
      review_praise:
        i === 0
          ? 'Owners consistently call out the long-lasting battery.'
          : 'Reviewers love the camera in everyday use.',
    }));
    const { getByTestId } = render(
      <ResultsAccordion {...makeProps({ reviewProducts: withDomain })} />
    );
    const { fireEvent } = require('@testing-library/react-native');
    fireEvent.press(getByTestId('results-accordion-toggle-reviews'));
    const block = getByTestId('accordion-reviews-praise-0');
    const text = allTextIn(block).toLowerCase();
    expect(text).not.toContain('amazon');
    expect(text).not.toContain('noon');
    expect(text).not.toContain('.com');
    // No bracketed citation markers.
    expect(text).not.toMatch(/\[\d+\]/);
  });

  it('renders real stars + rating·count when a genuine rating exists', () => {
    const { getByTestId, getByText } = render(
      <ResultsAccordion {...makeProps({ reviewProducts: withPraise() })} />
    );
    const { fireEvent } = require('@testing-library/react-native');
    fireEvent.press(getByTestId('results-accordion-toggle-reviews'));
    // iPhone rating 4.6 / 12,450 from fixture → "4.6 · 12,450 reviews".
    expect(getByText('4.6 · 12,450 reviews')).toBeTruthy();
  });

  it('skips a product with neither praise nor a rating', () => {
    const sparse = [
      {
        ...(fixture as any).reviews.products[0],
        review_praise: 'Owners praise the battery.',
      },
      {
        name: 'Galaxy S24',
        rating: null,
        review_count: null,
        retailer_quotes: undefined,
        review_praise: null,
      },
    ];
    // Also blank the ROOT product 1 — the component falls back to root
    // rating/praise (Contract 2 locates them there), so a true "no signal"
    // product must lack them in BOTH the review projection and the root.
    const rootProducts = [
      (fixture as any).overview.products[0],
      { name: 'Galaxy S24', rating: null, review_count: null, review_praise: null },
    ];
    const { getByTestId, queryByTestId } = render(
      <ResultsAccordion
        {...makeProps({ reviewProducts: sparse, products: rootProducts })}
      />
    );
    const { fireEvent } = require('@testing-library/react-native');
    fireEvent.press(getByTestId('results-accordion-toggle-reviews'));
    expect(getByTestId('accordion-reviews-praise-0')).toBeTruthy();
    expect(queryByTestId('accordion-reviews-praise-1')).toBeNull();
  });

  it('renders the calm empty line when no product has any review signal', () => {
    const empty = (fixture as any).reviews.products.map((p: any) => ({
      name: p.name,
      rating: null,
      review_count: null,
      review_praise: null,
      retailer_quotes: undefined,
    }));
    // Root products in the fixture DO carry ratings, so blank those too via
    // the products override to exercise the true-empty path.
    const emptyRoot = (fixture as any).overview.products.map((p: any) => ({
      name: p.name,
      rating: null,
      review_count: null,
      review_praise: null,
    }));
    const { getByText, getByTestId } = render(
      <ResultsAccordion
        {...makeProps({ reviewProducts: empty, products: emptyRoot })}
      />
    );
    const { fireEvent } = require('@testing-library/react-native');
    fireEvent.press(getByTestId('results-accordion-toggle-reviews'));
    expect(getByText('Reviews are still coming in.')).toBeTruthy();
  });
});
