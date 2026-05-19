/**
 * Bundle C — EditPreferencesFlow 5-tier passthrough (Plan B.4.4)
 *
 * Spec § 3a — EditPreferencesFlow accepts the full 5-tier BudgetValue.
 * Verifies the picker forwards `top_tier` upward and that
 * `savePreferences` receives the new tier verbatim.
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

// Real BudgetPicker — exercise its 5-tier card render through the flow.
// (Other pickers stubbed to keep this test focused on the budget page.)
jest.mock('../src/components/PrioritiesPicker', () => {
  const React = require('react');
  return function PrioritiesPicker(props: any) {
    return React.createElement('mock-PrioritiesPicker', { testID: 'page-priorities', value: JSON.stringify(props.value) });
  };
});
jest.mock('../src/components/LifestylePicker', () => {
  const React = require('react');
  return function LifestylePicker(props: any) {
    return React.createElement('mock-LifestylePicker', { testID: 'page-lifestyle', value: JSON.stringify(props.value) });
  };
});
jest.mock('../src/components/BrandAttitudePicker', () => {
  const React = require('react');
  const Component = function BrandAttitudePicker(props: any) {
    return React.createElement('mock-BrandAttitudePicker', { testID: 'page-brand', value: props.value });
  };
  return { __esModule: true, default: Component };
});

import EditPreferencesFlow from '../src/screens/EditPreferencesFlow';

function makeProps() {
  return {
    navigation: { goBack: jest.fn() },
    route: { key: 'edit-prefs', name: 'EditPreferences' as const, params: undefined },
  } as any;
}

beforeEach(() => {
  mockGetPreferences.mockReset();
  mockSavePreferences.mockReset();
});

test('user can pick top_tier on the budget page and save payload includes budget: top_tier', async () => {
  mockGetPreferences.mockResolvedValue({
    priorities: ['quality'],
    budget: 'mid',
    lifestyle: ['gamer'],
    brand_attitude: 'best_of_both',
  });
  mockSavePreferences.mockResolvedValue({ success: true });

  const props = makeProps();
  const { getByText, getByTestId, findByTestId } = render(<EditPreferencesFlow {...props} />);

  // Wait for getPreferences to resolve and the priorities page to render.
  await findByTestId('page-priorities');

  // Advance past priorities (page 1) → budget (page 2).
  await act(async () => {
    fireEvent.press(getByText('preferences.flow.continue'));
  });

  // The real BudgetPicker now renders. Pick top_tier.
  await act(async () => {
    fireEvent.press(getByTestId('budget-top_tier'));
  });

  // Advance budget → lifestyle → brand.
  await act(async () => { fireEvent.press(getByText('preferences.flow.continue')); });
  await act(async () => { fireEvent.press(getByText('preferences.flow.continue')); });

  // Last page button label is "preferences.flow.save". Save fires savePreferences.
  await act(async () => {
    fireEvent.press(getByText('preferences.flow.save'));
  });

  await waitFor(() => expect(mockSavePreferences).toHaveBeenCalledTimes(1));
  expect(mockSavePreferences).toHaveBeenCalledWith(
    expect.objectContaining({ budget: 'top_tier' }),
  );
});
