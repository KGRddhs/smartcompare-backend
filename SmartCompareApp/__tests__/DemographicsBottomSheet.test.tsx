/**
 * DemographicsBottomSheet component tests.
 *
 * Covers: render fields, all-skip submission, payload shape on save,
 * loading state, and i18n key usage. The trigger logic is tested
 * separately in demographicsTrigger.test.ts.
 */

import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import DemographicsBottomSheet from '../src/components/DemographicsBottomSheet';

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: 'en' },
  }),
}));

jest.mock('expo-localization', () => ({
  locale: 'en-US',
  getLocales: () => [{ languageCode: 'en', regionCode: 'BH' }],
}));

jest.mock('expo-haptics', () => ({
  selectionAsync: jest.fn(),
  impactAsync: jest.fn(),
  ImpactFeedbackStyle: { Light: 'light', Medium: 'medium' },
}));

describe('DemographicsBottomSheet', () => {
  const noop = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders nothing when not visible', () => {
    const { queryByText } = render(
      <DemographicsBottomSheet visible={false} onSubmit={noop} onSkip={noop} />
    );
    expect(queryByText('demographics.title')).toBeNull();
  });

  it('renders title, subtitle, and 3 question labels when visible', () => {
    const { getByText } = render(
      <DemographicsBottomSheet visible onSubmit={noop} onSkip={noop} />
    );
    expect(getByText('demographics.title')).toBeTruthy();
    expect(getByText('demographics.subtitle')).toBeTruthy();
    expect(getByText('demographics.age')).toBeTruthy();
    expect(getByText('demographics.gender')).toBeTruthy();
    expect(getByText('demographics.governorate')).toBeTruthy();
  });

  it('shows Save and Skip buttons', () => {
    const { getByText } = render(
      <DemographicsBottomSheet visible onSubmit={noop} onSkip={noop} />
    );
    expect(getByText('demographics.save')).toBeTruthy();
    expect(getByText('demographics.skip')).toBeTruthy();
  });

  it('calls onSkip when Skip pressed (no payload)', () => {
    const onSkip = jest.fn();
    const onSubmit = jest.fn();
    const { getByText } = render(
      <DemographicsBottomSheet visible onSubmit={onSubmit} onSkip={onSkip} />
    );
    fireEvent.press(getByText('demographics.skip'));
    expect(onSkip).toHaveBeenCalledTimes(1);
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('calls onSubmit with selected values when Save pressed', async () => {
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    const { getByText } = render(
      <DemographicsBottomSheet visible onSubmit={onSubmit} onSkip={noop} />
    );
    fireEvent.press(getByText('demographics.age.25_34'));
    fireEvent.press(getByText('demographics.gender.female'));
    fireEvent.press(getByText('demographics.governorate.northern'));
    fireEvent.press(getByText('demographics.save'));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalled();
    });
    const arg = onSubmit.mock.calls[0][0];
    expect(arg.age_group).toBe('25-34');
    expect(arg.gender).toBe('Female');
    expect(arg.governorate).toBe('Northern');
  });

  it('submits with all "Prefer not to say" if user only taps Save', async () => {
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    const { getByText } = render(
      <DemographicsBottomSheet visible onSubmit={onSubmit} onSkip={noop} />
    );
    // Default: nothing selected. Save still works (all become "Prefer not to say").
    fireEvent.press(getByText('demographics.save'));
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalled();
    });
    const arg = onSubmit.mock.calls[0][0];
    expect(arg.age_group).toBe('Prefer not to say');
    expect(arg.gender).toBe('Prefer not to say');
    expect(arg.governorate).toBe('Prefer not to say');
  });

  it('attaches auto-detected language from expo-localization', async () => {
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    const { getByText } = render(
      <DemographicsBottomSheet visible onSubmit={onSubmit} onSkip={noop} />
    );
    fireEvent.press(getByText('demographics.save'));
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalled();
    });
    const arg = onSubmit.mock.calls[0][0];
    expect(arg.language).toBe('English');
  });

  it('disables Save while submitting (loading state)', async () => {
    let resolve: () => void = () => {};
    const onSubmit = jest.fn(() => new Promise<void>((r) => { resolve = r; }));
    const onSkip = jest.fn();
    const { getByText, queryByText } = render(
      <DemographicsBottomSheet visible onSubmit={onSubmit} onSkip={onSkip} />
    );
    fireEvent.press(getByText('demographics.save'));
    // Save text is replaced by ActivityIndicator while submitting
    expect(queryByText('demographics.save')).toBeNull();
    // Skip press is also a no-op while submitting
    fireEvent.press(getByText('demographics.skip'));
    expect(onSkip).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });
    resolve();
  });

  it('lists 3 "Prefer not to say" chips (one per question)', () => {
    const { getAllByText } = render(
      <DemographicsBottomSheet visible onSubmit={noop} onSkip={noop} />
    );
    const skips = getAllByText('demographics.preferNotToSay');
    expect(skips.length).toBe(3);
  });
});
