/**
 * EditProfileScreen Bundle E S3 — integration render tests for coverage push.
 *
 * Source-grep contract test lives at EditProfileScreen.bundleE.s3.test.tsx;
 * this file adds runtime coverage by actually rendering the screen.
 *
 * Pattern: synchronous render() + waitFor() for async assertions. Avoid
 * @testing-library/react-native's act() wrapper — it triggers a "Can't
 * access .root on unmounted test renderer" error against the screen's
 * useFocusEffect → setState chain. The pattern below mirrors the working
 * AuthScreens.test.tsx in this codebase.
 */

import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react-native';

jest.mock('@react-navigation/native', () => {
  const ReactRequired = require('react');
  return {
    useFocusEffect: (cb: any) => {
      ReactRequired.useEffect(() => {
        const cleanup = cb();
        return cleanup;
      }, []);
    },
  };
});

const mockUpdateProfile = jest.fn();
const mockApiDelete = jest.fn();
const mockGetSavedUser = jest.fn();
const mockClearSession = jest.fn();
const mockUpdateSavedUserDisplayName = jest.fn();

jest.mock('../src/services/api', () => ({
  __esModule: true,
  default: {
    delete: (...args: any[]) => mockApiDelete(...args),
  },
  parseApiError: (e: any) => ({ message: e?.message || 'error' }),
  updateProfile: (...args: any[]) => mockUpdateProfile(...args),
}));

jest.mock('../src/services/authService', () => ({
  getSavedUser: (...args: any[]) => mockGetSavedUser(...args),
  clearSession: (...args: any[]) => mockClearSession(...args),
  updateSavedUserDisplayName: (...args: any[]) =>
    mockUpdateSavedUserDisplayName(...args),
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: any) => {
      if (opts && typeof opts === 'object' && 'defaultValue' in opts) {
        return opts.defaultValue;
      }
      return key;
    },
  }),
}));

import EditProfileScreen from '../src/screens/EditProfileScreen';

function makeProps(overrides: any = {}) {
  return {
    navigation: {
      goBack: jest.fn(),
      navigate: jest.fn(),
    },
    route: {
      params: undefined,
      key: 'EditProfile',
      name: 'EditProfile' as const,
    },
    onAccountDeleted: jest.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  mockGetSavedUser.mockResolvedValue({
    id: 'u1',
    display_name: 'Kareem',
    email: 'kareem@example.com',
  });
});

describe('EditProfileScreen S3 integration — initial render', () => {
  it('renders all 3 main interactive testIDs', () => {
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    expect(rendered.getByTestId('edit-save-cta')).toBeTruthy();
    expect(rendered.getByTestId('edit-delete-account-row')).toBeTruthy();
    expect(rendered.getByTestId('edit-style-profile-row')).toBeTruthy();
  });

  it('renders the Account actions eyebrow + Apple-relay placeholder slot', () => {
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    expect(rendered.getByText('Account actions')).toBeTruthy();
  });

  it('renders avatar letter from display_name after user loads', async () => {
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    await waitFor(() => {
      expect(rendered.getByText('K')).toBeTruthy();
    });
  });

  it('renders raw email when not Apple relay after user loads', async () => {
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    await waitFor(() => {
      expect(rendered.getByText('kareem@example.com')).toBeTruthy();
    });
  });

  it('initial Save CTA is disabled (clean state, not dirty)', () => {
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    const cta = rendered.getByTestId('edit-save-cta');
    // The accessibilityState is the React Native prop — the mocked
    // TouchableOpacity passes it through to the View tree.
    expect(cta.props.accessibilityState).toEqual({ disabled: true });
  });
});

describe('EditProfileScreen S3 integration — Apple Hide-My-Email mask', () => {
  it('shows Apple ID label + caption when @privaterelay.appleid.com', async () => {
    mockGetSavedUser.mockResolvedValueOnce({
      id: 'u2',
      display_name: 'Kareem',
      email: 'abc123@privaterelay.appleid.com',
    });
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    await waitFor(() => {
      expect(rendered.getByText('Apple ID')).toBeTruthy();
    });
    expect(rendered.getByText('Email kept private by Apple')).toBeTruthy();
  });

  it('handles null user from getSavedUser by rendering ? avatar', async () => {
    mockGetSavedUser.mockResolvedValueOnce(null);
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    await waitFor(() => {
      expect(rendered.getByText('?')).toBeTruthy();
    });
  });
});

describe('EditProfileScreen S3 integration — Edit-style-profile NavRow', () => {
  it('renders the sub-line caption from i18n defaultValue', () => {
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    expect(
      rendered.getByText('Update priorities, budget, and brand stance'),
    ).toBeTruthy();
  });

  it('pressing the Edit-style-profile row navigates to EditPreferences', async () => {
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    const row = rendered.getByTestId('edit-style-profile-row');
    fireEvent.press(row);
    expect(props.navigation.navigate).toHaveBeenCalledWith('EditPreferences');
  });
});

