/**
 * Step08Priorities tests — Phase 2 Task 15.
 *
 * 8 priority chips, 1-3 selectable. Personalization signal that feeds
 * scoring ±30% cap. See design spec § 2 row 8.
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { Step08Priorities } from '../../../src/screens/onboarding/Step08Priorities';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe('Step08Priorities', () => {
  it('renders all 8 priority chips', () => {
    const { getByTestId } = render(
      <Step08Priorities value={[]} onChange={jest.fn()} />
    );
    expect(getByTestId('priority-price')).toBeTruthy();
    expect(getByTestId('priority-quality')).toBeTruthy();
    expect(getByTestId('priority-brand_reputation')).toBeTruthy();
    expect(getByTestId('priority-durability')).toBeTruthy();
    expect(getByTestId('priority-latest_features')).toBeTruthy();
    expect(getByTestId('priority-ease_of_use')).toBeTruthy();
    expect(getByTestId('priority-eco_friendly')).toBeTruthy();
    expect(getByTestId('priority-health_safety')).toBeTruthy();
  });

  it('toggles selection on chip tap', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(
      <Step08Priorities value={[]} onChange={onChange} />
    );
    fireEvent.press(getByTestId('priority-quality'));
    expect(onChange).toHaveBeenCalledWith(['quality']);
  });

  it('removes a selected chip on second tap', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(
      <Step08Priorities value={['quality']} onChange={onChange} />
    );
    fireEvent.press(getByTestId('priority-quality'));
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it('blocks adding a 4th when 3 already selected', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(
      <Step08Priorities
        value={['quality', 'price', 'durability']}
        onChange={onChange}
      />
    );
    fireEvent.press(getByTestId('priority-eco_friendly'));
    expect(onChange).not.toHaveBeenCalled();
  });

  it('still allows DEselecting when at the cap of 3', () => {
    const onChange = jest.fn();
    const { getByTestId } = render(
      <Step08Priorities
        value={['quality', 'price', 'durability']}
        onChange={onChange}
      />
    );
    fireEvent.press(getByTestId('priority-quality'));
    expect(onChange).toHaveBeenCalledWith(['price', 'durability']);
  });

  it('marks selected chips with accessibilityState.selected=true', () => {
    const { getByTestId } = render(
      <Step08Priorities value={['quality']} onChange={jest.fn()} />
    );
    expect(getByTestId('priority-quality').props.accessibilityState?.selected).toBe(true);
    expect(getByTestId('priority-price').props.accessibilityState?.selected).toBe(false);
  });
});
