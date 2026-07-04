/**
 * EditPreferencesFlow — Bundle A Task 4.7
 *
 * Contract (Bundle A design §2 + plan Task 2.12):
 * - pre-fills 4 pages with values from getPreferences()
 * - Continue advances pageIndex (1 → 2 → 3 → 4)
 * - Back decrements pageIndex (or closes navigation on page 1)
 * - last page button label is "Save"
 * - Save calls savePreferences exactly once with merged payload
 * - shows inline error if save fails (no nav goBack)
 * - successful save navigates back
 */

import React from 'react';
import { render, fireEvent, waitFor, act } from '@testing-library/react-native';

const mockGetPreferences = jest.fn();
const mockSavePreferences = jest.fn();
jest.mock('../src/services/api', () => ({
  getPreferences: (...a: any[]) => mockGetPreferences(...a),
  savePreferences: (...a: any[]) => mockSavePreferences(...a),
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

jest.mock('lucide-react-native', () => ({ ChevronLeft: 'ChevronLeft', X: 'X' }));

jest.mock('expo-haptics', () => ({
  selectionAsync: jest.fn(),
  notificationAsync: jest.fn(),
  NotificationFeedbackType: { Success: 'success' },
}));

// Picker components — stub to a Text with a testID so we can assert which
// page is rendered without dragging their real implementations in.
jest.mock('../src/components/PrioritiesPicker', () => {
  const React = require('react');
  return function PrioritiesPicker(props: any) {
    return React.createElement(
      'mock-PrioritiesPicker',
      { testID: 'page-priorities', value: JSON.stringify(props.value) },
    );
  };
});
jest.mock('../src/components/BudgetPicker', () => {
  const React = require('react');
  const Component = function BudgetPicker(props: any) {
    return React.createElement(
      'mock-BudgetPicker',
      { testID: 'page-budget', value: String(props.value) },
    );
  };
  return { __esModule: true, default: Component };
});
jest.mock('../src/components/LifestylePicker', () => {
  const React = require('react');
  return function LifestylePicker(props: any) {
    return React.createElement(
      'mock-LifestylePicker',
      { testID: 'page-lifestyle', value: JSON.stringify(props.value) },
    );
  };
});
jest.mock('../src/components/BrandAttitudePicker', () => {
  const React = require('react');
  const Component = function BrandAttitudePicker(props: any) {
    return React.createElement(
      'mock-BrandAttitudePicker',
      { testID: 'page-brand', value: String(props.value) },
    );
  };
  return { __esModule: true, default: Component };
});

import EditPreferencesFlow from '../src/screens/EditPreferencesFlow';

const mockNavigation: any = { goBack: jest.fn() };

function renderScreen() {
  return render(
    <EditPreferencesFlow
      navigation={mockNavigation}
      route={{ params: undefined, key: 'k', name: 'EditPreferences' } as any}
    />,
  );
}

const FIXTURE_PREFS = {
  priorities: ['quality_reliability', 'best_price'],
  budget: 'premium',
  lifestyle: ['busy_professional'],
  brand_attitude: 'trust_known_brands',
};

describe('EditPreferencesFlow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetPreferences.mockResolvedValue(FIXTURE_PREFS);
    mockSavePreferences.mockResolvedValue({ success: true });
  });

  it('pre-fills priorities, mapping cohort-seeded values to canonical display keys', async () => {
    const { findByTestId } = renderScreen();
    const page = await findByTestId('page-priorities');
    // FIXTURE has cohort-derived priorities (quality_reliability, best_price)
    // which EditPreferencesFlow canonicalizes on load so the picker can show
    // and edit them instead of leaving them invisible (device bug 2026-07-04).
    expect(JSON.parse(page.props.value)).toEqual(['quality', 'price']);
  });

  it('Continue advances through all 4 pages and last page shows Save', async () => {
    const { findByText, findByTestId, getByText } = renderScreen();
    await findByTestId('page-priorities');

    fireEvent.press(getByText('preferences.flow.continue'));
    await findByTestId('page-budget');

    fireEvent.press(getByText('preferences.flow.continue'));
    await findByTestId('page-lifestyle');

    fireEvent.press(getByText('preferences.flow.continue'));
    await findByTestId('page-brand');

    // Last page — button label is Save
    await findByText('preferences.flow.save');
  });

  it('Back on page 1 closes via navigation.goBack', async () => {
    const { findByTestId, getByLabelText } = renderScreen();
    await findByTestId('page-priorities');

    fireEvent.press(getByLabelText('common.close'));
    expect(mockNavigation.goBack).toHaveBeenCalledTimes(1);
  });

  it('Back on page 2 returns to page 1 without closing', async () => {
    const { findByTestId, getByText, getByLabelText } = renderScreen();
    await findByTestId('page-priorities');
    fireEvent.press(getByText('preferences.flow.continue'));
    await findByTestId('page-budget');

    fireEvent.press(getByLabelText('common.back'));

    await findByTestId('page-priorities');
    expect(mockNavigation.goBack).not.toHaveBeenCalled();
  });

  it('Save calls savePreferences exactly once with merged payload and navigates back', async () => {
    const { findByTestId, findByText, getByText } = renderScreen();
    await findByTestId('page-priorities');
    fireEvent.press(getByText('preferences.flow.continue'));
    await findByTestId('page-budget');
    fireEvent.press(getByText('preferences.flow.continue'));
    await findByTestId('page-lifestyle');
    fireEvent.press(getByText('preferences.flow.continue'));
    await findByTestId('page-brand');

    const saveBtn = await findByText('preferences.flow.save');
    await act(async () => { fireEvent.press(saveBtn); });

    await waitFor(() => expect(mockSavePreferences).toHaveBeenCalledTimes(1));
    // priorities are saved as their canonicalized form (see load-time mapping).
    expect(mockSavePreferences).toHaveBeenCalledWith(
      expect.objectContaining({ ...FIXTURE_PREFS, priorities: ['quality', 'price'] }),
    );
    expect(mockNavigation.goBack).toHaveBeenCalled();
  });

  it('shows inline error when save fails and does NOT call goBack', async () => {
    mockSavePreferences.mockResolvedValueOnce({ success: false });

    const { findByTestId, findByText, getByText } = renderScreen();
    await findByTestId('page-priorities');
    for (let i = 0; i < 3; i++) {
      fireEvent.press(getByText('preferences.flow.continue'));
    }
    await findByTestId('page-brand');
    const saveBtn = await findByText('preferences.flow.save');
    await act(async () => { fireEvent.press(saveBtn); });

    await findByText('preferences.error.saveFailed');
    expect(mockNavigation.goBack).not.toHaveBeenCalled();
  });

  it('falls back to default preferences if getPreferences rejects', async () => {
    mockGetPreferences.mockRejectedValueOnce(new Error('network'));
    const { findByTestId } = renderScreen();
    const page = await findByTestId('page-priorities');
    expect(JSON.parse(page.props.value)).toEqual([]);
  });
});
