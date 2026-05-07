/**
 * StyleProfileCard redesign tests — Phase 5 Task 43.
 *
 * Adds the prominent "Strong match — N peers in Governorate" headline
 * + strength progress per design § 4d. The existing card behavior
 * (basedOn / priorities / edit button) is covered by the existing
 * StyleProfileCard.test.tsx; this file targets the new contract.
 */

import React from 'react';
import { render } from '@testing-library/react-native';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      let str = (opts?.defaultValue as string) ?? key;
      if (opts) {
        for (const [k, v] of Object.entries(opts)) {
          if (k === 'defaultValue') continue;
          str = str.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
        }
      }
      return str;
    },
  }),
}));

import StyleProfileCard from '../src/components/StyleProfileCard';

const baseDisplay = {
  persona_label: 'Quality-first focused buyer',
  n: 47,
  confidence: 'high' as const,
  modal: {
    top_deciding_factor: 'Quality',
    second_deciding_factor: 'Price',
    spend_bracket: 'mid',
    preferred_assistance_style: 'guided',
    governorate: 'Capital',
  },
};

describe('StyleProfileCard redesign — Phase 5 Task 43', () => {
  it('renders the match-strength eyebrow + sparkle headline', () => {
    const { getByTestId } = render(
      <StyleProfileCard display={baseDisplay} onEditPress={jest.fn()} />
    );
    expect(getByTestId('style-profile-strength-headline')).toBeTruthy();
  });

  it('renders the peer count + governorate sub-line when present', () => {
    const { getByText } = render(
      <StyleProfileCard display={baseDisplay} onEditPress={jest.fn()} />
    );
    // The peer count and governorate flow into the same line; the i18n
    // key receives both as interpolation params.
    expect(getByText(/47/)).toBeTruthy();
    expect(getByText(/Capital/)).toBeTruthy();
  });

  it('renders the strength-progress bar with high=1.0 progress', () => {
    const { getByTestId } = render(
      <StyleProfileCard display={baseDisplay} onEditPress={jest.fn()} />
    );
    const bar = getByTestId('style-profile-strength-bar');
    expect(bar.props['data-progress']).toBeCloseTo(1.0, 2);
  });

  it('drops to medium=~0.66 progress for confidence=medium', () => {
    const { getByTestId } = render(
      <StyleProfileCard
        display={{ ...baseDisplay, confidence: 'medium' }}
        onEditPress={jest.fn()}
      />
    );
    expect(getByTestId('style-profile-strength-bar').props['data-progress']).toBeCloseTo(0.66, 1);
  });

  it('drops to low=~0.33 progress for confidence=low', () => {
    const { getByTestId } = render(
      <StyleProfileCard
        display={{ ...baseDisplay, confidence: 'low' }}
        onEditPress={jest.fn()}
      />
    );
    expect(getByTestId('style-profile-strength-bar').props['data-progress']).toBeCloseTo(0.33, 1);
  });

  it('omits the governorate sub-line when modal.governorate is missing', () => {
    const { queryByText } = render(
      <StyleProfileCard
        display={{ ...baseDisplay, modal: { top_deciding_factor: 'Quality' } }}
        onEditPress={jest.fn()}
      />
    );
    expect(queryByText(/Capital/)).toBeNull();
  });

  it('still renders nothing when display is null (existing contract)', () => {
    const { queryByTestId } = render(
      <StyleProfileCard display={null} onEditPress={jest.fn()} />
    );
    expect(queryByTestId('style-profile-strength-headline')).toBeNull();
  });
});
