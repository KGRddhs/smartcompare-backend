/**
 * Test that StyleProfileCard renders priorities consistently across
 * the locale formats backend may emit (Quality vs Quality - Reliability,
 * pluralized vs singular trust sources, etc.).
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

describe('StyleProfileCard — priority formatting', () => {
  it('joins two factors with ", " separator', () => {
    const display: CohortDisplayProfile = {
      persona_label: 'X',
      n: 20,
      confidence: 'high',
      modal: { top_deciding_factor: 'Quality', second_deciding_factor: 'Price' },
    };
    const { getByText } = render(
      <StyleProfileCard display={display} onEditPress={jest.fn()} />
    );
    expect(getByText('Quality, Price')).toBeTruthy();
  });

  it('renders compound factor names verbatim (e.g. "Quality - Reliability")', () => {
    const display: CohortDisplayProfile = {
      persona_label: 'X',
      n: 20,
      confidence: 'high',
      modal: {
        top_deciding_factor: 'Quality - Reliability',
        second_deciding_factor: 'Value for money',
      },
    };
    const { getByText } = render(
      <StyleProfileCard display={display} onEditPress={jest.fn()} />
    );
    expect(getByText('Quality - Reliability, Value for money')).toBeTruthy();
  });

  it('handles empty-string second_deciding_factor as missing', () => {
    const display: CohortDisplayProfile = {
      persona_label: 'X',
      n: 20,
      confidence: 'high',
      modal: { top_deciding_factor: 'Quality', second_deciding_factor: '' },
    };
    const { getByText, queryByText } = render(
      <StyleProfileCard display={display} onEditPress={jest.fn()} />
    );
    expect(getByText('Quality')).toBeTruthy();
    // Should not render "Quality, " (with trailing empty)
    expect(queryByText('Quality, ')).toBeNull();
  });
});
