/**
 * Hero SVG snapshot — ConcentricMotif.
 *
 * Contract (design doc § 3.2):
 *   - 220×220px default
 *   - 3 emerald rings expanding outward from a center logo
 *   - Each ring loops withTiming({ scale: 0.8→2.5, opacity: 0.9→0 }, 2100ms),
 *     staggered 0ms / 700ms / 1400ms
 *   - useReducedMotion() → static (no loop)
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { ConcentricMotif } from '../../src/components/hero/ConcentricMotif';

describe('ConcentricMotif hero', () => {
  it('renders default snapshot (3 rings present)', () => {
    const tree = render(<ConcentricMotif />).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('renders at custom size', () => {
    const tree = render(<ConcentricMotif size={160} />).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('renders without throwing when animated={false}', () => {
    expect(() => render(<ConcentricMotif animated={false} />)).not.toThrow();
  });
});
