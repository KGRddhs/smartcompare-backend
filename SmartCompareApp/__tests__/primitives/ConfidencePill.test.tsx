/**
 * Primitive contract — ConfidencePill.
 *
 * Contract (plan S0.3):
 *   - Dot + label pill
 *   - Props: label, level: 'high' | 'medium' | 'low'
 *   - Dot color is emerald for high, amber for medium, gray for low
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { ConfidencePill } from '../../src/components/primitives/ConfidencePill';

describe('ConfidencePill primitive', () => {
  it('renders label text', () => {
    const { getByText } = render(<ConfidencePill label="High confidence" level="high" />);
    expect(getByText('High confidence')).toBeTruthy();
  });

  it('dot color matches level="high" (emerald)', () => {
    const { getByTestId } = render(<ConfidencePill label="x" level="high" />);
    const dot = getByTestId('confidence-pill-dot');
    const styleArr = Array.isArray(dot.props.style) ? dot.props.style : [dot.props.style];
    const flat = Object.assign({}, ...styleArr.filter(Boolean));
    // Emerald primary #10B981. Frontend may use the colors.accent token, so
    // accept either the literal hex or any string starting with `#10`.
    expect(String(flat.backgroundColor).toLowerCase()).toMatch(/^#10b981$/);
  });

  it('dot color differs across high / medium / low', () => {
    const { getByTestId: gHigh } = render(<ConfidencePill label="x" level="high" />);
    const { getByTestId: gMed } = render(<ConfidencePill label="x" level="medium" />);
    const { getByTestId: gLow } = render(<ConfidencePill label="x" level="low" />);

    const colorOf = (g: any) => {
      const node = g('confidence-pill-dot');
      const arr = Array.isArray(node.props.style) ? node.props.style : [node.props.style];
      const flat = Object.assign({}, ...arr.filter(Boolean));
      return String(flat.backgroundColor).toLowerCase();
    };

    const high = colorOf(gHigh);
    const med = colorOf(gMed);
    const low = colorOf(gLow);
    expect(new Set([high, med, low]).size).toBe(3);
  });
});
