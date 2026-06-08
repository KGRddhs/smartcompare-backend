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

describe('L3.4 — per-retailer review quote block (Screen 2)', () => {
  it('renders all 3 retailer quotes per product when present', () => {
    const { getByTestId, getByText } = render(
      <ResultsAccordion {...makeProps()} />
    );
    const { fireEvent } = require('@testing-library/react-native');
    fireEvent.press(getByTestId('results-accordion-toggle-reviews'));

    // First product (iPhone) retailer block carries 3 quotes from fixture.
    expect(getByTestId('accordion-reviews-quote-0-0')).toBeTruthy();
    expect(getByTestId('accordion-reviews-quote-0-1')).toBeTruthy();
    expect(getByTestId('accordion-reviews-quote-0-2')).toBeTruthy();
    // Surfaces retailer name + the unique quote text inside the iPhone block.
    const quote0 = getByTestId('accordion-reviews-quote-0-0');
    const quote1 = getByTestId('accordion-reviews-quote-0-1');
    const allTextIn = (node: any): string => {
      if (!node) return '';
      if (typeof node === 'string') return node;
      if (Array.isArray(node)) return node.map(allTextIn).join(' ');
      if (node.props?.children !== undefined) return allTextIn(node.props.children);
      return '';
    };
    expect(allTextIn(quote0).toLowerCase()).toContain('amazon');
    expect(allTextIn(quote1).toLowerCase()).toContain(
      'camera in low light is the best'
    );
  });

  it('gracefully omits the block when retailer_quotes is absent', () => {
    const noQuotesProducts = (fixture as any).reviews.products.map((p: any) => ({
      ...p,
      retailer_quotes: undefined,
    }));
    const { queryByTestId, getByTestId } = render(
      <ResultsAccordion
        {...makeProps({ reviewProducts: noQuotesProducts })}
      />
    );
    const { fireEvent } = require('@testing-library/react-native');
    fireEvent.press(getByTestId('results-accordion-toggle-reviews'));
    expect(queryByTestId('accordion-reviews-quote-0-0')).toBeNull();
  });
});
