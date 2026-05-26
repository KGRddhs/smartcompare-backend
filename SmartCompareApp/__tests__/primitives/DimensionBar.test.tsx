/**
 * Primitive contract — DimensionBar.
 *
 * Contract (plan S0.3 + design doc ResultsScreen):
 *   - Two-color comparative bar: secondary (gray) + emerald, with a 2px gap
 *     between them.
 *   - Props: left (0–1), right (0–1) — the relative proportions.
 *   - Winner side gets emerald; loser side gets secondary; ties show both
 *     gray.
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { DimensionBar } from '../../src/components/primitives/DimensionBar';

describe('DimensionBar primitive', () => {
  it('renders two segments + 2px gap', () => {
    const { getByTestId } = render(<DimensionBar left={0.6} right={0.4} winner="left" />);
    const leftSeg = getByTestId('dim-bar-left');
    const rightSeg = getByTestId('dim-bar-right');
    const gap = getByTestId('dim-bar-gap');
    expect(leftSeg).toBeTruthy();
    expect(rightSeg).toBeTruthy();
    // 2px gap contract.
    const gapStyleArr = Array.isArray(gap.props.style) ? gap.props.style : [gap.props.style];
    const flat = Object.assign({}, ...gapStyleArr.filter(Boolean));
    expect(flat.width).toBe(2);
  });

  it('left winner: left segment is emerald, right segment is secondary', () => {
    const { getByTestId } = render(<DimensionBar left={0.7} right={0.3} winner="left" />);
    const colorOf = (id: string) => {
      const node = getByTestId(id);
      const arr = Array.isArray(node.props.style) ? node.props.style : [node.props.style];
      const flat = Object.assign({}, ...arr.filter(Boolean));
      return String(flat.backgroundColor).toLowerCase();
    };
    expect(colorOf('dim-bar-left')).toBe('#10b981');
    expect(colorOf('dim-bar-right')).not.toBe('#10b981');
  });

  it('right winner: right segment is emerald, left segment is secondary', () => {
    const { getByTestId } = render(<DimensionBar left={0.3} right={0.7} winner="right" />);
    const colorOf = (id: string) => {
      const node = getByTestId(id);
      const arr = Array.isArray(node.props.style) ? node.props.style : [node.props.style];
      const flat = Object.assign({}, ...arr.filter(Boolean));
      return String(flat.backgroundColor).toLowerCase();
    };
    expect(colorOf('dim-bar-right')).toBe('#10b981');
    expect(colorOf('dim-bar-left')).not.toBe('#10b981');
  });

  it('tie: neither segment is emerald', () => {
    const { getByTestId } = render(<DimensionBar left={0.5} right={0.5} winner={null} />);
    const colorOf = (id: string) => {
      const node = getByTestId(id);
      const arr = Array.isArray(node.props.style) ? node.props.style : [node.props.style];
      const flat = Object.assign({}, ...arr.filter(Boolean));
      return String(flat.backgroundColor).toLowerCase();
    };
    expect(colorOf('dim-bar-left')).not.toBe('#10b981');
    expect(colorOf('dim-bar-right')).not.toBe('#10b981');
  });
});
