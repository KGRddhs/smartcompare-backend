/**
 * LifestylePicker — Bundle E F-S2.X3 regression suite.
 *
 * Pins the OptionRow icon-circle pattern + multi-select toggle
 * semantics after the X3 rewrite swapped the prior chip-flex-grid
 * layout for the W2 rhythm. No onboarding counterpart for lifestyle,
 * so the picker stands alone visually.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import LifestylePicker from '../../src/components/LifestylePicker';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('LifestylePicker (S2.X3 OptionRow rewrite)', () => {
  it('renders 11 lifestyle tag OptionRow icon-circles with lucide glyphs', () => {
    const { getAllByTestId } = render(
      <LifestylePicker value={[]} onChange={jest.fn()} />
    );
    // 11 canonical lifestyle tags × 1 ReactNode lucide glyph each.
    expect(getAllByTestId('option-row-icon-node').length).toBe(11);
  });

  it('adds a tag on press when absent', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(
      <LifestylePicker value={[]} onChange={onChange} />
    );
    fireEvent.press(getByTestId('lifestyle-creative'));
    expect(onChange).toHaveBeenCalledWith(['creative']);
  });

  it('removes a tag on press when present (multi-select toggle)', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(
      <LifestylePicker
        value={['fitness', 'minimalist']}
        onChange={onChange}
      />
    );
    fireEvent.press(getByTestId('lifestyle-fitness'));
    expect(onChange).toHaveBeenCalledWith(['minimalist']);
  });

  it('mirrors accessibilityState.selected for active tags', () => {
    const { getByTestId } = render(
      <LifestylePicker value={['outdoors']} onChange={jest.fn()} />
    );
    expect(
      getByTestId('lifestyle-outdoors').props.accessibilityState?.selected
    ).toBe(true);
    expect(
      getByTestId('lifestyle-fitness').props.accessibilityState?.selected
    ).toBe(false);
  });
});
