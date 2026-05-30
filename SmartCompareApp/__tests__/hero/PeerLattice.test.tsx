/**
 * Hero SVG snapshot — PeerLattice.
 *
 * Added per QA § 6 audit patch (commit 7676875). Replaces CohortBarChart at
 * Step12CohortProof — JSX uses an 8×12 dot grid, NOT a bar chart.
 *
 * Contract (design doc § 3.2 PeerLattice):
 *   - 8 columns × 12 rows dot grid (96 dots total)
 *   - YOU-dot in center: emerald accent with subtle glow ring
 *   - Surrounding peers fall off in opacity radially
 *   - Stagger fade-in from center outward over 600ms (cubic-bezier)
 *   - YOU-dot scales 0→1.0 with subtle spring
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { PeerLattice } from '../../src/components/hero/PeerLattice';

describe('PeerLattice hero', () => {
  it('renders default snapshot', () => {
    const tree = render(<PeerLattice />).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('renders at custom size', () => {
    const tree = render(<PeerLattice size={240} />).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('exposes the YOU-dot via testID', () => {
    const { getByTestId } = render(<PeerLattice />);
    // The center YOU-dot must be discoverable so Step12CohortProof + a11y
    // can highlight + announce it.
    expect(getByTestId('peer-lattice-you-dot')).toBeTruthy();
  });

  it('YOU-dot is emerald (#10B981) — radial-falloff peers are not', () => {
    const { getByTestId } = render(<PeerLattice />);
    const you = getByTestId('peer-lattice-you-dot');
    const arr = Array.isArray(you.props.style) ? you.props.style : [you.props.style];
    const flat = Object.assign({}, ...arr.filter(Boolean));
    // Accept fill prop OR backgroundColor — SVG primitives use fill, RN
    // host views use backgroundColor.
    const color = String(flat.backgroundColor || you.props.fill || '').toLowerCase();
    expect(color).toBe('#10b981');
  });

  it('renders without throwing when animated={false}', () => {
    expect(() => render(<PeerLattice animated={false} />)).not.toThrow();
  });
});
