/**
 * Edge cases for StyleProfileCard rendering.
 *
 * Confidence-gated visibility, partial modal data, and minimal payload
 * scenarios to ensure the card degrades gracefully.
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import StyleProfileCard from '../src/components/StyleProfileCard';
import type { CohortDisplayProfile } from '../src/services/api';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('StyleProfileCard — degraded payloads', () => {
  it('renders when modal is empty object (just persona + n)', () => {
    const minimal: CohortDisplayProfile = {
      persona_label: 'Balanced shopper',
      n: 50,
      confidence: 'medium',
      modal: {},
    };
    const { getByText, queryByText } = render(
      <StyleProfileCard display={minimal} onEditPress={jest.fn()} />
    );
    expect(getByText('Balanced shopper')).toBeTruthy();
    // No data rows since modal is empty
    expect(queryByText('profile.styleProfile.priorities')).toBeNull();
    expect(queryByText('profile.styleProfile.budget')).toBeNull();
    expect(queryByText('profile.styleProfile.style')).toBeNull();
  });

  it('renders when only top_deciding_factor present (single priority)', () => {
    const display: CohortDisplayProfile = {
      persona_label: 'Quality-first focused buyer',
      n: 12,
      confidence: 'medium',
      modal: { top_deciding_factor: 'Quality' },
    };
    const { getByText } = render(
      <StyleProfileCard display={display} onEditPress={jest.fn()} />
    );
    expect(getByText('profile.styleProfile.priorities')).toBeTruthy();
    expect(getByText('Quality')).toBeTruthy();
  });

  it('hides priorities row when both top and second deciding factors are missing', () => {
    const display: CohortDisplayProfile = {
      persona_label: 'X',
      n: 10,
      confidence: 'medium',
      modal: { spend_bracket: '25-50 BHD' },
    };
    const { queryByText, getByText } = render(
      <StyleProfileCard display={display} onEditPress={jest.fn()} />
    );
    expect(queryByText('profile.styleProfile.priorities')).toBeNull();
    expect(getByText('profile.styleProfile.budget')).toBeTruthy();
  });

  it('hides style row when preferred_assistance_style is missing', () => {
    const display: CohortDisplayProfile = {
      persona_label: 'X',
      n: 10,
      confidence: 'medium',
      modal: {
        top_deciding_factor: 'Quality',
        spend_bracket: '25-50 BHD',
      },
    };
    const { queryByText } = render(
      <StyleProfileCard display={display} onEditPress={jest.fn()} />
    );
    expect(queryByText('profile.styleProfile.style')).toBeNull();
  });

  it('renders edit button regardless of modal completeness', () => {
    const minimal: CohortDisplayProfile = {
      persona_label: 'X',
      n: 5,
      confidence: 'low',
      modal: {},
    };
    const { getByText } = render(
      <StyleProfileCard display={minimal} onEditPress={jest.fn()} />
    );
    expect(getByText('profile.styleProfile.editButton')).toBeTruthy();
  });

  it('handles n=1 (single matching user) gracefully — still renders', () => {
    const display: CohortDisplayProfile = {
      persona_label: 'Niche buyer',
      n: 1,
      confidence: 'low',
      modal: { top_deciding_factor: 'Brand' },
    };
    const { getByText } = render(
      <StyleProfileCard display={display} onEditPress={jest.fn()} />
    );
    expect(getByText('Niche buyer')).toBeTruthy();
    expect(getByText('Brand')).toBeTruthy();
  });

  it('handles long persona_label without truncation crash', () => {
    const longLabel = 'Quality-first focused premium-leaning brand-loyal buyer with strong service expectations';
    const display: CohortDisplayProfile = {
      persona_label: longLabel,
      n: 10,
      confidence: 'medium',
      modal: {},
    };
    const { getByText } = render(
      <StyleProfileCard display={display} onEditPress={jest.fn()} />
    );
    expect(getByText(longLabel)).toBeTruthy();
  });
});
