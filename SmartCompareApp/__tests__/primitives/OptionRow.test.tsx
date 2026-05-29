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

  // F-S2.W1 extension — icon-in-circle + sub-line rendering.
  describe('F-S2.W1 extension (icon glyph + sub line)', () => {
    it('renders option.icon inside the circle when style="icon-circle"', () => {
      const optionWithIcon = { key: 'bh', label: 'Bahrain', icon: '🇧🇭' };
      const { getByTestId, getByText } = render(
        <OptionRow
          option={optionWithIcon}
          active={false}
          onToggle={() => {}}
          style="icon-circle"
        />,
      );
      expect(getByTestId('option-row-icon-glyph')).toBeTruthy();
      expect(getByText('🇧🇭')).toBeTruthy();
    });

    it('does NOT render the icon glyph when style="plain" even if icon is set', () => {
      const optionWithIcon = { key: 'bh', label: 'Bahrain', icon: '🇧🇭' };
      const { queryByTestId } = render(
        <OptionRow
          option={optionWithIcon}
          active={false}
          onToggle={() => {}}
          style="plain"
        />,
      );
      expect(queryByTestId('option-row-icon-glyph')).toBeNull();
    });

    it('renders option.sub as a secondary line when provided', () => {
      const optionWithSub = {
        key: 'bh',
        label: 'Bahrain',
        sub: 'Capital, Muharraq, Northern, Southern',
      };
      const { getByText, getByTestId } = render(
        <OptionRow
          option={optionWithSub}
          active={false}
          onToggle={() => {}}
          style="icon-circle"
        />,
      );
      expect(getByText('Bahrain')).toBeTruthy();
      expect(getByText('Capital, Muharraq, Northern, Southern')).toBeTruthy();
      expect(getByTestId('option-row-sub')).toBeTruthy();
    });

    it('does NOT render the sub slot when option.sub is absent (backward-compat)', () => {
      const { queryByTestId } = render(
        <OptionRow
          option={sample}
          active={false}
          onToggle={() => {}}
          style="icon-circle"
        />,
      );
      expect(queryByTestId('option-row-sub')).toBeNull();
    });

    it('backward-compat: empty icon circle still renders when icon is unset', () => {
      // Pre-S2 callers may pass only {key, label}. Circle must still render
      // (as an empty 36px slot) — the only change is no glyph inside. The
      // `sample` constant above ships an `icon: 'star'` so this test
      // explicitly omits it.
      const optionNoIcon = { key: 'quality', label: 'Quality' };
      const { getByTestId, queryByTestId } = render(
        <OptionRow
          option={optionNoIcon}
          active={false}
          onToggle={() => {}}
          style="icon-circle"
        />,
      );
      expect(getByTestId('option-row-icon-circle')).toBeTruthy();
      expect(queryByTestId('option-row-icon-glyph')).toBeNull();
    });
  });
});
