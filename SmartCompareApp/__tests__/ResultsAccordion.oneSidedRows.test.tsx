/**
 * Task E3 (frag-content-quality WS-E / P7 / FE-3) — no silent one-sided spec rows.
 *
 * Contract: in the "Dig deeper" Specs table, a row where EXACTLY ONE product
 * has a value and the other renders the em-dash "—" (missing) is DROPPED —
 * matching CategoryProfile's symmetric contract. We never show a silent
 * value·LABEL·"—" row.
 *
 *  - both-present spec row  → renders normally (kept).
 *  - one-present / one-"—"  → dropped (no row, no cells).
 *  - both-missing handling  → unchanged from before (structural-fallback path).
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

// Two products: a spec present on BOTH (longevity), a spec present on A only
// (sillage on product 0, missing/null on product 1 → would render as "—").
function makeProps() {
  const specsProducts = [
    {
      name: 'Oud Wood',
      specs: {
        longevity: '8 hours',
        sillage: 'Moderate', // present on A only
        scent_family: 'Woody',
      },
    },
    {
      name: 'Oud Voyager',
      specs: {
        longevity: '10 hours',
        // sillage intentionally absent → one-sided row
        scent_family: 'Woody Aromatic',
      },
    },
  ];
  return {
    products: specsProducts as any,
    specsProducts,
    winnerIndex: 0 as 0 | 1,
    testID: 'accordion',
  };
}

describe('ResultsAccordion — one-sided spec rows (Task E3)', () => {
  it('drops a row where exactly one product has a value and the other is "—"', () => {
    const { getByTestId, queryByTestId } = render(
      <ResultsAccordion {...makeProps()} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));

    // sillage is present only on product 0 → the whole row must be dropped.
    expect(queryByTestId('accordion-specs-row-sillage')).toBeNull();
    expect(queryByTestId('accordion-specs-cell-sillage-0')).toBeNull();
    expect(queryByTestId('accordion-specs-cell-sillage-1')).toBeNull();
  });

  it('keeps a row where BOTH products have a value', () => {
    const { getByTestId } = render(<ResultsAccordion {...makeProps()} />);
    fireEvent.press(getByTestId('results-specs-toggle'));

    // longevity is present on both → row renders with both real values.
    expect(getByTestId('accordion-specs-row-longevity')).toBeTruthy();
    expect(getByTestId('accordion-specs-cell-longevity-0').props.children).toBe(
      '8 hours'
    );
    expect(getByTestId('accordion-specs-cell-longevity-1').props.children).toBe(
      '10 hours'
    );

    // scent_family present on both → also kept.
    expect(getByTestId('accordion-specs-row-scent_family')).toBeTruthy();
  });
});