describe('EditProfileScreen S3 integration — Save CTA flow', () => {
  it('CTA enables after typing a sufficiently long name change', async () => {
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    // Wait for initial user load to seed initialName='Kareem'.
    await waitFor(() => {
      expect(rendered.getByText('K')).toBeTruthy();
    });
    const inputs = rendered.UNSAFE_getAllByType('TextInput');
    fireEvent.changeText(inputs[0], 'Karim Updated');
    const cta = rendered.getByTestId('edit-save-cta');
    await waitFor(() => {
      expect(cta.props.accessibilityState).toEqual({ disabled: false });
    });
  });

  it('Save success path calls updateProfile + cache write + goBack', async () => {
    mockUpdateProfile.mockResolvedValueOnce({ success: true });
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    await waitFor(() => {
      expect(rendered.getByText('K')).toBeTruthy();
    });
    const inputs = rendered.UNSAFE_getAllByType('TextInput');
    fireEvent.changeText(inputs[0], 'Karim Updated');
    const cta = rendered.getByTestId('edit-save-cta');
    fireEvent.press(cta);
    await waitFor(() => {
      expect(mockUpdateProfile).toHaveBeenCalledWith('Karim Updated');
    });
    expect(mockUpdateSavedUserDisplayName).toHaveBeenCalledWith('Karim Updated');
    expect(props.navigation.goBack).toHaveBeenCalled();
  });

  it('Save backend-error path surfaces editProfile.error.saveFailed', async () => {
    mockUpdateProfile.mockResolvedValueOnce({ success: false });
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    await waitFor(() => {
      expect(rendered.getByText('K')).toBeTruthy();
    });
    const inputs = rendered.UNSAFE_getAllByType('TextInput');
    fireEvent.changeText(inputs[0], 'Karim Updated');
    const cta = rendered.getByTestId('edit-save-cta');
    fireEvent.press(cta);
    await waitFor(() => {
      expect(rendered.getByText('editProfile.error.saveFailed')).toBeTruthy();
    });
    expect(props.navigation.goBack).not.toHaveBeenCalled();
  });

  it('Save throw path catches + surfaces saveFailed', async () => {
    mockUpdateProfile.mockRejectedValueOnce(new Error('network boom'));
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    await waitFor(() => {
      expect(rendered.getByText('K')).toBeTruthy();
    });
    const inputs = rendered.UNSAFE_getAllByType('TextInput');
    fireEvent.changeText(inputs[0], 'Karim Updated');
    const cta = rendered.getByTestId('edit-save-cta');
    fireEvent.press(cta);
    await waitFor(() => {
      expect(rendered.getByText('editProfile.error.saveFailed')).toBeTruthy();
    });
  });
});

describe('EditProfileScreen S3 integration — back button + delete flow', () => {
  it('back button triggers navigation.goBack', () => {
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    const backBtns = rendered.UNSAFE_getAllByProps({
      accessibilityLabel: 'common.back',
    });
    fireEvent.press(backBtns[0]);
    expect(props.navigation.goBack).toHaveBeenCalled();
  });

  it('Delete row tap triggers Alert.alert; confirming deletes account', async () => {
    mockApiDelete.mockResolvedValueOnce({});
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert');
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    const deleteRow = rendered.getByTestId('edit-delete-account-row');
    fireEvent.press(deleteRow);
    expect(alertSpy).toHaveBeenCalled();
    const buttons = alertSpy.mock.calls[0][2] as any[];
    const destructive = buttons.find((b: any) => b.style === 'destructive');
    await destructive.onPress();
    expect(mockApiDelete).toHaveBeenCalledWith('/api/v1/auth/account');
    expect(mockClearSession).toHaveBeenCalled();
    expect(props.onAccountDeleted).toHaveBeenCalled();
    alertSpy.mockRestore();
  });

  it('Delete API failure path does NOT call onAccountDeleted', async () => {
    mockApiDelete.mockRejectedValueOnce(new Error('500 boom'));
    const RN = require('react-native');
    const alertSpy = jest.spyOn(RN.Alert, 'alert');
    const props = makeProps();
    const rendered = render(<EditProfileScreen {...props} />);
    const deleteRow = rendered.getByTestId('edit-delete-account-row');
    fireEvent.press(deleteRow);
    const buttons = alertSpy.mock.calls[0][2] as any[];
    const destructive = buttons.find((b: any) => b.style === 'destructive');
    await destructive.onPress();
    expect(props.onAccountDeleted).not.toHaveBeenCalled();
    alertSpy.mockRestore();
  });
});
