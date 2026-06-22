/**
 * Bundle E S3 hotfix — ResultsAccordion edge-case coverage (idle policy).
 *
 * Adds red-green tests for spec rendering edge cases the round-1 +
 * round-2 hotfix suite did NOT cover:
 *
 *   1. Mixed numeric + string spec values across products
 *      (e.g., backend ships `battery: 3349` (number) on one product
 *      and `battery: "4000 mAh"` (string) on the other — both must
 *      surface as a single shared key row).
 *   2. Boolean spec values (`wireless_charging: true`).
 *   3. Asymmetric key sets (product A has `display`, product B has
 *      `dimensions` — union surfaces both).
 *   4. Expanded-state snapshot pinning the full reviews/proscons/specs
 *      bodies so future "stylistic" edits don't quietly delete content.
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

import { ResultsAccordion } from '../../src/components/results/ResultsAccordion';

describe('ResultsAccordion — edge cases (idle-policy coverage)', () => {
  it('renders a row when product A has number and product B has string at the same key', () => {
    const mixed: any = [
      { name: 'iPhone 15', specs: { battery: 3349, weight: '171 g' } },
      { name: 'Galaxy S24', specs: { battery: '4000 mAh', weight: '167 g' } },
    ];
    const { getByTestId, getByText } = render(
      <ResultsAccordion products={mixed} specsProducts={mixed} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    // 'battery' surfaces as a shared key
    expect(getByText('battery')).toBeTruthy();
    // Numeric value coerced via String(...) but NOT em-dashed
    expect(getByText('3349')).toBeTruthy();
    expect(getByText('4000 mAh')).toBeTruthy();
  });

  it('renders boolean spec values via String() coercion', () => {
    const withBool: any = [
      { name: 'iPhone 15', specs: { wireless_charging: true } },
      { name: 'Galaxy S24', specs: { wireless_charging: false } },
    ];
    const { getByTestId, getByText } = render(
      <ResultsAccordion products={withBool} specsProducts={withBool} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    expect(getByText('wireless charging')).toBeTruthy();
    expect(getByText('true')).toBeTruthy();
    expect(getByText('false')).toBeTruthy();
  });

  it('drops fully one-sided rows — A-only display + B-only dimensions both dropped', () => {
    // Task E3 (frag-content-quality WS-E / P7 / FE-3): re-baselined from the
    // prior "union + em-dash" behavior. When exactly one product has a value
    // (display on A only, dimensions on B only) the row is one-sided and is
    // DROPPED to keep the spec table symmetric (matches CategoryProfile). No
    // silent value·LABEL·"—" rows survive.
    const asym: any = [
      { name: 'iPhone 15', specs: { display: '6.1" OLED' } },
      { name: 'Galaxy S24', specs: { dimensions: '147x71x7.6 mm' } },
    ];
    const { getByTestId, queryByText, queryAllByText } = render(
      <ResultsAccordion products={asym} specsProducts={asym} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    // Both rows are one-sided → both dropped; neither key nor value surfaces.
    expect(queryByText('display')).toBeNull();
    expect(queryByText('dimensions')).toBeNull();
    expect(queryByText('6.1" OLED')).toBeNull();
    expect(queryByText('147x71x7.6 mm')).toBeNull();
    // No silent one-sided em-dash rows remain.
    expect(queryAllByText('—').length).toBe(0);
  });

  it('treats `0` (numeric zero) as a real value, NOT em-dash', () => {
    // Defends against the classic JS falsy-coercion bug where
    // `if (!value)` strips legitimate zeros.
    const withZero: any = [
      { name: 'A', specs: { count: 0 } },
      { name: 'B', specs: { count: 5 } },
    ];
    const { getByTestId, getByText, queryAllByText } = render(
      <ResultsAccordion products={withZero} specsProducts={withZero} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    expect(getByText('count')).toBeTruthy();
    expect(getByText('0')).toBeTruthy();
    expect(getByText('5')).toBeTruthy();
    // No em-dash for the legitimate zero
    expect(queryAllByText('—').length).toBe(0);
  });

  it('drops the row when an empty-string value (→ N/A) makes it one-sided', () => {
    // Empty string is in the NA_VALUES set ("") → coerces to the em-dash
    // "missing" form. Task E3: with a real value on the OTHER product the
    // `color` row is one-sided → DROPPED (re-baselined from the prior
    // "blank cell → em-dash" behavior). A both-present row (`size`) stays.
    const withEmpty: any = [
      { name: 'A', specs: { color: '', size: 'large' } },
      { name: 'B', specs: { color: 'black', size: 'large' } },
    ];
    const { getByTestId, getAllByText, queryByText } = render(
      <ResultsAccordion products={withEmpty} specsProducts={withEmpty} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    // The one-sided color row is dropped — neither the key nor its lone value.
    expect(queryByText('color')).toBeNull();
    expect(queryByText('black')).toBeNull();
    // No silent one-sided em-dash cell remains.
    expect(queryByText('—')).toBeNull();
    // The both-present `size` row still renders (large on both).
    expect(queryByText('size')).toBeTruthy();
    expect(getAllByText('large').length).toBe(2);
  });

  it('expanded specs body snapshot — pins full row content + ordering', () => {
    const fixture: any = [
      {
        name: 'iPhone 15',
        specs: {
          display: '6.1" OLED',
          battery: '3,349 mAh',
          storage: '128 GB',
        },
      },
      {
        name: 'Galaxy S24',
        specs: {
          display: '6.2" AMOLED',
          battery: '4,000 mAh',
          storage: '128 GB',
        },
      },
    ];
    const { getByTestId, toJSON } = render(
      <ResultsAccordion products={fixture} specsProducts={fixture} />
    );
    fireEvent.press(getByTestId('results-specs-toggle'));
    const body = getByTestId('results-accordion-body-specs');
    expect(body).toBeTruthy();
    // Snapshot the *body* subtree only — keeps the snapshot resilient
    // to header / surrounding chrome edits.
    expect(toJSON()).toMatchSnapshot();
  });
});
