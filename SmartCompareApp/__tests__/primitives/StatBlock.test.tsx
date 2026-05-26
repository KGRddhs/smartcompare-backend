/**
 * Primitive contract — StatBlock.
 *
 * Added per QA § 6 audit patch (commit 7676875). Used at Step15Reveal
 * (Top priority / Budget / cohort count grid).
 *
 * Contract:
 *   - Renders { label, value } pair stacked vertically
 *   - Label is muted/secondary; value is bold primary
 *   - Used in a 3-column grid layout on Step15
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { StatBlock } from '../../src/components/primitives/StatBlock';

describe('StatBlock primitive', () => {
  it('renders label + value', () => {
    const { getByText } = render(<StatBlock label="Top priority" value="Quality" />);
    expect(getByText('Top priority')).toBeTruthy();
    expect(getByText('Quality')).toBeTruthy();
  });

  it('exposes value via testID', () => {
    const { getByTestId } = render(
      <StatBlock label="Budget" value="Mid" testID="stat-budget" />,
    );
    expect(getByTestId('stat-budget')).toBeTruthy();
  });

  it('handles numeric values', () => {
    const { getByText } = render(<StatBlock label="Cohort peers" value={2074} />);
    // Numeric should render somehow — accept exact "2074" or formatted "2,074".
    const node = getByText(/2[,]?074/);
    expect(node).toBeTruthy();
  });
});
