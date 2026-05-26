/**
 * Hero SVG snapshot — CohortBarChart.
 *
 * Contract (design doc § 3.2):
 *   - 8 vertical bars (24px wide, heights 30–90px)
 *   - One emerald-filled bar = user's cohort; rest gray
 *   - Caption "Capital · 25-34" below
 *   - Bars grow 0 → full height staggered 80ms each, cubic-bezier(0.32,0.72,0,1)
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { CohortBarChart } from '../../src/components/hero/CohortBarChart';

describe('CohortBarChart hero', () => {
  it('renders default snapshot with default cohort highlight', () => {
    const tree = render(<CohortBarChart />).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('honors custom cohortIndex highlight', () => {
    // 8 bars total, index 3 emerald, others gray.
    const tree = render(<CohortBarChart cohortIndex={3} />).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('renders caption when provided', () => {
    const { getByText } = render(
      <CohortBarChart cohortIndex={2} caption="Capital · 25-34" />,
    );
    expect(getByText('Capital · 25-34')).toBeTruthy();
  });
});
