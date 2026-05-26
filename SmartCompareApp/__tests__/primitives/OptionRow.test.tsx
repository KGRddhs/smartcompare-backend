/**
 * Primitive contract — OptionRow.
 *
 * Contract (plan S0.3 + design doc § 3.1 Step08Priorities):
 *   - Props: option, active, onToggle, style: 'icon-circle' | 'plain'
 *   - style='icon-circle' renders a 36px icon circle to the left
 *   - style='plain' renders no icon circle
 *   - Active state inverts background (black on select, Cal AI pattern)
 */
import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import { OptionRow } from '../../src/components/primitives/OptionRow';

describe('OptionRow primitive', () => {
  const sample = { key: 'quality', label: 'Quality', icon: 'star' };

  it('renders option label', () => {
    const { getByText } = render(
      <OptionRow option={sample} active={false} onToggle={() => {}} style="plain" />,
    );
    expect(getByText('Quality')).toBeTruthy();
  });

  it('style="icon-circle" renders the icon circle wrapper', () => {
    const { getByTestId } = render(
      <OptionRow option={sample} active={false} onToggle={() => {}} style="icon-circle" />,
    );
    const circle = getByTestId('option-row-icon-circle');
    expect(circle).toBeTruthy();
    // 36px contract from Cal-AI-Lite spec.
    const styleArr = Array.isArray(circle.props.style) ? circle.props.style : [circle.props.style];
    const flattened = Object.assign({}, ...styleArr.filter(Boolean));
    expect(flattened.width).toBe(36);
    expect(flattened.height).toBe(36);
  });

  it('style="plain" does NOT render the icon circle wrapper', () => {
    const { queryByTestId } = render(
      <OptionRow option={sample} active={false} onToggle={() => {}} style="plain" />,
    );
    expect(queryByTestId('option-row-icon-circle')).toBeNull();
  });

  it('calls onToggle with option key when pressed', () => {
    const onToggle = jest.fn();
    const { getByText } = render(
      <OptionRow option={sample} active={false} onToggle={onToggle} style="plain" />,
    );
    fireEvent.press(getByText('Quality'));
    expect(onToggle).toHaveBeenCalledWith('quality');
  });

  it('active state inverts via accessibilityState.selected', () => {
    const { getByTestId, rerender } = render(
      <OptionRow option={sample} active={false} onToggle={() => {}} style="icon-circle" testID="row" />,
    );
    expect(getByTestId('row').props.accessibilityState?.selected).toBe(false);
    rerender(
      <OptionRow option={sample} active={true} onToggle={() => {}} style="icon-circle" testID="row" />,
    );
    expect(getByTestId('row').props.accessibilityState?.selected).toBe(true);
  });
});
