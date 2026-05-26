/**
 * Hero SVG snapshot — LoadingRings.
 *
 * Contract (design doc § 3.2):
 *   - Reuses ConcentricMotif + tabular-nums counter chip below
 *   - Counter ticks 0→2074 over 2400ms (ease-out-cubic), requestAnimationFrame
 *   - Formatted with thousands separator: "2,074" NOT "2074"
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { LoadingRings } from '../../src/components/hero/LoadingRings';

describe('LoadingRings hero', () => {
  it('renders default snapshot', () => {
    const tree = render(<LoadingRings />).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('renders with explicit counter target', () => {
    const tree = render(<LoadingRings counterTarget={2074} />).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('formats counter with thousands separator (2,074 not 2074)', () => {
    // The component renders the FINAL value when animated={false} so we can
    // assert the format deterministically without driving rAF.
    const { queryByText } = render(
      <LoadingRings counterTarget={2074} animated={false} />,
    );
    // Acceptable formats: "2,074" or "2 074" (locale-dependent), but never
    // raw "2074" digits-only.
    const candidate = queryByText(/2[,\s]074/);
    expect(candidate).not.toBeNull();
    expect(queryByText(/^2074$/)).toBeNull();
  });
});
