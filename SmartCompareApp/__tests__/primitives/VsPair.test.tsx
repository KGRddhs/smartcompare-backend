/**
 * Primitive contract — VsPair.
 *
 * Frontend lands the component at src/components/primitives/VsPair.tsx during
 * S0.3 (plan § Frontend lane). Test stays RED until that ships.
 *
 * Contract (plan S0.3):
 *   - Two ProductBlock children with a center, absolute-positioned emerald
 *     "VS" pill between them.
 *   - Props: `left`, `right`, `winner: 'left' | 'right' | null`.
 *   - When winner='left', the left ProductBlock has the winner outline; when
 *     'right', the right block does. Null = no outline.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { VsPair } from '../../src/components/primitives/VsPair';

describe('VsPair primitive', () => {
  const productA = { name: 'iPhone 15', sub: '128GB · BHD 350' };
  const productB = { name: 'Galaxy S24', sub: '256GB · BHD 320' };

  it('renders both products + center vs pill', () => {
    const { getByText, getByTestId } = render(
      <VsPair left={productA} right={productB} winner={null} />,
    );
    expect(getByText('iPhone 15')).toBeTruthy();
    expect(getByText('Galaxy S24')).toBeTruthy();
    // emerald vs pill exposed via testID
    expect(getByTestId('vs-pair-pill')).toBeTruthy();
  });

  it('applies winner outline to left when winner="left"', () => {
    const { getByTestId } = render(
      <VsPair left={productA} right={productB} winner="left" />,
    );
    const left = getByTestId('vs-pair-block-left');
    const right = getByTestId('vs-pair-block-right');
    // ProductBlock receives a winner prop / testID flag — the visual
    // contract is "the winning block carries the emerald outline".
    expect(left.props.accessibilityState?.selected).toBe(true);
    expect(right.props.accessibilityState?.selected).toBe(false);
  });

  it('applies winner outline to right when winner="right"', () => {
    const { getByTestId } = render(
      <VsPair left={productA} right={productB} winner="right" />,
    );
    expect(getByTestId('vs-pair-block-right').props.accessibilityState?.selected).toBe(true);
    expect(getByTestId('vs-pair-block-left').props.accessibilityState?.selected).toBe(false);
  });

  it('no outline when winner=null', () => {
    const { getByTestId } = render(
      <VsPair left={productA} right={productB} winner={null} />,
    );
    expect(getByTestId('vs-pair-block-left').props.accessibilityState?.selected).toBe(false);
    expect(getByTestId('vs-pair-block-right').props.accessibilityState?.selected).toBe(false);
  });
});
