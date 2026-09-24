/**
 * W3-11bcd — MB-I18N-RTL-06: the two ResultsAccordion review-count sites
 * follow the APP digit policy, not the DEVICE locale.
 *
 * Measured at base b63a8368: `ResultsAccordion.tsx` rendered
 * `totalReviews.toLocaleString()` (the "Reviews" row sub) and
 * `ratingCount.toLocaleString()` (the per-product rating line) — digits and
 * separators from whatever locale the phone runs. The fix routes both
 * through `formatNumber` (ASCII, `,` grouping — APP_DIGIT_SYSTEM 'latn').
 *
 * Why the existing accordion suites cannot see a revert: jest runs on node's
 * en-US ICU, where `(21660).toLocaleString()` is already "21,660", so the
 * device-locale path and the policy path print the same thing. This suite
 * makes the device ARABIC for the duration of each render — every bare
 * `Number.prototype.toLocaleString()` call answers as `ar-SA` would on a
 * phone ("٢١٬٦٦٠") — so a site that consults the device locale shows
 * Arabic-Indic digits and a site that follows the policy does not.
 *
 * Harness = __tests__/components/ResultsAccordion.v2.test.tsx (real en.json
 * `t`, the v2 electronics fixture: review_count 12,450 + 9,210 = 21,660).
 */
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import fixture from '../fixtures/v2_response_electronics.json';

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

const ARABIC_INDIC = /[٠-٩۰-۹]/;
const realToLocaleString = Number.prototype.toLocaleString;

function makeProps() {
  const result = fixture as any;
  return {
    products: result.overview.products,
    reviewProducts: result.reviews.products.map((p: any, i: number) => ({
      ...p,
      review_praise: i === 0 ? 'Owners praise the battery.' : 'Reviewers love the camera.',
      rating_count: p.review_count,
    })),
    specsProducts: result.specs.products,
    specsComparison: result.specs.specs_comparison,
    winnerIndex: 0 as 0 | 1,
    testID: 'accordion',
  };
}

function allText(node: any): string {
  if (node == null) return '';
  if (typeof node === 'string') return node;
  if (Array.isArray(node)) return node.map(allText).join(' ');
  return allText(node.children);
}

beforeEach(() => {
  // An Arabic-locale phone: a bare toLocaleString() answers as ar-SA.
  jest
    .spyOn(Number.prototype, 'toLocaleString')
    .mockImplementation(function (this: number) {
      return realToLocaleString.call(this, 'ar-SA');
    });
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('W3-11 RTL-06 — ResultsAccordion review counts ignore the device locale', () => {
  it('control: the simulated device really is Arabic', () => {
    expect((21660).toLocaleString()).toMatch(ARABIC_INDIC);
  });

  it('the Reviews row sub shows the total as "21,660" in ASCII digits', () => {
    const { toJSON } = render(<ResultsAccordion {...makeProps()} />);
    const text = allText(toJSON());
    expect(text).toContain('21,660');
    expect(text).not.toMatch(ARABIC_INDIC);
  });

  it('the per-product rating line shows "12,450" in ASCII digits (a STRING count, spec R10)', () => {
    const { getByTestId, getByText, toJSON } = render(<ResultsAccordion {...makeProps()} />);
    fireEvent.press(getByTestId('results-accordion-toggle-reviews'));
    expect(getByText('4.6 · 12,450 reviews')).toBeTruthy();
    expect(allText(toJSON())).not.toMatch(ARABIC_INDIC);
  });
});
