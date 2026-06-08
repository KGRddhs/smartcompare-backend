/**
 * Idle-time per-category DimensionBars test — WIP branch
 * `wip/A-L3-percategory-mobile-fixtures-idle-time`.
 *
 * Per the design system spec (CATEGORY_DIMENSIONS in
 * app/services/scoring_service.py), each category surfaces a different
 * label set. Verifies that DimensionBars renders THE CORRECT category-
 * specific labels from each fixture's scoring_v2.dimensions[*] AND that
 * the emerald bar paint lands on the side declared by dim.winner.
 *
 * Generic labels (Price/Reviews/Value) are universal core dims so they
 * appear in every fixture's first three rows; category-specific dims
 * (Camera, Battery, Character, Longevity, etc.) follow as additional
 * rows. The hero card caps at 4 visible dims by default (HERO_CAP), so
 * the visible label set per category is {Price, Reviews, Value, +1}
 * unless the user taps "See full breakdown".
 *
 * Coverage:
 *  - Label correctness for every fixture's first 4 dims (hero-visible).
 *  - Expand-row exposes the remaining dims so all 6 labels surface.
 *  - dim.winner override flows through to BarSide fillColor.
 */

import React from 'react';
import { fireEvent, render } from '@testing-library/react-native';

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

jest.mock('expo-haptics', () => ({
  selectionAsync: jest.fn(),
  impactAsync: jest.fn(),
  ImpactFeedbackStyle: { Light: 'Light', Medium: 'Medium' },
}));

import { DimensionBars } from '../src/components/results/DimensionBars';
import { colors } from '../src/theme';

function flattenStyle(style: any) {
  const arr = Array.isArray(style) ? style : [style];
  return Object.assign({}, ...arr.filter(Boolean));
}

const FIXTURES: Array<{ name: string; fixture: any; expected: string[] }> = [
  {
    name: 'electronics',
    fixture: require('./fixtures/v2_response_electronics.json'),
    // Electronics fixture has only 4 dims — no expand row.
    expected: ['Camera', 'Battery', 'Performance', 'Value'],
  },
  {
    name: 'grocery',
    fixture: require('./fixtures/v2_response_grocery.json'),
    expected: ['Price', 'Reviews', 'Value', 'Nutrition', 'Ingredients', 'Taste'],
  },
  {
    name: 'supplements',
    fixture: require('./fixtures/v2_response_supplements.json'),
    expected: ['Price', 'Reviews', 'Value', 'Efficacy', 'Safety', 'Trust'],
  },
  {
    name: 'makeup',
    fixture: require('./fixtures/v2_response_makeup.json'),
    expected: ['Price', 'Reviews', 'Value', 'Shade range', 'Longevity', 'Finish'],
  },
  {
    name: 'skincare',
    fixture: require('./fixtures/v2_response_skincare.json'),
    expected: ['Price', 'Reviews', 'Value', 'Active ingredients', 'Evidence', 'Skin compatibility'],
  },
  {
    name: 'haircare',
    fixture: require('./fixtures/v2_response_haircare.json'),
    expected: ['Price', 'Reviews', 'Value', 'Hair match', 'Results', 'Ingredients'],
  },
  {
    name: 'fragrances',
    fixture: require('./fixtures/v2_response_fragrances.json'),
    expected: ['Price', 'Reviews', 'Value', 'Character', 'Longevity', 'Projection'],
  },
  {
    name: 'fashion',
    fixture: require('./fixtures/v2_response_fashion.json'),
    expected: ['Price', 'Reviews', 'Value', 'Craftsmanship', 'Durability', 'Heritage'],
  },
  {
    name: 'other',
    fixture: require('./fixtures/v2_response_other.json'),
    expected: ['Price', 'Reviews', 'Value', 'Function', 'Build', 'Reliability'],
  },
];

describe.each(FIXTURES)(
  'DimensionBars per-category — $name',
  ({ name, fixture, expected }) => {
    const dimensions = fixture.scoring_v2.dimensions;
    const winnerIndex = (fixture.winner_index ?? fixture.overview.winner.product_index) as 0 | 1;

    it('renders the first 4 hero-visible dim labels exactly', () => {
      const { getByText } = render(
        <DimensionBars dimensions={dimensions} winnerIndex={winnerIndex} testID="bars" />
      );
      for (const label of expected.slice(0, 4)) {
        expect(getByText(label)).toBeTruthy();
      }
    });

    it('expand row appears when dimensions.length > HERO_CAP (4)', () => {
      const { queryByTestId } = render(
        <DimensionBars dimensions={dimensions} winnerIndex={winnerIndex} testID="bars" />
      );
      const expandRow = queryByTestId('bars-expand-row');
      if (dimensions.length > 4) {
        expect(expandRow).toBeTruthy();
      } else {
        expect(expandRow).toBeNull();
      }
    });

    it('expand row toggle surfaces the remaining (hidden) dim labels', () => {
      if (dimensions.length <= 4) return; // no-op for electronics (4 dims)

      const { getByText, getByTestId, queryByText } = render(
        <DimensionBars dimensions={dimensions} winnerIndex={winnerIndex} testID="bars" />
      );

      // The 5th+ labels are hidden by default.
      const hiddenLabels = expected.slice(4);
      for (const lbl of hiddenLabels) {
        expect(queryByText(lbl)).toBeNull();
      }

      fireEvent.press(getByTestId('bars-expand-row'));

      // After expand, all labels surface.
      for (const lbl of hiddenLabels) {
        expect(getByText(lbl)).toBeTruthy();
      }
    });

    it('emerald bar paint follows dim.winner override on each row', () => {
      const { getByTestId } = render(
        <DimensionBars dimensions={dimensions} winnerIndex={winnerIndex} testID="bars" />
      );

      const visibleDims = dimensions.slice(0, 4);
      for (const dim of visibleDims) {
        if (dim.winner !== 0 && dim.winner !== 1) continue;
        const fillA = getByTestId(`bars-row-${dim.key}-fill-a`);
        const fillB = getByTestId(`bars-row-${dim.key}-fill-b`);
        const accentSide = dim.winner === 0 ? fillA : fillB;
        const otherSide = dim.winner === 0 ? fillB : fillA;
        expect(flattenStyle(accentSide.props.style).backgroundColor).toBe(colors.accent);
        expect(flattenStyle(otherSide.props.style).backgroundColor).not.toBe(colors.accent);
      }
    });

    it('no generic Performance/Value label is used when category is NOT electronics', () => {
      if (name === 'electronics') return; // electronics legitimately has "Performance"
      const { queryByText } = render(
        <DimensionBars dimensions={dimensions} winnerIndex={winnerIndex} testID="bars" />
      );
      // "Performance" is electronics-only; every other category must surface
      // its own dim label set (Character/Longevity/Efficacy/etc.) not the
      // generic catch-all. The plan pre-pin asserts this.
      expect(queryByText('Performance')).toBeNull();
    });
  }
);
