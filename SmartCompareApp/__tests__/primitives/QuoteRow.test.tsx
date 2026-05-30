/**
 * Primitive contract — QuoteRow.
 *
 * Added per design-doc patch 75e78f5 — Step01Welcome (OnboardingWelcomeScreen.jsx)
 * composes a trio of QuoteRow testimonial cards (NOT a PhoneMockup hero).
 *
 * Contract (plan S0.3 + design § 3.1 Step01 row):
 *   - Glass-blur card with an emerald dot + quote text + optional author/region
 *   - Used in trios on Step01Welcome
 *   - Frontend lands at src/components/primitives/QuoteRow.tsx during S0.3
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { QuoteRow } from '../../src/components/primitives/QuoteRow';

describe('QuoteRow primitive', () => {
  it('renders quote text', () => {
    const { getByText } = render(
      <QuoteRow quote="Saved me hours of doomscrolling." author="Lulwa, Manama" />,
    );
    expect(getByText('Saved me hours of doomscrolling.')).toBeTruthy();
  });

  it('renders author + region line when provided', () => {
    const { getByText } = render(
      <QuoteRow quote="Finally a comparison app for the GCC." author="Ahmed, Riyadh" />,
    );
    expect(getByText('Ahmed, Riyadh')).toBeTruthy();
  });

  it('exposes emerald dot via testID', () => {
    const { getByTestId } = render(<QuoteRow quote="x" author="y" />);
    const dot = getByTestId('quote-row-dot');
    const arr = Array.isArray(dot.props.style) ? dot.props.style : [dot.props.style];
    const flat = Object.assign({}, ...arr.filter(Boolean));
    // Emerald primary #10B981
    expect(String(flat.backgroundColor).toLowerCase()).toBe('#10b981');
  });

  it('renders without author when omitted', () => {
    const { getByText, queryByTestId } = render(<QuoteRow quote="No author here" />);
    expect(getByText('No author here')).toBeTruthy();
    // author block should be absent (testID="quote-row-author" not rendered)
    expect(queryByTestId('quote-row-author')).toBeNull();
  });
});
