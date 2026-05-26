/**
 * Primitive contract — CohortBullet.
 *
 * Added per QA § 6 audit patch (commit 7676875). Used at Step12CohortProof
 * (3 bullet items below the PeerLattice hero).
 *
 * Contract:
 *   - Icon (lucide-react-native) + text bullet item
 *   - Optional `accent` prop highlights this bullet in emerald
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { CohortBullet } from '../../src/components/primitives/CohortBullet';

describe('CohortBullet primitive', () => {
  it('renders bullet text', () => {
    const { getByText } = render(
      <CohortBullet icon="users" text="388 GCC shoppers helped train this" />,
    );
    expect(getByText('388 GCC shoppers helped train this')).toBeTruthy();
  });

  it('exposes icon via testID', () => {
    const { getByTestId } = render(
      <CohortBullet icon="users" text="x" testID="bullet-1" />,
    );
    expect(getByTestId('bullet-1')).toBeTruthy();
  });

  it('accent=true highlights in emerald', () => {
    const { getByTestId } = render(
      <CohortBullet
        icon="check"
        text="Privacy first"
        accent={true}
        testID="bullet-accent"
      />,
    );
    const node = getByTestId('bullet-accent');
    // Either backgroundColor or borderColor or color should be emerald
    // when accent=true. We accept any of those to give frontend latitude.
    const arr = Array.isArray(node.props.style) ? node.props.style : [node.props.style];
    const flat = Object.assign({}, ...arr.filter(Boolean));
    const colors = [flat.backgroundColor, flat.borderColor, flat.color]
      .filter(Boolean)
      .map((c) => String(c).toLowerCase());
    expect(colors.some((c) => c === '#10b981')).toBe(true);
  });
});
