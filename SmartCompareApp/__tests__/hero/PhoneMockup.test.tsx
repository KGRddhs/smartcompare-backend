/**
 * Hero SVG snapshot — PhoneMockup.
 *
 * Frontend lands the component at src/components/hero/PhoneMockup.tsx during
 * S0.1 (plan § Frontend lane). Test stays RED until that ships.
 *
 * Contract (design doc § 3.2):
 *   - 180×280px default render
 *   - 0.95→1.0 scale-in on mount (320ms cubic-bezier)
 *   - Respects useReducedMotion() — animation no-op when system reduces motion
 *   - Stylized iOS-shape SVG outline with Qaren wordmark + emerald accent dot
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { PhoneMockup } from '../../src/components/hero/PhoneMockup';

describe('PhoneMockup hero', () => {
  it('renders default snapshot', () => {
    const tree = render(<PhoneMockup />).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('renders at custom size', () => {
    const tree = render(<PhoneMockup size={240} />).toJSON();
    expect(tree).toMatchSnapshot();
  });

  it('renders without throwing when animated={false}', () => {
    // useReducedMotion() pathway — animation must no-op, NOT throw.
    expect(() => render(<PhoneMockup animated={false} />)).not.toThrow();
  });
});
