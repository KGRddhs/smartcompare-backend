/**
 * StyleProfileCard tests.
 *
 * Card visibility (per design Section 5.6):
 *   - render persona when display payload present
 *   - render NOTHING when display is null (low confidence or population fallback)
 *   - tap "edit" CTA invokes onEditPress
 */

import React from 'react';
import { render, fireEvent } from '@testing-library/react-native';
import StyleProfileCard from '../src/components/StyleProfileCard';
import type { CohortDisplayProfile } from '../src/services/api';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, any>) => {
      if (params) {
        return Object.entries(params).reduce(
          (acc, [k, v]) => acc.replace(`{{${k}}}`, String(v)),
          key
        );
      }
      return key;
    },
  }),
}));

const FULL_DISPLAY: CohortDisplayProfile = {
  persona_label: 'Quality-first focused buyer',
  n: 23,
  confidence: 'high',
  modal: {
    top_deciding_factor: 'Quality',
    second_deciding_factor: 'Price',
    spend_bracket: '25-50 BHD',
    preferred_assistance_style: 'Show me 2 or 3 suitable options',
  },
};

describe('StyleProfileCard', () => {
  it('renders nothing when display is null', () => {
    const { queryByText } = render(
      <StyleProfileCard display={null} onEditPress={jest.fn()} />
    );
    expect(queryByText('profile.styleProfile.title')).toBeNull();
  });

  it('renders persona label and based-on count when display is provided', () => {
    const { getByText, queryByText } = render(
      <StyleProfileCard display={FULL_DISPLAY} onEditPress={jest.fn()} />
    );
    // Phase 5 § 4d redesign — the legacy "STYLE PROFILE" eyebrow was
    // replaced by the prominent "Match strength" eyebrow + sparkle
    // headline. The persona label still renders for context. basedOn
    // is rendered when there's no governorate on the modal.
    expect(getByText('profile.styleProfile.matchStrength')).toBeTruthy();
    expect(getByText('Quality-first focused buyer')).toBeTruthy();
    expect(queryByText('profile.styleProfile.basedOn')).toBeTruthy();
  });

  it('renders top priorities row from modal', () => {
    const { getByText } = render(
      <StyleProfileCard display={FULL_DISPLAY} onEditPress={jest.fn()} />
    );
    expect(getByText('profile.styleProfile.priorities')).toBeTruthy();
    expect(getByText('Quality, Price')).toBeTruthy();
  });

  it('renders typical budget row from modal', () => {
    const { getByText } = render(
      <StyleProfileCard display={FULL_DISPLAY} onEditPress={jest.fn()} />
    );
    expect(getByText('profile.styleProfile.budget')).toBeTruthy();
    expect(getByText('25-50 BHD')).toBeTruthy();
  });

  it('renders style row from modal preferred_assistance_style', () => {
    const { getByText } = render(
      <StyleProfileCard display={FULL_DISPLAY} onEditPress={jest.fn()} />
    );
    expect(getByText('profile.styleProfile.style')).toBeTruthy();
    expect(getByText(/Show me 2 or 3 suitable options/)).toBeTruthy();
  });

  it('invokes onEditPress when Edit button pressed', () => {
    const onEditPress = jest.fn();
    const { getByText } = render(
      <StyleProfileCard display={FULL_DISPLAY} onEditPress={onEditPress} />
    );
    fireEvent.press(getByText('profile.styleProfile.editButton'));
    expect(onEditPress).toHaveBeenCalledTimes(1);
  });

  it('omits second_deciding_factor in priorities row when only one provided', () => {
    const partial: CohortDisplayProfile = {
      ...FULL_DISPLAY,
      modal: { ...FULL_DISPLAY.modal, second_deciding_factor: undefined },
    };
    const { getByText, queryByText } = render(
      <StyleProfileCard display={partial} onEditPress={jest.fn()} />
    );
    // priorities row renders just "Quality" (not "Quality, Price")
    expect(getByText('Quality')).toBeTruthy();
    expect(queryByText('Quality, Price')).toBeNull();
  });

  it('hides budget row entirely when modal lacks spend_bracket', () => {
    const noBudget: CohortDisplayProfile = {
      ...FULL_DISPLAY,
      modal: { ...FULL_DISPLAY.modal, spend_bracket: undefined },
    };
    const { queryByText } = render(
      <StyleProfileCard display={noBudget} onEditPress={jest.fn()} />
    );
    expect(queryByText('profile.styleProfile.budget')).toBeNull();
  });
});
