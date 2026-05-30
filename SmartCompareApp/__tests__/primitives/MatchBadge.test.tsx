/**
 * Primitive contract — MatchBadge.
 *
 * Added per QA § 6 audit patch (commit 7676875). Used at Step15Reveal
 * (replaces RevealBurst for Step15) AND potentially on ResultsScreen.
 *
 * Contract (design doc § 3.2 / § 3.1 Step15):
 *   - 88px emerald-accentLight circle
 *   - "%" number inside (default 92)
 *   - "✦" sparkle accent top-right
 *   - Optional `eyebrow` text above ("Strong match")
 *   - Light scale-in on mount (0.94→1.0 with withSpring)
 */
import React from 'react';
import { render } from '@testing-library/react-native';
import { MatchBadge } from '../../src/components/primitives/MatchBadge';

describe('MatchBadge primitive', () => {
  it('renders default percentage', () => {
    const { getByText } = render(<MatchBadge percent={92} />);
    expect(getByText('92%')).toBeTruthy();
  });

  it('renders custom percentage', () => {
    const { getByText } = render(<MatchBadge percent={87} />);
    expect(getByText('87%')).toBeTruthy();
  });

  it('shows eyebrow text when provided', () => {
    const { getByText } = render(<MatchBadge percent={92} eyebrow="Strong match" />);
    expect(getByText('Strong match')).toBeTruthy();
  });

  it('exposes sparkle accent via testID', () => {
    const { getByTestId } = render(<MatchBadge percent={92} />);
    expect(getByTestId('match-badge-sparkle')).toBeTruthy();
  });

  it('circle is 88px diameter (design spec)', () => {
    const { getByTestId } = render(<MatchBadge percent={92} />);
    const circle = getByTestId('match-badge-circle');
    const arr = Array.isArray(circle.props.style) ? circle.props.style : [circle.props.style];
    const flat = Object.assign({}, ...arr.filter(Boolean));
    expect(flat.width).toBe(88);
    expect(flat.height).toBe(88);
  });

  it('clamps percent to [0, 100]', () => {
    const { getByText: highPct } = render(<MatchBadge percent={150} />);
    expect(highPct('100%')).toBeTruthy();
    const { getByText: lowPct } = render(<MatchBadge percent={-10} />);
    expect(lowPct('0%')).toBeTruthy();
  });
});
