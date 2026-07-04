/**
 * PrioritiesPicker — Bundle E F-S2.X3 regression suite.
 *
 * Pins the OptionRow icon-circle pattern after the X3 rewrite swapped
 * the prior chip-flex-grid layout for the W2 onboarding rhythm. The
 * existing EditPreferencesFlow.test.tsx mocks this component wholesale,
 * so it can't catch a missing lucide glyph or a regression of the
 * silent MAX_SELECTIONS=3 cap.
 *
 * Mirrors the Step08Priorities.test.tsx contract conceptually but is
 * scoped to the standalone picker.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import PrioritiesPicker from '../../src/components/PrioritiesPicker';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('PrioritiesPicker (S2.X3 OptionRow rewrite)', () => {
  it('renders 8 priority OptionRow icon-circles with lucide ReactNode glyphs', () => {
    const { getAllByTestId } = render(
      <PrioritiesPicker value={[]} onChange={jest.fn()} />
    );
    // OptionRow exposes testID="option-row-icon-node" for the
    // ReactNode-icon render path. One node per priority → 8 total.
    expect(getAllByTestId('option-row-icon-node').length).toBe(8);
  });

  it('fires onChange when a priority is toggled', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(
      <PrioritiesPicker value={[]} onChange={onChange} />
    );
    fireEvent.press(getByTestId('priority-quality'));
    expect(onChange).toHaveBeenCalledWith(['quality']);
  });

  it('mirrors accessibilityState.selected for active rows', () => {
    const { getByTestId } = render(
      <PrioritiesPicker value={['eco_friendly']} onChange={jest.fn()} />
    );
    expect(
      getByTestId('priority-eco_friendly').props.accessibilityState?.selected
    ).toBe(true);
    expect(
      getByTestId('priority-price').props.accessibilityState?.selected
    ).toBe(false);
  });

  it('silently caps at MAX_SELECTIONS=3 (no scary copy on overflow)', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(
      <PrioritiesPicker
        value={['price', 'quality', 'durability']}
        onChange={onChange}
      />
    );
    // 4th selection attempt — onChange MUST NOT fire (silent cap per
    // Build Principle #4: engaging never scary).
    fireEvent.press(getByTestId('priority-latest_features'));
    expect(onChange).not.toHaveBeenCalled();
  });

  it('renders cohort-seeded priorities as selected canonical rows (device bug 2026-07-04)', () => {
    // A demographics-seeded user's priorities are stored as cohort-derived
    // enums (best_price / quality_reliability). Before the fix these were
    // INVISIBLE in the picker yet still consumed the 3-cap, so no priority
    // could be chosen. They must now render as selected canonical rows.
    const { getByTestId } = render(
      <PrioritiesPicker
        value={['best_price', 'quality_reliability']}
        onChange={jest.fn()}
      />
    );
    expect(
      getByTestId('priority-price').props.accessibilityState?.selected
    ).toBe(true);
    expect(
      getByTestId('priority-quality').props.accessibilityState?.selected
    ).toBe(true);
  });

  it('still allows adding a visible priority when cohort-seeded (cap not silently full)', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(
      <PrioritiesPicker
        value={['best_price', 'quality_reliability']}
        onChange={onChange}
      />
    );
    // 2 cohort priorities map to [price, quality]; a 3rd visible pick works.
    fireEvent.press(getByTestId('priority-durability'));
    expect(onChange).toHaveBeenCalledWith(['price', 'quality', 'durability']);
  });
});
